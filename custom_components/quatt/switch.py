"""Switch platform for quatt."""

from __future__ import annotations

import logging

from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.core import HomeAssistant

from .const import (
    DEVICE_BOILER_ID,
    DEVICE_CIC_ID,
    DEVICE_ENERGY_ID,
    DEVICE_FLOWMETER_ID,
    DEVICE_HEAT_BATTERY_ID,
    DEVICE_HEAT_CHARGER_ID,
    DEVICE_HEATPUMP_1_ID,
    DEVICE_HEATPUMP_2_ID,
    DEVICE_THERMOSTAT_ID,
    DOMAIN,
    QuattDeviceKind,
)
from .coordinator import QuattDataUpdateCoordinator
from .entity import (
    QuattEnergyPriceFlagSwitch,
    QuattFeatureFlags,
    QuattSettingSwitch,
    QuattSwitch,
    QuattSwitchEntityDescription,
)
from .entity_setup import async_setup_entities

ENERGY_SWITCHES: list[QuattSwitchEntityDescription] = [
    QuattSwitchEntityDescription(
        key="include_vat",
        name="Include VAT",
        icon="mdi:percent",
        quatt_entity_class=QuattEnergyPriceFlagSwitch,
    ),
    QuattSwitchEntityDescription(
        key="include_tax",
        name="Include energy tax",
        icon="mdi:cash-multiple",
        quatt_entity_class=QuattEnergyPriceFlagSwitch,
    ),
    QuattSwitchEntityDescription(
        key="include_markup",
        name="Include supplier markup",
        icon="mdi:cash-plus",
        quatt_entity_class=QuattEnergyPriceFlagSwitch,
    ),
]

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
        QuattSwitchEntityDescription(
            key="avoidNighttimeCharging.allEAvoidNighttimeCharging",
            name="Avoid nighttime charging",
            icon="mdi:weather-night",
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

    local_coordinator: QuattDataUpdateCoordinator | None = coordinators.get("cic_local")
    remote_coordinator: QuattDataUpdateCoordinator | None = coordinators.get("cic_remote")
    energy_coordinator: QuattDataUpdateCoordinator | None = coordinators.get("energy")

    switches: list[QuattSwitch] = []
    if local_coordinator is not None:
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

    if energy_coordinator is not None:
        for desc in ENERGY_SWITCHES:
            switches.append(
                desc.quatt_entity_class(
                    device_name="Energy",
                    device_id=DEVICE_ENERGY_ID,
                    sensor_key=desc.key,
                    coordinator=energy_coordinator,
                    entity_description=desc,
                    device_kind=QuattDeviceKind.HUB,
                )
            )

    async_add_devices(switches)
