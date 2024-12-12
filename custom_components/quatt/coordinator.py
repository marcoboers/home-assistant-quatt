"""DataUpdateCoordinator for quatt."""

from __future__ import annotations

from datetime import timedelta
import math

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import QuattApiClient, QuattApiClientAuthenticationError, QuattApiClientError
from .const import CONF_POWER_SENSOR, CONVERSION_FACTORS, DOMAIN, LOGGER


# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
class QuattDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        update_interval: int,
        client: QuattApiClient,
    ) -> None:
        """Initialize."""
        self.client = client
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )

        self._power_sensor_id: str = (
            self.config_entry.options.get(CONF_POWER_SENSOR, "")
            if (self.config_entry is not None)
            and (len(self.config_entry.options.get(CONF_POWER_SENSOR, "")) > 6)
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

    def getConversionFactor(self, temperature: float):
        """Get the conversion factor for the nearest temperature."""
        nearestTemperature = min(
            CONVERSION_FACTORS.keys(), key=lambda t: abs(t - temperature)
        )
        return CONVERSION_FACTORS[nearestTemperature]

    def electricalPower(self):
        """Get heatpump power from sensor."""
        if self._power_sensor_id is None:
            return None
        LOGGER.debug("electricalPower %s", self.hass.states.get(self._power_sensor_id))
        if self.hass.states.get(self._power_sensor_id) is None:
            return None
        if self.hass.states.get(self._power_sensor_id).state not in [
            STATE_UNAVAILABLE,
            STATE_UNKNOWN,
        ]:
            return self.hass.states.get(self._power_sensor_id).state
        return None

    def computedWaterDelta(self, parent_key: str | None = None):
        """Compute waterDelta."""
        if parent_key is None:
            parent_key = ""
            temperatureWaterOut = self.getValue("hp2.temperatureWaterOut")
            temperatureWaterIn = self.getValue("hp1.temperatureWaterIn")
        else:
            temperatureWaterOut = self.getValue(parent_key + ".temperatureWaterOut")
            temperatureWaterIn = self.getValue(parent_key + ".temperatureWaterIn")

        LOGGER.debug(
            "%s.computedWaterDelta.temperatureWaterOut %s",
            parent_key,
            temperatureWaterOut,
        )
        LOGGER.debug(
            "%s.computedWaterDelta.temperatureWaterIn %s",
            parent_key,
            temperatureWaterIn,
        )

        if temperatureWaterOut is None or temperatureWaterIn is None:
            return None

        return round(temperatureWaterOut - temperatureWaterIn, 2)

    def computedHeatPower(self, parent_key: str | None = None):
        """Compute heatPower."""

        # Retrieve the supervisory control mode state first
        state = self.getValue("qc.supervisoryControlMode")
        LOGGER.debug("computedBoilerHeatPower.supervisoryControlMode: %s", state)

        # If the state is not valid or the heatpump is not active, no need to proceed
        if state is None:
            return None
        if state not in [2, 3]:
            return 0.0

        if self.heatpump2Active():
            computedWaterDelta = self.computedWaterDelta(None)
            temperatureWaterOut = self.getValue("hp2.temperatureWaterOut")
        else:
            computedWaterDelta = self.computedWaterDelta("hp1")
            temperatureWaterOut = self.getValue("hp1.temperatureWaterOut")
        flowRate = self.getValue("qc.flowRateFiltered")

        LOGGER.debug("computedHeatPower.computedWaterDelta %s", computedWaterDelta)
        LOGGER.debug("computedHeatPower.flowRate %s", flowRate)
        LOGGER.debug("computedHeatPower.temperatureWaterOut %s", temperatureWaterOut)

        if (
            computedWaterDelta is None
            or flowRate is None
            or temperatureWaterOut is None
        ):
            return None

        value = round(
            computedWaterDelta
            * flowRate
            * self.getConversionFactor(temperatureWaterOut),
            2,
        )

        # Prevent any negative numbers
        return max(value, 0.00)

    def computedBoilerHeatPower(self, parent_key: str | None = None) -> float | None:
        """Compute the boiler's added heat power."""

        # Retrieve the supervisory control mode state first
        state = self.getValue("qc.supervisoryControlMode")
        LOGGER.debug("computedBoilerHeatPower.supervisoryControlMode: %s", state)

        # If the state is not valid or the boiler is not active, no need to proceed
        if state is None:
            return None
        if state not in [3, 4]:
            return 0.0

        # Retrieve other required values
        heatpumpWaterOut = (
            self.getValue("hp2.temperatureWaterOut")
            if self.heatpump2Active()
            else self.getValue("hp1.temperatureWaterOut")
        )
        flowRate = self.getValue("qc.flowRateFiltered")
        flowWaterTemperature = self.getValue("flowMeter.waterSupplyTemperature")

        # Log debug information
        LOGGER.debug(
            "computedBoilerHeatPower.temperatureWaterOut: %s", heatpumpWaterOut
        )
        LOGGER.debug("computedBoilerHeatPower.flowRate: %s", flowRate)
        LOGGER.debug(
            "computedBoilerHeatPower.waterSupplyTemperature: %s", flowWaterTemperature
        )

        # Validate other inputs
        if heatpumpWaterOut is None or flowRate is None or flowWaterTemperature is None:
            return None

        # Compute the heat power using the conversion factor
        conversionFactor = self.getConversionFactor(flowWaterTemperature)
        value = round(
            (flowWaterTemperature - heatpumpWaterOut) * flowRate * conversionFactor, 2
        )

        # Prevent any negative numbers
        return max(value, 0.00)

    def computedSystemPower(self, parent_key: str | None = None):
        """Compute total system power."""
        boilerPower = self.computedBoilerHeatPower(parent_key)
        heatpumpPower = self.computedPower(parent_key)

        # Log debug information
        LOGGER.debug("computedSystemPower.boilerPower: %s", boilerPower)
        LOGGER.debug("computedSystemPower.heatpumpPower: %s", heatpumpPower)

        # Validate inputs
        if boilerPower is None or heatpumpPower is None:
            return None

        return float(boilerPower) + float(heatpumpPower)

    def computedPowerInput(self, parent_key: str | None = None):
        """Compute total powerInput."""
        powerInputHp1 = float(self.getValue("hp1.powerInput", 0))
        powerInputHp2 = (
            float(self.getValue("hp2.powerInput", 0)) if self.heatpump2Active() else 0
        )
        return powerInputHp1 + powerInputHp2

    def computedPower(self, parent_key: str | None = None):
        """Compute total power."""
        powerHp1 = float(self.getValue("hp1.power", 0))
        powerHp2 = float(self.getValue("hp2.power", 0)) if self.heatpump2Active() else 0
        return powerHp1 + powerHp2

    def computedCop(self, parent_key: str | None = None):
        """Compute COP."""
        electricalPower = self.electricalPower()
        computedHeatPower = self.computedHeatPower(parent_key)

        LOGGER.debug("computedCop.electricalPower %s", electricalPower)
        LOGGER.debug("computedCop.computedHeatPower %s", computedHeatPower)

        if electricalPower is None or computedHeatPower is None:
            return None

        computedHeatPower = float(computedHeatPower)
        electricalPower = float(electricalPower)
        if electricalPower == 0:
            return None

        return round(computedHeatPower / electricalPower, 2)

    def computedQuattCop(self, parent_key: str | None = None):
        """Compute Quatt COP."""
        if parent_key is None:
            powerInput = self.computedPowerInput(parent_key)
            powerOutput = self.computedPower(parent_key)
        else:
            powerInput = self.getValue(parent_key + ".powerInput")
            powerOutput = self.getValue(parent_key + ".power")

        LOGGER.debug("%s.computedQuattCop.powerInput %s", parent_key, powerInput)
        LOGGER.debug("%s.computedQuattCop.powerOutput %s", parent_key, powerOutput)

        if powerInput is None or powerOutput is None:
            return None

        powerOutput = float(powerOutput)
        powerInput = float(powerInput)
        if powerInput == 0:
            return None

        value = round(powerOutput / powerInput, 2)

        # Prevent negative sign for 0 values (like: -0.0)
        return math.copysign(0.0, 1) if value == 0 else value

    def computedDefrost(self, parent_key: str | None = None):
        """Compute Quatt Defrost State."""
        if parent_key is None:
            return None

        # Get the needed information to determine the defrost case
        state = self.getValue("qc.supervisoryControlMode")
        power_output = self.getValue(f"{parent_key}.power")
        water_delta = self.computedWaterDelta(parent_key)

        LOGGER.debug("%s.computedDefrost.supervisoryControlMode %s", parent_key, state)
        LOGGER.debug("%s.computedDefrost.powerOutput %s", parent_key, power_output)
        LOGGER.debug(
            "%s.computedDefrost.computedWaterDelta %s", parent_key, water_delta
        )

        if state is None or power_output is None or water_delta is None:
            return None

        state = int(state)
        power_output = float(power_output)
        water_delta = float(water_delta)

        # State equals to "Heating - heatpump" only or "heatpump + boiler"
        return state in [2, 3] and power_output == 0 and water_delta < -1

    def computedSupervisoryControlMode(self, parent_key: str | None = None):
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
        if state >= 100:
            return "Commissioning modes"
        return None

    def getValue(self, value_path: str, default: float | None = None):
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
                # Ignore any warnings about hp2 - for single quatt installations it is valid that hp2 does not exist.
                if key != "hp2":
                    LOGGER.warning("Could not find %s of %s", key, value_path)
                    LOGGER.debug("in %s", value)
                return default
            value = value[key]
            parent_key = key

        return value
