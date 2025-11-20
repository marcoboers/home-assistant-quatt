"""Local DataUpdateCoordinator for Quatt integration."""

from __future__ import annotations

import inspect
import math
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN

from .const import (
    CONVERSION_FACTORS,
    LOGGER,
    AllElectricSupervisoryControlMode,
    ElectricityTariffType,
    GasTariffType,
    SupervisoryControlMode,
)
from .coordinator import QuattDataUpdateCoordinator


# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
class QuattLocalDataUpdateCoordinator(QuattDataUpdateCoordinator):
    """Class to manage fetching data from the local API."""

    config_entry: ConfigEntry

    def heatpump_1_active(self) -> bool:
        """Check if heatpump 1 is active."""
        return self.get_value("hp1") is not None

    def heatpump_2_active(self) -> bool:
        """Check if heatpump 2 is active."""
        return self.get_value("hp2") is not None

    def all_electric_active(self) -> bool:
        """Check if it is an all electric installation."""
        return self.get_value("hc.electricalPower") is not None

    def is_boiler_opentherm(self) -> bool:
        """Check if the boiler connected to the CIC offers OpenTherm."""
        return self.get_value("boiler.otFbChModeActive") is not None

    def get_conversion_factor(self, temperature: float) -> float:
        """Get the conversion factor for the nearest temperature."""
        nearest_temperature = min(
            CONVERSION_FACTORS.keys(), key=lambda t: abs(t - temperature)
        )
        return CONVERSION_FACTORS[nearest_temperature]

    def electricalPower(self) -> float | None:  # pylint: disable=invalid-name
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

    def computedWaterDelta(self, parent_key: str | None = None) -> float | None:  # pylint: disable=invalid-name
        """Compute waterdelta."""
        if parent_key is None:
            parent_key = "" if self.heatpump_2_active() else "hp1"

        if parent_key == "":
            temperature_water_out = self.get_value("hp2.temperatureWaterOut")
            temperature_water_in = self.get_value("hp1.temperatureWaterIn")
        else:
            temperature_water_out = self.get_value(parent_key + ".temperatureWaterOut")
            temperature_water_in = self.get_value(parent_key + ".temperatureWaterIn")

        LOGGER.debug(
            "%s.computedWaterDelta.temperatureWaterOut %s",
            parent_key,
            temperature_water_out,
        )
        LOGGER.debug(
            "%s.computedWaterDelta.temperatureWaterIn %s",
            parent_key,
            temperature_water_in,
        )

        if temperature_water_out is None or temperature_water_in is None:
            return None

        return round(temperature_water_out - temperature_water_in, 2)

    def computedHeatPower(self) -> float | None:  # pylint: disable=invalid-name
        """Compute heatpower."""

        # Retrieve the supervisory control mode state first
        state = self.get_value("qc.supervisoryControlMode")
        LOGGER.debug("computedBoilerHeatPower.supervisoryControlMode: %s", state)

        # If the state is not valid or the heatpump is not active, no need to proceed
        if state is None:
            return None
        if state not in [
            SupervisoryControlMode.HEATING_HEATPUMP_ONLY,
            SupervisoryControlMode.HEATING_HEATPUMP_PLUS_BOILER,
        ]:
            return 0.0

        if self.heatpump_2_active():
            computed_water_delta = self.computedWaterDelta(None)
            temperature_water_out = self.get_value("hp2.temperatureWaterOut")
        else:
            computed_water_delta = self.computedWaterDelta("hp1")
            temperature_water_out = self.get_value("hp1.temperatureWaterOut")
        flowrate = self.get_value("qc.flowRateFiltered")

        LOGGER.debug("computedHeatPower.computedWaterDelta %s", computed_water_delta)
        LOGGER.debug("computedHeatPower.flowRate %s", flowrate)
        LOGGER.debug("computedHeatPower.temperatureWaterOut %s", temperature_water_out)

        if (
            computed_water_delta is None
            or flowrate is None
            or temperature_water_out is None
        ):
            return None

        value = round(
            computed_water_delta
            * flowrate
            * self.get_conversion_factor(temperature_water_out),
            2,
        )

        # Prevent any negative numbers
        return max(value, 0.00)

    def computedBoilerHeatPower(self) -> float | None:  # pylint: disable=invalid-name
        """Compute the boiler's added heat power."""

        # Retrieve the supervisory control mode state first
        state = self.get_value("qc.supervisoryControlMode")
        LOGGER.debug("computedBoilerHeatPower.supervisoryControlMode: %s", state)

        # If the state is not valid or the boiler is not active, no need to proceed
        if state is None:
            return None
        if state not in [
            SupervisoryControlMode.HEATING_HEATPUMP_PLUS_BOILER,
            SupervisoryControlMode.HEATING_BOILER_ONLY,
        ]:
            return 0.0

        # Retrieve other required values
        heatpump_water_out = (
            self.get_value("hp2.temperatureWaterOut")
            if self.heatpump_2_active()
            else self.get_value("hp1.temperatureWaterOut")
        )
        flowrate = self.get_value("qc.flowRateFiltered")
        flow_water_temperature = self.get_value("flowMeter.waterSupplyTemperature")

        # Log debug information
        LOGGER.debug(
            "computedBoilerHeatPower.temperatureWaterOut: %s", heatpump_water_out
        )
        LOGGER.debug("computedBoilerHeatPower.flowRate: %s", flowrate)
        LOGGER.debug(
            "computedBoilerHeatPower.waterSupplyTemperature: %s", flow_water_temperature
        )

        # Validate other inputs
        if (
            heatpump_water_out is None
            or flowrate is None
            or flow_water_temperature is None
        ):
            return None

        # Compute the heat power using the conversion factor
        conversion_factor = self.get_conversion_factor(flow_water_temperature)
        value = round(
            (flow_water_temperature - heatpump_water_out)
            * flowrate
            * conversion_factor,
            2,
        )

        # Prevent any negative numbers
        return max(value, 0.00)

    def computedSystemPower(self) -> float | None:  # pylint: disable=invalid-name
        """Compute total system power."""
        heater_power = (
            self.get_value("hc.electricalPower")
            if self.all_electric_active()
            else self.computedBoilerHeatPower()
        )
        heatpump_power = self.computedPower()

        # Log debug information
        LOGGER.debug("computedSystemPower.boilerPower: %s", heater_power)
        LOGGER.debug("computedSystemPower.heatpumpPower: %s", heatpump_power)

        # Validate inputs
        if heater_power is None or heatpump_power is None:
            return None

        return float(heater_power) + float(heatpump_power)

    def computedPowerInput(self) -> float | None:  # pylint: disable=invalid-name
        """Compute total powerInput."""
        power_input_hp_1 = float(self.get_value("hp1.powerInput", 0))
        power_input_hp_2 = (
            float(self.get_value("hp2.powerInput", 0))
            if self.heatpump_2_active()
            else 0
        )
        return power_input_hp_1 + power_input_hp_2

    def computedPower(self) -> float | None:  # pylint: disable=invalid-name
        """Compute total power."""
        power_hp_1 = float(self.get_value("hp1.power", 0))
        power_hp_2 = (
            float(self.get_value("hp2.power", 0)) if self.heatpump_2_active() else 0
        )
        return power_hp_1 + power_hp_2

    def computedCop(self) -> float | None:  # pylint: disable=invalid-name
        """Compute COP."""
        electrical_power = self.electricalPower()
        computed_heat_power = self.computedHeatPower()

        LOGGER.debug("computedCop.electricalPower %s", electrical_power)
        LOGGER.debug("computedCop.computedHeatPower %s", computed_heat_power)

        if electrical_power is None or computed_heat_power is None:
            return None

        computed_heat_power = float(computed_heat_power)
        electrical_power = float(electrical_power)
        if electrical_power == 0:
            return None

        return round(computed_heat_power / electrical_power, 2)

    def computedQuattCop(self, parent_key: str | None = None) -> float | None:  # pylint: disable=invalid-name
        """Compute Quatt COP."""
        if parent_key is None:
            power_input = self.computedPowerInput()
            power_output = self.computedPower()
        else:
            power_input = self.get_value(parent_key + ".powerInput")
            power_output = self.get_value(parent_key + ".power")

        LOGGER.debug("%s.computedQuattCop.powerInput %s", parent_key, power_input)
        LOGGER.debug("%s.computedQuattCop.powerOutput %s", parent_key, power_output)

        if power_input is None or power_output is None:
            return None

        power_output = float(power_output)
        power_input = float(power_input)
        if power_input == 0:
            return None

        value = round(power_output / power_input, 2)

        # Prevent negative sign for 0 values (like: -0.0)
        return math.copysign(0.0, 1) if value == 0 else value

    def computedDefrost(self, parent_key: str | None = None) -> bool:  # pylint: disable=invalid-name
        """Compute Quatt Defrost State."""
        if parent_key is None:
            return None

        # Get the needed information to determine the defrost case
        state = self.get_value("qc.supervisoryControlMode")
        power_output = self.get_value(f"{parent_key}.power")
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

        return (
            state
            in [
                SupervisoryControlMode.HEATING_HEATPUMP_ONLY,
                SupervisoryControlMode.HEATING_HEATPUMP_PLUS_BOILER,
            ]
            and power_output < -1
            and water_delta < -1
        )

    def computedSupervisoryControlMode(self) -> str | None:  # pylint: disable=invalid-name
        """Map the numeric supervisoryControlMode to a textual status."""
        state = self.get_value("qc.supervisoryControlMode")
        if state is None:
            return None

        # Codes >= 100 are Commissioning modes
        if state >= 100:
            return "Commissioning modes"

        try:
            return SupervisoryControlMode(state).description
        except ValueError:
            return None

    def computedAllESupervisoryControlMode(self) -> str | None:  # pylint: disable=invalid-name
        """Map the numeric All-electric supervisoryControlMode to a textual status."""
        state = self.get_value("qcAllE.allESupervisoryControlMode")
        if state is None:
            return None

        try:
            return AllElectricSupervisoryControlMode(state).description
        except ValueError:
            return None

    def computedElectricityTariffType(self) -> str | None:  # pylint: disable=invalid-name
        """Map the numeric electricityTariffType to a textual status."""
        state = self.get_value("system.electricityTariffType")
        if state is None:
            return None

        try:
            return ElectricityTariffType(state).description
        except ValueError:
            return None

    def computedGasTariffType(self) -> str | None:  # pylint: disable=invalid-name
        """Map the numeric gasTariffType to a textual status."""
        state = self.get_value("system.gasTariffType")
        if state is None:
            return None

        try:
            return GasTariffType(state).description
        except ValueError:
            return None

    def get_value(self, value_path: str, default: float | None = None) -> Any:
        """Retrieve a value by dot notation or invoke a computed method."""
        parts = value_path.split(".")
        current_node = self.data
        parent_key = None
        for part in parts:
            # Could not find the value, return default
            if current_node is None:
                return default

            # Computed method invocation
            if part.startswith("computed") and hasattr(self, part):
                method = getattr(self, part)
                sig = inspect.signature(method)
                # Call with parent_key if accepted, else without
                if "parent_key" in sig.parameters:
                    return method(parent_key)
                return method()

            # Dict key access
            if isinstance(current_node, dict) and part in current_node:
                current_node = current_node[part]

            # Missing key
            else:
                # Ignore any warnings about hp2, boiler and hc
                # hp2: for single heatpump installations it is valid that hp2 does not exist.
                # boiler: for all electic installations it is valid that boiler does not exist.
                # hc: for hybrid installations it is valid that hc does not exist.
                if part not in ("hp2", "boiler", "hc"):
                    LOGGER.warning("Could not find %s of %s", part, value_path)
                    LOGGER.debug(" in %s %s", current_node, type(current_node))
                return default

            parent_key = part

        return current_node
