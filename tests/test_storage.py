"""Unit tests for Smart Drip persistent storage and recorder backfill."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smart_drip.const import (
    CONF_ZONE_1_ENABLED,
    CONF_ZONE_2_ENABLED,
    DOMAIN,
)
from custom_components.smart_drip.coordinator import SmartDripCoordinator


@pytest.fixture
def mock_entry() -> MockConfigEntry:
    """Fixture providing a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Smart Drip",
        data={
            CONF_ZONE_1_ENABLED: True,
            CONF_ZONE_2_ENABLED: True,
        },
    )


@pytest.mark.asyncio
async def test_storage_restores_persisted_state(
    hass: HomeAssistant, mock_entry: MockConfigEntry
) -> None:
    """Test coordinator restores persisted state from storage."""
    mock_entry.add_to_hass(hass)
    coordinator = SmartDripCoordinator(hass, mock_entry)

    saved_data = {
        "last_et0": 3.75,
        "yesterday_rain": 4.5,
        "zone_deficits": {"1": 6.8, "2": 0.0},
        "zone_status": {
            "1": {"state": "Ready", "reason": "Deficit accumulated"},
            "2": {"state": "Skipped: Zone Disabled", "reason": "Disabled"},
        },
    }

    with (
        patch.object(Store, "async_load", new_callable=AsyncMock, return_value=saved_data),
        patch("custom_components.smart_drip.coordinator.async_track_time_change"),
    ):
        await coordinator.async_setup()

    assert coordinator.last_et0 == 3.75
    assert coordinator.yesterday_rain == 4.5
    assert coordinator.zone_deficits[1] == 6.8
    assert coordinator.zone_deficits[2] == 0.0
    assert coordinator.zone_status[1]["state"] == "Ready"


@pytest.mark.asyncio
async def test_first_run_recorder_backfill_success(
    hass: HomeAssistant, mock_entry: MockConfigEntry
) -> None:
    """Test cold start backfills yesterday's rain from recorder."""
    mock_entry.add_to_hass(hass)
    coordinator = SmartDripCoordinator(hass, mock_entry)

    hass.config.components.add("recorder")

    mock_recorder = MagicMock()
    mock_state = MagicMock()
    mock_state.state = "14.2"
    states_dict = {
        "sensor.vaderstation_nederbord": [mock_state],
    }
    mock_recorder.async_add_executor_job = AsyncMock(return_value=states_dict)

    with (
        patch.object(Store, "async_load", new_callable=AsyncMock, return_value=None),
        patch.object(Store, "async_save", new_callable=AsyncMock) as mock_save,
        patch("homeassistant.components.recorder.get_instance", return_value=mock_recorder),
        patch("custom_components.smart_drip.coordinator.async_track_time_change"),
    ):
        await coordinator.async_setup()

    assert coordinator.yesterday_rain == 14.2
    mock_save.assert_awaited()


@pytest.mark.asyncio
async def test_first_run_recorder_not_active(
    hass: HomeAssistant, mock_entry: MockConfigEntry
) -> None:
    """Test cold start skips backfill if recorder is not in components."""
    mock_entry.add_to_hass(hass)
    coordinator = SmartDripCoordinator(hass, mock_entry)

    if "recorder" in hass.config.components:
        hass.config.components.remove("recorder")

    with (
        patch.object(Store, "async_load", new_callable=AsyncMock, return_value=None),
        patch.object(Store, "async_save", new_callable=AsyncMock),
        patch("custom_components.smart_drip.coordinator.async_track_time_change"),
    ):
        await coordinator.async_setup()

    assert coordinator.yesterday_rain == 0.0


@pytest.mark.asyncio
async def test_first_run_recorder_error_handled(
    hass: HomeAssistant, mock_entry: MockConfigEntry
) -> None:
    """Test cold start gracefully handles exceptions from recorder query."""
    mock_entry.add_to_hass(hass)
    coordinator = SmartDripCoordinator(hass, mock_entry)

    hass.config.components.add("recorder")

    with (
        patch.object(Store, "async_load", new_callable=AsyncMock, return_value=None),
        patch.object(Store, "async_save", new_callable=AsyncMock),
        patch(
            "homeassistant.components.recorder.get_instance", side_effect=RuntimeError("DB busy")
        ),
        patch("custom_components.smart_drip.coordinator.async_track_time_change"),
    ):
        await coordinator.async_setup()

    assert coordinator.yesterday_rain == 0.0


@pytest.mark.asyncio
async def test_save_state_handles_storage_exception(
    hass: HomeAssistant, mock_entry: MockConfigEntry
) -> None:
    """Test save_state gracefully handles Store.async_save errors."""
    mock_entry.add_to_hass(hass)
    coordinator = SmartDripCoordinator(hass, mock_entry)

    with patch.object(
        Store, "async_save", new_callable=AsyncMock, side_effect=OSError("Disk full")
    ):
        # Should not raise exception
        await coordinator.async_save_state()
