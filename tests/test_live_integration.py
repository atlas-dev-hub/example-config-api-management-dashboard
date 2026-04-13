"""Integration tests against a live System Monitor instance.

Run with:
    SM_LIVE_TEST=1 python -m pytest tests/test_live_integration.py -v

Optionally set SM_ADDRESS (default: localhost:7000).
"""

import pytest

from tests.conftest import requires_live_sm


@requires_live_sm
class TestSystemServiceLive:
    """Live tests for SystemService."""

    def test_get_status(self, live_client):
        status = live_client.system.get_status()
        assert hasattr(status, "link_status")
        assert hasattr(status, "online")
        assert hasattr(status, "live_update")

    def test_get_unit_list(self, live_client):
        units = live_client.system.get_unit_list()
        assert isinstance(units, list)
        assert len(units) > 0

    def test_get_licence_details(self, live_client):
        lic = live_client.system.get_licence_details()
        assert hasattr(lic, "consortium")
        assert hasattr(lic, "owner")

    def test_get_log_folder(self, live_client):
        folder = live_client.system.get_log_folder()
        assert isinstance(folder, str)
        assert len(folder) > 0


@requires_live_sm
class TestProjectServiceLive:
    """Live tests for ProjectService."""

    def test_get_version_number(self, live_client):
        ver = live_client.project.get_version_number()
        assert ver.major_version > 0

    def test_get_app_details(self, live_client):
        apps = live_client.project.get_app_details()
        assert isinstance(apps, list)
        assert len(apps) > 0
        assert hasattr(apps[0], "app_id")
        assert hasattr(apps[0], "app_name")

    def test_get_active_apps(self, live_client):
        active = live_client.project.get_active_apps()
        assert isinstance(active, list)
        assert len(active) > 0

    def test_get_errors(self, live_client):
        errors = live_client.project.get_errors()
        assert isinstance(errors, list)


@requires_live_sm
class TestParameterServiceLive:
    """Live tests for ParameterService."""

    def test_get_parameters(self, live_client):
        apps = live_client.project.get_app_details()
        assert len(apps) > 0
        app_id = apps[0].app_id

        params = live_client.parameter.get_parameters(app_id, data_type=0)
        assert isinstance(params, list)
        assert len(params) > 0
        assert hasattr(params[0], "id")
        assert hasattr(params[0], "name")

    def test_get_conversions(self, live_client):
        apps = live_client.project.get_app_details()
        app_id = apps[0].app_id

        convs = live_client.parameter.get_conversions(app_id)
        assert isinstance(convs, list)
        assert len(convs) > 0

    def test_get_parameter_properties(self, live_client):
        apps = live_client.project.get_app_details()
        app_id = apps[0].app_id

        props = live_client.parameter.get_parameter_properties(app_id, data_type=0)
        assert isinstance(props, list)
        assert len(props) > 0
        p = props[0]
        assert hasattr(p, "Id")
        assert hasattr(p, "name")
        assert hasattr(p, "units")


@requires_live_sm
class TestLoggingServiceLive:
    """Live tests for LoggingService."""

    def test_get_logging_channel_properties(self, live_client):
        channels = live_client.logging.get_logging_channel_properties()
        assert isinstance(channels, list)
        assert len(channels) > 0
        assert hasattr(channels[0], "index")
        assert hasattr(channels[0], "name")

    def test_get_logging_wrap(self, live_client):
        wrap = live_client.logging.get_logging_wrap()
        assert isinstance(wrap, bool)

    def test_get_logging_slots_used(self, live_client):
        slots = live_client.logging.get_logging_slots_used()
        assert isinstance(slots, int)
        assert slots >= 0

    def test_get_logging_triggers(self, live_client):
        triggers = live_client.logging.get_logging_triggers()
        assert isinstance(triggers, list)


@requires_live_sm
class TestMultiClient:
    """Test multiple client connections to the same SM instance."""

    def test_two_clients_simultaneously(self, live_config):
        from sm_config_api import SystemMonitorClient

        with SystemMonitorClient(live_config, timeout=10.0) as c1:
            with SystemMonitorClient(live_config, timeout=10.0) as c2:
                s1 = c1.system.get_status()
                s2 = c2.system.get_status()
                assert s1.link_status == s2.link_status
                assert s1.online == s2.online
