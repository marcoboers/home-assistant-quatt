"""Remote DataUpdateCoordinator for Quatt integration."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry

from .const import LOGGER
from .coordinator import QuattDataUpdateCoordinator


class QuattRemoteDataUpdateCoordinator(QuattDataUpdateCoordinator):
    """Class to manage fetching data from the Remote API."""

    config_entry: ConfigEntry

    async def _async_update_data(self):
        """Update data via the client, including insights data."""
        # Get the main CIC data
        data = await super()._async_update_data()

        # If we have data and this is a remote client, fetch insights
        if data and hasattr(self.client, "get_insights"):
            insights_data = await self.client.get_insights()
            if insights_data:
                # Add insights data to the coordinator data
                if "result" in data:
                    data["result"]["insights"] = insights_data
                else:
                    data["insights"] = insights_data
                LOGGER.debug("Insights data fetched and added to coordinator data")
            else:
                LOGGER.debug("No insights data available")

        return data

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
        return self.get_value("allEStatus") or False

    def is_boiler_opentherm(self) -> bool:
        """Check if the boiler is connected."""
        # Returning whether the boiler is connected is not sufficient, as it may be
        # connected but not OpenTherm. The sensors using this field should be only
        # used on the local API when OpenTherm is present.
        return self.get_value("isBoilerConnected") or False
