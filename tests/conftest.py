"""Shared pytest fixtures for sm_config_api tests."""

from __future__ import annotations

import os
import ssl
import socket

import pytest

# Whether a live SM instance is available for integration tests
LIVE_SM = os.environ.get("SM_LIVE_TEST", "").lower() in ("1", "true", "yes")
SM_ADDRESS = os.environ.get("SM_ADDRESS", "localhost:7000")

requires_live_sm = pytest.mark.skipif(
    not LIVE_SM,
    reason="Set SM_LIVE_TEST=1 and SM_ADDRESS to run live integration tests",
)


def fetch_server_cert(host: str = "localhost", port: int = 7000) -> bytes:
    """Probe a TLS server and return the certificate as PEM bytes."""
    from cryptography import x509
    from cryptography.hazmat.primitives.serialization import Encoding

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with socket.create_connection((host, port), timeout=5) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as ssock:
            der = ssock.getpeercert(binary_form=True)
    return x509.load_der_x509_certificate(der).public_bytes(Encoding.PEM)


@pytest.fixture(scope="session")
def live_config():
    """ConnectionConfig for a live SM instance (only when SM_LIVE_TEST=1)."""
    from sm_config_api import ConnectionConfig

    host_port = SM_ADDRESS
    host = host_port.split(":")[0] if ":" in host_port else host_port
    port = int(host_port.split(":")[1]) if ":" in host_port else 7000

    try:
        ca_pem = fetch_server_cert(host, port)
    except Exception:
        ca_pem = None

    if ca_pem:
        return ConnectionConfig(
            address=host_port,
            ca_cert=ca_pem,
            insecure=False,
            options=[("grpc.ssl_target_name_override", host)],
        )
    else:
        return ConnectionConfig(address=host_port, insecure=True)


@pytest.fixture(scope="session")
def live_client(live_config):
    """A connected SystemMonitorClient for live tests."""
    from sm_config_api import SystemMonitorClient

    client = SystemMonitorClient(live_config, timeout=10.0)
    yield client
    client.close()
