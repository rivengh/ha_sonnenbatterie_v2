from unittest.mock import Mock

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sonnenbatterie_v2 import coordinator as coordinator_module
from custom_components.sonnenbatterie_v2.api import SonnenAuthError, SonnenV2Api
from custom_components.sonnenbatterie_v2.const import (
    AUTH_ERROR_GRACE_PERIOD,
    CONF_EXPOSE_POWERMETER_SENSORS,
    DOMAIN,
)
from custom_components.sonnenbatterie_v2.coordinator import (
    SonnenCoordinator,
    SonnenDiagnosticCoordinator,
)


@pytest.fixture
def entry(hass):
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_EXPOSE_POWERMETER_SENSORS: True},
    )
    config_entry.add_to_hass(hass)
    return config_entry


def test_auth_error_within_grace_period_is_update_failed(hass, entry, monkeypatch):
    monkeypatch.setattr(coordinator_module.time, "monotonic", lambda: 100)
    coordinator = SonnenCoordinator(hass, entry, Mock(spec=SonnenV2Api), 30)
    coordinator._auth_error_since = 99

    with pytest.raises(UpdateFailed):
        coordinator._raise_api_error(SonnenAuthError("unauthorized"))


def test_auth_error_after_grace_period_requires_reauth(hass, entry, monkeypatch):
    now = 100 + AUTH_ERROR_GRACE_PERIOD + 1
    monkeypatch.setattr(coordinator_module.time, "monotonic", lambda: now)
    coordinator = SonnenCoordinator(hass, entry, Mock(spec=SonnenV2Api), 30)
    coordinator._auth_error_since = 100

    with pytest.raises(ConfigEntryAuthFailed):
        coordinator._raise_api_error(SonnenAuthError("unauthorized"))


async def test_partial_diagnostic_success_does_not_reset_auth_grace_period(
    hass, entry, monkeypatch
):
    now = 100 + AUTH_ERROR_GRACE_PERIOD + 1
    monkeypatch.setattr(coordinator_module.time, "monotonic", lambda: now)
    monkeypatch.setattr(coordinator_module, "MAX_API_RETRIES", 0)

    api = Mock(spec=SonnenV2Api)
    api.get_inverter.return_value = {}
    api.get_battery.side_effect = SonnenAuthError("unauthorized")
    api.get_powermeter.return_value = []

    coordinator = SonnenDiagnosticCoordinator(hass, entry, api, 30)
    coordinator._auth_error_since = 100

    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()
