"""Smoke test — verify connectivity to a live System Monitor instance.

Usage:
    # Auto-detect TLS (fetches server cert automatically):
    python scripts/smoke_test.py
    python scripts/smoke_test.py --address localhost:7000

    # With explicit certs:
    python scripts/smoke_test.py --ca-cert server_cert.pem
    python scripts/smoke_test.py --pfx cert.pfx --pfx-password secret

    # With C# settings.json:
    python scripts/smoke_test.py --settings settings.json

    # Force insecure (plaintext):
    python scripts/smoke_test.py --insecure
"""

from __future__ import annotations

import argparse
import logging
import socket
import ssl
import sys
import os

# Ensure the project root is on sys.path so sm_config_api is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sm_config_api.connection import Connection, ConnectionConfig
from sm_config_api.services.system import SystemService
from sm_config_api.enums import LinkStatus

logger = logging.getLogger(__name__)


def fetch_server_cert(host: str, port: int, timeout: float = 5.0) -> bytes | None:
    """Connect to a TLS server, retrieve its certificate, and return PEM bytes.

    Returns ``None`` if the connection fails (e.g. server doesn't use TLS).
    """
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                der_cert = ssock.getpeercert(binary_form=True)

        from cryptography import x509
        from cryptography.hazmat.primitives.serialization import Encoding

        cert = x509.load_der_x509_certificate(der_cert)
        logger.info(
            "Server cert: Subject=%s  Issuer=%s", cert.subject, cert.issuer,
        )
        return cert.public_bytes(Encoding.PEM)
    except Exception as exc:
        logger.debug("TLS probe failed: %s", exc)
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test System Monitor connectivity")
    parser.add_argument("--address", default="localhost:7000", help="Server address (host:port)")
    parser.add_argument("--insecure", action="store_true", help="Force insecure (plaintext) channel")
    parser.add_argument("--pfx", help="Path to PFX client certificate")
    parser.add_argument("--pfx-password", help="PFX password")
    parser.add_argument("--ca-cert", help="Path to CA/server certificate (PEM)")
    parser.add_argument("--settings", help="Path to C# settings.json file")
    parser.add_argument("--timeout", type=float, default=5.0, help="RPC timeout in seconds")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    # Logging setup
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )

    # Build config
    if args.settings:
        config = ConnectionConfig.from_json(args.settings)
        print(f"Loaded settings from {args.settings}")
    elif args.insecure:
        config = ConnectionConfig(address=args.address, insecure=True)
    elif args.pfx or args.ca_cert:
        config = ConnectionConfig(
            address=args.address,
            pfx_path=args.pfx,
            pfx_password=args.pfx_password,
            ca_cert=args.ca_cert,
            insecure=False,
        )
    else:
        # Auto-detect: probe the server for its TLS cert
        tmp = ConnectionConfig(address=args.address)
        host, _, port_str = tmp.target.partition(":")
        port = int(port_str) if port_str else 7000

        print(f"Probing {host}:{port} for TLS certificate...")
        server_pem = fetch_server_cert(host, port)

        if server_pem:
            print("  TLS detected — using server's certificate as trust anchor")
            config = ConnectionConfig(
                address=args.address,
                ca_cert=server_pem,
                insecure=False,
                options=[("grpc.ssl_target_name_override", host)],
            )
        else:
            print("  No TLS detected — falling back to insecure channel")
            config = ConnectionConfig(address=args.address, insecure=True)

    mode = "insecure" if config.insecure else "TLS"
    print(f"Target: {config.target} ({mode})")
    print()

    # Connect and call GetStatus
    try:
        with Connection(config) as conn:
            system_svc = SystemService(conn.channel, timeout=args.timeout)

            print("Calling GetStatus...")
            status = system_svc.get_status()

            # Map link_status to enum name if possible
            try:
                link_name = LinkStatus(status.link_status).name
            except ValueError:
                link_name = f"UNKNOWN({status.link_status})"

            print()
            print("╔══════════════════════════════════════╗")
            print("║   System Monitor — Connected! ✓      ║")
            print("╠══════════════════════════════════════╣")
            print(f"║  Link Status : {link_name:<22s}║")
            print(f"║  Online      : {str(status.online):<22s}║")
            print(f"║  Live Update : {str(status.live_update):<22s}║")
            print(f"║  Return Code : {status.return_code:<22d}║")
            print("╚══════════════════════════════════════╝")
            print()
            return 0

    except Exception as e:
        print()
        print(f"FAILED: {type(e).__name__}: {e}")
        print()
        if "UNAVAILABLE" in str(e) or "Connection" in type(e).__name__:
            print("Troubleshooting:")
            print("  1. Is System Monitor running?")
            print("  2. Is the gRPC API enabled (requires SM ≥8.85)?")
            print(f"  3. Is it listening on {config.target}?")
            print("  4. If TLS is required, provide --ca-cert or --settings")
            print("  5. Check hostname matches cert CN (try --address localhost:7000)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
