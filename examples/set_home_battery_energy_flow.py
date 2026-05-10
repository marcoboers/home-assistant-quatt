entity_id = data.get("entity_id", "sensor.quatt_home_battery_energy_flow")
energy_flow = data.get("energy_flow")
new_state = data.get("new_state", "ok")

# Check whether energy flow data has been received
if not energy_flow:
    logger.warning(
        "set_home_battery_energy_flow: no energy flow data provided")
else:
    if not isinstance(energy_flow, str):
        energy_flow = str(energy_flow)
    hass.states.set(entity_id, new_state, {"energy_flow_json": energy_flow})
