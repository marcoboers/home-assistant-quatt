"""Sensor entity implementations for Quatt."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.helpers.typing import StateType
import homeassistant.util.dt as dt_util

from .const import ALL_ELECTRIC_SYSTEM, DUO_HEATPUMP_SYSTEM, OPENTHERM_SYSTEM
from .entity import (
    CHILL_SENTENCE_CASE_KEYS,
    QuattSensor,
    _format_chill_enum_value,
)


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
