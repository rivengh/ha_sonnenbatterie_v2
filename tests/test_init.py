"""Tests for setup, polling and the entities' data."""

from __future__ import annotations

from aiohttp import ClientError
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.sonnenbatterie_v2.diagnostics import (
    async_get_config_entry_diagnostics,
)

from . import mock_battery

_METER_FIELDS = [
    "w_total", "w_l1", "w_l2", "w_l3", "a_l1", "a_l2", "a_l3",
    "v_l1_n", "v_l2_n", "v_l3_n", "kwh_imported", "kwh_exported",
]  # fmt: skip
_METER_KEYS = {
    f"{meter}_{field}"
    for meter in ("meter_production_0_1", "meter_consumption_1_2")
    for field in _METER_FIELDS
}
# Entity keys (unique id = "<entry_id>_<key>") of an existing installation.
# Changing any of them would orphan entities and break dashboards on update.
EXISTING_KEYS = {
    "backup_buffer",
    "battery_balance_charge_request",
    "battery_care",
    "battery_cell_temperature_max",
    "battery_cell_temperature_min",
    "battery_cell_voltage_max",
    "battery_cell_voltage_min",
    "battery_charge",
    "battery_cycles",
    "battery_discharge",
    "battery_full_charge_capacity",
    "battery_power",
    "battery_reserve",
    "battery_state",
    "battery_state_of_health",
    "battery_system_alarm",
    "battery_system_dc_current",
    "battery_system_dc_voltage",
    "battery_system_warning",
    "consumption",
    "consumption_avg",
    "force_charge",
    "force_discharge",
    "frequency_ac",
    "grid_export",
    "grid_import",
    "grid_power",
    "grid_status",
    "inverter_pv_current",
    "inverter_pv_power",
    "inverter_pv_voltage",
    "inverter_temperature",
    "operating_mode",
    "operating_mode_select",
    "production",
    "remaining_capacity",
    "reset_all",
    "reset_charge",
    "reset_discharge",
    "soc_relative",
    "soc_user",
    "system_installed_capacity",
    "system_inverter_max_power",
    "system_module_count",
    "system_software_version",
    "voltage_ac",
    "voltage_battery",
} | _METER_KEYS  # fmt: skip


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def _entity_keys(hass: HomeAssistant, entry: MockConfigEntry) -> set[str]:
    return {
        e.unique_id.removeprefix(f"{entry.entry_id}_")
        for e in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    }


def _state(hass: HomeAssistant, entity_id: str) -> str:
    return hass.states.get(entity_id).state


async def test_setup_and_unload(
    hass: HomeAssistant, battery: AiohttpClientMocker, config_entry: MockConfigEntry
) -> None:
    await _setup(hass, config_entry)
    assert config_entry.state is ConfigEntryState.LOADED
    assert _entity_keys(hass, config_entry) == EXISTING_KEYS

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.NOT_LOADED


async def test_values(
    hass: HomeAssistant, battery: AiohttpClientMocker, config_entry: MockConfigEntry
) -> None:
    await _setup(hass, config_entry)

    # entity ids are derived from english translations of the keys
    assert _state(hass, "sensor.sonnenbatterie_consumption") == "336"
    assert _state(hass, "sensor.sonnenbatterie_production") == "645"
    assert _state(hass, "sensor.sonnenbatterie_ac_power") == "-271"
    assert _state(hass, "sensor.sonnenbatterie_remaining_capacity_relative") == "1289"
    assert _state(hass, "sensor.sonnenbatterie_state") == "charging"
    assert _state(hass, "sensor.sonnenbatterie_operating_mode") == "self_consumption"
    assert _state(hass, "binary_sensor.sonnenbatterie_battery_care") == "off"
    # 5734.605 Wh measured / (3 modules * 2000 Wh)
    assert _state(hass, "sensor.sonnenbatterie_battery_state_of_health") == "95.6"
    assert _state(hass, "binary_sensor.sonnenbatterie_battery_system_alarm") == "off"
    assert _state(hass, "select.sonnenbatterie_operating_mode") == "self_consumption"
    assert _state(hass, "number.sonnenbatterie_backup_buffer") == "0"
    manual_charge = hass.states.get("number.sonnenbatterie_manual_charge")
    assert float(manual_charge.state) == 0
    assert manual_charge.attributes["max"] == 3000  # IC_InverterMaxPower_w


async def test_status_unreachable_retries_setup(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
) -> None:
    mock_battery(aioclient_mock, status={"exc": ClientError()})
    await _setup(hass, config_entry)
    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_rejected_token_starts_reauth(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
) -> None:
    mock_battery(aioclient_mock, battery={"status": 401})
    await _setup(hass, config_entry)
    assert config_entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress()
    assert [flow["context"]["source"] for flow in flows] == [SOURCE_REAUTH]


async def test_diagnostics_redact_token(
    hass: HomeAssistant, battery: AiohttpClientMocker, config_entry: MockConfigEntry
) -> None:
    await _setup(hass, config_entry)
    diagnostics = await async_get_config_entry_diagnostics(hass, config_entry)
    assert diagnostics["config"]["token"] == "**REDACTED**"
    assert diagnostics["coordinators"]["status_data"]["status"]["Consumption_W"] == 336
