"""Unit tests for smart_drip mathematical models and pure calculations."""

from datetime import UTC, datetime

import pytest

from custom_components.smart_drip.calc import (
    calculate_actual_vapor_pressure,
    calculate_deficit,
    calculate_et0,
    calculate_psychrometric_constant,
    calculate_runtime_seconds,
    calculate_saturation_vapor_pressure,
    calculate_slope_vapor_pressure,
    evaluate_irrigation_decision,
    integrate_state_history,
    integrate_trapezoidal_rain,
)
from custom_components.smart_drip.const import (
    DEFAULT_MAX_BUCKET_MM,
    DEFAULT_MIN_DEFICIT_TRIGGER_MM,
    DEFAULT_RAIN_TODAY_CUTOFF_MM,
    DEFAULT_SAFETY_LIMIT_SECONDS,
    DEFAULT_TEMP_CUTOFF_C,
    DEFAULT_YESTERDAY_RAIN_CUTOFF_MM,
    STATUS_READY,
    STATUS_SKIPPED_ACTIVE_RAIN,
    STATUS_SKIPPED_DAILY_RAIN_EXCEEDED,
    STATUS_SKIPPED_LOW_TEMP,
    STATUS_SKIPPED_YESTERDAY_HEAVY_SOAK,
    STATUS_SKIPPED_ZERO_DEFICIT,
    STATUS_SKIPPED_ZONE_DISABLED,
)


def test_saturation_vapor_pressure() -> None:
    """Test saturation vapor pressure at 20 C is approx 2.338 kPa."""
    e0 = calculate_saturation_vapor_pressure(20.0)
    assert pytest.approx(e0, rel=1e-3) == 2.338


def test_actual_vapor_pressure_from_rh() -> None:
    """Test actual vapor pressure from RH."""
    # At 20 C and 50% RH: 2.338 * 0.5 = 1.169 kPa
    ea = calculate_actual_vapor_pressure(temp_c=20.0, relative_humidity=50.0)
    assert pytest.approx(ea, rel=1e-3) == 1.169


def test_actual_vapor_pressure_from_dewpoint() -> None:
    """Test actual vapor pressure from dewpoint temperature."""
    # Dewpoint 10 C should equal saturation vapor pressure at 10 C
    ea = calculate_actual_vapor_pressure(temp_c=20.0, dewpoint_c=10.0)
    e0_10 = calculate_saturation_vapor_pressure(10.0)
    assert pytest.approx(ea, rel=1e-3) == e0_10


def test_slope_vapor_pressure() -> None:
    """Test slope of saturation vapor pressure curve at 20 C."""
    delta = calculate_slope_vapor_pressure(20.0)
    # At 20 C, delta is approx 0.145 kPa / C
    assert pytest.approx(delta, rel=1e-2) == 0.145


def test_psychrometric_constant() -> None:
    """Test psychrometric constant at 101.3 kPa (1013 hPa)."""
    gamma = calculate_psychrometric_constant(pressure_hpa=1013.25)
    # gamma at sea level approx 0.0673 kPa / C
    assert pytest.approx(gamma, rel=1e-2) == 0.0674


def test_fao56_penman_monteith_standard_case() -> None:
    """Test standard FAO-56 calculation.

    Conditions:
    - Temp: 20 C
    - Net radiation Rn: 15.0 MJ/m2/day
    - Wind speed: 2.0 m/s
    - RH: 50%
    - Pressure: 1013 hPa
    """
    et0 = calculate_et0(
        temp_c=20.0,
        net_radiation_mj=15.0,
        wind_speed_m_s=2.0,
        relative_humidity=50.0,
        pressure_hpa=1013.25,
    )
    # For a sunny 20 C day with moderate wind and 15 MJ/m2 net radiation,
    # ET0 is approx 5.31 mm/day
    assert 5.0 <= et0 <= 5.5


def test_fao56_penman_monteith_negative_radiation_clamped() -> None:
    """Test that ET0 is clamped to 0 on dark/freezing conditions."""
    et0 = calculate_et0(
        temp_c=-2.0,
        net_radiation_mj=0.0,
        wind_speed_m_s=0.5,
        relative_humidity=95.0,
        pressure_hpa=1013.25,
    )
    assert et0 == 0.0


def test_deficit_accumulation_and_clamping() -> None:
    """Test water budget balance clamping to 0 and max bucket."""
    # Day 1: start at 0, ET0=4.0, rain=0, irrigation=0 -> deficit 4.0
    d1 = calculate_deficit(
        previous_deficit=0.0,
        et0=4.0,
        rainfall=0.0,
        irrigation_applied=0.0,
        max_bucket=DEFAULT_MAX_BUCKET_MM,
    )
    assert pytest.approx(d1) == 4.0

    # Day 2: previous=4.0, ET0=3.0, rain=10.0 -> deficit clamped to 0.0
    d2 = calculate_deficit(
        previous_deficit=4.0,
        et0=3.0,
        rainfall=10.0,
        irrigation_applied=0.0,
        max_bucket=DEFAULT_MAX_BUCKET_MM,
    )
    assert d2 == 0.0

    # Large accumulation exceeding max bucket (24 mm)
    d3 = calculate_deficit(
        previous_deficit=20.0,
        et0=10.0,
        rainfall=0.0,
        irrigation_applied=0.0,
        max_bucket=DEFAULT_MAX_BUCKET_MM,
    )
    assert pytest.approx(d3) == DEFAULT_MAX_BUCKET_MM


def test_runtime_seconds_calculation() -> None:
    """Test runtime calculation for Zone 1 (flow=40 L/h, area=4.8 m2 -> Pr=8.333 mm/h)."""
    # 8.333 mm/h -> 432 s/mm
    # Deficit 2.0 mm -> 864 seconds
    duration = calculate_runtime_seconds(
        deficit_mm=2.0,
        flow_rate_l_h=40.0,
        area_m2=4.8,
        safety_ceiling_seconds=DEFAULT_SAFETY_LIMIT_SECONDS,
    )
    assert duration == 864

    # Clamping at safety limit (2700 s)
    excess_duration = calculate_runtime_seconds(
        deficit_mm=10.0,
        flow_rate_l_h=40.0,
        area_m2=4.8,
        safety_ceiling_seconds=DEFAULT_SAFETY_LIMIT_SECONDS,
    )
    assert excess_duration == DEFAULT_SAFETY_LIMIT_SECONDS


def test_runtime_seconds_zero_area_or_flow() -> None:
    """Test safety handling when area or flow is 0."""
    duration = calculate_runtime_seconds(deficit_mm=2.0, flow_rate_l_h=0.0, area_m2=4.8)
    assert duration == 0


def test_evaluate_irrigation_decision_rules() -> None:
    """Test all skip conditions in decision state machine."""
    # 1. Zone disabled
    res, reason = evaluate_irrigation_decision(
        zone_enabled=False,
        temp_c=20.0,
        current_rain_rate_mm_h=0.0,
        rain_today_mm=0.0,
        rain_yesterday_mm=0.0,
        deficit_mm=3.0,
    )
    assert res == STATUS_SKIPPED_ZONE_DISABLED

    # 2. Low temperature
    res, reason = evaluate_irrigation_decision(
        zone_enabled=True,
        temp_c=3.5,
        current_rain_rate_mm_h=0.0,
        rain_today_mm=0.0,
        rain_yesterday_mm=0.0,
        deficit_mm=3.0,
        temp_cutoff_c=DEFAULT_TEMP_CUTOFF_C,
    )
    assert res == STATUS_SKIPPED_LOW_TEMP

    # 3. Active rain
    res, reason = evaluate_irrigation_decision(
        zone_enabled=True,
        temp_c=18.0,
        current_rain_rate_mm_h=0.5,
        rain_today_mm=0.0,
        rain_yesterday_mm=0.0,
        deficit_mm=3.0,
    )
    assert res == STATUS_SKIPPED_ACTIVE_RAIN

    # 4. Daily rain cutoff exceeded (>= 2.5 mm)
    res, reason = evaluate_irrigation_decision(
        zone_enabled=True,
        temp_c=18.0,
        current_rain_rate_mm_h=0.0,
        rain_today_mm=3.0,
        rain_yesterday_mm=0.0,
        deficit_mm=3.0,
        rain_today_cutoff_mm=DEFAULT_RAIN_TODAY_CUTOFF_MM,
    )
    assert res == STATUS_SKIPPED_DAILY_RAIN_EXCEEDED

    # 5. Yesterday heavy soak (>= 10.0 mm)
    res, reason = evaluate_irrigation_decision(
        zone_enabled=True,
        temp_c=18.0,
        current_rain_rate_mm_h=0.0,
        rain_today_mm=0.0,
        rain_yesterday_mm=12.0,
        deficit_mm=3.0,
        yesterday_rain_cutoff_mm=DEFAULT_YESTERDAY_RAIN_CUTOFF_MM,
    )
    assert res == STATUS_SKIPPED_YESTERDAY_HEAVY_SOAK

    # 6. Zero deficit (< 1.0 mm)
    res, reason = evaluate_irrigation_decision(
        zone_enabled=True,
        temp_c=18.0,
        current_rain_rate_mm_h=0.0,
        rain_today_mm=0.0,
        rain_yesterday_mm=0.0,
        deficit_mm=0.8,
        min_deficit_trigger_mm=DEFAULT_MIN_DEFICIT_TRIGGER_MM,
    )
    assert res == STATUS_SKIPPED_ZERO_DEFICIT

    # 7. Ready
    res, reason = evaluate_irrigation_decision(
        zone_enabled=True,
        temp_c=18.0,
        current_rain_rate_mm_h=0.0,
        rain_today_mm=0.0,
        rain_yesterday_mm=0.0,
        deficit_mm=3.0,
    )
    assert res == STATUS_READY
    assert "Deficit: 3.00 mm" in reason


def test_integrate_trapezoidal_rain() -> None:
    """Test trapezoidal rain accumulation from rate pairs."""
    # 0 duration
    assert integrate_trapezoidal_rain(10.0, 10.0, 0.0) == 0.0
    # Negative duration
    assert integrate_trapezoidal_rain(10.0, 10.0, -10.0) == 0.0
    # Steady 2.6 mm/h for 1 hour (3600s) = 2.6 mm
    assert round(integrate_trapezoidal_rain(2.6, 2.6, 3600.0), 2) == 2.6
    # Rate change from 4.0 to 0.0 over 30 minutes (1800s) = 1.0 mm
    assert round(integrate_trapezoidal_rain(4.0, 0.0, 1800.0), 2) == 1.0


def test_integrate_state_history() -> None:
    """Test integrating historical series of timestamped rain rates."""
    # Empty or single state
    assert integrate_state_history([]) == 0.0
    t0 = datetime(2026, 9, 26, 10, 0, 0, tzinfo=UTC)
    assert integrate_state_history([(2.0, t0)]) == 0.0

    # 10:00 rate=2.0 -> 10:30 rate=4.0 -> 11:00 rate=0.0
    t1 = datetime(2026, 9, 26, 10, 30, 0, tzinfo=UTC)
    t2 = datetime(2026, 9, 26, 11, 0, 0, tzinfo=UTC)
    history = [(2.0, t0), (4.0, t1), (0.0, t2)]
    # First interval (1800s): ((2+4)/2) * 0.5 = 1.5 mm
    # Second interval (1800s): ((4+0)/2) * 0.5 = 1.0 mm
    # Total = 2.5 mm
    assert integrate_state_history(history) == 2.5

    # Outage gap exceeding max_gap_seconds (e.g. 5 hours) is safely ignored
    t3 = datetime(2026, 9, 26, 16, 0, 0, tzinfo=UTC)
    history_gap = [(2.0, t0), (4.0, t3)]
    assert integrate_state_history(history_gap, max_gap_seconds=3600.0) == 0.0
