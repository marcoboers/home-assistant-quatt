"""Time platform for quatt."""

from __future__ import annotations

from homeassistant.components.time import DOMAIN as TIME_DOMAIN
from homeassistant.core import HomeAssistant

from .const import (
    DEVICE_BOILER_ID,
    DEVICE_CIC_ID,
    DEVICE_FLOWMETER_ID,
    DEVICE_HEAT_BATTERY_ID,
    DEVICE_HEAT_CHARGER_ID,
    DEVICE_HEATPUMP_1_ID,
    DEVICE_HEATPUMP_2_ID,
    DEVICE_THERMOSTAT_ID,
    DOMAIN,
)
from .coordinator import QuattDataUpdateCoordinator
from .entity import (
    QuattFeatureFlags,
    QuattTime,
    QuattTimeEntityDescription,
)
from .entity_setup import async_setup_entities
from .entity_time import (
    NIGHT_WINDOW_END_KEY,
    NIGHT_WINDOW_START_KEY,
    QuattNightWindowTime,
)

TIMES = {
    # The HUB CIC sensor must be created first to ensure the HUB device is present
    DEVICE_CIC_ID: [
        QuattTimeEntityDescription(
            key=NIGHT_WINDOW_START_KEY,
            name="Night time start",
            icon="mdi:weather-night",
            quatt_features=QuattFeatureFlags(
                mobile_api=True,
            ),
            quatt_entity_class=QuattNightWindowTime,
        ),
        QuattTimeEntityDescription(
            key=NIGHT_WINDOW_END_KEY,
            name="Night time end",
            icon="mdi:weather-sunset-up",
            quatt_features=QuattFeatureFlags(
                mobile_api=True,
            ),
            quatt_entity_class=QuattNightWindowTime,
        ),
    ],
    DEVICE_HEAT_BATTERY_ID: [],
    DEVICE_HEAT_CHARGER_ID: [],
    DEVICE_HEATPUMP_1_ID: [],
    DEVICE_HEATPUMP_2_ID: [],
    DEVICE_BOILER_ID: [],
    DEVICE_FLOWMETER_ID: [],
    DEVICE_THERMOSTAT_ID: [],
}


async def async_setup_entry(hass: HomeAssistant, entry, async_add_devices):
    """Set up the time platform."""
    coordinators = hass.data[DOMAIN][entry.entry_id]

    local_coordinator: QuattDataUpdateCoordinator | None = coordinators.get("cic_local")
    remote_coordinator: QuattDataUpdateCoordinator | None = coordinators.get(
        "cic_remote"
    )

    times: list[QuattTime] = []
    if local_coordinator is not None:
        times += await async_setup_entities(
            hass=hass,
            coordinator=local_coordinator,
            entry=entry,
            remote=False,
            entity_descriptions=TIMES,
            entity_domain=TIME_DOMAIN,
        )

    if remote_coordinator:
        times += await async_setup_entities(
            hass=hass,
            coordinator=remote_coordinator,
            entry=entry,
            remote=True,
            entity_descriptions=TIMES,
            entity_domain=TIME_DOMAIN,
        )

    async_add_devices(times)
