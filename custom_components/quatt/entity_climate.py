"""Climate entity implementations for Quatt."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import PRECISION_TENTHS, UnitOfTemperature

from .api_remote_cic import QuattCicRemoteApiClient
from .const import QuattDeviceKind
from .coordinator import QuattDataUpdateCoordinator
from .entity import (
    QuattChillFanMode,
    QuattChillMode,
    QuattChillStatus,
    QuattClimateEntityDescription,
    QuattEntity,
    _format_chill_enum_value,
)

_LOGGER = logging.getLogger(__name__)


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

    def set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Implement required base class method but do not use it."""
        raise NotImplementedError("Use async_set_hvac_mode instead")

    def set_fan_mode(self, fan_mode: str) -> None:
        """Implement required base class method but do not use it."""
        raise NotImplementedError("Use async_set_fan_mode instead")

    def set_temperature(self, **kwargs) -> None:
        """Implement required base class method but do not use it."""
        raise NotImplementedError("Use async_set_temperature instead")

    def set_humidity(self, humidity: int) -> None:
        """Implement unsupported base class method."""
        raise NotImplementedError

    def set_preset_mode(self, preset_mode: str) -> None:
        """Implement unsupported base class method."""
        raise NotImplementedError

    def set_swing_horizontal_mode(self, swing_horizontal_mode: str) -> None:
        """Implement unsupported base class method."""
        raise NotImplementedError

    def set_swing_mode(self, swing_mode: str) -> None:
        """Implement unsupported base class method."""
        raise NotImplementedError

    def turn_on(self) -> None:
        """Implement required base class method but do not use it."""
        raise NotImplementedError("Use async_set_hvac_mode instead")

    def turn_off(self) -> None:
        """Implement required base class method but do not use it."""
        raise NotImplementedError("Use async_set_hvac_mode instead")

    def toggle(self) -> None:
        """Implement required base class method but do not use it."""
        raise NotImplementedError("Use async_set_hvac_mode instead")

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
