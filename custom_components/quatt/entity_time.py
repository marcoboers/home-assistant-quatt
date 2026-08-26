"""Time entity implementations for Quatt."""

from __future__ import annotations

from datetime import time
import logging

from homeassistant.exceptions import ServiceValidationError

from .api_remote_cic import QuattCicRemoteApiClient
from .entity import QuattTime

_LOGGER = logging.getLogger(__name__)

# The Quatt nightWindow endpoint only accepts times on 30-minute boundaries.
NIGHT_WINDOW_MINUTE_STEP = 30

NIGHT_WINDOW_START_KEY = "soundNightTimeStart"
NIGHT_WINDOW_END_KEY = "soundNightTimeEnd"


class QuattNightWindowTime(QuattTime):
    """Time entity for one boundary (start or end) of the CIC night window.

    The CIC data exposes the boundaries as separate hour/minute fields
    (``soundNightTimeStartHour``, ``soundNightTimeStartMin``, ...), while the
    nightWindow endpoint updates both boundaries in a single request.
    """

    @property
    def native_value(self) -> time | None:
        """Combine the hour/minute coordinator values into a time."""
        hour = self.coordinator.get_value(f"{self.entity_description.key}Hour")
        if hour is None:
            return None
        minute = self.coordinator.get_value(f"{self.entity_description.key}Min")
        return time(hour=int(hour), minute=int(minute or 0))

    async def async_set_value(self, value: time) -> None:
        """Validate the 30-minute step before performing the update."""
        if value.minute % NIGHT_WINDOW_MINUTE_STEP or value.second or value.microsecond:
            raise ServiceValidationError(
                f"Night window times must be in {NIGHT_WINDOW_MINUTE_STEP}-minute "
                "steps (e.g. 21:00 or 21:30)"
            )
        await super().async_set_value(value)

    async def _perform_api_update(self, value: time) -> bool:
        """Send both night window boundaries to the nightWindow endpoint."""
        remote_client = self.coordinator.client
        if not isinstance(remote_client, QuattCicRemoteApiClient):
            _LOGGER.error(
                "Cannot update %s: remote client required", self.entity_description.key
            )
            return False

        start_hour = self.coordinator.get_value(f"{NIGHT_WINDOW_START_KEY}Hour")
        start_minute = self.coordinator.get_value(f"{NIGHT_WINDOW_START_KEY}Min")
        end_hour = self.coordinator.get_value(f"{NIGHT_WINDOW_END_KEY}Hour")
        end_minute = self.coordinator.get_value(f"{NIGHT_WINDOW_END_KEY}Min")

        if self.entity_description.key == NIGHT_WINDOW_START_KEY:
            start_hour, start_minute = value.hour, value.minute
        else:
            end_hour, end_minute = value.hour, value.minute

        if None in (start_hour, start_minute, end_hour, end_minute):
            _LOGGER.error(
                "Cannot update night window: missing current values "
                "(start=%s:%s, end=%s:%s)",
                start_hour,
                start_minute,
                end_hour,
                end_minute,
            )
            return False

        return await remote_client.update_night_window(
            int(start_hour), int(start_minute), int(end_hour), int(end_minute)
        )
