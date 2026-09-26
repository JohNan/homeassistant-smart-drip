"""Switch platform for smart_drip."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_ZONE_1_ENABLED,
    CONF_ZONE_2_ENABLED,
    DOMAIN,
)
from .coordinator import SmartDripCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up smart_drip switches from a config entry."""
    coordinator: SmartDripCoordinator = hass.data[DOMAIN][entry.entry_id]

    switches = [
        SmartDripZoneSwitch(coordinator, entry, zone=1),
        SmartDripZoneSwitch(coordinator, entry, zone=2),
    ]

    async_add_entities(switches)


class SmartDripZoneSwitch(CoordinatorEntity[SmartDripCoordinator], SwitchEntity):
    """Switch controlling automatic irrigation schedule enablement for a zone."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SmartDripCoordinator, entry: ConfigEntry, zone: int) -> None:
        """Initialize zone auto-irrigation switch."""
        super().__init__(coordinator)
        self.entry = entry
        self.zone = zone
        self._key = CONF_ZONE_1_ENABLED if zone == 1 else CONF_ZONE_2_ENABLED

        self._attr_unique_id = f"{entry.entry_id}_zone_{zone}_auto_irrigation"
        self._attr_name = f"Zone {zone} Auto Irrigation"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Smart Drip",
            manufacturer="Sonoff / WeatherFlow / Gardena",
            model="Micro-Drip ET0 Controller",
        )

    @property
    def is_on(self) -> bool:
        """Return True if auto-irrigation is enabled for this zone."""
        default = self.zone == 1
        return bool(self.coordinator._get_conf(self._key, default))

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable auto-irrigation schedule for this zone."""
        current_options = dict(self.entry.options or {})
        current_options[self._key] = True
        self.hass.config_entries.async_update_entry(self.entry, options=current_options)
        await self.coordinator.async_evaluate_zones()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable auto-irrigation schedule for this zone."""
        current_options = dict(self.entry.options or {})
        current_options[self._key] = False
        self.hass.config_entries.async_update_entry(self.entry, options=current_options)
        await self.coordinator.async_evaluate_zones()
