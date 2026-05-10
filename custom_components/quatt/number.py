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
    DEVICE_HOME_BATTERY_ID,
    DEVICE_THERMOSTAT_ID,
    DOMAIN,
    QuattDeviceKind,
)
from .coordinator import QuattDataUpdateCoordinator
from .entity import (
    QuattFeatureFlags,
    QuattHomeBatterySolarCapacityNumber,
    QuattNumber,
    QuattNumberEntityDescription,
    QuattSettingNumber,
)
from .entity_setup import async_setup_entities

HOME_BATTERY_NUMBERS: list[QuattNumberEntityDescription] = [
    QuattNumberEntityDescription(
        key="solarCapacitykWp",
        name="Solar capacity",
        icon="mdi:solar-power",
        native_unit_of_measurement="kWp",
        native_min_value=0,
        native_max_value=50,
        native_step=1,
        mode=NumberMode.BOX,
        quatt_entity_class=QuattHomeBatterySolarCapacityNumber,
    ),
]

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

    local_coordinator: QuattDataUpdateCoordinator | None = coordinators.get("cic_local")
    remote_coordinator: QuattDataUpdateCoordinator | None = coordinators.get("cic_remote")
    home_battery_coordinator: QuattDataUpdateCoordinator | None = coordinators.get(
        "home_battery"
    )

    numbers: list[QuattNumber] = []
    if local_coordinator is not None:
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

    if home_battery_coordinator is not None:
        for desc in HOME_BATTERY_NUMBERS:
            numbers.append(
                desc.quatt_entity_class(
                    device_name="Home battery",
                    device_id=DEVICE_HOME_BATTERY_ID,
                    sensor_key=desc.key,
                    coordinator=home_battery_coordinator,
                    entity_description=desc,
                    device_kind=QuattDeviceKind.HUB,
                )
            )

    async_add_devices(numbers)
