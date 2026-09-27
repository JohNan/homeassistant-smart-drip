from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import data_entry_flow
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smart_drip.const import (
    CONF_MAX_BUCKET,
    CONF_RAIN_TOMORROW_CUTOFF,
    CONF_RESET_STORAGE,
    CONF_SAFETY_LIMIT,
    CONF_SENSOR_RAIN_INTENSITY,
    CONF_SENSOR_RAIN_TODAY,
    CONF_WEATHER_ENTITY,
    CONF_ZONE_1_AREA,
    CONF_ZONE_1_ENABLED,
    CONF_ZONE_1_FLOW_RATE,
    CONF_ZONE_2_AREA,
    CONF_ZONE_2_ENABLED,
    CONF_ZONE_2_FLOW_RATE,
    DOMAIN,
)


@pytest.mark.asyncio
async def test_config_flow_user_step(hass: HomeAssistant) -> None:
    """Test standard user flow initializes entry."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"

    # Fill form with valid data
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
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
    assert result2["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Smart Drip Irrigation"
    assert result2["data"][CONF_ZONE_1_AREA] == 4.8


@pytest.mark.asyncio
async def test_options_flow(hass: HomeAssistant) -> None:
    """Test options flow allows updating zone and bucket parameters."""
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
            CONF_WEATHER_ENTITY: "weather.custom_forecast",
            CONF_RAIN_TOMORROW_CUTOFF: 8.0,
            CONF_SENSOR_RAIN_TODAY: "sensor.custom_rain_helper",
            CONF_SENSOR_RAIN_INTENSITY: "sensor.custom_rain_rate",
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
    assert entry.options[CONF_ZONE_1_AREA] == 6.0
    assert entry.options[CONF_MAX_BUCKET] == 30.0


@pytest.mark.asyncio
async def test_config_flow_detects_existing_storage_and_allows_reset(
    hass: HomeAssistant,
) -> None:
    """Test user flow detects existing storage and erases it when requested."""
    with (
        patch.object(Store, "async_load", new_callable=AsyncMock, return_value={"stored": "data"}),
        patch.object(Store, "async_remove", new_callable=AsyncMock) as mock_remove,
    ):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        assert result["type"] == data_entry_flow.FlowResultType.FORM
        schema_keys = [
            k.schema if hasattr(k, "schema") else str(k) for k in result["data_schema"].schema
        ]
        assert CONF_RESET_STORAGE in schema_keys

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_ZONE_1_AREA: 4.8,
                CONF_ZONE_1_FLOW_RATE: 40.0,
                CONF_ZONE_1_ENABLED: True,
                CONF_ZONE_2_AREA: 5.0,
                CONF_ZONE_2_FLOW_RATE: 40.0,
                CONF_ZONE_2_ENABLED: False,
                CONF_MAX_BUCKET: 24.0,
                CONF_SAFETY_LIMIT: 2700,
                CONF_RESET_STORAGE: True,
            },
        )
        assert result2["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        mock_remove.assert_awaited_once()
        assert CONF_RESET_STORAGE not in result2["data"]


@pytest.mark.asyncio
async def test_config_flow_detects_existing_storage_and_preserves_it(
    hass: HomeAssistant,
) -> None:
    """Test user flow preserves existing storage when reset is unchecked."""
    with (
        patch.object(Store, "async_load", new_callable=AsyncMock, return_value={"stored": "data"}),
        patch.object(Store, "async_remove", new_callable=AsyncMock) as mock_remove,
    ):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        assert result["type"] == data_entry_flow.FlowResultType.FORM

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_ZONE_1_AREA: 4.8,
                CONF_ZONE_1_FLOW_RATE: 40.0,
                CONF_ZONE_1_ENABLED: True,
                CONF_ZONE_2_AREA: 5.0,
                CONF_ZONE_2_FLOW_RATE: 40.0,
                CONF_ZONE_2_ENABLED: False,
                CONF_MAX_BUCKET: 24.0,
                CONF_SAFETY_LIMIT: 2700,
                CONF_RESET_STORAGE: False,
            },
        )
        assert result2["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        mock_remove.assert_not_called()
