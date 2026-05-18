"""QuattEntity class."""

from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityDescription,
    HVACMode,
)
from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity
import homeassistant.util.dt as dt_util

from .const import ATTRIBUTION, DOMAIN, NAME, QuattDeviceKind
from .coordinator import QuattDataUpdateCoordinator
from .coordinator_remote_cic import QuattCicRemoteDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

CHILL_SENTENCE_CASE_KEYS = {"color", "fanMode", "mode", "status", "updateState"}


def _format_chill_sentence_case(value: str) -> str:
    """Format Quatt Chill enum text as sentence case."""
    text = value.replace("_", " ").lower()
    return text[:1].upper() + text[1:]


class QuattChillApiEnum(str, Enum):
    """Base class for Quatt Chill API enum values."""

    @classmethod
    def from_api_value(cls, value: Any):
        """Return the enum member for a case-insensitive API value."""
        if not isinstance(value, str):
            return None

        normalized_value = value.upper()
        for item in cls:
            if item.value == normalized_value:
                return item
        return None

    @classmethod
    def from_display_value(cls, value: str):
        """Return the enum member for a display value."""
        normalized_value = value.replace(" ", "_").upper()
        return cls.from_api_value(normalized_value)

    @property
    def display_value(self) -> str:
        """Return the Home Assistant display value."""
        return _format_chill_sentence_case(self.value)


class QuattChillFanMode(QuattChillApiEnum):
    """Quatt Chill fan mode values."""

    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"


class QuattChillMode(QuattChillApiEnum):
    """Quatt Chill mode values."""

    COOLING = "COOLING"
    HEATING = "HEATING"

    @property
    def hvac_mode(self) -> HVACMode:
        """Return the matching Home Assistant HVAC mode."""
        return HVACMode.COOL if self == QuattChillMode.COOLING else HVACMode.HEAT


class QuattChillStatus(QuattChillApiEnum):
    """Quatt Chill status values."""

    OFF = "OFF"
    OFFLINE = "OFFLINE"
    COOLING = "COOLING"
    HEATING = "HEATING"

    @property
    def hvac_mode(self) -> HVACMode:
        """Return the matching Home Assistant HVAC mode."""
        if self in {QuattChillStatus.OFF, QuattChillStatus.OFFLINE}:
            return HVACMode.OFF
        return HVACMode.COOL if self == QuattChillStatus.COOLING else HVACMode.HEAT


def _format_chill_enum_value(key: str, value: str) -> str:
    """Format a Quatt Chill enum text value for Home Assistant."""
    enum_class: type[QuattChillApiEnum] | None = {
        "fanMode": QuattChillFanMode,
        "mode": QuattChillMode,
        "status": QuattChillStatus,
    }.get(key)

    if enum_class:
        if enum_value := enum_class.from_api_value(value):
            return enum_value.display_value
        _LOGGER.debug("Unknown Chill %s value: %s", key, value)

    return _format_chill_sentence_case(value)


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
        device_kind: QuattDeviceKind,
        unique_id_key: str | None = None,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)

        entry = coordinator.config_entry
        if entry is None:
            raise RuntimeError("Coordinator has no config_entry")

        # Get a HUB id based in the config entry id to make sure all entities
        # created in this config entry are part of the same device.
        self._hub_id = (entry.unique_id or entry.entry_id).strip()

        self._device_name = device_name
        self._device_id = device_id
        self._attr_unique_id = (
            f"{self._hub_id}:{device_id}:{unique_id_key or sensor_key}"
        )

        attach_to_hub = device_kind == QuattDeviceKind.HUB
        is_service_device = device_kind == QuattDeviceKind.SERVICE

        if attach_to_hub:
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, self._hub_id)},
                name=device_name,
                manufacturer=NAME,
                model="—",
                entry_type=DeviceEntryType.SERVICE if is_service_device else None,
            )
        else:
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, f"{self._hub_id}:{device_id}")},
                via_device=(DOMAIN, self._hub_id),
                name=device_name,
                manufacturer=NAME,
                model="—",
                entry_type=DeviceEntryType.SERVICE if is_service_device else None,
            )

    def _current_chill_index(self) -> int | None:
        """Return the current Chill list index for this entity's device."""
        chills = self.coordinator.get_value("chills", [])
        if not isinstance(chills, list):
            return None

        for index, chill in enumerate(chills):
            if isinstance(chill, dict) and chill.get("uuid") == self._device_id:
                return index

        return None

    @staticmethod
    def _chill_key_at_index(key: str, index: int) -> str:
        """Return a Chill coordinator key for the current response-list index."""
        key_parts = key.split(".", 2)
        if len(key_parts) < 2 or key_parts[0] != "chills":
            return key
        if len(key_parts) == 2:
            return f"chills.{index}"
        return f"chills.{index}.{key_parts[2]}"


class QuattSensor(QuattEntity, SensorEntity):
    """Quatt Sensor class."""

    def __init__(
        self,
        device_name: str,
        device_id: str,
        sensor_key: str,
        coordinator: QuattDataUpdateCoordinator,
        entity_description: QuattSensorEntityDescription,
        device_kind: QuattDeviceKind,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(
            device_name,
            device_id,
            sensor_key,
            coordinator,
            device_kind,
            entity_description.quatt_unique_id_key,
        )
        self.entity_description = entity_description

    @property
    def entity_registry_enabled_default(self):
        """Return whether the sensor should be enabled by default."""
        return self.entity_description.entity_registry_enabled_default

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        """Return the native value of the sensor."""
        value = self.coordinator.get_value(self.entity_description.key)

        if value is None:
            return None

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
        device_kind: QuattDeviceKind,
    ) -> None:
        """Initialize the binary_sensor class."""
        super().__init__(
            device_name,
            device_id,
            sensor_key,
            coordinator,
            device_kind,
            entity_description.quatt_unique_id_key,
        )
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
        sensor_key: str,
        coordinator: QuattDataUpdateCoordinator,
        entity_description: QuattSelectEntityDescription,
        device_kind: QuattDeviceKind,
    ) -> None:
        """Initialize the select class."""
        super().__init__(
            device_name,
            device_id,
            sensor_key,
            coordinator,
            device_kind,
            entity_description.quatt_unique_id_key,
        )
        self.entity_description = entity_description

    @property
    def entity_registry_enabled_default(self):
        """Return whether the select should be enabled by default."""
        return self.entity_description.entity_registry_enabled_default

    @property
    def current_option(self) -> str | None:
        """Return the current selected option."""
        return self.coordinator.get_value(self.entity_description.key)

    def select_option(self, option: str) -> None:
        """Implement required base class method but do not use it (async handled separately)."""
        raise NotImplementedError("Use async_select_option instead")

    @abstractmethod
    async def _perform_api_update(self, option: str) -> bool:
        """Perform the API call to update this setting.

        Must return True if the update succeeded, False otherwise.
        """
        raise NotImplementedError

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        # Only remote coordinator supports updating settings
        if not isinstance(self.coordinator, QuattCicRemoteDataUpdateCoordinator):
            _LOGGER.error(
                "Cannot update %s: only available via remote API",
                self.entity_description.key,
            )
            raise NotImplementedError(
                f"Setting {self.entity_description.key} is only available via remote API"
            )

        success = False
        try:
            success = await self._perform_api_update(option)
        except Exception as err:
            _LOGGER.exception("Error updating %s", self.entity_description.key)
            raise RuntimeError(
                f"Failed to update {self.entity_description.key}"
            ) from err

        if not success:
            _LOGGER.warning("Failed to update %s", self.entity_description.key)
            raise RuntimeError(f"Failed to update {self.entity_description.key}")

        # Always refresh coordinator data after a successful update
        await self.coordinator.async_request_refresh()


class QuattSwitch(QuattEntity, SwitchEntity):
    """Quatt Switch class."""

    def __init__(
        self,
        device_name: str,
        device_id: str,
        sensor_key: str,
        coordinator: QuattDataUpdateCoordinator,
        entity_description: QuattSwitchEntityDescription,
        device_kind: QuattDeviceKind,
    ) -> None:
        """Initialize the switch class."""
        super().__init__(
            device_name,
            device_id,
            sensor_key,
            coordinator,
            device_kind,
            entity_description.quatt_unique_id_key,
        )
        self.entity_description = entity_description

    @property
    def entity_registry_enabled_default(self):
        """Return whether the switch should be enabled by default."""
        return self.entity_description.entity_registry_enabled_default

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self.coordinator.get_value(self.entity_description.key)

    def turn_on(self, **kwargs) -> None:
        """Implement required base class method but do not use it (async handled separately)."""
        raise NotImplementedError("Use async_turn_on instead")

    def turn_off(self, **kwargs) -> None:
        """Implement required base class method but do not use it (async handled separately)."""
        raise NotImplementedError("Use async_turn_off instead")

    @abstractmethod
    async def _perform_api_update(self, state: bool) -> bool:
        """Perform the API call to update this setting.

        Must return True if the update succeeded, False otherwise.
        """
        raise NotImplementedError

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        await self._async_set_state(True)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        await self._async_set_state(False)

    async def _async_set_state(self, state: bool) -> None:
        """Set the switch state."""
        # Only remote coordinator supports updating settings
        if not isinstance(self.coordinator, QuattCicRemoteDataUpdateCoordinator):
            _LOGGER.error(
                "Cannot update %s: only available via remote API",
                self.entity_description.key,
            )
            raise NotImplementedError(
                f"Setting {self.entity_description.key} is only available via remote API"
            )

        success = False
        try:
            success = await self._perform_api_update(state)
        except Exception as err:
            _LOGGER.exception("Error updating %s", self.entity_description.key)
            raise RuntimeError(
                f"Failed to update {self.entity_description.key}"
            ) from err

        if not success:
            _LOGGER.warning("Failed to update %s", self.entity_description.key)
            raise RuntimeError(f"Failed to update {self.entity_description.key}")

        # Always refresh coordinator data after a successful update
        await self.coordinator.async_request_refresh()


class QuattNumber(QuattEntity, NumberEntity):
    """Quatt Number class."""

    def __init__(
        self,
        device_name: str,
        device_id: str,
        sensor_key: str,
        coordinator: QuattDataUpdateCoordinator,
        entity_description: QuattNumberEntityDescription,
        device_kind: QuattDeviceKind,
    ) -> None:
        """Initialize the number class."""
        super().__init__(
            device_name,
            device_id,
            sensor_key,
            coordinator,
            device_kind,
            entity_description.quatt_unique_id_key,
        )
        self.entity_description = entity_description

    @property
    def entity_registry_enabled_default(self):
        """Return whether the number should be enabled by default."""
        return self.entity_description.entity_registry_enabled_default

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        return self.coordinator.get_value(f"{self.entity_description.key}.value")

    @property
    def native_min_value(self) -> float:
        """Return the minimum value."""
        value = self.coordinator.get_value(f"{self.entity_description.key}.minValue")
        if value is None:
            return super().native_min_value
        return value

    @property
    def native_max_value(self) -> float:
        """Return the maximum value."""
        value = self.coordinator.get_value(f"{self.entity_description.key}.maxValue")
        if value is None:
            return super().native_max_value
        return value

    @property
    def native_step(self) -> float | None:
        """Return the step value."""
        value = self.coordinator.get_value(f"{self.entity_description.key}.increment")
        if value is None:
            return super().native_step
        return value

    def set_native_value(self, value: float) -> None:
        """Implement required base class method but do not use it (async handled separately)."""
        raise NotImplementedError("Use async_set_native_value instead")

    @abstractmethod
    async def _perform_api_update(self, value: float) -> bool:
        """Perform the API call to update this setting.

        Must return True if the update succeeded, False otherwise.
        """
        raise NotImplementedError

    async def async_set_native_value(self, value: float) -> None:
        """Set the new value."""
        # Only remote coordinator supports updating settings
        if not isinstance(self.coordinator, QuattCicRemoteDataUpdateCoordinator):
            _LOGGER.error(
                "Cannot update %s: only available via remote API",
                self.entity_description.key,
            )
            raise NotImplementedError(
                f"Setting {self.entity_description.key} is only available via remote API"
            )

        success = False
        try:
            success = await self._perform_api_update(value)
        except Exception as err:
            _LOGGER.exception("Error updating %s", self.entity_description.key)
            raise RuntimeError(
                f"Failed to update {self.entity_description.key}"
            ) from err

        if not success:
            _LOGGER.warning("Failed to update %s", self.entity_description.key)
            raise RuntimeError(f"Failed to update {self.entity_description.key}")

        # Always refresh coordinator data after a successful update
        await self.coordinator.async_request_refresh()


@dataclass(frozen=True)
class QuattFeatureFlags:
    """Quatt feature flags used an entity."""

    hybrid: bool = False
    all_electric: bool = False
    duo: bool = False
    opentherm: bool = False
    mobile_api: bool = False


class QuattSensorEntityDescription(SensorEntityDescription, frozen_or_thawed=True):
    """A class that describes Quatt sensor entities."""

    quatt_features: QuattFeatureFlags = QuattFeatureFlags()
    quatt_entity_class: type[QuattEntity] = QuattSensor
    quatt_unique_id_key: str | None = None


class QuattBinarySensorEntityDescription(
    BinarySensorEntityDescription, frozen_or_thawed=True
):
    """A class that describes Quatt binary sensor entities."""

    quatt_features: QuattFeatureFlags = QuattFeatureFlags()
    quatt_entity_class: type[QuattEntity] = QuattBinarySensor
    quatt_unique_id_key: str | None = None


class QuattSelectEntityDescription(SelectEntityDescription, frozen_or_thawed=True):
    """A class that describes Quatt select entities."""

    quatt_features: QuattFeatureFlags = QuattFeatureFlags()
    quatt_entity_class: type[QuattEntity] = QuattSelect
    quatt_unique_id_key: str | None = None


class QuattSwitchEntityDescription(SwitchEntityDescription, frozen_or_thawed=True):
    """A class that describes Quatt switch entities."""

    quatt_features: QuattFeatureFlags = QuattFeatureFlags()
    quatt_entity_class: type[QuattEntity] = QuattSwitch
    quatt_unique_id_key: str | None = None


class QuattNumberEntityDescription(NumberEntityDescription, frozen_or_thawed=True):
    """A class that describes Quatt number entities."""

    quatt_features: QuattFeatureFlags = QuattFeatureFlags()
    quatt_entity_class: type[QuattEntity] = QuattNumber
    quatt_unique_id_key: str | None = None


class QuattClimateEntityDescription(ClimateEntityDescription, frozen_or_thawed=True):
    """A class that describes Quatt climate entities."""

    quatt_features: QuattFeatureFlags = QuattFeatureFlags()
    quatt_entity_class: type[QuattEntity] = ClimateEntity
    quatt_unique_id_key: str | None = None
