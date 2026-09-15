"""The sonnenBatterie (v2 API) integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_SCAN_INTERVAL,
    CONF_TOKEN,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SonnenV2Api
from .const import (
    CONF_DIAGNOSTIC_SCAN_INTERVAL,
    CONF_CONFIGURATION_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_DIAGNOSTIC_SCAN_INTERVAL,
    DEFAULT_CONFIGURATION_SCAN_INTERVAL,
    PLATFORMS,
)
from .coordinator import (
    SonnenCoordinator,
    SonnenDiagnosticCoordinator,
    SonnenConfigurationCoordinator,
)

from dataclasses import dataclass


@dataclass
class SonnenRuntimeData:
    """Runtime coordinators for the integration."""

    coordinator: SonnenCoordinator
    diagnostic_coordinator: SonnenDiagnosticCoordinator
    configuration_coordinator: SonnenConfigurationCoordinator


type SonnenConfigEntry = ConfigEntry[SonnenRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: SonnenConfigEntry) -> bool:
    """Set up sonnenBatterie from a config entry."""
    api = SonnenV2Api(
        entry.data[CONF_HOST],
        entry.data.get(CONF_TOKEN),
        async_get_clientsession(hass),
    )

    configuration_coordinator = SonnenConfigurationCoordinator(
        hass,
        entry,
        api,
        entry.data.get(
            CONF_CONFIGURATION_SCAN_INTERVAL, DEFAULT_CONFIGURATION_SCAN_INTERVAL
        ),
    )

    await configuration_coordinator.async_config_entry_first_refresh()

    coordinator = SonnenCoordinator(
        hass,
        entry,
        api,
        entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        configuration_coordinator=configuration_coordinator,
    )

    diagnostic_coordinator = SonnenDiagnosticCoordinator(
        hass,
        entry,
        api,
        entry.data.get(CONF_DIAGNOSTIC_SCAN_INTERVAL, DEFAULT_DIAGNOSTIC_SCAN_INTERVAL),
        configuration_coordinator=configuration_coordinator,
    )

    await coordinator.async_config_entry_first_refresh()
    await diagnostic_coordinator.async_config_entry_first_refresh()

    entry.runtime_data = SonnenRuntimeData(
        coordinator=coordinator,
        diagnostic_coordinator=diagnostic_coordinator,
        configuration_coordinator=configuration_coordinator,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def _async_reload(hass: HomeAssistant, entry: SonnenConfigEntry) -> None:
    """Reload the entry when its options/data change (e.g. after reconfigure)."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: SonnenConfigEntry) -> bool:
    """Unload a config entry, including all forwarded platforms."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
