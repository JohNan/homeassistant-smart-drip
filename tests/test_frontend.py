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
    VERSION,
    async_register_frontend,
)


@pytest.mark.asyncio
async def test_async_register_frontend_success(hass: HomeAssistant) -> None:
    """Test successful registration of static paths and extra module url."""
    hass.data.pop(DATA_FRONTEND_REGISTERED, None)
    hass.http = MagicMock()
    hass.http.async_register_static_paths = AsyncMock()

    await async_register_frontend(hass)

    # Verify static path registered
    hass.http.async_register_static_paths.assert_awaited_once()
    configs = hass.http.async_register_static_paths.call_args[0][0]
    assert len(configs) == 1
    assert configs[0].url_path == CARD_URL

    # Verify frontend extra module url added
    expected_url = f"{CARD_URL}?v={VERSION}"
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
    expected_url = f"{CARD_URL}?v={VERSION}"
    mock_resources.async_create_item.assert_awaited_once_with(
        {"res_type": "module", "url": expected_url}
    )


@pytest.mark.asyncio
async def test_async_register_frontend_existing_lovelace_resource(hass: HomeAssistant) -> None:
    """Test Lovelace resource is not duplicated if already present."""
    hass.data.pop(DATA_FRONTEND_REGISTERED, None)
    hass.http = MagicMock()
    hass.http.async_register_static_paths = AsyncMock()

    mock_resources = MagicMock(spec=ResourceStorageCollection)
    mock_resources.loaded = True
    mock_resources.async_items.return_value = [{"url": f"{CARD_URL}?v=0.9.0"}]
    mock_resources.async_create_item = AsyncMock()

    lovelace_data = MagicMock(spec=LovelaceData)
    lovelace_data.resources = mock_resources
    hass.data[LOVELACE_DATA] = lovelace_data

    await async_register_frontend(hass)

    # Should not call create_item because existing starts with CARD_URL
    mock_resources.async_create_item.assert_not_called()


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
