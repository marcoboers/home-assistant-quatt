"""Number platform for quatt."""

from __future__ import annotations

import logging

from homeassistant.components.number import DOMAIN as NUMBER_DOMAIN, NumberMode
from homeassistant.const import UnitOfTemperature
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
    QuattNumber,
    QuattNumberEntityDescription,
    QuattSettingNumber,
)
from .entity_setup import async_setup_entities

NUMBERS = {
    # The HUB CIC sensor must be created first to ensure the HUB device is present
    DEVICE_CIC_ID: [
        QuattNumberEntityDescription(
            key="chMaxWaterTemperature",
            name="Max water temperature",
            icon="mdi:thermometer-high",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            mode=NumberMode.BOX,
            quatt_features=QuattFeatureFlags(
                mobile_api=True,
            ),
            quatt_entity_class=QuattSettingNumber,
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
    """Set up the number platform."""
    coordinators = hass.data[DOMAIN][entry.entry_id]

    local_coordinator: QuattDataUpdateCoordinator = coordinators["local"]
    remote_coordinator: QuattDataUpdateCoordinator = coordinators["remote"]

    numbers: list[QuattNumber] = []
    numbers += await async_setup_entities(
        hass=hass,
        coordinator=local_coordinator,
        entry=entry,
        remote=False,
        entity_descriptions=NUMBERS,
        entity_domain=NUMBER_DOMAIN,
    )

    if remote_coordinator:
        numbers += await async_setup_entities(
            hass=hass,
            coordinator=remote_coordinator,
            entry=entry,
            remote=True,
            entity_descriptions=NUMBERS,
            entity_domain=NUMBER_DOMAIN,
        )

    async_add_devices(numbers)
