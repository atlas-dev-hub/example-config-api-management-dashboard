"""Connection manager — stores and manages multiple SM connections."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sm_config_api import ConnectionConfig, SystemMonitorClient

logger = logging.getLogger(__name__)

SETTINGS_FILE = Path(__file__).parent.parent / "connections.json"


def _friendly_error(exc: Exception) -> str:
    """Extract a short, human-readable message from gRPC / connection errors."""
    msg = str(exc)
    # gRPC UNAVAILABLE — server unreachable
    if "UNAVAILABLE" in msg or "failed to connect" in msg:
        return "Server unreachable — check address and ensure System Monitor is running"
    # Deadline exceeded
    if "DEADLINE_EXCEEDED" in msg or "timed out" in msg.lower():
        return "Connection timed out — server did not respond"
    # TLS handshake
    if "handshake" in msg.lower() or "SSL" in msg or "certificate" in msg.lower():
        return "TLS handshake failed — try toggling Insecure or check certificates"
    # DNS resolution
    if "DNS" in msg or "Name resolution" in msg:
        return "DNS resolution failed — check hostname"
    # Fallback: trim to first meaningful line
    first_line = msg.split("\n")[0].strip()
    return first_line[:200] if len(first_line) > 200 else first_line


@dataclass
class SMConnection:
    """Represents one System Monitor connection."""

    name: str
    address: str
    ca_cert: bytes | None = None
    insecure: bool = False
    client: SystemMonitorClient | None = field(default=None, repr=False)

    # Last known status
    link_status: str = "Unknown"
    online: bool = False
    live_update: bool = False
    connected: bool = False
    failed: bool = False
    error_message: str = ""

    # Application details (fetched on connect, refreshed on demand)
    # Each entry: {"app_id": int, "app_name": str, "pgv_id": int, "dtv_version": str}
    app_info: list[dict] = field(default_factory=list)

    def config(self) -> ConnectionConfig:
        options = []
        if self.ca_cert:
            # Override hostname to match the certificate CN (e.g. "localhost")
            # rather than the actual connection address (e.g. "10.0.0.1")
            cn = self._extract_cert_cn()
            if cn:
                options.append(("grpc.ssl_target_name_override", cn))
        return ConnectionConfig(
            address=self.address,
            ca_cert=self.ca_cert,
            insecure=self.insecure,
            options=options,
        )

    def _extract_cert_cn(self) -> str | None:
        """Extract the Common Name from the probed server certificate."""
        if not self.ca_cert:
            return None
        try:
            from cryptography import x509
            cert = x509.load_pem_x509_certificate(self.ca_cert)
            cns = cert.subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)
            return cns[0].value if cns else None
        except Exception:
            return None

    def connect(self) -> None:
        """Open the gRPC connection and verify the server is reachable."""
        self.failed = False
        try:
            self.client = SystemMonitorClient(self.config(), timeout=None)
            # gRPC channels are lazy — force an actual RPC to verify connectivity
            status = self.client.system.get_status(timeout=15.0)
            self.connected = True
            self.error_message = ""
            # Populate initial status from the validation call
            try:
                from sm_config_api.enums import LinkStatus
                self.link_status = LinkStatus(status.link_status).name
            except (ValueError, ImportError):
                self.link_status = f"UNKNOWN({status.link_status})"
            self.online = status.online
            self.live_update = status.live_update
            logger.info("Connected to %s (%s)", self.name, self.address)
            # Fetch application details (PGV/DTV) on initial connect
            self.fetch_app_info()
        except Exception as exc:
            self.connected = False
            self.failed = True
            self.error_message = _friendly_error(exc)
            if self.client:
                try:
                    self.client.close()
                except Exception:
                    pass
            self.client = None
            logger.error("Failed to connect to %s: %s", self.name, self.error_message)

    def disconnect(self) -> None:
        """Close the gRPC connection."""
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass
        self.client = None
        self.connected = False
        self.failed = False
        self.link_status = "Disconnected"
        self.online = False
        self.live_update = False
        self.app_info = []

    def poll_status(self) -> None:
        """Poll the SM status — call from background thread only."""
        if not self.client:
            return
        try:
            from sm_config_api.enums import LinkStatus
            status = self.client.system.get_status(timeout=15.0)
            try:
                self.link_status = LinkStatus(status.link_status).name
            except ValueError:
                self.link_status = f"UNKNOWN({status.link_status})"
            self.online = status.online
            self.live_update = status.live_update
            self.error_message = ""
        except Exception as exc:
            self.link_status = "ERROR"
            self.online = False
            self.live_update = False
            self.error_message = _friendly_error(exc)

    def fetch_app_info(self) -> None:
        """Fetch per-application PGV/DTV details. Safe to call from any thread."""
        if not self.client:
            return
        try:
            apps = self.client.project.get_app_details()
            info: list[dict] = []
            for app in apps:
                entry: dict = {
                    "app_id": app.app_id,
                    "app_name": app.app_name,
                    "pgv_id": None,
                    "dtv_version": None,
                }
                try:
                    entry["pgv_id"] = self.client.project.get_pgv_id(app.app_id)
                except Exception:
                    pass
                try:
                    entry["dtv_version"] = self.client.project.get_dtv_version(app.app_id)
                except Exception:
                    pass
                info.append(entry)
            self.app_info = info
            logger.debug("Fetched app info for %s: %d apps", self.name, len(info))
        except Exception as exc:
            logger.debug("Could not fetch app info for %s: %s", self.name, exc)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "address": self.address, "insecure": self.insecure}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SMConnection:
        return cls(
            name=data.get("name", "Unnamed"),
            address=data.get("address", "localhost:7000"),
            insecure=data.get("insecure", False),
        )


class ConnectionStore:
    """Manages a list of SM connections with persistence."""

    def __init__(self):
        self.connections: list[SMConnection] = []

    def add(self, conn: SMConnection) -> None:
        self.connections.append(conn)

    def remove(self, index: int) -> None:
        if 0 <= index < len(self.connections):
            self.connections[index].disconnect()
            del self.connections[index]

    def save(self, path: Path = SETTINGS_FILE) -> None:
        data = [c.to_dict() for c in self.connections]
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def load(self, path: Path = SETTINGS_FILE) -> None:
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for item in data:
                self.connections.append(SMConnection.from_dict(item))
        except Exception as exc:
            logger.error("Failed to load connections: %s", exc)

    def disconnect_all(self) -> None:
        for conn in self.connections:
            conn.disconnect()
