"""Pure mathematical calculations and decision state machine for smart_drip."""

from __future__ import annotations

import math
from datetime import datetime

from .const import (
    DEFAULT_MAX_BUCKET_MM,
    DEFAULT_MIN_DEFICIT_TRIGGER_MM,
    DEFAULT_RAIN_TODAY_CUTOFF_MM,
    DEFAULT_RAIN_TOMORROW_CUTOFF_MM,
    DEFAULT_SAFETY_LIMIT_SECONDS,
    DEFAULT_TEMP_CUTOFF_C,
    DEFAULT_YESTERDAY_RAIN_CUTOFF_MM,
    STATUS_READY,
    STATUS_SKIPPED_ACTIVE_RAIN,
    STATUS_SKIPPED_DAILY_RAIN_EXCEEDED,
    STATUS_SKIPPED_LOW_TEMP,
    STATUS_SKIPPED_RAIN_TOMORROW,
    STATUS_SKIPPED_YESTERDAY_HEAVY_SOAK,
    STATUS_SKIPPED_ZERO_DEFICIT,
    STATUS_SKIPPED_ZONE_DISABLED,
)


def calculate_saturation_vapor_pressure(temp_c: float) -> float:
    """Calculate saturation vapor pressure e0(T) in kPa using Tetens/FAO-56 equation."""
    return 0.6108 * math.exp((17.27 * temp_c) / (temp_c + 237.3))


def calculate_actual_vapor_pressure(
    temp_c: float,
    relative_humidity: float | None = None,
    dewpoint_c: float | None = None,
) -> float:
    """Calculate actual vapor pressure ea in kPa from RH or dewpoint."""
    if dewpoint_c is not None:
        return calculate_saturation_vapor_pressure(dewpoint_c)
    if relative_humidity is not None:
        e0 = calculate_saturation_vapor_pressure(temp_c)
        return e0 * (max(0.0, min(100.0, relative_humidity)) / 100.0)
    # Fallback to saturation vapor pressure if humidity missing
    return calculate_saturation_vapor_pressure(temp_c)


def calculate_slope_vapor_pressure(temp_c: float) -> float:
    """Calculate slope of saturation vapor pressure curve Delta in kPa / C."""
    e0 = calculate_saturation_vapor_pressure(temp_c)
    return (4098.0 * e0) / ((temp_c + 237.3) ** 2)


def calculate_psychrometric_constant(pressure_hpa: float) -> float:
    """Calculate psychrometric constant gamma in kPa / C from atmospheric pressure in hPa."""
    pressure_kpa = pressure_hpa / 10.0
    return 0.000665 * pressure_kpa


def calculate_et0(
    temp_c: float,
    net_radiation_mj: float,
    wind_speed_m_s: float,
    relative_humidity: float | None = None,
    dewpoint_c: float | None = None,
    pressure_hpa: float = 1013.25,
) -> float:
    """Calculate FAO-56 Penman-Monteith daily reference evapotranspiration (ET0) in mm/day.

    ET0 = [0.408 * Delta * (Rn - G) + gamma * (900 / (T + 273)) * u2 * (es - ea)] /
          [Delta + gamma * (1 + 0.34 * u2)]
    """
    # Clamping freezing temperatures for positive sensible heat flux
    if temp_c <= -5.0 or net_radiation_mj <= 0.0:
        return 0.0

    delta = calculate_slope_vapor_pressure(temp_c)
    gamma = calculate_psychrometric_constant(pressure_hpa)
    es = calculate_saturation_vapor_pressure(temp_c)
    ea = calculate_actual_vapor_pressure(temp_c, relative_humidity, dewpoint_c)

    vpd = max(0.0, es - ea)
    u2 = max(0.0, wind_speed_m_s)
    rn = max(0.0, net_radiation_mj)
    g = 0.0  # Daily soil heat flux is approx 0

    numerator = (0.408 * delta * (rn - g)) + (gamma * (900.0 / (temp_c + 273.15)) * u2 * vpd)
    denominator = delta + (gamma * (1.0 + 0.34 * u2))

    if denominator <= 0.0:
        return 0.0

    et0 = numerator / denominator
    return max(0.0, round(et0, 2))


def calculate_deficit(
    previous_deficit: float,
    et0: float,
    rainfall: float,
    irrigation_applied: float,
    max_bucket: float = DEFAULT_MAX_BUCKET_MM,
) -> float:
    """Calculate new cumulative soil water deficit clamped between 0 and max_bucket (mm).

    Deficit_t = max(0, min(MaxBucket, Deficit_{t-1} + ET0 - Rainfall - IrrigationApplied))
    """
    net_change = et0 - rainfall - irrigation_applied
    new_deficit = previous_deficit + net_change
    clamped = max(0.0, min(max_bucket, new_deficit))
    return round(clamped, 2)


def calculate_precipitation_rate(flow_rate_l_h: float, area_m2: float) -> float:
    """Calculate precipitation rate in mm/h from flow rate (L/h) and irrigated area (m2).

    1 L/m2 = 1 mm -> Pr (mm/h) = Flow (L/h) / Area (m2).
    """
    if area_m2 <= 0.0 or flow_rate_l_h <= 0.0:
        return 0.0
    return flow_rate_l_h / area_m2


def calculate_runtime_seconds(
    deficit_mm: float,
    flow_rate_l_h: float,
    area_m2: float,
    safety_ceiling_seconds: int = DEFAULT_SAFETY_LIMIT_SECONDS,
) -> int:
    """Calculate required valve open runtime in seconds, clamped to safety ceiling."""
    if deficit_mm <= 0.0 or flow_rate_l_h <= 0.0 or area_m2 <= 0.0:
        return 0

    pr_mm_h = calculate_precipitation_rate(flow_rate_l_h, area_m2)
    if pr_mm_h <= 0.0:
        return 0

    # duration in hours = deficit / Pr -> seconds = (deficit / Pr) * 3600
    duration_seconds = (deficit_mm / pr_mm_h) * 3600.0
    rounded_seconds = int(round(duration_seconds))
    return max(0, min(safety_ceiling_seconds, rounded_seconds))


def evaluate_irrigation_decision(
    zone_enabled: bool,
    temp_c: float,
    current_rain_rate_mm_h: float,
    rain_today_mm: float,
    rain_yesterday_mm: float,
    deficit_mm: float,
    temp_cutoff_c: float = DEFAULT_TEMP_CUTOFF_C,
    rain_today_cutoff_mm: float = DEFAULT_RAIN_TODAY_CUTOFF_MM,
    yesterday_rain_cutoff_mm: float = DEFAULT_YESTERDAY_RAIN_CUTOFF_MM,
    min_deficit_trigger_mm: float = DEFAULT_MIN_DEFICIT_TRIGGER_MM,
    rain_tomorrow_mm: float = 0.0,
    rain_tomorrow_cutoff_mm: float = DEFAULT_RAIN_TOMORROW_CUTOFF_MM,
) -> tuple[str, str]:
    """Evaluate skip criteria in prioritized order and return (Status, Reason)."""
    if not zone_enabled:
        return STATUS_SKIPPED_ZONE_DISABLED, "Zone is currently disabled in settings."

    if temp_c < temp_cutoff_c:
        return (
            STATUS_SKIPPED_LOW_TEMP,
            f"Ambient temperature ({temp_c:.1f}°C) is below freeze protection threshold ({temp_cutoff_c:.1f}°C).",
        )

    if current_rain_rate_mm_h > 0.0:
        return (
            STATUS_SKIPPED_ACTIVE_RAIN,
            f"Active precipitation detected ({current_rain_rate_mm_h:.1f} mm/h).",
        )

    if rain_today_mm >= rain_today_cutoff_mm:
        return (
            STATUS_SKIPPED_DAILY_RAIN_EXCEEDED,
            f"Rainfall today ({rain_today_mm:.1f} mm) exceeds cutoff threshold ({rain_today_cutoff_mm:.1f} mm).",
        )

    if rain_yesterday_mm >= yesterday_rain_cutoff_mm:
        return (
            STATUS_SKIPPED_YESTERDAY_HEAVY_SOAK,
            f"Yesterday's soak ({rain_yesterday_mm:.1f} mm) exceeds threshold ({yesterday_rain_cutoff_mm:.1f} mm).",
        )

    if rain_tomorrow_cutoff_mm > 0.0 and rain_tomorrow_mm >= rain_tomorrow_cutoff_mm:
        return (
            STATUS_SKIPPED_RAIN_TOMORROW,
            f"Tomorrow's rain forecast ({rain_tomorrow_mm:.1f} mm) exceeds cutoff threshold ({rain_tomorrow_cutoff_mm:.1f} mm).",
        )

    if deficit_mm < min_deficit_trigger_mm:
        return (
            STATUS_SKIPPED_ZERO_DEFICIT,
            f"Accumulated deficit ({deficit_mm:.2f} mm) is below trigger threshold ({min_deficit_trigger_mm:.1f} mm).",
        )

    return (
        STATUS_READY,
        f"Zone ready for irrigation. Deficit: {deficit_mm:.2f} mm.",
    )


def integrate_trapezoidal_rain(
    rate1_mm_h: float,
    rate2_mm_h: float,
    duration_seconds: float,
) -> float:
    """Calculate accumulated precipitation (mm) over duration using trapezoidal integration.

    Rain (mm) = ((rate1 + rate2) / 2) * (duration_seconds / 3600)
    """
    if duration_seconds <= 0.0:
        return 0.0
    r1 = max(0.0, rate1_mm_h)
    r2 = max(0.0, rate2_mm_h)
    return ((r1 + r2) / 2.0) * (duration_seconds / 3600.0)


def integrate_state_history(
    states: list[tuple[float, datetime]],
    max_gap_seconds: float = 3600.0,
) -> float:
    """Integrate a series of timestamped rate values using trapezoidal rule.

    states: list of (rate_mm_h, timestamp) sorted by timestamp ascending.
    """
    if len(states) < 2:
        return 0.0

    total_rain = 0.0
    for i in range(1, len(states)):
        r1, t1 = states[i - 1]
        r2, t2 = states[i]
        dt = (t2 - t1).total_seconds()
        if 0 < dt <= max_gap_seconds:
            total_rain += integrate_trapezoidal_rain(r1, r2, dt)

    return round(total_rain, 2)


def integrate_delta_history(states: list[tuple[float, datetime]]) -> float:
    """Sum interval delta precipitation amounts (mm) from sensors reporting per-period totals."""
    return round(sum(val for val, _ in states if val > 0.0), 2)


def integrate_trapezoidal_solar(
    rate1_w_m2: float,
    rate2_w_m2: float,
    duration_seconds: float,
) -> float:
    """Calculate accumulated solar irradiation (MJ/m2) from irradiance (W/m2) over duration.

    Energy (MJ/m2) = (((rate1 + rate2) / 2) * duration_seconds) / 1,000,000
    """
    if duration_seconds <= 0.0:
        return 0.0
    r1 = max(0.0, rate1_w_m2)
    r2 = max(0.0, rate2_w_m2)
    return ((r1 + r2) / 2.0) * (duration_seconds / 1_000_000.0)


def integrate_solar_history(
    states: list[tuple[float, datetime]],
    max_gap_seconds: float = 3600.0,
) -> float:
    """Integrate a series of timestamped irradiance (W/m2) values into total daily MJ/m2.

    states: list of (irradiance_w_m2, timestamp) sorted by timestamp ascending.
    """
    if len(states) < 2:
        return 0.0

    total_mj = 0.0
    for i in range(1, len(states)):
        r1, t1 = states[i - 1]
        r2, t2 = states[i]
        dt = (t2 - t1).total_seconds()
        if 0 < dt <= max_gap_seconds:
            total_mj += integrate_trapezoidal_solar(r1, r2, dt)

    return round(total_mj, 3)
