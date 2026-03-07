"""DataUpdateCoordinator for Better Stack Uptime."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import API_BASE_URL

_LOGGER = logging.getLogger(__name__)


class BetterStackCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Fetch Better Stack monitors and provide data to entities."""

    def __init__(
        self,
        hass: HomeAssistant,
        api_token: str,
        poll_interval: int,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Better Stack Uptime",
            update_interval=timedelta(seconds=poll_interval),
        )
        self._api_token = api_token

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
                        "status": attrs.get("status", "unknown"),
                        "monitor_type": attrs.get("monitor_type"),
                        "url": attrs.get("url"),
                        "last_checked_at": attrs.get("last_checked_at"),
                    }

                url = payload.get("pagination", {}).get("next")

        except aiohttp.ClientResponseError as err:
            raise UpdateFailed(f"API request failed: {err.status}") from err
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Cannot reach Better Stack: {err}") from err

        return monitors
