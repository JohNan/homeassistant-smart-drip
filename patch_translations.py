import json
import os

def update_translation(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    config_data = data["config"]["step"]["user"]["data"]
    config_desc = data["config"]["step"]["user"]["data_description"]

    options_data = data["options"]["step"]["init"]["data"]
    options_desc = data["options"]["step"]["init"]["data_description"]

    for key in ["sensor_temp", "sensor_humidity", "sensor_dewpoint", "sensor_radiation", "sensor_wind", "sensor_pressure", "zone_1_switch", "zone_2_switch"]:
        if key in config_data:
            options_data[key] = config_data[key]
        if key in config_desc:
            options_desc[key] = config_desc[key]

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

update_translation("custom_components/smart_drip/strings.json")
update_translation("custom_components/smart_drip/translations/en.json")
update_translation("custom_components/smart_drip/translations/sv.json")
print("Done")
