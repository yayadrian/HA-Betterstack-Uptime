"""Shared fixtures for Better Stack Uptime tests."""

from __future__ import annotations

import hashlib
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.betterstack_uptime.const import (
    API_BASE_URL,
    CONF_API_TOKEN,
    CONF_POLL_INTERVAL,
    DOMAIN,
)

TEST_API_TOKEN = "test_api_token_1234567890"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable custom integrations for all tests."""


def make_monitor(
    monitor_id: str,
    name: str = "My Monitor",
    status: str = "up",
    monitor_type: str = "keyword",
    url: str = "https://example.com",
    last_checked_at: str = "2025-01-01T00:00:00Z",
) -> dict:
    """Build an API monitor item."""
    return {
        "id": monitor_id,
        "attributes": {
            "pronounceable_name": name,
            "status": status,
            "monitor_type": monitor_type,
            "url": url,
            "last_checked_at": last_checked_at,
        },
    }


MOCK_MONITORS = [
    make_monitor("1001", "Web App", "up", "keyword", "https://app.example.com"),
    make_monitor("1002", "API", "down", "status", "https://api.example.com"),
    make_monitor("1003", "Staging", "validating", "ping", "https://staging.example.com"),
]


def make_heartbeat(
    heartbeat_id: str,
    name: str = "My Heartbeat",
    status: str = "up",
    period: int = 86400,
    grace: int = 300,
    paused_at: str | None = None,
    url: str = "https://uptime.betterstack.com/api/v1/heartbeat/secret-token",
) -> dict:
    """Build an API heartbeat item."""
    return {
        "id": heartbeat_id,
        "type": "heartbeat",
        "attributes": {
            "name": name,
            "status": status,
            "period": period,
            "grace": grace,
            "paused_at": paused_at,
            "url": url,
        },
    }


MOCK_HEARTBEATS = [
    make_heartbeat("1001", "Nightly Backup", "up"),
    make_heartbeat("2001", "Cron Cleanup", "down", period=3600, grace=60),
]


def mock_api_page(items: list[dict], next_url: str | None = None) -> dict:
    """Build an API response payload."""
    pagination = {"next": next_url} if next_url else {"next": None}
    return {"data": items, "pagination": pagination}


def _mock_response(page: dict | int) -> AsyncMock:
    """Build a response for a page payload, or an HTTP error for a status code."""
    resp = AsyncMock()
    if isinstance(page, int):
        resp.status = page
        resp.raise_for_status = MagicMock(
            side_effect=aiohttp.ClientResponseError(
                request_info=MagicMock(), history=(), status=page
            )
        )
    else:
        resp.status = 200
        resp.raise_for_status = MagicMock()
        resp.json = AsyncMock(return_value=page)
    return resp


def mock_session(
    monitor_pages: list[dict | int],
    heartbeat_pages: list[dict | int] | None = None,
) -> patch:
    """Patch the client session to serve monitor and heartbeat pages by URL.

    Each endpoint's first page is served at its base URL and every later page
    at the previous page's ``pagination.next``. An int in place of a page makes
    that request fail with that HTTP status.
    """
    if heartbeat_pages is None:
        heartbeat_pages = [mock_api_page([])]

    routes: dict[str, dict | int] = {}
    for endpoint, pages in (("monitors", monitor_pages), ("heartbeats", heartbeat_pages)):
        url: str | None = f"{API_BASE_URL}/{endpoint}"
        for page in pages:
            routes[url] = page
            url = None if isinstance(page, int) else page["pagination"]["next"]

    def get(url: str, **kwargs) -> AsyncMock:
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=_mock_response(routes[url]))
        ctx.__aexit__ = AsyncMock(return_value=False)
        return ctx

    session = MagicMock()
    session.get = MagicMock(side_effect=get)

    return patch(
        "custom_components.betterstack_uptime.coordinator.async_get_clientsession",
        return_value=session,
    )


def make_config_entry() -> MockConfigEntry:
    """Build a config entry for the test API token."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Better Stack Uptime",
        data={CONF_API_TOKEN: TEST_API_TOKEN},
        options={CONF_POLL_INTERVAL: 60},
        unique_id=hashlib.sha256(TEST_API_TOKEN.encode()).hexdigest()[:16],
    )


@pytest.fixture
def mock_config_entry(hass: HomeAssistant):
    """Create a mock config entry."""
    entry = make_config_entry()
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def mock_coordinator_data():
    """Return processed coordinator data (as the coordinator would produce)."""
    return {
        "1001": {
            "id": "1001",
            "pronounceable_name": "Web App",
            "status": "up",
            "monitor_type": "keyword",
            "url": "https://app.example.com",
            "last_checked_at": "2025-01-01T00:00:00Z",
        },
        "1002": {
            "id": "1002",
            "pronounceable_name": "API",
            "status": "down",
            "monitor_type": "status",
            "url": "https://api.example.com",
            "last_checked_at": "2025-01-01T00:00:00Z",
        },
        "1003": {
            "id": "1003",
            "pronounceable_name": "Staging",
            "status": "validating",
            "monitor_type": "ping",
            "url": "https://staging.example.com",
            "last_checked_at": "2025-01-01T00:00:00Z",
        },
        "heartbeat-1001": {
            "id": "1001",
            "name": "Nightly Backup",
            "status": "up",
            "period": 86400,
            "grace": 300,
            "paused_at": None,
        },
    }
