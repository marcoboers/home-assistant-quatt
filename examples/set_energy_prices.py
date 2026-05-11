entity_id = data.get("entity_id", "sensor.quatt_energy_prices")
prices = data.get("prices")
new_state = data.get("new_state", "ok")

# Check whether prices data has been received
if not prices:
    logger.warning("set_energy_prices: no prices data provided")
else:
    if not isinstance(prices, str):
        prices = str(prices)
    hass.states.set(entity_id, new_state, {"prices_json": prices})
