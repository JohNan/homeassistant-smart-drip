import re

with open("README.md", "r") as f:
    content = f.read()

content = content.replace(
    "- **Hardware Interlocks & Solenoid Protection**:",
    "- **Runtime Reconfigurability**: Modify zone areas, flow rates, rain sensors, weather providers, and physical switch channels directly via Home Assistant Options Flow without needing to delete and reinstall the integration.\n- **Dual-Domain Valve Support**: Easily route actuation calls to standard `switch` entities (`turn_on`/`turn_off`) or specialized smart `valve` entities (`open_valve`/`close_valve`).\n- **Hardware Interlocks & Solenoid Protection**:"
)

with open("README.md", "w") as f:
    f.write(content)

with open("AGENTS.md", "r") as f:
    agents = f.read()

agents = agents.replace(
    "All configurations are requested during initial Config Flow setup.",
    "All configurations are requested during initial Config Flow setup and can be modified later via Options Flow."
)

with open("AGENTS.md", "w") as f:
    f.write(agents)

print("Done")
