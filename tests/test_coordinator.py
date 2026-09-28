from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant, SupportsResponse
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_mock_service,
)

from custom_components.smart_drip.const import (
    CONF_RAIN_IS_RATE,
    CONF_SENSOR_DEWPOINT,
    CONF_SENSOR_HUMIDITY,
    CONF_SENSOR_PRESSURE,
    CONF_SENSOR_RADIATION,
    CONF_SENSOR_RAIN_INTENSITY,
    CONF_SENSOR_RAIN_TODAY,
    CONF_SENSOR_TEMP,
    CONF_SENSOR_WIND,
    CONF_ZONE_1_AREA,
    CONF_ZONE_1_ENABLED,
    CONF_ZONE_1_FLOW_RATE,
    CONF_ZONE_1_SWITCH,
    CONF_ZONE_2_AREA,
    CONF_ZONE_2_ENABLED,
    CONF_ZONE_2_FLOW_RATE,
    CONF_ZONE_2_SWITCH,
    DEFAULT_SENSOR_DEWPOINT,
    DEFAULT_SENSOR_HUMIDITY,
    DEFAULT_SENSOR_PRESSURE,
    DEFAULT_SENSOR_RADIATION,
    DEFAULT_SENSOR_RAIN_INTENSITY,
    DEFAULT_SENSOR_RAIN_TODAY,
    DEFAULT_SENSOR_TEMP,
    DEFAULT_SENSOR_WIND,
    DEFAULT_ZONE_1_SWITCH,
    DEFAULT_ZONE_2_SWITCH,
    DOMAIN,
    STATUS_READY,
    STATUS_SKIPPED_ACTIVE_RAIN,
    STATUS_SKIPPED_DAILY_RAIN_EXCEEDED,
    STATUS_SKIPPED_LOW_TEMP,
    STATUS_SKIPPED_RAIN_TOMORROW,
    STATUS_SKIPPED_ZERO_DEFICIT,
    STATUS_SKIPPED_ZONE_DISABLED,
)
from custom_components.smart_drip.coordinator import SmartDripCoordinator


def setup_mock_weather_sensors(
    hass: HomeAssistant,
    temp: float = 21.0,
    humidity: float = 55.0,
    dewpoint: float = 11.5,
    radiation: float = 16.0,
    wind: float = 2.5,
    pressure: float = 1012.0,
    rain_today: float = 0.0,
    rain_intensity: float = 0.0,
) -> None:
    """Set up state entries for mock Tempest WeatherFlow sensors."""
    hass.states.async_set(DEFAULT_SENSOR_TEMP, str(temp))
    hass.states.async_set(DEFAULT_SENSOR_HUMIDITY, str(humidity))
    hass.states.async_set(DEFAULT_SENSOR_DEWPOINT, str(dewpoint))
    hass.states.async_set(DEFAULT_SENSOR_RADIATION, str(radiation))
    hass.states.async_set(DEFAULT_SENSOR_WIND, str(wind))
    hass.states.async_set(DEFAULT_SENSOR_PRESSURE, str(pressure))
    hass.states.async_set(DEFAULT_SENSOR_RAIN_TODAY, str(rain_today))
    hass.states.async_set(DEFAULT_SENSOR_RAIN_INTENSITY, str(rain_intensity))


def get_mock_entry() -> MockConfigEntry:
    """Create a mock ConfigEntry for smart_drip."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Smart Drip",
        data={
            CONF_SENSOR_TEMP: DEFAULT_SENSOR_TEMP,
            CONF_SENSOR_HUMIDITY: DEFAULT_SENSOR_HUMIDITY,
            CONF_SENSOR_DEWPOINT: DEFAULT_SENSOR_DEWPOINT,
            CONF_SENSOR_RADIATION: DEFAULT_SENSOR_RADIATION,
            CONF_SENSOR_WIND: DEFAULT_SENSOR_WIND,
            CONF_SENSOR_PRESSURE: DEFAULT_SENSOR_PRESSURE,
            CONF_SENSOR_RAIN_TODAY: DEFAULT_SENSOR_RAIN_TODAY,
            CONF_SENSOR_RAIN_INTENSITY: DEFAULT_SENSOR_RAIN_INTENSITY,
            CONF_ZONE_1_SWITCH: DEFAULT_ZONE_1_SWITCH,
            CONF_ZONE_2_SWITCH: DEFAULT_ZONE_2_SWITCH,
            CONF_ZONE_1_AREA: 4.8,
            CONF_ZONE_2_AREA: 5.0,
            CONF_ZONE_1_FLOW_RATE: 40.0,
            CONF_ZONE_2_FLOW_RATE: 40.0,
            CONF_ZONE_1_ENABLED: True,
            CONF_ZONE_2_ENABLED: False,
            CONF_RAIN_IS_RATE: False,
        },
    )


@pytest.mark.asyncio
async def test_coordinator_et0_calculation_and_deficit(hass: HomeAssistant) -> None:
    """Test ET0 calculation and deficit accumulation from weather sensors."""
    setup_mock_weather_sensors(hass, temp=20.0, radiation=15.0, wind=2.0, humidity=50.0)
    entry = get_mock_entry()
    entry.add_to_hass(hass)

    coordinator = SmartDripCoordinator(hass, entry)
    await coordinator.async_setup()

    # Initial state
    assert coordinator.zone_deficits[1] == 0.0

    # Calculate ET0
    await coordinator.async_calculate_daily_et0()
    assert coordinator.last_et0 > 0.0
    # Deficit should have increased by ET0
    assert coordinator.zone_deficits[1] == coordinator.last_et0


@pytest.mark.asyncio
async def test_coordinator_zone_evaluation_skip_conditions(hass: HomeAssistant) -> None:
    """Test decision state machine transitions for various weather conditions."""
    entry = get_mock_entry()
    entry.add_to_hass(hass)

    coordinator = SmartDripCoordinator(hass, entry)
    await coordinator.async_setup()

    # 1. Deficit is 0 -> Skipped: Zero Deficit
    setup_mock_weather_sensors(hass, temp=20.0, rain_today=0.0, rain_intensity=0.0)
    await coordinator.async_evaluate_zones()
    assert coordinator.zone_status[1]["state"] == STATUS_SKIPPED_ZERO_DEFICIT
    assert coordinator.zone_status[2]["state"] == STATUS_SKIPPED_ZONE_DISABLED

    # Set deficit above threshold
    coordinator.zone_deficits[1] = 3.0

    # 2. Temperature < 4.0 C -> Skipped: Low Temperature
    setup_mock_weather_sensors(hass, temp=3.2)
    await coordinator.async_evaluate_zones()
    assert coordinator.zone_status[1]["state"] == STATUS_SKIPPED_LOW_TEMP

    # 3. Active rain > 0 -> Skipped: Active Rain
    setup_mock_weather_sensors(hass, temp=15.0, rain_intensity=1.2)
    await coordinator.async_evaluate_zones()
    assert coordinator.zone_status[1]["state"] == STATUS_SKIPPED_ACTIVE_RAIN

    # 4. Rain today >= 2.5 mm -> Skipped: Daily Rain Exceeded
    setup_mock_weather_sensors(hass, temp=15.0, rain_today=3.0, rain_intensity=0.0)
    await coordinator.async_evaluate_zones()
    assert coordinator.zone_status[1]["state"] == STATUS_SKIPPED_DAILY_RAIN_EXCEEDED

    # 5. Normal sunny conditions -> Ready
    setup_mock_weather_sensors(hass, temp=18.0, rain_today=0.0, rain_intensity=0.0)
    await coordinator.async_evaluate_zones()
    assert coordinator.zone_status[1]["state"] == STATUS_READY
    assert coordinator.zone_status[1]["target_duration_seconds"] > 0


@pytest.mark.asyncio
async def test_coordinator_sequential_morning_execution(hass: HomeAssistant) -> None:
    """Test sequential execution of morning schedule enforcing 10s interlock pause."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Smart Drip",
        data={
            CONF_SENSOR_TEMP: DEFAULT_SENSOR_TEMP,
            CONF_SENSOR_HUMIDITY: DEFAULT_SENSOR_HUMIDITY,
            CONF_SENSOR_DEWPOINT: DEFAULT_SENSOR_DEWPOINT,
            CONF_SENSOR_RADIATION: DEFAULT_SENSOR_RADIATION,
            CONF_SENSOR_WIND: DEFAULT_SENSOR_WIND,
            CONF_SENSOR_PRESSURE: DEFAULT_SENSOR_PRESSURE,
            CONF_SENSOR_RAIN_TODAY: DEFAULT_SENSOR_RAIN_TODAY,
            CONF_SENSOR_RAIN_INTENSITY: DEFAULT_SENSOR_RAIN_INTENSITY,
            CONF_ZONE_1_SWITCH: DEFAULT_ZONE_1_SWITCH,
            CONF_ZONE_2_SWITCH: DEFAULT_ZONE_2_SWITCH,
            CONF_ZONE_1_AREA: 4.8,
            CONF_ZONE_2_AREA: 5.0,
            CONF_ZONE_1_FLOW_RATE: 40.0,
            CONF_ZONE_2_FLOW_RATE: 40.0,
            CONF_ZONE_1_ENABLED: True,
            CONF_ZONE_2_ENABLED: True,
        },
    )
    entry.add_to_hass(hass)

    # Set initial switch states
    hass.states.async_set(DEFAULT_ZONE_1_SWITCH, "off")
    hass.states.async_set(DEFAULT_ZONE_2_SWITCH, "off")

    setup_mock_weather_sensors(hass, temp=20.0, rain_today=0.0, rain_intensity=0.0)

    coordinator = SmartDripCoordinator(hass, entry)
    await coordinator.async_setup()

    # Set water deficits
    coordinator.zone_deficits[1] = 2.0  # ~864s
    coordinator.zone_deficits[2] = 2.0  # ~900s

    calls_turn_on = async_mock_service(hass, "switch", "turn_on")
    calls_turn_off = async_mock_service(hass, "switch", "turn_off")

    with patch("asyncio.sleep", new_callable=AsyncMock):
        await coordinator.async_execute_morning_schedule()

        # Both channels should have received turn_on and turn_off service calls
        assert len(calls_turn_on) == 2
        assert len(calls_turn_off) == 2
        assert calls_turn_on[0].data["entity_id"] == DEFAULT_ZONE_1_SWITCH
        assert calls_turn_off[0].data["entity_id"] == DEFAULT_ZONE_1_SWITCH
        assert calls_turn_on[1].data["entity_id"] == DEFAULT_ZONE_2_SWITCH
        assert calls_turn_off[1].data["entity_id"] == DEFAULT_ZONE_2_SWITCH

        # Deficits should have been cleared/reduced
        assert coordinator.zone_deficits[1] == 0.0
        assert coordinator.zone_deficits[2] == 0.0

        # Last run statistics should be recorded
        assert coordinator.zone_status[1]["last_run_timestamp"] is not None
        assert coordinator.zone_status[1]["last_run_duration_seconds"] > 0
        assert coordinator.zone_status[1]["last_run_liters"] > 0.0
        assert coordinator.zone_status[1]["last_run_applied_mm"] > 0.0
        assert coordinator.zone_status[1]["last_run_trigger"] == "automatic_morning_schedule"
        assert coordinator.zone_status[2]["last_run_timestamp"] is not None
        assert coordinator.zone_status[2]["last_run_trigger"] == "automatic_morning_schedule"


@pytest.mark.asyncio
async def test_coordinator_reset_bucket(hass: HomeAssistant) -> None:
    """Test reset bucket resets deficit to 0."""
    entry = get_mock_entry()
    entry.add_to_hass(hass)

    coordinator = SmartDripCoordinator(hass, entry)
    await coordinator.async_setup()

    coordinator.zone_deficits[1] = 12.5
    coordinator.zone_deficits[2] = 8.0

    # Reset zone 1 only
    await coordinator.async_reset_bucket(1)
    assert coordinator.zone_deficits[1] == 0.0
    assert coordinator.zone_deficits[2] == 8.0

    # Reset all
    await coordinator.async_reset_bucket("all")
    assert coordinator.zone_deficits[1] == 0.0
    assert coordinator.zone_deficits[2] == 0.0


@pytest.mark.asyncio
async def test_coordinator_manual_run_and_triggers(hass: HomeAssistant) -> None:
    """Test manual zone run and scheduled trigger callbacks."""
    entry = get_mock_entry()
    entry.add_to_hass(hass)

    coordinator = SmartDripCoordinator(hass, entry)
    await coordinator.async_setup()

    # Test invalid zone raises ValueError
    with pytest.raises(ValueError, match="Invalid zone 3"):
        await coordinator.async_run_zone_manual(3, 100)

    # Test valid manual run
    calls_on = async_mock_service(hass, "switch", "turn_on")
    calls_off = async_mock_service(hass, "switch", "turn_off")
    with patch("asyncio.sleep", new_callable=AsyncMock):
        await coordinator.async_run_zone_manual(1, 300)
        assert len(calls_on) == 1
        assert len(calls_off) == 1
        assert coordinator.zone_status[1]["last_run_timestamp"] is not None
        assert coordinator.zone_status[1]["last_run_duration_seconds"] == 300
        assert coordinator.zone_status[1]["last_run_trigger"] == "manual"
        assert coordinator.zone_status[1]["last_run_liters"] > 0.0

    # Test scheduled trigger callbacks
    with (
        patch.object(coordinator, "async_calculate_daily_et0", new_callable=AsyncMock) as mock_et0,
        patch.object(
            coordinator, "async_execute_morning_schedule", new_callable=AsyncMock
        ) as mock_sched,
    ):
        await coordinator._handle_nightly_et0_trigger(None)  # type: ignore[arg-type]
        mock_et0.assert_awaited_once()

        await coordinator._handle_morning_irrigation_trigger(None)  # type: ignore[arg-type]
        mock_sched.assert_awaited_once()

    # Test unload
    await coordinator.async_unload()
    assert len(coordinator._unsub_schedules) == 0


@pytest.mark.asyncio
async def test_coordinator_dynamic_weather_state_change(hass: HomeAssistant) -> None:
    """Test reactive zone re-evaluation when weather telemetry states change."""
    setup_mock_weather_sensors(hass, temp=21.0, rain_today=0.0)
    entry = get_mock_entry()
    entry.add_to_hass(hass)

    coordinator = SmartDripCoordinator(hass, entry)
    await coordinator.async_setup()

    assert coordinator.rain_today == 0.0
    assert coordinator.zone_status[1]["state"] == STATUS_SKIPPED_ZERO_DEFICIT

    # Simulate rainfall update during the day with comma formatting support ("2,6")
    hass.states.async_set(DEFAULT_SENSOR_RAIN_TODAY, "2,6")
    await hass.async_block_till_done()

    assert coordinator.rain_today == 2.6
    assert coordinator.zone_status[1]["state"] == STATUS_SKIPPED_DAILY_RAIN_EXCEEDED
    assert coordinator.zone_status[1]["last_rain_today_mm"] == 2.6
    assert "2.6 mm" in coordinator.zone_status[1]["reason"]
    assert "Rainfall today" in coordinator.zone_status[1]["reason"]


@pytest.mark.asyncio
async def test_coordinator_rain_rate_live_integration(hass: HomeAssistant) -> None:
    """Test dynamic numerical integration of rain rate into rain_today across time steps."""
    setup_mock_weather_sensors(hass, temp=20.0, rain_today=0.0)
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Smart Drip Rate",
        data={
            CONF_SENSOR_TEMP: DEFAULT_SENSOR_TEMP,
            CONF_SENSOR_RAIN_TODAY: DEFAULT_SENSOR_RAIN_TODAY,
            CONF_SENSOR_RAIN_INTENSITY: DEFAULT_SENSOR_RAIN_INTENSITY,
            CONF_ZONE_1_SWITCH: DEFAULT_ZONE_1_SWITCH,
            CONF_ZONE_1_ENABLED: True,
            CONF_RAIN_IS_RATE: True,
        },
    )
    entry.add_to_hass(hass)

    coordinator = SmartDripCoordinator(hass, entry)
    await coordinator.async_setup()

    assert coordinator.rain_today == 0.0

    # Simulate 30 minutes of rain at 4.0 mm/h
    # Initial rate 0.0 at t - 1800s
    coordinator._last_rain_rate = 4.0
    coordinator._last_rain_rate_timestamp = dt_util.now() - timedelta(minutes=30)

    # State updates to 4.0 mm/h -> trapezoid ((4.0 + 4.0)/2) * 0.5h = 2.0 mm
    hass.states.async_set(DEFAULT_SENSOR_RAIN_TODAY, "4.0")
    await hass.async_block_till_done()

    assert coordinator.rain_today == 2.0

    # Another 15 minutes at 2.4 mm/h -> trapezoid ((4.0 + 2.4)/2) * 0.25h = 0.8 mm
    coordinator._last_rain_rate = 4.0
    coordinator._last_rain_rate_timestamp = dt_util.now() - timedelta(minutes=15)
    hass.states.async_set(DEFAULT_SENSOR_RAIN_TODAY, "2.4")
    await hass.async_block_till_done()

    assert coordinator.rain_today == 2.8


@pytest.mark.asyncio
async def test_coordinator_midnight_rollover(hass: HomeAssistant) -> None:
    """Test midnight rollover moves rain_today into yesterday_rain and resets accumulator."""
    entry = get_mock_entry()
    entry.add_to_hass(hass)

    coordinator = SmartDripCoordinator(hass, entry)
    await coordinator.async_setup()

    coordinator.rain_today = 3.65
    with patch.object(coordinator, "async_save_state", new_callable=AsyncMock) as mock_save:
        await coordinator._handle_midnight_rollover(dt_util.now())
        assert coordinator.yesterday_rain == 3.65
        assert coordinator.rain_today == 0.0
        mock_save.assert_awaited_once()


@pytest.mark.asyncio
async def test_coordinator_forecast_service_update(hass: HomeAssistant) -> None:
    """Test retrieving tomorrow's precipitation forecast via weather.get_forecasts service."""
    entry = get_mock_entry()
    entry.add_to_hass(hass)

    coordinator = SmartDripCoordinator(hass, entry)
    now = dt_util.now()
    tomorrow_str = (now + timedelta(days=1)).isoformat()

    mock_response = {
        "weather.smhi_home": {
            "forecast": [
                {"datetime": now.isoformat(), "precipitation": 0.0},
                {"datetime": tomorrow_str, "precipitation": 7.5},
            ]
        }
    }

    async def mock_call_service(call):
        return mock_response

    hass.services.async_register(
        "weather",
        "get_forecasts",
        mock_call_service,
        supports_response=SupportsResponse.ONLY,
    )

    rain = await coordinator.async_update_forecast()
    assert rain == 7.5
    assert coordinator.rain_tomorrow == 7.5


@pytest.mark.asyncio
async def test_coordinator_forecast_fallback_attribute(hass: HomeAssistant) -> None:
    """Test falling back to weather entity forecast state attribute if service fails."""
    entry = get_mock_entry()
    entry.add_to_hass(hass)

    coordinator = SmartDripCoordinator(hass, entry)
    now = dt_util.now()

    hass.states.async_set(
        "weather.smhi_home",
        "partlycloudy",
        {
            "forecast": [
                {"datetime": now.isoformat(), "precipitation": 0.0},
                {"datetime": (now + timedelta(days=1)).isoformat(), "precipitation": 4.2},
            ]
        },
    )

    # Without registering weather.get_forecasts, the service call fails and falls back to state attribute
    rain = await coordinator.async_update_forecast()
    assert rain == 4.2
    assert coordinator.rain_tomorrow == 4.2


@pytest.mark.asyncio
async def test_coordinator_et0_does_not_overwrite_yesterday_rain(hass: HomeAssistant) -> None:
    """Verify that daily ET0 calculation at 23:00 does NOT overwrite yesterday_rain prematurely."""
    entry = get_mock_entry()
    entry.add_to_hass(hass)

    coordinator = SmartDripCoordinator(hass, entry)
    coordinator.yesterday_rain = 5.0
    coordinator.rain_today = 2.0

    setup_mock_weather_sensors(hass, temp=20.0, rain_today=2.0)

    with (
        patch.object(coordinator, "async_save_state", new_callable=AsyncMock),
        patch.object(coordinator, "async_update_forecast", new_callable=AsyncMock),
    ):
        await coordinator.async_calculate_daily_et0()

    # yesterday_rain must remain unchanged at 5.0 (only 00:00 midnight rolls it over)
    assert coordinator.yesterday_rain == 5.0
    assert coordinator.rain_today == 2.0


@pytest.mark.asyncio
async def test_coordinator_skip_tomorrow_rain(hass: HomeAssistant) -> None:
    """Test skipping irrigation when rain forecast tomorrow exceeds cutoff."""
    entry = get_mock_entry()
    entry.add_to_hass(hass)

    coordinator = SmartDripCoordinator(hass, entry)
    coordinator.zone_deficits[1] = 4.0
    coordinator.rain_tomorrow = 8.0

    setup_mock_weather_sensors(hass, temp=18.0, rain_today=0.0, rain_intensity=0.0)
    await coordinator.async_evaluate_zones()

    assert coordinator.zone_status[1]["state"] == STATUS_SKIPPED_RAIN_TOMORROW
    assert "Tomorrow's rain forecast" in coordinator.zone_status[1]["reason"]
