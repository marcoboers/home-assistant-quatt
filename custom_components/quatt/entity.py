"""QuattEntity class."""

from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
import homeassistant.util.dt as dt_util

from .const import ATTRIBUTION, DOMAIN, NAME
from .coordinator import QuattDataUpdateCoordinator
from .coordinator_remote import QuattRemoteDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class QuattSensorEntityDescription(SensorEntityDescription, frozen_or_thawed=True):
    """A class that describes Quatt sensor entities."""

    quatt_hybrid: bool = False
    quatt_all_electric: bool = False
    quatt_duo: bool = False
    quatt_opentherm: bool = False
    quatt_mobile_api: bool = False


class QuattBinarySensorEntityDescription(
    BinarySensorEntityDescription, frozen_or_thawed=True
):
    """A class that describes Quatt binary sensor entities."""

    quatt_hybrid: bool = False
    quatt_all_electric: bool = False
    quatt_duo: bool = False
    quatt_opentherm: bool = False
    quatt_mobile_api: bool = False


class QuattSelectEntityDescription(SelectEntityDescription, frozen_or_thawed=True):
    """A class that describes Quatt select entities."""

    quatt_hybrid: bool = False
    quatt_all_electric: bool = False
    quatt_duo: bool = False
    quatt_opentherm: bool = False
    quatt_mobile_api: bool = False


class QuattEntity(CoordinatorEntity[QuattDataUpdateCoordinator]):
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


class QuattSensor(QuattEntity, SensorEntity):
    """Quatt Sensor class."""

    def __init__(
        self,
        device_name: str,
        device_id: str,
        sensor_key: str,
        coordinator: QuattDataUpdateCoordinator,
        entity_description: QuattSensorEntityDescription,
        attach_to_hub: bool,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(device_name, device_id, sensor_key, coordinator, attach_to_hub)
        self.entity_description = entity_description

    @property
    def entity_registry_enabled_default(self):
        """Return whether the sensor should be enabled by default."""
        return self.entity_description.entity_registry_enabled_default

    @property
    def native_value(self) -> str:
        """Return the native value of the sensor."""
        value = self.coordinator.get_value(self.entity_description.key)

        if not value:
            return value

        if self.entity_description.device_class == SensorDeviceClass.TIMESTAMP:
            value = dt_util.parse_datetime(value)

        return value


class QuattBinarySensor(QuattEntity, BinarySensorEntity):
    """Quatt BinarySensor class."""

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


class QuattSelect(QuattEntity, SelectEntity):
    """Quatt Select class."""

    def __init__(
        self,
        device_name: str,
        device_id: str,
        select_key: str,
        coordinator: QuattDataUpdateCoordinator,
        entity_description: QuattSelectEntityDescription,
        attach_to_hub: bool,
    ) -> None:
        """Initialize the select class."""
        super().__init__(device_name, device_id, select_key, coordinator, attach_to_hub)
        self.entity_description = entity_description

    @property
    def entity_registry_enabled_default(self):
        """Return whether the select should be enabled by default."""
        return self.entity_description.entity_registry_enabled_default

    @property
    def current_option(self) -> str | None:
        """Return the current selected option."""
        return self.coordinator.get_value(self.entity_description.key)

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        # Only remote coordinator supports updating settings
        if not isinstance(self.coordinator, QuattRemoteDataUpdateCoordinator):
            _LOGGER.error("Cannot update sound level: only available via remote API")
            raise NotImplementedError(
                "Setting sound level is only available via remote API"
            )

        # Get current values for both sound levels
        day_level = self.coordinator.get_value("dayMaxSoundLevel")
        night_level = self.coordinator.get_value("nightMaxSoundLevel")

        # Update the value that changed
        if self.entity_description.key == "dayMaxSoundLevel":
            day_level = option
        elif self.entity_description.key == "nightMaxSoundLevel":
            night_level = option

        # Validate that we have both values
        if not day_level or not night_level:
            _LOGGER.error(
                "Cannot update sound level: missing current values (day=%s, night=%s)",
                day_level,
                night_level,
            )
            raise ValueError("Cannot update sound level: missing current values")

        # Send both values to the API
        settings = {
            "dayMaxSoundLevel": day_level,
            "nightMaxSoundLevel": night_level,
        }

        _LOGGER.debug("Updating CIC sound levels: %s", settings)
        success = await self.coordinator.client.update_cic_settings(settings)

        if not success:
            _LOGGER.error("Failed to update sound level settings")
            raise RuntimeError("Failed to update sound level settings")

        # Request a coordinator refresh to update the state
        await self.coordinator.async_request_refresh()
