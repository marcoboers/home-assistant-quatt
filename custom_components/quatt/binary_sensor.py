"""Binary sensor platform for quatt."""

from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
import homeassistant.helpers.device_registry as dr
import homeassistant.helpers.entity_registry as er

from .const import DOMAIN
from .coordinator import QuattDataUpdateCoordinator
from .entity import QuattEntity, QuattSensorEntityDescription

BINARY_SENSORS = [
    # Heatpump 1
    QuattSensorEntityDescription(
        name="HP1 silentmode",
        key="hp1.silentModeStatus",
        translation_key="hp_silentModeStatus",
        icon="mdi:sleep",
    ),
    QuattSensorEntityDescription(
        name="HP1 limited by COP",
        key="hp1.limitedByCop",
        translation_key="hp_silentModeStatus",
        icon="mdi:arrow-collapse-up",
    ),
    QuattSensorEntityDescription(
        name="HP1 defrost",
        key="hp1.computedDefrost",
        translation_key="hp_silentModeStatus",
        icon="mdi:snowflake",
    ),
    # Heatpump 2
    QuattSensorEntityDescription(
        name="HP2 silentmode",
        key="hp2.silentModeStatus",
        translation_key="hp_silentModeStatus",
        icon="mdi:sleep",
        quatt_duo=True,
    ),
    QuattSensorEntityDescription(
        name="HP2 limited by COP",
        key="hp2.limitedByCop",
        translation_key="hp_silentModeStatus",
        icon="mdi:arrow-collapse-up",
        quatt_duo=True,
    ),
    QuattSensorEntityDescription(
        name="HP2 defrost",
        key="hp2.computedDefrost",
        icon="mdi:snowflake",
        quatt_duo=True,
    ),
    # Boiler
    QuattSensorEntityDescription(
        name="Boiler heating",
        key="boiler.otFbChModeActive",
        icon="mdi:heating-coil",
        quatt_hybrid=True,
        quatt_opentherm=True,
    ),
    QuattSensorEntityDescription(
        name="Boiler domestic hot water",
        key="boiler.otFbDhwActive",
        icon="mdi:water-boiler",
        quatt_hybrid=True,
        quatt_opentherm=True,
    ),
    QuattSensorEntityDescription(
        name="Boiler flame",
        key="boiler.otFbFlameOn",
        icon="mdi:fire",
        quatt_hybrid=True,
        quatt_opentherm=True,
    ),
    QuattSensorEntityDescription(
        name="Boiler CIC heating",
        key="boiler.otTbCH",
        icon="mdi:heating-coil",
        quatt_hybrid=True,
    ),
    QuattSensorEntityDescription(
        name="Boiler CIC on/off",
        key="boiler.oTtbTurnOnOffBoilerOn",
        icon="mdi:water-boiler",
        quatt_hybrid=True,
    ),
    # Thermostat
    QuattSensorEntityDescription(
        name="Thermostat heating",
        key="thermostat.otFtChEnabled",
        icon="mdi:home-thermometer",
    ),
    QuattSensorEntityDescription(
        name="Thermostat domestic hot water",
        key="thermostat.otFtDhwEnabled",
        icon="mdi:water-thermometer",
    ),
    QuattSensorEntityDescription(
        name="Thermostat cooling",
        key="thermostat.otFtCoolingEnabled",
        icon="mdi:snowflake-thermometer",
    ),
    # QC
    QuattSensorEntityDescription(
        name="QC pump protection",
        key="qc.stickyPumpProtectionEnabled",
        icon="mdi:shield-refresh-outline",
    ),
]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_devices):
    """Set up the binary_sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    registry = er.async_get(hass)

    _LOGGER.debug("Heatpump 1 active: %s", coordinator.heatpump1Active())
    _LOGGER.debug("Heatpump 2 active: %s", coordinator.heatpump2Active())
    _LOGGER.debug("All electric active: %s", coordinator.allElectricActive())
    _LOGGER.debug("boiler OpenTherm: %s", coordinator.boilerOpenTherm())

    # Create only those sensors that make sense for this installation type.
    # Remove sensors that are not applicable based on the configuration.
    # This can occur when the configuration changes, e.g., from hybrid or duo to all-electric.
    device_reg = dr.async_get(hass)
    devices = dr.async_entries_for_config_entry(device_reg, entry.entry_id)
    device_ids = {dev.id for dev in devices}

    # Cache the active states
    heatpump2_active = coordinator.heatpump2Active()
    all_electric_active = coordinator.allElectricActive()
    boiler_opentherm = coordinator.boilerOpenTherm()

    # Determine which sensors to create based on the detected configuration
    flag_conditions = [
        ("quatt_hybrid", not all_electric_active),
        ("quatt_all_electric", all_electric_active),
        ("quatt_duo", heatpump2_active),
        ("quatt_opentherm", boiler_opentherm),
    ]

    # Determine which sensors to create based on the flags
    sensor_keys = {
        sensor_description.key
        for sensor_description in BINARY_SENSORS
        if not any(getattr(sensor_description, flag) for flag, _ in flag_conditions)
        or all(
            condition
            for flag, condition in flag_conditions
            if getattr(sensor_description, flag)
        )
    }

    # Remove not applicable sensors
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

    # Create sensor entities based on the filtered sensor keys
    sensors = [
        QuattBinarySensor(
            coordinator=coordinator,
            sensor_key=descr.key,
            entity_description=descr,
        )
        for descr in BINARY_SENSORS
        if descr.key in sensor_keys
    ]
    async_add_devices(sensors)


class QuattBinarySensor(QuattEntity, BinarySensorEntity):
    """quatt binary_sensor class."""

    def __init__(
        self,
        sensor_key: str,
        coordinator: QuattDataUpdateCoordinator,
        entity_description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary_sensor class."""
        super().__init__(coordinator, sensor_key)
        self.entity_description = entity_description

    @property
    def entity_registry_enabled_default(self):
        """Return whether the sensor should be enabled by default."""
        return self.entity_description.entity_registry_enabled_default

    @property
    def is_on(self) -> bool:
        """Return true if the binary_sensor is on."""
        return self.coordinator.getValue(self.entity_description.key)
