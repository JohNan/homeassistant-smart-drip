/**
 * Smart Drip Irrigation Lovelace Card
 * Custom card for Home Assistant to monitor ET0, soil water deficit, telemetry, and control irrigation zones.
 * Version 1.1.0
 */

const CARD_VERSION = "1.1.0";

class SmartDripCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = null;
    this._discoveredEntities = null;
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  setConfig(config) {
    this._config = {
      title: "Smart Drip Irrigation",
      show_gauges: true,
      show_zones: true,
      show_actions: true,
      ...config,
    };
    this._discoveredEntities = null;
    this._render();
  }

  getCardSize() {
    return 6;
  }

  static getConfigElement() {
    return document.createElement("smart-drip-card-editor");
  }

  static getStubConfig(hass, _entities, _entitiesFallback) {
    // Auto-discover default entities if possible
    const et0Entity = Object.keys(hass.states).find((e) =>
      e.startsWith("sensor.smart_drip_") && e.endsWith("_daily_et0")
    ) || "sensor.smart_drip_daily_et0";

    const z1Status = Object.keys(hass.states).find((e) =>
      e.startsWith("sensor.smart_drip_") && e.includes("zone_1_status")
    ) || "sensor.smart_drip_zone_1_status";

    const z2Status = Object.keys(hass.states).find((e) =>
      e.startsWith("sensor.smart_drip_") && e.includes("zone_2_status")
    ) || "sensor.smart_drip_zone_2_status";

    return {
      type: "custom:smart-drip-card",
      title: "Smart Drip Irrigation",
      daily_et0_entity: et0Entity,
      zone_1_status_entity: z1Status,
      zone_2_status_entity: z2Status,
    };
  }

  _discoverEntities() {
    if (this._discoveredEntities) return this._discoveredEntities;
    if (!this._hass) return {};

    const states = this._hass.states;
    const findEntity = (prefix, suffix) => {
      return Object.keys(states).find(
        (id) => id.includes(prefix) && (id.endsWith(suffix) || id.includes(suffix))
      );
    };

    const entities = {
      daily_et0:
        this._config.daily_et0_entity ||
        findEntity("smart_drip", "daily_et0") ||
        "sensor.smart_drip_daily_et0",
      z1_status:
        this._config.zone_1_status_entity ||
        findEntity("smart_drip", "zone_1_status") ||
        "sensor.smart_drip_zone_1_status",
      z2_status:
        this._config.zone_2_status_entity ||
        findEntity("smart_drip", "zone_2_status") ||
        "sensor.smart_drip_zone_2_status",
      z1_deficit:
        this._config.zone_1_deficit_entity ||
        findEntity("smart_drip", "zone_1_deficit") ||
        "sensor.smart_drip_zone_1_deficit",
      z2_deficit:
        this._config.zone_2_deficit_entity ||
        findEntity("smart_drip", "zone_2_deficit") ||
        "sensor.smart_drip_zone_2_deficit",
      z1_duration:
        this._config.zone_1_duration_entity ||
        findEntity("smart_drip", "zone_1_duration") ||
        "sensor.smart_drip_zone_1_duration",
      z2_duration:
        this._config.zone_2_duration_entity ||
        findEntity("smart_drip", "zone_2_duration") ||
        "sensor.smart_drip_zone_2_duration",
      z1_auto:
        this._config.zone_1_auto_entity ||
        findEntity("smart_drip", "zone_1_auto_irrigation") ||
        "switch.smart_drip_zone_1_auto_irrigation",
      z2_auto:
        this._config.zone_2_auto_entity ||
        findEntity("smart_drip", "zone_2_auto_irrigation") ||
        "switch.smart_drip_zone_2_auto_irrigation",
      z1_valve:
        this._config.zone_1_valve_entity ||
        findEntity("sonoff", "channel_1") ||
        "switch.sonoff_water_valve_channel_1",
      z2_valve:
        this._config.zone_2_valve_entity ||
        findEntity("sonoff", "channel_2") ||
        "switch.sonoff_water_valve_channel_2",
      z1_run_btn:
        this._config.zone_1_run_button ||
        findEntity("smart_drip", "run_zone_1") ||
        "button.smart_drip_run_zone_1",
      z2_run_btn:
        this._config.zone_2_run_button ||
        findEntity("smart_drip", "run_zone_2") ||
        "button.smart_drip_run_zone_2",
      rain_today:
        this._config.rain_today_entity ||
        findEntity("smart_drip", "rain_today") ||
        findEntity("vaderstation", "nederbord") ||
        findEntity("weatherflow", "precipitation_today") ||
        "sensor.smart_drip_rain_today",
      rain_tomorrow:
        this._config.rain_tomorrow_entity ||
        findEntity("smart_drip", "rain_tomorrow") ||
        "sensor.smart_drip_rain_tomorrow",
      yesterday_rain:
        this._config.yesterday_rain_entity ||
        findEntity("smart_drip", "yesterday_rain") ||
        "sensor.smart_drip_yesterday_rain",
    };

    this._discoveredEntities = entities;
    return entities;
  }

  _getStatusColor(status) {
    const s = (status || "").toLowerCase();
    if (s.includes("running")) return "var(--info-color, #03a9f4)";
    if (s.includes("ready")) return "var(--success-color, #4caf50)";
    if (s.includes("skipped")) return "var(--warning-color, #ff9800)";
    if (s.includes("idle")) return "var(--primary-color, #2196f3)";
    if (s.includes("error") || s.includes("fail")) return "var(--error-color, #f44336)";
    return "var(--secondary-text-color, #757575)";
  }

  _render() {
    if (!this._hass || !this._config) return;

    const entities = this._discoverEntities();
    const states = this._hass.states;

    const et0State = states[entities.daily_et0];
    const et0Val = et0State ? parseFloat(et0State.state) || 0.0 : 0.0;

    const rainState = states[entities.rain_today];
    const rainVal = rainState ? parseFloat(rainState.state) || 0.0 : 0.0;

    const rainTomorrowState = states[entities.rain_tomorrow];
    const rainTomorrowVal = rainTomorrowState ? parseFloat(rainTomorrowState.state) || 0.0 : 0.0;

    const yesterdayRainState = states[entities.yesterday_rain];
    const yesterdayRainVal = yesterdayRainState ? parseFloat(yesterdayRainState.state) || 0.0 : 0.0;

    const z1StatusState = states[entities.z1_status];
    const z1Status = z1StatusState ? z1StatusState.state : "Unknown";
    const z1Reason = z1StatusState?.attributes?.reason || "System standby";

    const z1DeficitState = states[entities.z1_deficit];
    const z1Deficit = z1DeficitState ? parseFloat(z1DeficitState.state) || 0.0 : 0.0;

    const z1DurationState = states[entities.z1_duration];
    const z1DurationSec = z1DurationState ? parseInt(z1DurationState.state, 10) || 0 : 0;
    const z1DurationMin = Math.round(z1DurationSec / 60);

    const z2StatusState = states[entities.z2_status];
    const z2Status = z2StatusState ? z2StatusState.state : "Unknown";
    const z2Reason = z2StatusState?.attributes?.reason || "System standby";

    const z2DeficitState = states[entities.z2_deficit];
    const z2Deficit = z2DeficitState ? parseFloat(z2DeficitState.state) || 0.0 : 0.0;

    const z2DurationState = states[entities.z2_duration];
    const z2DurationSec = z2DurationState ? parseInt(z2DurationState.state, 10) || 0 : 0;
    const z2DurationMin = Math.round(z2DurationSec / 60);

    const z1AutoState = states[entities.z1_auto];
    const z1AutoOn = z1AutoState ? z1AutoState.state === "on" : true;

    const z2AutoState = states[entities.z2_auto];
    const z2AutoOn = z2AutoState ? z2AutoState.state === "on" : true;

    const z1ValveState = states[entities.z1_valve];
    const z1ValveOpen = z1ValveState ? z1ValveState.state === "on" : false;

    const z2ValveState = states[entities.z2_valve];
    const z2ValveOpen = z2ValveState ? z2ValveState.state === "on" : false;

    const isRunning = z1ValveOpen || z2ValveOpen || z1Status.includes("Running") || z2Status.includes("Running");
    const activeZone = z1ValveOpen ? "Zone 1" : z2ValveOpen ? "Zone 2" : null;

    this.shadowRoot.innerHTML = `
      <style>
        ha-card {
          padding: 16px;
          background: var(--ha-card-background, var(--card-background-color, #fff));
          border-radius: var(--ha-card-border-radius, 12px);
          box-shadow: var(--ha-card-box-shadow, 0 2px 8px rgba(0,0,0,0.08));
          color: var(--primary-text-color, #212121);
          font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif);
        }
        .header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 14px;
        }
        .header-title {
          font-size: 1.25rem;
          font-weight: 600;
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .header-icon {
          color: var(--primary-color, #0288d1);
        }
        .status-badge {
          display: inline-flex;
          align-items: center;
          padding: 4px 10px;
          border-radius: 16px;
          font-size: 0.75rem;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          background: rgba(0, 0, 0, 0.05);
          color: var(--primary-text-color);
        }
        .status-pulse {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          margin-right: 6px;
          display: inline-block;
          animation: pulse 2s infinite ease-in-out;
        }
        @keyframes pulse {
          0% { transform: scale(0.95); opacity: 0.8; }
          50% { transform: scale(1.3); opacity: 1; }
          100% { transform: scale(0.95); opacity: 0.8; }
        }
        .banner {
          background: var(--secondary-background-color, #f7f9fa);
          border-radius: 8px;
          padding: 12px;
          margin-bottom: 16px;
          border-left: 4px solid var(--primary-color, #0288d1);
        }
        .banner-reason {
          font-size: 0.85rem;
          color: var(--secondary-text-color, #616161);
          line-height: 1.35;
          margin-top: 4px;
        }
        .metrics-grid {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 8px;
          margin-bottom: 16px;
        }
        .metric-box {
          background: var(--secondary-background-color, #f7f9fa);
          padding: 10px 8px;
          border-radius: 8px;
          text-align: center;
        }
        .metric-val {
          font-size: 1.15rem;
          font-weight: 700;
          color: var(--primary-text-color, #212121);
        }
        .metric-unit {
          font-size: 0.7rem;
          color: var(--secondary-text-color, #757575);
          font-weight: normal;
        }
        .metric-label {
          font-size: 0.7rem;
          text-transform: uppercase;
          color: var(--secondary-text-color, #757575);
          margin-top: 2px;
          letter-spacing: 0.3px;
        }
        .zones-container {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .zone-card {
          border: 1px solid var(--divider-color, #e0e0e0);
          border-radius: 8px;
          padding: 12px;
          display: flex;
          flex-direction: column;
          gap: 8px;
          background: var(--card-background-color, #ffffff);
        }
        .zone-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        .zone-title {
          font-weight: 600;
          font-size: 0.95rem;
          display: flex;
          align-items: center;
          gap: 6px;
        }
        .zone-controls {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding-top: 6px;
          border-top: 1px dashed var(--divider-color, #e0e0e0);
        }
        .zone-stats {
          display: flex;
          gap: 12px;
          font-size: 0.8rem;
          color: var(--secondary-text-color, #616161);
        }
        .zone-actions {
          display: flex;
          gap: 8px;
          align-items: center;
        }
        button.btn {
          background: var(--primary-color, #0288d1);
          color: white;
          border: none;
          padding: 6px 12px;
          border-radius: 4px;
          font-size: 0.8rem;
          font-weight: 600;
          cursor: pointer;
          display: inline-flex;
          align-items: center;
          gap: 4px;
          transition: background 0.2s;
        }
        button.btn:hover {
          filter: brightness(1.1);
        }
        button.btn:active {
          transform: scale(0.98);
        }
        button.btn.btn-outline {
          background: transparent;
          color: var(--primary-color, #0288d1);
          border: 1px solid var(--primary-color, #0288d1);
        }
        .switch-toggle {
          position: relative;
          display: inline-block;
          width: 36px;
          height: 20px;
        }
        .switch-toggle input {
          opacity: 0;
          width: 0;
          height: 0;
        }
        .slider {
          position: absolute;
          cursor: pointer;
          top: 0; left: 0; right: 0; bottom: 0;
          background-color: #ccc;
          transition: .3s;
          border-radius: 20px;
        }
        .slider:before {
          position: absolute;
          content: "";
          height: 14px;
          width: 14px;
          left: 3px;
          bottom: 3px;
          background-color: white;
          transition: .3s;
          border-radius: 50%;
        }
        input:checked + .slider {
          background-color: var(--primary-color, #0288d1);
        }
        input:checked + .slider:before {
          transform: translateX(16px);
        }
        .quick-actions {
          display: flex;
          justify-content: flex-end;
          gap: 8px;
          margin-top: 14px;
          padding-top: 10px;
          border-top: 1px solid var(--divider-color, #e0e0e0);
        }
        .plan-section {
          margin-top: 16px;
          padding-top: 12px;
          border-top: 1px solid var(--divider-color, #e0e0e0);
        }
        .plan-section-title {
          font-size: 0.8rem;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          color: var(--secondary-text-color, #616161);
          margin-bottom: 10px;
          display: flex;
          align-items: center;
          gap: 6px;
        }
        .plan-forecast-bar {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 10px;
          font-size: 0.82rem;
          color: var(--secondary-text-color, #616161);
        }
        .forecast-chip {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          background: var(--secondary-background-color, #f7f9fa);
          border-radius: 12px;
          padding: 3px 10px;
          font-size: 0.8rem;
          font-weight: 600;
        }
        .plan-zone-row {
          display: flex;
          align-items: flex-start;
          gap: 10px;
          padding: 8px 0;
          border-bottom: 1px dashed var(--divider-color, #e0e0e0);
        }
        .plan-zone-row:last-child {
          border-bottom: none;
        }
        .plan-badge {
          flex-shrink: 0;
          display: inline-flex;
          align-items: center;
          gap: 4px;
          padding: 3px 10px;
          border-radius: 12px;
          font-size: 0.75rem;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.3px;
          min-width: 68px;
          justify-content: center;
        }
        .plan-badge.will-irrigate {
          background: rgba(76, 175, 80, 0.12);
          color: #2e7d32;
          border: 1px solid rgba(76, 175, 80, 0.4);
        }
        .plan-badge.will-skip {
          background: rgba(255, 152, 0, 0.12);
          color: #e65100;
          border: 1px solid rgba(255, 152, 0, 0.4);
        }
        .plan-badge.zone-disabled {
          background: rgba(117, 117, 117, 0.1);
          color: var(--secondary-text-color, #757575);
          border: 1px solid rgba(117, 117, 117, 0.3);
        }
        .plan-zone-detail {
          flex: 1;
          min-width: 0;
        }
        .plan-zone-name {
          font-weight: 600;
          font-size: 0.85rem;
          margin-bottom: 2px;
        }
        .plan-zone-reason {
          font-size: 0.78rem;
          color: var(--secondary-text-color, #616161);
          line-height: 1.3;
        }
        .plan-zone-meta {
          font-size: 0.78rem;
          color: var(--primary-text-color, #212121);
          font-weight: 600;
          margin-top: 2px;
        }
      </style>

      <ha-card>
        <div class="header">
          <div class="header-title">
            <ha-icon class="header-icon" icon="mdi:sprinkler-variant"></ha-icon>
            <span>${this._config.title}</span>
          </div>
          <div class="status-badge" style="border: 1px solid ${this._getStatusColor(isRunning ? 'Running' : z1Status)}">
            <span class="status-pulse" style="background: ${this._getStatusColor(isRunning ? 'Running' : z1Status)}"></span>
            <span>${isRunning ? `Active: ${activeZone || 'Irrigating'}` : z1Status}</span>
          </div>
        </div>

        <div class="banner" style="border-left-color: ${this._getStatusColor(z1Status)}">
          <strong>Decision Telemetry</strong>
          <div class="banner-reason">${z1Reason}</div>
        </div>

        ${
          this._config.show_gauges !== false
            ? `
        <div class="metrics-grid">
          <div class="metric-box">
            <div class="metric-val">${et0Val.toFixed(1)} <span class="metric-unit">mm</span></div>
            <div class="metric-label">Daily ET₀</div>
          </div>
          <div class="metric-box">
            <div class="metric-val">${rainVal.toFixed(1)} <span class="metric-unit">mm</span></div>
            <div class="metric-label">Rain Today</div>
          </div>
          <div class="metric-box">
            <div class="metric-val">${z1Deficit.toFixed(1)} <span class="metric-unit">mm</span></div>
            <div class="metric-label">Z1 Deficit</div>
          </div>
          <div class="metric-box">
            <div class="metric-val">${z1DurationMin} <span class="metric-unit">min</span></div>
            <div class="metric-label">Z1 Target</div>
          </div>
        </div>
        `
            : ""
        }

        ${
          this._config.show_zones !== false
            ? `
        <div class="zones-container">
          <!-- Zone 1 -->
          <div class="zone-card">
            <div class="zone-header">
              <div class="zone-title">
                <ha-icon icon="mdi:flower" style="color: #4caf50;"></ha-icon>
                <span>Zone 1: Stora rabatten</span>
                ${
                  z1ValveOpen
                    ? `<span style="font-size:0.75rem; color:#03a9f4; font-weight:bold;">(OPEN)</span>`
                    : ""
                }
              </div>
              <div style="display:flex; align-items:center; gap:8px;">
                <span style="font-size:0.75rem; color:var(--secondary-text-color);">Auto</span>
                <label class="switch-toggle">
                  <input type="checkbox" id="z1-auto-toggle" ${z1AutoOn ? "checked" : ""}>
                  <span class="slider"></span>
                </label>
              </div>
            </div>
            <div class="zone-controls">
              <div class="zone-stats">
                <span>Deficit: <strong>${z1Deficit.toFixed(1)} mm</strong></span>
                <span>Est: <strong>${z1DurationMin} min</strong></span>
              </div>
              <div class="zone-actions">
                <button class="btn" id="z1-run-btn">
                  <ha-icon icon="mdi:play" style="--mdc-icon-size:16px;"></ha-icon>
                  <span>Manual Run</span>
                </button>
              </div>
            </div>
          </div>

          <!-- Zone 2 -->
          <div class="zone-card">
            <div class="zone-header">
              <div class="zone-title">
                <ha-icon icon="mdi:sprout" style="color: #8bc34a;"></ha-icon>
                <span>Zone 2: Zon 2</span>
                ${
                  z2ValveOpen
                    ? `<span style="font-size:0.75rem; color:#03a9f4; font-weight:bold;">(OPEN)</span>`
                    : ""
                }
              </div>
              <div style="display:flex; align-items:center; gap:8px;">
                <span style="font-size:0.75rem; color:var(--secondary-text-color);">Auto</span>
                <label class="switch-toggle">
                  <input type="checkbox" id="z2-auto-toggle" ${z2AutoOn ? "checked" : ""}>
                  <span class="slider"></span>
                </label>
              </div>
            </div>
            <div class="zone-controls">
              <div class="zone-stats">
                <span>Deficit: <strong>${z2Deficit.toFixed(1)} mm</strong></span>
                <span>Est: <strong>${z2DurationMin} min</strong></span>
              </div>
              <div class="zone-actions">
                <button class="btn" id="z2-run-btn">
                  <ha-icon icon="mdi:play" style="--mdc-icon-size:16px;"></ha-icon>
                  <span>Manual Run</span>
                </button>
              </div>
            </div>
          </div>
        </div>
        `
            : ""
        }

        ${this._buildTomorrowPlanHtml(
          z1Status, z1Reason, z1DurationMin,
          z1AutoOn, z2Status, z2Reason, z2DurationMin,
          z2AutoOn, rainTomorrowVal, yesterdayRainVal
        )}

        ${
          this._config.show_actions !== false
            ? `
        <div class="quick-actions">
          <button class="btn btn-outline" id="btn-recalculate">
            <ha-icon icon="mdi:calculator" style="--mdc-icon-size:16px;"></ha-icon>
            <span>Recalculate ET₀</span>
          </button>
          <button class="btn btn-outline" id="btn-reset-deficit">
            <ha-icon icon="mdi:refresh" style="--mdc-icon-size:16px;"></ha-icon>
            <span>Reset Deficit</span>
          </button>
        </div>
        `
            : ""
        }
      </ha-card>
    `;

    this._attachEventHandlers(entities);
  }

  _buildTomorrowPlanHtml(
    z1Status, z1Reason, z1DurationMin,
    z1AutoOn, z2Status, z2Reason, z2DurationMin,
    z2AutoOn, rainTomorrowVal, yesterdayRainVal
  ) {
    const _zoneRow = (zoneName, status, reason, durationMin, autoOn) => {
      const s = (status || "").toLowerCase();
      const willIrrigate = s.includes("ready");
      const isDisabled = s.includes("disabled");

      let badgeClass = "will-skip";
      let badgeIcon = "mdi:water-off";
      let badgeLabel = "Skip";
      if (willIrrigate) {
        badgeClass = "will-irrigate";
        badgeIcon = "mdi:water";
        badgeLabel = "Irrigate";
      } else if (isDisabled) {
        badgeClass = "zone-disabled";
        badgeIcon = "mdi:cancel";
        badgeLabel = "Disabled";
      }

      const metaLine = willIrrigate && !autoOn
        ? `<div class="plan-zone-meta">⚠️ Auto-mode OFF — manual trigger needed</div>`
        : willIrrigate && durationMin > 0
        ? `<div class="plan-zone-meta">⏱ Est. ${durationMin} min starting 06:00</div>`
        : "";

      return `
        <div class="plan-zone-row">
          <span class="plan-badge ${badgeClass}">
            <ha-icon icon="${badgeIcon}" style="--mdc-icon-size:13px;"></ha-icon>
            ${badgeLabel}
          </span>
          <div class="plan-zone-detail">
            <div class="plan-zone-name">${zoneName}</div>
            <div class="plan-zone-reason">${reason}</div>
            ${metaLine}
          </div>
        </div>`;
    };

    const rainForecastColor = rainTomorrowVal >= 5 ? "var(--info-color, #03a9f4)" : "var(--secondary-text-color, #757575)";
    const yesterdayColor = yesterdayRainVal >= 10 ? "var(--info-color, #03a9f4)" : "var(--secondary-text-color, #757575)";

    return `
      <div class="plan-section">
        <div class="plan-section-title">
          <ha-icon icon="mdi:calendar-clock" style="--mdc-icon-size:15px;"></ha-icon>
          Tomorrow's Schedule
        </div>
        <div class="plan-forecast-bar">
          <span>Forecast:</span>
          <span class="forecast-chip" style="color: ${rainForecastColor};">
            <ha-icon icon="mdi:weather-rainy" style="--mdc-icon-size:14px;"></ha-icon>
            ${rainTomorrowVal.toFixed(1)} mm tomorrow
          </span>
          <span class="forecast-chip" style="color: ${yesterdayColor};">
            <ha-icon icon="mdi:history" style="--mdc-icon-size:14px;"></ha-icon>
            ${yesterdayRainVal.toFixed(1)} mm yesterday
          </span>
        </div>
        ${_zoneRow("Zone 1: Stora rabatten", z1Status, z1Reason, z1DurationMin, z1AutoOn)}
        ${_zoneRow("Zone 2", z2Status, z2Reason, z2DurationMin, z2AutoOn)}
      </div>`;
  }

  _attachEventHandlers(entities) {
    const root = this.shadowRoot;

    // Zone 1 Auto Toggle
    const z1Toggle = root.getElementById("z1-auto-toggle");
    if (z1Toggle) {
      z1Toggle.addEventListener("change", (e) => {
        this._callService("switch", "toggle", { entity_id: entities.z1_auto });
      });
    }

    // Zone 2 Auto Toggle
    const z2Toggle = root.getElementById("z2-auto-toggle");
    if (z2Toggle) {
      z2Toggle.addEventListener("change", (e) => {
        this._callService("switch", "toggle", { entity_id: entities.z2_auto });
      });
    }

    // Zone 1 Run Button
    const z1RunBtn = root.getElementById("z1-run-btn");
    if (z1RunBtn) {
      z1RunBtn.addEventListener("click", () => {
        if (entities.z1_run_btn && this._hass.states[entities.z1_run_btn]) {
          this._callService("button", "press", { entity_id: entities.z1_run_btn });
        } else {
          this._callService("smart_drip", "run_zone", { zone: 1, duration: 600 });
        }
      });
    }

    // Zone 2 Run Button
    const z2RunBtn = root.getElementById("z2-run-btn");
    if (z2RunBtn) {
      z2RunBtn.addEventListener("click", () => {
        if (entities.z2_run_btn && this._hass.states[entities.z2_run_btn]) {
          this._callService("button", "press", { entity_id: entities.z2_run_btn });
        } else {
          this._callService("smart_drip", "run_zone", { zone: 2, duration: 600 });
        }
      });
    }

    // Recalculate Button
    const btnRecalc = root.getElementById("btn-recalculate");
    if (btnRecalc) {
      btnRecalc.addEventListener("click", () => {
        this._callService("smart_drip", "calculate_now", {});
      });
    }

    // Reset Deficit Button
    const btnReset = root.getElementById("btn-reset-deficit");
    if (btnReset) {
      btnReset.addEventListener("click", () => {
        this._callService("smart_drip", "reset_bucket", { zone: "all" });
      });
    }
  }

  _callService(domain, service, data) {
    if (!this._hass) return;
    this._hass.callService(domain, service, data);
  }
}

// Visual Card Editor for Dashboard UI
class SmartDripCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
  }

  setConfig(config) {
    this._config = config;
    this._render();
  }

  _render() {
    this.shadowRoot.innerHTML = `
      <style>
        .editor-row {
          display: flex;
          flex-direction: column;
          margin-bottom: 12px;
        }
        label {
          font-weight: 500;
          font-size: 0.85rem;
          margin-bottom: 4px;
          color: var(--primary-text-color, #212121);
        }
        input[type="text"] {
          padding: 8px;
          border-radius: 4px;
          border: 1px solid var(--divider-color, #ccc);
          background: var(--card-background-color, #fff);
          color: var(--primary-text-color, #212121);
        }
        .checkbox-row {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 8px;
        }
      </style>
      <div class="editor-container">
        <div class="editor-row">
          <label>Card Title</label>
          <input type="text" id="title" value="${this._config.title || "Smart Drip Irrigation"}">
        </div>
        <div class="checkbox-row">
          <input type="checkbox" id="show_gauges" ${this._config.show_gauges !== false ? "checked" : ""}>
          <label for="show_gauges">Show Telemetry Gauges</label>
        </div>
        <div class="checkbox-row">
          <input type="checkbox" id="show_zones" ${this._config.show_zones !== false ? "checked" : ""}>
          <label for="show_zones">Show Zones Control</label>
        </div>
        <div class="checkbox-row">
          <input type="checkbox" id="show_actions" ${this._config.show_actions !== false ? "checked" : ""}>
          <label for="show_actions">Show Quick Actions</label>
        </div>
      </div>
    `;

    const titleInput = this.shadowRoot.getElementById("title");
    titleInput.addEventListener("change", (e) => {
      this._updateConfig("title", e.target.value);
    });

    const gaugesCheck = this.shadowRoot.getElementById("show_gauges");
    gaugesCheck.addEventListener("change", (e) => {
      this._updateConfig("show_gauges", e.target.checked);
    });

    const zonesCheck = this.shadowRoot.getElementById("show_zones");
    zonesCheck.addEventListener("change", (e) => {
      this._updateConfig("show_zones", e.target.checked);
    });

    const actionsCheck = this.shadowRoot.getElementById("show_actions");
    actionsCheck.addEventListener("change", (e) => {
      this._updateConfig("show_actions", e.target.checked);
    });
  }

  _updateConfig(key, value) {
    this._config = { ...this._config, [key]: value };
    const event = new CustomEvent("config-changed", {
      detail: { config: this._config },
      bubbles: true,
      composed: true,
    });
    this.dispatchEvent(event);
  }
}

// Register Custom Elements
customElements.define("smart-drip-card", SmartDripCard);
customElements.define("smart-drip-card-editor", SmartDripCardEditor);

// Register in Home Assistant Custom Card Picker UI
window.customCards = window.customCards || [];
window.customCards.push({
  type: "smart-drip-card",
  name: "Smart Drip Irrigation Card",
  description: "Monitor ET0, soil water deficit, weather telemetry, and control smart micro-drip zones.",
  preview: true,
  documentationURL: "https://github.com/JohNan/homeassistant-smart-drip",
});

console.info(
  `%c SMART-DRIP-CARD %c v${CARD_VERSION} `,
  "color: white; background: #0288d1; font-weight: 700; border-radius: 2px 0 0 2px;",
  "color: #0288d1; background: #e1f5fe; font-weight: 700; border-radius: 0 2px 2px 0;"
);
