"""Unit tests for smart_drip entity platforms (sensor, switch, button)."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
)

from custom_components.smart_drip.const import (
    CONF_ZONE_1_ENABLED,
    CONF_ZONE_2_ENABLED,
    DOMAIN,
)


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
async def test_entity_platforms_setup(hass: HomeAssistant, mock_entry: MockConfigEntry) -> None:
    """Test loading smart_drip platforms creates sensors, switches, and buttons."""
    mock_entry.add_to_hass(hass)

    with (
        patch("custom_components.smart_drip.coordinator.async_track_time_change"),
        patch(
            "custom_components.smart_drip.coordinator.SmartDripCoordinator.async_evaluate_zones",
            new_callable=AsyncMock,
        ),
    ):
        assert await hass.config_entries.async_setup(mock_entry.entry_id)
        await hass.async_block_till_done()

    # Check sensors exist
    status_sensor = hass.states.get("sensor.smart_drip_zone_1_status")
    assert status_sensor is not None
    assert status_sensor.attributes.get("reason") is not None

    et0_sensor = hass.states.get("sensor.smart_drip_daily_et0")
    assert et0_sensor is not None

    deficit_sensor = hass.states.get("sensor.smart_drip_zone_1_deficit")
    assert deficit_sensor is not None

    # Check zone switches exist
    z1_switch = hass.states.get("switch.smart_drip_zone_1_auto_irrigation")
    assert z1_switch is not None
    assert z1_switch.state == "on"

    # Check manual run buttons exist
    z1_button = hass.states.get("button.smart_drip_run_zone_1_now")
    assert z1_button is not None


@pytest.mark.asyncio
async def test_switch_toggling(hass: HomeAssistant, mock_entry: MockConfigEntry) -> None:
    """Test toggling the zone switch updates configuration."""
    mock_entry.add_to_hass(hass)

    with (
        patch("custom_components.smart_drip.coordinator.async_track_time_change"),
        patch(
            "custom_components.smart_drip.coordinator.SmartDripCoordinator.async_evaluate_zones",
            new_callable=AsyncMock,
        ),
    ):
        await hass.config_entries.async_setup(mock_entry.entry_id)
        await hass.async_block_till_done()

    # Turn off Zone 1 auto-irrigation switch
    await hass.services.async_call(
        "switch",
        "turn_off",
        {"entity_id": "switch.smart_drip_zone_1_auto_irrigation"},
        blocking=True,
    )
    assert hass.states.get("switch.smart_drip_zone_1_auto_irrigation").state == "off"

    # Turn on Zone 1 auto-irrigation switch
    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": "switch.smart_drip_zone_1_auto_irrigation"},
        blocking=True,
    )
    assert hass.states.get("switch.smart_drip_zone_1_auto_irrigation").state == "on"


@pytest.mark.asyncio
async def test_button_press_triggers_run_zone(
    hass: HomeAssistant, mock_entry: MockConfigEntry
) -> None:
    """Test pressing manual run button calls run_zone with safety ceiling."""
    mock_entry.add_to_hass(hass)

    with (
        patch("custom_components.smart_drip.coordinator.async_track_time_change"),
        patch(
            "custom_components.smart_drip.coordinator.SmartDripCoordinator.async_evaluate_zones",
            new_callable=AsyncMock,
        ),
    ):
        await hass.config_entries.async_setup(mock_entry.entry_id)
        await hass.async_block_till_done()

    coordinator = hass.data[DOMAIN][mock_entry.entry_id]
    with patch.object(coordinator, "async_run_zone_manual", new_callable=AsyncMock) as mock_run:
        await hass.services.async_call(
            "button",
            "press",
            {"entity_id": "button.smart_drip_run_zone_1_now"},
            blocking=True,
        )
        mock_run.assert_awaited_once_with(1, 600)


@pytest.mark.asyncio
async def test_custom_services_and_unload(hass: HomeAssistant, mock_entry: MockConfigEntry) -> None:
    """Test calculate_now, reset_bucket, run_zone services and integration unload."""
    mock_entry.add_to_hass(hass)

    with (
        patch("custom_components.smart_drip.coordinator.async_track_time_change"),
        patch(
            "custom_components.smart_drip.coordinator.SmartDripCoordinator.async_evaluate_zones",
            new_callable=AsyncMock,
        ),
    ):
        await hass.config_entries.async_setup(mock_entry.entry_id)
        await hass.async_block_till_done()

    coordinator = hass.data[DOMAIN][mock_entry.entry_id]

    with patch.object(
        coordinator, "async_calculate_daily_et0", new_callable=AsyncMock
    ) as mock_calc:
        await hass.services.async_call(DOMAIN, "calculate_now", {}, blocking=True)
        mock_calc.assert_awaited_once()

    with patch.object(coordinator, "async_reset_bucket", new_callable=AsyncMock) as mock_reset:
        await hass.services.async_call(DOMAIN, "reset_bucket", {"zone": "1"}, blocking=True)
        mock_reset.assert_awaited_once_with(1)

    with patch.object(
        coordinator, "async_run_zone_manual", new_callable=AsyncMock
    ) as mock_run_zone:
        await hass.services.async_call(
            DOMAIN, "run_zone", {"zone": 1, "duration": 120}, blocking=True
        )
        mock_run_zone.assert_awaited_once_with(1, 120)

    # Test entry unload
    assert await hass.config_entries.async_unload(mock_entry.entry_id)
    await hass.async_block_till_done()
    assert DOMAIN not in hass.data or mock_entry.entry_id not in hass.data[DOMAIN]
