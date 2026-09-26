"""Button platform for smart_drip."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SmartDripCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up smart_drip buttons from a config entry."""
    coordinator: SmartDripCoordinator = hass.data[DOMAIN][entry.entry_id]

    buttons = [
        SmartDripRunZoneButton(coordinator, entry, zone=1),
        SmartDripRunZoneButton(coordinator, entry, zone=2),
    ]

    async_add_entities(buttons)


class SmartDripRunZoneButton(CoordinatorEntity[SmartDripCoordinator], ButtonEntity):
    """Button to trigger an immediate manual irrigation run for a zone."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SmartDripCoordinator, entry: ConfigEntry, zone: int) -> None:
        """Initialize run zone button."""
        super().__init__(coordinator)
        self.entry = entry
        self.zone = zone
        self._attr_unique_id = f"{entry.entry_id}_zone_{zone}_run_now"
        self._attr_name = f"Run Zone {zone} Now"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Smart Drip",
            manufacturer="Sonoff / WeatherFlow / Gardena",
            model="Micro-Drip ET0 Controller",
        )

    async def async_press(self) -> None:
        """Press the button to execute irrigation run."""
        # Use target duration if calculated, else fallback to 600s (10 minutes)
        target = self.coordinator.zone_status[self.zone].get("target_duration_seconds", 0)
        duration = target if target > 0 else 600

        await self.coordinator.async_run_zone_manual(self.zone, duration)
