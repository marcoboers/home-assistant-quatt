entity_id = data.get("entity_id", "sensor.quatt_cic_insights")
insights = data.get("insights")
new_state = data.get("new_state", "ok")

# Check whether insights have been received
if not insights:
    logger.warning("set_cic_insights: no insights data provided")
else:
    if not isinstance(insights, str):
        insights = str(insights)
    hass.states.set(entity_id, new_state, {"insights_json": insights})
