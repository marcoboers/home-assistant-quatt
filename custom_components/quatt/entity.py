"""QuattEntity class."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntityDescription
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.helpers.device_registry import DeviceInfo
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
        attach_to_hub: bool,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)

        # Get a HUB id based in the config entry id to make sure all entities
        # created in this config entry are part of the same device.
        self._hub_id = (
            coordinator.config_entry.unique_id or coordinator.config_entry.entry_id
        ).strip()

        self._device_name = device_name
        self._device_id = device_id
        self._attr_unique_id = f"{self._hub_id}:{device_id}:{sensor_key}"
        self._attr_device_info = DeviceInfo(
            identifiers={
                (
                    DOMAIN,
                    self._hub_id if attach_to_hub else f"{self._hub_id}:{device_id}",
                )
            },
            via_device=None if attach_to_hub else (DOMAIN, self._hub_id),
            name=device_name,
            manufacturer=NAME,
            model="—",
        )
