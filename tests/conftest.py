"""Shared fixtures for Better Stack Uptime tests."""

from __future__ import annotations

import hashlib
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.betterstack_uptime.const import (
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


def mock_api_page(monitors: list[dict], next_url: str | None = None) -> dict:
    """Build an API response payload."""
    pagination = {"next": next_url} if next_url else {"next": None}
    return {"data": monitors, "pagination": pagination}


@pytest.fixture
def mock_config_entry(hass: HomeAssistant):
    """Create a mock config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Better Stack Uptime",
        data={CONF_API_TOKEN: TEST_API_TOKEN},
        options={CONF_POLL_INTERVAL: 60},
        unique_id=hashlib.sha256(TEST_API_TOKEN.encode()).hexdigest()[:16],
    )
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
    }
