"""Shared setup logic for Quatt entities."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
import homeassistant.helpers.device_registry as dr
import homeassistant.helpers.entity_registry as er

from .const import DEVICE_CIC_ID, DEVICE_LIST, DOMAIN
from .coordinator import QuattDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entities(
    hass: HomeAssistant,
    coordinator: QuattDataUpdateCoordinator,
    entry,
    remote: bool,
    entity_class,
    entity_descriptions: dict[str, list],
    entity_domain: str,
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
        for device_sensors in entity_descriptions.values()
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
                and entry_reg.domain == entity_domain
                and entry_reg.platform == DOMAIN
                and not any(entry_reg.unique_id.endswith(key) for key in sensor_keys)
            ):
                _LOGGER.info(
                    "[%s] Removing obsolete entity: %s (%s)",
                    entity_domain,
                    entry_reg.entity_id,
                    entry_reg.unique_id,
                )
                registry.async_remove(entry_reg.entity_id)

        # Remove the device in case it has no remaining entities
        if not any(er.async_entries_for_device(registry, dev_id)):
            # Do not remove the hub device
            dev = device_reg.async_get(dev_id)
            if dev and (DOMAIN, hub_id) in dev.identifiers:
                continue
            _LOGGER.info(
                "[%s] Removing obsolete device: %s (identifiers=%s)",
                entity_domain,
                dev.name or dev_id,
                dev.identifiers if dev else "unknown",
            )
            device_reg.async_remove_device(dev_id)

    # Create sensor entities based on the filtered sensor keys
    device_name_map = {d["id"]: d["name"] for d in DEVICE_LIST}
    sensors: list = []
    for device_id, sensor_descriptions in entity_descriptions.items():
        for sensor_description in sensor_descriptions:
            # Skip sensors that are not selected based on the installation type
            if sensor_description.key not in sensor_keys:
                continue

            # Skip sensors that do not match the remote indicator
            if sensor_keys[sensor_description.key] != remote:
                continue

            _LOGGER.info(
                "[%s] Creating entity: %s (device=%s, remote=%s)",
                entity_domain,
                sensor_description.key,
                device_id,
                remote,
            )

            sensors.append(
                entity_class(
                    device_name=device_name_map.get(device_id, device_id),
                    device_id=device_id,
                    sensor_key=sensor_description.key,
                    coordinator=coordinator,
                    entity_description=sensor_description,
                    attach_to_hub=(device_id == DEVICE_CIC_ID),
                )
            )

    return sensors
