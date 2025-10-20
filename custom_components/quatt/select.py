"""Select platform for quatt."""

from __future__ import annotations

import logging

from homeassistant.components.select import DOMAIN as SELECT_DOMAIN
from homeassistant.core import HomeAssistant
import homeassistant.helpers.device_registry as dr
import homeassistant.helpers.entity_registry as er

from .const import (
    DEVICE_BOILER_ID,
    DEVICE_CIC_ID,
    DEVICE_FLOWMETER_ID,
    DEVICE_HEAT_BATTERY_ID,
    DEVICE_HEAT_CHARGER_ID,
    DEVICE_HEATPUMP_1_ID,
    DEVICE_HEATPUMP_2_ID,
    DEVICE_LIST,
    DEVICE_THERMOSTAT_ID,
    DOMAIN,
)
from .coordinator import QuattDataUpdateCoordinator
from .entity import QuattSelect, QuattSelectEntityDescription

# Sound level options
SOUND_LEVEL_OPTIONS = ["normal", "library", "silent"]

SELECTS = {
    # The HUB CIC sensor must be created first to ensure the HUB device is present
    DEVICE_CIC_ID: [
        QuattSelectEntityDescription(
            key="dayMaxSoundLevel",
            name="Day max sound level",
            icon="mdi:volume-high",
            options=SOUND_LEVEL_OPTIONS,
            quatt_mobile_api=True,
        ),
        QuattSelectEntityDescription(
            key="nightMaxSoundLevel",
            name="Night max sound level",
            icon="mdi:volume-low",
            options=SOUND_LEVEL_OPTIONS,
            quatt_mobile_api=True,
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
    selects += await async_setup_select(hass, local_coordinator, entry)

    _LOGGER.debug(len(selects))

    if remote_coordinator:
        selects += await async_setup_select(hass, remote_coordinator, entry, True)

    _LOGGER.debug(len(selects))

    async_add_devices(selects)


async def async_setup_select(
    hass: HomeAssistant,
    coordinator: QuattDataUpdateCoordinator,
    entry,
    remote: bool = False,
):
    """Set up the binary_sensor platform."""
    registry = er.async_get(hass)

    # Cache the active states
    heatpump_1_active = coordinator.heatpump_1_active()
    heatpump_2_active = coordinator.heatpump_2_active()
    all_electric_active = coordinator.all_electric_active()
    is_boiler_opentherm = coordinator.is_boiler_opentherm()

    _LOGGER.debug("Heatpump 1 active: %s", heatpump_1_active)
    _LOGGER.debug("Heatpump 2 active: %s", heatpump_2_active)
    _LOGGER.debug("All electric active: %s", all_electric_active)
    _LOGGER.debug("boiler OpenTherm: %s", is_boiler_opentherm)

    # Create only those sensors that make sense for this installation type.
    # Remove sensors that are not applicable based on the configuration.
    # This can occur when the configuration changes, e.g., from hybrid or duo to all-electric.
    device_reg = dr.async_get(hass)
    devices = dr.async_entries_for_config_entry(device_reg, entry.entry_id)
    device_ids = {dev.id for dev in devices}

    # Determine which sensors to create based on the detected configuration
    flag_conditions = [
        ("quatt_hybrid", not all_electric_active),
        ("quatt_all_electric", all_electric_active),
        ("quatt_duo", heatpump_2_active),
        ("quatt_opentherm", is_boiler_opentherm),
    ]

    # Flatten out all sensor descriptions
    flat_descriptions = [
        sensor_description
        for device_sensors in SELECTS.values()
        for sensor_description in device_sensors
    ]

    # Determine which sensors to create based on the flags
    sensor_keys: dict[str, bool] = {}
    for desc in flat_descriptions:
        # Check if it matches normal feature conditions
        if not any(getattr(desc, flag) for flag, _ in flag_conditions) or all(
            condition for flag, condition in flag_conditions if getattr(desc, flag)
        ):
            # Include the sensor and the mobile API status
            sensor_keys[desc.key] = desc.quatt_mobile_api

    # Remove not applicable sensors
    hub_id = (entry.unique_id or entry.entry_id).strip()
    for dev_id in device_ids:
        for entry_reg in er.async_entries_for_device(
            registry, dev_id, include_disabled_entities=True
        ):
            if (
                entry_reg.config_entry_id == entry.entry_id
                and entry_reg.domain == SELECT_DOMAIN
                and entry_reg.platform == DOMAIN
                and not any(entry_reg.unique_id.endswith(key) for key in sensor_keys)
            ):
                registry.async_remove(entry_reg.entity_id)

        # Remove the device in case it has no remaining entities
        if not any(er.async_entries_for_device(registry, dev_id)):
            # Do not remove the hub device
            dev = device_reg.async_get(dev_id)
            if dev and (DOMAIN, hub_id) in dev.identifiers:
                continue
            device_reg.async_remove_device(dev_id)

    # Create sensor entities based on the filtered sensor keys
    device_name_map = {d["id"]: d["name"] for d in DEVICE_LIST}
    sensors: list[QuattSelect] = []
    for device_id, sensor_descriptions in SELECTS.items():
        for sensor_description in sensor_descriptions:
            # Skip sensors that are not selected based on the installation type
            if sensor_description.key not in sensor_keys:
                continue

            # Skip sensors that do not match the remote indicator
            if sensor_keys[sensor_description.key] != remote:
                continue

            sensors.append(
                QuattSelect(
                    device_name=device_name_map.get(device_id, device_id),
                    device_id=device_id,
                    sensor_key=sensor_description.key,
                    coordinator=coordinator,
                    entity_description=sensor_description,
                    attach_to_hub=(device_id == DEVICE_CIC_ID),
                )
            )

    return sensors
