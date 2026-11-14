"""Binary sensor platform for Better Stack Uptime."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import MONITOR_STATUS_OPTIONS, STATUSES_UP
from .coordinator import BetterStackConfigEntry, BetterStackCoordinator
from .entity import (
    BetterStackEntity,
    async_remove_missing_monitors,
    async_remove_stale_registry_entities,
)

# Coordinator-based platform; entities never poll individually
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BetterStackConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up binary sensors from a config entry."""
    coordinator = entry.runtime_data

    known_ids: set[str] = set()
    current_ids = set(coordinator.data)

    async_remove_stale_registry_entities(
        hass,
        entry,
        current_ids,
        "binary_sensor",
        "up",
    )

    @callback
    def _async_add_new_monitors() -> None:
        """Detect and add entities for newly discovered monitors."""
        current_ids = set(coordinator.data)
        async_remove_missing_monitors(
            hass,
            current_ids,
            known_ids,
            "binary_sensor",
            "up",
        )

        new_entities: list[BetterStackUpBinarySensor] = []
        for monitor_id in current_ids:
            if monitor_id not in known_ids:
                known_ids.add(monitor_id)
                new_entities.append(BetterStackUpBinarySensor(coordinator, monitor_id))
        if new_entities:
            async_add_entities(new_entities)

    # Add entities for initial data
    _async_add_new_monitors()

    # Listen for future updates to pick up dynamically added monitors
    entry.async_on_unload(coordinator.async_add_listener(_async_add_new_monitors))


class BetterStackUpBinarySensor(BetterStackEntity, BinarySensorEntity):
    """Binary sensor: is the monitor up?"""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_translation_key = "up"

    def __init__(
        self, coordinator: BetterStackCoordinator, monitor_id: str
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, monitor_id)
        self._attr_unique_id = f"{monitor_id}-up"

    @property
    def is_on(self) -> bool | None:
        """Return True when the monitor is up, or None for an unrecognised status."""
        if (data := self._monitor_data) is None:
            return None
        if (status := data["status"]) not in MONITOR_STATUS_OPTIONS:
            return None
        return status in STATUSES_UP
