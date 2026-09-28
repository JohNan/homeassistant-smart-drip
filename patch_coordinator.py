import re

with open("custom_components/smart_drip/coordinator.py", "r") as f:
    content = f.read()

def replace_async_execute_morning_schedule(match):
    return """            async def turn_on(z: int = zone, sw: str = switch_entity, d: int = duration) -> None:
                self.zone_status[z]["state"] = STATUS_RUNNING
                self.zone_status[z]["reason"] = (
                    f"Scheduled irrigation active ({round(d / 60)} min)."
                )
                self.async_set_updated_data(self._build_coordinator_data())

                domain = sw.split(".", 1)[0]
                if domain == "valve":
                    await self.hass.services.async_call("valve", "open_valve", {"entity_id": sw}, blocking=True)
                elif domain == "switch":
                    await self.hass.services.async_call("switch", "turn_on", {"entity_id": sw}, blocking=True)
                else:
                    await self.hass.services.async_call("homeassistant", "turn_on", {"entity_id": sw}, blocking=True)

            async def turn_off(
                z: int = zone,
                sw: str = switch_entity,
                d: int = duration,
                f: float = flow,
                a: float = area,
            ) -> None:
                domain = sw.split(".", 1)[0]
                if domain == "valve":
                    await self.hass.services.async_call("valve", "close_valve", {"entity_id": sw}, blocking=True)
                elif domain == "switch":
                    await self.hass.services.async_call("switch", "turn_off", {"entity_id": sw}, blocking=True)
                else:
                    await self.hass.services.async_call("homeassistant", "turn_off", {"entity_id": sw}, blocking=True)
"""

content = re.sub(
    r"""            async def turn_on\(z: int = zone, sw: str = switch_entity, d: int = duration\) -> None:.*?await self\.hass\.services\.async_call\(\n                    "switch", "turn_off", \{"entity_id": sw\}, blocking=True\n                \)""",
    replace_async_execute_morning_schedule,
    content,
    flags=re.DOTALL
)


def replace_async_run_zone_manual(match):
    return """        async def turn_on() -> None:
            self.zone_status[zone]["state"] = STATUS_RUNNING
            self.zone_status[zone]["reason"] = (
                f"Manual irrigation active ({round(duration_seconds / 60)} min)."
            )
            self.zone_status[zone]["target_duration_seconds"] = duration_seconds
            self.zone_status[zone]["estimated_liters"] = round(
                (duration_seconds / 3600.0) * flow, 1
            )
            self.async_set_updated_data(self._build_coordinator_data())

            domain = switch_entity.split(".", 1)[0]
            if domain == "valve":
                await self.hass.services.async_call("valve", "open_valve", {"entity_id": switch_entity}, blocking=True)
            elif domain == "switch":
                await self.hass.services.async_call("switch", "turn_on", {"entity_id": switch_entity}, blocking=True)
            else:
                await self.hass.services.async_call("homeassistant", "turn_on", {"entity_id": switch_entity}, blocking=True)

        async def turn_off() -> None:
            domain = switch_entity.split(".", 1)[0]
            if domain == "valve":
                await self.hass.services.async_call("valve", "close_valve", {"entity_id": switch_entity}, blocking=True)
            elif domain == "switch":
                await self.hass.services.async_call("switch", "turn_off", {"entity_id": switch_entity}, blocking=True)
            else:
                await self.hass.services.async_call("homeassistant", "turn_off", {"entity_id": switch_entity}, blocking=True)
"""

content = re.sub(
    r"""        async def turn_on\(\) -> None:.*?await self\.hass\.services\.async_call\(\n                "switch", "turn_off", \{"entity_id": switch_entity\}, blocking=True\n            \)""",
    replace_async_run_zone_manual,
    content,
    flags=re.DOTALL
)

with open("custom_components/smart_drip/coordinator.py", "w") as f:
    f.write(content)
