/**
 * Smart Drip Irrigation Lovelace Card
 * Custom card for Home Assistant to monitor ET0, soil water deficit, telemetry, and control irrigation zones.
 * Git Commit Hash: ec96825
 */

const CARD_VERSION = "ec96825";

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
      z1_last_run:
        this._config.zone_1_last_run_entity ||
        findEntity("smart_drip", "zone_1_last_run") ||
        "sensor.smart_drip_zone_1_last_run",
      z2_last_run:
        this._config.zone_2_last_run_entity ||
        findEntity("smart_drip", "zone_2_last_run") ||
        "sensor.smart_drip_zone_2_last_run",
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

  _formatLastRunInfo(isoString, durationSec, liters, mm, trigger) {
    if (!isoString) return { dateStr: "Never", statsStr: "No previous runs recorded", hasRun: false };
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return { dateStr: String(isoString), statsStr: "", hasRun: true };

    const now = new Date();
    const isToday = date.toDateString() === now.toDateString();
    const yesterday = new Date(now);
    yesterday.setDate(yesterday.getDate() - 1);
    const isYesterday = date.toDateString() === yesterday.toDateString();

    const hours = String(date.getHours()).padStart(2, "0");
    const minutes = String(date.getMinutes()).padStart(2, "0");
    const timeStr = `${hours}:${minutes}`;

    const diffMs = Math.max(0, now.getTime() - date.getTime());
    const diffMins = Math.floor(diffMs / (1000 * 60));
    let relative = "";
    if (diffMins < 60) {
      relative = `${diffMins}m ago`;
    } else {
      const diffHours = Math.floor(diffMins / 60);
      if (diffHours < 24) {
        relative = `${diffHours}h ago`;
      } else {
        const diffDays = Math.floor(diffHours / 24);
        relative = `${diffDays}d ago`;
      }
    }

    let dateStr = "";
    if (isToday) {
      dateStr = `Today at ${timeStr} (${relative})`;
    } else if (isYesterday) {
      dateStr = `Yesterday at ${timeStr} (${relative})`;
    } else {
      const month = date.toLocaleString("en-US", { month: "short" });
      const day = date.getDate();
      dateStr = `${month} ${day}, ${timeStr} (${relative})`;
    }

    const durMin = Math.round((durationSec || 0) / 60);
    const lVal = parseFloat(liters) || 0;
    const mmVal = parseFloat(mm) || 0;
    const trigText = trigger === "manual" ? "Manual" : "Auto 06:00";
    const statsParts = [];
    if (durMin > 0) statsParts.push(`${durMin} min`);
    if (lVal > 0) statsParts.push(`${lVal.toFixed(1)} L`);
    if (mmVal > 0) statsParts.push(`${mmVal.toFixed(1)} mm`);
    statsParts.push(trigText);
    const statsStr = statsParts.join(" · ");

    return { dateStr, statsStr, hasRun: true, durMin, lVal, mmVal, trigText };
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

    const z1LastRunState = states[entities.z1_last_run];
    const z2LastRunState = states[entities.z2_last_run];

    const z1LastRunTs =
      z1LastRunState?.state && z1LastRunState.state !== "unavailable" && z1LastRunState.state !== "unknown"
        ? z1LastRunState.state
        : z1StatusState?.attributes?.last_run_timestamp;
    const z1LastRunDurationSec =
      z1LastRunState?.attributes?.duration_seconds ?? z1StatusState?.attributes?.last_run_duration_seconds ?? 0;
    const z1LastRunLiters =
      z1LastRunState?.attributes?.liters ?? z1StatusState?.attributes?.last_run_liters ?? 0.0;
    const z1LastRunMm =
      z1LastRunState?.attributes?.applied_mm ?? z1StatusState?.attributes?.last_run_applied_mm ?? 0.0;
    const z1LastRunTrigger =
      z1LastRunState?.attributes?.trigger ?? z1StatusState?.attributes?.last_run_trigger;
    const z1LastRunInfo = this._formatLastRunInfo(
      z1LastRunTs,
      z1LastRunDurationSec,
      z1LastRunLiters,
      z1LastRunMm,
      z1LastRunTrigger
    );

    const z2LastRunTs =
      z2LastRunState?.state && z2LastRunState.state !== "unavailable" && z2LastRunState.state !== "unknown"
        ? z2LastRunState.state
        : z2StatusState?.attributes?.last_run_timestamp;
    const z2LastRunDurationSec =
      z2LastRunState?.attributes?.duration_seconds ?? z2StatusState?.attributes?.last_run_duration_seconds ?? 0;
    const z2LastRunLiters =
      z2LastRunState?.attributes?.liters ?? z2StatusState?.attributes?.last_run_liters ?? 0.0;
    const z2LastRunMm =
      z2LastRunState?.attributes?.applied_mm ?? z2StatusState?.attributes?.last_run_applied_mm ?? 0.0;
    const z2LastRunTrigger =
      z2LastRunState?.attributes?.trigger ?? z2StatusState?.attributes?.last_run_trigger;
    const z2LastRunInfo = this._formatLastRunInfo(
      z2LastRunTs,
      z2LastRunDurationSec,
      z2LastRunLiters,
      z2LastRunMm,
      z2LastRunTrigger
    );

    const z1Running =
      z1ValveOpen || (typeof z1Status === "string" && z1Status.toLowerCase().includes("running"));
    const z2Running =
      z2ValveOpen || (typeof z2Status === "string" && z2Status.toLowerCase().includes("running"));
    const isRunning = z1Running || z2Running;
    const activeZone = z1Running ? "Zone 1" : z2Running ? "Zone 2" : null;
    const activeZoneName = z1Running ? "Zone 1: Stora rabatten" : z2Running ? "Zone 2: Zon 2" : "Irrigating";
    const activeDurationSec = z1Running ? (z1DurationSec || 0) : (z2DurationSec || 0);
    const activeDurationMin = Math.round(activeDurationSec / 60);
    const activeLiters = z1Running
      ? (z1StatusState?.attributes?.estimated_liters || (activeDurationSec ? ((activeDurationSec / 3600) * 40).toFixed(1) : "0.0"))
      : (z2StatusState?.attributes?.estimated_liters || (activeDurationSec ? ((activeDurationSec / 3600) * 40).toFixed(1) : "0.0"));

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
        .active-irrigation-card {
          background: linear-gradient(135deg, rgba(3, 169, 244, 0.12) 0%, rgba(2, 136, 209, 0.22) 100%);
          border: 2px solid #03a9f4;
          border-radius: 10px;
          padding: 12px 14px;
          margin-bottom: 16px;
          box-shadow: 0 0 12px rgba(3, 169, 244, 0.35);
          animation: active-glow 2.5s infinite alternate;
        }
        @keyframes active-glow {
          0% { box-shadow: 0 0 6px rgba(3, 169, 244, 0.25); }
          100% { box-shadow: 0 0 16px rgba(3, 169, 244, 0.6); }
        }
        .active-irrigation-header {
          display: flex;
          align-items: center;
          gap: 10px;
        }
        .active-icon-wrapper {
          width: 36px;
          height: 36px;
          border-radius: 50%;
          background: #0288d1;
          display: flex;
          align-items: center;
          justify-content: center;
          color: #fff;
          animation: spin-pulse 3s infinite ease-in-out;
        }
        @keyframes spin-pulse {
          0% { transform: scale(0.95); }
          50% { transform: scale(1.1); }
          100% { transform: scale(0.95); }
        }
        .active-details {
          flex: 1;
        }
        .active-title {
          font-weight: 700;
          font-size: 0.95rem;
          color: var(--primary-text-color, #212121);
        }
        .active-subtitle {
          font-size: 0.78rem;
          color: var(--secondary-text-color, #616161);
          margin-top: 1px;
        }
        .active-badge {
          background: #0288d1;
          color: #fff;
          font-size: 0.68rem;
          font-weight: 700;
          letter-spacing: 0.5px;
          padding: 3px 8px;
          border-radius: 10px;
          animation: pulse 1.5s infinite ease-in-out;
        }
        .active-metrics {
          display: flex;
          gap: 8px;
          margin-top: 10px;
          padding-top: 8px;
          border-top: 1px solid rgba(3, 169, 244, 0.3);
          flex-wrap: wrap;
        }
        .active-metric-chip {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          background: rgba(255, 255, 255, 0.7);
          padding: 3px 8px;
          border-radius: 6px;
          font-size: 0.75rem;
          color: var(--primary-text-color, #212121);
        }
        .zone-card-running {
          border: 2px solid #03a9f4 !important;
          background: rgba(3, 169, 244, 0.04) !important;
        }
        .badge-running-pill {
          display: inline-flex;
          align-items: center;
          gap: 3px;
          background: #0288d1;
          color: #fff;
          font-size: 0.68rem;
          font-weight: 700;
          letter-spacing: 0.4px;
          padding: 2px 7px;
          border-radius: 8px;
          margin-left: 6px;
          animation: pulse 1.5s infinite;
        }
        .zone-last-run-box {
          background: var(--secondary-background-color, #f7f9fa);
          border-radius: 6px;
          padding: 6px 10px;
          margin: 2px 0 4px 0;
          border-left: 3px solid #81c784;
        }
        .zone-last-run-header {
          display: flex;
          align-items: center;
          gap: 5px;
          font-size: 0.78rem;
          color: var(--secondary-text-color, #616161);
        }
        .zone-last-run-header strong {
          color: var(--primary-text-color, #212121);
        }
        .zone-last-run-stats {
          font-size: 0.74rem;
          color: var(--secondary-text-color, #757575);
          margin-top: 2px;
          padding-left: 19px;
        }
        button.btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
          filter: none;
        }
        button.btn.btn-running {
          background: #00acc1;
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

        ${
          isRunning
            ? `
        <div class="active-irrigation-card">
          <div class="active-irrigation-header">
            <div class="active-icon-wrapper">
              <ha-icon icon="mdi:water-pump" class="active-pulse-icon" style="--mdc-icon-size:20px;"></ha-icon>
            </div>
            <div class="active-details">
              <div class="active-title">Currently Irrigating: ${activeZoneName}</div>
              <div class="active-subtitle">Solenoid valve open · 40.0 L/h emitter flow rate</div>
            </div>
            <div class="active-badge">IRRIGATING NOW</div>
          </div>
          <div class="active-metrics">
            <div class="active-metric-chip">
              <ha-icon icon="mdi:timer-outline" style="--mdc-icon-size: 14px;"></ha-icon>
              <span>Target: <strong>${activeDurationMin} min</strong></span>
            </div>
            <div class="active-metric-chip">
              <ha-icon icon="mdi:water" style="--mdc-icon-size: 14px;"></ha-icon>
              <span>Est. Volume: <strong>${activeLiters} L</strong></span>
            </div>
            <div class="active-metric-chip">
              <ha-icon icon="mdi:pipe-valve" style="--mdc-icon-size: 14px;"></ha-icon>
              <span>Active Channel: <strong>${z1Running ? "Channel 1" : "Channel 2"}</strong></span>
            </div>
          </div>
        </div>
        `
            : ""
        }

        <div class="banner" style="border-left-color: ${this._getStatusColor(isRunning ? 'Running' : z1Status)}">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <strong>Decision Telemetry</strong>
            ${
              !isRunning && (z1LastRunInfo.hasRun || z2LastRunInfo.hasRun)
                ? `<span style="font-size:0.75rem; color:var(--secondary-text-color);">Recent Activity Logged</span>`
                : ""
            }
          </div>
          <div class="banner-reason">${isRunning ? `Active irrigation running for ${activeZoneName} (Target ${activeDurationMin} min, est. ${activeLiters} L).` : z1Reason}</div>
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
          <div class="zone-card ${z1Running ? 'zone-card-running' : ''}">
            <div class="zone-header">
              <div class="zone-title">
                <ha-icon icon="mdi:flower" style="color: #4caf50;"></ha-icon>
                <span>Zone 1: Stora rabatten</span>
                ${
                  z1Running
                    ? `<span class="badge-running-pill"><ha-icon icon="mdi:water" style="--mdc-icon-size:12px;"></ha-icon> IRRIGATING</span>`
                    : z1ValveOpen
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

            <div class="zone-last-run-box">
              <div class="zone-last-run-header">
                <ha-icon icon="mdi:history" style="--mdc-icon-size:14px; color:${z1LastRunInfo.hasRun ? '#2e7d32' : 'inherit'};"></ha-icon>
                <span>Last run: <strong>${z1LastRunInfo.dateStr}</strong></span>
              </div>
              ${z1LastRunInfo.hasRun ? `<div class="zone-last-run-stats">${z1LastRunInfo.statsStr}</div>` : ""}
            </div>

            <div class="zone-controls">
              <div class="zone-stats">
                <span>Deficit: <strong>${z1Deficit.toFixed(1)} mm</strong></span>
                <span>Next: <strong>${z1DurationMin} min</strong></span>
              </div>
              <div class="zone-actions">
                <button class="btn ${z1Running ? 'btn-running' : ''}" id="z1-run-btn" ${z1Running ? "disabled" : ""}>
                  <ha-icon icon="${z1Running ? 'mdi:progress-clock' : 'mdi:play'}" style="--mdc-icon-size:16px;"></ha-icon>
                  <span>${z1Running ? 'Irrigating...' : 'Manual Run'}</span>
                </button>
              </div>
            </div>
          </div>

          <!-- Zone 2 -->
          <div class="zone-card ${z2Running ? 'zone-card-running' : ''}">
            <div class="zone-header">
              <div class="zone-title">
                <ha-icon icon="mdi:sprout" style="color: #8bc34a;"></ha-icon>
                <span>Zone 2: Zon 2</span>
                ${
                  z2Running
                    ? `<span class="badge-running-pill"><ha-icon icon="mdi:water" style="--mdc-icon-size:12px;"></ha-icon> IRRIGATING</span>`
                    : z2ValveOpen
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

            <div class="zone-last-run-box">
              <div class="zone-last-run-header">
                <ha-icon icon="mdi:history" style="--mdc-icon-size:14px; color:${z2LastRunInfo.hasRun ? '#2e7d32' : 'inherit'};"></ha-icon>
                <span>Last run: <strong>${z2LastRunInfo.dateStr}</strong></span>
              </div>
              ${z2LastRunInfo.hasRun ? `<div class="zone-last-run-stats">${z2LastRunInfo.statsStr}</div>` : ""}
            </div>

            <div class="zone-controls">
              <div class="zone-stats">
                <span>Deficit: <strong>${z2Deficit.toFixed(1)} mm</strong></span>
                <span>Next: <strong>${z2DurationMin} min</strong></span>
              </div>
              <div class="zone-actions">
                <button class="btn ${z2Running ? 'btn-running' : ''}" id="z2-run-btn" ${z2Running ? "disabled" : ""}>
                  <ha-icon icon="${z2Running ? 'mdi:progress-clock' : 'mdi:play'}" style="--mdc-icon-size:16px;"></ha-icon>
                  <span>${z2Running ? 'Irrigating...' : 'Manual Run'}</span>
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
