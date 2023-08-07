"""Binary sensor platform for quatt."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)

from .const import BINARY_SENSORS, DOMAIN
from .coordinator import QuattDataUpdateCoordinator
from .entity import QuattEntity

import logging

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
    def is_on(self) -> bool:
        """Return true if the binary_sensor is on."""
        return self.coordinator.getValue(self.entity_description.key)
