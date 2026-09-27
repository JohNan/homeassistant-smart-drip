"""Config flow for Smart Drip Irrigation integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithConfigEntry,
)
from homeassistant.core import callback
from homeassistant.helpers.storage import Store

from .const import (
    CONF_MAX_BUCKET,
    CONF_RAIN_IS_RATE,
    CONF_RAIN_TOMORROW_CUTOFF,
    CONF_RESET_STORAGE,
    CONF_SAFETY_LIMIT,
    CONF_SENSOR_DEWPOINT,
    CONF_SENSOR_HUMIDITY,
    CONF_SENSOR_PRESSURE,
    CONF_SENSOR_RADIATION,
    CONF_SENSOR_RAIN_INTENSITY,
    CONF_SENSOR_RAIN_TODAY,
    CONF_SENSOR_TEMP,
    CONF_SENSOR_WIND,
    CONF_WEATHER_ENTITY,
    CONF_ZONE_1_AREA,
    CONF_ZONE_1_ENABLED,
    CONF_ZONE_1_FLOW_RATE,
    CONF_ZONE_1_SWITCH,
    CONF_ZONE_2_AREA,
    CONF_ZONE_2_ENABLED,
    CONF_ZONE_2_FLOW_RATE,
    CONF_ZONE_2_SWITCH,
    DEFAULT_MAX_BUCKET_MM,
    DEFAULT_RAIN_IS_RATE,
    DEFAULT_RAIN_TOMORROW_CUTOFF_MM,
    DEFAULT_SAFETY_LIMIT_SECONDS,
    DEFAULT_SENSOR_DEWPOINT,
    DEFAULT_SENSOR_HUMIDITY,
    DEFAULT_SENSOR_PRESSURE,
    DEFAULT_SENSOR_RADIATION,
    DEFAULT_SENSOR_RAIN_INTENSITY,
    DEFAULT_SENSOR_RAIN_TODAY,
    DEFAULT_SENSOR_TEMP,
    DEFAULT_SENSOR_WIND,
    DEFAULT_WEATHER_ENTITY,
    DEFAULT_ZONE_1_AREA_M2,
    DEFAULT_ZONE_1_FLOW_RATE_L_H,
    DEFAULT_ZONE_1_SWITCH,
    DEFAULT_ZONE_2_AREA_M2,
    DEFAULT_ZONE_2_FLOW_RATE_L_H,
    DEFAULT_ZONE_2_SWITCH,
    DOMAIN,
    STORAGE_KEY,
    STORAGE_VERSION,
)


class SmartDripConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Smart Drip Irrigation."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        store = Store[dict[str, Any]](self.hass, STORAGE_VERSION, STORAGE_KEY)

        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()

            reset_storage = user_input.pop(CONF_RESET_STORAGE, False)
            if reset_storage:
                await store.async_remove()

            return self.async_create_entry(
                title="Smart Drip Irrigation",
                data=user_input,
            )

        stored = await store.async_load()
        has_existing_storage = stored is not None

        schema_dict: dict[Any, Any] = {
            vol.Required(CONF_SENSOR_TEMP, default=DEFAULT_SENSOR_TEMP): str,
            vol.Required(CONF_SENSOR_HUMIDITY, default=DEFAULT_SENSOR_HUMIDITY): str,
            vol.Required(CONF_SENSOR_DEWPOINT, default=DEFAULT_SENSOR_DEWPOINT): str,
            vol.Required(CONF_SENSOR_RADIATION, default=DEFAULT_SENSOR_RADIATION): str,
            vol.Required(CONF_SENSOR_WIND, default=DEFAULT_SENSOR_WIND): str,
            vol.Required(CONF_SENSOR_PRESSURE, default=DEFAULT_SENSOR_PRESSURE): str,
            vol.Required(CONF_SENSOR_RAIN_TODAY, default=DEFAULT_SENSOR_RAIN_TODAY): str,
            vol.Required(CONF_SENSOR_RAIN_INTENSITY, default=DEFAULT_SENSOR_RAIN_INTENSITY): str,
            vol.Required(CONF_RAIN_IS_RATE, default=DEFAULT_RAIN_IS_RATE): bool,
            vol.Optional(CONF_WEATHER_ENTITY, default=DEFAULT_WEATHER_ENTITY): str,
            vol.Optional(
                CONF_RAIN_TOMORROW_CUTOFF, default=DEFAULT_RAIN_TOMORROW_CUTOFF_MM
            ): vol.Coerce(float),
            vol.Required(CONF_ZONE_1_SWITCH, default=DEFAULT_ZONE_1_SWITCH): str,
            vol.Required(CONF_ZONE_1_AREA, default=DEFAULT_ZONE_1_AREA_M2): vol.Coerce(float),
            vol.Required(CONF_ZONE_1_FLOW_RATE, default=DEFAULT_ZONE_1_FLOW_RATE_L_H): vol.Coerce(
                float
            ),
            vol.Required(CONF_ZONE_1_ENABLED, default=True): bool,
            vol.Required(CONF_ZONE_2_SWITCH, default=DEFAULT_ZONE_2_SWITCH): str,
            vol.Required(CONF_ZONE_2_AREA, default=DEFAULT_ZONE_2_AREA_M2): vol.Coerce(float),
            vol.Required(CONF_ZONE_2_FLOW_RATE, default=DEFAULT_ZONE_2_FLOW_RATE_L_H): vol.Coerce(
                float
            ),
            vol.Required(CONF_ZONE_2_ENABLED, default=False): bool,
            vol.Required(CONF_MAX_BUCKET, default=DEFAULT_MAX_BUCKET_MM): vol.Coerce(float),
            vol.Required(CONF_SAFETY_LIMIT, default=DEFAULT_SAFETY_LIMIT_SECONDS): vol.Coerce(int),
        }

        if has_existing_storage:
            schema_dict[vol.Optional(CONF_RESET_STORAGE, default=False)] = bool

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> SmartDripOptionsFlowHandler:
        """Get the options flow for this handler."""
        return SmartDripOptionsFlowHandler(config_entry)


class SmartDripOptionsFlowHandler(OptionsFlowWithConfigEntry):
    """Handle options for Smart Drip."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        super().__init__(config_entry)

    def _get_val(self, key: str, default: Any) -> Any:
        """Get option value with fallback to config entry data."""
        if self.config_entry.options and key in self.config_entry.options:
            return self.config_entry.options[key]
        if self.config_entry.data and key in self.config_entry.data:
            return self.config_entry.data[key]
        return default

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options_schema = vol.Schema(
            {
                vol.Required(
                    CONF_SENSOR_RAIN_TODAY,
                    default=str(self._get_val(CONF_SENSOR_RAIN_TODAY, DEFAULT_SENSOR_RAIN_TODAY)),
                ): str,
                vol.Required(
                    CONF_SENSOR_RAIN_INTENSITY,
                    default=str(
                        self._get_val(CONF_SENSOR_RAIN_INTENSITY, DEFAULT_SENSOR_RAIN_INTENSITY)
                    ),
                ): str,
                vol.Required(
                    CONF_RAIN_IS_RATE,
                    default=bool(self._get_val(CONF_RAIN_IS_RATE, DEFAULT_RAIN_IS_RATE)),
                ): bool,
                vol.Optional(
                    CONF_WEATHER_ENTITY,
                    default=str(self._get_val(CONF_WEATHER_ENTITY, DEFAULT_WEATHER_ENTITY)),
                ): str,
                vol.Optional(
                    CONF_RAIN_TOMORROW_CUTOFF,
                    default=float(
                        self._get_val(CONF_RAIN_TOMORROW_CUTOFF, DEFAULT_RAIN_TOMORROW_CUTOFF_MM)
                    ),
                ): vol.Coerce(float),
                vol.Required(
                    CONF_ZONE_1_AREA,
                    default=float(self._get_val(CONF_ZONE_1_AREA, DEFAULT_ZONE_1_AREA_M2)),
                ): vol.Coerce(float),
                vol.Required(
                    CONF_ZONE_1_FLOW_RATE,
                    default=float(
                        self._get_val(CONF_ZONE_1_FLOW_RATE, DEFAULT_ZONE_1_FLOW_RATE_L_H)
                    ),
                ): vol.Coerce(float),
                vol.Required(
                    CONF_ZONE_1_ENABLED,
                    default=bool(self._get_val(CONF_ZONE_1_ENABLED, True)),
                ): bool,
                vol.Required(
                    CONF_ZONE_2_AREA,
                    default=float(self._get_val(CONF_ZONE_2_AREA, DEFAULT_ZONE_2_AREA_M2)),
                ): vol.Coerce(float),
                vol.Required(
                    CONF_ZONE_2_FLOW_RATE,
                    default=float(
                        self._get_val(CONF_ZONE_2_FLOW_RATE, DEFAULT_ZONE_2_FLOW_RATE_L_H)
                    ),
                ): vol.Coerce(float),
                vol.Required(
                    CONF_ZONE_2_ENABLED,
                    default=bool(self._get_val(CONF_ZONE_2_ENABLED, False)),
                ): bool,
                vol.Required(
                    CONF_MAX_BUCKET,
                    default=float(self._get_val(CONF_MAX_BUCKET, DEFAULT_MAX_BUCKET_MM)),
                ): vol.Coerce(float),
                vol.Required(
                    CONF_SAFETY_LIMIT,
                    default=int(self._get_val(CONF_SAFETY_LIMIT, DEFAULT_SAFETY_LIMIT_SECONDS)),
                ): vol.Coerce(int),
            }
        )

        return self.async_show_form(step_id="init", data_schema=options_schema)
