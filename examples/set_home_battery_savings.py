entity_id = data.get("entity_id", "sensor.quatt_home_battery_savings")
savings = data.get("savings")
new_state = data.get("new_state", "ok")

# Check whether savings data has been received
if not savings:
    logger.warning("set_home_battery_savings: no savings data provided")
else:
    if not isinstance(savings, str):
        savings = str(savings)
    hass.states.set(entity_id, new_state, {"savings_json": savings})
