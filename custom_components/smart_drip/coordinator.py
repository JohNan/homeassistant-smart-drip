"""DataUpdateCoordinator for smart_drip."""

from __future__ import annotations

import logging
from contextlib import suppress
from datetime import datetime, timedelta
from typing import Any, Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, Event, EventStateChangedData, HomeAssistant
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .calc import (
    calculate_deficit,
    calculate_et0,
    calculate_precipitation_rate,
    calculate_runtime_seconds,
    evaluate_irrigation_decision,
    integrate_state_history,
    integrate_trapezoidal_rain,
)
from .const import (
    CONF_MAX_BUCKET,
    CONF_RAIN_IS_RATE,
    CONF_SAFETY_LIMIT,
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
    DEFAULT_MAX_BUCKET_MM,
    DEFAULT_RAIN_IS_RATE,
    DEFAULT_SAFETY_LIMIT_SECONDS,
    DEFAULT_SENSOR_DEWPOINT,
    DEFAULT_SENSOR_HUMIDITY,
    DEFAULT_SENSOR_PRESSURE,
    DEFAULT_SENSOR_RADIATION,
    DEFAULT_SENSOR_RAIN_INTENSITY,
    DEFAULT_SENSOR_RAIN_TODAY,
    DEFAULT_SENSOR_TEMP,
    DEFAULT_SENSOR_WIND,
    DEFAULT_ZONE_1_AREA_M2,
    DEFAULT_ZONE_1_FLOW_RATE_L_H,
    DEFAULT_ZONE_1_SWITCH,
    DEFAULT_ZONE_2_AREA_M2,
    DEFAULT_ZONE_2_FLOW_RATE_L_H,
    DEFAULT_ZONE_2_SWITCH,
    DOMAIN,
    INTERLOCK_DELAY_SECONDS,
    STATUS_IDLE,
    STATUS_READY,
    STATUS_RUNNING,
    STORAGE_KEY,
    STORAGE_VERSION,
)
from .interlock import SolenoidInterlock

_LOGGER: Final = logging.getLogger(__name__)


class SmartDripCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator handling weather telemetry, ET0 calculations, and valve sequencing."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
        )
        self.entry = entry
        self.interlock = SolenoidInterlock(
            interlock_delay=INTERLOCK_DELAY_SECONDS,
            max_duration_seconds=self._get_conf(CONF_SAFETY_LIMIT, DEFAULT_SAFETY_LIMIT_SECONDS),
        )
        self._store: Store[dict[str, Any]] = Store(
            hass,
            STORAGE_VERSION,
            f"{STORAGE_KEY}.{entry.entry_id}",
        )

        self.last_et0: float = 0.0
        self.yesterday_rain: float = 0.0
        self.rain_today: float = 0.0
        self.rain_today_date: str = dt_util.now().date().isoformat()
        self._last_rain_rate: float | None = None
        self._last_rain_rate_timestamp: datetime | None = None
        self.zone_deficits: dict[int, float] = {1: 0.0, 2: 0.0}
        self.zone_status: dict[int, dict[str, Any]] = {
            1: self._initial_zone_status(1),
            2: self._initial_zone_status(2),
        }
        self._unsub_schedules: list[CALLBACK_TYPE] = []

    def _initial_zone_status(self, zone: int) -> dict[str, Any]:
        """Return the initial zone decision state structure."""
        return {
            "state": STATUS_IDLE,
            "reason": "Initialized; awaiting first evaluation cycle.",
            "target_duration_seconds": 0,
            "estimated_liters": 0.0,
            "last_run_timestamp": None,
        }

    def _get_conf(self, key: str, default: Any) -> Any:
        """Retrieve config value from options or data."""
        if self.entry.options and key in self.entry.options:
            return self.entry.options[key]
        if self.entry.data and key in self.entry.data:
            return self.entry.data[key]
        return default

    def _get_float_state(self, entity_id: str, default: float = 0.0) -> float:
        """Helper to get a numeric state safely from Home Assistant."""
        state = self.hass.states.get(entity_id)
        if state is None or state.state in ("unknown", "unavailable"):
            return default
        try:
            return float(str(state.state).replace(",", ".").strip())
        except (ValueError, TypeError):
            return default

    async def async_setup(self) -> None:
        """Setup persistent storage, time listeners, and initial state evaluation."""
        await self._async_load_or_backfill_state()

        # Midnight rollover at 00:00:00 to reset daily rain accumulator
        unsub_midnight = async_track_time_change(
            self.hass,
            self._handle_midnight_rollover,
            hour=0,
            minute=0,
            second=0,
        )
        self._unsub_schedules.append(unsub_midnight)

        # Daily ET0 computation at 23:00:00
        unsub_et0 = async_track_time_change(
            self.hass,
            self._handle_nightly_et0_trigger,
            hour=23,
            minute=0,
            second=0,
        )
        self._unsub_schedules.append(unsub_et0)

        # Morning irrigation sequence at 06:00:00
        unsub_morning = async_track_time_change(
            self.hass,
            self._handle_morning_irrigation_trigger,
            hour=6,
            minute=0,
            second=0,
        )
        self._unsub_schedules.append(unsub_morning)

        # Initialize live rain rate tracker
        rain_entity = self._get_conf(CONF_SENSOR_RAIN_TODAY, DEFAULT_SENSOR_RAIN_TODAY)
        self._last_rain_rate = self._get_float_state(rain_entity, 0.0)
        self._last_rain_rate_timestamp = dt_util.now()

        # Dynamic state change tracking for weather telemetry
        weather_entities = [
            self._get_conf(CONF_SENSOR_RAIN_TODAY, DEFAULT_SENSOR_RAIN_TODAY),
            self._get_conf(CONF_SENSOR_RAIN_INTENSITY, DEFAULT_SENSOR_RAIN_INTENSITY),
            self._get_conf(CONF_SENSOR_TEMP, DEFAULT_SENSOR_TEMP),
        ]
        valid_weather_entities = [e for e in weather_entities if isinstance(e, str) and e]
        if valid_weather_entities:
            unsub_weather = async_track_state_change_event(
                self.hass,
                valid_weather_entities,
                self._handle_weather_state_change,
            )
            self._unsub_schedules.append(unsub_weather)

        # Initial zone status evaluation
        await self.async_evaluate_zones()

    async def _handle_midnight_rollover(self, _now: datetime) -> None:
        """Scheduled callback at 00:00 midnight to roll over daily rainfall accumulator."""
        _LOGGER.info("Executing scheduled midnight rollover: resetting daily rain.")
        self.yesterday_rain = round(self.rain_today, 2)
        self.rain_today = 0.0
        self.rain_today_date = dt_util.now().date().isoformat()
        self._last_rain_rate_timestamp = dt_util.now()
        await self.async_evaluate_zones()
        self.async_set_updated_data(self._build_coordinator_data())
        await self.async_save_state()

    async def _handle_weather_state_change(self, event: Event[EventStateChangedData]) -> None:
        """Handle dynamic state change in weather telemetry sensors."""
        entity_id = event.data.get("entity_id")
        rain_entity = self._get_conf(CONF_SENSOR_RAIN_TODAY, DEFAULT_SENSOR_RAIN_TODAY)
        rain_is_rate = bool(self._get_conf(CONF_RAIN_IS_RATE, DEFAULT_RAIN_IS_RATE))

        if entity_id == rain_entity and rain_is_rate:
            curr_rate = self._get_float_state(rain_entity, 0.0)
            now = dt_util.now()
            if self._last_rain_rate is not None and self._last_rain_rate_timestamp is not None:
                dt_sec = (now - self._last_rain_rate_timestamp).total_seconds()
                if 0 < dt_sec <= 3600:
                    d_rain = integrate_trapezoidal_rain(self._last_rain_rate, curr_rate, dt_sec)
                    if d_rain > 0.0:
                        self.rain_today = round(self.rain_today + d_rain, 2)
            self._last_rain_rate = curr_rate
            self._last_rain_rate_timestamp = now

        _LOGGER.debug("Weather telemetry changed for %s; re-evaluating zones.", entity_id)
        await self.async_evaluate_zones()

    async def _async_load_or_backfill_state(self) -> None:
        """Load persisted state from storage or backfill from recorder on cold start."""
        stored = await self._store.async_load()
        if stored:
            _LOGGER.debug("Restoring persisted Smart Drip state from storage.")
            self.last_et0 = float(stored.get("last_et0", 0.0))
            self.yesterday_rain = float(stored.get("yesterday_rain", 0.0))
            stored_date = stored.get("rain_today_date")
            today_str = dt_util.now().date().isoformat()
            yesterday_str = (dt_util.now().date() - timedelta(days=1)).isoformat()

            if stored_date == today_str:
                self.rain_today = float(stored.get("rain_today", 0.0))
                self.rain_today_date = today_str
            elif stored_date == yesterday_str:
                self.yesterday_rain = float(stored.get("rain_today", 0.0))
                self.rain_today = 0.0
                self.rain_today_date = today_str
            else:
                self.rain_today = 0.0
                self.rain_today_date = today_str

            if "zone_deficits" in stored and isinstance(stored["zone_deficits"], dict):
                for k, v in stored["zone_deficits"].items():
                    with suppress(ValueError, TypeError):
                        self.zone_deficits[int(k)] = float(v)
            if "zone_status" in stored and isinstance(stored["zone_status"], dict):
                for k, v in stored["zone_status"].items():
                    with suppress(ValueError, TypeError):
                        zk = int(k)
                        if isinstance(v, dict):
                            self.zone_status[zk] = {**self._initial_zone_status(zk), **v}
            return

        _LOGGER.info("No persisted state found in storage. Attempting first-run recorder backfill.")
        await self._async_backfill_historical_rain()
        await self.async_save_state()

    async def _async_backfill_historical_rain(self) -> None:
        """Query recorder database for historical precipitation on cold start."""
        if "recorder" not in self.hass.config.components:
            _LOGGER.debug("Recorder integration not active; skipping DB backfill.")
            return

        rain_entity = self._get_conf(CONF_SENSOR_RAIN_TODAY, DEFAULT_SENSOR_RAIN_TODAY)
        rain_is_rate = bool(self._get_conf(CONF_RAIN_IS_RATE, DEFAULT_RAIN_IS_RATE))
        now = dt_util.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today_start - timedelta(days=1)

        def _query() -> dict[str, Any]:
            from homeassistant.components.recorder.history import get_significant_states

            return get_significant_states(
                self.hass,
                start_time=yesterday_start,
                end_time=now,
                entity_ids=[rain_entity],
                significant_changes_only=False,
            )

        try:
            from homeassistant.components.recorder import get_instance

            recorder_instance = get_instance(self.hass)
            states_dict = await recorder_instance.async_add_executor_job(_query)
            if rain_entity in states_dict and states_dict[rain_entity]:
                all_states = states_dict[rain_entity]
                if rain_is_rate:
                    yesterday_pairs: list[tuple[float, datetime]] = []
                    today_pairs: list[tuple[float, datetime]] = []
                    for st in all_states:
                        val_str = getattr(st, "state", None)
                        ts = getattr(st, "last_updated", None)
                        if val_str not in (None, "unknown", "unavailable") and ts is not None:
                            with suppress(ValueError, TypeError):
                                rate = float(str(val_str).replace(",", ".").strip())
                                if ts < today_start:
                                    yesterday_pairs.append((rate, ts))
                                else:
                                    today_pairs.append((rate, ts))

                    if yesterday_pairs:
                        self.yesterday_rain = integrate_state_history(yesterday_pairs)
                        _LOGGER.info(
                            "Seeded yesterday's rainfall via rate integration (%s): %.2f mm",
                            rain_entity,
                            self.yesterday_rain,
                        )
                    if today_pairs:
                        self.rain_today = integrate_state_history(today_pairs)
                        _LOGGER.info(
                            "Seeded today's rainfall via rate integration (%s): %.2f mm",
                            rain_entity,
                            self.rain_today,
                        )
                else:
                    for st in all_states:
                        val = getattr(st, "state", None)
                        ts = getattr(st, "last_updated", None)
                        if val not in (None, "unknown", "unavailable"):
                            with suppress(ValueError, TypeError):
                                num = float(str(val).replace(",", ".").strip())
                                if ts is not None and ts < today_start:
                                    self.yesterday_rain = num
                                else:
                                    self.rain_today = num
        except Exception as err:
            _LOGGER.warning("Could not backfill historical rain from recorder: %s", err)

    async def async_save_state(self) -> None:
        """Persist current state to Home Assistant storage."""
        data = {
            "last_et0": self.last_et0,
            "yesterday_rain": self.yesterday_rain,
            "rain_today": self.rain_today,
            "rain_today_date": self.rain_today_date,
            "zone_deficits": {str(k): v for k, v in self.zone_deficits.items()},
            "zone_status": {str(k): v for k, v in self.zone_status.items()},
        }
        try:
            await self._store.async_save(data)
        except Exception as err:
            _LOGGER.error("Failed to save Smart Drip state to storage: %s", err)

    async def async_unload(self) -> None:
        """Unload scheduled timers and release resources."""
        for unsub in self._unsub_schedules:
            unsub()
        self._unsub_schedules.clear()

    async def _handle_nightly_et0_trigger(self, _now: datetime) -> None:
        """Scheduled callback at 23:00 nightly to calculate ET0."""
        _LOGGER.info("Executing scheduled nightly ET0 calculation at 23:00.")
        await self.async_calculate_daily_et0()

    async def _handle_morning_irrigation_trigger(self, _now: datetime) -> None:
        """Scheduled callback at 06:00 morning to evaluate and execute irrigation."""
        _LOGGER.info("Executing scheduled morning irrigation sequence at 06:00.")
        await self.async_execute_morning_schedule()

    async def async_calculate_daily_et0(self) -> float:
        """Calculate daily ET0 using sensor telemetry and update water deficits."""
        temp_c = self._get_float_state(self._get_conf(CONF_SENSOR_TEMP, DEFAULT_SENSOR_TEMP), 18.0)
        humidity = self._get_float_state(
            self._get_conf(CONF_SENSOR_HUMIDITY, DEFAULT_SENSOR_HUMIDITY), 60.0
        )
        dewpoint = self._get_float_state(
            self._get_conf(CONF_SENSOR_DEWPOINT, DEFAULT_SENSOR_DEWPOINT), 10.0
        )
        radiation = self._get_float_state(
            self._get_conf(CONF_SENSOR_RADIATION, DEFAULT_SENSOR_RADIATION), 15.0
        )
        wind = self._get_float_state(self._get_conf(CONF_SENSOR_WIND, DEFAULT_SENSOR_WIND), 1.5)
        pressure = self._get_float_state(
            self._get_conf(CONF_SENSOR_PRESSURE, DEFAULT_SENSOR_PRESSURE), 1013.25
        )
        rain_is_rate = bool(self._get_conf(CONF_RAIN_IS_RATE, DEFAULT_RAIN_IS_RATE))
        rain_entity = self._get_conf(CONF_SENSOR_RAIN_TODAY, DEFAULT_SENSOR_RAIN_TODAY)
        rain_today = self.rain_today if rain_is_rate else self._get_float_state(rain_entity, 0.0)

        et0 = calculate_et0(
            temp_c=temp_c,
            net_radiation_mj=radiation,
            wind_speed_m_s=wind,
            relative_humidity=humidity,
            dewpoint_c=dewpoint,
            pressure_hpa=pressure,
        )
        self.last_et0 = et0
        self.yesterday_rain = rain_today

        max_bucket = float(self._get_conf(CONF_MAX_BUCKET, DEFAULT_MAX_BUCKET_MM))

        # Update cumulative deficit for each zone
        for zone in (1, 2):
            prev = self.zone_deficits[zone]
            new_deficit = calculate_deficit(
                previous_deficit=prev,
                et0=et0,
                rainfall=rain_today,
                irrigation_applied=0.0,
                max_bucket=max_bucket,
            )
            self.zone_deficits[zone] = new_deficit
            _LOGGER.info(
                "Zone %s deficit updated: prev=%.2f mm, ET0=%.2f mm, rain=%.2f mm -> new=%.2f mm",
                zone,
                prev,
                et0,
                rain_today,
                new_deficit,
            )

        await self.async_evaluate_zones()
        self.async_set_updated_data(self._build_coordinator_data())
        await self.async_save_state()
        return et0

    async def async_evaluate_zones(self) -> None:
        """Evaluate decision state machine for both zones."""
        temp_c = self._get_float_state(self._get_conf(CONF_SENSOR_TEMP, DEFAULT_SENSOR_TEMP), 18.0)
        rain_rate = self._get_float_state(
            self._get_conf(CONF_SENSOR_RAIN_INTENSITY, DEFAULT_SENSOR_RAIN_INTENSITY), 0.0
        )
        rain_entity = self._get_conf(CONF_SENSOR_RAIN_TODAY, DEFAULT_SENSOR_RAIN_TODAY)
        rain_is_rate = bool(self._get_conf(CONF_RAIN_IS_RATE, DEFAULT_RAIN_IS_RATE))

        if rain_is_rate:
            curr_rate = self._get_float_state(rain_entity, 0.0)
            if curr_rate > rain_rate:
                rain_rate = curr_rate
            rain_today = self.rain_today
        else:
            rain_today = self._get_float_state(rain_entity, self.rain_today)
            self.rain_today = rain_today

        safety_limit = int(self._get_conf(CONF_SAFETY_LIMIT, DEFAULT_SAFETY_LIMIT_SECONDS))

        zone_configs = {
            1: {
                "enabled": bool(self._get_conf(CONF_ZONE_1_ENABLED, True)),
                "area": float(self._get_conf(CONF_ZONE_1_AREA, DEFAULT_ZONE_1_AREA_M2)),
                "flow": float(self._get_conf(CONF_ZONE_1_FLOW_RATE, DEFAULT_ZONE_1_FLOW_RATE_L_H)),
            },
            2: {
                "enabled": bool(self._get_conf(CONF_ZONE_2_ENABLED, False)),
                "area": float(self._get_conf(CONF_ZONE_2_AREA, DEFAULT_ZONE_2_AREA_M2)),
                "flow": float(self._get_conf(CONF_ZONE_2_FLOW_RATE, DEFAULT_ZONE_2_FLOW_RATE_L_H)),
            },
        }

        for zone in (1, 2):
            cfg = zone_configs[zone]
            deficit = self.zone_deficits[zone]

            state, reason = evaluate_irrigation_decision(
                zone_enabled=bool(cfg["enabled"]),
                temp_c=temp_c,
                current_rain_rate_mm_h=rain_rate,
                rain_today_mm=rain_today,
                rain_yesterday_mm=self.yesterday_rain,
                deficit_mm=deficit,
            )

            duration = 0
            liters = 0.0
            if state == STATUS_READY:
                duration = calculate_runtime_seconds(
                    deficit_mm=deficit,
                    flow_rate_l_h=cfg["flow"],
                    area_m2=cfg["area"],
                    safety_ceiling_seconds=safety_limit,
                )
                # Liters = (duration_seconds / 3600) * flow_rate_l_h
                liters = round((duration / 3600.0) * cfg["flow"], 1)

            self.zone_status[zone]["state"] = state
            self.zone_status[zone]["reason"] = reason
            self.zone_status[zone]["target_duration_seconds"] = duration
            self.zone_status[zone]["estimated_liters"] = liters
            self.zone_status[zone]["last_rain_today_mm"] = rain_today

        self.async_set_updated_data(self._build_coordinator_data())

    async def async_execute_morning_schedule(self) -> None:
        """Evaluate zones and sequentially run active valves at 06:00."""
        await self.async_evaluate_zones()

        zone_switches = {
            1: self._get_conf(CONF_ZONE_1_SWITCH, DEFAULT_ZONE_1_SWITCH),
            2: self._get_conf(CONF_ZONE_2_SWITCH, DEFAULT_ZONE_2_SWITCH),
        }
        zone_flows = {
            1: float(self._get_conf(CONF_ZONE_1_FLOW_RATE, DEFAULT_ZONE_1_FLOW_RATE_L_H)),
            2: float(self._get_conf(CONF_ZONE_2_FLOW_RATE, DEFAULT_ZONE_2_FLOW_RATE_L_H)),
        }
        zone_areas = {
            1: float(self._get_conf(CONF_ZONE_1_AREA, DEFAULT_ZONE_1_AREA_M2)),
            2: float(self._get_conf(CONF_ZONE_2_AREA, DEFAULT_ZONE_2_AREA_M2)),
        }

        for zone in (1, 2):
            status = self.zone_status[zone]
            if status["state"] != STATUS_READY:
                _LOGGER.info(
                    "Skipping Zone %s: State is '%s' (%s)",
                    zone,
                    status["state"],
                    status["reason"],
                )
                continue

            duration = status["target_duration_seconds"]
            if duration <= 0:
                continue

            switch_entity = zone_switches[zone]
            flow = zone_flows[zone]
            area = zone_areas[zone]

            async def turn_on(z: int = zone, sw: str = switch_entity) -> None:
                self.zone_status[z]["state"] = STATUS_RUNNING
                self.async_set_updated_data(self._build_coordinator_data())
                await self.hass.services.async_call(
                    "switch", "turn_on", {"entity_id": sw}, blocking=True
                )

            async def turn_off(
                z: int = zone,
                sw: str = switch_entity,
                d: int = duration,
                f: float = flow,
                a: float = area,
            ) -> None:
                await self.hass.services.async_call(
                    "switch", "turn_off", {"entity_id": sw}, blocking=True
                )
                # Compute applied precipitation in mm
                pr = calculate_precipitation_rate(f, a)
                applied_mm = (d / 3600.0) * pr
                self.zone_deficits[z] = max(0.0, round(self.zone_deficits[z] - applied_mm, 2))
                self.zone_status[z]["state"] = STATUS_IDLE
                self.zone_status[z]["last_run_timestamp"] = dt_util.now().isoformat()
                self.zone_status[z]["target_duration_seconds"] = 0
                self.zone_status[z]["estimated_liters"] = 0.0
                self.async_set_updated_data(self._build_coordinator_data())
                await self.async_save_state()

            _LOGGER.info("Starting guarded execution for Zone %s (%s s).", zone, duration)
            await self.interlock.execute_irrigation(
                channel=zone,
                duration_seconds=duration,
                turn_on_fn=turn_on,
                turn_off_fn=turn_off,
            )

    async def async_run_zone_manual(self, zone: int, duration_seconds: int) -> None:
        """Trigger a manual irrigation run for a zone with safety interlock."""
        if zone not in (1, 2):
            raise ValueError(f"Invalid zone {zone}; must be 1 or 2.")

        zone_switches = {
            1: self._get_conf(CONF_ZONE_1_SWITCH, DEFAULT_ZONE_1_SWITCH),
            2: self._get_conf(CONF_ZONE_2_SWITCH, DEFAULT_ZONE_2_SWITCH),
        }
        zone_flows = {
            1: float(self._get_conf(CONF_ZONE_1_FLOW_RATE, DEFAULT_ZONE_1_FLOW_RATE_L_H)),
            2: float(self._get_conf(CONF_ZONE_2_FLOW_RATE, DEFAULT_ZONE_2_FLOW_RATE_L_H)),
        }
        zone_areas = {
            1: float(self._get_conf(CONF_ZONE_1_AREA, DEFAULT_ZONE_1_AREA_M2)),
            2: float(self._get_conf(CONF_ZONE_2_AREA, DEFAULT_ZONE_2_AREA_M2)),
        }

        switch_entity = zone_switches[zone]
        flow = zone_flows[zone]
        area = zone_areas[zone]

        async def turn_on() -> None:
            self.zone_status[zone]["state"] = STATUS_RUNNING
            self.async_set_updated_data(self._build_coordinator_data())
            await self.hass.services.async_call(
                "switch", "turn_on", {"entity_id": switch_entity}, blocking=True
            )

        async def turn_off() -> None:
            await self.hass.services.async_call(
                "switch", "turn_off", {"entity_id": switch_entity}, blocking=True
            )
            pr = calculate_precipitation_rate(flow, area)
            applied_mm = (duration_seconds / 3600.0) * pr
            self.zone_deficits[zone] = max(0.0, round(self.zone_deficits[zone] - applied_mm, 2))
            self.zone_status[zone]["state"] = STATUS_IDLE
            self.zone_status[zone]["last_run_timestamp"] = dt_util.now().isoformat()
            self.async_set_updated_data(self._build_coordinator_data())
            await self.async_save_state()

        await self.interlock.execute_irrigation(
            channel=zone,
            duration_seconds=duration_seconds,
            turn_on_fn=turn_on,
            turn_off_fn=turn_off,
        )

    async def async_reset_bucket(self, zone: int | str = "all") -> None:
        """Reset water deficit to 0 for a zone or all zones."""
        if str(zone) in ("1", "all"):
            self.zone_deficits[1] = 0.0
            _LOGGER.info("Reset water deficit for Zone 1 to 0 mm.")
        if str(zone) in ("2", "all"):
            self.zone_deficits[2] = 0.0
            _LOGGER.info("Reset water deficit for Zone 2 to 0 mm.")

        await self.async_evaluate_zones()
        self.async_set_updated_data(self._build_coordinator_data())
        await self.async_save_state()

    def _build_coordinator_data(self) -> dict[str, Any]:
        """Construct the reactive coordinator payload for entities."""
        return {
            "last_et0": self.last_et0,
            "yesterday_rain": self.yesterday_rain,
            "rain_today": self.rain_today,
            "zone_deficits": dict(self.zone_deficits),
            "zone_status": {z: dict(self.zone_status[z]) for z in (1, 2)},
            "interlock_active": self.interlock.is_active,
            "interlock_active_channel": self.interlock.active_channel,
        }
