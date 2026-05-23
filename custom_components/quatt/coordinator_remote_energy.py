"""DataUpdateCoordinator for the Quatt Energy (mijnenergie) hub."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry

from .const import LOGGER
from .coordinator import QuattDataUpdateCoordinator


class QuattEnergyDataUpdateCoordinator(QuattDataUpdateCoordinator):
    """Coordinator for refreshing the Quatt Energy web session.

    Step 1 keeps the laravel session alive and exposes the EAN + rotating
    auth identifiers. Step 2 will fold in the usage/savings endpoints.
    """

    config_entry: ConfigEntry

    def get_value(self, value_path: str, default: Any | None = None) -> Any:
        """Retrieve a value by dot notation from the energy response."""
        parts = value_path.split(".")
        current_node = self.data

        for part in parts:
            if current_node is None:
                return default
            if isinstance(current_node, dict) and part in current_node:
                current_node = current_node[part]
            else:
                LOGGER.debug("Could not find %s of %s", part, value_path)
                return default

        return current_node
