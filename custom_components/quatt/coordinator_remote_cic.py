"""Remote (mobile API) DataUpdateCoordinator for the Quatt CIC (heatpump)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
import homeassistant.util.dt as dt_util

from .api import QuattApiClient
from .const import (
    BOOST_ACTIVE_STATUSES,
    BOOST_FAST_SCAN_INTERVAL,
    BOOST_FAST_SCAN_TAIL,
    LOGGER,
)
from .coordinator import QuattCicDataUpdateCoordinator


class QuattCicRemoteDataUpdateCoordinator(QuattCicDataUpdateCoordinator):
    """Class to manage fetching CIC data from the mobile (remote) API."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        update_interval: timedelta,
        client: QuattApiClient,
    ) -> None:
        """Initialize the remote CIC coordinator."""
        super().__init__(hass=hass, update_interval=update_interval, client=client)
        self._configured_update_interval = update_interval
        self._boost_fast_scan_until: datetime | None = None

    async def _async_update_data(self):
        """Fetch data and adapt the poll interval to the boost state."""
        data = await super()._async_update_data()
        self.update_interval = self._next_update_interval(data)
        return data

    def _next_update_interval(self, data: Any) -> timedelta:
        """Return the poll interval matching the current boost state.

        While a boost is starting/active we poll fast so its progress shows up
        quickly, and we keep polling fast until BOOST_FAST_SCAN_TAIL minutes
        after the boost was last seen active, so the wind-down after a
        completion or cancel is picked up too. Outside a boost the configured
        scan interval applies; a boost started from the Quatt app is then
        noticed on the next regular poll, which switches to fast polling.
        """
        boost = data.get("allElectricBoost") if isinstance(data, dict) else None
        status = boost.get("status") if isinstance(boost, dict) else None

        now = dt_util.utcnow()
        if isinstance(status, str) and status.upper() in BOOST_ACTIVE_STATUSES:
            self._boost_fast_scan_until = now + timedelta(minutes=BOOST_FAST_SCAN_TAIL)
            return timedelta(seconds=BOOST_FAST_SCAN_INTERVAL)

        if self._boost_fast_scan_until is not None:
            if now < self._boost_fast_scan_until:
                return timedelta(seconds=BOOST_FAST_SCAN_INTERVAL)
            LOGGER.debug("Boost fast polling ended, back to configured scan interval")
            self._boost_fast_scan_until = None

        return self._configured_update_interval

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
