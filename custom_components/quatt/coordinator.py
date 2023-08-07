"""DataUpdateCoordinator for quatt."""
from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.exceptions import ConfigEntryAuthFailed

from .api import (
    QuattApiClient,
    QuattApiClientAuthenticationError,
    QuattApiClientError,
)
from .const import DOMAIN, LOGGER


# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
class QuattDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        client: QuattApiClient,
    ) -> None:
        """Initialize."""
        self.client = client
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=10),
        )

    async def _async_update_data(self):
        """Update data via library."""
        try:
            return await self.client.async_get_data()
        except QuattApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except QuattApiClientError as exception:
            raise UpdateFailed(exception) from exception

    def heatpump1Active(self):
        """Check if heatpump 1 is active."""
        LOGGER.debug(self.getValue("hp1"))
        return self.getValue("hp1") is not None

    def heatpump2Active(self):
        """Check if heatpump 2 is active."""
        LOGGER.debug(self.getValue("hp2"))
        return self.getValue("hp2") is not None

    def getValue(self, value_path: str):
        """Check retrieve a value by dot notation."""
        keys = value_path.split(".")
        value = self.data
        for key in keys:
            if value is None:
                return None

            if key.isdigit():
                key = int(key)
                if type(value) is not list or len(value) < key:
                    LOGGER.warning(
                        "Could not find %d of %s",
                        key,
                        value_path,
                    )
                    LOGGER.debug(" in %s %s", value, type(value))
                    return None

            elif key not in value:
                LOGGER.warning("Could not find %s of %s", key, value_path)
                LOGGER.debug("in %s", value)
                return None
            value = value[key]

        return value
