# Architecture & Technical Design Specification: `smart_drip`

Comprehensive reference document capturing hardware constraints, physical topology, sensor telemetry mapping, mathematical models, and custom integration design for the **Sonoff SWV-ZF2**, **Tempest WeatherFlow**, and **Gardena 15mm Micro-Drip** system.

---

## 1. Physical Plumbing & Hydraulic Hardware Stack

### 1.1 In-Line Topology
The physical installation order is strictly enforced:
$$\text{Municipal Tap (2--5 bar)} \longrightarrow \text{Sonoff SWV-ZF2 Smart Valve} \longrightarrow \text{Gardena Huvudenhet 1000 (13333-20)} \longrightarrow \text{15mm Micro-Drip Pipe}$$

* **Sonoff SWV-ZF2**: Requires mains pressure ($\ge 1.0\text{ bar}$) to reliably seat and latch internal pilot-assisted solenoids.
* **Gardena Huvudenhet 1000 (Master Unit 1000)**:
  * Integrated 40-mesh water filter protects micro-drip labyrinths from particulate clogging.
  * Clamps downstream dynamic working pressure to precisely **$1.5\text{ bar}$ ($21.8\text{ psi}$)**.
  * Absorbs solenoid shutoff shockwaves (water hammer protection).
  * Capacity: Up to $1000\text{ L/h}$ ($16.6\text{ L/min}$).

### 1.2 Valve Physical & Firmware Constraints
* **Mutual Exclusion**: Hardware cannot actuate both latching solenoids simultaneously. Opening Channel 2 automatically forces Channel 1 closed in MCU firmware.
* **Interlock Requirement**: A mandatory **10-second idle pause** must separate closing Channel 1 and opening Channel 2 to allow the latching capacitors to recharge and pipe pressure to equalize.
* **Low-Flow Turbine Stall**: The internal Hall-effect turbine has a detection stall threshold at $\approx 1.5\text{--}2.0\text{ L/min}$ ($90\text{--}120\text{ L/h}$). A typical 40 L/h micro-drip line hovers at $\approx 0.67\text{ L/min}$, meaning volume measurement must rely on **calibrated flow rate $\times$ duration**, not raw turbine counts.
* **Hardware Quirk Configuration** (`/workspace/water-valve/quirk.py`):
  * `water_shortage_alarm`: **`OFF`** (Prevents false dry-run trip-off).
  * `water_shortage_auto_close`: **`OFF`** (Prevents valve preemption on low flow).
  * `alarm_water_shortage_duration`: **`10 min`**.
  * `default_irrigation_duration`: **`45 min`** (Hardware safety ceiling).
  * `safety_run_limit`: **`60 min`** (Emergency dead-man's switch).
  * `water_leak_alarm`: **`ON`** (`alarm_water_leak_duration`: `2 min`).

---

## 2. Weather Telemetry: Tempest WeatherFlow

### 2.1 Live Entity Mappings in Home Assistant
Verified and active from user's Home Assistant instance:
* **Air Temperature**: `sensor.vaderstation_temperatur` ($^\circ\text{C}$)
* **Relative Humidity**: `sensor.vaderstation_luftfuktighet` ($\%$)
* **Dewpoint**: `sensor.vaderstation_daggpunkt` ($^\circ\text{C}$)
* **Solar Radiation**: `sensor.vaderstation_stralning` ($kW/m^2$ or $W/m^2$)
* **Wind Speed**: `sensor.vaderstation_vindhastighet` ($m/s$)
* **Barometric Pressure**: `sensor.vaderstation_lufttryck` ($hPa$)
* **Daily Precipitation Accumulation**: `sensor.vaderstation_nederbord` ($mm$)
* **Instantaneous Rain Intensity**: `sensor.vaderstation_nederbordsintensitet` ($mm/h$)

### 2.2 Redundancy & Precipitation Checks
* **Rain Today Cutoff**: If $\text{Rain Today} \ge 2.5\text{ mm}$, abort cycle.
* **Instant Rain Detection**: If active precipitation $> 0\text{ mm/h}$ or haptic sensor `on`, abort cycle.
* **Yesterday Heavy Soak**: If yesterday's rain $\ge 10.0\text{ mm}$, bypass the morning run.
* **Frost Protection**: If ambient temperature $< 4.0^\circ\text{C}$, abort cycle.

---

## 3. Zone Calibrations

### Zone 1 ("Stora rabatten")
* **Status**: Active / Enabled
* **Valve Entity**: `switch.sonoff_water_valve_channel_1`
* **Area**: $4.8\text{ m}^2$
* **Total Flow Rate**: $40\text{ L/h} = \mathbf{0.67\text{ L/min}}$
* **Precipitation Rate**:
  $$P_r = \frac{40\text{ L/h}}{4.8\text{ m}^2} = \mathbf{8.33\text{ mm/h}} \quad (\approx 0.139\text{ mm/min})$$
* **Runtime Conversion**:
  $$\text{Duration (seconds)} = \frac{\text{Deficit (mm)}}{8.33\text{ mm/h}} \times 3600 = \text{Deficit (mm)} \times 432\text{ s}$$

### Zone 2 ("Zon 2")
* **Status**: Template / Disabled by default until planted
* **Valve Entity**: `switch.sonoff_water_valve_channel_2`
* **Area**: Default $5.0\text{ m}^2$ (Configurable)
* **Total Flow Rate**: Default $40\text{ L/h} = 0.67\text{ L/min}$ (Configurable)

---

## 4. Evapotranspiration & Water Budget Mathematical Model

### 4.1 FAO-56 Penman-Monteith Reference Evapotranspiration ($ET_0$)
Executed nightly at **23:00** across the aggregated daily telemetry:

$$ET_0 = \frac{0.408 \Delta (R_n - G) + \gamma \frac{900}{T + 273} u_2 (e_s - e_a)}{\Delta + \gamma (1 + 0.34 u_2)}$$

Where:
* $R_n$: Net solar radiation at the crop surface ($MJ/m^2/day$) derived from `sensor.vaderstation_stralning`.
* $G$: Soil heat flux density ($\approx 0$ for daily calculations).
* $T$: Mean daily air temperature ($^\circ\text{C}$) from `sensor.vaderstation_temperatur`.
* $u_2$: Wind speed at 2m height ($m/s$) from `sensor.vaderstation_vindhastighet`.
* $e_s - e_a$: Vapor pressure deficit ($kPa$) calculated from temperature and `sensor.vaderstation_luftfuktighet`.
* $\Delta$: Slope of the vapor pressure curve ($kPa/^\circ\text{C}$).
* $\gamma$: Psychrometric constant derived from `sensor.vaderstation_lufttryck`.

### 4.2 Soil Water Balance & Deficit Equation
$$\text{Deficit}_{t} = \max\left(0, \min(\text{MaxBucket}, \text{Deficit}_{t-1} + ET_0 - \text{Rainfall} - \text{IrrigationApplied})\right)$$

* Max Bucket: $24.0\text{ mm}$ (soil holding capacity for shallow root zones).
* Threshold to trigger irrigation: Deficit $\ge 1.0\text{ mm}$.

---

## 5. Custom Integration Architecture: `custom_components/smart_drip`

### 5.1 File Directory Structure
```
/workspace/water-valve/custom_components/smart_drip/
├── __init__.py           # Component lifecycle, coordinator registration, service registration
├── manifest.json         # Integration manifest, domain "smart_drip", version, dependencies
├── const.py              # Constants, configuration keys, default physical parameters
├── config_flow.py        # Discovery of Tempest device, zone setup wizard, options flow
├── coordinator.py        # Central data coordinator: nightly ET calculations, state machine
├── sensor.py             # Decision status sensor, ET sensor, rainfall sensor, runtime sensor
├── switch.py             # Zone enable/disable toggle, automatic schedule master toggle
├── button.py             # "Run Zone Now" manual trigger buttons with automatic shutoff
└── services.yaml         # Custom service definitions: calculate_now, reset_bucket, run_zone
```

### 5.2 Transparent Decision State Machine (`sensor.smart_drip_<zone>_status`)
Primary observable entity per zone:
* States:
  * **`Ready`**: Water deficit accumulated; scheduled to run at 06:00.
  * **`Running`**: Solenoid active; attributes display countdown and delivered volume.
  * **`Skipped: Active Rain`**: Tempest detected rain during evaluation.
  * **`Skipped: Daily Rain Exceeded`**: Rain today $\ge 2.5\text{ mm}$.
  * **`Skipped: Yesterday Heavy Soak`**: Rain yesterday $\ge 10.0\text{ mm}$.
  * **`Skipped: Zero Deficit`**: Rainfall/low ET met plant water needs.
  * **`Skipped: Low Temperature`**: Temperature $< 4.0^\circ\text{C}$ (freeze protection).
  * **`Skipped: Zone Disabled`**: Zone switch toggled OFF.
* Attributes:
  * `reason`: Explicit human-readable sentence explaining the exact decision.
  * `last_calculated_et0_mm`: Daily $ET_0$.
  * `last_rain_today_mm`: Rainfall recorded today.
  * `current_deficit_mm`: Cumulative water deficit.
  * `target_duration_seconds`: Target runtime (clamped between $0$ and $2700\text{ s}$).
  * `estimated_liters`: Liters to be delivered.
  * `last_run_timestamp`: ISO 8601 timestamp of previous completed run.

### 5.3 Execution Engine (Morning 06:00 Sequence)
1. **06:00 Trigger**:
2. **Evaluate Zone 1 ("Stora rabatten")**:
   * If enabled and state is `Ready`:
     * Open `switch.sonoff_water_valve_channel_1`.
     * Set status to `Running`.
     * Sleep for `target_duration_seconds` (max 45 min).
     * Close `switch.sonoff_water_valve_channel_1`.
     * Update deficit ($\text{Deficit} \leftarrow \text{Deficit} - \text{IrrigationApplied}$).
     * Emit Logbook event: *"Stora rabatten completed: delivered X liters in Y minutes."*
3. **10-Second Hardware Interlock Delay**:
   * Both valves idle; allows line pressure equalization.
4. **Evaluate Zone 2 ("Zon 2")**:
   * If enabled and state is `Ready`:
     * Open `switch.sonoff_water_valve_channel_2`.
     * Sleep for target seconds.
     * Close `switch.sonoff_water_valve_channel_2`.
     * Update deficit.

---

## 6. Pre-Configured Dashboard UI (Lovelace)
A clean, modular Lovelace card layout is specified to provide full visibility:
* Badge for current status and human-readable explanation.
* Live gauges for Daily Evapotranspiration ($ET_0$), Daily Rainfall, and Current Water Deficit.
* Zone toggle switches (Zone 1 / Zone 2).
* One-click manual run buttons.
