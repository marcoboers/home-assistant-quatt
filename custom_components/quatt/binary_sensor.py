"""Binary sensor platform for quatt."""

from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
import homeassistant.helpers.device_registry as dr
import homeassistant.helpers.entity_registry as er

from .const import (
    DEVICE_BOILER_ID,
    DEVICE_CIC_ID,
    DEVICE_HEATPUMP_1_ID,
    DEVICE_HEATPUMP_2_ID,
    DEVICE_LIST,
    DEVICE_THERMOSTAT_ID,
    DOMAIN,
)
from .coordinator import QuattDataUpdateCoordinator
from .entity import QuattBinarySensorEntityDescription, QuattEntity


def create_heatpump_sensor_entity_descriptions(
    prefix: str, is_duo: bool = False
) -> list[QuattBinarySensorEntityDescription]:
    """Create the heatpump sensor entity descriptions based on the prefix."""
    return [
        QuattBinarySensorEntityDescription(
            name="Silentmode",
            key=f"{prefix}.silentModeStatus",
            translation_key="hp_silentModeStatus",
            icon="mdi:sleep",
            quatt_duo=is_duo,
        ),
        QuattBinarySensorEntityDescription(
            name="Limited by COP",
            key=f"{prefix}.limitedByCop",
            translation_key="hp_silentModeStatus",
            icon="mdi:arrow-collapse-up",
            quatt_duo=is_duo,
        ),
        QuattBinarySensorEntityDescription(
            name="Defrost",
            key=f"{prefix}.computedDefrost",
            translation_key="hp_silentModeStatus",
            icon="mdi:snowflake",
            quatt_duo=is_duo,
        ),
    ]


BINARY_SENSORS = {
    # The HUB CIC sensor must be created first to ensure the HUB device is present
    DEVICE_CIC_ID: [
        QuattBinarySensorEntityDescription(
            name="QC pump protection",
            key="qc.stickyPumpProtectionEnabled",
            icon="mdi:shield-refresh-outline",
        ),
        QuattBinarySensorEntityDescription(
            name="Anti legionella active",
            key="qcAllE.isAntilegionellaActive",
            icon="mdi:shield-check",
            quatt_all_electric=True,
        ),
    ],
    DEVICE_HEATPUMP_1_ID: create_heatpump_sensor_entity_descriptions(
        prefix="hp1", is_duo=False
    ),
    DEVICE_HEATPUMP_2_ID: create_heatpump_sensor_entity_descriptions(
        prefix="hp2", is_duo=True
    ),
    DEVICE_BOILER_ID: [
        QuattBinarySensorEntityDescription(
            name="Heating",
            key="boiler.otFbChModeActive",
            icon="mdi:heating-coil",
            quatt_hybrid=True,
            quatt_opentherm=True,
        ),
        QuattBinarySensorEntityDescription(
            name="Domestic hot water",
            key="boiler.otFbDhwActive",
            icon="mdi:water-boiler",
            quatt_hybrid=True,
            quatt_opentherm=True,
        ),
        QuattBinarySensorEntityDescription(
            name="Flame",
            key="boiler.otFbFlameOn",
            icon="mdi:fire",
            quatt_hybrid=True,
            quatt_opentherm=True,
        ),
        QuattBinarySensorEntityDescription(
            name="CIC heating",
            key="boiler.otTbCH",
            icon="mdi:heating-coil",
            quatt_hybrid=True,
        ),
        QuattBinarySensorEntityDescription(
            name="CIC on/off mode",
            key="boiler.oTtbTurnOnOffBoilerOn",
            icon="mdi:water-boiler",
            quatt_hybrid=True,
        ),
    ],
    DEVICE_THERMOSTAT_ID: [
        QuattBinarySensorEntityDescription(
            name="Heating",
            key="thermostat.otFtChEnabled",
            icon="mdi:home-thermometer",
        ),
        QuattBinarySensorEntityDescription(
            name="Domestic hot water",
            key="thermostat.otFtDhwEnabled",
            icon="mdi:water-thermometer",
        ),
        QuattBinarySensorEntityDescription(
            name="Cooling",
            key="thermostat.otFtCoolingEnabled",
            icon="mdi:snowflake-thermometer",
        ),
    ],
}

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_devices):
    """Set up the binary_sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
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
        for device_sensors in BINARY_SENSORS.values()
        for sensor_description in device_sensors
    ]

    # Determine which sensors to create based on the flags
    sensor_keys = {
        sensor_description.key
        for sensor_description in flat_descriptions
        if not any(getattr(sensor_description, flag) for flag, _ in flag_conditions)
        or all(
            condition
            for flag, condition in flag_conditions
            if getattr(sensor_description, flag)
        )
    }

    # Remove not applicable sensors
    hub_id = (entry.unique_id or entry.entry_id).strip()
    for dev_id in device_ids:
        for entry_reg in er.async_entries_for_device(
            registry, dev_id, include_disabled_entities=True
        ):
            if (
                entry_reg.config_entry_id == entry.entry_id
                and entry_reg.domain == BINARY_SENSOR_DOMAIN
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
    sensors: list[QuattBinarySensor] = []
    for device_id, sensor_descriptions in BINARY_SENSORS.items():
        sensors.extend(
            QuattBinarySensor(
                device_name=device_name_map.get(device_id, device_id),
                device_id=device_id,
                sensor_key=sensor_description.key,
                coordinator=coordinator,
                entity_description=sensor_description,
                attach_to_hub=(device_id == DEVICE_CIC_ID),
            )
            for sensor_description in sensor_descriptions
            if sensor_description.key in sensor_keys
        )

    async_add_devices(sensors)


class QuattBinarySensor(QuattEntity, BinarySensorEntity):
    """quatt binary_sensor class."""

    def __init__(
        self,
        device_name: str,
        device_id: str,
        sensor_key: str,
        coordinator: QuattDataUpdateCoordinator,
        entity_description: QuattBinarySensorEntityDescription,
        attach_to_hub: bool,
    ) -> None:
        """Initialize the binary_sensor class."""
        super().__init__(device_name, device_id, sensor_key, coordinator, attach_to_hub)
        self.entity_description = entity_description

    @property
    def entity_registry_enabled_default(self):
        """Return whether the sensor should be enabled by default."""
        return self.entity_description.entity_registry_enabled_default

    @property
    def is_on(self) -> bool:
        """Return true if the binary_sensor is on."""
        return self.coordinator.get_value(self.entity_description.key)
