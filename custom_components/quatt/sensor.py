"""Sensor platform for quatt."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)

import homeassistant.util.dt as dt_util

from .const import DOMAIN, SENSORS
from .coordinator import QuattDataUpdateCoordinator
from .entity import QuattEntity

import logging

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_devices):
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    _LOGGER.debug("Heatpump 1 active: %s", coordinator.heatpump1Active())
    _LOGGER.debug("Heatpump 2 active: %s", coordinator.heatpump2Active())
    _LOGGER.debug("boiler OpenTherm: %s", coordinator.boilerOpenTherm())
    async_add_devices(
        QuattSensor(
            coordinator=coordinator,
            sensor_key=entity_description.key,
            entity_description=entity_description,
        )
        for entity_description in SENSORS
    )


class QuattSensor(QuattEntity, SensorEntity):
    """quatt Sensor class."""

    def __init__(
        self,
        sensor_key: str,
        coordinator: QuattDataUpdateCoordinator,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator, sensor_key)
        self.entity_description = entity_description

    @property
    def native_value(self) -> str:
        """Return the native value of the sensor."""
        value = self.coordinator.getValue(self.entity_description.key)

        if not value:
            return value

        if self.entity_description.device_class == SensorDeviceClass.TIMESTAMP:
            value = dt_util.parse_datetime(value)

        return value
