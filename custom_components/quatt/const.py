"""Constants for quatt."""
from logging import Logger, getLogger

from homeassistant.components.sensor import SensorEntityDescription, SensorDeviceClass
from homeassistant.const import (
    EntityCategory,
    UnitOfTemperature,
)

LOGGER: Logger = getLogger(__package__)

NAME = "Quatt"
DOMAIN = "quatt"
VERSION = "0.1.0"
ATTRIBUTION = "marcoboers"

CONF_POWER_SENSOR = "power_sensor"

BINARY_SENSORS = [
    # Heatpump 1
    SensorEntityDescription(
        name="HP1 silentMode",
        key="hp1.silentModeStatus",
        translation_key="hp_silentModeStatus",
        icon="mdi:sleep",
    ),
    SensorEntityDescription(
        name="HP1 limitedByCop",
        key="hp1.limitedByCop",
        translation_key="hp_silentModeStatus",
        icon="mdi:arrow-collapse-up",
    ),
    SensorEntityDescription(
        name="HP1 defrost",
        key="hp1.computedDefrost",
        translation_key="hp_silentModeStatus",
        icon="mdi:snowflake",
    ),
    # Heatpump 2
    SensorEntityDescription(
        name="HP2 silentMode",
        key="hp2.silentModeStatus",
        translation_key="hp_silentModeStatus",
        entity_registry_enabled_default=False,
        icon="mdi:sleep",
    ),
    SensorEntityDescription(
        name="HP2 limitedByCop",
        key="hp2.limitedByCop",
        translation_key="hp_silentModeStatus",
        entity_registry_enabled_default=False,
        icon="mdi:arrow-collapse-up",
    ),
    SensorEntityDescription(
        name="HP2 defrost",
        key="hp2.computedDefrost",
        icon="mdi:snowflake",
    ),
    # Boiler
    SensorEntityDescription(
        name="Boiler heating",
        key="boiler.otFbChModeActive",
        icon="mdi:heating-coil",
    ),
    SensorEntityDescription(
        name="Boiler domestic hot water",
        key="boiler.otFbDhwActive",
        icon="mdi:water-boiler",
    ),
    SensorEntityDescription(
        name="Boiler flame",
        key="boiler.otFbFlameOn",
        icon="mdi:fire",
    ),
    SensorEntityDescription(
        name="Boiler heating",
        key="boiler.otTbCH",
        icon="mdi:heating-coil",
    ),
    SensorEntityDescription(
        name="Boiler on/off mode",
        key="boiler.oTtbTurnOnOffBoilerOn",
        icon="mdi:water-boiler",
    ),
    # Thermostat
    SensorEntityDescription(
        name="Thermostat heating",
        key="thermostat.otFtChEnabled",
        icon="mdi:home-thermometer",
    ),
    SensorEntityDescription(
        name="Thermostat domestic hot water",
        key="thermostat.otFtDhwEnabled",
        icon="mdi:water-thermometer",
    ),
    SensorEntityDescription(
        name="Thermostat cooling",
        key="thermostat.otFtCoolingEnabled",
        icon="mdi:snowflake-thermometer",
    ),
    # QC
    SensorEntityDescription(
        name="QC pump protection",
        key="qc.stickyPumpProtectionEnabled",
        icon="mdi:shield-refresh-outline",
    ),
]


SENSORS = [
    # Time
    SensorEntityDescription(
        name="Timestamp last update",
        key="time.tsHuman",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    # Heatpump 1
    SensorEntityDescription(
        name="HP1 workingmode",
        key="hp1.getMainWorkingMode",
        icon="mdi:auto-mode",
    ),
    SensorEntityDescription(
        name="HP1 temperatureOutside",
        key="hp1.temperatureOutside",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=2,
    ),
    SensorEntityDescription(
        name="HP1 temperatureWaterIn",
        key="hp1.temperatureWaterIn",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=2,
    ),
    SensorEntityDescription(
        name="HP1 temperatureWaterOut",
        key="hp1.temperatureWaterOut",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=2,
    ),
    SensorEntityDescription(
        name="HP1 waterDelta",
        key="hp1.computedWaterDelta",
        icon="mdi:thermometer-water",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=2,
    ),
    SensorEntityDescription(
        name="HP1 heatPower",
        key="hp1.computedHeatPower",
        icon="mdi:heat-wave",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        suggested_display_precision=0,
    ),
    SensorEntityDescription(
        name="HP1 powerInput",
        key="hp1.powerInput",
        icon="mdi:lightning-bolt",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        suggested_display_precision=0,
    ),
    SensorEntityDescription(
        name="HP1 power",
        key="hp1.power",
        icon="mdi:heat-wave",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        suggested_display_precision=0,
    ),
    SensorEntityDescription(
        name="HP1 Quatt COP",
        key="hp1.computedQuattCop",
        icon="mdi:heat-pump",
        native_unit_of_measurement="CoP",
        suggested_display_precision=2,
        state_class="measurement",
    ),
    SensorEntityDescription(
        name="HP1 COP",
        key="hp1.computedCop",
        icon="mdi:heat-pump",
        native_unit_of_measurement="CoP",
        suggested_display_precision=2,
        state_class="measurement",
    ),
    # Heatpump 2
    SensorEntityDescription(
        name="HP2 workingmode",
        key="hp2.getMainWorkingMode",
        icon="mdi:auto-mode",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        name="HP2 temperatureOutside",
        key="hp2.temperatureOutside",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        entity_registry_enabled_default=False,
        suggested_display_precision=2,
    ),
    SensorEntityDescription(
        name="HP2 temperatureWaterIn",
        key="hp2.temperatureWaterIn",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        entity_registry_enabled_default=False,
        suggested_display_precision=2,
    ),
    SensorEntityDescription(
        name="HP2 temperatureWaterOut",
        key="hp2.temperatureWaterOut",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        entity_registry_enabled_default=False,
        suggested_display_precision=2,
    ),
    SensorEntityDescription(
        name="HP2 waterDelta",
        key="hp2.computedWaterDelta",
        icon="mdi:thermometer-water",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        entity_registry_enabled_default=False,
        suggested_display_precision=2,
    ),
    SensorEntityDescription(
        name="HP2 powerInput",
        key="hp2.powerInput",
        icon="mdi:lightning-bolt",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        entity_registry_enabled_default=False,
        suggested_display_precision=0,
    ),
    SensorEntityDescription(
        name="HP2 power",
        key="hp2.power",
        icon="mdi:heat-wave",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        entity_registry_enabled_default=False,
        suggested_display_precision=0,
    ),
    SensorEntityDescription(
        name="HP2 Quatt COP",
        key="hp2.computedQuattCop",
        icon="mdi:heat-pump",
        native_unit_of_measurement="CoP",
        entity_registry_enabled_default=False,
        suggested_display_precision=2,
        state_class="measurement",
    ),
    # Combined
    SensorEntityDescription(
        name="Total powerInput",
        key="computedPowerInput",
        icon="mdi:lightning-bolt",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        entity_registry_enabled_default=False,
        suggested_display_precision=0,
    ),
    SensorEntityDescription(
        name="Total power",
        key="computedPower",
        icon="mdi:heat-wave",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        entity_registry_enabled_default=False,
        suggested_display_precision=0,
    ),
    SensorEntityDescription(
        name="Total waterDelta",
        key="computedWaterDelta",
        icon="mdi:thermometer-water",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        entity_registry_enabled_default=False,
        suggested_display_precision=2,
    ),
    SensorEntityDescription(
        name="Total Quatt COP",
        key="computedQuattCop",
        icon="mdi:heat-pump",
        native_unit_of_measurement="CoP",
        entity_registry_enabled_default=False,
        suggested_display_precision=2,
        state_class="measurement",
    ),
    # Boiler
    SensorEntityDescription(
        name="Boiler temperature water inlet",
        key="boiler.otFbSupplyInletTemperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=2,
    ),
    SensorEntityDescription(
        name="Boiler temperature water outlet",
        key="boiler.otFbSupplyOutletTemperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=2,
    ),
    # Flowmeter
    SensorEntityDescription(
        name="FlowMeter temperature",
        key="flowMeter.waterSupplyTemperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=2,
    ),
    SensorEntityDescription(
        name="FlowMeter flowRate",
        key="flowMeter.flowRate",
        icon="mdi:gauge",
        native_unit_of_measurement="l/h",
        suggested_display_precision=2,
    ),
    # Thermostat
    SensorEntityDescription(
        name="Thermostat control setpoint",
        key="thermostat.otFtControlSetpoint",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=2,
    ),
    SensorEntityDescription(
        name="Thermostat room setpoint",
        key="thermostat.otFtRoomSetpoint",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        name="Thermostat room temperature",
        key="thermostat.otFtRoomTemperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=2,
    ),
    # QC
    SensorEntityDescription(
        name="QC supervisoryControlMode", key="qc.supervisoryControlMode"
    ),
    SensorEntityDescription(
        name="QC supervisory control mode", key="qc.computedSupervisoryControlMode"
    ),
    # System
    SensorEntityDescription(
        name="system hostname",
        key="system.hostName",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
]
