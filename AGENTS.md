# Agent Guide: `integration/` (Home Assistant Custom Integration `smart_drip`)

This directory houses the standalone, production-ready Home Assistant custom integration for smart micro-drip irrigation.

---

## 1. Directory Structure

```
integration/
├── custom_components/
│   └── smart_drip/
│       ├── __init__.py           # Component lifecycle, coordinator registration, service registration
│       ├── calc.py               # Pure math engine: FAO-56 Penman-Monteith, deficit equations
│       ├── const.py              # Constants, entity identifiers, threshold defaults
│       ├── coordinator.py        # SmartDripCoordinator: weather ingestion, morning scheduler
│       ├── interlock.py          # SolenoidInterlock: mutual exclusion, 10s pause, safety ceiling
│       ├── sensor.py             # Decision status sensor, ET0 gauge, deficit gauge, duration gauge
│       ├── switch.py             # Auto-irrigation toggles per zone
│       ├── button.py             # Manual run trigger buttons
│       ├── config_flow.py        # UI setup and OptionsFlowWithConfigEntry calibration
│       ├── manifest.json         # HA integration manifest (strict alphabetical sorting)
│       ├── services.yaml         # Schema for calculate_now, reset_bucket, run_zone
│       └── strings.json          # UI localization strings
├── tests/
│   ├── conftest.py               # Custom integration pytest fixtures
│   ├── test_calc.py              # Math and state machine unit tests
│   ├── test_coordinator.py       # Coordinator telemetry, scheduler, and deficit tests
│   ├── test_entities.py          # Sensor, switch, button, service, and unload tests
│   ├── test_interlock.py         # Hardware interlock, mutual exclusion, safety tests
│   └── test_config_flow.py       # Config flow and options flow tests
├── pyproject.toml                # UV package definition, Ruff config, fail_under=70 coverage
├── mise.toml                     # Mise tasks: test, lint, format, typecheck
├── uv.lock                       # Pinned dependency lockfile
├── hacs.json                     # HACS metadata
├── README.md                     # Integration user guide
└── AGENTS.md                     # Developer & agent guide (this file)
```

---

## 2. Core Architectural Principles

1. **Decoupled Math Engine (`calc.py`)**:
   Keep math formulas completely free of Home Assistant imports to ensure instantaneous, deterministic unit testing.
2. **Solenoid Interlock Protection (`interlock.py`)**:
   The Sonoff SWV-ZF2 hardware uses latching pulse solenoids with internal capacitors. Actuation of both channels simultaneously is physically forbidden. An idle pause of $\ge 10\text{ seconds}$ is mandatory between operations.
3. **Safety Clamping**:
   Irrigation runtime must be clamped to a maximum of $2700\text{ s}$ (45 min) by default, with a hard watchdog limit of $3600\text{ s}$ (60 min).
4. **Transparent Decision Status (`sensor.py`)**:
   The zone status sensor must always display human-readable reasoning in its `reason` attribute explaining why irrigation is running or why it was skipped.

---

## 3. Toolchain & Testing

```bash
# Run tests with coverage report (enforced >= 70%)
uv run pytest

# Check linting and formatting
uv run ruff check .
uv run ruff format --check .

# Static type check
uv run mypy custom_components/smart_drip
```
