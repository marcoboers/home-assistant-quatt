"""QuattEntity class."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntityDescription
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN, NAME
from .coordinator import QuattDataUpdateCoordinator


class QuattSensorEntityDescription(SensorEntityDescription, frozen_or_thawed=True):
    """A class that describes Quatt sensor entities."""

    quatt_hybrid: bool = False
    quatt_all_electric: bool = False
    quatt_duo: bool = False
    quatt_opentherm: bool = False


class QuattBinarySensorEntityDescription(
    BinarySensorEntityDescription, frozen_or_thawed=True
):
    """A class that describes Quatt binary sensor entities."""

    quatt_hybrid: bool = False
    quatt_all_electric: bool = False
    quatt_duo: bool = False
    quatt_opentherm: bool = False


class QuattEntity(CoordinatorEntity):
    """QuattEntity class."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        device_name: str,
        device_id: str,
        sensor_key: str,
        coordinator: QuattDataUpdateCoordinator,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = coordinator.config_entry.entry_id + sensor_key
        self._device_name = device_name
        self._device_id = device_id

    @property
    def device_info(self):
        """Return the device information."""
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._device_name,
            "manufacturer": NAME,
            "model": "—",
        }
