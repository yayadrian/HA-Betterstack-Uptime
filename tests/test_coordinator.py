"""Tests for Better Stack Uptime coordinator."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import logging

import aiohttp
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.betterstack_uptime.coordinator import BetterStackCoordinator

from .conftest import (
    MOCK_HEARTBEATS,
    MOCK_MONITORS,
    make_config_entry,
    make_heartbeat,
    make_monitor,
    mock_api_page,
    mock_session,
)


async def test_single_page_fetch(hass: HomeAssistant) -> None:
    """Test fetching monitors from a single page response."""
    page = mock_api_page(MOCK_MONITORS)

    coordinator = BetterStackCoordinator(hass, make_config_entry())

    with mock_session([page]):
        data = await coordinator._async_update_data()

    assert len(data) == 3
    assert "1001" in data
    assert "1002" in data
    assert "1003" in data
    assert data["1001"]["status"] == "up"
    assert data["1002"]["status"] == "down"
    assert data["1003"]["status"] == "validating"


async def test_paginated_fetch(hass: HomeAssistant) -> None:
    """Test fetching monitors across multiple pages."""
    page1 = mock_api_page(
        [make_monitor("1", "First")],
        next_url="https://uptime.betterstack.com/api/v2/monitors?page=2",
    )
    page2 = mock_api_page([make_monitor("2", "Second")])

    coordinator = BetterStackCoordinator(hass, make_config_entry())

    with mock_session([page1, page2]):
        data = await coordinator._async_update_data()

    assert len(data) == 2
    assert data["1"]["pronounceable_name"] == "First"
    assert data["2"]["pronounceable_name"] == "Second"


async def test_empty_response(hass: HomeAssistant) -> None:
    """Test empty API response returns empty dict."""
    page = mock_api_page([])

    coordinator = BetterStackCoordinator(hass, make_config_entry())

    with mock_session([page]):
        data = await coordinator._async_update_data()

    assert data == {}


async def test_api_client_response_error(hass: HomeAssistant) -> None:
    """Test ClientResponseError raises UpdateFailed."""
    resp = AsyncMock()
    resp.raise_for_status = MagicMock(
        side_effect=aiohttp.ClientResponseError(
            request_info=MagicMock(), history=(), status=500
        )
    )

    session = MagicMock()

    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    ctx.__aexit__ = AsyncMock(return_value=False)
    session.get = MagicMock(return_value=ctx)

    coordinator = BetterStackCoordinator(hass, make_config_entry())

    with (
        patch(
            "custom_components.betterstack_uptime.coordinator.async_get_clientsession",
            return_value=session,
        ),
        pytest.raises(UpdateFailed, match="API request failed: 500"),
    ):
        await coordinator._async_update_data()


@pytest.mark.parametrize("status", [401, 403])
async def test_api_auth_error(hass: HomeAssistant, status: int) -> None:
    """Test a rejected token raises ConfigEntryAuthFailed to trigger reauth."""
    resp = AsyncMock()
    resp.raise_for_status = MagicMock(
        side_effect=aiohttp.ClientResponseError(
            request_info=MagicMock(), history=(), status=status
        )
    )

    session = MagicMock()

    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    ctx.__aexit__ = AsyncMock(return_value=False)
    session.get = MagicMock(return_value=ctx)

    coordinator = BetterStackCoordinator(hass, make_config_entry())

    with (
        patch(
            "custom_components.betterstack_uptime.coordinator.async_get_clientsession",
            return_value=session,
        ),
        pytest.raises(ConfigEntryAuthFailed),
    ):
        await coordinator._async_update_data()


async def test_api_client_error(hass: HomeAssistant) -> None:
    """Test ClientError raises UpdateFailed."""
    session = MagicMock()
    session.get = MagicMock(side_effect=aiohttp.ClientError("Connection refused"))

    coordinator = BetterStackCoordinator(hass, make_config_entry())

    with (
        patch(
            "custom_components.betterstack_uptime.coordinator.async_get_clientsession",
            return_value=session,
        ),
        pytest.raises(UpdateFailed, match="Cannot reach Better Stack"),
    ):
        await coordinator._async_update_data()


async def test_data_extraction_fields(hass: HomeAssistant) -> None:
    """Test all monitor fields are correctly extracted from API response."""
    monitor = make_monitor(
        "42",
        name="Production",
        status="down",
        monitor_type="keyword",
        url="https://prod.example.com",
        last_checked_at="2025-06-15T12:00:00Z",
    )
    page = mock_api_page([monitor])

    coordinator = BetterStackCoordinator(hass, make_config_entry())

    with mock_session([page]):
        data = await coordinator._async_update_data()

    m = data["42"]
    assert m["kind"] == "monitor"
    assert m["id"] == "42"
    assert m["pronounceable_name"] == "Production"
    assert m["status"] == "down"
    assert m["monitor_type"] == "keyword"
    assert m["url"] == "https://prod.example.com"
    assert m["last_checked_at"] == "2025-06-15T12:00:00Z"


async def test_data_extraction_defaults_for_missing_fields(hass: HomeAssistant) -> None:
    """Test defaults are applied when attributes are missing."""
    monitor = {"id": "99", "attributes": {}}
    page = mock_api_page([monitor])

    coordinator = BetterStackCoordinator(hass, make_config_entry())

    with mock_session([page]):
        data = await coordinator._async_update_data()

    m = data["99"]
    assert m["id"] == "99"
    assert m["pronounceable_name"] == "Monitor 99"
    assert m["status"] is None
    assert m["monitor_type"] is None
    assert m["url"] is None
    assert m["last_checked_at"] is None


async def test_monitor_ids_are_normalized_to_strings(hass: HomeAssistant) -> None:
    """Test API monitor IDs are normalized to strings."""
    monitor = {
        "id": 42,
        "attributes": {
            "pronounceable_name": "Numeric ID Monitor",
            "status": "up",
        },
    }
    page = mock_api_page([monitor])

    coordinator = BetterStackCoordinator(hass, make_config_entry())

    with mock_session([page]):
        data = await coordinator._async_update_data()

    assert "42" in data
    assert data["42"]["id"] == "42"


async def test_heartbeats_fetched_with_prefixed_keys(hass: HomeAssistant) -> None:
    """Test heartbeats sit alongside monitors under heartbeat- prefixed keys."""
    coordinator = BetterStackCoordinator(hass, make_config_entry())

    with mock_session([mock_api_page(MOCK_MONITORS)], [mock_api_page(MOCK_HEARTBEATS)]):
        data = await coordinator._async_update_data()

    # Monitor 1001 and heartbeat 1001 share an ID in Better Stack
    assert set(data) == {"1001", "1002", "1003", "heartbeat-1001", "heartbeat-2001"}
    assert data["1001"]["kind"] == "monitor"
    assert data["heartbeat-1001"]["kind"] == "heartbeat"
    assert data["heartbeat-2001"]["status"] == "down"


async def test_heartbeat_data_extraction_fields(hass: HomeAssistant) -> None:
    """Test heartbeat fields are extracted and the heartbeat URL is never kept."""
    heartbeat = make_heartbeat(
        "7",
        name="Backups",
        status="paused",
        period=3600,
        grace=120,
        paused_at="2025-06-15T12:00:00Z",
    )
    coordinator = BetterStackCoordinator(hass, make_config_entry())

    with mock_session([mock_api_page([])], [mock_api_page([heartbeat])]):
        data = await coordinator._async_update_data()

    assert data["heartbeat-7"] == {
        "kind": "heartbeat",
        "id": "7",
        "name": "Backups",
        "status": "paused",
        "period": 3600,
        "grace": 120,
        "paused_at": "2025-06-15T12:00:00Z",
    }


async def test_heartbeat_defaults_for_missing_fields(hass: HomeAssistant) -> None:
    """Test defaults are applied when heartbeat attributes are missing."""
    coordinator = BetterStackCoordinator(hass, make_config_entry())

    with mock_session([mock_api_page([])], [mock_api_page([{"id": 8, "attributes": {}}])]):
        data = await coordinator._async_update_data()

    h = data["heartbeat-8"]
    assert h["id"] == "8"
    assert h["name"] == "Heartbeat 8"
    assert h["status"] is None


async def test_paginated_heartbeats(hass: HomeAssistant) -> None:
    """Test heartbeats are fetched across multiple pages."""
    page1 = mock_api_page(
        [make_heartbeat("1", "First")],
        next_url="https://uptime.betterstack.com/api/v2/heartbeats?page=2",
    )
    page2 = mock_api_page([make_heartbeat("2", "Second")])
    coordinator = BetterStackCoordinator(hass, make_config_entry())

    with mock_session([mock_api_page([])], [page1, page2]):
        data = await coordinator._async_update_data()

    assert data["heartbeat-1"]["name"] == "First"
    assert data["heartbeat-2"]["name"] == "Second"


@pytest.mark.parametrize("status", [401, 403])
async def test_heartbeats_forbidden_keeps_monitors(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture, status: int
) -> None:
    """Test a token without heartbeat access still reports monitors, warning once."""
    coordinator = BetterStackCoordinator(hass, make_config_entry())
    caplog.set_level(logging.WARNING)

    with mock_session([mock_api_page(MOCK_MONITORS)], [status]):
        first = await coordinator._async_update_data()
        second = await coordinator._async_update_data()

    assert set(first) == set(second) == {"1001", "1002", "1003"}
    assert caplog.text.count("cannot read heartbeats") == 1


async def test_heartbeats_server_error_fails_update(hass: HomeAssistant) -> None:
    """Test any other heartbeat error fails the whole update."""
    coordinator = BetterStackCoordinator(hass, make_config_entry())

    with (
        mock_session([mock_api_page(MOCK_MONITORS)], [500]),
        pytest.raises(UpdateFailed, match="API request failed: 500"),
    ):
        await coordinator._async_update_data()
