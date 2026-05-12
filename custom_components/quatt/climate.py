"""Climate platform for quatt."""

from __future__ import annotations

from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
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
    QuattChillClimate,
    QuattClimateEntityDescription,
    QuattFeatureFlags,
)
from .entity_setup import async_setup_entities, create_chill_entity_descriptions

CLIMATES = {
    # The HUB CIC sensor must be created first to ensure the HUB device is present
    DEVICE_CIC_ID: [],
    DEVICE_HEAT_BATTERY_ID: [],
    DEVICE_HEAT_CHARGER_ID: [],
    DEVICE_HEATPUMP_1_ID: [],
    DEVICE_HEATPUMP_2_ID: [],
    DEVICE_BOILER_ID: [],
    DEVICE_FLOWMETER_ID: [],
    DEVICE_THERMOSTAT_ID: [],
}


def create_chill_climate_entity_descriptions(
    index: int,
) -> list[QuattClimateEntityDescription]:
    """Create the chill climate entity descriptions based on the index."""
    return [
        QuattClimateEntityDescription(
            key=f"chills.{index}",
            quatt_features=QuattFeatureFlags(
                mobile_api=True,
            ),
            quatt_entity_class=QuattChillClimate,
        )
    ]


async def async_setup_entry(hass: HomeAssistant, entry, async_add_devices):
    """Set up the climate platform."""
    coordinators = hass.data[DOMAIN][entry.entry_id]

    remote_coordinator: QuattDataUpdateCoordinator | None = coordinators.get(
        "cic_remote"
    )

    climates: list[QuattChillClimate] = []

    if remote_coordinator:
        entity_descriptions, device_names, device_kinds = (
            create_chill_entity_descriptions(
                remote_coordinator,
                CLIMATES,
                create_chill_climate_entity_descriptions,
            )
        )

        climates += await async_setup_entities(
            hass=hass,
            coordinator=remote_coordinator,
            entry=entry,
            remote=True,
            entity_descriptions=entity_descriptions,
            entity_domain=CLIMATE_DOMAIN,
            device_names=device_names,
            device_kinds=device_kinds,
        )

    async_add_devices(climates)
