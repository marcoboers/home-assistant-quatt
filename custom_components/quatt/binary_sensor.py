"""Binary sensor platform for quatt."""
from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)

from .const import DOMAIN
from .coordinator import QuattDataUpdateCoordinator
from .entity import QuattEntity, QuattSensorEntityDescription

BINARY_SENSORS = [
    # Heatpump 1
    QuattSensorEntityDescription(
        name="HP1 silentMode",
        key="hp1.silentModeStatus",
        translation_key="hp_silentModeStatus",
        icon="mdi:sleep",
    ),
    QuattSensorEntityDescription(
        name="HP1 limitedByCop",
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
        name="HP2 silentMode",
        key="hp2.silentModeStatus",
        translation_key="hp_silentModeStatus",
        icon="mdi:sleep",
        quatt_duo=True,
    ),
    QuattSensorEntityDescription(
        name="HP2 limitedByCop",
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
    ),
    QuattSensorEntityDescription(
        name="Boiler domestic hot water",
        key="boiler.otFbDhwActive",
        icon="mdi:water-boiler",
    ),
    QuattSensorEntityDescription(
        name="Boiler flame",
        key="boiler.otFbFlameOn",
        icon="mdi:fire",
    ),
    QuattSensorEntityDescription(
        name="Boiler heating",
        key="boiler.otTbCH",
        icon="mdi:heating-coil",
    ),
    QuattSensorEntityDescription(
        name="Boiler on/off mode",
        key="boiler.oTtbTurnOnOffBoilerOn",
        icon="mdi:water-boiler",
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


async def async_setup_entry(hass, entry, async_add_devices):
    """Set up the binary_sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_devices(
        QuattBinarySensor(
            coordinator=coordinator,
            sensor_key=entity_description.key,
            entity_description=entity_description,
        )
        for entity_description in BINARY_SENSORS
    )


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
        # Only check the duo property when set, enable when duo found
        if self.entity_description.entity_registry_enabled_default and self.entity_description.quatt_duo:
            return self.coordinator.heatpump2Active()

        # For all other sensors
        return self.entity_description.entity_registry_enabled_default


    @property
    def is_on(self) -> bool:
        """Return true if the binary_sensor is on."""
        if not self.entity_description.quatt_duo or self.coordinator.heatpump2Active():
            return self.coordinator.getValue(self.entity_description.key)
        return False
