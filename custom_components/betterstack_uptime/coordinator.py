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

from .const import (
    API_BASE_URL,
    CONF_API_TOKEN,
    CONF_POLL_INTERVAL,
    DEFAULT_POLL_INTERVAL,
    HEARTBEAT_ID_PREFIX,
)

_LOGGER = logging.getLogger(__name__)

type BetterStackConfigEntry = ConfigEntry[BetterStackCoordinator]

_AUTH_ERROR_STATUSES = (401, 403)


class BetterStackCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Fetch Better Stack checks (monitors and heartbeats) for entities."""

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
        # False while the token cannot read heartbeats; their entities are
        # then kept as unavailable rather than removed
        self.heartbeats_available = True

    async def _async_fetch_all(self, endpoint: str) -> list[dict[str, Any]]:
        """Fetch every item from a paginated Better Stack endpoint."""
        items: list[dict[str, Any]] = []
        url: str | None = f"{API_BASE_URL}/{endpoint}"
        headers = {"Authorization": f"Bearer {self._api_token}"}
        session = async_get_clientsession(self.hass)

        while url:
            async with session.get(url, headers=headers) as resp:
                resp.raise_for_status()
                payload = await resp.json()

            items.extend(payload.get("data", []))
            url = payload.get("pagination", {}).get("next")

        return items

    async def _async_fetch_heartbeats(self) -> list[dict[str, Any]]:
        """Fetch heartbeats, treating a token without heartbeat access as having none."""
        try:
            heartbeats = await self._async_fetch_all("heartbeats")
        except aiohttp.ClientResponseError as err:
            if err.status not in _AUTH_ERROR_STATUSES:
                raise
            if self.heartbeats_available:
                _LOGGER.warning(
                    "Better Stack API token cannot read heartbeats (HTTP %s); "
                    "heartbeat entities will be unavailable",
                    err.status,
                )
                self.heartbeats_available = False
            return []

        self.heartbeats_available = True
        return heartbeats

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Fetch all monitors and heartbeats from Better Stack."""
        checks: dict[str, dict[str, Any]] = {}

        try:
            for item in await self._async_fetch_all("monitors"):
                monitor_id = str(item["id"])
                attrs = item.get("attributes", {})
                checks[monitor_id] = {
                    "id": monitor_id,
                    "pronounceable_name": attrs.get("pronounceable_name", f"Monitor {monitor_id}"),
                    "status": attrs.get("status"),
                    "monitor_type": attrs.get("monitor_type"),
                    "url": attrs.get("url"),
                    "last_checked_at": attrs.get("last_checked_at"),
                }

            for item in await self._async_fetch_heartbeats():
                heartbeat_id = str(item["id"])
                attrs = item.get("attributes", {})
                # The heartbeat URL lets anyone report on the heartbeat's
                # behalf, so it is deliberately never stored
                checks[f"{HEARTBEAT_ID_PREFIX}{heartbeat_id}"] = {
                    "id": heartbeat_id,
                    "name": attrs.get("name") or f"Heartbeat {heartbeat_id}",
                    "status": attrs.get("status"),
                    "period": attrs.get("period"),
                    "grace": attrs.get("grace"),
                    "paused_at": attrs.get("paused_at"),
                }

        except aiohttp.ClientResponseError as err:
            if err.status in _AUTH_ERROR_STATUSES:
                raise ConfigEntryAuthFailed(
                    f"Better Stack rejected the API token: {err.status}"
                ) from err
            raise UpdateFailed(f"API request failed: {err.status}") from err
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Cannot reach Better Stack: {err}") from err

        return checks
