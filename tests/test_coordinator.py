"""Tests for Better Stack Uptime coordinator."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.betterstack_uptime.coordinator import BetterStackCoordinator

from .conftest import MOCK_MONITORS, TEST_API_TOKEN, make_monitor, mock_api_page


def _mock_session_with_pages(pages: list[dict]):
    """Create a mock session returned by async_get_clientsession."""
    responses = []
    for page in pages:
        resp = AsyncMock()
        resp.status = 200
        resp.raise_for_status = MagicMock()
        resp.json = AsyncMock(return_value=page)
        responses.append(resp)

    call_index = {"i": 0}

    session = MagicMock()

    def make_get_ctx(*args, **kwargs):
        ctx = AsyncMock()
        idx = call_index["i"]
        call_index["i"] += 1
        ctx.__aenter__ = AsyncMock(return_value=responses[idx])
        ctx.__aexit__ = AsyncMock(return_value=False)
        return ctx

    session.get = MagicMock(side_effect=make_get_ctx)

    return patch(
        "custom_components.betterstack_uptime.coordinator.async_get_clientsession",
        return_value=session,
    )


async def test_single_page_fetch(hass: HomeAssistant) -> None:
    """Test fetching monitors from a single page response."""
    page = mock_api_page(MOCK_MONITORS)

    coordinator = BetterStackCoordinator(hass, TEST_API_TOKEN, 60)

    with _mock_session_with_pages([page]):
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

    coordinator = BetterStackCoordinator(hass, TEST_API_TOKEN, 60)

    with _mock_session_with_pages([page1, page2]):
        data = await coordinator._async_update_data()

    assert len(data) == 2
    assert data["1"]["pronounceable_name"] == "First"
    assert data["2"]["pronounceable_name"] == "Second"


async def test_empty_response(hass: HomeAssistant) -> None:
    """Test empty API response returns empty dict."""
    page = mock_api_page([])

    coordinator = BetterStackCoordinator(hass, TEST_API_TOKEN, 60)

    with _mock_session_with_pages([page]):
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

    coordinator = BetterStackCoordinator(hass, TEST_API_TOKEN, 60)

    with (
        patch(
            "custom_components.betterstack_uptime.coordinator.async_get_clientsession",
            return_value=session,
        ),
        pytest.raises(UpdateFailed, match="API request failed: 500"),
    ):
        await coordinator._async_update_data()


async def test_api_client_error(hass: HomeAssistant) -> None:
    """Test ClientError raises UpdateFailed."""
    session = MagicMock()
    session.get = MagicMock(side_effect=aiohttp.ClientError("Connection refused"))

    coordinator = BetterStackCoordinator(hass, TEST_API_TOKEN, 60)

    with (
        patch(
            "custom_components.betterstack_uptime.coordinator.async_get_clientsession",
            return_value=session,
        ),
        pytest.raises(UpdateFailed, match="Cannot reach Better Stack"),
    ):
        await coordinator._async_update_data()


async def test_data_extraction_fields(hass: HomeAssistant) -> None:
    """Test all 6 fields are correctly extracted from API response."""
    monitor = make_monitor(
        "42",
        name="Production",
        status="down",
        monitor_type="keyword",
        url="https://prod.example.com",
        last_checked_at="2025-06-15T12:00:00Z",
    )
    page = mock_api_page([monitor])

    coordinator = BetterStackCoordinator(hass, TEST_API_TOKEN, 60)

    with _mock_session_with_pages([page]):
        data = await coordinator._async_update_data()

    m = data["42"]
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

    coordinator = BetterStackCoordinator(hass, TEST_API_TOKEN, 60)

    with _mock_session_with_pages([page]):
        data = await coordinator._async_update_data()

    m = data["99"]
    assert m["id"] == "99"
    assert m["pronounceable_name"] == "Monitor 99"
    assert m["status"] == "unknown"
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

    coordinator = BetterStackCoordinator(hass, TEST_API_TOKEN, 60)

    with _mock_session_with_pages([page]):
        data = await coordinator._async_update_data()

    assert "42" in data
    assert data["42"]["id"] == "42"
