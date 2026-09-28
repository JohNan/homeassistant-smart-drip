import re

with open("tests/test_coordinator.py", "r") as f:
    content = f.read()

# Make test_coordinator_sequential_morning_execution also test valve
def replace_test_coordinator_sequential_morning_execution(match):
    return """async def test_coordinator_sequential_morning_execution(hass: HomeAssistant) -> None:
    \"\"\"Test sequential execution of morning schedule enforcing 10s interlock pause.\"\"\"
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
            CONF_ZONE_1_SWITCH: "valve.zone_1_valve",
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

    # Set initial switch/valve states
    hass.states.async_set("valve.zone_1_valve", "closed")
    hass.states.async_set(DEFAULT_ZONE_2_SWITCH, "off")

    setup_mock_weather_sensors(hass, temp=20.0, rain_today=0.0, rain_intensity=0.0)

    coordinator = SmartDripCoordinator(hass, entry)
    await coordinator.async_setup()

    # Set water deficits
    coordinator.zone_deficits[1] = 2.0  # ~864s
    coordinator.zone_deficits[2] = 2.0  # ~900s

    calls_turn_on = async_mock_service(hass, "switch", "turn_on")
    calls_turn_off = async_mock_service(hass, "switch", "turn_off")
    calls_open_valve = async_mock_service(hass, "valve", "open_valve")
    calls_close_valve = async_mock_service(hass, "valve", "close_valve")

    # Fast-forward asyncio.sleep (bypassing real wait times)
    with patch("asyncio.sleep", new_callable=AsyncMock):
        await coordinator.async_execute_morning_schedule()

        assert len(calls_turn_on) == 1
        assert len(calls_turn_off) == 1
        assert len(calls_open_valve) == 1
        assert len(calls_close_valve) == 1

        assert calls_open_valve[0].data["entity_id"] == "valve.zone_1_valve"
        assert calls_close_valve[0].data["entity_id"] == "valve.zone_1_valve"
        assert calls_turn_on[0].data["entity_id"] == DEFAULT_ZONE_2_SWITCH
        assert calls_turn_off[0].data["entity_id"] == DEFAULT_ZONE_2_SWITCH

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
        assert coordinator.zone_status[2]["last_run_trigger"] == "automatic_morning_schedule\"\"\"
"""

content = re.sub(
    r"""async def test_coordinator_sequential_morning_execution\(hass: HomeAssistant\) -> None:.*?assert coordinator\.zone_status\[2\]\["last_run_trigger"\] == "automatic_morning_schedule\"""",
    replace_test_coordinator_sequential_morning_execution,
    content,
    flags=re.DOTALL
)

# Test manual zone run and scheduled trigger callbacks for switch and valve
def replace_test_coordinator_manual_run_and_triggers(match):
    return """async def test_coordinator_manual_run_and_triggers(hass: HomeAssistant) -> None:
    \"\"\"Test manual zone run and scheduled trigger callbacks.\"\"\"
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
            CONF_ZONE_2_SWITCH: "valve.zone_2_valve",
            CONF_ZONE_1_AREA: 4.8,
            CONF_ZONE_2_AREA: 5.0,
            CONF_ZONE_1_FLOW_RATE: 40.0,
            CONF_ZONE_2_FLOW_RATE: 40.0,
            CONF_ZONE_1_ENABLED: True,
            CONF_ZONE_2_ENABLED: True,
        },
    )
    entry.add_to_hass(hass)

    coordinator = SmartDripCoordinator(hass, entry)
    await coordinator.async_setup()

    # Test invalid zone raises ValueError
    with pytest.raises(ValueError, match="Invalid zone 3"):
        await coordinator.async_run_zone_manual(3, 100)

    # Test valid manual run on switch
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

    # Test valid manual run on valve
    calls_open = async_mock_service(hass, "valve", "open_valve")
    calls_close = async_mock_service(hass, "valve", "close_valve")
    with patch("asyncio.sleep", new_callable=AsyncMock):
        await coordinator.async_run_zone_manual(2, 200)
        assert len(calls_open) == 1
        assert len(calls_close) == 1
        assert coordinator.zone_status[2]["last_run_timestamp"] is not None
        assert coordinator.zone_status[2]["last_run_duration_seconds"] == 200
        assert coordinator.zone_status[2]["last_run_trigger"] == "manual"
        assert coordinator.zone_status[2]["last_run_liters"] > 0.0

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
    assert len(coordinator._unsub_schedules) == 0"""

content = re.sub(
    r"""async def test_coordinator_manual_run_and_triggers\(hass: HomeAssistant\) -> None:.*?assert len\(coordinator\._unsub_schedules\) == 0""",
    replace_test_coordinator_manual_run_and_triggers,
    content,
    flags=re.DOTALL
)

with open("tests/test_coordinator.py", "w") as f:
    f.write(content.replace('"""""\n', ""))
