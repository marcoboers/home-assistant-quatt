"""Number entity implementations for Quatt."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import (
    DEFAULT_MAX_VALUE,
    DEFAULT_MIN_VALUE,
    DEFAULT_STEP,
)

from .api_remote_cic import QuattCicRemoteApiClient
from .api_remote_home_battery import QuattHomeBatteryApiClient
from .coordinator_home_battery import QuattHomeBatteryDataUpdateCoordinator
from .entity import QuattNumber

_LOGGER = logging.getLogger(__name__)


class QuattHomeBatterySolarCapacityNumber(QuattNumber):
    """Number entity for the home battery installation's ``solarCapacitykWp``."""

    @property
    def native_value(self) -> float | None:
        """Read the scalar value directly from the coordinator data."""
        return self.coordinator.get_value(self.entity_description.raw_value_key)

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

    def set_native_value(self, value: float) -> None:
        """Implement required base class method but do not use it."""
        raise NotImplementedError("Use async_set_native_value instead")

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

    def set_native_value(self, value: float) -> None:
        """Implement required base class method but do not use it."""
        raise NotImplementedError("Use async_set_native_value instead")

    async def _perform_api_update(self, value: float) -> bool:
        """Perform numeric setting update."""
        remote_client = self.coordinator.client
        if not isinstance(remote_client, QuattCicRemoteApiClient):
            _LOGGER.error(
                "Cannot update %s: remote client required", self.entity_description.key
            )
            return False

        step = self.native_step
        if step is not None and float(step).is_integer() and float(value).is_integer():
            payload_value: int | float = int(value)
        else:
            payload_value = value

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
