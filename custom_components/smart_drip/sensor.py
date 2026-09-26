"""Sensor platform for smart_drip."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
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
    """Set up smart_drip sensors from a config entry."""
    coordinator: SmartDripCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = [
        SmartDripDailyET0Sensor(coordinator, entry),
        SmartDripYesterdayRainSensor(coordinator, entry),
    ]

    for zone in (1, 2):
        entities.extend(
            [
                SmartDripZoneStatusSensor(coordinator, entry, zone),
                SmartDripZoneDeficitSensor(coordinator, entry, zone),
                SmartDripZoneDurationSensor(coordinator, entry, zone),
            ]
        )

    async_add_entities(entities)


class SmartDripBaseEntity(CoordinatorEntity[SmartDripCoordinator]):
    """Base entity for smart_drip."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: SmartDripCoordinator, entry: ConfigEntry, zone: int | None = None
    ) -> None:
        """Initialize the base entity."""
        super().__init__(coordinator)
        self.entry = entry
        self.zone = zone
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Smart Drip",
            manufacturer="Sonoff / WeatherFlow / Gardena",
            model="Micro-Drip ET0 Controller",
        )


class SmartDripDailyET0Sensor(SmartDripBaseEntity, SensorEntity):
    """Sensor reporting the calculated daily reference evapotranspiration."""

    _attr_translation_key = "daily_et0"
    _attr_native_unit_of_measurement = "mm/d"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_device_class = SensorDeviceClass.PRECIPITATION

    def __init__(self, coordinator: SmartDripCoordinator, entry: ConfigEntry) -> None:
        """Initialize ET0 sensor."""
        super().__init__(coordinator, entry, zone=None)
        self._attr_unique_id = f"{entry.entry_id}_daily_et0"
        self._attr_name = "Daily ET0"

    @property
    def native_value(self) -> float:
        """Return the last calculated ET0 in mm/d."""
        return self.coordinator.last_et0


class SmartDripZoneStatusSensor(SmartDripBaseEntity, SensorEntity):
    """Sensor reporting the transparent decision state for a zone."""

    _attr_translation_key = "zone_status"

    def __init__(self, coordinator: SmartDripCoordinator, entry: ConfigEntry, zone: int) -> None:
        """Initialize zone status sensor."""
        super().__init__(coordinator, entry, zone=zone)
        self.zone: int = zone
        self._attr_unique_id = f"{entry.entry_id}_zone_{zone}_status"
        self._attr_name = f"Zone {zone} Status"

    @property
    def native_value(self) -> str:
        """Return current status machine state."""
        return str(self.coordinator.zone_status[self.zone]["state"])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return descriptive decision attributes."""
        status = self.coordinator.zone_status[self.zone]
        return {
            "reason": status.get("reason"),
            "last_calculated_et0_mm": self.coordinator.last_et0,
            "last_rain_today_mm": status.get("last_rain_today_mm", 0.0),
            "current_deficit_mm": self.coordinator.zone_deficits[self.zone],
            "target_duration_seconds": status.get("target_duration_seconds", 0),
            "estimated_liters": status.get("estimated_liters", 0.0),
            "last_run_timestamp": status.get("last_run_timestamp"),
        }


class SmartDripZoneDeficitSensor(SmartDripBaseEntity, SensorEntity):
    """Sensor reporting cumulative soil moisture deficit in mm."""

    _attr_native_unit_of_measurement = "mm"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: SmartDripCoordinator, entry: ConfigEntry, zone: int) -> None:
        """Initialize deficit sensor."""
        super().__init__(coordinator, entry, zone=zone)
        self.zone: int = zone
        self._attr_unique_id = f"{entry.entry_id}_zone_{zone}_deficit"
        self._attr_name = f"Zone {zone} Deficit"

    @property
    def native_value(self) -> float:
        """Return cumulative water deficit in mm."""
        return self.coordinator.zone_deficits[self.zone]


class SmartDripZoneDurationSensor(SmartDripBaseEntity, SensorEntity):
    """Sensor reporting the target irrigation runtime in seconds."""

    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_device_class = SensorDeviceClass.DURATION

    def __init__(self, coordinator: SmartDripCoordinator, entry: ConfigEntry, zone: int) -> None:
        """Initialize duration sensor."""
        super().__init__(coordinator, entry, zone=zone)
        self.zone: int = zone
        self._attr_unique_id = f"{entry.entry_id}_zone_{zone}_target_duration"
        self._attr_name = f"Zone {zone} Target Duration"

    @property
    def native_value(self) -> int:
        """Return duration in seconds."""
        return int(self.coordinator.zone_status[self.zone].get("target_duration_seconds", 0))


class SmartDripYesterdayRainSensor(SmartDripBaseEntity, SensorEntity):
    """Sensor reporting yesterday's rainfall accumulation."""

    _attr_native_unit_of_measurement = "mm"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_device_class = SensorDeviceClass.PRECIPITATION

    def __init__(self, coordinator: SmartDripCoordinator, entry: ConfigEntry) -> None:
        """Initialize yesterday rain sensor."""
        super().__init__(coordinator, entry, zone=None)
        self._attr_unique_id = f"{entry.entry_id}_yesterday_rain"
        self._attr_name = "Yesterday Rain"

    @property
    def native_value(self) -> float:
        """Return yesterday's rainfall in mm."""
        return float(self.coordinator.yesterday_rain)
