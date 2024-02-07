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

    def computedWaterDelta(self, parent_key: str = None):
        """Compute waterDelta."""
        if parent_key is None:
            parent_key = ""
            temperatureWaterOut = self.getValue("hp2.temperatureWaterOut")
            temperatureWaterIn = self.getValue("hp1.temperatureWaterIn")
        else:
            temperatureWaterOut = self.getValue(parent_key + ".temperatureWaterOut")
            temperatureWaterIn = self.getValue(parent_key + ".temperatureWaterIn")

        LOGGER.debug("%s.computedWaterDelta.temperatureWaterOut %s", parent_key, temperatureWaterOut)
        LOGGER.debug("%s.computedWaterDelta.temperatureWaterIn %s", parent_key, temperatureWaterIn)

        if temperatureWaterOut is None or temperatureWaterIn is None:
            return None

        return round(temperatureWaterOut - temperatureWaterIn, 2)

    def computedHeatPower(self, parent_key: str = None):
        """Compute heatPower."""
        computedWaterDelta = self.computedWaterDelta()
        flowRate = self.getValue("qc.flowRateFiltered")

        LOGGER.debug("computedHeatPower.computedWaterDelta %s", computedWaterDelta)
        LOGGER.debug("computedHeatPower.flowRate %s", flowRate)

        if computedWaterDelta is None or flowRate is None:
            return None

        return round(
            computedWaterDelta * flowRate * 1.137888,
            2,
        )

    def computedPowerInput(self, parent_key: str = None):
        """Compute total powerInput."""
        powerInputHp1 = self.getValue("hp1.powerInput", 0)
        powerInputHp2 = self.getValue("hp2.powerInput", 0)

        return float(powerInputHp1) + float(powerInputHp2)

    def computedPower(self, parent_key: str = None):
        """Compute total powerInput."""
        powerHp1 = self.getValue("hp1.power", 0)
        powerHp2 = self.getValue("hp2.power", 0)

        return float(powerHp1) + float(powerHp2)

    def computedCop(self, parent_key: str = None):
        """Compute COP."""
        electicalPower = self.electicalPower()
        computedHeatPower = self.computedHeatPower()

        LOGGER.debug("computedCop.electicalPower %s", electicalPower)
        LOGGER.debug("computedCop.computedHeatPower %s", computedHeatPower)

        if electicalPower is None or computedHeatPower is None:
            return None

        computedHeatPower = float(computedHeatPower)
        if computedHeatPower == 0:
            return None

        electicalPower = float(electicalPower)
        if electicalPower == 0:
            return None

        return round(computedHeatPower / electicalPower, 2)

    def computedQuattCop(self, parent_key: str = None):
        """Compute Quatt COP."""
        if parent_key is None:
            parent_key = ""
            powerInput = self.getValue("hp1.powerInput", 0) + self.getValue("hp2.powerInput", 0)
            powerOutput = self.getValue("hp1.power", 0) + self.getValue("hp2.power", 0)
        else:
            powerInput = self.getValue(parent_key + ".powerInput")
            powerOutput = self.getValue(parent_key + ".power")

        LOGGER.debug("%s.computedQuattCop.powerInput %s", parent_key, powerInput)
        LOGGER.debug("%s.computedQuattCop.powerOutput %s", parent_key, powerOutput)

        if powerInput is None or powerOutput is None:
            return None

        powerOutput = float(powerOutput)
        if powerOutput == 0:
            return None

        powerInput = float(powerInput)
        if powerInput == 0:
            return None

        return round(powerOutput / powerInput, 2)

    def computedDefrost(self, parent_key: str = None):
        """Compute Quatt Defrost State."""
        if parent_key is None:
            return None
        else:
            powerInput = self.getValue(parent_key + ".powerInput")
            powerOutput = self.getValue(parent_key + ".power")

        LOGGER.debug("%s.computedDefrost.powerInput %s", parent_key, powerInput)
        LOGGER.debug("%s.computedDefrost.powerOutput %s", parent_key, powerOutput)

        if powerInput is None or powerOutput is None:
            return None

        powerOutput = float(powerOutput)
        if powerOutput == 0:
            return None

        powerInput = float(powerInput)
        if powerInput == 0:
            return None

        return powerOutput < -100 and powerInput > 100

    def computedSupervisoryControlMode(self, parent_key: str = None):
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

    def getValue(self, value_path: str, default: float = None):
        """Check retrieve a value by dot notation."""
        keys = value_path.split(".")
        value = self.data
        parent_key = None
        for key in keys:
            if value is None:
                return default

            if key.isdigit():
                key = int(key)
                if not isinstance(value, list) or len(value) < key:
                    LOGGER.warning(
                        "Could not find %d of %s",
                        key,
                        value_path,
                    )
                    LOGGER.debug(" in %s %s", value, type(value))
                    return default

            elif len(key) > 8 and key[0:8] == "computed" and key in dir(self):
                method = getattr(self, key)
                return method(parent_key)
            elif key not in value:
                LOGGER.warning("Could not find %s of %s", key, value_path)
                LOGGER.debug("in %s", value)
                return default
            value = value[key]
            parent_key = key

        return value
