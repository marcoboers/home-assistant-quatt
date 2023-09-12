"""DataUpdateCoordinator for quatt."""
from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
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
from .const import CONF_POWER_SENSOR, DOMAIN, LOGGER


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

        self._power_sensor_id: str = (
            self.config_entry.data.get(CONF_POWER_SENSOR)
            if len(self.config_entry.data.get(CONF_POWER_SENSOR, "")) > 6
            else None
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

    def boilerOpenTherm(self):
        """Check if boiler is connected to CIC ofer OpenTherm."""
        LOGGER.debug(self.getValue("boiler.otFbChModeActive"))
        return self.getValue("boiler.otFbChModeActive") is not None

    def electicalPower(self):
        """Get heatpump power from sensor."""
        if self._power_sensor_id is None:
            return None
        LOGGER.debug("electicalPower %s", self.hass.states.get(self._power_sensor_id))
        if self.hass.states.get(self._power_sensor_id) is None:
            return None
        if self.hass.states.get(self._power_sensor_id).state not in [
            STATE_UNAVAILABLE,
            STATE_UNKNOWN,
        ]:
            return self.hass.states.get(self._power_sensor_id).state

    def computedWaterDelta(self):
        """Compute waterDelta."""
        temperatureWaterOut = self.getValue("hp1.temperatureWaterOut")
        temperatureWaterIn = self.getValue("hp1.temperatureWaterIn")
        LOGGER.debug("computedWaterDelta.temperatureWaterOut %s", temperatureWaterOut)
        LOGGER.debug("computedWaterDelta.temperatureWaterIn %s", temperatureWaterIn)
        if temperatureWaterOut is None or temperatureWaterIn is None:
            return None
        if temperatureWaterOut < temperatureWaterIn:
            return None
        return temperatureWaterOut - temperatureWaterIn

    def computedHeatPower(self):
        """Compute heatPower."""
        computedWaterDelta = self.computedWaterDelta()
        flowRate = self.getValue("flowMeter.flowRate")
        LOGGER.debug("computedHeatPower.computedWaterDelta %s", computedWaterDelta)
        LOGGER.debug("computedHeatPower.flowRate %s", flowRate)
        if computedWaterDelta is None or flowRate is None:
            return None
        return round(
            computedWaterDelta * flowRate * 1.137888,
            2,
        )

    def computedCop(self):
        """Compute COP."""
        electicalPower = self.electicalPower()
        computedHeatPower = self.computedHeatPower()
        LOGGER.debug("computedCop.electicalPower %s", electicalPower)
        LOGGER.debug("computedCop.computedHeatPower %s", computedHeatPower)
        if electicalPower is None or computedHeatPower is None:
            return None
        if electicalPower == 0:
            return None
        return round(computedHeatPower / electicalPower, 2)

    def computedSupervisoryControlMode(self):
        """Map the numeric supervisoryControlMode to a textual status."""
        state = self.getValue("qc.supervisoryControlMode")
        mapping = {
            0: "Standby",
            1: "Standby - heating",
            2: "Heating - heatpump only",
            3: "Heating - heatpump + boiler",
            4: "Heating - boiler only",
            96: "Anti-freeze protection - boiler on",
            97: "Anti-freeze protection - boiler pre-pump",
            98: "Anti-freeze protection - water circulation",
            99: "Fault - circulation pump on",
        }

        if state in mapping:
            return mapping[state]
        elif state >= 100:
            return "Commissioning modes"
        else:
            return None

    def getValue(self, value_path: str):
        """Check retrieve a value by dot notation."""
        keys = value_path.split(".")
        value = self.data
        for key in keys:
            if value is None:
                return None

            if key.isdigit():
                key = int(key)
                if not isinstance(value, list) or len(value) < key:
                    LOGGER.warning(
                        "Could not find %d of %s",
                        key,
                        value_path,
                    )
                    LOGGER.debug(" in %s %s", value, type(value))
                    return None

            elif len(key) > 8 and key[0:8] == "computed" and key in dir(self):
                method = getattr(self, key)
                return method()
            elif key not in value:
                LOGGER.warning("Could not find %s of %s", key, value_path)
                LOGGER.debug("in %s", value)
                return None
            value = value[key]

        return value
