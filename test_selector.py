from homeassistant.helpers import selector
import voluptuous as vol

print(selector.EntitySelector(selector.EntitySelectorConfig(domain=["switch", "valve"])))
