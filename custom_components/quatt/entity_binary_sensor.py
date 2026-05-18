"""Binary sensor entity implementations for Quatt."""

from __future__ import annotations

from .entity import QuattBinarySensor


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
