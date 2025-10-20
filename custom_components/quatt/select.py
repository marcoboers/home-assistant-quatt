"""Select platform for quatt."""

from __future__ import annotations

import logging

from homeassistant.components.select import DOMAIN as SELECT_DOMAIN
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
from .entity import QuattFeatureFlags, QuattSelect, QuattSelectEntityDescription
from .entity_setup import async_setup_entities

# Sound level options
SOUND_LEVEL_OPTIONS = ["normal", "library", "silent", "building87"]

SELECTS = {
    # The HUB CIC sensor must be created first to ensure the HUB device is present
    DEVICE_CIC_ID: [
        QuattSelectEntityDescription(
            key="dayMaxSoundLevel",
            name="Day max sound level",
            icon="mdi:volume-high",
            options=SOUND_LEVEL_OPTIONS,
            features=QuattFeatureFlags(
                quatt_mobile_api=True,
            ),
        ),
        QuattSelectEntityDescription(
            key="nightMaxSoundLevel",
            name="Night max sound level",
            icon="mdi:volume-low",
            options=SOUND_LEVEL_OPTIONS,
            features=QuattFeatureFlags(
                quatt_mobile_api=True,
            ),
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

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_devices):
    """Set up the select platform."""
    coordinators = hass.data[DOMAIN][entry.entry_id]

    local_coordinator: QuattDataUpdateCoordinator = coordinators["local"]
    remote_coordinator: QuattDataUpdateCoordinator = coordinators["remote"]

    selects: list[QuattSelect] = []
    selects += await async_setup_entities(
        hass=hass,
        coordinator=local_coordinator,
        entry=entry,
        remote=False,
        entity_class=QuattSelect,
        entity_descriptions=SELECTS,
        entity_domain=SELECT_DOMAIN,
    )

    if remote_coordinator:
        selects += await async_setup_entities(
            hass=hass,
            coordinator=remote_coordinator,
            entry=entry,
            remote=True,
            entity_class=QuattSelect,
            entity_descriptions=SELECTS,
            entity_domain=SELECT_DOMAIN,
        )

    async_add_devices(selects)
