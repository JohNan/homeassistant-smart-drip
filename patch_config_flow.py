import re

with open("custom_components/smart_drip/config_flow.py", "r") as f:
    content = f.read()

# Add selector import
content = content.replace("from homeassistant.helpers.storage import Store", "from homeassistant.helpers.storage import Store\nfrom homeassistant.helpers import selector")

# Replace config flow user schema
schema_user = """        schema_dict: dict[Any, Any] = {
            vol.Required(CONF_SENSOR_TEMP, default=DEFAULT_SENSOR_TEMP): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
            vol.Required(CONF_SENSOR_HUMIDITY, default=DEFAULT_SENSOR_HUMIDITY): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
            vol.Required(CONF_SENSOR_DEWPOINT, default=DEFAULT_SENSOR_DEWPOINT): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
            vol.Required(CONF_SENSOR_RADIATION, default=DEFAULT_SENSOR_RADIATION): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
            vol.Required(CONF_SENSOR_WIND, default=DEFAULT_SENSOR_WIND): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
            vol.Required(CONF_SENSOR_PRESSURE, default=DEFAULT_SENSOR_PRESSURE): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
            vol.Required(CONF_SENSOR_RAIN_TODAY, default=DEFAULT_SENSOR_RAIN_TODAY): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
            vol.Required(CONF_SENSOR_RAIN_INTENSITY, default=DEFAULT_SENSOR_RAIN_INTENSITY): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
            vol.Required(CONF_RAIN_IS_RATE, default=DEFAULT_RAIN_IS_RATE): selector.BooleanSelector(),
            vol.Optional(CONF_WEATHER_ENTITY, default=DEFAULT_WEATHER_ENTITY): selector.EntitySelector(selector.EntitySelectorConfig(domain="weather")),
            vol.Optional(
                CONF_RAIN_TOMORROW_CUTOFF, default=DEFAULT_RAIN_TOMORROW_CUTOFF_MM
            ): selector.NumberSelector(selector.NumberSelectorConfig(mode=selector.NumberSelectorMode.BOX, step="any")),
            vol.Required(CONF_ZONE_1_SWITCH, default=DEFAULT_ZONE_1_SWITCH): selector.EntitySelector(selector.EntitySelectorConfig(domain=["switch", "valve"])),
            vol.Required(CONF_ZONE_1_AREA, default=DEFAULT_ZONE_1_AREA_M2): selector.NumberSelector(selector.NumberSelectorConfig(mode=selector.NumberSelectorMode.BOX, step="any")),
            vol.Required(CONF_ZONE_1_FLOW_RATE, default=DEFAULT_ZONE_1_FLOW_RATE_L_H): selector.NumberSelector(selector.NumberSelectorConfig(mode=selector.NumberSelectorMode.BOX, step="any")),
            vol.Required(CONF_ZONE_1_ENABLED, default=True): selector.BooleanSelector(),
            vol.Required(CONF_ZONE_2_SWITCH, default=DEFAULT_ZONE_2_SWITCH): selector.EntitySelector(selector.EntitySelectorConfig(domain=["switch", "valve"])),
            vol.Required(CONF_ZONE_2_AREA, default=DEFAULT_ZONE_2_AREA_M2): selector.NumberSelector(selector.NumberSelectorConfig(mode=selector.NumberSelectorMode.BOX, step="any")),
            vol.Required(CONF_ZONE_2_FLOW_RATE, default=DEFAULT_ZONE_2_FLOW_RATE_L_H): selector.NumberSelector(selector.NumberSelectorConfig(mode=selector.NumberSelectorMode.BOX, step="any")),
            vol.Required(CONF_ZONE_2_ENABLED, default=False): selector.BooleanSelector(),
            vol.Required(CONF_MAX_BUCKET, default=DEFAULT_MAX_BUCKET_MM): selector.NumberSelector(selector.NumberSelectorConfig(mode=selector.NumberSelectorMode.BOX, step="any")),
            vol.Required(CONF_SAFETY_LIMIT, default=DEFAULT_SAFETY_LIMIT_SECONDS): selector.NumberSelector(selector.NumberSelectorConfig(mode=selector.NumberSelectorMode.BOX, step=1)),
        }"""

content = re.sub(r"        schema_dict: dict\[Any, Any\] = {.*?vol\.Required\(CONF_SAFETY_LIMIT.*?\}", schema_user, content, flags=re.DOTALL)

schema_options = """        options_schema = vol.Schema(
            {
                vol.Required(
                    CONF_SENSOR_TEMP, default=str(self._get_val(CONF_SENSOR_TEMP, DEFAULT_SENSOR_TEMP))
                ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
                vol.Required(
                    CONF_SENSOR_HUMIDITY, default=str(self._get_val(CONF_SENSOR_HUMIDITY, DEFAULT_SENSOR_HUMIDITY))
                ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
                vol.Required(
                    CONF_SENSOR_DEWPOINT, default=str(self._get_val(CONF_SENSOR_DEWPOINT, DEFAULT_SENSOR_DEWPOINT))
                ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
                vol.Required(
                    CONF_SENSOR_RADIATION, default=str(self._get_val(CONF_SENSOR_RADIATION, DEFAULT_SENSOR_RADIATION))
                ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
                vol.Required(
                    CONF_SENSOR_WIND, default=str(self._get_val(CONF_SENSOR_WIND, DEFAULT_SENSOR_WIND))
                ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
                vol.Required(
                    CONF_SENSOR_PRESSURE, default=str(self._get_val(CONF_SENSOR_PRESSURE, DEFAULT_SENSOR_PRESSURE))
                ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
                vol.Required(
                    CONF_SENSOR_RAIN_TODAY,
                    default=str(self._get_val(CONF_SENSOR_RAIN_TODAY, DEFAULT_SENSOR_RAIN_TODAY)),
                ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
                vol.Required(
                    CONF_SENSOR_RAIN_INTENSITY,
                    default=str(
                        self._get_val(CONF_SENSOR_RAIN_INTENSITY, DEFAULT_SENSOR_RAIN_INTENSITY)
                    ),
                ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
                vol.Required(
                    CONF_RAIN_IS_RATE,
                    default=bool(self._get_val(CONF_RAIN_IS_RATE, DEFAULT_RAIN_IS_RATE)),
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_WEATHER_ENTITY,
                    default=str(self._get_val(CONF_WEATHER_ENTITY, DEFAULT_WEATHER_ENTITY)),
                ): selector.EntitySelector(selector.EntitySelectorConfig(domain="weather")),
                vol.Optional(
                    CONF_RAIN_TOMORROW_CUTOFF,
                    default=float(
                        self._get_val(CONF_RAIN_TOMORROW_CUTOFF, DEFAULT_RAIN_TOMORROW_CUTOFF_MM)
                    ),
                ): selector.NumberSelector(selector.NumberSelectorConfig(mode=selector.NumberSelectorMode.BOX, step="any")),
                vol.Required(
                    CONF_ZONE_1_SWITCH, default=str(self._get_val(CONF_ZONE_1_SWITCH, DEFAULT_ZONE_1_SWITCH))
                ): selector.EntitySelector(selector.EntitySelectorConfig(domain=["switch", "valve"])),
                vol.Required(
                    CONF_ZONE_1_AREA,
                    default=float(self._get_val(CONF_ZONE_1_AREA, DEFAULT_ZONE_1_AREA_M2)),
                ): selector.NumberSelector(selector.NumberSelectorConfig(mode=selector.NumberSelectorMode.BOX, step="any")),
                vol.Required(
                    CONF_ZONE_1_FLOW_RATE,
                    default=float(
                        self._get_val(CONF_ZONE_1_FLOW_RATE, DEFAULT_ZONE_1_FLOW_RATE_L_H)
                    ),
                ): selector.NumberSelector(selector.NumberSelectorConfig(mode=selector.NumberSelectorMode.BOX, step="any")),
                vol.Required(
                    CONF_ZONE_1_ENABLED,
                    default=bool(self._get_val(CONF_ZONE_1_ENABLED, True)),
                ): selector.BooleanSelector(),
                vol.Required(
                    CONF_ZONE_2_SWITCH, default=str(self._get_val(CONF_ZONE_2_SWITCH, DEFAULT_ZONE_2_SWITCH))
                ): selector.EntitySelector(selector.EntitySelectorConfig(domain=["switch", "valve"])),
                vol.Required(
                    CONF_ZONE_2_AREA,
                    default=float(self._get_val(CONF_ZONE_2_AREA, DEFAULT_ZONE_2_AREA_M2)),
                ): selector.NumberSelector(selector.NumberSelectorConfig(mode=selector.NumberSelectorMode.BOX, step="any")),
                vol.Required(
                    CONF_ZONE_2_FLOW_RATE,
                    default=float(
                        self._get_val(CONF_ZONE_2_FLOW_RATE, DEFAULT_ZONE_2_FLOW_RATE_L_H)
                    ),
                ): selector.NumberSelector(selector.NumberSelectorConfig(mode=selector.NumberSelectorMode.BOX, step="any")),
                vol.Required(
                    CONF_ZONE_2_ENABLED,
                    default=bool(self._get_val(CONF_ZONE_2_ENABLED, False)),
                ): selector.BooleanSelector(),
                vol.Required(
                    CONF_MAX_BUCKET,
                    default=float(self._get_val(CONF_MAX_BUCKET, DEFAULT_MAX_BUCKET_MM)),
                ): selector.NumberSelector(selector.NumberSelectorConfig(mode=selector.NumberSelectorMode.BOX, step="any")),
                vol.Required(
                    CONF_SAFETY_LIMIT,
                    default=int(self._get_val(CONF_SAFETY_LIMIT, DEFAULT_SAFETY_LIMIT_SECONDS)),
                ): selector.NumberSelector(selector.NumberSelectorConfig(mode=selector.NumberSelectorMode.BOX, step=1)),
            }
        )"""

content = re.sub(r"        options_schema = vol\.Schema\(.*?vol\.Required\(\n                    CONF_SAFETY_LIMIT,.*?\}\n        \)", schema_options, content, flags=re.DOTALL)

with open("custom_components/smart_drip/config_flow.py", "w") as f:
    f.write(content)
