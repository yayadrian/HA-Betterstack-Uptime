"""Sensor platform for Better Stack Uptime."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CHECK_STATUS_OPTIONS
from .coordinator import BetterStackConfigEntry, BetterStackCoordinator
from .entity import (
    BetterStackEntity,
    async_remove_missing_checks,
    async_remove_stale_registry_entities,
)

# Coordinator-based platform; entities never poll individually
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BetterStackConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors from a config entry."""
    coordinator = entry.runtime_data

    known_ids: set[str] = set()
    current_ids = set(coordinator.data)

    async_remove_stale_registry_entities(
        hass,
        entry,
        current_ids,
        "sensor",
        "status",
    )

    @callback
    def _async_add_new_checks() -> None:
        """Detect and add entities for newly discovered checks."""
        current_ids = set(coordinator.data)
        async_remove_missing_checks(
            hass,
            current_ids,
            known_ids,
            "sensor",
            "status",
        )

        new_entities: list[BetterStackStatusSensor] = []
        for check_id in current_ids:
            if check_id not in known_ids:
                known_ids.add(check_id)
                new_entities.append(BetterStackStatusSensor(coordinator, check_id))
        if new_entities:
            async_add_entities(new_entities)

    _async_add_new_checks()
    entry.async_on_unload(coordinator.async_add_listener(_async_add_new_checks))


class BetterStackStatusSensor(BetterStackEntity, SensorEntity):
    """Sensor showing the raw check status string."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = CHECK_STATUS_OPTIONS
    _attr_translation_key = "status"

    def __init__(
        self, coordinator: BetterStackCoordinator, check_id: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, check_id)
        self._attr_unique_id = f"{check_id}-status"

    @property
    def native_value(self) -> str | None:
        """Return the check status, or None if it is not a known option."""
        if (data := self._check_data) is None:
            return None
        if (status := data["status"]) not in CHECK_STATUS_OPTIONS:
            return None
        return status
