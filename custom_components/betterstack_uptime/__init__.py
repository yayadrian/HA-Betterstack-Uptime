"""Better Stack Uptime integration for Home Assistant."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL
from .coordinator import BetterStackConfigEntry, BetterStackCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]


async def _async_update_listener(hass: HomeAssistant, entry: BetterStackConfigEntry) -> None:
    """Update coordinator poll interval when options change."""
    coordinator = entry.runtime_data
    poll_interval = entry.options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
    coordinator.update_interval = timedelta(seconds=poll_interval)
    await coordinator.async_refresh()


async def async_setup_entry(hass: HomeAssistant, entry: BetterStackConfigEntry) -> bool:
    """Set up Better Stack Uptime from a config entry."""
    coordinator = BetterStackCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: BetterStackConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
