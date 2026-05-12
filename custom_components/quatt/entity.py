"""QuattEntity class."""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Mapping
from copy import deepcopy
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
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.components.number import (
    DEFAULT_MAX_VALUE,
    DEFAULT_MIN_VALUE,
    DEFAULT_STEP,
    NumberEntity,
    NumberEntityDescription,
)
from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import PRECISION_TENTHS, UnitOfTemperature
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity
import homeassistant.util.dt as dt_util

from .api_remote_cic import QuattCicRemoteApiClient
from .api_remote_home_battery import QuattHomeBatteryApiClient
from .const import (
    ALL_ELECTRIC_SYSTEM,
    ATTRIBUTION,
    DOMAIN,
    DUO_HEATPUMP_SYSTEM,
    NAME,
    OPENTHERM_SYSTEM,
    QuattDeviceKind,
)
from .coordinator import QuattDataUpdateCoordinator
from .coordinator_home_battery import QuattHomeBatteryDataUpdateCoordinator
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
        self._attr_unique_id = f"{self._hub_id}:{device_id}:{unique_id_key or sensor_key}"

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


class QuattChillSensor(QuattSensor):
    """Quatt Chill sensor class."""

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        """Return the native value of the Chill sensor."""
        chill_index = self._current_chill_index()
        if chill_index is None:
            return None

        value = self.coordinator.get_value(
            self._chill_key_at_index(self.entity_description.key, chill_index)
        )

        if value is None:
            return None

        if self.entity_description.device_class == SensorDeviceClass.TIMESTAMP:
            value = dt_util.parse_datetime(value)

        if not isinstance(value, str):
            return value

        key = self.entity_description.key.rsplit(".", 1)[-1]
        if key not in CHILL_SENTENCE_CASE_KEYS:
            return value

        return _format_chill_enum_value(key, value)


class QuattSystemSensor(QuattSensor):
    """Quatt System Sensor class."""

    @property
    def extra_state_attributes(self) -> dict[str, bool]:
        """Expose Quatt feature flags as state attributes."""
        return {
            DUO_HEATPUMP_SYSTEM: self.coordinator.heatpump_2_active(),
            ALL_ELECTRIC_SYSTEM: self.coordinator.all_electric_active(),
            OPENTHERM_SYSTEM: self.coordinator.is_boiler_opentherm(),
        }


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


class QuattChillBinarySensor(QuattBinarySensor):
    """Quatt Chill binary sensor class."""

    @property
    def is_on(self) -> bool:
        """Return true if the Chill binary sensor is on."""
        chill_index = self._current_chill_index()
        if chill_index is None:
            return False
        return self.coordinator.get_value(
            self._chill_key_at_index(self.entity_description.key, chill_index)
        )


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


class QuattSoundSelect(QuattSelect):
    """Select entity for Quatt sound level configuration."""

    async def _perform_api_update(self, option: str) -> bool:
        """Perform paired day/night sound level update."""

        remote_client = self.coordinator.client
        if not isinstance(remote_client, QuattCicRemoteApiClient):
            _LOGGER.error(
                "Cannot update %s: remote client required", self.entity_description.key
            )
            return False

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
            return False

        # Send both values to the API
        settings = {
            "dayMaxSoundLevel": day_level,
            "nightMaxSoundLevel": night_level,
        }

        _LOGGER.debug("Updating CIC sound levels: %s", settings)
        return await remote_client.update_cic_settings(settings)


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


class QuattSettingSwitch(QuattSwitch):
    """Switch entity for Quatt boolean settings."""

    async def _perform_api_update(self, state: bool) -> bool:
        """Perform boolean setting update."""
        remote_client = self.coordinator.client
        if not isinstance(remote_client, QuattCicRemoteApiClient):
            _LOGGER.error(
                "Cannot update %s: remote client required", self.entity_description.key
            )
            return False

        # Convert dot notation to nested object structure
        key_parts = self.entity_description.key.split(".")

        # Build nested dictionary from dot notation
        settings = {}
        current = settings
        for i, part in enumerate(key_parts):
            if i == len(key_parts) - 1:
                # Last part - set the actual value
                current[part] = state
            else:
                # Intermediate part - create nested dict
                current[part] = {}
                current = current[part]

        _LOGGER.debug("Updating CIC setting: %s", settings)
        return await remote_client.update_cic_settings(settings)


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


class QuattHomeBatterySolarCapacityNumber(QuattNumber):
    """Number entity for the home battery installation's ``solarCapacitykWp``.

    The value is a flat scalar on the installation record (not wrapped in
    ``{value,minValue,maxValue,increment}``), so min/max/step come from the
    entity description instead of the coordinator data.
    """

    @property
    def native_value(self) -> float | None:
        """Read the scalar value directly from the coordinator data."""
        return self.coordinator.get_value(self.entity_description.key)

    @property
    def native_min_value(self) -> float:
        """Use the entity description's min value, else HA's default."""
        value = self.entity_description.native_min_value
        return value if value is not None else DEFAULT_MIN_VALUE

    @property
    def native_max_value(self) -> float:
        """Use the entity description's max value, else HA's default."""
        value = self.entity_description.native_max_value
        return value if value is not None else DEFAULT_MAX_VALUE

    @property
    def native_step(self) -> float | None:
        """Use the entity description's step, else HA's default."""
        value = self.entity_description.native_step
        return value if value is not None else DEFAULT_STEP

    async def _perform_api_update(self, value: float) -> bool:
        """Send the PATCH to the home battery installation endpoint."""
        client = self.coordinator.client
        if not isinstance(client, QuattHomeBatteryApiClient):
            _LOGGER.error(
                "Cannot update %s: home battery client required",
                self.entity_description.key,
            )
            return False
        return await client.update_solar_capacity(value)

    async def async_set_native_value(self, value: float) -> None:
        """Set the new value via the home battery coordinator."""
        if not isinstance(self.coordinator, QuattHomeBatteryDataUpdateCoordinator):
            _LOGGER.error(
                "Cannot update %s: home battery coordinator required",
                self.entity_description.key,
            )
            raise NotImplementedError(
                f"Setting {self.entity_description.key} requires a home battery hub"
            )

        try:
            success = await self._perform_api_update(value)
        except Exception as err:
            _LOGGER.exception("Error updating %s", self.entity_description.key)
            raise RuntimeError(
                f"Failed to update {self.entity_description.key}"
            ) from err

        if not success:
            raise RuntimeError(f"Failed to update {self.entity_description.key}")

        await self.coordinator.async_request_refresh()


class QuattSettingNumber(QuattNumber):
    """Number entity for Quatt numeric settings stored as {value, minValue, maxValue, increment}."""

    async def _perform_api_update(self, value: float) -> bool:
        """Perform numeric setting update."""
        remote_client = self.coordinator.client
        if not isinstance(remote_client, QuattCicRemoteApiClient):
            _LOGGER.error(
                "Cannot update %s: remote client required", self.entity_description.key
            )
            return False

        # Preserve integer type when the step is whole-number
        step = self.native_step
        if step is not None and float(step).is_integer() and float(value).is_integer():
            payload_value: int | float = int(value)
        else:
            payload_value = value

        # Convert dot notation to nested object structure ending at ".value"
        key_parts = self.entity_description.key.split(".") + ["value"]

        settings: dict[str, Any] = {}
        current = settings
        for i, part in enumerate(key_parts):
            if i == len(key_parts) - 1:
                current[part] = payload_value
            else:
                current[part] = {}
                current = current[part]

        _LOGGER.debug("Updating CIC setting: %s", settings)
        return await remote_client.update_cic_settings(settings)


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


class QuattChillClimate(QuattEntity, ClimateEntity):
    """Climate entity for Quatt chill devices."""

    _attr_fan_modes = [fan_mode.display_value for fan_mode in QuattChillFanMode]
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.COOL, HVACMode.OFF]
    _attr_name = None
    _attr_precision = PRECISION_TENTHS
    _attr_target_temperature_step = 1.0
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE
    )

    def __init__(
        self,
        device_name: str,
        device_id: str,
        sensor_key: str,
        coordinator: QuattDataUpdateCoordinator,
        entity_description: QuattClimateEntityDescription,
        device_kind: QuattDeviceKind,
    ) -> None:
        """Initialize the chill climate entity."""
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
    def chill_index(self) -> int | None:
        """Return the current Chill list index for this climate entity."""
        return self._current_chill_index()

    def _chill_value(self, key: str) -> Any:
        """Return a value from the current Chill data."""
        chill_index = self.chill_index
        if chill_index is None:
            return None
        return self.coordinator.get_value(f"chills.{chill_index}.{key}")

    def _async_set_chill_values(self, updates: Mapping[str, Any]) -> None:
        """Optimistically update the cached chill values."""
        chill_index = self.chill_index
        if chill_index is None:
            return

        data = deepcopy(self.coordinator.data)
        current_node = data
        if isinstance(current_node, dict) and "result" in current_node:
            current_node = current_node["result"]

        if not isinstance(current_node, dict):
            return

        chills = current_node.get("chills")
        if not isinstance(chills, list) or chill_index >= len(chills):
            return

        chill = chills[chill_index]
        if not isinstance(chill, dict):
            return

        for value_path, value in updates.items():
            node = chill
            parts = value_path.split(".")
            for part in parts[:-1]:
                child = node.setdefault(part, {})
                if not isinstance(child, dict):
                    return
                node = child
            node[parts[-1]] = value

        self.coordinator.async_set_updated_data(data)

    @staticmethod
    def _status_to_hvac_mode(status: Any, source: str) -> HVACMode | None:
        """Convert a Quatt Chill status or mode value to an HVAC mode."""
        if chill_status := QuattChillStatus.from_api_value(status):
            return chill_status.hvac_mode
        if chill_mode := QuattChillMode.from_api_value(status):
            return chill_mode.hvac_mode
        if isinstance(status, str):
            _LOGGER.debug("Unknown Chill %s value: %s", source, status)
        return None

    @property
    def hvac_mode(self) -> HVACMode:
        """Return the current HVAC mode."""
        status = self._chill_value("status")
        if hvac_mode := self._status_to_hvac_mode(status, "status"):
            return hvac_mode

        is_on = self._chill_value("isOn.value")
        if not is_on:
            return HVACMode.OFF

        mode = self._chill_value("mode")
        if hvac_mode := self._status_to_hvac_mode(mode, "mode"):
            return hvac_mode

        return HVACMode.OFF

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self._chill_value("ambientTemperature")

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        hvac_mode = self.hvac_mode
        if hvac_mode == HVACMode.OFF:
            mode = self._chill_value("mode")
            hvac_mode = self._status_to_hvac_mode(mode, "mode")

        if hvac_mode == HVACMode.COOL:
            return self._chill_value("coolingTargetTemperature")
        if hvac_mode == HVACMode.HEAT:
            return self._chill_value("heatingTargetTemperature")
        return None

    @property
    def target_temperature_high(self) -> float | None:
        """Return the maximum target temperature."""
        return self._chill_value("maxTargetTemperature")

    @property
    def target_temperature_low(self) -> float | None:
        """Return the minimum target temperature."""
        return self._chill_value("minTargetTemperature")

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature."""
        min_temp = self._chill_value("minTargetTemperature")
        return float(min_temp) if min_temp is not None else 5.0

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature."""
        max_temp = self._chill_value("maxTargetTemperature")
        return float(max_temp) if max_temp is not None else 40.0

    @property
    def temperature_unit(self) -> str:
        """Return the unit of measurement."""
        return UnitOfTemperature.CELSIUS

    @property
    def fan_mode(self) -> str | None:
        """Return the current fan mode."""
        fan_mode = self._chill_value("fanMode")
        if isinstance(fan_mode, str):
            return _format_chill_enum_value("fanMode", fan_mode)
        return None

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set the HVAC mode."""
        remote_client = self.coordinator.client
        if not isinstance(remote_client, QuattCicRemoteApiClient):
            raise NotImplementedError("HVAC mode setting requires remote API")

        chill_uuid = self._chill_value("uuid")
        if not chill_uuid:
            raise RuntimeError("Cannot find chill UUID")

        if hvac_mode == HVACMode.OFF:
            data = {"type": "SET_ON_OFF", "on": False}
            _LOGGER.debug("Turning off chill %s: %s", chill_uuid, data)
            success = await remote_client.update_chill_action(chill_uuid, data)
            if not success:
                raise RuntimeError(f"Failed to set HVAC mode to {hvac_mode}")

            self._async_set_chill_values(
                {
                    "isOn.value": False,
                    "status": QuattChillStatus.OFF.value,
                }
            )
            return

        if hvac_mode == HVACMode.COOL:
            chill_mode = QuattChillMode.COOLING
            chill_status = QuattChillStatus.COOLING
        elif hvac_mode == HVACMode.HEAT:
            chill_mode = QuattChillMode.HEATING
            chill_status = QuattChillStatus.HEATING
        else:
            raise ValueError(f"Unsupported HVAC mode: {hvac_mode}")

        if self.hvac_mode == HVACMode.OFF:
            data = {"type": "SET_ON_OFF", "on": True}
            _LOGGER.debug("Turning on chill %s: %s", chill_uuid, data)
            success = await remote_client.update_chill_action(chill_uuid, data)
            if not success:
                raise RuntimeError(f"Failed to set HVAC mode to {hvac_mode}")
            self._async_set_chill_values({"isOn.value": True})

        data = {"type": "SET_MODE", "mode": chill_mode.value}
        _LOGGER.debug("Setting HVAC mode for chill %s: %s", chill_uuid, data)
        success = await remote_client.update_chill_action(chill_uuid, data)
        if not success:
            raise RuntimeError(f"Failed to set HVAC mode to {hvac_mode}")

        self._async_set_chill_values(
            {
                "isOn.value": True,
                "mode": chill_mode.value,
                "status": chill_status.value,
            }
        )

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set the fan mode."""
        remote_client = self.coordinator.client
        if not isinstance(remote_client, QuattCicRemoteApiClient):
            raise NotImplementedError("Fan mode setting requires remote API")

        chill_fan_mode = QuattChillFanMode.from_display_value(fan_mode)
        if chill_fan_mode is None:
            raise ValueError(f"Unsupported fan mode: {fan_mode}")

        chill_uuid = self._chill_value("uuid")
        if not chill_uuid:
            raise RuntimeError("Cannot find chill UUID")

        data = {"type": "SET_FAN_MODE", "fanMode": chill_fan_mode.value}
        _LOGGER.debug("Setting fan mode for chill %s: %s", chill_uuid, data)
        success = await remote_client.update_chill_action(chill_uuid, data)
        if success:
            self._async_set_chill_values({"fanMode": chill_fan_mode.value})
        else:
            raise RuntimeError(f"Failed to set fan mode to {fan_mode}")

    async def async_set_temperature(self, **kwargs) -> None:
        """Set the target temperature."""
        remote_client = self.coordinator.client
        if not isinstance(remote_client, QuattCicRemoteApiClient):
            raise NotImplementedError("Temperature setting requires remote API")

        temperature = kwargs.get("temperature")
        if temperature is None:
            return
        temperature = int(round(temperature))

        chill_uuid = self._chill_value("uuid")
        if not chill_uuid:
            raise RuntimeError("Cannot find chill UUID")

        hvac_mode = self.hvac_mode
        if hvac_mode == HVACMode.OFF:
            mode = self._chill_value("mode")
            hvac_mode = self._status_to_hvac_mode(mode, "mode")

        if hvac_mode == HVACMode.COOL:
            data = {
                "type": "SET_COOLING_TARGET_TEMPERATURE",
                "coolingTargetTemperature": temperature,
            }
        elif hvac_mode == HVACMode.HEAT:
            data = {
                "type": "SET_HEATING_TARGET_TEMPERATURE",
                "heatingTargetTemperature": temperature,
            }
        else:
            raise RuntimeError(f"Unknown chill mode: {hvac_mode}")

        _LOGGER.debug("Setting target temperature for chill %s: %s", chill_uuid, data)
        success = await remote_client.update_chill_action(chill_uuid, data)
        if success:
            self._async_set_chill_values(
                {
                    "coolingTargetTemperature"
                    if hvac_mode == HVACMode.COOL
                    else "heatingTargetTemperature": temperature
                }
            )
        else:
            raise RuntimeError(f"Failed to set temperature to {temperature}")
