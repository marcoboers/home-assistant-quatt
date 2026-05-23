entity_id = data.get("entity_id", "sensor.quatt_energy_costs")
costs = data.get("costs")
new_state = data.get("new_state", "ok")

# Check whether costs data has been received
if not costs:
    logger.warning("set_energy_costs: no costs data provided")
else:
    if not isinstance(costs, str):
        costs = str(costs)
    hass.states.set(entity_id, new_state, {"costs_json": costs})
