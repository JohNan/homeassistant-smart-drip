"""Unit tests for Smart Drip frontend card registration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.frontend import DATA_EXTRA_MODULE_URL
from homeassistant.components.lovelace import LOVELACE_DATA, LovelaceData
from homeassistant.components.lovelace.resources import ResourceStorageCollection
from homeassistant.core import HomeAssistant

from custom_components.smart_drip.frontend import (
    CARD_URL,
    DATA_FRONTEND_REGISTERED,
    GIT_HASH,
    async_register_frontend,
)


@pytest.mark.asyncio
async def test_async_register_frontend_success(hass: HomeAssistant) -> None:
    """Test successful registration of static paths and extra module url."""
    hass.data.pop(DATA_FRONTEND_REGISTERED, None)
    hass.http = MagicMock()
    hass.http.async_register_static_paths = AsyncMock()

    await async_register_frontend(hass)

    # Verify static paths registered (card + brand assets)
    hass.http.async_register_static_paths.assert_awaited_once()
    configs = hass.http.async_register_static_paths.call_args[0][0]
    assert any(c.url_path == CARD_URL for c in configs)
    assert any(c.url_path == "/smart_drip/logo.png" for c in configs)
    assert any(c.url_path == "/smart_drip/icon.png" for c in configs)

    # Verify frontend extra module url added with git hash cache buster
    expected_url = f"{CARD_URL}?v={GIT_HASH}"
    assert expected_url in hass.data[DATA_EXTRA_MODULE_URL].urls
    assert hass.data.get(DATA_FRONTEND_REGISTERED) is True

    # Calling again should be idempotent and not register again
    hass.http.async_register_static_paths.reset_mock()
    await async_register_frontend(hass)
    hass.http.async_register_static_paths.assert_not_called()


@pytest.mark.asyncio
async def test_async_register_frontend_with_lovelace_resources(hass: HomeAssistant) -> None:
    """Test registration in Lovelace storage resources."""
    hass.data.pop(DATA_FRONTEND_REGISTERED, None)
    hass.http = MagicMock()
    hass.http.async_register_static_paths = AsyncMock()

    mock_resources = MagicMock(spec=ResourceStorageCollection)
    mock_resources.loaded = False
    mock_resources.async_load = AsyncMock()
    mock_resources.async_items.return_value = []
    mock_resources.async_create_item = AsyncMock()

    lovelace_data = MagicMock(spec=LovelaceData)
    lovelace_data.resources = mock_resources
    hass.data[LOVELACE_DATA] = lovelace_data

    await async_register_frontend(hass)

    mock_resources.async_load.assert_awaited_once()
    expected_url = f"{CARD_URL}?v={GIT_HASH}"
    mock_resources.async_create_item.assert_awaited_once_with(
        {"res_type": "module", "url": expected_url}
    )


@pytest.mark.asyncio
async def test_async_register_frontend_existing_lovelace_resource_outdated(
    hass: HomeAssistant,
) -> None:
    """Test Lovelace resource is updated when the query parameter is outdated."""
    hass.data.pop(DATA_FRONTEND_REGISTERED, None)
    hass.http = MagicMock()
    hass.http.async_register_static_paths = AsyncMock()

    mock_resources = MagicMock(spec=ResourceStorageCollection)
    mock_resources.loaded = True
    mock_resources.async_items.return_value = [{"id": "item_123", "url": f"{CARD_URL}?v=old_hash"}]
    mock_resources.async_create_item = AsyncMock()
    mock_resources.async_update_item = AsyncMock()

    lovelace_data = MagicMock(spec=LovelaceData)
    lovelace_data.resources = mock_resources
    hass.data[LOVELACE_DATA] = lovelace_data

    await async_register_frontend(hass)

    # Should not call create_item (no duplicate)
    mock_resources.async_create_item.assert_not_called()
    # Should call update_item with new git hash query param
    expected_url = f"{CARD_URL}?v={GIT_HASH}"
    mock_resources.async_update_item.assert_awaited_once_with(
        "item_123",
        {"res_type": "module", "url": expected_url},
    )


@pytest.mark.asyncio
async def test_async_register_frontend_existing_lovelace_resource_matching(
    hass: HomeAssistant,
) -> None:
    """Test Lovelace resource is untouched when query parameter already matches."""
    hass.data.pop(DATA_FRONTEND_REGISTERED, None)
    hass.http = MagicMock()
    hass.http.async_register_static_paths = AsyncMock()

    expected_url = f"{CARD_URL}?v={GIT_HASH}"
    mock_resources = MagicMock(spec=ResourceStorageCollection)
    mock_resources.loaded = True
    mock_resources.async_items.return_value = [{"id": "item_123", "url": expected_url}]
    mock_resources.async_create_item = AsyncMock()
    mock_resources.async_update_item = AsyncMock()

    lovelace_data = MagicMock(spec=LovelaceData)
    lovelace_data.resources = mock_resources
    hass.data[LOVELACE_DATA] = lovelace_data

    await async_register_frontend(hass)

    mock_resources.async_create_item.assert_not_called()
    mock_resources.async_update_item.assert_not_called()


@pytest.mark.asyncio
async def test_async_register_frontend_missing_card_file(hass: HomeAssistant) -> None:
    """Test handling when card file does not exist."""
    hass.data.pop(DATA_FRONTEND_REGISTERED, None)
    hass.http = MagicMock()
    hass.http.async_register_static_paths = AsyncMock()

    with patch("pathlib.Path.exists", return_value=False):
        await async_register_frontend(hass)

    hass.http.async_register_static_paths.assert_not_called()
    assert not hass.data.get(DATA_FRONTEND_REGISTERED)


@pytest.mark.asyncio
async def test_async_register_frontend_http_error(hass: HomeAssistant) -> None:
    """Test that errors in static path registration are handled gracefully."""
    hass.data.pop(DATA_FRONTEND_REGISTERED, None)
    hass.http = MagicMock()
    hass.http.async_register_static_paths = AsyncMock(side_effect=RuntimeError("HTTP error"))

    # Should not raise exception
    await async_register_frontend(hass)
    assert hass.data.get(DATA_FRONTEND_REGISTERED) is True


def test_card_bundle_elements_and_version_parity() -> None:
    """Test that smart-drip-card.js defines both cards and matches GIT_HASH."""
    from pathlib import Path

    card_file = (
        Path(__file__).parent.parent
        / "custom_components"
        / "smart_drip"
        / "frontend"
        / "smart-drip-card.js"
    )
    assert card_file.exists()
    content = card_file.read_text(encoding="utf-8")

    # Assert version parity
    assert f'const CARD_VERSION = "{GIT_HASH}";' in content

    # Assert both custom elements defined
    assert 'customElements.define("smart-drip-card", SmartDripCard);' in content
    assert 'customElements.define("smart-drip-schedule-card", SmartDripScheduleCard);' in content

    # Assert both card picker registrations
    assert 'type: "smart-drip-card"' in content
    assert 'type: "smart-drip-schedule-card"' in content
