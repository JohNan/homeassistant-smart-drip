/**
 * Smart Drip Irrigation Lovelace Cards
 * Custom cards for Home Assistant to monitor ET0, soil water deficit, weather telemetry, and control irrigation zones.
 * Includes:
 *   1. smart-drip-card: Focused zone telemetry, control, and multi-zone tabbed view.
 *   2. smart-drip-schedule-card: Dedicated irrigation dispatch schedule and forecast card.
 * Git Commit Hash: b1eb91d
 */

const CARD_VERSION = "b1eb91d";

class SmartDripCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = null;
    this._discoveredEntities = null;
    this._activeTab = 1;
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  setConfig(config) {
    this._config = {
      title: "",
      zone: "all",
      view_mode: "tabs",
      show_gauges: true,
      show_zones: true,
      show_actions: true,
      show_schedule: false,
      ...config,
    };
    if (this._config.zone === 1 || this._config.zone === "1") {
      this._activeTab = 1;
    } else if (this._config.zone === 2 || this._config.zone === "2") {
      this._activeTab = 2;
    } else if (this._config.view_mode === "stacked") {
      this._activeTab = "all";
    }
    this._discoveredEntities = null;
    this._render();
  }

  getCardSize() {
    return this._config.zone === "all" ? 6 : 4;
  }

  static getConfigElement() {
    return document.createElement("smart-drip-card-editor");
  }

  static getStubConfig(hass, _entities, _entitiesFallback) {
    const et0Entity =
      Object.keys(hass.states).find(
        (e) => e.startsWith("sensor.smart_drip_") && e.endsWith("_daily_et0")
      ) || "sensor.smart_drip_daily_et0";

    const z1Status =
      Object.keys(hass.states).find(
        (e) => e.startsWith("sensor.smart_drip_") && e.includes("zone_1_status")
      ) || "sensor.smart_drip_zone_1_status";

    const z2Status =
      Object.keys(hass.states).find(
        (e) => e.startsWith("sensor.smart_drip_") && e.includes("zone_2_status")
      ) || "sensor.smart_drip_zone_2_status";

    return {
      type: "custom:smart-drip-card",
      title: "",
      zone: "all",
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

    const isZ1 = this._config.zone === 1 || this._config.zone === "1";
    const isZ2 = this._config.zone === 2 || this._config.zone === "2";

    const entities = {
      daily_et0:
        this._config.daily_et0_entity ||
        findEntity("smart_drip", "daily_et0") ||
        "sensor.smart_drip_daily_et0",
      z1_status:
        (isZ1 && this._config.status_entity) ||
        this._config.zone_1_status_entity ||
        findEntity("smart_drip", "zone_1_status") ||
        "sensor.smart_drip_zone_1_status",
      z2_status:
        (isZ2 && this._config.status_entity) ||
        this._config.zone_2_status_entity ||
        findEntity("smart_drip", "zone_2_status") ||
        "sensor.smart_drip_zone_2_status",
      z1_deficit:
        (isZ1 && this._config.deficit_entity) ||
        this._config.zone_1_deficit_entity ||
        findEntity("smart_drip", "zone_1_deficit") ||
        "sensor.smart_drip_zone_1_deficit",
      z2_deficit:
        (isZ2 && this._config.deficit_entity) ||
        this._config.zone_2_deficit_entity ||
        findEntity("smart_drip", "zone_2_deficit") ||
        "sensor.smart_drip_zone_2_deficit",
      z1_duration:
        (isZ1 && this._config.duration_entity) ||
        this._config.zone_1_duration_entity ||
        findEntity("smart_drip", "zone_1_duration") ||
        "sensor.smart_drip_zone_1_duration",
      z2_duration:
        (isZ2 && this._config.duration_entity) ||
        this._config.zone_2_duration_entity ||
        findEntity("smart_drip", "zone_2_duration") ||
        "sensor.smart_drip_zone_2_duration",
      z1_auto:
        (isZ1 && this._config.auto_entity) ||
        this._config.zone_1_auto_entity ||
        findEntity("smart_drip", "zone_1_auto_irrigation") ||
        "switch.smart_drip_zone_1_auto_irrigation",
      z2_auto:
        (isZ2 && this._config.auto_entity) ||
        this._config.zone_2_auto_entity ||
        findEntity("smart_drip", "zone_2_auto_irrigation") ||
        "switch.smart_drip_zone_2_auto_irrigation",
      z1_valve:
        (isZ1 && this._config.valve_entity) ||
        this._config.zone_1_valve_entity ||
        findEntity("smart_drip", "stora_rabatten") ||
        findEntity("sonoff", "channel_1") ||
        "switch.sonoff_water_valve_channel_1",
      z2_valve:
        (isZ2 && this._config.valve_entity) ||
        this._config.zone_2_valve_entity ||
        findEntity("smart_drip", "lilla_rabatten") ||
        findEntity("sonoff", "channel_2") ||
        "switch.sonoff_water_valve_channel_2",
      z1_run_btn:
        (isZ1 && this._config.run_button) ||
        this._config.zone_1_run_button ||
        findEntity("smart_drip", "run_zone_1") ||
        "button.smart_drip_run_zone_1",
      z2_run_btn:
        (isZ2 && this._config.run_button) ||
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
        (isZ1 && this._config.last_run_entity) ||
        this._config.zone_1_last_run_entity ||
        findEntity("smart_drip", "zone_1_last_run") ||
        "sensor.smart_drip_zone_1_last_run",
      z2_last_run:
        (isZ2 && this._config.last_run_entity) ||
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

    const isSingleZ1 = this._config.zone === 1 || this._config.zone === "1";
    const isSingleZ2 = this._config.zone === 2 || this._config.zone === "2";
    const isMultiZone = !isSingleZ1 && !isSingleZ2;

    const z1ValveState = states[entities.z1_valve];
    const z2ValveState = states[entities.z2_valve];

    const z1Name =
      this._config.zone_1_name ||
      z1ValveState?.attributes?.friendly_name ||
      "Stora rabatten";
    const z2Name =
      this._config.zone_2_name ||
      z2ValveState?.attributes?.friendly_name ||
      "Lilla rabatten";

    let cardTitle = this._config.title;
    if (!cardTitle) {
      if (isSingleZ1) cardTitle = `Zone 1: ${z1Name}`;
      else if (isSingleZ2) cardTitle = `Zone 2: ${z2Name}`;
      else cardTitle = "Smart Drip Irrigation";
    }

    const et0State = states[entities.daily_et0];
    const et0Val = et0State ? parseFloat(et0State.state) || 0.0 : 0.0;

    const rainState = states[entities.rain_today];
    const rainVal = rainState ? parseFloat(rainState.state) || 0.0 : 0.0;

    const rainTomorrowState = states[entities.rain_tomorrow];
    const rainTomorrowVal = rainTomorrowState ? parseFloat(rainTomorrowState.state) || 0.0 : 0.0;

    const yesterdayRainState = states[entities.yesterday_rain];
    const yesterdayRainVal = yesterdayRainState ? parseFloat(yesterdayRainState.state) || 0.0 : 0.0;

    // Zone 1 Telemetry
    const z1StatusState = states[entities.z1_status];
    const z1Status = z1StatusState ? z1StatusState.state : "Unknown";
    const z1Reason = z1StatusState?.attributes?.reason || "System standby";

    const z1DeficitState = states[entities.z1_deficit];
    const z1Deficit = z1DeficitState ? parseFloat(z1DeficitState.state) || 0.0 : 0.0;

    const z1DurationState = states[entities.z1_duration];
    const z1DurationSec = z1DurationState ? parseInt(z1DurationState.state, 10) || 0 : 0;
    const z1DurationMin = Math.round(z1DurationSec / 60);

    const z1AutoState = states[entities.z1_auto];
    const z1AutoOn = z1AutoState ? z1AutoState.state === "on" : true;
    const z1ValveOpen = z1ValveState ? z1ValveState.state === "on" : false;

    const z1LastRunState = states[entities.z1_last_run];
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

    // Zone 2 Telemetry
    const z2StatusState = states[entities.z2_status];
    const z2Status = z2StatusState ? z2StatusState.state : "Unknown";
    const z2Reason = z2StatusState?.attributes?.reason || "System standby";

    const z2DeficitState = states[entities.z2_deficit];
    const z2Deficit = z2DeficitState ? parseFloat(z2DeficitState.state) || 0.0 : 0.0;

    const z2DurationState = states[entities.z2_duration];
    const z2DurationSec = z2DurationState ? parseInt(z2DurationState.state, 10) || 0 : 0;
    const z2DurationMin = Math.round(z2DurationSec / 60);

    const z2AutoState = states[entities.z2_auto];
    const z2AutoOn = z2AutoState ? z2AutoState.state === "on" : true;
    const z2ValveOpen = z2ValveState ? z2ValveState.state === "on" : false;

    const z2LastRunState = states[entities.z2_last_run];
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

    const isRunning = isSingleZ1 ? z1Running : isSingleZ2 ? z2Running : z1Running || z2Running;
    const activeZone = z1Running ? "Zone 1" : z2Running ? "Zone 2" : null;
    const activeZoneName = z1Running ? `Zone 1: ${z1Name}` : z2Running ? `Zone 2: ${z2Name}` : "Irrigating";
    const activeDurationSec = z1Running ? z1DurationSec : z2DurationSec;
    const activeDurationMin = Math.round((activeDurationSec || 0) / 60);
    const activeLiters = z1Running
      ? (z1StatusState?.attributes?.estimated_liters || (activeDurationSec ? ((activeDurationSec / 3600) * 40).toFixed(1) : "0.0"))
      : (z2StatusState?.attributes?.estimated_liters || (activeDurationSec ? ((activeDurationSec / 3600) * 40).toFixed(1) : "0.0"));

    // Current focused view evaluation
    let focusedView = isSingleZ1 ? 1 : isSingleZ2 ? 2 : this._activeTab;
    if (this._config.view_mode === "stacked" && isMultiZone) {
      focusedView = "all";
    }

    let badgeStatus = "Unknown";
    let bannerReason = "";
    if (isRunning) {
      badgeStatus = `Active: ${activeZone || 'Irrigating'}`;
      bannerReason = `Active irrigation running for ${activeZoneName} (Target ${activeDurationMin} min, est. ${activeLiters} L).`;
    } else if (focusedView === 1) {
      badgeStatus = z1Status;
      bannerReason = z1Reason;
    } else if (focusedView === 2) {
      badgeStatus = z2Status;
      bannerReason = z2Reason;
    } else {
      badgeStatus = z1Status === z2Status ? z1Status : `${z1Status} / ${z2Status}`;
      bannerReason = `
        <div style="display:flex; flex-direction:column; gap:4px;">
          <div><strong style="color:var(--primary-text-color);">${z1Name}:</strong> ${z1Reason}</div>
          <div><strong style="color:var(--primary-text-color);">${z2Name}:</strong> ${z2Reason}</div>
        </div>`;
    }

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
        .zone-tabs {
          display: flex;
          gap: 6px;
          margin-bottom: 14px;
          background: var(--secondary-background-color, #f7f9fa);
          padding: 4px;
          border-radius: 8px;
          border: 1px solid var(--divider-color, #e0e0e0);
        }
        .zone-tab {
          flex: 1;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 6px;
          padding: 7px 10px;
          border-radius: 6px;
          font-size: 0.82rem;
          font-weight: 600;
          cursor: pointer;
          border: none;
          background: transparent;
          color: var(--secondary-text-color, #616161);
          transition: all 0.2s ease;
        }
        .zone-tab.active {
          background: var(--card-background-color, #fff);
          color: var(--primary-color, #0288d1);
          box-shadow: 0 1px 4px rgba(0,0,0,0.1);
        }
        .zone-tab:hover:not(.active) {
          background: rgba(0, 0, 0, 0.04);
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
        .zone-card-running {
          border: 2px solid #03a9f4 !important;
          background: rgba(3, 169, 244, 0.04) !important;
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
        button.btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
          filter: none;
        }
        button.btn.btn-running {
          background: #00acc1;
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
            <span>${cardTitle}</span>
          </div>
          <div class="status-badge" style="border: 1px solid ${this._getStatusColor(isRunning ? 'Running' : badgeStatus)}">
            <span class="status-pulse" style="background: ${this._getStatusColor(isRunning ? 'Running' : badgeStatus)}"></span>
            <span>${badgeStatus}</span>
          </div>
        </div>

        ${
          isMultiZone && this._config.view_mode !== "stacked"
            ? `
        <div class="zone-tabs">
          <button class="zone-tab ${focusedView === 1 ? 'active' : ''}" id="tab-z1">
            <ha-icon icon="mdi:flower" style="--mdc-icon-size:15px; color:#4caf50;"></ha-icon>
            <span>${z1Name}</span>
            ${z1Running ? '<span class="status-pulse" style="background:#03a9f4; width:6px; height:6px;"></span>' : ''}
          </button>
          <button class="zone-tab ${focusedView === 2 ? 'active' : ''}" id="tab-z2">
            <ha-icon icon="mdi:sprout" style="--mdc-icon-size:15px; color:#8bc34a;"></ha-icon>
            <span>${z2Name}</span>
            ${z2Running ? '<span class="status-pulse" style="background:#03a9f4; width:6px; height:6px;"></span>' : ''}
          </button>
          <button class="zone-tab ${focusedView === 'all' ? 'active' : ''}" id="tab-all">
            <ha-icon icon="mdi:view-dashboard-outline" style="--mdc-icon-size:15px;"></ha-icon>
            <span>Overview</span>
          </button>
        </div>
        `
            : ""
        }

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

        <div class="banner" style="border-left-color: ${this._getStatusColor(isRunning ? 'Running' : (focusedView === 2 ? z2Status : z1Status))}">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <strong>Decision Telemetry</strong>
            ${
              !isRunning && ((focusedView !== 2 && z1LastRunInfo.hasRun) || (focusedView !== 1 && z2LastRunInfo.hasRun))
                ? `<span style="font-size:0.75rem; color:var(--secondary-text-color);">Recent Activity Logged</span>`
                : ""
            }
          </div>
          <div class="banner-reason">${bannerReason}</div>
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
          ${
            focusedView === 1
              ? `
          <div class="metric-box">
            <div class="metric-val">${z1Deficit.toFixed(1)} <span class="metric-unit">mm</span></div>
            <div class="metric-label">Soil Deficit</div>
          </div>
          <div class="metric-box">
            <div class="metric-val">${z1DurationMin} <span class="metric-unit">min</span></div>
            <div class="metric-label">Target Run</div>
          </div>
          `
              : focusedView === 2
              ? `
          <div class="metric-box">
            <div class="metric-val">${z2Deficit.toFixed(1)} <span class="metric-unit">mm</span></div>
            <div class="metric-label">Soil Deficit</div>
          </div>
          <div class="metric-box">
            <div class="metric-val">${z2DurationMin} <span class="metric-unit">min</span></div>
            <div class="metric-label">Target Run</div>
          </div>
          `
              : `
          <div class="metric-box">
            <div class="metric-val">${z1Deficit.toFixed(1)} <span class="metric-unit">mm</span></div>
            <div class="metric-label">Z1 Deficit</div>
          </div>
          <div class="metric-box">
            <div class="metric-val">${z2Deficit.toFixed(1)} <span class="metric-unit">mm</span></div>
            <div class="metric-label">Z2 Deficit</div>
          </div>
          `
          }
        </div>
        `
            : ""
        }

        ${
          this._config.show_zones !== false
            ? `
        <div class="zones-container">
          ${focusedView === 1 || focusedView === "all" ? this._renderZoneCardHtml(1, z1Name, z1Running, z1ValveOpen, z1AutoOn, z1LastRunInfo, z1Deficit, z1DurationMin) : ""}
          ${focusedView === 2 || focusedView === "all" ? this._renderZoneCardHtml(2, z2Name, z2Running, z2ValveOpen, z2AutoOn, z2LastRunInfo, z2Deficit, z2DurationMin) : ""}
        </div>
        `
            : ""
        }

        ${
          this._config.show_schedule === true
            ? this._buildTomorrowPlanHtml(
                z1Name, z1Status, z1Reason, z1DurationMin, z1AutoOn,
                z2Name, z2Status, z2Reason, z2DurationMin, z2AutoOn,
                rainTomorrowVal, yesterdayRainVal, focusedView
              )
            : ""
        }

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

  _renderZoneCardHtml(zoneNum, zoneName, isRunning, isValveOpen, isAutoOn, lastRunInfo, deficitVal, durationMin) {
    const iconName = zoneNum === 1 ? "mdi:flower" : "mdi:sprout";
    const iconColor = zoneNum === 1 ? "#4caf50" : "#8bc34a";
    return `
      <div class="zone-card ${isRunning ? 'zone-card-running' : ''}">
        <div class="zone-header">
          <div class="zone-title">
            <ha-icon icon="${iconName}" style="color: ${iconColor};"></ha-icon>
            <span>Zone ${zoneNum}: ${zoneName}</span>
            ${
              isRunning
                ? `<span class="badge-running-pill"><ha-icon icon="mdi:water" style="--mdc-icon-size:12px;"></ha-icon> IRRIGATING</span>`
                : isValveOpen
                ? `<span style="font-size:0.75rem; color:#03a9f4; font-weight:bold;">(OPEN)</span>`
                : ""
            }
          </div>
          <div style="display:flex; align-items:center; gap:8px;">
            <span style="font-size:0.75rem; color:var(--secondary-text-color);">Auto</span>
            <label class="switch-toggle">
              <input type="checkbox" id="z${zoneNum}-auto-toggle" ${isAutoOn ? "checked" : ""}>
              <span class="slider"></span>
            </label>
          </div>
        </div>

        <div class="zone-last-run-box">
          <div class="zone-last-run-header">
            <ha-icon icon="mdi:history" style="--mdc-icon-size:14px; color:${lastRunInfo.hasRun ? '#2e7d32' : 'inherit'};"></ha-icon>
            <span>Last run: <strong>${lastRunInfo.dateStr}</strong></span>
          </div>
          ${lastRunInfo.hasRun ? `<div class="zone-last-run-stats">${lastRunInfo.statsStr}</div>` : ""}
        </div>

        <div class="zone-controls">
          <div class="zone-stats">
            <span>Deficit: <strong>${deficitVal.toFixed(1)} mm</strong></span>
            <span>Next: <strong>${durationMin} min</strong></span>
          </div>
          <div class="zone-actions">
            <button class="btn ${isRunning ? 'btn-running' : ''}" id="z${zoneNum}-run-btn" ${isRunning ? "disabled" : ""}>
              <ha-icon icon="${isRunning ? 'mdi:progress-clock' : 'mdi:play'}" style="--mdc-icon-size:16px;"></ha-icon>
              <span>${isRunning ? 'Irrigating...' : 'Manual Run'}</span>
            </button>
          </div>
        </div>
      </div>`;
  }

  _buildTomorrowPlanHtml(
    z1Name, z1Status, z1Reason, z1DurationMin, z1AutoOn,
    z2Name, z2Status, z2Reason, z2DurationMin, z2AutoOn,
    rainTomorrowVal, yesterdayRainVal, focusedView
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
        ${focusedView === 1 || focusedView === "all" ? _zoneRow(`Zone 1: ${z1Name}`, z1Status, z1Reason, z1DurationMin, z1AutoOn) : ""}
        ${focusedView === 2 || focusedView === "all" ? _zoneRow(`Zone 2: ${z2Name}`, z2Status, z2Reason, z2DurationMin, z2AutoOn) : ""}
      </div>`;
  }

  _attachEventHandlers(entities) {
    const root = this.shadowRoot;

    // Tabs
    const tabZ1 = root.getElementById("tab-z1");
    if (tabZ1) {
      tabZ1.addEventListener("click", () => {
        this._activeTab = 1;
        this._render();
      });
    }

    const tabZ2 = root.getElementById("tab-z2");
    if (tabZ2) {
      tabZ2.addEventListener("click", () => {
        this._activeTab = 2;
        this._render();
      });
    }

    const tabAll = root.getElementById("tab-all");
    if (tabAll) {
      tabAll.addEventListener("click", () => {
        this._activeTab = "all";
        this._render();
      });
    }

    // Zone 1 Auto Toggle
    const z1Toggle = root.getElementById("z1-auto-toggle");
    if (z1Toggle) {
      z1Toggle.addEventListener("change", () => {
        this._callService("switch", "toggle", { entity_id: entities.z1_auto });
      });
    }

    // Zone 2 Auto Toggle
    const z2Toggle = root.getElementById("z2-auto-toggle");
    if (z2Toggle) {
      z2Toggle.addEventListener("change", () => {
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

// Dedicated Schedule & Forecast Lovelace Card
class SmartDripScheduleCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = null;
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  setConfig(config) {
    this._config = {
      title: "Irrigation Schedule & Forecast",
      show_forecast_chips: true,
      ...config,
    };
    this._render();
  }

  getCardSize() {
    return 4;
  }

  static getConfigElement() {
    return document.createElement("smart-drip-schedule-card-editor");
  }

  static getStubConfig(hass) {
    return {
      type: "custom:smart-drip-schedule-card",
      title: "Irrigation Schedule & Forecast",
    };
  }

  _render() {
    if (!this._hass || !this._config) return;

    const states = this._hass.states;
    const findEntity = (prefix, suffix) => {
      return Object.keys(states).find(
        (id) => id.includes(prefix) && (id.endsWith(suffix) || id.includes(suffix))
      );
    };

    const rainTomorrowEntity =
      this._config.rain_tomorrow_entity ||
      findEntity("smart_drip", "rain_tomorrow") ||
      "sensor.smart_drip_rain_tomorrow";
    const yesterdayRainEntity =
      this._config.yesterday_rain_entity ||
      findEntity("smart_drip", "yesterday_rain") ||
      "sensor.smart_drip_yesterday_rain";
    const rainTodayEntity =
      this._config.rain_today_entity ||
      findEntity("smart_drip", "rain_today") ||
      findEntity("vaderstation", "nederbord") ||
      "sensor.smart_drip_rain_today";

    const z1StatusEntity =
      this._config.zone_1_status_entity ||
      findEntity("smart_drip", "zone_1_status") ||
      "sensor.smart_drip_zone_1_status";
    const z2StatusEntity =
      this._config.zone_2_status_entity ||
      findEntity("smart_drip", "zone_2_status") ||
      "sensor.smart_drip_zone_2_status";

    const z1DurationEntity =
      this._config.zone_1_duration_entity ||
      findEntity("smart_drip", "zone_1_duration") ||
      "sensor.smart_drip_zone_1_duration";
    const z2DurationEntity =
      this._config.zone_2_duration_entity ||
      findEntity("smart_drip", "zone_2_duration") ||
      "sensor.smart_drip_zone_2_duration";

    const z1AutoEntity =
      this._config.zone_1_auto_entity ||
      findEntity("smart_drip", "zone_1_auto_irrigation") ||
      "switch.smart_drip_zone_1_auto_irrigation";
    const z2AutoEntity =
      this._config.zone_2_auto_entity ||
      findEntity("smart_drip", "zone_2_auto_irrigation") ||
      "switch.smart_drip_zone_2_auto_irrigation";

    const z1ValveEntity =
      findEntity("smart_drip", "stora_rabatten") ||
      findEntity("sonoff", "channel_1") ||
      "switch.sonoff_water_valve_channel_1";
    const z2ValveEntity =
      findEntity("smart_drip", "lilla_rabatten") ||
      findEntity("sonoff", "channel_2") ||
      "switch.sonoff_water_valve_channel_2";

    const z1Name =
      this._config.zone_1_name ||
      states[z1ValveEntity]?.attributes?.friendly_name ||
      "Stora rabatten";
    const z2Name =
      this._config.zone_2_name ||
      states[z2ValveEntity]?.attributes?.friendly_name ||
      "Lilla rabatten";

    const rainTomorrowState = states[rainTomorrowEntity];
    const rainTomorrowVal = rainTomorrowState ? parseFloat(rainTomorrowState.state) || 0.0 : 0.0;

    const yesterdayRainState = states[yesterdayRainEntity];
    const yesterdayRainVal = yesterdayRainState ? parseFloat(yesterdayRainState.state) || 0.0 : 0.0;

    const rainTodayState = states[rainTodayEntity];
    const rainTodayVal = rainTodayState ? parseFloat(rainTodayState.state) || 0.0 : 0.0;

    const z1StatusState = states[z1StatusEntity];
    const z1Status = z1StatusState ? z1StatusState.state : "Unknown";
    const z1Reason = z1StatusState?.attributes?.reason || "System standby";

    const z1DurationState = states[z1DurationEntity];
    const z1DurationSec = z1DurationState ? parseInt(z1DurationState.state, 10) || 0 : 0;
    const z1DurationMin = Math.round(z1DurationSec / 60);

    const z1AutoState = states[z1AutoEntity];
    const z1AutoOn = z1AutoState ? z1AutoState.state === "on" : true;

    const z2StatusState = states[z2StatusEntity];
    const z2Status = z2StatusState ? z2StatusState.state : "Unknown";
    const z2Reason = z2StatusState?.attributes?.reason || "System standby";

    const z2DurationState = states[z2DurationEntity];
    const z2DurationSec = z2DurationState ? parseInt(z2DurationState.state, 10) || 0 : 0;
    const z2DurationMin = Math.round(z2DurationSec / 60);

    const z2AutoState = states[z2AutoEntity];
    const z2AutoOn = z2AutoState ? z2AutoState.state === "on" : true;

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
        .dispatch-badge {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          padding: 4px 10px;
          border-radius: 16px;
          font-size: 0.75rem;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          background: rgba(3, 169, 244, 0.1);
          color: var(--primary-color, #0288d1);
          border: 1px solid rgba(3, 169, 244, 0.3);
        }
        .plan-forecast-bar {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 14px;
          flex-wrap: wrap;
        }
        .forecast-chip {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          background: var(--secondary-background-color, #f7f9fa);
          border-radius: 12px;
          padding: 4px 10px;
          font-size: 0.8rem;
          font-weight: 600;
        }
        .plan-zone-row {
          display: flex;
          align-items: flex-start;
          gap: 12px;
          padding: 10px 0;
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
          padding: 4px 10px;
          border-radius: 12px;
          font-size: 0.75rem;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.3px;
          min-width: 72px;
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
          font-size: 0.9rem;
          margin-bottom: 2px;
        }
        .plan-zone-reason {
          font-size: 0.8rem;
          color: var(--secondary-text-color, #616161);
          line-height: 1.35;
        }
        .plan-zone-meta {
          font-size: 0.78rem;
          color: var(--primary-text-color, #212121);
          font-weight: 600;
          margin-top: 3px;
        }
        .plan-footer {
          margin-top: 12px;
          padding-top: 8px;
          border-top: 1px solid var(--divider-color, #e0e0e0);
          font-size: 0.72rem;
          color: var(--secondary-text-color, #757575);
          display: flex;
          align-items: center;
          gap: 6px;
        }
      </style>

      <ha-card>
        <div class="header">
          <div class="header-title">
            <ha-icon class="header-icon" icon="mdi:calendar-clock"></ha-icon>
            <span>${this._config.title}</span>
          </div>
          <div class="dispatch-badge">
            <ha-icon icon="mdi:clock-outline" style="--mdc-icon-size:12px;"></ha-icon>
            <span>06:00 Dispatch</span>
          </div>
        </div>

        ${
          this._config.show_forecast_chips !== false
            ? `
        <div class="plan-forecast-bar">
          <span class="forecast-chip" style="color: ${rainForecastColor};">
            <ha-icon icon="mdi:weather-rainy" style="--mdc-icon-size:14px;"></ha-icon>
            ${rainTomorrowVal.toFixed(1)} mm tomorrow
          </span>
          <span class="forecast-chip" style="color: ${yesterdayColor};">
            <ha-icon icon="mdi:history" style="--mdc-icon-size:14px;"></ha-icon>
            ${yesterdayRainVal.toFixed(1)} mm yesterday
          </span>
          <span class="forecast-chip">
            <ha-icon icon="mdi:water-outline" style="--mdc-icon-size:14px;"></ha-icon>
            ${rainTodayVal.toFixed(1)} mm today
          </span>
        </div>
        `
            : ""
        }

        <div class="plan-zones">
          ${_zoneRow(`Zone 1: ${z1Name}`, z1Status, z1Reason, z1DurationMin, z1AutoOn)}
          ${_zoneRow(`Zone 2: ${z2Name}`, z2Status, z2Reason, z2DurationMin, z2AutoOn)}
        </div>

        <div class="plan-footer">
          <ha-icon icon="mdi:information-outline" style="--mdc-icon-size:13px;"></ha-icon>
          <span>Automated night evaluation runs at 23:59 before morning sequential dispatch.</span>
        </div>
      </ha-card>
    `;
  }
}

// Visual Card Editor for SmartDripCard
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
        .editor-container {
          padding: 8px 0;
          font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif);
        }
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
        input[type="text"], select {
          padding: 8px;
          border-radius: 4px;
          border: 1px solid var(--divider-color, #ccc);
          background: var(--card-background-color, #fff);
          color: var(--primary-text-color, #212121);
          font-size: 0.85rem;
        }
        .checkbox-row {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 8px;
        }
        details {
          margin-top: 12px;
          border: 1px solid var(--divider-color, #e0e0e0);
          border-radius: 6px;
          padding: 8px;
        }
        summary {
          font-weight: 600;
          font-size: 0.85rem;
          cursor: pointer;
          color: var(--primary-color, #0288d1);
        }
      </style>
      <div class="editor-container">
        <div class="editor-row">
          <label>Card Title (Leave blank for automatic)</label>
          <input type="text" id="title" value="${this._config.title || ""}">
        </div>
        <div class="editor-row">
          <label>Monitored Zone</label>
          <select id="zone">
            <option value="all" ${(!this._config.zone || this._config.zone === "all") ? "selected" : ""}>All Zones (Tabbed / Overview)</option>
            <option value="1" ${(this._config.zone === 1 || this._config.zone === "1") ? "selected" : ""}>Zone 1 only</option>
            <option value="2" ${(this._config.zone === 2 || this._config.zone === "2") ? "selected" : ""}>Zone 2 only</option>
          </select>
        </div>
        <div class="editor-row" id="view-mode-row" style="${this._config.zone === 1 || this._config.zone === 2 ? 'display:none;' : ''}">
          <label>All Zones View Mode</label>
          <select id="view_mode">
            <option value="tabs" ${this._config.view_mode !== "stacked" ? "selected" : ""}>Tabs (Compact & Clean)</option>
            <option value="stacked" ${this._config.view_mode === "stacked" ? "selected" : ""}>Stacked (Both visible)</option>
          </select>
        </div>
        <div class="checkbox-row">
          <input type="checkbox" id="show_gauges" ${this._config.show_gauges !== false ? "checked" : ""}>
          <label for="show_gauges">Show Telemetry Gauges</label>
        </div>
        <div class="checkbox-row">
          <input type="checkbox" id="show_zones" ${this._config.show_zones !== false ? "checked" : ""}>
          <label for="show_zones">Show Zone Controls</label>
        </div>
        <div class="checkbox-row">
          <input type="checkbox" id="show_actions" ${this._config.show_actions !== false ? "checked" : ""}>
          <label for="show_actions">Show Quick Actions</label>
        </div>
        <div class="checkbox-row">
          <input type="checkbox" id="show_schedule" ${this._config.show_schedule === true ? "checked" : ""}>
          <label for="show_schedule">Show Schedule Section (or use Smart Drip Schedule Card)</label>
        </div>

        <details>
          <summary>Custom Entity Overrides</summary>
          <div style="margin-top: 8px;">
            <div class="editor-row">
              <label>Status Entity Override</label>
              <input type="text" id="status_entity" value="${this._config.status_entity || ""}" placeholder="e.g. sensor.smart_drip_zone_1_status">
            </div>
            <div class="editor-row">
              <label>Deficit Entity Override</label>
              <input type="text" id="deficit_entity" value="${this._config.deficit_entity || ""}" placeholder="e.g. sensor.smart_drip_zone_1_deficit">
            </div>
            <div class="editor-row">
              <label>Valve Entity Override</label>
              <input type="text" id="valve_entity" value="${this._config.valve_entity || ""}" placeholder="e.g. switch.sonoff_water_valve_channel_1">
            </div>
          </div>
        </details>
      </div>
    `;

    const titleInput = this.shadowRoot.getElementById("title");
    titleInput.addEventListener("change", (e) => {
      this._updateConfig("title", e.target.value);
    });

    const zoneSelect = this.shadowRoot.getElementById("zone");
    zoneSelect.addEventListener("change", (e) => {
      const val = e.target.value;
      this._updateConfig("zone", val === "all" ? "all" : parseInt(val, 10));
      const vmRow = this.shadowRoot.getElementById("view-mode-row");
      if (vmRow) vmRow.style.display = (val === "1" || val === "2") ? "none" : "";
    });

    const viewModeSelect = this.shadowRoot.getElementById("view_mode");
    if (viewModeSelect) {
      viewModeSelect.addEventListener("change", (e) => {
        this._updateConfig("view_mode", e.target.value);
      });
    }

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

    const schedCheck = this.shadowRoot.getElementById("show_schedule");
    schedCheck.addEventListener("change", (e) => {
      this._updateConfig("show_schedule", e.target.checked);
    });

    const statusEntityInput = this.shadowRoot.getElementById("status_entity");
    if (statusEntityInput) {
      statusEntityInput.addEventListener("change", (e) => {
        this._updateConfig("status_entity", e.target.value);
      });
    }

    const deficitEntityInput = this.shadowRoot.getElementById("deficit_entity");
    if (deficitEntityInput) {
      deficitEntityInput.addEventListener("change", (e) => {
        this._updateConfig("deficit_entity", e.target.value);
      });
    }

    const valveEntityInput = this.shadowRoot.getElementById("valve_entity");
    if (valveEntityInput) {
      valveEntityInput.addEventListener("change", (e) => {
        this._updateConfig("valve_entity", e.target.value);
      });
    }
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

// Visual Card Editor for SmartDripScheduleCard
class SmartDripScheduleCardEditor extends HTMLElement {
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
        .editor-container {
          padding: 8px 0;
          font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif);
        }
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
          font-size: 0.85rem;
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
          <input type="text" id="title" value="${this._config.title || "Irrigation Schedule & Forecast"}">
        </div>
        <div class="checkbox-row">
          <input type="checkbox" id="show_forecast_chips" ${this._config.show_forecast_chips !== false ? "checked" : ""}>
          <label for="show_forecast_chips">Show Weather Forecast Chips</label>
        </div>
      </div>
    `;

    const titleInput = this.shadowRoot.getElementById("title");
    titleInput.addEventListener("change", (e) => {
      this._updateConfig("title", e.target.value);
    });

    const forecastCheck = this.shadowRoot.getElementById("show_forecast_chips");
    forecastCheck.addEventListener("change", (e) => {
      this._updateConfig("show_forecast_chips", e.target.checked);
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
customElements.define("smart-drip-schedule-card", SmartDripScheduleCard);
customElements.define("smart-drip-schedule-card-editor", SmartDripScheduleCardEditor);

// Register in Home Assistant Custom Card Picker UI
window.customCards = window.customCards || [];
window.customCards.push({
  type: "smart-drip-card",
  name: "Smart Drip Irrigation Card",
  description: "Monitor ET₀, soil water deficit, weather telemetry, and control smart micro-drip zones.",
  preview: true,
  documentationURL: "https://github.com/JohNan/homeassistant-smart-drip",
});
window.customCards.push({
  type: "smart-drip-schedule-card",
  name: "Smart Drip Schedule Card",
  description: "View tomorrow's 06:00 automated irrigation dispatch plan, skip reasons, and weather forecast.",
  preview: true,
  documentationURL: "https://github.com/JohNan/homeassistant-smart-drip",
});

console.info(
  `%c SMART-DRIP-CARD %c v${CARD_VERSION} `,
  "color: white; background: #0288d1; font-weight: 700; border-radius: 2px 0 0 2px;",
  "color: #0288d1; background: #e1f5fe; font-weight: 700; border-radius: 0 2px 2px 0;"
);
