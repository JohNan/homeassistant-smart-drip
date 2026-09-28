import voluptuous as vol
from homeassistant.helpers import selector
schema = vol.Schema({
    vol.Required("sensor"): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor"))
})
print("success")
