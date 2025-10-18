"""DataUpdateCoordinator for quatt remote API."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from .api import (
    QuattApiClientAuthenticationError,
    QuattApiClientError,
    QuattRemoteApiClient,
)
from .const import DOMAIN, LOGGER
from .coordinator import QuattDataUpdateCoordinator


class QuattRemoteDataUpdateCoordinator(QuattDataUpdateCoordinator):
    """Class to manage fetching data from the Remote API."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        update_interval: int,
        client: QuattRemoteApiClient,
    ) -> None:
        """Initialize."""
        self.client = client
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )

    async def _async_update_data(self):
        """Update data via library."""
        try:
            return await self.client.async_get_data()
        except QuattApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except QuattApiClientError as exception:
            raise UpdateFailed(exception) from exception

    def get_value(self, value_path: str, default: Any | None = None) -> Any:
        """Retrieve a value by dot notation from the remote API response.

        Note: Remote API has a different structure with result.* prefix.
        """
        parts = value_path.split(".")
        current_node = self.data

        # Remote API response is wrapped in meta/result structure
        if current_node and "result" in current_node:
            current_node = current_node["result"]

        for part in parts:
            # Could not find the value, return default
            if current_node is None:
                return default

            # Dict key access
            if isinstance(current_node, dict) and part in current_node:
                current_node = current_node[part]
            # List index access for heatPumps array
            elif isinstance(current_node, list):
                try:
                    index = int(part)
                    current_node = current_node[index]
                except (ValueError, IndexError):
                    LOGGER.warning("Could not find index %s in list", part)
                    return default
            # Missing key
            else:
                LOGGER.debug("Could not find %s of %s", part, value_path)
                return default

        return current_node

    def heatpump_count(self) -> int:
        """Get the number of heat pumps."""
        heat_pumps = self.get_value("heatPumps", [])
        return len(heat_pumps) if isinstance(heat_pumps, list) else 0

    def heatpump_1_active(self) -> bool:
        """Check if heatpump 1 is active."""
        return self.heatpump_count() >= 1

    def heatpump_2_active(self) -> bool:
        """Check if heatpump 2 is active."""
        return self.heatpump_count() >= 2

    def all_electric_active(self) -> bool:
        """Check if it is an all electric installation."""
        return self.get_value("allEStatus") is not None

    def is_boiler_opentherm(self) -> bool:
        """Check if the boiler is connected."""
        return self.get_value("isBoilerConnected") is not None
