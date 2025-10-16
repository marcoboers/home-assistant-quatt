"""Base coordinator for Quatt integration."""

from abc import ABC, abstractmethod
from typing import Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator


class QuattDataUpdateCoordinator(DataUpdateCoordinator, ABC):
    """Abstract base class for Quatt data update coordinators."""

    @abstractmethod
    def get_value(self, value_path: str, default: Any | None = None) -> Any:
        """Get a value from the coordinator data using dot notation.

        Args: value_path: The path to the value using dot notation (e.g., "hp1.temperatureOutside")
              default: The default value to return if the path is not found

        Returns: The value at the specified path, or the default value if not found
        """

        return

    @abstractmethod
    def heatpump_1_active(self) -> bool:
        """Check if heatpump 1 is active.

        Returns: True if heatpump 1 is active, False otherwise
        """

        return

    @abstractmethod
    def heatpump_2_active(self) -> bool:
        """Check if heatpump 2 is active.

        Returns: True if heatpump 2 is active, False otherwise
        """

        return

    @abstractmethod
    def all_electric_active(self) -> bool:
        """Check if all-electric mode is active.

        Returns: True if all-electric mode is active, False otherwise
        """

        return

    @abstractmethod
    def is_boiler_opentherm(self) -> bool:
        """Check if boiler is opentherm.

        Returns: True if boiler mode is opentherm, False otherwise
        """

        return

