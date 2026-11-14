"""Tests for Better Stack Uptime diagnostics."""

from __future__ import annotations

from homeassistant.components.diagnostics import REDACTED
from homeassistant.core import HomeAssistant

from custom_components.betterstack_uptime.const import CONF_API_TOKEN, CONF_POLL_INTERVAL
from custom_components.betterstack_uptime.coordinator import BetterStackCoordinator
from custom_components.betterstack_uptime.diagnostics import (
    async_get_config_entry_diagnostics,
)

from .conftest import TEST_API_TOKEN


async def test_diagnostics_redacts_token(
    hass: HomeAssistant, mock_config_entry, mock_coordinator_data
) -> None:
    """Test diagnostics include check data and redact the token and URLs."""
    coordinator = BetterStackCoordinator(hass, mock_config_entry)
    coordinator.data = mock_coordinator_data
    mock_config_entry.runtime_data = coordinator

    result = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    assert result["entry"]["data"] == {CONF_API_TOKEN: REDACTED}
    assert result["entry"]["options"] == {CONF_POLL_INTERVAL: 60}
    assert result["checks"].keys() == mock_coordinator_data.keys()
    for check_id, check in result["checks"].items():
        assert check["status"] == mock_coordinator_data[check_id]["status"]
        if check["kind"] == "monitor":
            assert check["url"] == REDACTED
    assert result["checks"]["heartbeat-1001"]["name"] == "Nightly Backup"
    # The coordinator's own data is not modified
    assert mock_coordinator_data["1001"]["url"] == "https://app.example.com"
    assert TEST_API_TOKEN not in str(result)
