"""Select entity implementations for Quatt."""

from __future__ import annotations

import logging

from .api_remote_cic import QuattCicRemoteApiClient
from .entity import QuattSelect

_LOGGER = logging.getLogger(__name__)


class QuattSoundSelect(QuattSelect):
    """Select entity for Quatt sound level configuration."""

    def select_option(self, option: str) -> None:
        """Implement required base class method but do not use it."""
        raise NotImplementedError("Use async_select_option instead")

    async def _perform_api_update(self, option: str) -> bool:
        """Perform paired day/night sound level update."""
        remote_client = self.coordinator.client
        if not isinstance(remote_client, QuattCicRemoteApiClient):
            _LOGGER.error(
                "Cannot update %s: remote client required", self.entity_description.key
            )
            return False

        day_level = self.coordinator.get_value("dayMaxSoundLevel")
        night_level = self.coordinator.get_value("nightMaxSoundLevel")

        if self.entity_description.key == "dayMaxSoundLevel":
            day_level = option
        elif self.entity_description.key == "nightMaxSoundLevel":
            night_level = option

        if not day_level or not night_level:
            _LOGGER.error(
                "Cannot update sound level: missing current values (day=%s, night=%s)",
                day_level,
                night_level,
            )
            return False

        settings = {
            "dayMaxSoundLevel": day_level,
            "nightMaxSoundLevel": night_level,
        }

        _LOGGER.debug("Updating CIC sound levels: %s", settings)
        return await remote_client.update_cic_settings(settings)
