"""Sonoff SWV - Zigbee smart water valve."""

from typing import Any, ClassVar

import zigpy.types as t
from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import (
    QuirkBuilder,
    ReportingConfig,
    SensorDeviceClass,  # Sensor device class
    SensorStateClass,  # Sensor state class (for line charts)
)

# Import unit constants (duration/volume)
from zigpy.quirks.v2.homeassistant import EntityType, UnitOfTime, UnitOfVolume
from zigpy.quirks.v2.homeassistant.binary_sensor import BinarySensorDeviceClass
from zigpy.zcl import foundation
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

try:
    from zhaquirks import LocalDataCluster
except ImportError:
    class LocalDataCluster(CustomCluster):
        """Fallback local cluster implementation."""

        async def bind(self, **kwargs):
            return (foundation.Status.SUCCESS,)

        async def unbind(self):
            return (foundation.Status.SUCCESS,)

        async def _configure_reporting(self, *args, **kwargs):
            return (foundation.ConfigureReportingResponse.deserialize(b"\x00")[0],)

        async def read_attributes_raw(self, attributes, manufacturer=None, **kwargs):
            records = [
                foundation.ReadAttributeRecord(
                    attr,
                    foundation.Status.SUCCESS,
                    foundation.TypeValue(
                        self.find_attribute(attr).zcl_type, self.get(attr)
                    ),
                )
                for attr in attributes
            ]
            return (records,)


def _extract_elements(value: Any) -> list[int] | None:
    """Safely extract list of integer elements from ZCL collection/array."""
    if value is None:
        return None
    if isinstance(value, foundation.Array):
        if value.value is None:
            return None
        return list(value.value)
    if (
        hasattr(value, "value")
        and isinstance(value.value, (list, tuple, bytes, bytearray))
    ):
        return list(value.value)
    if isinstance(value, (list, tuple, bytes, bytearray)):
        return list(value)
    return None


class ValveState(t.enum8):
    """Water valve state (8-bit value, bit-defined)."""

    # Basic states (single bit)
    Normal = 0  # 000000 (no abnormal condition)
    Water_Shortage = 1 << 0  # 000001 (bit0: water shortage channel 1)
    Water_Leakage = 1 << 1  # 000010 (bit1: water leakage)
    Anti_Frost_Alarm = 1 << 2  # 000100 (bit2: anti-frost alarm)
    FailSafe_Channel_1 = 1 << 3  # 001000 (bit3: fail-safe shutoff channel 1)
    Water_Shortage_Channel_2 = 1 << 4  # 010000 (bit4: water shortage channel 2)
    FailSafe_Channel_2 = 1 << 5  # 100000 (bit5: fail-safe shutoff channel 2)


class CustomSonoffCluster(CustomCluster):
    """Custom Sonoff cluster."""

    cluster_id = 0xFC11

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        # childLock: {name: "childLock", ID: 0x0000, type: Zcl.DataType.BOOLEAN, write: true},
        child_lock = ZCLAttributeDef(
            id=0x0000, 
            type=t.Bool,
            access="rwp",
            # is_manufacturer_specific=True,
            manufacturer_code=None,
        )

        # realTimeIrrigationDuration: {name: "realTimeIrrigationDuration", ID: 0x5006, type: Zcl.DataType.UINT32},
        realtime_irrigation_duration = ZCLAttributeDef(
            id=0x5006,
            type=t.uint32_t,
            manufacturer_code=None,
        )

        # realTimeIrrigationVolume: {name: "realTimeIrrigationVolume", ID: 0x5007, type: Zcl.DataType.UINT32},
        realtime_irrigation_volume = ZCLAttributeDef(
            id=0x5007,
            type=t.uint32_t,
            manufacturer_code=None,
        )

        # valveAbnormalState: {name: "valveAbnormalState", ID: 0x500c, type: Zcl.DataType.UINT8},
        water_valve_state = ZCLAttributeDef(
            id=0x500C,
            type=ValveState,
            manufacturer_code=None,
        )

        # rainDelayEndDatetime: {name: "rainDelayEndDatetime", ID: 0x5014, type: Zcl.DataType.UINT32},

        # hourIrrigationVolume: {name: "hourIrrigationVolume", ID: 0x501b, type: Zcl.DataType.UINT32},
        hour_irrigation_volume = ZCLAttributeDef(
            id=0x501B,
            type=t.uint32_t,
            manufacturer_code=None,
        )

        # hourIrrigationDuration: {name: "hourIrrigationDuration", ID: 0x501c, type: Zcl.DataType.UINT32},
        hour_irrigation_duration = ZCLAttributeDef(
            id=0x501C,
            type=t.uint32_t,
            manufacturer_code=None,
        )

        # manualDefaultSettings: {name: "manualDefaultSettings", ID: 0x501d, type: Zcl.DataType.ARRAY, write: true},
        manual_default_settings = ZCLAttributeDef(
            id=0x501D,
            type=foundation.Array,
            access="rwp",
            manufacturer_code=None,
        )
        # seasonalWateringAdjustment: {name: "seasonalWateringAdjustment", ID: 0x501e, type: Zcl.DataType.ARRAY, write: true},
        # irrigationScheduleStatus: {name: "irrigationScheduleStatus", ID: 0x501f, type: Zcl.DataType.ARRAY},
        valve_alarm_settings = ZCLAttributeDef(
            id=0x5020,
            type=foundation.Array,
            access="rwp",
            manufacturer_code=None,
        )

    def _update_attribute(self, attrid: int, value: Any) -> None:
        super()._update_attribute(attrid, value)
        alarm_cluster = self.endpoint.in_clusters.get(
            ValveAlarmSettingsCluster.cluster_id
        )
        if alarm_cluster is not None:
            if attrid == self.AttributeDefs.valve_alarm_settings.id:
                alarm_cluster.update_alarm_settings(value)
            elif attrid == self.AttributeDefs.manual_default_settings.id:
                alarm_cluster.update_manual_settings(value)

    async def apply_custom_configuration(self, *args: Any, **kwargs: Any) -> None:
        """Read settings during pairing."""
        await super().apply_custom_configuration(*args, **kwargs)
        if self.endpoint.endpoint_id == 1:
            await self.read_attributes([
                self.AttributeDefs.valve_alarm_settings.id,
                self.AttributeDefs.manual_default_settings.id,
            ])


class ValveAlarmSettingsCluster(LocalDataCluster):
    """Local cluster exposing valve alarm and safety configuration controls."""

    cluster_id = 0xFC20
    ep_attribute = "valve_alarm_settings"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        water_shortage_alarm = ZCLAttributeDef(
            id=0x0000,
            type=t.Bool,
            access="rwp",
        )
        water_leak_alarm = ZCLAttributeDef(
            id=0x0001,
            type=t.Bool,
            access="rwp",
        )
        water_shortage_auto_close = ZCLAttributeDef(
            id=0x0002,
            type=t.Bool,
            access="rwp",
        )
        alarm_water_shortage_duration = ZCLAttributeDef(
            id=0x0003,
            type=t.uint8_t,
            access="rwp",
        )
        alarm_water_leak_duration = ZCLAttributeDef(
            id=0x0004,
            type=t.uint8_t,
            access="rwp",
        )
        safety_run_limit = ZCLAttributeDef(
            id=0x0005,
            type=t.uint16_t,
            access="rwp",
        )
        default_irrigation_duration = ZCLAttributeDef(
            id=0x0006,
            type=t.uint16_t,
            access="rwp",
        )

    _ALARM_BITS: ClassVar[dict[int, int]] = {
        AttributeDefs.water_shortage_alarm.id: 0x01,  # bit0: water shortage alarm
        AttributeDefs.water_leak_alarm.id: 0x02,  # bit1: water leak alarm
        AttributeDefs.water_shortage_auto_close.id: 0x08,  # bit3: auto close on water shortage
    }

    _DEFAULT_VALUES: ClassVar[dict[int, Any]] = {
        AttributeDefs.water_shortage_alarm.id: t.Bool.true,
        AttributeDefs.water_leak_alarm.id: t.Bool.true,
        AttributeDefs.water_shortage_auto_close.id: t.Bool.false,
        AttributeDefs.alarm_water_shortage_duration.id: t.uint8_t(1),
        AttributeDefs.alarm_water_leak_duration.id: t.uint8_t(1),
        AttributeDefs.safety_run_limit.id: t.uint16_t(0),
        AttributeDefs.default_irrigation_duration.id: t.uint16_t(30),
    }

    def update_alarm_settings(self, value: Any) -> None:
        """Update local switch and number attributes from valveAlarmSettings array."""
        elements = _extract_elements(value)
        if not elements:
            return

        enable_bits = elements[0]
        for attr_id, bit in self._ALARM_BITS.items():
            self._update_attribute(attr_id, t.Bool(bool(enable_bits & bit)))

        if len(elements) > 1:
            self._update_attribute(
                self.AttributeDefs.alarm_water_shortage_duration.id,
                t.uint8_t(elements[1]),
            )
        if len(elements) > 2:
            self._update_attribute(
                self.AttributeDefs.alarm_water_leak_duration.id,
                t.uint8_t(elements[2]),
            )

    def update_manual_settings(self, value: Any) -> None:
        """Update local safety run limit and default duration from manualDefaultSettings array."""
        elements = _extract_elements(value)
        if not elements or len(elements) < 12:
            return

        irrigation_duration = (elements[3] << 8) | elements[4]
        if irrigation_duration == 0:
            irrigation_duration = (elements[1] << 8) | elements[2]

        safety_limit = (elements[10] << 8) | elements[11]
        self._update_attribute(
            self.AttributeDefs.default_irrigation_duration.id,
            t.uint16_t(irrigation_duration),
        )
        self._update_attribute(
            self.AttributeDefs.safety_run_limit.id,
            t.uint16_t(safety_limit),
        )

    async def write_attributes(
        self,
        attributes: dict[str | int | ZCLAttributeDef, Any],
        **kwargs: Any,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Translate individual entity writes into 0x5020 or 0x501D array writes."""
        sonoff_cluster = self.endpoint.in_clusters.get(CustomSonoffCluster.cluster_id)
        if sonoff_cluster is None:
            return [[foundation.WriteAttributesStatusRecord(foundation.Status.FAILURE)]]

        # Handle manualDefaultSettings writes to 0x501D (safety_run_limit, default_irrigation_duration)
        manual_keys = {
            self.AttributeDefs.safety_run_limit.name,
            self.AttributeDefs.safety_run_limit.id,
            self.AttributeDefs.default_irrigation_duration.name,
            self.AttributeDefs.default_irrigation_duration.id,
        }
        if any(k in attributes for k in manual_keys):
            current = sonoff_cluster.get(
                CustomSonoffCluster.AttributeDefs.manual_default_settings.id
            )
            elements = _extract_elements(current)
            if not elements:
                elements = [0, 0, 30, 0, 30, 0, 10, 0, 0, 10, 0, 0]

            while len(elements) < 12:
                elements.append(0)

            if (
                self.AttributeDefs.safety_run_limit.name in attributes
                or self.AttributeDefs.safety_run_limit.id in attributes
            ):
                val = attributes.get(
                    self.AttributeDefs.safety_run_limit.name,
                    attributes.get(self.AttributeDefs.safety_run_limit.id),
                )
                parsed_val = max(0, min(719, int(val)))
                elements[10] = (parsed_val >> 8) & 0xFF
                elements[11] = parsed_val & 0xFF
                self._update_attribute(
                    self.AttributeDefs.safety_run_limit.id,
                    t.uint16_t(parsed_val),
                )

            if (
                self.AttributeDefs.default_irrigation_duration.name in attributes
                or self.AttributeDefs.default_irrigation_duration.id in attributes
            ):
                val = attributes.get(
                    self.AttributeDefs.default_irrigation_duration.name,
                    attributes.get(self.AttributeDefs.default_irrigation_duration.id),
                )
                parsed_dur = max(1, min(719, int(val)))
                elements[1] = (parsed_dur >> 8) & 0xFF
                elements[2] = parsed_dur & 0xFF
                elements[3] = (parsed_dur >> 8) & 0xFF
                elements[4] = parsed_dur & 0xFF
                self._update_attribute(
                    self.AttributeDefs.default_irrigation_duration.id,
                    t.uint16_t(parsed_dur),
                )

            payload = foundation.Array(
                type=foundation.DataType.uint8.type_id,
                value=t.LVList[t.uint8_t, t.uint16_t](elements),
            )
            await sonoff_cluster.write_attributes(
                {CustomSonoffCluster.AttributeDefs.manual_default_settings.id: payload},
                **kwargs,
            )
            sonoff_cluster._update_attribute(
                CustomSonoffCluster.AttributeDefs.manual_default_settings.id,
                payload,
            )

        # Handle alarm settings writes to 0x5020
        alarm_keys = {
            self.AttributeDefs.water_shortage_alarm.id,
            self.AttributeDefs.water_leak_alarm.id,
            self.AttributeDefs.water_shortage_auto_close.id,
            self.AttributeDefs.alarm_water_shortage_duration.id,
            self.AttributeDefs.alarm_water_leak_duration.id,
            self.AttributeDefs.water_shortage_alarm.name,
            self.AttributeDefs.water_leak_alarm.name,
            self.AttributeDefs.water_shortage_auto_close.name,
            self.AttributeDefs.alarm_water_shortage_duration.name,
            self.AttributeDefs.alarm_water_leak_duration.name,
        }
        if any(k in attributes for k in alarm_keys):
            current = sonoff_cluster.get(
                CustomSonoffCluster.AttributeDefs.valve_alarm_settings.id
            )
            elements = _extract_elements(current)
            if not elements:
                elements = [0x03, 1, 1, 0]

            while len(elements) < 4:
                elements.append(0)

            for attr, value in attributes.items():
                attr_def = self.find_attribute(attr)
                if attr_def.id in self._ALARM_BITS:
                    bit = self._ALARM_BITS[attr_def.id]
                    if value:
                        elements[0] |= bit
                    else:
                        elements[0] &= ~bit
                    self._update_attribute(attr_def.id, t.Bool(bool(value)))
                elif attr_def.id == self.AttributeDefs.alarm_water_shortage_duration.id:
                    parsed = max(1, min(10, int(value)))
                    elements[1] = parsed
                    self._update_attribute(attr_def.id, t.uint8_t(parsed))
                elif attr_def.id == self.AttributeDefs.alarm_water_leak_duration.id:
                    parsed = max(1, min(3, int(value)))
                    elements[2] = parsed
                    self._update_attribute(attr_def.id, t.uint8_t(parsed))

            payload = foundation.Array(
                type=foundation.DataType.uint8.type_id,
                value=t.LVList[t.uint8_t, t.uint16_t](elements),
            )
            await sonoff_cluster.write_attributes(
                {CustomSonoffCluster.AttributeDefs.valve_alarm_settings.id: payload},
                **kwargs,
            )
            sonoff_cluster._update_attribute(
                CustomSonoffCluster.AttributeDefs.valve_alarm_settings.id,
                payload,
            )

        return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]


# Register dual-channel devices (SWV-ZF2U / SWV-ZF2E) separately,
# adding the channel 2 irrigation duration line chart.
(
    QuirkBuilder("SONOFF", "SWV-ZF2")
    .also_applies_to("SONOFF", "SWV-ZF2U")
    .also_applies_to("SONOFF", "SWV-ZF2E")
    .replaces(CustomSonoffCluster)
    .replaces(
        CustomSonoffCluster, endpoint_id=2
    )  # Endpoint 2 also uses the custom cluster
    .adds(ValveAlarmSettingsCluster)
    # Child Lock
    .switch(
        CustomSonoffCluster.AttributeDefs.child_lock.name,
        CustomSonoffCluster.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        unique_id_suffix="child_lock",
        translation_key="child_lock",
        fallback_name="Child lock",
        reporting_config=ReportingConfig(
            min_interval=30, 
            max_interval=900, 
            reportable_change=1
        ),
    )
    # Water shortage alarm switch
    .switch(
        ValveAlarmSettingsCluster.AttributeDefs.water_shortage_alarm.name,
        ValveAlarmSettingsCluster.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        unique_id_suffix="alarm_water_shortage",
        translation_key="alarm_water_shortage",
        fallback_name="Water shortage alarm",
    )
    # Water leak alarm switch
    .switch(
        ValveAlarmSettingsCluster.AttributeDefs.water_leak_alarm.name,
        ValveAlarmSettingsCluster.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        unique_id_suffix="alarm_water_leak",
        translation_key="alarm_water_leak",
        fallback_name="Water leak alarm",
    )
    # Water shortage auto-close valve switch
    .switch(
        ValveAlarmSettingsCluster.AttributeDefs.water_shortage_auto_close.name,
        ValveAlarmSettingsCluster.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        unique_id_suffix="water_shortage_auto_close",
        translation_key="water_shortage_auto_close",
        fallback_name="Water shortage auto-close",
    )
    # Water shortage alarm duration delay
    .number(
        ValveAlarmSettingsCluster.AttributeDefs.alarm_water_shortage_duration.name,
        ValveAlarmSettingsCluster.cluster_id,
        endpoint_id=1,
        min_value=1,
        max_value=10,
        step=1,
        unit=UnitOfTime.MINUTES,
        entity_type=EntityType.CONFIG,
        unique_id_suffix="alarm_water_shortage_duration",
        translation_key="alarm_water_shortage_duration",
        fallback_name="Water shortage alarm delay",
    )
    # Water leak alarm duration delay
    .number(
        ValveAlarmSettingsCluster.AttributeDefs.alarm_water_leak_duration.name,
        ValveAlarmSettingsCluster.cluster_id,
        endpoint_id=1,
        min_value=1,
        max_value=3,
        step=1,
        unit=UnitOfTime.MINUTES,
        entity_type=EntityType.CONFIG,
        unique_id_suffix="alarm_water_leak_duration",
        translation_key="alarm_water_leak_duration",
        fallback_name="Water leak alarm delay",
    )
    # Hardware safety run limit / auto-off timeout
    .number(
        ValveAlarmSettingsCluster.AttributeDefs.safety_run_limit.name,
        ValveAlarmSettingsCluster.cluster_id,
        endpoint_id=1,
        min_value=0,
        max_value=719,
        step=1,
        unit=UnitOfTime.MINUTES,
        entity_type=EntityType.CONFIG,
        unique_id_suffix="safety_run_limit",
        translation_key="safety_run_limit",
        fallback_name="Safety run limit",
    )
    # Default hardware manual irrigation duration
    .number(
        ValveAlarmSettingsCluster.AttributeDefs.default_irrigation_duration.name,
        ValveAlarmSettingsCluster.cluster_id,
        endpoint_id=1,
        min_value=1,
        max_value=719,
        step=1,
        unit=UnitOfTime.MINUTES,
        entity_type=EntityType.CONFIG,
        unique_id_suffix="default_irrigation_duration",
        translation_key="default_irrigation_duration",
        fallback_name="Default manual run duration",
    )
    # Real Time irrigation duration sensor - channel 1 (endpoint 1, 0x5006)
    .sensor(
        attribute_name=CustomSonoffCluster.AttributeDefs.realtime_irrigation_duration.name,
        cluster_id=CustomSonoffCluster.cluster_id,
        endpoint_id=1,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTime.MINUTES,
        unique_id_suffix="realtime_irrigation_duration_ch1",
        reporting_config=ReportingConfig(
            min_interval=10, max_interval=900, reportable_change=1
        ),
        translation_key="realtime_irrigation_duration_ch1",
        fallback_name="Realtime irrigation duration CH1",
    )
    # Real Time irrigation duration sensor - channel 2 (endpoint 2, 0x5006)
    .sensor(
        attribute_name=CustomSonoffCluster.AttributeDefs.realtime_irrigation_duration.name,
        cluster_id=CustomSonoffCluster.cluster_id,
        endpoint_id=2,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTime.MINUTES,
        unique_id_suffix="realtime_irrigation_duration_ch2",
        reporting_config=ReportingConfig(
            min_interval=10, max_interval=900, reportable_change=1
        ),
        translation_key="realtime_irrigation_duration_ch2",
        fallback_name="Realtime irrigation duration CH2",
    )
    # irrigation volume sensor
    .sensor(
        attribute_name=CustomSonoffCluster.AttributeDefs.realtime_irrigation_volume.name,
        cluster_id=CustomSonoffCluster.cluster_id,
        endpoint_id=1,
        device_class=SensorDeviceClass.VOLUME,
        state_class=SensorStateClass.TOTAL_INCREASING,  # VOLUME must use total_increasing
        unit=UnitOfVolume.LITERS,
        unique_id_suffix="realtime_irrigation_volume",
        reporting_config=ReportingConfig(
            min_interval=10, max_interval=900, reportable_change=1
        ),
        translation_key="realtime_irrigation_volume",
        fallback_name="Realtime irrigation volume",
    )
    
    # Water leak sensor (bit1)
    .binary_sensor(
        CustomSonoffCluster.AttributeDefs.water_valve_state.name,
        CustomSonoffCluster.cluster_id,
        endpoint_id=1,
        device_class=BinarySensorDeviceClass.MOISTURE,
        attribute_converter=lambda x: bool(x & ValveState.Water_Leakage),
        unique_id_suffix="water_leak_status",
        reporting_config=ReportingConfig(
            min_interval=10, max_interval=900, reportable_change=1
        ),
        translation_key="water_leak",
        fallback_name="Water leak",
    )
    # Water shortage sensor - channel 1 (bit0)
    .binary_sensor(
        CustomSonoffCluster.AttributeDefs.water_valve_state.name,
        CustomSonoffCluster.cluster_id,
        endpoint_id=1,
        device_class=BinarySensorDeviceClass.PROBLEM,
        attribute_converter=lambda x: bool(x & ValveState.Water_Shortage),
        unique_id_suffix="water_shortage_ch1",
        translation_key="water_shortage_ch1",
        fallback_name="Water shortage CH1",
    )
    # Water shortage sensor - channel 2 (bit4)
    .binary_sensor(
        CustomSonoffCluster.AttributeDefs.water_valve_state.name,
        CustomSonoffCluster.cluster_id,
        endpoint_id=2,
        device_class=BinarySensorDeviceClass.PROBLEM,
        attribute_converter=lambda x: bool(x & ValveState.Water_Shortage_Channel_2),
        unique_id_suffix="water_shortage_ch2",
        translation_key="water_shortage_ch2",
        fallback_name="Water shortage CH2",
    )
    # Freeze / anti-frost alarm sensor (bit2)
    .binary_sensor(
        CustomSonoffCluster.AttributeDefs.water_valve_state.name,
        CustomSonoffCluster.cluster_id,
        endpoint_id=1,
        device_class=BinarySensorDeviceClass.COLD,
        attribute_converter=lambda x: bool(x & ValveState.Anti_Frost_Alarm),
        unique_id_suffix="anti_frost_alarm",
        translation_key="anti_frost_alarm",
        fallback_name="Anti-frost alarm",
    )
    # Fail-safe emergency shutoff - channel 1 (bit3)
    .binary_sensor(
        CustomSonoffCluster.AttributeDefs.water_valve_state.name,
        CustomSonoffCluster.cluster_id,
        endpoint_id=1,
        device_class=BinarySensorDeviceClass.SAFETY,
        attribute_converter=lambda x: bool(x & ValveState.FailSafe_Channel_1),
        unique_id_suffix="failsafe_ch1",
        translation_key="failsafe_ch1",
        fallback_name="Fail-safe shutoff CH1",
    )
    # Fail-safe emergency shutoff - channel 2 (bit5)
    .binary_sensor(
        CustomSonoffCluster.AttributeDefs.water_valve_state.name,
        CustomSonoffCluster.cluster_id,
        endpoint_id=2,
        device_class=BinarySensorDeviceClass.SAFETY,
        attribute_converter=lambda x: bool(x & ValveState.FailSafe_Channel_2),
        unique_id_suffix="failsafe_ch2",
        translation_key="failsafe_ch2",
        fallback_name="Fail-safe shutoff CH2",
    )
    # irrigation duration sensor - channel 1 (endpoint 1, 0x501C)
    .sensor(
        attribute_name=CustomSonoffCluster.AttributeDefs.hour_irrigation_duration.name,
        cluster_id=CustomSonoffCluster.cluster_id,
        endpoint_id=1,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTime.MINUTES,
        unique_id_suffix="irrigation_duration_ch1",
        reporting_config=ReportingConfig(
            min_interval=30, max_interval=900, reportable_change=1
        ),
        translation_key="irrigation_duration_ch1",
        fallback_name="Hourly irrigation duration CH1",
    )
    # irrigation duration sensor - channel 2 (endpoint 2, 0x501C)
    .sensor(
        attribute_name=CustomSonoffCluster.AttributeDefs.hour_irrigation_duration.name,
        cluster_id=CustomSonoffCluster.cluster_id,
        endpoint_id=2,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTime.MINUTES,
        unique_id_suffix="irrigation_duration_ch2",
        reporting_config=ReportingConfig(
            min_interval=30, max_interval=900, reportable_change=1
        ),
        translation_key="irrigation_duration_ch2",
        fallback_name="Hourly irrigation duration CH2",
    )
    # irrigation volume sensor
    .sensor(
        attribute_name=CustomSonoffCluster.AttributeDefs.hour_irrigation_volume.name,
        cluster_id=CustomSonoffCluster.cluster_id,
        endpoint_id=1,
        device_class=SensorDeviceClass.VOLUME,
        state_class=SensorStateClass.TOTAL_INCREASING,  # VOLUME must use total_increasing
        unit=UnitOfVolume.LITERS,
        unique_id_suffix="irrigation_volume",
        reporting_config=ReportingConfig(
            min_interval=30, max_interval=900, reportable_change=1
        ),
        translation_key="irrigation_volume",
        fallback_name="Hourly irrigation volume",
    )
    .add_to_registry()
)
