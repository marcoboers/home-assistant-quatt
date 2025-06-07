"""Sensor platform for quatt."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    DOMAIN as SENSOR_DOMAIN,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    EntityCategory,
    UnitOfPower,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant
import homeassistant.helpers.device_registry as dr
import homeassistant.helpers.entity_registry as er
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
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        suggested_display_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    QuattSensorEntityDescription(
        name="HP1 power",
        key="hp1.power",
        icon="mdi:heat-wave",
        native_unit_of_measurement=UnitOfPower.WATT,
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
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        suggested_display_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
        quatt_duo=True,
    ),
    QuattSensorEntityDescription(
        name="HP2 power",
        key="hp2.power",
        icon="mdi:heat-wave",
        native_unit_of_measurement=UnitOfPower.WATT,
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
        native_unit_of_measurement=UnitOfPower.WATT,
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
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        suggested_display_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
        quatt_duo=True,
    ),
    QuattSensorEntityDescription(
        name="Total power",
        key="computedPower",
        icon="mdi:heat-wave",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        suggested_display_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
        quatt_duo=True,
    ),
    QuattSensorEntityDescription(
        name="Total system power",
        key="computedSystemPower",
        icon="mdi:heat-wave",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        suggested_display_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    QuattSensorEntityDescription(
        name="Total water delta",
        key="computedWaterDelta",
        icon="mdi:thermometer-water",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        quatt_duo=True,
    ),
    QuattSensorEntityDescription(
        name="Total Quatt COP",
        key="computedQuattCop",
        icon="mdi:heat-pump",
        native_unit_of_measurement="CoP",
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        quatt_duo=True,
    ),
    # Heat Charger
    QuattSensorEntityDescription(
        name="HC electrical power",
        key="hc.electricalPower",
        icon="mdi:lightning-bolt",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        suggested_display_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
        quatt_all_electric=True,
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
        quatt_hybrid=True,
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
        quatt_hybrid=True,
        quatt_opentherm=True,
    ),
    QuattSensorEntityDescription(
        name="Boiler water pressure",
        key="boiler.otFbWaterPressure",
        icon="mdi:gauge",
        native_unit_of_measurement=UnitOfPressure.BAR,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        quatt_hybrid=True,
        quatt_opentherm=True,
    ),
    QuattSensorEntityDescription(
        name="Boiler heat power",
        key="boiler.computedBoilerHeatPower",
        icon="mdi:heat-wave",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        suggested_display_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
        quatt_hybrid=True,
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
        native_unit_of_measurement=UnitOfVolumeFlowRate.LITERS_PER_HOUR,
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


async def async_setup_entry(hass: HomeAssistant, entry, async_add_devices):
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    registry = er.async_get(hass)

    _LOGGER.debug("Heatpump 1 active: %s", coordinator.heatpump1Active())
    _LOGGER.debug("Heatpump 2 active: %s", coordinator.heatpump2Active())
    _LOGGER.debug("All electric active: %s", coordinator.allElectricActive())
    _LOGGER.debug("boiler OpenTherm: %s", coordinator.boilerOpenTherm())

    # Create only those sensors that make sense for this installation type.
    # Remove sensors that are not applicable based on the configuration.
    # This can occur when the configuration changes, e.g., from hybrid or duo to all-electric.
    device_reg = dr.async_get(hass)
    devices = dr.async_entries_for_config_entry(device_reg, entry.entry_id)
    device_ids = {dev.id for dev in devices}

    # Cache the active states
    heatpump2_active = coordinator.heatpump2Active()
    all_electric_active = coordinator.allElectricActive()
    boiler_opentherm = coordinator.boilerOpenTherm()

    # Determine which sensors to create based on the detected configuration
    flag_conditions = [
        ("quatt_hybrid", not all_electric_active),
        ("quatt_all_electric", all_electric_active),
        ("quatt_duo", heatpump2_active),
        ("quatt_opentherm", boiler_opentherm),
    ]

    # Determine which sensors to create based on the flags
    sensor_keys = {
        sensor_description.key
        for sensor_description in SENSORS
        if not any(getattr(sensor_description, flag) for flag, _ in flag_conditions)
        or all(
            condition
            for flag, condition in flag_conditions
            if getattr(sensor_description, flag)
        )
    }

    # Remove not applicable sensors
    for dev_id in device_ids:
        for entry_reg in er.async_entries_for_device(
            registry, dev_id, include_disabled_entities=True
        ):
            if (
                entry_reg.config_entry_id == entry.entry_id
                and entry_reg.domain == SENSOR_DOMAIN
                and entry_reg.platform == DOMAIN
                and not any(entry_reg.unique_id.endswith(key) for key in sensor_keys)
            ):
                registry.async_remove(entry_reg.entity_id)

    # Create sensor entities based on the filtered sensor keys
    sensors = [
        QuattSensor(
            coordinator=coordinator,
            sensor_key=descr.key,
            entity_description=descr,
        )
        for descr in SENSORS
        if descr.key in sensor_keys
    ]
    async_add_devices(sensors)


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
        return self.entity_description.entity_registry_enabled_default

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
