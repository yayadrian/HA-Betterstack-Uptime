"""Binary sensor platform for Better Stack Uptime."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CHECK_STATUS_OPTIONS, STATUSES_UP
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
    def _async_add_new_checks() -> None:
        """Detect and add entities for newly discovered checks."""
        current_ids = set(coordinator.data)
        async_remove_missing_checks(
            hass,
            current_ids,
            known_ids,
            "binary_sensor",
            "up",
        )

        new_entities: list[BetterStackUpBinarySensor] = []
        for check_id in current_ids:
            if check_id not in known_ids:
                known_ids.add(check_id)
                new_entities.append(BetterStackUpBinarySensor(coordinator, check_id))
        if new_entities:
            async_add_entities(new_entities)

    # Add entities for initial data
    _async_add_new_checks()

    # Listen for future updates to pick up dynamically added checks
    entry.async_on_unload(coordinator.async_add_listener(_async_add_new_checks))


class BetterStackUpBinarySensor(BetterStackEntity, BinarySensorEntity):
    """Binary sensor: is the check up?"""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_translation_key = "up"

    def __init__(
        self, coordinator: BetterStackCoordinator, check_id: str
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, check_id)
        self._attr_unique_id = f"{check_id}-up"
        # "Connected" reads wrongly for a scheduled job, so heartbeats show On/Off
        if self._is_heartbeat:
            self._attr_device_class = None

    @property
    def is_on(self) -> bool | None:
        """Return True when the check is up, or None for an unrecognised status."""
        if (data := self._check_data) is None:
            return None
        if (status := data["status"]) not in CHECK_STATUS_OPTIONS:
            return None
        return status in STATUSES_UP
