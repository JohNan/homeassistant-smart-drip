"""Lovelace card registration and frontend assets for Smart Drip Irrigation."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Final

from homeassistant.components.frontend import DATA_EXTRA_MODULE_URL, UrlManager, add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER: Final = logging.getLogger(__name__)

URL_BASE: Final = "/smart_drip"
CARD_FILENAME: Final = "smart-drip-card.js"
CARD_URL: Final = f"{URL_BASE}/{CARD_FILENAME}"
DATA_FRONTEND_REGISTERED: Final = f"{DOMAIN}_frontend_registered"
VERSION: Final = "1.0.0"


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Register the Smart Drip Lovelace card static path and frontend resource."""
    if hass.data.get(DATA_FRONTEND_REGISTERED):
        return

    card_dir = Path(__file__).parent / "frontend"
    card_path = card_dir / CARD_FILENAME

    if not card_path.exists():
        _LOGGER.warning("Smart Drip Lovelace card file not found at %s", card_path)
        return

    # 1. Register static path with Home Assistant HTTP
    if hasattr(hass, "http") and hass.http:
        try:
            await hass.http.async_register_static_paths(
                [
                    StaticPathConfig(
                        url_path=CARD_URL,
                        path=str(card_path),
                        cache_headers=True,
                    )
                ]
            )
        except Exception as err:
            _LOGGER.error("Failed to register static path for Smart Drip card: %s", err)

    # 2. Add extra JS module URL to Home Assistant frontend
    versioned_url = f"{CARD_URL}?v={VERSION}"
    try:
        if DATA_EXTRA_MODULE_URL not in hass.data:
            hass.data[DATA_EXTRA_MODULE_URL] = UrlManager(lambda _action, _url: None, [])
        add_extra_js_url(hass, versioned_url)
        _LOGGER.debug("Registered Smart Drip frontend resource: %s", versioned_url)
    except Exception as err:
        _LOGGER.error("Failed to add extra JS URL for Smart Drip card: %s", err)

    # 3. If Lovelace resources storage collection is present, ensure resource exists
    await _async_register_lovelace_resource(hass, versioned_url)

    hass.data[DATA_FRONTEND_REGISTERED] = True


async def _async_register_lovelace_resource(hass: HomeAssistant, resource_url: str) -> None:
    """Register card in Lovelace storage resources collection if available."""
    try:
        from homeassistant.components.lovelace import LOVELACE_DATA, LovelaceData
        from homeassistant.components.lovelace.resources import ResourceStorageCollection

        lovelace_data: LovelaceData | None = hass.data.get(LOVELACE_DATA)
        if not lovelace_data or not hasattr(lovelace_data, "resources"):
            return

        resources = lovelace_data.resources
        if isinstance(resources, ResourceStorageCollection):
            if not resources.loaded:
                await resources.async_load()
                resources.loaded = True

            existing = any(
                item.get("url", "").startswith(CARD_URL) for item in resources.async_items()
            )
            if not existing:
                await resources.async_create_item(
                    {
                        "res_type": "module",
                        "url": resource_url,
                    }
                )
                _LOGGER.info("Auto-registered Smart Drip Lovelace resource: %s", resource_url)
    except Exception as err:
        _LOGGER.debug("Could not register Lovelace storage resource (non-critical): %s", err)
