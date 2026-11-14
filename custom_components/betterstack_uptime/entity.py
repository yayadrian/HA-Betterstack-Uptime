"""Shared base entity for Better Stack Uptime."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, HEARTBEAT_ID_PREFIX
from .coordinator import BetterStackCoordinator


def _check_id_from_unique_id(unique_id: str, suffix: str) -> str | None:
    """Extract a check ID from a platform unique ID."""
    suffix_marker = f"-{suffix}"
    if not unique_id.endswith(suffix_marker):
        return None
    return unique_id[: -len(suffix_marker)]


@callback
def async_remove_stale_registry_entities(
    hass: HomeAssistant,
    entry: ConfigEntry,
    current_ids: set[str],
    entity_domain: str,
    unique_id_suffix: str,
) -> None:
    """Remove registry entries for checks no longer returned by the API."""
    entity_registry = er.async_get(hass)

    for entity_entry in er.async_entries_for_config_entry(entity_registry, entry.entry_id):
        if entity_entry.platform != DOMAIN or entity_entry.domain != entity_domain:
            continue

        check_id = _check_id_from_unique_id(entity_entry.unique_id, unique_id_suffix)
        if check_id is None or check_id in current_ids:
            continue

        entity_registry.async_remove(entity_entry.entity_id)


@callback
def async_remove_missing_checks(
    hass: HomeAssistant,
    current_ids: set[str],
    known_ids: set[str],
    entity_domain: str,
    unique_id_suffix: str,
) -> None:
    """Remove runtime entities for checks that disappeared from Better Stack."""
    entity_registry = er.async_get(hass)

    for check_id in known_ids - current_ids:
        known_ids.remove(check_id)
        if entity_id := entity_registry.async_get_entity_id(
            entity_domain, DOMAIN, f"{check_id}-{unique_id_suffix}"
        ):
            entity_registry.async_remove(entity_id)


class BetterStackEntity(CoordinatorEntity[BetterStackCoordinator]):
    """Shared base class for Better Stack Uptime entities."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: BetterStackCoordinator, check_id: str
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._check_id = check_id
        self._is_heartbeat = check_id.startswith(HEARTBEAT_ID_PREFIX)

    @property
    def _check_data(self) -> dict | None:
        """Return the data dict for this check, or None if unavailable."""
        return self.coordinator.data.get(self._check_id)

    @property
    def available(self) -> bool:
        """Return True if coordinator is available and check data exists."""
        return super().available and self._check_data is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        if (data := self._check_data) is None:
            return {}
        if self._is_heartbeat:
            # Never the heartbeat URL: anyone holding it can report on its behalf
            return {
                "period": data.get("period"),
                "grace": data.get("grace"),
                "paused_at": data.get("paused_at"),
            }
        return {
            "monitor_type": data.get("monitor_type"),
            "url": data.get("url"),
            "pronounceable_name": data.get("pronounceable_name"),
            "last_checked_at": data.get("last_checked_at"),
        }

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return device information for this check."""
        if (data := self._check_data) is None:
            return None
        if self._is_heartbeat:
            return DeviceInfo(
                identifiers={(DOMAIN, self._check_id)},
                name=data.get("name", f"Heartbeat {data.get('id')}"),
                manufacturer="Better Stack",
                model="Heartbeat",
            )
        return DeviceInfo(
            identifiers={(DOMAIN, self._check_id)},
            name=data.get("pronounceable_name", f"Monitor {self._check_id}"),
            manufacturer="Better Stack",
            model=f"Uptime {data.get('monitor_type', 'monitor')}",
        )
