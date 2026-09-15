"""Data update coordinators for the sonnenBatterie v2 integration."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any, NoReturn

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SonnenApiError, SonnenAuthError, SonnenV2Api
from .const import DEFAULT_NAME, DOMAIN, LOGGER


class _SonnenBaseCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Provide shared setup, device metadata, and error handling."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api: SonnenV2Api,
        scan_interval: int,
        configuration_coordinator: SonnenConfigurationCoordinator | None = None,
    ) -> None:
        """Initialize a coordinator for the configured polling interval."""
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.api = api
        self._configuration_coordinator = configuration_coordinator or self

    @property
    def device_info(self) -> DeviceInfo:
        """Return device metadata shared by all integration entities."""
        configuration_data = self._configuration_coordinator.data
        cfg = (
            configuration_data.get("configurations", {})
            if isinstance(configuration_data, dict)
            else {}
        )

        return DeviceInfo(
            identifiers={(DOMAIN, self.config_entry.entry_id)},
            manufacturer="Sonnen",
            model="sonnenBatterie",
            name=DEFAULT_NAME,
            sw_version=cfg.get("DE_Software"),
            configuration_url=f"http://{self.api.host}",
        )

    @staticmethod
    def _raise_api_error(err: Exception) -> NoReturn:
        """Convert API exceptions into Home Assistant coordinator errors."""
        if isinstance(err, SonnenAuthError):
            raise ConfigEntryAuthFailed(str(err)) from err
        if isinstance(err, SonnenApiError):
            raise UpdateFailed(str(err)) from err
        raise err


class SonnenCoordinator(_SonnenBaseCoordinator):
    """Poll frequently changing battery status data."""

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch operational status and calculate derived values."""
        try:
            status = await self.api.get_status()
        except Exception as err:
            self._raise_api_error(err)

        data: dict[str, Any] = {
            "status": status,
        }
        data["derived"] = self._derive(data)
        return data

    @staticmethod
    def _derive(data: dict[str, Any]) -> dict[str, Any]:
        """Determine the current battery operating state."""
        status = data["status"]

        if status.get("BatteryCharging"):
            state = "charging"
        elif status.get("BatteryDischarging"):
            state = "discharging"
        else:
            state = "standby"

        return {"battery_state": state}


class SonnenDiagnosticCoordinator(_SonnenBaseCoordinator):
    """Poll inverter, powermeter, and battery diagnostic data."""

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch diagnostic endpoints concurrently."""
        try:
            inverter, powermeter, battery = await asyncio.gather(
                self.api.get_inverter(),
                self.api.get_powermeter(),
                self.api.get_battery(),
            )
        except Exception as err:
            self._raise_api_error(err)

        data = {
            "inverter": inverter or {},
            "powermeter": powermeter or [],
            "battery": battery or {},
        }
        data["derived"] = self._derive(data)
        return data

    def _derive(self, data: dict[str, Any]) -> dict[str, Any]:
        """Calculate battery state of health."""
        configuration_data = self._configuration_coordinator.data
        cfg_derived = (
            configuration_data.get("derived", {})
            if isinstance(configuration_data, dict)
            else {}
        )

        fcc = data["battery"].get("fullchargecapacitywh")
        installed = cfg_derived.get("installed_capacity_wh")

        if (
            isinstance(fcc, (int, float))
            and isinstance(installed, (int, float))
            and installed > 0
        ):
            state_of_health_pct = round(fcc / installed * 100, 1)
        else:
            state_of_health_pct = None

        return {"state_of_health_pct": state_of_health_pct}


class SonnenConfigurationCoordinator(_SonnenBaseCoordinator):
    """Poll slowly changing battery configuration data."""

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch configuration data and calculate derived capacity."""
        try:
            configurations = await self.api.get_configurations()
        except Exception as err:
            self._raise_api_error(err)

        data: dict[str, Any] = {
            "configurations": configurations or {},
        }
        data["derived"] = self._derive(data)
        return data

    @property
    def inverter_max_power(self) -> int | None:
        """Return the configured maximum inverter power, if available."""
        try:
            return int(self.data["configurations"]["IC_InverterMaxPower_w"])
        except (KeyError, TypeError, ValueError):
            return None

    @staticmethod
    def _derive(data: dict[str, Any]) -> dict[str, Any]:
        """Calculate total installed battery capacity in watt-hours."""
        cfg = data["configurations"]

        try:
            modules = int(cfg["IC_BatteryModules"])
            per_module = int(cfg["CM_MarketingModuleCapacity"])
            installed_capacity_wh = modules * per_module
        except (KeyError, TypeError, ValueError):
            installed_capacity_wh = None

        return {
            "installed_capacity_wh": installed_capacity_wh,
        }
