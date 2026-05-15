"""CIC sensor descriptions for Quatt."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    CURRENCY_EURO,
    EntityCategory,
    UnitOfEnergy,
    UnitOfMass,
    UnitOfPower,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolume,
    UnitOfVolumeFlowRate,
)

from .entity import QuattFeatureFlags, QuattSensorEntityDescription
from .entity_sensor import QuattSystemSensor


CIC_SENSORS: list[QuattSensorEntityDescription] = [
    QuattSensorEntityDescription(
        name="Timestamp last update",
        key="time.tsHuman",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_registry_enabled_default=False,
    ),
    QuattSensorEntityDescription(
        name="Heat power",
        key="computedHeatPower",
        icon="mdi:heat-wave",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        suggested_display_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    QuattSensorEntityDescription(
        name="COP",
        key="computedCop",
        icon="mdi:heat-pump",
        native_unit_of_measurement="CoP",
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    QuattSensorEntityDescription(
        name="Total power input",
        key="computedPowerInput",
        icon="mdi:lightning-bolt",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        suggested_display_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    QuattSensorEntityDescription(
        name="Total power",
        key="computedPower",
        icon="mdi:heat-wave",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        suggested_display_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
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
    ),
    QuattSensorEntityDescription(
        name="Total Quatt COP",
        key="computedQuattCop",
        icon="mdi:heat-pump",
        native_unit_of_measurement="CoP",
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    QuattSensorEntityDescription(
        name="QC supervisory control mode code",
        key="qc.supervisoryControlMode",
    ),
    QuattSensorEntityDescription(
        name="QC supervisory control mode",
        key="qc.computedSupervisoryControlMode",
    ),
    QuattSensorEntityDescription(
        name="QC All-Electric supervisory control mode code",
        key="qcAllE.allESupervisoryControlMode",
        quatt_features=QuattFeatureFlags(
            all_electric=True,
        ),
    ),
    QuattSensorEntityDescription(
        name="QC All-Electric supervisory control mode",
        key="qcAllE.computedAllESupervisoryControlMode",
        quatt_features=QuattFeatureFlags(
            all_electric=True,
        ),
    ),
    QuattSensorEntityDescription(
        name="Electricity price used",
        key="qc.electricityPriceUsed",
        icon="mdi:currency-eur",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    QuattSensorEntityDescription(
        name="Electricity tariff type",
        key="system.computedElectricityTariffType",
        icon="mdi:swap-horizontal-circle",
    ),
    QuattSensorEntityDescription(
        name="Gas price used",
        key="qc.gasPriceUsed",
        icon="mdi:currency-eur",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfVolume.CUBIC_METERS}",
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    QuattSensorEntityDescription(
        name="Gas tariff type",
        key="system.computedGasTariffType",
        icon="mdi:swap-horizontal-circle",
    ),
    QuattSensorEntityDescription(
        name="System",
        key="system.hostName",
        entity_category=EntityCategory.DIAGNOSTIC,
        quatt_entity_class=QuattSystemSensor,
    ),
    QuattSensorEntityDescription(
        name="Installation ID",
        key="installationId",
        icon="mdi:identifier",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        quatt_features=QuattFeatureFlags(
            mobile_api=True,
        ),
    ),
    QuattSensorEntityDescription(
        name="Installed at",
        key="installedAt",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        quatt_features=QuattFeatureFlags(
            mobile_api=True,
        ),
    ),
    QuattSensorEntityDescription(
        name="Status",
        key="status",
        icon="mdi:information",
        entity_category=EntityCategory.DIAGNOSTIC,
        quatt_features=QuattFeatureFlags(
            mobile_api=True,
        ),
    ),
    QuattSensorEntityDescription(
        name="Cable connection status",
        key="cableConnectionStatus",
        icon="mdi:ethernet",
        entity_category=EntityCategory.DIAGNOSTIC,
        quatt_features=QuattFeatureFlags(
            mobile_api=True,
        ),
    ),
    QuattSensorEntityDescription(
        name="LTE connection status",
        key="lteConnectionStatus",
        icon="mdi:signal",
        entity_category=EntityCategory.DIAGNOSTIC,
        quatt_features=QuattFeatureFlags(
            mobile_api=True,
        ),
    ),
    QuattSensorEntityDescription(
        name="WiFi connection status",
        key="wifiConnectionStatus",
        icon="mdi:wifi",
        entity_category=EntityCategory.DIAGNOSTIC,
        quatt_features=QuattFeatureFlags(
            mobile_api=True,
        ),
    ),
    QuattSensorEntityDescription(
        name="WiFi SSID",
        key="wifiSSID",
        icon="mdi:wifi",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        quatt_features=QuattFeatureFlags(
            mobile_api=True,
        ),
    ),
    QuattSensorEntityDescription(
        name="Electricity price",
        key="electricityPrice",
        icon="mdi:currency-eur",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        quatt_features=QuattFeatureFlags(
            mobile_api=True,
        ),
    ),
    QuattSensorEntityDescription(
        name="Day electricity price",
        key="dayElectricityPrice",
        icon="mdi:currency-eur",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        quatt_features=QuattFeatureFlags(
            mobile_api=True,
        ),
    ),
    QuattSensorEntityDescription(
        name="Night electricity price",
        key="nightElectricityPrice",
        icon="mdi:currency-eur",
        native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        quatt_features=QuattFeatureFlags(
            mobile_api=True,
        ),
    ),
    QuattSensorEntityDescription(
        name="Gas price",
        key="gasPrice",
        icon="mdi:currency-eur",
        native_unit_of_measurement=f"{CURRENCY_EURO}/m³",
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        quatt_features=QuattFeatureFlags(
            mobile_api=True,
        ),
    ),
    QuattSensorEntityDescription(
        name="Silent mode",
        key="silentMode",
        icon="mdi:sleep",
        quatt_features=QuattFeatureFlags(
            mobile_api=True,
        ),
    ),
    QuattSensorEntityDescription(
        name="Supervisory control mode",
        key="supervisoryControlMode",
        icon="mdi:cog",
        quatt_features=QuattFeatureFlags(
            mobile_api=True,
        ),
    ),
    QuattSensorEntityDescription(
        name="Number of heat pumps",
        key="numberOfHeatPumps",
        icon="mdi:heat-pump",
        suggested_display_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        quatt_features=QuattFeatureFlags(
            mobile_api=True,
        ),
    ),
    QuattSensorEntityDescription(
        name="Insights start at",
        key="insightsStartAt",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        quatt_features=QuattFeatureFlags(
            mobile_api=True,
        ),
        entity_registry_enabled_default=False,
    ),
    QuattSensorEntityDescription(
        name="Quatt build",
        key="quattBuild",
        icon="mdi:package-variant",
        entity_category=EntityCategory.DIAGNOSTIC,
        quatt_features=QuattFeatureFlags(
            mobile_api=True,
        ),
    ),
    QuattSensorEntityDescription(
        name="Quatt heating production amount",
        key="quattHeatingProductionAmount",
        icon="mdi:heat-wave",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        suggested_display_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
        quatt_features=QuattFeatureFlags(
            mobile_api=True,
        ),
    ),
    QuattSensorEntityDescription(
        name="Electricity consumption amount",
        key="electricityConsumptionAmount",
        icon="mdi:lightning-bolt",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        quatt_features=QuattFeatureFlags(
            mobile_api=True,
        ),
    ),
    QuattSensorEntityDescription(
        name="Name",
        key="name",
        icon="mdi:label",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        quatt_features=QuattFeatureFlags(
            mobile_api=True,
        ),
    ),
    QuattSensorEntityDescription(
        name="Zip code",
        key="zipCode",
        icon="mdi:map-marker",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        quatt_features=QuattFeatureFlags(
            mobile_api=True,
        ),
    ),
    QuattSensorEntityDescription(
        name="Country",
        key="country",
        icon="mdi:flag",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        quatt_features=QuattFeatureFlags(
            mobile_api=True,
        ),
    ),
    QuattSensorEntityDescription(
        name="Order number",
        key="orderNumber",
        icon="mdi:receipt",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        quatt_features=QuattFeatureFlags(
            mobile_api=True,
        ),
    ),
    QuattSensorEntityDescription(
        name="Electricity night time start hour",
        key="electricityNightTimeStartHour",
        icon="mdi:clock-start",
        native_unit_of_measurement=UnitOfTime.HOURS,
        suggested_display_precision=0,
        quatt_features=QuattFeatureFlags(
            mobile_api=True,
        ),
    ),
    QuattSensorEntityDescription(
        name="Electricity night time end hour",
        key="electricityNightTimeEndHour",
        icon="mdi:clock-end",
        native_unit_of_measurement=UnitOfTime.HOURS,
        suggested_display_precision=0,
        quatt_features=QuattFeatureFlags(
            mobile_api=True,
        ),
    ),
    QuattSensorEntityDescription(
        name="Sound night time start hour",
        key="soundNightTimeStartHour",
        icon="mdi:clock-start",
        native_unit_of_measurement=UnitOfTime.HOURS,
        suggested_display_precision=0,
        quatt_features=QuattFeatureFlags(
            mobile_api=True,
        ),
    ),
    QuattSensorEntityDescription(
        name="Sound night time end hour",
        key="soundNightTimeEndHour",
        icon="mdi:clock-end",
        native_unit_of_measurement=UnitOfTime.HOURS,
        suggested_display_precision=0,
        quatt_features=QuattFeatureFlags(
            mobile_api=True,
        ),
    ),
    QuattSensorEntityDescription(
        name="Sound night time start min",
        key="soundNightTimeStartMin",
        icon="mdi:clock-start",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        suggested_display_precision=0,
        quatt_features=QuattFeatureFlags(
            mobile_api=True,
        ),
    ),
    QuattSensorEntityDescription(
        name="Sound night time end min",
        key="soundNightTimeEndMin",
        icon="mdi:clock-end",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        suggested_display_precision=0,
        quatt_features=QuattFeatureFlags(
            mobile_api=True,
        ),
    ),
]


BOILER_SENSORS: list[QuattSensorEntityDescription] = [
    QuattSensorEntityDescription(
        name="Temperature water inlet",
        key="boiler.otFbSupplyInletTemperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        quatt_features=QuattFeatureFlags(
            hybrid=True,
            opentherm=True,
        ),
    ),
    QuattSensorEntityDescription(
        name="Temperature water outlet",
        key="boiler.otFbSupplyOutletTemperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        quatt_features=QuattFeatureFlags(
            hybrid=True,
            opentherm=True,
        ),
    ),
    QuattSensorEntityDescription(
        name="Water pressure",
        key="boiler.otFbWaterPressure",
        icon="mdi:gauge",
        native_unit_of_measurement=UnitOfPressure.BAR,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        quatt_features=QuattFeatureFlags(
            hybrid=True,
            opentherm=True,
        ),
    ),
    QuattSensorEntityDescription(
        name="Heat power",
        key="boiler.computedBoilerHeatPower",
        icon="mdi:heat-wave",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        suggested_display_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
        quatt_features=QuattFeatureFlags(
            hybrid=True,
        ),
    ),
    QuattSensorEntityDescription(
        name="Boiler power",
        key="boilerPower",
        icon="mdi:fire",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        suggested_display_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
        quatt_features=QuattFeatureFlags(
            hybrid=True,
            mobile_api=True,
        ),
    ),
    QuattSensorEntityDescription(
        name="Boiler water temperature in",
        key="boilerWaterTemperatureIn",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        quatt_features=QuattFeatureFlags(
            hybrid=True,
            mobile_api=True,
        ),
    ),
    QuattSensorEntityDescription(
        name="Boiler water temperature out",
        key="boilerWaterTemperatureOut",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        quatt_features=QuattFeatureFlags(
            hybrid=True,
            mobile_api=True,
        ),
    ),
]


FLOWMETER_SENSORS: list[QuattSensorEntityDescription] = [
    QuattSensorEntityDescription(
        name="Temperature",
        key="flowMeter.waterSupplyTemperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    QuattSensorEntityDescription(
        name="Flowrate",
        key="qc.flowRateFiltered",
        icon="mdi:gauge",
        native_unit_of_measurement=UnitOfVolumeFlowRate.LITERS_PER_HOUR,
        suggested_display_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
    ),
]


THERMOSTAT_SENSORS: list[QuattSensorEntityDescription] = [
    QuattSensorEntityDescription(
        name="Control setpoint",
        key="thermostat.otFtControlSetpoint",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    QuattSensorEntityDescription(
        name="Room setpoint",
        key="thermostat.otFtRoomSetpoint",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=1,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    QuattSensorEntityDescription(
        name="Room temperature",
        key="thermostat.otFtRoomTemperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    QuattSensorEntityDescription(
        name="Temperature outside",
        key="temperatureOutside",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=1,
        state_class=SensorStateClass.MEASUREMENT,
        quatt_features=QuattFeatureFlags(
            mobile_api=True,
        ),
    ),
]


CIC_INSIGHTS_SENSORS: list[QuattSensorEntityDescription] = [
    QuattSensorEntityDescription(
        name="Total heat pump heat",
        key="insights.totalHpHeat",
        icon="mdi:heat-wave",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=0,
        state_class=SensorStateClass.TOTAL_INCREASING,
        quatt_features=QuattFeatureFlags(
            mobile_api=True,
        ),
    ),
    QuattSensorEntityDescription(
        name="Total heat pump electric",
        key="insights.totalHpElectric",
        icon="mdi:lightning-bolt",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=0,
        state_class=SensorStateClass.TOTAL_INCREASING,
        quatt_features=QuattFeatureFlags(
            mobile_api=True,
        ),
    ),
    QuattSensorEntityDescription(
        name="Total boiler heat",
        key="insights.totalBoilerHeat",
        icon="mdi:fire",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=0,
        state_class=SensorStateClass.TOTAL_INCREASING,
        quatt_features=QuattFeatureFlags(
            mobile_api=True,
        ),
    ),
    QuattSensorEntityDescription(
        name="Total boiler gas",
        key="insights.totalBoilerGas",
        icon="mdi:gas-cylinder",
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        device_class=SensorDeviceClass.GAS,
        suggested_display_precision=2,
        state_class=SensorStateClass.TOTAL_INCREASING,
        quatt_features=QuattFeatureFlags(
            mobile_api=True,
        ),
    ),
    QuattSensorEntityDescription(
        name="Average COP",
        key="insights.averageCOP",
        icon="mdi:heat-pump",
        native_unit_of_measurement="CoP",
        suggested_display_precision=1,
        state_class=SensorStateClass.MEASUREMENT,
        quatt_features=QuattFeatureFlags(
            mobile_api=True,
        ),
    ),
    QuattSensorEntityDescription(
        name="Savings money",
        key="insights.savingsMoney",
        icon="mdi:currency-eur",
        native_unit_of_measurement=CURRENCY_EURO,
        device_class=SensorDeviceClass.MONETARY,
        suggested_display_precision=2,
        state_class=SensorStateClass.TOTAL,
        quatt_features=QuattFeatureFlags(
            mobile_api=True,
        ),
    ),
    QuattSensorEntityDescription(
        name="Savings CO2",
        key="insights.savingsCo2",
        icon="mdi:molecule-co2",
        native_unit_of_measurement=UnitOfMass.KILOGRAMS,
        suggested_display_precision=2,
        state_class=SensorStateClass.TOTAL,
        quatt_features=QuattFeatureFlags(
            mobile_api=True,
        ),
    ),
    QuattSensorEntityDescription(
        name="Savings gas",
        key="insights.savingsGas",
        icon="mdi:gas-cylinder",
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        device_class=SensorDeviceClass.GAS,
        suggested_display_precision=2,
        state_class=SensorStateClass.TOTAL,
        quatt_features=QuattFeatureFlags(
            mobile_api=True,
        ),
    ),
    QuattSensorEntityDescription(
        name="Savings gas money",
        key="insights.savingsGasMoney",
        icon="mdi:currency-eur",
        native_unit_of_measurement=CURRENCY_EURO,
        device_class=SensorDeviceClass.MONETARY,
        suggested_display_precision=2,
        state_class=SensorStateClass.TOTAL,
        quatt_features=QuattFeatureFlags(
            mobile_api=True,
        ),
    ),
    QuattSensorEntityDescription(
        name="Savings Quatt electricity cost",
        key="insights.savingsQuattElectricityCost",
        icon="mdi:currency-eur",
        native_unit_of_measurement=CURRENCY_EURO,
        device_class=SensorDeviceClass.MONETARY,
        suggested_display_precision=2,
        state_class=SensorStateClass.TOTAL,
        quatt_features=QuattFeatureFlags(
            mobile_api=True,
        ),
    ),
    QuattSensorEntityDescription(
        name="CO2 gas saved",
        key="insights.co2GasSaved",
        icon="mdi:molecule-co2",
        native_unit_of_measurement=UnitOfMass.KILOGRAMS,
        suggested_display_precision=2,
        state_class=SensorStateClass.TOTAL,
        quatt_features=QuattFeatureFlags(
            mobile_api=True,
        ),
    ),
    QuattSensorEntityDescription(
        name="CO2 electricity",
        key="insights.co2Electricity",
        icon="mdi:molecule-co2",
        native_unit_of_measurement=UnitOfMass.KILOGRAMS,
        suggested_display_precision=2,
        state_class=SensorStateClass.TOTAL,
        quatt_features=QuattFeatureFlags(
            mobile_api=True,
        ),
    ),
]
