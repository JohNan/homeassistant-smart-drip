"""Constants for the Smart Drip Irrigation integration."""

from typing import Final

DOMAIN: Final = "smart_drip"

# Platform definitions
PLATFORMS: Final = ["sensor", "switch", "button"]

# Configuration keys
CONF_WEATHER_ENTITY_PREFIX: Final = "weather_entity_prefix"
CONF_ZONE_1_SWITCH: Final = "zone_1_switch"
CONF_ZONE_2_SWITCH: Final = "zone_2_switch"
CONF_ZONE_1_AREA: Final = "zone_1_area"
CONF_ZONE_2_AREA: Final = "zone_2_area"
CONF_ZONE_1_FLOW_RATE: Final = "zone_1_flow_rate"
CONF_ZONE_2_FLOW_RATE: Final = "zone_2_flow_rate"
CONF_ZONE_1_ENABLED: Final = "zone_1_enabled"
CONF_ZONE_2_ENABLED: Final = "zone_2_enabled"
CONF_MAX_BUCKET: Final = "max_bucket"
CONF_SAFETY_LIMIT: Final = "safety_limit"

# Sensor entities for Tempest WeatherFlow (Swedish entity defaults)
CONF_SENSOR_TEMP: Final = "sensor_temp"
CONF_SENSOR_HUMIDITY: Final = "sensor_humidity"
CONF_SENSOR_DEWPOINT: Final = "sensor_dewpoint"
CONF_SENSOR_RADIATION: Final = "sensor_radiation"
CONF_SENSOR_WIND: Final = "sensor_wind"
CONF_SENSOR_PRESSURE: Final = "sensor_pressure"
CONF_SENSOR_RAIN_TODAY: Final = "sensor_rain_today"
CONF_SENSOR_RAIN_INTENSITY: Final = "sensor_rain_intensity"
CONF_RAIN_IS_RATE: Final = "rain_is_rate"
CONF_WEATHER_ENTITY: Final = "weather_entity"
CONF_RAIN_TOMORROW_CUTOFF: Final = "rain_tomorrow_cutoff"

DEFAULT_RAIN_IS_RATE: Final = True
DEFAULT_WEATHER_ENTITY: Final = "weather.smhi_home"
DEFAULT_RAIN_TOMORROW_CUTOFF_MM: Final = 5.0
DEFAULT_SENSOR_TEMP: Final = "sensor.vaderstation_temperatur"
DEFAULT_SENSOR_HUMIDITY: Final = "sensor.vaderstation_luftfuktighet"
DEFAULT_SENSOR_DEWPOINT: Final = "sensor.vaderstation_daggpunkt"
DEFAULT_SENSOR_RADIATION: Final = "sensor.vaderstation_stralning"
DEFAULT_SENSOR_WIND: Final = "sensor.vaderstation_vindhastighet"
DEFAULT_SENSOR_PRESSURE: Final = "sensor.vaderstation_lufttryck"
DEFAULT_SENSOR_RAIN_TODAY: Final = "sensor.vaderstation_nederbord"
DEFAULT_SENSOR_RAIN_INTENSITY: Final = "sensor.vaderstation_nederbordsintensitet"

DEFAULT_ZONE_1_SWITCH: Final = "switch.sonoff_water_valve_channel_1"
DEFAULT_ZONE_2_SWITCH: Final = "switch.sonoff_water_valve_channel_2"

# Default physical values
DEFAULT_ZONE_1_NAME: Final = "Stora rabatten"
DEFAULT_ZONE_2_NAME: Final = "Zon 2"
DEFAULT_ZONE_1_AREA_M2: Final = 4.8
DEFAULT_ZONE_2_AREA_M2: Final = 5.0
DEFAULT_ZONE_1_FLOW_RATE_L_H: Final = 40.0
DEFAULT_ZONE_2_FLOW_RATE_L_H: Final = 40.0
DEFAULT_MAX_BUCKET_MM: Final = 24.0
DEFAULT_SAFETY_LIMIT_SECONDS: Final = 2700  # 45 minutes
HARD_SAFETY_LIMIT_SECONDS: Final = 3600  # 60 minutes
INTERLOCK_DELAY_SECONDS: Final = 10  # 10s idle interlock

# Skip thresholds
DEFAULT_RAIN_TODAY_CUTOFF_MM: Final = 2.5
DEFAULT_YESTERDAY_RAIN_CUTOFF_MM: Final = 10.0
DEFAULT_TEMP_CUTOFF_C: Final = 4.0
DEFAULT_MIN_DEFICIT_TRIGGER_MM: Final = 1.0

# Decision states
STATUS_READY: Final = "Ready"
STATUS_RUNNING: Final = "Running"
STATUS_SKIPPED_ACTIVE_RAIN: Final = "Skipped: Active Rain"
STATUS_SKIPPED_DAILY_RAIN_EXCEEDED: Final = "Skipped: Daily Rain Exceeded"
STATUS_SKIPPED_YESTERDAY_HEAVY_SOAK: Final = "Skipped: Yesterday Heavy Soak"
STATUS_SKIPPED_RAIN_TOMORROW: Final = "Skipped: Rain Forecast Tomorrow"
STATUS_SKIPPED_ZERO_DEFICIT: Final = "Skipped: Zero Deficit"
STATUS_SKIPPED_LOW_TEMP: Final = "Skipped: Low Temperature"
STATUS_SKIPPED_ZONE_DISABLED: Final = "Skipped: Zone Disabled"
STATUS_IDLE: Final = "Idle"

# Services
SERVICE_CALCULATE_NOW: Final = "calculate_now"
SERVICE_RESET_BUCKET: Final = "reset_bucket"
SERVICE_RUN_ZONE: Final = "run_zone"

# Storage
STORAGE_VERSION: Final = 1
STORAGE_KEY: Final = "smart_drip"
CONF_RESET_STORAGE: Final = "reset_storage"
