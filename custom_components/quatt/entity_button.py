"""Button entity implementations for Quatt."""

from __future__ import annotations

import logging

from .api_remote_cic import QuattCicRemoteApiClient
from .entity import QuattButton

_LOGGER = logging.getLogger(__name__)


class QuattNightWindowResetButton(QuattButton):
    """Button that resets the CIC night window to the Quatt defaults."""

    async def _perform_api_update(self) -> bool:
        """Send null values to the nightWindow endpoint to reset it."""
        remote_client = self.coordinator.client
        if not isinstance(remote_client, QuattCicRemoteApiClient):
            _LOGGER.error(
                "Cannot update %s: remote client required", self.entity_description.key
            )
            return False

        return await remote_client.update_night_window(None, None, None, None)
