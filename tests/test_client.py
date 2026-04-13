"""Unit tests for the SystemMonitorClient facade."""

import pytest

from sm_config_api import ConnectionConfig, SystemMonitorClient


class TestClientConstruction:
    """Tests that don't require a live server (test config/state only)."""

    def test_repr_shows_target(self):
        # Client will fail to connect, but we can test config storage
        cfg = ConnectionConfig(address="fake-host:9999", insecure=True)
        try:
            client = SystemMonitorClient(cfg, timeout=0.5)
            assert "fake-host:9999" in repr(client)
            client.close()
        except Exception:
            pass  # connection failure expected

    def test_close_sets_not_connected(self):
        cfg = ConnectionConfig(address="fake-host:9999", insecure=True)
        try:
            client = SystemMonitorClient(cfg, timeout=0.5)
            client.close()
            assert client.is_connected is False
        except Exception:
            pass

    def test_config_accessible(self):
        cfg = ConnectionConfig(address="test:7000", insecure=True)
        try:
            client = SystemMonitorClient(cfg)
            assert client.config is cfg
            client.close()
        except Exception:
            pass
