"""Sensor platform for quatt."""

from __future__ import annotations

from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.core import HomeAssistant

from .const import (
    DEVICE_BOILER_ID,
    DEVICE_CIC_ID,
    DEVICE_CIC_INSIGHTS_ID,
    DEVICE_ENERGY_ID,
    DEVICE_FLOWMETER_ID,
    DEVICE_HEAT_BATTERY_ID,
    DEVICE_HEAT_CHARGER_ID,
    DEVICE_HEATPUMP_1_ID,
    DEVICE_HEATPUMP_2_ID,
    DEVICE_HOME_BATTERY_ENERGY_FLOW_ID,
    DEVICE_HOME_BATTERY_ID,
    DEVICE_HOME_BATTERY_INSIGHTS_ID,
    DEVICE_HOME_BATTERY_SAVINGS_ID,
    DEVICE_THERMOSTAT_ID,
    DOMAIN,
    QuattDeviceKind,
)
from .coordinator import QuattDataUpdateCoordinator
from .entity import QuattSensor
from .entity_setup import async_setup_entities, create_chill_entity_descriptions
from .sensor_descriptions_chill import create_chill_sensor_entity_descriptions
from .sensor_descriptions_cic import (
    BOILER_SENSORS,
    CIC_INSIGHTS_SENSORS,
    CIC_SENSORS,
    FLOWMETER_SENSORS,
    THERMOSTAT_SENSORS,
)
from .sensor_descriptions_energy import ENERGY_SENSORS
from .sensor_descriptions_heat import (
    HEAT_BATTERY_SENSORS,
    HEAT_CHARGER_SENSORS,
    create_heatpump_sensor_entity_descriptions,
)
from .sensor_descriptions_home_battery import (
    HOME_BATTERY_ENERGY_FLOW_SENSORS,
    HOME_BATTERY_INSIGHTS_SENSORS,
    HOME_BATTERY_SAVINGS_SENSORS,
    HOME_BATTERY_SENSORS,
)

SENSORS = {
    # The HUB CIC sensor must be created first to ensure the HUB device is present
    DEVICE_CIC_ID: CIC_SENSORS,
    DEVICE_HEAT_BATTERY_ID: HEAT_BATTERY_SENSORS,
    DEVICE_HEAT_CHARGER_ID: HEAT_CHARGER_SENSORS,
    DEVICE_HEATPUMP_1_ID: create_heatpump_sensor_entity_descriptions(
        index=0, is_duo=False
    ),
    DEVICE_HEATPUMP_2_ID: create_heatpump_sensor_entity_descriptions(
        index=1, is_duo=True
    ),
    DEVICE_BOILER_ID: BOILER_SENSORS,
    DEVICE_FLOWMETER_ID: FLOWMETER_SENSORS,
    DEVICE_THERMOSTAT_ID: THERMOSTAT_SENSORS,
    DEVICE_CIC_INSIGHTS_ID: CIC_INSIGHTS_SENSORS,
}


def _create_home_battery_sensors(
    coordinator: QuattDataUpdateCoordinator,
) -> list[QuattSensor]:
    """Create Home Battery sensor entities."""
    sensors: list[QuattSensor] = []

    for desc in HOME_BATTERY_SENSORS:
        sensors.append(
            QuattSensor(
                device_name="Home battery",
                device_id=DEVICE_HOME_BATTERY_ID,
                sensor_key=desc.key,
                coordinator=coordinator,
                entity_description=desc,
                device_kind=QuattDeviceKind.HUB,
            )
        )
    for desc in HOME_BATTERY_SAVINGS_SENSORS:
        sensors.append(
            QuattSensor(
                device_name="Savings",
                device_id=DEVICE_HOME_BATTERY_SAVINGS_ID,
                sensor_key=desc.key,
                coordinator=coordinator,
                entity_description=desc,
                device_kind=QuattDeviceKind.SERVICE,
            )
        )
    for desc in HOME_BATTERY_INSIGHTS_SENSORS:
        sensors.append(
            QuattSensor(
                device_name="Insights",
                device_id=DEVICE_HOME_BATTERY_INSIGHTS_ID,
                sensor_key=desc.key,
                coordinator=coordinator,
                entity_description=desc,
                device_kind=QuattDeviceKind.SERVICE,
            )
        )
    for desc in HOME_BATTERY_ENERGY_FLOW_SENSORS:
        sensors.append(
            QuattSensor(
                device_name="Energy flow",
                device_id=DEVICE_HOME_BATTERY_ENERGY_FLOW_ID,
                sensor_key=desc.key,
                coordinator=coordinator,
                entity_description=desc,
                device_kind=QuattDeviceKind.SERVICE,
            )
        )

    return sensors


def _create_energy_sensors(
    coordinator: QuattDataUpdateCoordinator,
) -> list[QuattSensor]:
    """Create Quatt Energy (mijnenergie) hub sensor entities."""
    sensors: list[QuattSensor] = []

    for desc in ENERGY_SENSORS:
        sensors.append(
            desc.quatt_entity_class(
                device_name="Energy",
                device_id=DEVICE_ENERGY_ID,
                sensor_key=desc.key,
                coordinator=coordinator,
                entity_description=desc,
                device_kind=QuattDeviceKind.HUB,
            )
        )

    return sensors


async def async_setup_entry(hass: HomeAssistant, entry, async_add_devices):
    """Set up the sensor platform."""
    coordinators = hass.data[DOMAIN][entry.entry_id]

    local_coordinator: QuattDataUpdateCoordinator | None = coordinators.get("cic_local")
    remote_coordinator: QuattDataUpdateCoordinator | None = coordinators.get(
        "cic_remote"
    )
    home_battery_coordinator: QuattDataUpdateCoordinator | None = coordinators.get(
        "home_battery"
    )
    energy_coordinator: QuattDataUpdateCoordinator | None = coordinators.get("energy")

    sensors: list[QuattSensor] = []

    if local_coordinator is not None:
        sensors += await async_setup_entities(
            hass=hass,
            coordinator=local_coordinator,
            entry=entry,
            remote=False,
            entity_descriptions=SENSORS,
            entity_domain=SENSOR_DOMAIN,
        )

    if remote_coordinator:
        entity_descriptions, device_names, device_kinds = (
            create_chill_entity_descriptions(
                remote_coordinator,
                SENSORS,
                create_chill_sensor_entity_descriptions,
            )
        )

        sensors += await async_setup_entities(
            hass=hass,
            coordinator=remote_coordinator,
            entry=entry,
            remote=True,
            entity_descriptions=entity_descriptions,
            entity_domain=SENSOR_DOMAIN,
            device_names=device_names,
            device_kinds=device_kinds,
        )

    if home_battery_coordinator is not None:
        sensors += _create_home_battery_sensors(home_battery_coordinator)

    if energy_coordinator is not None:
        sensors += _create_energy_sensors(energy_coordinator)

    async_add_devices(sensors)
