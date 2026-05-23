entity_id = data.get("entity_id", "sensor.quatt_energy_power")
power = data.get("power")
new_state = data.get("new_state", "ok")

# Check whether power data has been received
if not power:
    logger.warning("set_energy_power: no power data provided")
else:
    if not isinstance(power, str):
        power = str(power)
    hass.states.set(entity_id, new_state, {"power_json": power})
