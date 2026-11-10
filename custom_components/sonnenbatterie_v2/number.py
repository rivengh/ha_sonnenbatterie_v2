"""Number platform: forced charge/discharge setpoints and battery reserve."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
    RestoreNumber,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_EM_USOC
from .coordinator import SonnenConfigEntry
from .entity import SonnenEntity

_DEFAULT_MAX_POWER = 5000


def _to_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True, kw_only=True)
class SonnenSetpointEntityDescription(NumberEntityDescription):
    direction: str  # "charge" | "discharge"


SETPOINTS: tuple[SonnenSetpointEntityDescription, ...] = (
    SonnenSetpointEntityDescription(
        key="force_charge",
        translation_key="force_charge",
        icon="mdi:battery-plus-outline",
        entity_category=EntityCategory.CONFIG,
        device_class=NumberDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        native_min_value=0,
        native_step=100,
        mode=NumberMode.SLIDER,
        direction="charge",
    ),
    SonnenSetpointEntityDescription(
        key="force_discharge",
        translation_key="force_discharge",
        icon="mdi:battery-minus-outline",
        entity_category=EntityCategory.CONFIG,
        device_class=NumberDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        native_min_value=0,
        native_step=100,
        mode=NumberMode.SLIDER,
        direction="discharge",
    ),
)

RESERVE: tuple[NumberEntityDescription, ...] = (
    NumberEntityDescription(
        key="battery_reserve",
        translation_key="battery_reserve",
        icon="mdi:battery-lock",
        entity_category=EntityCategory.CONFIG,
        device_class=NumberDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        mode=NumberMode.SLIDER,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SonnenConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sonnenBatterie number entities."""
    runtime = entry.runtime_data
    entities: list[Any] = []
    # Add SonnenReserveNumber entities for default coordinator (status data)
    entities.extend(
        SonnenReserveNumber(runtime.coordinator, description) for description in RESERVE
    )
    # Add SonnenSetpointNumber entities for configuration coordinator (configuration data)
    entities.extend(
        SonnenSetpointNumber(runtime.configuration_coordinator, description)
        for description in SETPOINTS
    )
    async_add_entities(entities)


class SonnenSetpointNumber(SonnenEntity, RestoreNumber):
    """Forced charge/discharge power.

    The API can't read a setpoint back, so this shows the last written value
    (kept in the configuration coordinator, shared with the reset buttons) and
    restores it after a restart.
    """

    entity_description: SonnenSetpointEntityDescription

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_number_data()
        if last is not None and last.native_value:
            direction = self.entity_description.direction
            self.coordinator.setpoints[direction] = int(last.native_value)

    @property
    def native_max_value(self) -> float:
        return self.coordinator.inverter_max_power or _DEFAULT_MAX_POWER

    @property
    def native_value(self) -> float:
        return self.coordinator.setpoints[
            self.entity_description.direction
        ]

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_setpoint(
            self.entity_description.direction, int(value)
        )


class SonnenReserveNumber(SonnenEntity, NumberEntity):
    """Battery reserve for backup power (EM_USOC), read back from /status."""

    @property
    def native_value(self) -> int | None:
        return _to_int(self.coordinator.data["status"].get("BackupBuffer"))

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_configuration(CONF_EM_USOC, int(value))
