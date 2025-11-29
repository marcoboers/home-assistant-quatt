entity_id = data.get("entity_id", "sensor.quatt_insights")
insights = data.get("insights")
# Check whether insights have been received
if not insights:
    logger.warning("set_quatt_insights: no insights data provided")
else:
    hass.states.set(entity_id, "ok", {"insights_json": insights})