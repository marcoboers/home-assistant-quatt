"""Switch platform for quatt."""

from __future__ import annotations

import logging

from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
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
    QuattSettingSwitch,
    QuattSwitch,
    QuattSwitchEntityDescription,
)
from .entity_setup import async_setup_entities

SWITCHES = {
    # The HUB CIC sensor must be created first to ensure the HUB device is present
    DEVICE_CIC_ID: [
        QuattSwitchEntityDescription(
            key="usePricingToLimitHeatPump",
            name="Use pricing to limit heatpump",
            icon="mdi:currency-eur",
            quatt_features=QuattFeatureFlags(
                mobile_api=True,
            ),
            quatt_entity_class=QuattSettingSwitch,
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
    """Set up the switch platform."""
    coordinators = hass.data[DOMAIN][entry.entry_id]

    local_coordinator: QuattDataUpdateCoordinator = coordinators["local"]
    remote_coordinator: QuattDataUpdateCoordinator = coordinators["remote"]

    switches: list[QuattSwitch] = []
    switches += await async_setup_entities(
        hass=hass,
        coordinator=local_coordinator,
        entry=entry,
        remote=False,
        entity_descriptions=SWITCHES,
        entity_domain=SWITCH_DOMAIN,
    )

    if remote_coordinator:
        switches += await async_setup_entities(
            hass=hass,
            coordinator=remote_coordinator,
            entry=entry,
            remote=True,
            entity_descriptions=SWITCHES,
            entity_domain=SWITCH_DOMAIN,
        )

    async_add_devices(switches)
