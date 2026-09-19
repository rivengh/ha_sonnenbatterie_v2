"""Binary sensor platform: battery alarm and warning flags (from /battery)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SonnenConfigEntry
from .entity import SonnenEntity


@dataclass(frozen=True, kw_only=True)
class SonnenBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Binary sensor description with a value extractor against the coordinator data."""

    value_fn: Callable[[dict[str, Any]], bool | None]


def _battery_flag(data: dict[str, Any], key: str) -> bool | None:
    """Map a numeric battery flag to bool, or None if the /battery read is missing."""
    value = data["battery"].get(key)
    return bool(value) if value is not None else None


def _status_flag(data: dict[str, Any], key: str) -> bool | None:
    """Map a status flag to bool."""
    value = data["status"].get(key)
    return bool(value) if value is not None else None


# Names are provided via translations (entity.binary_sensor.<key>.name).
STATUS_BINARY_SENSORS: tuple[SonnenBinarySensorEntityDescription, ...] = (
    SonnenBinarySensorEntityDescription(
        key="battery_care",
        translation_key="battery_care",
        icon="mdi:wrench-clock",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda d: _status_flag(d, "dischargeNotAllowed"),
    ),
)

DIAGNOSTIC_BINARY_SENSORS: tuple[SonnenBinarySensorEntityDescription, ...] = (
    SonnenBinarySensorEntityDescription(
        key="balance_charge_request",
        translation_key="balance_charge_request",
        icon="mdi:battery-arrow-up",
        device_class=BinarySensorDeviceClass.RUNNING,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: _battery_flag(d, "balancechargerequest"),
    ),
    SonnenBinarySensorEntityDescription(
        key="system_alarm",
        translation_key="system_alarm",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: _battery_flag(d, "systemalarm"),
    ),
    SonnenBinarySensorEntityDescription(
        key="system_warning",
        translation_key="system_warning",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: _battery_flag(d, "systemwarning"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SonnenConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sonnenBatterie binary sensors."""
    runtime = entry.runtime_data

    entities: list[SonnenBinarySensor] = [
        SonnenBinarySensor(runtime.coordinator, description)
        for description in STATUS_BINARY_SENSORS
    ]

    entities.extend(
        SonnenBinarySensor(runtime.diagnostic_coordinator, description)
        for description in DIAGNOSTIC_BINARY_SENSORS
    )

    async_add_entities(entities)


class SonnenBinarySensor(SonnenEntity, BinarySensorEntity):
    """A sonnenBatterie binary sensor (battery alarm / warning)."""

    entity_description: SonnenBinarySensorEntityDescription

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.value_fn(self.coordinator.data)
