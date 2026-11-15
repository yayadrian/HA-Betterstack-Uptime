"""Tests for Better Stack Uptime integration setup and unload."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.betterstack_uptime.const import DOMAIN
from custom_components.betterstack_uptime.coordinator import BetterStackCoordinator

from .conftest import (
    MOCK_MONITORS,
    make_heartbeat,
    make_monitor,
    mock_api_page,
    mock_session,
)


async def test_setup_entry(hass: HomeAssistant, mock_config_entry) -> None:
    """Test successful setup creates coordinator and forwards platforms."""
    with mock_session([mock_api_page(MOCK_MONITORS)]):
        result = await hass.config_entries.async_setup(mock_config_entry.entry_id)

    assert result is True
    assert mock_config_entry.state is ConfigEntryState.LOADED

    coordinator = mock_config_entry.runtime_data
    assert isinstance(coordinator, BetterStackCoordinator)
    assert coordinator.config_entry is mock_config_entry
    assert len(coordinator.data) == 3


async def test_unload_entry(hass: HomeAssistant, mock_config_entry) -> None:
    """Test unload removes coordinator data and unloads platforms."""
    with mock_session([mock_api_page(MOCK_MONITORS)]):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    result = await hass.config_entries.async_unload(mock_config_entry.entry_id)
    assert result is True
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


async def test_setup_entry_failure(hass: HomeAssistant, mock_config_entry) -> None:
    """Test setup fails when coordinator first_refresh raises."""
    with patch.object(
        BetterStackCoordinator,
        "_async_update_data",
        side_effect=UpdateFailed("Network error"),
    ):
        result = await hass.config_entries.async_setup(mock_config_entry.entry_id)

    assert result is False
    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_setup_entry_auth_failed_starts_reauth(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """Test a rejected token fails setup and starts a reauth flow."""
    with patch.object(
        BetterStackCoordinator,
        "_async_update_data",
        side_effect=ConfigEntryAuthFailed("Invalid token"),
    ):
        result = await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert result is False
    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR

    flows = hass.config_entries.flow.async_progress()
    assert len(flows) == 1
    assert flows[0]["context"]["source"] == SOURCE_REAUTH
    assert flows[0]["context"]["entry_id"] == mock_config_entry.entry_id


async def test_removed_monitors_are_cleaned_up(hass: HomeAssistant, mock_config_entry) -> None:
    """Test entities are removed when monitors disappear from Better Stack."""
    with mock_session([mock_api_page([make_monitor("1", "First")])]):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    entity_registry = er.async_get(hass)

    binary_entity_id = entity_registry.async_get_entity_id(
        "binary_sensor", DOMAIN, "1-up"
    )
    sensor_entity_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, "1-status"
    )

    assert binary_entity_id is not None
    assert sensor_entity_id is not None
    assert hass.states.get(binary_entity_id) is not None
    assert hass.states.get(sensor_entity_id) is not None

    coordinator.async_set_updated_data({})
    await hass.async_block_till_done()

    assert entity_registry.async_get(binary_entity_id) is None
    assert entity_registry.async_get(sensor_entity_id) is None
    assert hass.states.get(binary_entity_id) is None
    assert hass.states.get(sensor_entity_id) is None


async def _setup_monitor_and_heartbeat(hass: HomeAssistant, entry) -> None:
    """Set up an entry whose monitor and heartbeat share Better Stack ID 1."""
    with mock_session(
        [mock_api_page([make_monitor("1", "Website")])],
        [mock_api_page([make_heartbeat("1", "Backups")])],
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()


async def test_monitor_and_heartbeat_with_same_id_coexist(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """Test a monitor and heartbeat sharing an ID get separate devices and entities."""
    await _setup_monitor_and_heartbeat(hass, mock_config_entry)

    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)

    for domain, suffix in (("binary_sensor", "up"), ("sensor", "status")):
        assert entity_registry.async_get_entity_id(domain, DOMAIN, f"1-{suffix}")
        assert entity_registry.async_get_entity_id(
            domain, DOMAIN, f"heartbeat-1-{suffix}"
        )

    monitor_device = device_registry.async_get_device_by_identifier(
        (DOMAIN, "1"), mock_config_entry.entry_id
    )
    heartbeat_device = device_registry.async_get_device_by_identifier(
        (DOMAIN, "heartbeat-1"), mock_config_entry.entry_id
    )
    assert monitor_device.name == "Website"
    assert heartbeat_device.name == "Backups"
    assert heartbeat_device.model == "Heartbeat"


async def test_heartbeat_entities_survive_reload(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """Test stale-entity cleanup on setup keeps heartbeats that still exist."""
    await _setup_monitor_and_heartbeat(hass, mock_config_entry)
    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await _setup_monitor_and_heartbeat(hass, mock_config_entry)

    entity_registry = er.async_get(hass)
    assert entity_registry.async_get_entity_id("binary_sensor", DOMAIN, "heartbeat-1-up")
    assert entity_registry.async_get_entity_id("sensor", DOMAIN, "heartbeat-1-status")


async def test_removed_heartbeat_is_cleaned_up(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """Test a removed heartbeat's entities go, while the same-ID monitor stays."""
    await _setup_monitor_and_heartbeat(hass, mock_config_entry)

    coordinator = mock_config_entry.runtime_data
    coordinator.async_set_updated_data(
        {k: v for k, v in coordinator.data.items() if k != "heartbeat-1"}
    )
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    assert entity_registry.async_get_entity_id("binary_sensor", DOMAIN, "heartbeat-1-up") is None
    assert entity_registry.async_get_entity_id("sensor", DOMAIN, "heartbeat-1-status") is None
    assert entity_registry.async_get_entity_id("binary_sensor", DOMAIN, "1-up")
    assert entity_registry.async_get_entity_id("sensor", DOMAIN, "1-status")


async def test_heartbeats_kept_unavailable_when_access_lost(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """Test losing heartbeat access keeps heartbeat entities, unavailable, until it returns."""
    await _setup_monitor_and_heartbeat(hass, mock_config_entry)
    coordinator = mock_config_entry.runtime_data
    entity_registry = er.async_get(hass)
    heartbeat_entity_id = entity_registry.async_get_entity_id(
        "binary_sensor", DOMAIN, "heartbeat-1-up"
    )

    with mock_session([mock_api_page([make_monitor("1", "Website")])], [403]):
        await coordinator.async_refresh()
        await hass.async_block_till_done()

    assert entity_registry.async_get(heartbeat_entity_id) is not None
    assert hass.states.get(heartbeat_entity_id).state == STATE_UNAVAILABLE
    assert hass.states.get("binary_sensor.website_up").state == "on"

    with mock_session(
        [mock_api_page([make_monitor("1", "Website")])],
        [mock_api_page([make_heartbeat("1", "Backups", "down")])],
    ):
        await coordinator.async_refresh()
        await hass.async_block_till_done()

    assert hass.states.get(heartbeat_entity_id).state == "off"
    # Access returning reuses the kept entities rather than adding duplicates
    heartbeat_entries = [
        e
        for e in er.async_entries_for_config_entry(entity_registry, mock_config_entry.entry_id)
        if e.unique_id.startswith("heartbeat-1-")
    ]
    assert len(heartbeat_entries) == 2


async def test_heartbeats_kept_on_reload_without_access(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """Test setup without heartbeat access does not purge heartbeat registry entries."""
    await _setup_monitor_and_heartbeat(hass, mock_config_entry)
    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)

    with mock_session([mock_api_page([make_monitor("1", "Website")])], [403]):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    assert entity_registry.async_get_entity_id("binary_sensor", DOMAIN, "heartbeat-1-up")
    assert entity_registry.async_get_entity_id("sensor", DOMAIN, "heartbeat-1-status")


async def test_heartbeat_deleted_while_access_lost_is_cleaned_up(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """Test a heartbeat kept over a reload without access is removed once access shows it is gone."""
    await _setup_monitor_and_heartbeat(hass, mock_config_entry)
    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)

    with mock_session([mock_api_page([make_monitor("1", "Website")])], [403]):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    assert entity_registry.async_get_entity_id("binary_sensor", DOMAIN, "heartbeat-1-up")

    # Access returns, but the heartbeat was deleted in Better Stack meanwhile
    with mock_session(
        [mock_api_page([make_monitor("1", "Website")])], [mock_api_page([])]
    ):
        await mock_config_entry.runtime_data.async_refresh()
        await hass.async_block_till_done()

    assert entity_registry.async_get_entity_id("binary_sensor", DOMAIN, "heartbeat-1-up") is None
    assert entity_registry.async_get_entity_id("sensor", DOMAIN, "heartbeat-1-status") is None
    assert entity_registry.async_get_entity_id("binary_sensor", DOMAIN, "1-up")
