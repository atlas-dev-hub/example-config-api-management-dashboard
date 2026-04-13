"""Connection management for the System Monitor Configuration API.

Handles:
- mTLS channel creation (PEM files or PFX/PKCS#12 certificates)
- OAuth2 ``client_credentials`` token management with automatic refresh
- Bearer-token injection via gRPC call credentials
- Compatibility with the C# sample client ``settings.json`` format

Quick start — insecure (local dev)::

    from sm_config_api.connection import ConnectionConfig, create_channel

    cfg = ConnectionConfig(address="localhost:5001", insecure=True)
    channel = create_channel(cfg)

Quick start — mTLS + OAuth2::

    cfg = ConnectionConfig.from_json("settings.json")
    conn = Connection(cfg)
    # conn.channel  → grpc.Channel (with auto-injected bearer tokens)
    # conn.token_manager.refresh()  → force token refresh
    conn.close()

Or as a context manager::

    with Connection(cfg) as conn:
        stub = SystemMonitorSystemStub(conn.channel)
        ...
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

import grpc

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class ConnectionConfig:
    """Configuration for connecting to a System Monitor Configuration API server.

    Supports three connection modes:

    1. **Insecure** (plaintext) — set ``insecure=True``; for local development only.
    2. **TLS with PEM certificates** — provide ``client_cert``, ``client_key``,
       and optionally ``ca_cert`` as file paths or raw ``bytes``.
    3. **TLS with PFX/PKCS#12** — provide ``pfx_path`` and ``pfx_password``.
       This is compatible with the C# sample which uses
       ``X509Certificate2(path, password)``.

    OAuth2 bearer-token authentication can be layered on top of any TLS mode
    by setting ``use_token=True`` together with ``client_id``, ``client_secret``,
    ``token_uri``, and ``audience``.
    """

    # Server address — accepts "https://host:port", "host:port", or just "host"
    address: str = ""

    # --- mTLS: PEM paths or raw bytes ---
    client_cert: str | bytes | None = None
    client_key: str | bytes | None = None
    ca_cert: str | bytes | None = None

    # --- mTLS: PFX (PKCS#12) alternative ---
    pfx_path: str | None = None
    pfx_password: str | None = None

    # --- OAuth2 client_credentials ---
    use_token: bool = False
    client_id: str | None = None
    client_secret: str | None = None
    token_uri: str | None = None
    audience: str | None = None

    # --- Connection options ---
    insecure: bool = False
    options: list[tuple[str, str | int]] = field(default_factory=list)

    # ---- Factories ----

    @classmethod
    def from_json(cls, path: str | Path) -> ConnectionConfig:
        """Load from a ``settings.json`` file.

        Accepts the same JSON keys used by the C# sample client::

            {
                "address": "https://hostname:port",
                "certifiate": "path/to/cert.pfx",
                "key": "pfx_password",
                "use_token": false,
                "client_id": "...",
                "client_secret": "...",
                "token_uri": "...",
                "audience": "..."
            }

        .. note:: The typo ``"certifiate"`` in the C# sample is intentionally
           supported alongside the correct ``"certificate"`` spelling.
        """
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict) -> ConnectionConfig:
        """Create from a dictionary.

        Recognises both C# settings.json keys and native Python field names.
        """
        # Handle the C# "certifiate" typo and our own field names
        cert = (
            data.get("pfx_path")
            or data.get("certificate")
            or data.get("certifiate")  # C# sample typo
        )
        key = data.get("pfx_password") or data.get("key")

        return cls(
            address=data.get("address", ""),
            pfx_path=cert,
            pfx_password=key,
            client_cert=data.get("client_cert"),
            client_key=data.get("client_key"),
            ca_cert=data.get("ca_cert"),
            use_token=data.get("use_token", False),
            client_id=data.get("client_id"),
            client_secret=data.get("client_secret"),
            token_uri=data.get("token_uri"),
            audience=data.get("audience"),
            insecure=data.get("insecure", False),
            options=data.get("options", []),
        )

    # ---- Helpers ----

    @property
    def target(self) -> str:
        """Return a gRPC-compatible target string (``host:port``).

        Strips any URI scheme (``https://``, ``http://``) since Python gRPC
        channel constructors expect plain ``host:port``.
        """
        addr = self.address.strip()
        if not addr:
            raise ValueError("ConnectionConfig.address is empty")

        parsed = urlparse(addr)
        if parsed.hostname:
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            return f"{parsed.hostname}:{port}"

        # Already in host:port format (or bare hostname)
        return addr if ":" in addr else f"{addr}:443"


# ---------------------------------------------------------------------------
# Certificate helpers
# ---------------------------------------------------------------------------

def _read_pem(source: str | bytes | None) -> bytes | None:
    """Read PEM material from a file path or return raw bytes as-is."""
    if source is None:
        return None
    if isinstance(source, bytes):
        return source
    return Path(source).read_bytes()


def _load_pfx(pfx_path: str, password: str | None = None) -> tuple[bytes, bytes, bytes | None]:
    """Extract PEM certificate, private key, and optional CA chain from a PFX file.

    Args:
        pfx_path: Path to the ``.pfx`` / ``.p12`` file.
        password: PFX password (may be ``None`` for unprotected files).

    Returns:
        ``(client_cert_pem, client_key_pem, ca_certs_pem_or_none)``

    Raises:
        ValueError: If the PFX does not contain a valid key+certificate pair.
        FileNotFoundError: If *pfx_path* does not exist.
    """
    from cryptography.hazmat.primitives.serialization import (
        Encoding,
        NoEncryption,
        PrivateFormat,
        pkcs12,
    )

    pfx_data = Path(pfx_path).read_bytes()
    pwd = password.encode("utf-8") if password else None

    private_key, certificate, additional_certs = pkcs12.load_key_and_certificates(
        pfx_data, pwd,
    )

    if private_key is None or certificate is None:
        raise ValueError(
            f"PFX file '{pfx_path}' does not contain a valid key/certificate pair"
        )

    key_pem = private_key.private_bytes(
        Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption(),
    )
    cert_pem = certificate.public_bytes(Encoding.PEM)

    ca_pem: bytes | None = None
    if additional_certs:
        ca_pem = b"".join(c.public_bytes(Encoding.PEM) for c in additional_certs)

    return cert_pem, key_pem, ca_pem


# ---------------------------------------------------------------------------
# OAuth2 token management
# ---------------------------------------------------------------------------

class TokenManager:
    """Manages OAuth2 access tokens using the ``client_credentials`` grant.

    Fetches tokens from the configured ``token_uri``, caches them, and
    automatically refreshes when they approach expiry.

    Example::

        tm = TokenManager(config)
        if tm.is_configured:
            token = tm.access_token   # auto-fetches / refreshes
            print(tm.authorization_value)  # "Bearer eyJ..."
    """

    _EXPIRY_MARGIN_SECONDS = 30

    def __init__(self, config: ConnectionConfig):
        self._config = config
        self._access_token: str | None = None
        self._token_type: str = "Bearer"
        self._expires_at: float = 0.0

    # ---- State queries ----

    @property
    def is_configured(self) -> bool:
        """``True`` if OAuth2 settings are present and ``use_token`` is enabled."""
        return (
            self._config.use_token
            and bool(self._config.token_uri)
            and bool(self._config.client_id)
            and bool(self._config.client_secret)
        )

    @property
    def is_expired(self) -> bool:
        """``True`` if the cached token is missing or past its expiry margin."""
        return self._access_token is None or time.time() >= self._expires_at

    # ---- Token access ----

    @property
    def access_token(self) -> str | None:
        """Return the current access token, refreshing automatically if needed.

        Returns ``None`` when OAuth2 is not configured.
        """
        if not self.is_configured:
            return None
        if self.is_expired:
            self.refresh()
        return self._access_token

    @property
    def authorization_value(self) -> str | None:
        """Full ``Authorization`` header value, e.g. ``"Bearer eyJ..."``."""
        token = self.access_token
        if token is None:
            return None
        return f"{self._token_type} {token}"

    # ---- Refresh ----

    def refresh(self) -> str:
        """Fetch a new token from the OAuth2 endpoint.

        Returns:
            The new access-token string.

        Raises:
            ConnectionError: If the HTTP request fails or returns non-200.
        """
        import requests as _requests  # lazy import — only needed when OAuth2 is used

        payload = {
            "client_id": self._config.client_id,
            "client_secret": self._config.client_secret,
            "audience": self._config.audience,
            "grant_type": "client_credentials",
        }

        logger.debug("Requesting access token from %s", self._config.token_uri)

        try:
            response = _requests.post(
                self._config.token_uri,  # type: ignore[arg-type]
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
        except _requests.RequestException as exc:
            raise ConnectionError(f"Token request failed: {exc}") from exc

        if response.status_code != 200:
            raise ConnectionError(
                f"Token request failed [{response.status_code}]: {response.text}"
            )

        data = response.json()
        self._access_token = data["access_token"]
        self._token_type = data.get("token_type", "Bearer")

        expires_in = int(data.get("expires_in", 3600))
        self._expires_at = time.time() + expires_in - self._EXPIRY_MARGIN_SECONDS

        logger.info("Access token obtained (expires in %ds)", expires_in)
        return self._access_token

    def clear(self) -> None:
        """Discard the cached token, forcing a refresh on next access."""
        self._access_token = None
        self._expires_at = 0.0


# ---------------------------------------------------------------------------
# gRPC auth metadata plugin
# ---------------------------------------------------------------------------

class _BearerTokenPlugin(grpc.AuthMetadataPlugin):
    """Injects the OAuth2 bearer token into every gRPC call's metadata."""

    def __init__(self, token_manager: TokenManager):
        self._token_manager = token_manager

    def __call__(
        self,
        context: grpc.AuthMetadataContext,
        callback: grpc.AuthMetadataPluginCallback,
    ) -> None:
        auth = self._token_manager.authorization_value
        metadata = (("authorization", auth),) if auth else ()
        callback(metadata, None)


# ---------------------------------------------------------------------------
# Channel factory
# ---------------------------------------------------------------------------

def create_channel(
    config: ConnectionConfig,
    token_manager: TokenManager | None = None,
) -> grpc.Channel:
    """Create a gRPC channel from the given configuration.

    Args:
        config: Connection settings (address, certs, OAuth2, etc.).
        token_manager: Optional pre-built :class:`TokenManager`. If ``None``
            and OAuth2 is configured, a new one is created internally.

    Returns:
        A :class:`grpc.Channel` ready for creating service stubs.
    """
    target = config.target
    options = config.options or []

    # --- Insecure (plaintext) channel ---
    if config.insecure:
        logger.info("Creating insecure channel → %s", target)
        return grpc.insecure_channel(target, options=options)

    # --- Resolve certificate material ---
    client_cert_pem: bytes | None = None
    client_key_pem: bytes | None = None
    ca_cert_pem: bytes | None = None

    if config.pfx_path:
        client_cert_pem, client_key_pem, pfx_ca = _load_pfx(
            config.pfx_path, config.pfx_password,
        )
        ca_cert_pem = pfx_ca
        logger.debug("Loaded client certificate from PFX: %s", config.pfx_path)
    else:
        client_cert_pem = _read_pem(config.client_cert)
        client_key_pem = _read_pem(config.client_key)

    # Explicit CA cert always overrides PFX-embedded CA chain
    explicit_ca = _read_pem(config.ca_cert)
    if explicit_ca is not None:
        ca_cert_pem = explicit_ca

    # --- Build SSL channel credentials ---
    ssl_creds = grpc.ssl_channel_credentials(
        root_certificates=ca_cert_pem,
        private_key=client_key_pem,
        certificate_chain=client_cert_pem,
    )

    # --- Optionally layer OAuth2 bearer token ---
    if token_manager is None:
        token_manager = TokenManager(config)

    if token_manager.is_configured:
        call_creds = grpc.metadata_call_credentials(
            _BearerTokenPlugin(token_manager),
        )
        channel_creds = grpc.composite_channel_credentials(ssl_creds, call_creds)
        logger.info("Creating secure channel → %s (mTLS + OAuth2)", target)
    else:
        channel_creds = ssl_creds
        logger.info("Creating secure channel → %s (mTLS)", target)

    return grpc.secure_channel(target, channel_creds, options=options)


# ---------------------------------------------------------------------------
# Connection wrapper
# ---------------------------------------------------------------------------

class Connection:
    """High-level connection wrapper that bundles a gRPC channel with its
    :class:`TokenManager` and :class:`ConnectionConfig`.

    Intended as the main entry point for the library::

        with Connection(cfg) as conn:
            stub = SystemMonitorSystemStub(conn.channel)
            reply = stub.GetVersion(Empty())

    The :class:`~sm_config_api.client.SystemMonitorClient` facade (step 10)
    will accept a ``Connection`` and wire up all five service wrappers.
    """

    def __init__(self, config: ConnectionConfig):
        self.config = config
        self.token_manager = TokenManager(config)
        self.channel = create_channel(config, token_manager=self.token_manager)

    # ---- Lifecycle ----

    def close(self) -> None:
        """Close the underlying gRPC channel and clear any cached tokens."""
        try:
            self.channel.close()
        except Exception:  # noqa: BLE001
            logger.debug("Error closing gRPC channel", exc_info=True)
        self.token_manager.clear()
        logger.info("Connection closed")

    def __enter__(self) -> Connection:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # noqa: ANN001
        self.close()

    def __repr__(self) -> str:
        mode = "insecure" if self.config.insecure else "mTLS"
        if self.token_manager.is_configured:
            mode += "+OAuth2"
        return f"<Connection target={self.config.target!r} mode={mode}>"
