# Smart Drip Irrigation (`smart_drip`)

Custom Home Assistant integration for smart micro-drip irrigation using the **Sonoff SWV-ZF2** smart water valve, **Tempest WeatherFlow** weather station, and **Gardena 15mm Micro-Drip** infrastructure.

## Key Features

- **Evapotranspiration Math Model**: Nightly calculation of FAO-56 Penman-Monteith reference evapotranspiration ($ET_0$) using live localized sensor telemetry from Tempest WeatherFlow (solar radiation, temperature, relative humidity, wind speed, barometric pressure).
- **Dynamic Water Budget & Deficit Tracking**: Soil moisture deficit modeling with configurable bucket capacity, rain subtraction, and runtime derivation ($40\text{ L/h} \Rightarrow 8.33\text{ mm/h} \Rightarrow 432\text{ s/mm}$).
- **Hardware Interlocks & Solenoid Protection**:
  - Mutual exclusion preventing concurrent dual-channel actuation.
  - Mandatory 10-second idle interlock between channel switches for latching capacitor recharge and pressure stabilization.
  - Automatic software safety ceiling clamped at 45 minutes ($2700\text{ s}$).
- **Transparent Decision State Machine**: Clear status reporting (`Ready`, `Running`, `Skipped: Active Rain`, `Skipped: Daily Rain Exceeded`, `Skipped: Yesterday Heavy Soak`, `Skipped: Low Temperature`, `Skipped: Zero Deficit`, `Skipped: Zone Disabled`) with human-readable diagnostic explanations.
- **Persistent State Storage**: Soil water deficits, yesterday's precipitation totals, and run status are stored persistently in Home Assistant's `.storage` store across system restarts.
- **Cold-Start History Ingestion**: Safely backfills yesterday's rainfall telemetry directly from Home Assistant's built-in recorder database on clean initial installations to arm rainfall soak guards immediately on Day 1.
- **Lovelace Custom Card**: Native custom card (`custom:smart-drip-card`) auto-loaded on integration startup with live $ET_0$/rain/deficit metrics, status decision banner, zone toggles, and manual run controls.

## Dashboard Lovelace Card

The integration automatically registers and serves its custom dashboard card:
* **Card Type**: `custom:smart-drip-card`
* **Auto-Loading**: Automatically injected into the Home Assistant frontend and registered as a Lovelace resource. No manual file copying or resource configuration required.
* **UI Card Picker**: Available directly in the "Add Card" dashboard menu as **Smart Drip Irrigation Card** with visual live preview and visual configuration editor.

### Example YAML Configuration

```yaml
type: custom:smart-drip-card
title: Smart Drip Irrigation
show_gauges: true
show_zones: true
show_actions: true
```

## Development & Testing

This project uses `mise` and `uv` for reproducible environments and task management.

```bash
# Linting & Formatting
mise run lint
mise run format

# Run Test Suite
mise run test

# Type Checking
mise run typecheck
```
