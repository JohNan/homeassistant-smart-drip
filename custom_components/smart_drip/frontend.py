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

# Short git commit hash for cache busting (manually bumped on each PR modifying the card)
GIT_HASH: Final = "88b1414"
VERSION: Final = GIT_HASH


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Register the Smart Drip Lovelace card static path and frontend resource."""
    if hass.data.get(DATA_FRONTEND_REGISTERED):
        return

    card_dir = Path(__file__).parent / "frontend"
    card_path = card_dir / CARD_FILENAME

    if not card_path.exists():
        _LOGGER.warning("Smart Drip Lovelace card file not found at %s", card_path)
        return

    # 1. Register static paths with Home Assistant HTTP
    if hasattr(hass, "http") and hass.http:
        try:
            static_paths = [
                StaticPathConfig(
                    url_path=CARD_URL,
                    path=str(card_path),
                    cache_headers=True,
                )
            ]
            for asset_name in ("logo.png", "logo.svg", "icon.png", "icon.svg"):
                asset_path = card_dir / asset_name
                if asset_path.exists():
                    static_paths.append(
                        StaticPathConfig(
                            url_path=f"{URL_BASE}/{asset_name}",
                            path=str(asset_path),
                            cache_headers=True,
                        )
                    )
            await hass.http.async_register_static_paths(static_paths)
        except Exception as err:
            _LOGGER.error("Failed to register static paths for Smart Drip frontend: %s", err)

    # 2. Add extra JS module URL to Home Assistant frontend
    versioned_url = f"{CARD_URL}?v={GIT_HASH}"
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

            existing_item = next(
                (
                    item
                    for item in resources.async_items()
                    if item.get("url", "").startswith(CARD_URL)
                ),
                None,
            )
            if existing_item is None:
                await resources.async_create_item(
                    {
                        "res_type": "module",
                        "url": resource_url,
                    }
                )
                _LOGGER.info("Auto-registered Smart Drip Lovelace resource: %s", resource_url)
            elif existing_item.get("url") != resource_url:
                item_id = existing_item.get("id")
                if item_id:
                    await resources.async_update_item(
                        item_id,
                        {
                            "res_type": "module",
                            "url": resource_url,
                        },
                    )
                    _LOGGER.info(
                        "Updated Smart Drip Lovelace resource cache buster from %s to %s",
                        existing_item.get("url"),
                        resource_url,
                    )
    except Exception as err:
        _LOGGER.debug("Could not register Lovelace storage resource (non-critical): %s", err)
