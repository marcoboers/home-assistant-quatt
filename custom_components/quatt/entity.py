"""QuattEntity class."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN, NAME
from .coordinator import QuattDataUpdateCoordinator


class QuattSensorEntityDescription(SensorEntityDescription, frozen_or_thawed=True):
    """A class that describes Quatt sensor entities."""

    quatt_duo: bool = False


class QuattEntity(CoordinatorEntity):
    """QuattEntity class."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: QuattDataUpdateCoordinator,
        sensor_key: str,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = coordinator.config_entry.entry_id + sensor_key
        # self._attr_device_info = DeviceInfo(
        #     identifiers={(DOMAIN, self.unique_id)},
        #     name=NAME,
        #     model=VERSION,
        #     manufacturer=NAME,
        # )

    @property
    def device_info(self):
        """Return the device information."""
        return {
            "identifiers": {(DOMAIN, self.coordinator.config_entry.entry_id)},
            "name": "Heatpump",
            "manufacturer": NAME,
            "model": self.coordinator.getValue("system.hostName"),
        }
