"""Unit tests for ConnectionConfig — no live server required."""

import json
import tempfile
from pathlib import Path

import pytest

from sm_config_api import ConnectionConfig


class TestConnectionConfig:
    """Tests for ConnectionConfig construction and factory methods."""

    def test_default_values(self):
        cfg = ConnectionConfig()
        assert cfg.address == ""
        assert cfg.insecure is False
        assert cfg.use_token is False

    def test_target_from_host_port(self):
        cfg = ConnectionConfig(address="myhost:5000")
        assert cfg.target == "myhost:5000"

    def test_target_from_https_url(self):
        cfg = ConnectionConfig(address="https://myhost:7000")
        assert cfg.target == "myhost:7000"

    def test_target_from_bare_host(self):
        cfg = ConnectionConfig(address="myhost")
        assert cfg.target == "myhost:443"

    def test_target_empty_raises(self):
        cfg = ConnectionConfig(address="")
        with pytest.raises(ValueError, match="empty"):
            _ = cfg.target

    def test_from_dict_basic(self):
        data = {"address": "https://10.0.0.1:7000", "insecure": True}
        cfg = ConnectionConfig.from_dict(data)
        assert cfg.target == "10.0.0.1:7000"
        assert cfg.insecure is True

    def test_from_dict_csharp_typo(self):
        """The C# sample uses 'certifiate' (missing 'c')."""
        data = {
            "address": "https://host:7000",
            "certifiate": "path/to/cert.pfx",
            "key": "mypassword",
        }
        cfg = ConnectionConfig.from_dict(data)
        assert cfg.pfx_path == "path/to/cert.pfx"
        assert cfg.pfx_password == "mypassword"

    def test_from_dict_correct_spelling(self):
        data = {
            "address": "https://host:7000",
            "certificate": "cert.pfx",
            "key": "pass",
        }
        cfg = ConnectionConfig.from_dict(data)
        assert cfg.pfx_path == "cert.pfx"

    def test_from_dict_oauth2(self):
        data = {
            "address": "host:443",
            "use_token": True,
            "client_id": "my-id",
            "client_secret": "my-secret",
            "token_uri": "https://auth.example.com/token",
            "audience": "https://api.example.com",
        }
        cfg = ConnectionConfig.from_dict(data)
        assert cfg.use_token is True
        assert cfg.client_id == "my-id"

    def test_from_json_file(self, tmp_path):
        settings = {
            "address": "https://host:7000",
            "certifiate": "cert.pfx",
            "key": "pass123",
            "use_token": False,
        }
        json_file = tmp_path / "settings.json"
        json_file.write_text(json.dumps(settings), encoding="utf-8")

        cfg = ConnectionConfig.from_json(str(json_file))
        assert cfg.target == "host:7000"
        assert cfg.pfx_path == "cert.pfx"
        assert cfg.pfx_password == "pass123"


class TestTokenManager:
    """Tests for TokenManager state without making real HTTP requests."""

    def test_not_configured_when_use_token_false(self):
        from sm_config_api import TokenManager

        cfg = ConnectionConfig(address="host:7000", use_token=False)
        tm = TokenManager(cfg)
        assert tm.is_configured is False
        assert tm.access_token is None

    def test_is_configured_when_all_fields_set(self):
        from sm_config_api import TokenManager

        cfg = ConnectionConfig(
            address="host:7000",
            use_token=True,
            client_id="id",
            client_secret="secret",
            token_uri="https://auth/token",
            audience="aud",
        )
        tm = TokenManager(cfg)
        assert tm.is_configured is True
        assert tm.is_expired is True  # no token yet

    def test_clear_resets_token(self):
        from sm_config_api import TokenManager

        cfg = ConnectionConfig(
            address="host:7000",
            use_token=True,
            client_id="id",
            client_secret="secret",
            token_uri="https://auth/token",
        )
        tm = TokenManager(cfg)
        tm._access_token = "fake-token"
        tm._expires_at = 9999999999.0
        assert tm.is_expired is False
        tm.clear()
        assert tm.is_expired is True
