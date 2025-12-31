"""Base DataUpdateCoordinator for Quatt integration."""

from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import QuattApiClient, QuattApiClientAuthenticationError, QuattApiClientError
from .const import CONF_POWER_SENSOR, DOMAIN, LOGGER


class QuattDataUpdateCoordinator(DataUpdateCoordinator, ABC):
    """Abstract base class for Quatt data update coordinators."""

    def __init__(
        self,
        hass: HomeAssistant,
        update_interval: timedelta,
        client: QuattApiClient,
    ) -> None:
        """Initialize."""
        self.client = client
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

        self._power_sensor_id: str = (
            self.config_entry.options.get(CONF_POWER_SENSOR, "")
            if (self.config_entry is not None)
            and (len(self.config_entry.options.get(CONF_POWER_SENSOR, "")) > 6)
            else None
        )

    async def _async_update_data(self):
        """Update data via the client.

        Returns: The data fetched from the API
        """
        try:
            return await self.client.async_get_data()
        except QuattApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except QuattApiClientError as exception:
            raise UpdateFailed(exception) from exception

    @abstractmethod
    def get_value(self, value_path: str, default: Any | None = None) -> Any:
        """Get a value from the coordinator data using dot notation.

        Args: value_path: The path to the value using dot notation (e.g., "hp1.temperatureOutside")
              default: The default value to return if the path is not found

        Returns: The value at the specified path, or the default value if not found
        """

        raise NotImplementedError

    @abstractmethod
    def heatpump_1_active(self) -> bool:
        """Check if heatpump 1 is active.

        Returns: True if heatpump 1 is active, False otherwise
        """

        raise NotImplementedError

    @abstractmethod
    def heatpump_2_active(self) -> bool:
        """Check if heatpump 2 is active.

        Returns: True if heatpump 2 is active, False otherwise
        """

        raise NotImplementedError

    @abstractmethod
    def all_electric_active(self) -> bool:
        """Check if all-electric mode is active.

        Returns: True if all-electric mode is active, False otherwise
        """

        raise NotImplementedError

    @abstractmethod
    def is_boiler_opentherm(self) -> bool:
        """Check if boiler is opentherm.

        Returns: True if boiler mode is opentherm, False otherwise
        """

        raise NotImplementedError
