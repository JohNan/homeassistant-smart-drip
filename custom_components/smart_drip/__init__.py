"""Smart Drip Irrigation Home Assistant integration."""

from __future__ import annotations

import logging
from typing import Final

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    PLATFORMS,
    SERVICE_CALCULATE_NOW,
    SERVICE_RESET_BUCKET,
    SERVICE_RUN_ZONE,
)
from .coordinator import SmartDripCoordinator
from .frontend import async_register_frontend

_LOGGER: Final = logging.getLogger(__name__)

SERVICE_CALCULATE_NOW_SCHEMA: Final = vol.Schema({})
SERVICE_RESET_BUCKET_SCHEMA: Final = vol.Schema(
    {
        vol.Optional("zone", default="all"): vol.Any(cv.positive_int, cv.string),
    }
)
SERVICE_RUN_ZONE_SCHEMA: Final = vol.Schema(
    {
        vol.Required("zone"): cv.positive_int,
        vol.Required("duration"): vol.All(cv.positive_int, vol.Range(min=1, max=2700)),
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Smart Drip from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    await async_register_frontend(hass)

    coordinator = SmartDripCoordinator(hass, entry)
    await coordinator.async_setup()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    async def handle_calculate_now(_call: ServiceCall) -> None:
        """Handle calculate_now service call."""
        _LOGGER.info("Service calculate_now called.")
        for coord in hass.data[DOMAIN].values():
            await coord.async_calculate_daily_et0()

    async def handle_reset_bucket(call: ServiceCall) -> None:
        """Handle reset_bucket service call."""
        zone_raw = call.data.get("zone", "all")
        _LOGGER.info("Service reset_bucket called for zone %s.", zone_raw)
        try:
            zone_val: int | str = int(zone_raw)
        except (ValueError, TypeError):
            zone_val = str(zone_raw).lower()

        for coord in hass.data[DOMAIN].values():
            await coord.async_reset_bucket(zone_val)

    async def handle_run_zone(call: ServiceCall) -> None:
        """Handle run_zone manual irrigation call."""
        zone = int(call.data["zone"])
        duration = int(call.data["duration"])
        _LOGGER.info("Service run_zone called: Zone %s for %s seconds.", zone, duration)
        for coord in hass.data[DOMAIN].values():
            await coord.async_run_zone_manual(zone, duration)

    if not hass.services.has_service(DOMAIN, SERVICE_CALCULATE_NOW):
        hass.services.async_register(
            DOMAIN,
            SERVICE_CALCULATE_NOW,
            handle_calculate_now,
            schema=SERVICE_CALCULATE_NOW_SCHEMA,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_RESET_BUCKET):
        hass.services.async_register(
            DOMAIN,
            SERVICE_RESET_BUCKET,
            handle_reset_bucket,
            schema=SERVICE_RESET_BUCKET_SCHEMA,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_RUN_ZONE):
        hass.services.async_register(
            DOMAIN,
            SERVICE_RUN_ZONE,
            handle_run_zone,
            schema=SERVICE_RUN_ZONE_SCHEMA,
        )

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        coordinator: SmartDripCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_unload()

    if not hass.data[DOMAIN]:
        hass.services.async_remove(DOMAIN, SERVICE_CALCULATE_NOW)
        hass.services.async_remove(DOMAIN, SERVICE_RESET_BUCKET)
        hass.services.async_remove(DOMAIN, SERVICE_RUN_ZONE)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
