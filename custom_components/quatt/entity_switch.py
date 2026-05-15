"""Switch entity implementations for Quatt."""

from __future__ import annotations

import logging

from .api_remote_cic import QuattCicRemoteApiClient
from .entity import QuattSwitch

_LOGGER = logging.getLogger(__name__)


class QuattSettingSwitch(QuattSwitch):
    """Switch entity for Quatt boolean settings."""

    def turn_on(self, **kwargs) -> None:
        """Implement required base class method but do not use it."""
        raise NotImplementedError("Use async_turn_on instead")

    def turn_off(self, **kwargs) -> None:
        """Implement required base class method but do not use it."""
        raise NotImplementedError("Use async_turn_off instead")

    async def _perform_api_update(self, state: bool) -> bool:
        """Perform boolean setting update."""
        remote_client = self.coordinator.client
        if not isinstance(remote_client, QuattCicRemoteApiClient):
            _LOGGER.error(
                "Cannot update %s: remote client required", self.entity_description.key
            )
            return False

        key_parts = self.entity_description.key.split(".")
        settings = {}
        current = settings
        for i, part in enumerate(key_parts):
            if i == len(key_parts) - 1:
                current[part] = state
            else:
                current[part] = {}
                current = current[part]

        _LOGGER.debug("Updating CIC setting: %s", settings)
        return await remote_client.update_cic_settings(settings)
