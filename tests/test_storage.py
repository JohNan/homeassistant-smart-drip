"""Unit tests for Smart Drip persistent storage and recorder backfill."""

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smart_drip.const import (
    CONF_RAIN_IS_RATE,
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

    today_str = dt_util.now().date().isoformat()
    saved_data = {
        "last_et0": 3.75,
        "yesterday_rain": 4.5,
        "rain_today": 1.2,
        "rain_today_date": today_str,
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
    assert coordinator.rain_today == 1.2
    assert coordinator.zone_deficits[1] == 6.8
    assert coordinator.zone_deficits[2] == 0.0
    assert coordinator.zone_status[1]["state"] == "Ready"


@pytest.mark.asyncio
async def test_storage_rollover_on_next_day(
    hass: HomeAssistant, mock_entry: MockConfigEntry
) -> None:
    """Test storage from previous day rolls rain_today into yesterday_rain."""
    mock_entry.add_to_hass(hass)
    coordinator = SmartDripCoordinator(hass, mock_entry)

    yesterday_str = (dt_util.now().date() - timedelta(days=1)).isoformat()
    saved_data = {
        "last_et0": 3.75,
        "yesterday_rain": 1.0,
        "rain_today": 8.4,
        "rain_today_date": yesterday_str,
        "zone_deficits": {"1": 2.0, "2": 0.0},
        "zone_status": {},
    }

    with (
        patch.object(Store, "async_load", new_callable=AsyncMock, return_value=saved_data),
        patch("custom_components.smart_drip.coordinator.async_track_time_change"),
    ):
        await coordinator.async_setup()

    assert coordinator.yesterday_rain == 8.4
    assert coordinator.rain_today == 0.0


@pytest.mark.asyncio
async def test_first_run_recorder_backfill_success(
    hass: HomeAssistant, mock_entry: MockConfigEntry
) -> None:
    """Test cold start backfills today's and yesterday's rain from recorder rate history."""
    mock_entry.add_to_hass(hass)
    coordinator = SmartDripCoordinator(hass, mock_entry)

    hass.config.components.add("recorder")

    now = dt_util.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)

    # Yesterday: 1h rain from 10:00 to 11:00 at 4.0 mm/h = 4.0 mm
    s1 = MagicMock(state="4.0", last_updated=yesterday_start + timedelta(hours=10))
    s2 = MagicMock(state="4.0", last_updated=yesterday_start + timedelta(hours=11))

    # Today: 1h rain from 06:00 to 07:00 at 2.6 mm/h = 2.6 mm
    s3 = MagicMock(state="2.6", last_updated=today_start + timedelta(hours=6))
    s4 = MagicMock(state="2.6", last_updated=today_start + timedelta(hours=7))

    mock_recorder = MagicMock()
    states_dict = {
        "sensor.vaderstation_nederbord": [s1, s2, s3, s4],
    }
    mock_recorder.async_add_executor_job = AsyncMock(return_value=states_dict)

    with (
        patch.object(Store, "async_load", new_callable=AsyncMock, return_value=None),
        patch.object(Store, "async_save", new_callable=AsyncMock) as mock_save,
        patch("homeassistant.components.recorder.get_instance", return_value=mock_recorder),
        patch("custom_components.smart_drip.coordinator.async_track_time_change"),
    ):
        await coordinator.async_setup()

    assert coordinator.yesterday_rain == 4.0
    assert coordinator.rain_today == 2.6
    mock_save.assert_awaited()


@pytest.mark.asyncio
async def test_first_run_recorder_backfill_non_rate(hass: HomeAssistant) -> None:
    """Test cold start backfill when rain entity is a cumulative sensor."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Smart Drip Non-Rate",
        data={
            CONF_ZONE_1_ENABLED: True,
            CONF_RAIN_IS_RATE: False,
        },
    )
    entry.add_to_hass(hass)
    coordinator = SmartDripCoordinator(hass, entry)

    hass.config.components.add("recorder")

    now = dt_util.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)

    s1 = MagicMock(state="14.2", last_updated=yesterday_start + timedelta(hours=12))
    s2 = MagicMock(state="3.5", last_updated=today_start + timedelta(hours=8))

    mock_recorder = MagicMock()
    states_dict = {
        "sensor.vaderstation_nederbord": [s1, s2],
    }
    mock_recorder.async_add_executor_job = AsyncMock(return_value=states_dict)

    with (
        patch.object(Store, "async_load", new_callable=AsyncMock, return_value=None),
        patch.object(Store, "async_save", new_callable=AsyncMock),
        patch("homeassistant.components.recorder.get_instance", return_value=mock_recorder),
        patch("custom_components.smart_drip.coordinator.async_track_time_change"),
    ):
        await coordinator.async_setup()

    assert coordinator.yesterday_rain == 14.2
    assert coordinator.rain_today == 3.5


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


@pytest.mark.asyncio
async def test_storage_migrates_legacy_per_entry_file(
    hass: HomeAssistant, mock_entry: MockConfigEntry
) -> None:
    """Test coordinator migrates legacy per-entry storage to domain storage."""
    mock_entry.add_to_hass(hass)
    coordinator = SmartDripCoordinator(hass, mock_entry)

    today_str = dt_util.now().date().isoformat()
    legacy_data = {
        "last_et0": 2.5,
        "yesterday_rain": 1.2,
        "rain_today": 0.5,
        "rain_today_date": today_str,
        "zone_deficits": {"1": 3.0, "2": 0.0},
        "zone_status": {},
    }

    with (
        patch.object(Store, "async_load", side_effect=[None, legacy_data]),
        patch.object(Store, "async_save", new_callable=AsyncMock) as mock_save,
        patch.object(Store, "async_remove", new_callable=AsyncMock) as mock_remove,
        patch("custom_components.smart_drip.coordinator.async_track_time_change"),
    ):
        await coordinator.async_setup()

    assert coordinator.last_et0 == 2.5
    assert coordinator.yesterday_rain == 1.2
    assert coordinator.rain_today == 0.5
    mock_save.assert_awaited()
    mock_remove.assert_awaited_once()
