"""Constants for the sonnenBatterie (v2 API) integration."""

from __future__ import annotations

import logging
from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "sonnenbatterie_v2"
LOGGER = logging.getLogger(__package__)

CONF_DIAGNOSTIC_SCAN_INTERVAL = "diagnostic_scan_interval"
CONF_CONFIGURATION_SCAN_INTERVAL = "configuration_scan_interval"
CONF_EXPOSE_POWERMETER_SENSORS = "expose_powermeter_sensors"

DEFAULT_NAME: Final = "sonnenBatterie"
DEFAULT_SCAN_INTERVAL: Final = 30  # 30s
DEFAULT_DIAGNOSTIC_SCAN_INTERVAL: Final = 300  # 5m
DEFAULT_CONFIGURATION_SCAN_INTERVAL: Final = 3600  # 1h
MIN_SCAN_INTERVAL: Final = 5

# Maximum number of API retries before raising an error.
# Note: This is used in the coordinator to retry API calls with exponential backoff.
MAX_API_RETRIES: Final = 3

PLATFORMS: Final = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.SELECT,
    Platform.NUMBER,
    Platform.BUTTON,
]

# --- Operating modes (EM_OperatingMode) -------------------------------------
# API value (a string, the way /status returns it) -> option name in HA.
# Names match the modes offered in the sonnenBatterie dashboard.
OPERATING_MODES: Final[dict[str, str]] = {
    "1": "manual",
    "2": "self_consumption",
    "4": "testing",
    "6": "module_extension",
    "10": "time_of_use",
    "11": "automatic_optimization",
}
# Modes that can be set from HA. "testing" and "module_extension" are
# installer/service modes: they are shown by the sensor but never set.
SELECTABLE_MODES: Final = (
    "self_consumption",
    "automatic_optimization",
    "time_of_use",
    "manual",
)

# Configuration keys writable via PUT /api/v2/configurations
CONF_EM_OPERATING_MODE: Final = "EM_OperatingMode"
CONF_EM_USOC: Final = "EM_USOC"
