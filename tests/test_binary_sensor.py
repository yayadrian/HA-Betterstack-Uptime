"""Tests for Better Stack Uptime binary sensor."""

from __future__ import annotations

import pytest
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.core import HomeAssistant

from custom_components.betterstack_uptime.binary_sensor import (
    BetterStackUpBinarySensor,
)
from custom_components.betterstack_uptime.const import DOMAIN
from custom_components.betterstack_uptime.coordinator import BetterStackCoordinator

from .conftest import make_config_entry


def _make_coordinator(hass: HomeAssistant, data: dict) -> BetterStackCoordinator:
    """Create a coordinator with preset data."""
    coordinator = BetterStackCoordinator(hass, make_config_entry())
    coordinator.data = data
    return coordinator


def _monitor_data(
    monitor_id: str = "100",
    status: str | None = "up",
    name: str = "Test Monitor",
    monitor_type: str = "keyword",
    url: str = "https://example.com",
    last_checked_at: str = "2025-01-01T00:00:00Z",
) -> dict:
    return {
        monitor_id: {
            "id": monitor_id,
            "pronounceable_name": name,
            "status": status,
            "monitor_type": monitor_type,
            "url": url,
            "last_checked_at": last_checked_at,
        }
    }


def _heartbeat_data(
    heartbeat_id: str = "100",
    status: str | None = "up",
    name: str = "Nightly Backup",
    period: int = 86400,
    grace: int = 300,
    paused_at: str | None = None,
) -> dict:
    return {
        f"heartbeat-{heartbeat_id}": {
            "id": heartbeat_id,
            "name": name,
            "status": status,
            "period": period,
            "grace": grace,
            "paused_at": paused_at,
        }
    }


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("up", True),
        ("validating", True),
        ("pending", False),
        ("down", False),
        ("paused", False),
    ],
)
async def test_is_on_by_status(hass: HomeAssistant, status: str, expected: bool) -> None:
    """Test is_on reflects status correctly."""
    coordinator = _make_coordinator(hass, _monitor_data(status=status))
    sensor = BetterStackUpBinarySensor(coordinator, "100")
    assert sensor.is_on is expected


@pytest.mark.parametrize("status", [None, "unknown", "something_new"])
async def test_is_on_unrecognised_status(
    hass: HomeAssistant, status: str | None
) -> None:
    """Test is_on is unknown for a missing or unrecognised status."""
    coordinator = _make_coordinator(hass, _monitor_data(status=status))
    sensor = BetterStackUpBinarySensor(coordinator, "100")
    assert sensor.is_on is None


async def test_unique_id(hass: HomeAssistant) -> None:
    """Test unique ID format."""
    coordinator = _make_coordinator(hass, _monitor_data())
    sensor = BetterStackUpBinarySensor(coordinator, "100")
    assert sensor.unique_id == "100-up"


async def test_device_info(hass: HomeAssistant) -> None:
    """Test device info structure."""
    coordinator = _make_coordinator(hass, _monitor_data(name="My Site", monitor_type="keyword"))
    sensor = BetterStackUpBinarySensor(coordinator, "100")
    info = sensor.device_info
    assert info["identifiers"] == {(DOMAIN, "100")}
    assert info["name"] == "My Site"
    assert info["manufacturer"] == "Better Stack"
    assert info["model"] == "Uptime keyword"


async def test_extra_state_attributes(hass: HomeAssistant) -> None:
    """Test extra state attributes are exposed."""
    coordinator = _make_coordinator(
        hass,
        _monitor_data(
            monitor_type="status",
            url="https://api.example.com",
            name="API Monitor",
            last_checked_at="2025-06-15T00:00:00Z",
        ),
    )
    sensor = BetterStackUpBinarySensor(coordinator, "100")
    attrs = sensor.extra_state_attributes
    assert attrs["monitor_type"] == "status"
    assert attrs["url"] == "https://api.example.com"
    assert attrs["pronounceable_name"] == "API Monitor"
    assert attrs["last_checked_at"] == "2025-06-15T00:00:00Z"


async def test_unavailable_when_monitor_missing(hass: HomeAssistant) -> None:
    """Test sensor is unavailable when monitor is not in coordinator data."""
    coordinator = _make_coordinator(hass, {})
    sensor = BetterStackUpBinarySensor(coordinator, "999")
    assert sensor.available is False
    assert sensor.is_on is None
    assert sensor.extra_state_attributes == {}
    assert sensor.device_info is None


async def test_dynamic_monitors(hass: HomeAssistant, mock_config_entry) -> None:
    """Test new monitors are added when coordinator data updates."""
    coordinator = BetterStackCoordinator(hass, mock_config_entry)
    coordinator.data = _monitor_data("1", name="First")
    mock_config_entry.runtime_data = coordinator

    added_entities: list = []

    def mock_add_entities(entities):
        added_entities.extend(entities)

    from custom_components.betterstack_uptime.binary_sensor import async_setup_entry

    await async_setup_entry(hass, mock_config_entry, mock_add_entities)

    assert len(added_entities) == 1
    assert added_entities[0].unique_id == "1-up"

    # Simulate new monitor appearing
    coordinator.data["2"] = {
        "id": "2",
        "pronounceable_name": "Second",
        "status": "down",
        "monitor_type": "status",
        "url": "https://second.example.com",
        "last_checked_at": None,
    }

    # Trigger coordinator listeners
    coordinator.async_set_updated_data(coordinator.data)

    assert len(added_entities) == 2
    assert added_entities[1].unique_id == "2-up"


async def test_monitor_device_class(hass: HomeAssistant) -> None:
    """Test monitor Up sensors are connectivity sensors."""
    coordinator = _make_coordinator(hass, _monitor_data())
    sensor = BetterStackUpBinarySensor(coordinator, "100")
    assert sensor.device_class == BinarySensorDeviceClass.CONNECTIVITY


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("up", True),
        ("validating", True),
        ("pending", False),
        ("down", False),
        ("paused", False),
        ("maintenance", False),
        ("something_new", None),
    ],
)
async def test_heartbeat_is_on_by_status(
    hass: HomeAssistant, status: str, expected: bool | None
) -> None:
    """Test heartbeat Up follows the same rules as monitors."""
    coordinator = _make_coordinator(hass, _heartbeat_data(status=status))
    sensor = BetterStackUpBinarySensor(coordinator, "heartbeat-100")
    assert sensor.is_on is expected


async def test_heartbeat_has_no_device_class(hass: HomeAssistant) -> None:
    """Test heartbeat Up sensors have no device class."""
    coordinator = _make_coordinator(hass, _heartbeat_data())
    sensor = BetterStackUpBinarySensor(coordinator, "heartbeat-100")
    assert sensor.device_class is None


async def test_heartbeat_unique_id(hass: HomeAssistant) -> None:
    """Test heartbeat unique IDs carry the heartbeat- prefix."""
    coordinator = _make_coordinator(hass, _heartbeat_data())
    sensor = BetterStackUpBinarySensor(coordinator, "heartbeat-100")
    assert sensor.unique_id == "heartbeat-100-up"


async def test_heartbeat_device_info(hass: HomeAssistant) -> None:
    """Test heartbeat devices are named after the heartbeat."""
    coordinator = _make_coordinator(hass, _heartbeat_data(name="Backups"))
    sensor = BetterStackUpBinarySensor(coordinator, "heartbeat-100")
    info = sensor.device_info
    assert info["identifiers"] == {(DOMAIN, "heartbeat-100")}
    assert info["name"] == "Backups"
    assert info["manufacturer"] == "Better Stack"
    assert info["model"] == "Heartbeat"


async def test_heartbeat_extra_state_attributes(hass: HomeAssistant) -> None:
    """Test heartbeats expose period, grace and paused_at, and never a URL."""
    coordinator = _make_coordinator(
        hass,
        _heartbeat_data(period=3600, grace=60, paused_at="2025-06-15T00:00:00Z"),
    )
    sensor = BetterStackUpBinarySensor(coordinator, "heartbeat-100")
    assert sensor.extra_state_attributes == {
        "period": 3600,
        "grace": 60,
        "paused_at": "2025-06-15T00:00:00Z",
    }
