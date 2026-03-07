"""Tests for Better Stack Uptime integration setup and unload."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.betterstack_uptime.const import DOMAIN
from custom_components.betterstack_uptime.coordinator import BetterStackCoordinator

from .conftest import TEST_API_TOKEN, make_monitor, mock_api_page, MOCK_MONITORS


def _mock_coordinator_session(page: dict) -> patch:
    """Return a patch for async_get_clientsession yielding a single-page response."""
    resp = AsyncMock()
    resp.status = 200
    resp.raise_for_status = MagicMock()
    resp.json = AsyncMock(return_value=page)

    session = MagicMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    ctx.__aexit__ = AsyncMock(return_value=False)
    session.get = MagicMock(return_value=ctx)

    return patch(
        "custom_components.betterstack_uptime.coordinator.async_get_clientsession",
        return_value=session,
    )


async def test_setup_entry(hass: HomeAssistant, mock_config_entry) -> None:
    """Test successful setup creates coordinator and forwards platforms."""
    with _mock_coordinator_session(mock_api_page(MOCK_MONITORS)):
        result = await hass.config_entries.async_setup(mock_config_entry.entry_id)

    assert result is True
    assert DOMAIN in hass.data
    assert mock_config_entry.entry_id in hass.data[DOMAIN]

    coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]
    assert len(coordinator.data) == 3


async def test_unload_entry(hass: HomeAssistant, mock_config_entry) -> None:
    """Test unload removes coordinator data and unloads platforms."""
    with _mock_coordinator_session(mock_api_page(MOCK_MONITORS)):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    result = await hass.config_entries.async_unload(mock_config_entry.entry_id)
    assert result is True
    assert mock_config_entry.entry_id not in hass.data[DOMAIN]


async def test_setup_entry_failure(hass: HomeAssistant, mock_config_entry) -> None:
    """Test setup fails when coordinator first_refresh raises."""
    with patch.object(
        BetterStackCoordinator,
        "_async_update_data",
        side_effect=UpdateFailed("Network error"),
    ):
        result = await hass.config_entries.async_setup(mock_config_entry.entry_id)

    assert result is False
    assert mock_config_entry.entry_id not in hass.data.get(DOMAIN, {})


async def test_removed_monitors_are_cleaned_up(hass: HomeAssistant, mock_config_entry) -> None:
    """Test entities are removed when monitors disappear from Better Stack."""
    with _mock_coordinator_session(mock_api_page([make_monitor("1", "First")])):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]
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
