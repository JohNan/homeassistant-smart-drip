import re

with open("tests/test_config_flow.py", "r") as f:
    content = f.read()

# Add missing imports for CONF_ZONE_1_SWITCH and CONF_ZONE_2_SWITCH
content = content.replace("CONF_ZONE_1_FLOW_RATE,", "CONF_ZONE_1_FLOW_RATE,\n    CONF_ZONE_1_SWITCH,\n    CONF_ZONE_2_SWITCH,")

# Add some missing fields that are required in the options flow schema
def replace_test_options_flow(match):
    return """@pytest.mark.asyncio
async def test_options_flow(hass: HomeAssistant) -> None:
    \"\"\"Test options flow allows updating zone and bucket parameters.\"\"\"
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Smart Drip",
        data={
            CONF_ZONE_1_AREA: 4.8,
            CONF_ZONE_1_FLOW_RATE: 40.0,
            CONF_ZONE_1_ENABLED: True,
            CONF_ZONE_2_AREA: 5.0,
            CONF_ZONE_2_FLOW_RATE: 40.0,
            CONF_ZONE_2_ENABLED: False,
            CONF_MAX_BUCKET: 24.0,
            CONF_SAFETY_LIMIT: 2700,
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "sensor_temp": "sensor.temp",
            "sensor_humidity": "sensor.humidity",
            "sensor_dewpoint": "sensor.dewpoint",
            "sensor_radiation": "sensor.rad",
            "sensor_wind": "sensor.wind",
            "sensor_pressure": "sensor.pressure",
            "rain_is_rate": False,
            CONF_WEATHER_ENTITY: "weather.custom_forecast",
            CONF_RAIN_TOMORROW_CUTOFF: 8.0,
            CONF_SENSOR_RAIN_TODAY: "sensor.custom_rain_helper",
            CONF_SENSOR_RAIN_INTENSITY: "sensor.custom_rain_rate",
            CONF_ZONE_1_SWITCH: "valve.zone_1_valve",
            CONF_ZONE_2_SWITCH: "valve.zone_2_valve",
            CONF_ZONE_1_AREA: 6.0,
            CONF_ZONE_1_FLOW_RATE: 50.0,
            CONF_ZONE_1_ENABLED: True,
            CONF_ZONE_2_AREA: 8.0,
            CONF_ZONE_2_FLOW_RATE: 60.0,
            CONF_ZONE_2_ENABLED: True,
            CONF_MAX_BUCKET: 30.0,
            CONF_SAFETY_LIMIT: 1800,
        },
    )
    assert result2["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_WEATHER_ENTITY] == "weather.custom_forecast"
    assert entry.options[CONF_RAIN_TOMORROW_CUTOFF] == 8.0
    assert entry.options[CONF_SENSOR_RAIN_TODAY] == "sensor.custom_rain_helper"
    assert entry.options[CONF_ZONE_1_SWITCH] == "valve.zone_1_valve"
    assert entry.options[CONF_ZONE_2_SWITCH] == "valve.zone_2_valve"
    assert entry.options[CONF_ZONE_1_AREA] == 6.0
    assert entry.options[CONF_MAX_BUCKET] == 30.0
"""

content = re.sub(
    r"""@pytest\.mark\.asyncio\nasync def test_options_flow\(hass: HomeAssistant\) -> None:.*?assert entry\.options\[CONF_MAX_BUCKET\] == 30\.0\n""",
    replace_test_options_flow,
    content,
    flags=re.DOTALL
)

with open("tests/test_config_flow.py", "w") as f:
    f.write(content)
