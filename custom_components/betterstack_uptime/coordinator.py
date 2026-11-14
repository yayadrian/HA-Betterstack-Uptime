"""DataUpdateCoordinator for Better Stack Uptime."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import API_BASE_URL, CONF_API_TOKEN, CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL

_LOGGER = logging.getLogger(__name__)

type BetterStackConfigEntry = ConfigEntry[BetterStackCoordinator]


class BetterStackCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Fetch Better Stack monitors and provide data to entities."""

    config_entry: BetterStackConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: BetterStackConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        poll_interval = config_entry.options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name="Better Stack Uptime",
            update_interval=timedelta(seconds=poll_interval),
        )
        self._api_token = config_entry.data[CONF_API_TOKEN]

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Fetch all monitors from Better Stack, handling pagination."""
        monitors: dict[str, dict[str, Any]] = {}
        url: str | None = f"{API_BASE_URL}/monitors"
        headers = {"Authorization": f"Bearer {self._api_token}"}
        session = async_get_clientsession(self.hass)

        try:
            while url:
                async with session.get(url, headers=headers) as resp:
                    resp.raise_for_status()
                    payload = await resp.json()

                for item in payload.get("data", []):
                    monitor_id = str(item["id"])
                    attrs = item.get("attributes", {})
                    monitors[monitor_id] = {
                        "id": monitor_id,
                        "pronounceable_name": attrs.get("pronounceable_name", f"Monitor {monitor_id}"),
                        "status": attrs.get("status"),
                        "monitor_type": attrs.get("monitor_type"),
                        "url": attrs.get("url"),
                        "last_checked_at": attrs.get("last_checked_at"),
                    }

                url = payload.get("pagination", {}).get("next")

        except aiohttp.ClientResponseError as err:
            if err.status in (401, 403):
                raise ConfigEntryAuthFailed(
                    f"Better Stack rejected the API token: {err.status}"
                ) from err
            raise UpdateFailed(f"API request failed: {err.status}") from err
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Cannot reach Better Stack: {err}") from err

        return monitors
