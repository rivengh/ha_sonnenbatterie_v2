"""Diagnostics: the raw API data, for attaching to bug reports."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_TOKEN
from homeassistant.core import HomeAssistant

from .coordinator import SonnenConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: SonnenConfigEntry
) -> dict[str, Any]:
    """Return the entry config (token redacted) and the last polled data."""
    runtime = entry.runtime_data
    return {
        "config": async_redact_data(dict(entry.data), {CONF_TOKEN}),
        "coordinators": {
            "status_data": runtime.coordinator.data,
            "diagnostic_data": runtime.diagnostic_coordinator.data,
            "configuration_data": runtime.configuration_coordinator.data,
            "configuration_setpoints": runtime.configuration_coordinator.setpoints,
        },
    }
