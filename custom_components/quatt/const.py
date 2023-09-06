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
    ),
    SensorEntityDescription(
        name="HP1 limitedByCop",
        key="hp1.limitedByCop",
        translation_key="hp_silentModeStatus",
    ),
    # Heatpump 2
    SensorEntityDescription(
        name="HP2 silentMode",
        key="hp2.silentModeStatus",
        translation_key="hp_silentModeStatus",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        name="HP2 limitedByCop",
        key="hp2.limitedByCop",
        translation_key="hp_silentModeStatus",
        entity_registry_enabled_default=False,
    ),
    # Boiler
    SensorEntityDescription(
        name="Boiler heating",
        key="boiler.otFbChModeActive",
    ),
    SensorEntityDescription(
        name="Boiler domestic hot water",
        key="boiler.otFbDhwActive",
    ),
    SensorEntityDescription(
        name="Boiler flame",
        key="boiler.otFbFlameOn",
    ),
    SensorEntityDescription(
        name="Boiler heating",
        key="boiler.otTbCH",
    ),
    SensorEntityDescription(
        name="Boiler on/off mode",
        key="boiler.oTtbTurnOnOffBoilerOn",
    ),
    # Thermostat
    SensorEntityDescription(name="Thermostat heating", key="thermostat.otFtChEnabled"),
    SensorEntityDescription(
        name="Thermostat domestic hot water",
        key="thermostat.otFtDhwEnabled",
    ),
    SensorEntityDescription(
        name="Thermostat cooling", key="thermostat.otFtCoolingEnabled"
    ),
    # QC
    SensorEntityDescription(
        name="QC pump protection", key="qc.stickyPumpProtectionEnabled"
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
    ),
    SensorEntityDescription(
        name="HP1 temperatureOutside",
        key="hp1.temperatureOutside",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    SensorEntityDescription(
        name="HP1 temperatureWaterIn",
        key="hp1.temperatureWaterIn",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    SensorEntityDescription(
        name="HP1 temperatureWaterOut",
        key="hp1.temperatureWaterOut",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    SensorEntityDescription(
        name="HP1 waterDelta",
        key="hp1.computedWaterDelta",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    SensorEntityDescription(
        name="HP1 heatPower",
        key="hp1.computedHeatPower",
        icon="mdi:heat-wave",
        device_class=SensorDeviceClass.POWER,
    ),
    SensorEntityDescription(
        name="HP1 COP",
        key="hp1.computedCop",
        icon="mdi:heat-pump",
    ),
    # Heatpump 2
    SensorEntityDescription(
        name="HP2 workingmode",
        key="hp2.getMainWorkingMode",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        name="HP2 temperatureOutside",
        key="hp2.temperatureOutside",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        name="HP2 temperatureWaterIn",
        key="hp2.temperatureWaterIn",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        name="HP2 temperatureWaterOut",
        key="hp2.temperatureWaterOut",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        entity_registry_enabled_default=False,
    ),
    # Boiler
    SensorEntityDescription(
        name="Boiler temperature water inlet",
        key="boiler.otFbSupplyInletTemperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    SensorEntityDescription(
        name="Boiler temperature water outlet",
        key="boiler.otFbSupplyOutletTemperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    # Flowmeter
    SensorEntityDescription(
        name="FlowMeter temperature",
        key="flowMeter.waterSupplyTemperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    SensorEntityDescription(
        name="FlowMeter flowRate",
        key="flowMeter.flowRate",
        icon="mdi:gauge",
        unit_of_measurement="l/h",
    ),
    # Thermostat
    SensorEntityDescription(
        name="Thermostat control setpoint",
        key="thermostat.otFtControlSetpoint",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    SensorEntityDescription(
        name="Thermostat room setpoint",
        key="thermostat.otFtRoomSetpoint",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    SensorEntityDescription(
        name="Thermostat room temperature",
        key="thermostat.otFtRoomTemperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    # QC
    SensorEntityDescription(
        name="Quatt QC supervisoryControlMode", key="qc.supervisoryControlMode"
    ),
    # System
    SensorEntityDescription(
        name="Quatt system hostname",
        key="system.hostName",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
]
