"""Sensor platform for quatt."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfTemperature
import homeassistant.util.dt as dt_util

from .const import DOMAIN
from .coordinator import QuattDataUpdateCoordinator
from .entity import QuattEntity, QuattSensorEntityDescription

SENSORS = [
    # Time
    QuattSensorEntityDescription(
        name="Timestamp last update",
        key="time.tsHuman",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_registry_enabled_default=False,
    ),
    # Heatpump 1
    QuattSensorEntityDescription(
        name="HP1 workingmode",
        key="hp1.getMainWorkingMode",
        icon="mdi:auto-mode",
    ),
    QuattSensorEntityDescription(
        name="HP1 temperature outside",
        key="hp1.temperatureOutside",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    QuattSensorEntityDescription(
        name="HP1 temperature water in",
        key="hp1.temperatureWaterIn",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    QuattSensorEntityDescription(
        name="HP1 temperature water out",
        key="hp1.temperatureWaterOut",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    QuattSensorEntityDescription(
        name="HP1 water delta",
        key="hp1.computedWaterDelta",
        icon="mdi:thermometer-water",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    QuattSensorEntityDescription(
        name="HP1 power input",
        key="hp1.powerInput",
        icon="mdi:lightning-bolt",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        suggested_display_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    QuattSensorEntityDescription(
        name="HP1 power",
        key="hp1.power",
        icon="mdi:heat-wave",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        suggested_display_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    QuattSensorEntityDescription(
        name="HP1 Quatt COP",
        key="hp1.computedQuattCop",
        icon="mdi:heat-pump",
        native_unit_of_measurement="CoP",
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # Heatpump 2
    QuattSensorEntityDescription(
        name="HP2 workingmode",
        key="hp2.getMainWorkingMode",
        icon="mdi:auto-mode",
        quatt_duo=True,
    ),
    QuattSensorEntityDescription(
        name="HP2 temperature outside",
        key="hp2.temperatureOutside",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        quatt_duo=True,
    ),
    QuattSensorEntityDescription(
        name="HP2 temperature water in",
        key="hp2.temperatureWaterIn",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        quatt_duo=True,
    ),
    QuattSensorEntityDescription(
        name="HP2 temperature water out",
        key="hp2.temperatureWaterOut",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        quatt_duo=True,
    ),
    QuattSensorEntityDescription(
        name="HP2 water delta",
        key="hp2.computedWaterDelta",
        icon="mdi:thermometer-water",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        quatt_duo=True,
    ),
    QuattSensorEntityDescription(
        name="HP2 power input",
        key="hp2.powerInput",
        icon="mdi:lightning-bolt",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        suggested_display_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
        quatt_duo=True,
    ),
    QuattSensorEntityDescription(
        name="HP2 power",
        key="hp2.power",
        icon="mdi:heat-wave",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        suggested_display_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
        quatt_duo=True,
    ),
    QuattSensorEntityDescription(
        name="HP2 Quatt COP",
        key="hp2.computedQuattCop",
        icon="mdi:heat-pump",
        native_unit_of_measurement="CoP",
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        quatt_duo=True,
    ),
    # Combined
    QuattSensorEntityDescription(
        name="Heat power",
        key="computedHeatPower",
        icon="mdi:heat-wave",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        suggested_display_precision=0,
        state_class="measurement",
    ),
    QuattSensorEntityDescription(
        name="COP",
        key="computedCop",
        icon="mdi:heat-pump",
        native_unit_of_measurement="CoP",
        suggested_display_precision=2,
        state_class="measurement",
    ),
    QuattSensorEntityDescription(
        name="Total power input",
        key="computedPowerInput",
        icon="mdi:lightning-bolt",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        entity_registry_enabled_default=False,
        suggested_display_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
        quatt_duo=True,
    ),
    QuattSensorEntityDescription(
        name="Total power",
        key="computedPower",
        icon="mdi:heat-wave",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        entity_registry_enabled_default=False,
        suggested_display_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
        quatt_duo=True,
    ),
    QuattSensorEntityDescription(
        name="Total water delta",
        key="computedWaterDelta",
        icon="mdi:thermometer-water",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        entity_registry_enabled_default=False,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        quatt_duo=True,
    ),
    QuattSensorEntityDescription(
        name="Total Quatt COP",
        key="computedQuattCop",
        icon="mdi:heat-pump",
        native_unit_of_measurement="CoP",
        entity_registry_enabled_default=False,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        quatt_duo=True,
    ),
    # Boiler
    QuattSensorEntityDescription(
        name="Boiler temperature water inlet",
        key="boiler.otFbSupplyInletTemperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        quatt_opentherm=True,
    ),
    QuattSensorEntityDescription(
        name="Boiler temperature water outlet",
        key="boiler.otFbSupplyOutletTemperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        quatt_opentherm=True,
    ),
    # Flowmeter
    QuattSensorEntityDescription(
        name="Flowmeter temperature",
        key="flowMeter.waterSupplyTemperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    QuattSensorEntityDescription(
        name="Flowmeter flowrate",
        key="qc.flowRateFiltered",
        icon="mdi:gauge",
        native_unit_of_measurement="L/h",
        device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
        suggested_display_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # Thermostat
    QuattSensorEntityDescription(
        name="Thermostat control setpoint",
        key="thermostat.otFtControlSetpoint",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    QuattSensorEntityDescription(
        name="Thermostat room setpoint",
        key="thermostat.otFtRoomSetpoint",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=1,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    QuattSensorEntityDescription(
        name="Thermostat room temperature",
        key="thermostat.otFtRoomTemperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # QC
    QuattSensorEntityDescription(
        name="QC supervisory control mode code",
        key="qc.supervisoryControlMode",
    ),
    QuattSensorEntityDescription(
        name="QC supervisory control mode",
        key="qc.computedSupervisoryControlMode",
    ),
    # System
    QuattSensorEntityDescription(
        name="system hostname",
        key="system.hostName",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_devices):
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    _LOGGER.debug("Heatpump 1 active: %s", coordinator.heatpump1Active())
    _LOGGER.debug("Heatpump 2 active: %s", coordinator.heatpump2Active())
    _LOGGER.debug("boiler OpenTherm: %s", coordinator.boilerOpenTherm())

    async_add_devices(
        QuattSensor(
            coordinator=coordinator,
            sensor_key=entity_description.key,
            entity_description=entity_description,
        )
        for entity_description in SENSORS
    )


class QuattSensor(QuattEntity, SensorEntity):
    """quatt Sensor class."""

    def __init__(
        self,
        sensor_key: str,
        coordinator: QuattDataUpdateCoordinator,
        entity_description: QuattSensorEntityDescription,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator, sensor_key)
        self.entity_description = entity_description

    @property
    def entity_registry_enabled_default(self):
        """Return whether the sensor should be enabled by default."""
        value = self.entity_description.entity_registry_enabled_default

        # Only check the duo property when set, enable when duo found
        if value and self.entity_description.quatt_duo:
            value = self.coordinator.heatpump2Active()

        # Only check the openthern when set, enable when opentherm found
        if value and self.entity_description.quatt_opentherm:
            value = self.coordinator.boilerOpenTherm()

        return value

    @property
    def native_value(self) -> str:
        """Return the native value of the sensor."""
        value = (
            self.coordinator.getValue(self.entity_description.key)
            if not self.entity_description.quatt_duo
            or self.coordinator.heatpump2Active()
            else None
        )

        if not value:
            return value

        if self.entity_description.device_class == SensorDeviceClass.TIMESTAMP:
            value = dt_util.parse_datetime(value)

        return value
