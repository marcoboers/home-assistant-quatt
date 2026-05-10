"""Sensor platform for quatt."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    DOMAIN as SENSOR_DOMAIN,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    CURRENCY_EURO,
    PERCENTAGE,
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
from homeassistant.core import HomeAssistant

from .const import (
    DEVICE_BOILER_ID,
    DEVICE_CIC_ID,
    DEVICE_FLOWMETER_ID,
    DEVICE_HEAT_BATTERY_ID,
    DEVICE_HEAT_CHARGER_ID,
    DEVICE_HEATPUMP_1_ID,
    DEVICE_HEATPUMP_2_ID,
    DEVICE_HOME_BATTERY_ENERGY_FLOW_ID,
    DEVICE_HOME_BATTERY_ID,
    DEVICE_HOME_BATTERY_INSIGHTS_ID,
    DEVICE_HOME_BATTERY_SAVINGS_ID,
    DEVICE_CIC_INSIGHTS_ID,
    DEVICE_THERMOSTAT_ID,
    DOMAIN,
    QuattDeviceKind,
)
from .coordinator import QuattDataUpdateCoordinator
from .entity import (
    QuattFeatureFlags,
    QuattSensor,
    QuattSensorEntityDescription,
    QuattSystemSensor,
)
from .entity_setup import async_setup_entities


def create_heatpump_sensor_entity_descriptions(
    index: int, is_duo: bool = False
) -> list[QuattSensorEntityDescription]:
    """Create the heatpump sensor entity descriptions based on the index."""
    prefix = "hp1" if index == 0 else "hp2"

    return [
        QuattSensorEntityDescription(
            name="Workingmode",
            key=f"{prefix}.getMainWorkingMode",
            icon="mdi:auto-mode",
            quatt_features=QuattFeatureFlags(
                duo=is_duo,
            ),
        ),
        QuattSensorEntityDescription(
            name="Temperature outside",
            key=f"{prefix}.temperatureOutside",
            icon="mdi:thermometer",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            suggested_display_precision=2,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_features=QuattFeatureFlags(
                duo=is_duo,
            ),
        ),
        QuattSensorEntityDescription(
            name="Temperature water in",
            key=f"{prefix}.temperatureWaterIn",
            icon="mdi:thermometer",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            suggested_display_precision=2,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_features=QuattFeatureFlags(
                duo=is_duo,
            ),
        ),
        QuattSensorEntityDescription(
            name="Temperature water out",
            key=f"{prefix}.temperatureWaterOut",
            icon="mdi:thermometer",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            suggested_display_precision=2,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_features=QuattFeatureFlags(
                duo=is_duo,
            ),
        ),
        QuattSensorEntityDescription(
            name="Water delta",
            key=f"{prefix}.computedWaterDelta",
            icon="mdi:thermometer-water",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            suggested_display_precision=2,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_features=QuattFeatureFlags(
                duo=is_duo,
            ),
        ),
        QuattSensorEntityDescription(
            name="Power input",
            key=f"{prefix}.powerInput",
            icon="mdi:lightning-bolt",
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            suggested_display_precision=0,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_features=QuattFeatureFlags(
                duo=is_duo,
            ),
        ),
        QuattSensorEntityDescription(
            name="Power",
            key=f"{prefix}.power",
            icon="mdi:heat-wave",
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            suggested_display_precision=0,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_features=QuattFeatureFlags(
                duo=is_duo,
            ),
        ),
        QuattSensorEntityDescription(
            name="Quatt COP",
            key=f"{prefix}.computedQuattCop",
            icon="mdi:heat-pump",
            native_unit_of_measurement="CoP",
            suggested_display_precision=2,
            state_class="measurement",
            quatt_features=QuattFeatureFlags(
                duo=is_duo,
            ),
        ),
        QuattSensorEntityDescription(
            name="Modbus slave ID",
            key=f"{prefix}.modbusSlaveId",
            icon="mdi:identifier",
            entity_category=EntityCategory.DIAGNOSTIC,
            quatt_features=QuattFeatureFlags(
                duo=is_duo,
            ),
        ),
        QuattSensorEntityDescription(
            name="Compressor frequency",
            key=f"heatPumps.{index}.compressorFrequency",
            icon="mdi:sine-wave",
            native_unit_of_measurement="Hz",
            suggested_display_precision=0,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_features=QuattFeatureFlags(
                duo=is_duo,
                mobile_api=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Compressor frequency demand",
            key=f"heatPumps.{index}.compressorFrequencyDemand",
            icon="mdi:sine-wave",
            native_unit_of_measurement="Hz",
            suggested_display_precision=0,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_features=QuattFeatureFlags(
                duo=is_duo,
                mobile_api=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Minimum power",
            key=f"heatPumps.{index}.minimumPower",
            icon="mdi:lightning-bolt",
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            suggested_display_precision=0,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_features=QuattFeatureFlags(
                duo=is_duo,
                mobile_api=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Electrical power",
            key=f"heatPumps.{index}.electricalPower",
            icon="mdi:lightning-bolt",
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            suggested_display_precision=2,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_features=QuattFeatureFlags(
                duo=is_duo,
                mobile_api=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Rated power",
            key=f"heatPumps.{index}.ratedPower",
            icon="mdi:gauge",
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            suggested_display_precision=2,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_features=QuattFeatureFlags(
                duo=is_duo,
                mobile_api=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Expected power",
            key=f"heatPumps.{index}.expectedPower",
            icon="mdi:lightning-bolt-outline",
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            suggested_display_precision=0,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_features=QuattFeatureFlags(
                duo=is_duo,
                mobile_api=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Status",
            key=f"heatPumps.{index}.status",
            icon="mdi:information",
            entity_category=EntityCategory.DIAGNOSTIC,
            quatt_features=QuattFeatureFlags(
                duo=is_duo,
                mobile_api=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Water pump level",
            key=f"heatPumps.{index}.waterPumpLevel",
            icon="mdi:pump",
            suggested_display_precision=0,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_features=QuattFeatureFlags(
                duo=is_duo,
                mobile_api=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="ODU type",
            key=f"heatPumps.{index}.oduType",
            icon="mdi:hvac",
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
            quatt_features=QuattFeatureFlags(
                duo=is_duo,
                mobile_api=True,
            ),
        ),
    ]


SENSORS = {
    # The HUB CIC sensor must be created first to ensure the HUB device is present
    DEVICE_CIC_ID: [
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
        # Electricity and gas prices and tariffs
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
        # System
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
    ],
    DEVICE_HEAT_BATTERY_ID: [
        QuattSensorEntityDescription(
            name="Shower minutes remaining",
            key="hb.showerMinutes",
            icon="mdi:shower",
            native_unit_of_measurement="min",
            suggested_display_precision=0,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_features=QuattFeatureFlags(
                all_electric=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Top temperature",
            key="hb.topTemperature",
            icon="mdi:thermometer",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            suggested_display_precision=2,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_features=QuattFeatureFlags(
                all_electric=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Middle temperature",
            key="hb.middleTemperature",
            icon="mdi:thermometer",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            suggested_display_precision=2,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_features=QuattFeatureFlags(
                all_electric=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Bottom temperature",
            key="hb.bottomTemperature",
            icon="mdi:thermometer",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            suggested_display_precision=2,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_features=QuattFeatureFlags(
                all_electric=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Serial number",
            key="allEStatus.heatBatterySerialNumber",
            icon="mdi:identifier",
            entity_category=EntityCategory.DIAGNOSTIC,
            quatt_features=QuattFeatureFlags(
                all_electric=True,
                mobile_api=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Status",
            key="allEStatus.heatBatteryStatus",
            icon="mdi:battery",
            entity_category=EntityCategory.DIAGNOSTIC,
            quatt_features=QuattFeatureFlags(
                all_electric=True,
                mobile_api=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Size",
            key="allEStatus.heatBatterySize",
            icon="mdi:battery-high",
            entity_category=EntityCategory.DIAGNOSTIC,
            quatt_features=QuattFeatureFlags(
                all_electric=True,
                mobile_api=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Percentage",
            key="allEStatus.heatBatteryPercentage",
            device_class=SensorDeviceClass.BATTERY,
            native_unit_of_measurement=PERCENTAGE,
            suggested_display_precision=0,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_features=QuattFeatureFlags(
                all_electric=True,
                mobile_api=True,
            ),
        ),
    ],
    DEVICE_HEAT_CHARGER_ID: [
        QuattSensorEntityDescription(
            name="Electrical power",
            key="hc.electricalPower",
            icon="mdi:lightning-bolt",
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            suggested_display_precision=0,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_features=QuattFeatureFlags(
                all_electric=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Heat exchanger inlet temperature",
            key="hc.chHeatExchangerInletTemperature",
            icon="mdi:thermometer",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            suggested_display_precision=2,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_features=QuattFeatureFlags(
                all_electric=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Heating system pressure",
            key="hc.heatingSystemPressure",
            icon="mdi:gauge",
            native_unit_of_measurement=UnitOfPressure.BAR,
            suggested_display_precision=2,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_features=QuattFeatureFlags(
                all_electric=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Distribution system supply temperature",
            key="hc.distributionSystemSupplyTemperature",
            icon="mdi:thermometer",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            suggested_display_precision=2,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_features=QuattFeatureFlags(
                all_electric=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Serial number",
            key="allEStatus.heatChargerSerialNumber",
            icon="mdi:identifier",
            entity_category=EntityCategory.DIAGNOSTIC,
            quatt_features=QuattFeatureFlags(
                all_electric=True,
                mobile_api=True,
            ),
        ),
    ],
    DEVICE_HEATPUMP_1_ID: create_heatpump_sensor_entity_descriptions(
        index=0, is_duo=False
    ),
    DEVICE_HEATPUMP_2_ID: create_heatpump_sensor_entity_descriptions(
        index=1, is_duo=True
    ),
    DEVICE_BOILER_ID: [
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
    ],
    DEVICE_FLOWMETER_ID: [
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
    ],
    DEVICE_THERMOSTAT_ID: [
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
    ],
    DEVICE_CIC_INSIGHTS_ID: [
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
    ],
}

HOME_BATTERY_SENSORS: list[QuattSensorEntityDescription] = [
    QuattSensorEntityDescription(
        key="live.chargeStatePercent",
        name="State of charge",
        icon="mdi:battery",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    QuattSensorEntityDescription(
        key="live.powerKw",
        name="Power",
        icon="mdi:flash",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        suggested_display_precision=3,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    QuattSensorEntityDescription(
        key="live.powerFlowDirection",
        name="Power flow direction",
        icon="mdi:transmission-tower",
    ),
    QuattSensorEntityDescription(
        key="live.controlAction",
        name="Control action",
        icon="mdi:state-machine",
    ),
    QuattSensorEntityDescription(
        key="controlMode",
        name="Control mode",
        icon="mdi:tune",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    QuattSensorEntityDescription(
        key="capacityKWh",
        name="Capacity",
        icon="mdi:battery-high",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY_STORAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    QuattSensorEntityDescription(
        key="inverterPowerKw",
        name="Inverter power",
        icon="mdi:current-ac",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    QuattSensorEntityDescription(
        key="serial",
        name="Serial",
        icon="mdi:identifier",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    QuattSensorEntityDescription(
        key="lastMeasurementAt",
        name="Last measurement",
        icon="mdi:clock-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
]


def _savings_money_sensor(
    key: str,
    name: str,
    *,
    icon: str = "mdi:currency-eur",
    state_class: SensorStateClass = SensorStateClass.TOTAL_INCREASING,
    enabled: bool = True,
    diagnostic: bool = False,
) -> QuattSensorEntityDescription:
    """Build a monetary savings sensor description (value in euros)."""
    return QuattSensorEntityDescription(
        key=key,
        name=name,
        icon=icon,
        native_unit_of_measurement=CURRENCY_EURO,
        device_class=SensorDeviceClass.MONETARY,
        suggested_display_precision=2,
        state_class=state_class,
        entity_registry_enabled_default=enabled,
        entity_category=EntityCategory.DIAGNOSTIC if diagnostic else None,
    )


HOME_BATTERY_SAVINGS_SENSORS: list[QuattSensorEntityDescription] = [
    # Cumulative savings (totals since install) - incl VAT (primary display)
    _savings_money_sensor(
        "savings.cumulative.totalSavingsEurInclVat",
        "Total savings",
    ),
    _savings_money_sensor(
        "savings.cumulative.homeBatterySavingsEurInclVat",
        "Home battery savings",
    ),
    _savings_money_sensor(
        "savings.cumulative.solarSavingsEurInclVat",
        "Solar savings",
    ),
    _savings_money_sensor(
        "savings.cumulative.imbalanceSavingsEurInclVat",
        "Imbalance savings",
    ),
    _savings_money_sensor(
        "savings.cumulative.totalSavingsWithoutSolarEurInclVat",
        "Total savings without solar",
        enabled=False,
    ),
    # Cumulative - excl VAT (diagnostic, disabled by default)
    _savings_money_sensor(
        "savings.cumulative.totalSavingsEurExclVat",
        "Total savings (excl. VAT)",
        enabled=False,
        diagnostic=True,
    ),
    _savings_money_sensor(
        "savings.cumulative.homeBatterySavingsEurExclVat",
        "Home battery savings (excl. VAT)",
        enabled=False,
        diagnostic=True,
    ),
    _savings_money_sensor(
        "savings.cumulative.solarSavingsEurExclVat",
        "Solar savings (excl. VAT)",
        enabled=False,
        diagnostic=True,
    ),
    _savings_money_sensor(
        "savings.cumulative.imbalanceSavingsEurExclVat",
        "Imbalance savings (excl. VAT)",
        enabled=False,
        diagnostic=True,
    ),
    # Yesterday (reset daily → MEASUREMENT state class)
    _savings_money_sensor(
        "savings.yesterday.totalSavingsEurInclVat",
        "Yesterday total savings",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    _savings_money_sensor(
        "savings.yesterday.homeBatterySavingsEurInclVat",
        "Yesterday home battery savings",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    _savings_money_sensor(
        "savings.yesterday.solarSavingsEurInclVat",
        "Yesterday solar savings",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    _savings_money_sensor(
        "savings.yesterday.imbalanceSavingsEurInclVat",
        "Yesterday imbalance savings",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    QuattSensorEntityDescription(
        key="savings.cumulative.avgVatPercent",
        name="Average VAT percentage",
        icon="mdi:percent",
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    QuattSensorEntityDescription(
        key="savings.lastUpdatedAt",
        name="Last updated",
        icon="mdi:clock-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
]


HOME_BATTERY_INSIGHTS_SENSORS: list[QuattSensorEntityDescription] = [
    QuattSensorEntityDescription(
        key="insights.totalChargedKwh",
        name="Energy charged today",
        icon="mdi:battery-plus",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    QuattSensorEntityDescription(
        key="insights.totalDischargedKwh",
        name="Energy discharged today",
        icon="mdi:battery-minus",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    QuattSensorEntityDescription(
        key="insights.peakChargeKw",
        name="Peak charge power today",
        icon="mdi:flash",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        suggested_display_precision=3,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    QuattSensorEntityDescription(
        key="insights.peakDischargeKw",
        name="Peak discharge power today",
        icon="mdi:flash-outline",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        suggested_display_precision=3,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    QuattSensorEntityDescription(
        key="insights.maxChargeStatePercent",
        name="Highest SoC today",
        icon="mdi:battery-high",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    QuattSensorEntityDescription(
        key="insights.minChargeStatePercent",
        name="Lowest SoC today",
        icon="mdi:battery-low",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    QuattSensorEntityDescription(
        key="insights.dataPoints",
        name="Data points today",
        icon="mdi:counter",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    QuattSensorEntityDescription(
        key="insights.latestTimestamp",
        name="Latest insights timestamp",
        icon="mdi:clock-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
]


def _energy_flow_sensor(
    key: str,
    name: str,
    icon: str,
) -> QuattSensorEntityDescription:
    """Build a kWh energy-flow sensor description for the aggregated day total."""
    return QuattSensorEntityDescription(
        key=key,
        name=name,
        icon=icon,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        state_class=SensorStateClass.TOTAL_INCREASING,
    )


HOME_BATTERY_ENERGY_FLOW_SENSORS: list[QuattSensorEntityDescription] = [
    _energy_flow_sensor(
        "energyFlow.batteryChargedKWh",
        "Battery charged today",
        "mdi:battery-plus",
    ),
    _energy_flow_sensor(
        "energyFlow.batteryDischargedKWh",
        "Battery discharged today",
        "mdi:battery-minus",
    ),
    _energy_flow_sensor(
        "energyFlow.solarProductionKWh",
        "Solar production today",
        "mdi:solar-power",
    ),
    _energy_flow_sensor(
        "energyFlow.houseConsumptionKWh",
        "House consumption today",
        "mdi:home-lightning-bolt",
    ),
    _energy_flow_sensor(
        "energyFlow.gridImportKWh",
        "Grid import today",
        "mdi:transmission-tower-import",
    ),
    _energy_flow_sensor(
        "energyFlow.gridExportKWh",
        "Grid export today",
        "mdi:transmission-tower-export",
    ),
    QuattSensorEntityDescription(
        key="energyFlow.periodKey",
        name="Energy flow period",
        icon="mdi:calendar",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    QuattSensorEntityDescription(
        key="energyFlow.periodTo",
        name="Energy flow period end",
        icon="mdi:clock-end",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
]


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_devices):
    """Set up the sensor platform."""
    coordinators = hass.data[DOMAIN][entry.entry_id]

    local_coordinator: QuattDataUpdateCoordinator | None = coordinators.get("cic_local")
    remote_coordinator: QuattDataUpdateCoordinator | None = coordinators.get("cic_remote")
    home_battery_coordinator: QuattDataUpdateCoordinator | None = coordinators.get(
        "home_battery"
    )

    sensors: list[QuattSensor] = []

    if local_coordinator is not None:
        sensors += await async_setup_entities(
            hass=hass,
            coordinator=local_coordinator,
            entry=entry,
            remote=False,
            entity_descriptions=SENSORS,
            entity_domain=SENSOR_DOMAIN,
        )

    if remote_coordinator:
        sensors += await async_setup_entities(
            hass=hass,
            coordinator=remote_coordinator,
            entry=entry,
            remote=True,
            entity_descriptions=SENSORS,
            entity_domain=SENSOR_DOMAIN,
        )

    if home_battery_coordinator is not None:
        for desc in HOME_BATTERY_SENSORS:
            sensors.append(
                QuattSensor(
                    device_name="Home battery",
                    device_id=DEVICE_HOME_BATTERY_ID,
                    sensor_key=desc.key,
                    coordinator=home_battery_coordinator,
                    entity_description=desc,
                    device_kind=QuattDeviceKind.HUB,
                )
            )
        for desc in HOME_BATTERY_SAVINGS_SENSORS:
            sensors.append(
                QuattSensor(
                    device_name="Savings",
                    device_id=DEVICE_HOME_BATTERY_SAVINGS_ID,
                    sensor_key=desc.key,
                    coordinator=home_battery_coordinator,
                    entity_description=desc,
                    device_kind=QuattDeviceKind.SERVICE,
                )
            )
        for desc in HOME_BATTERY_INSIGHTS_SENSORS:
            sensors.append(
                QuattSensor(
                    device_name="Insights",
                    device_id=DEVICE_HOME_BATTERY_INSIGHTS_ID,
                    sensor_key=desc.key,
                    coordinator=home_battery_coordinator,
                    entity_description=desc,
                    device_kind=QuattDeviceKind.SERVICE,
                )
            )
        for desc in HOME_BATTERY_ENERGY_FLOW_SENSORS:
            sensors.append(
                QuattSensor(
                    device_name="Energy flow",
                    device_id=DEVICE_HOME_BATTERY_ENERGY_FLOW_ID,
                    sensor_key=desc.key,
                    coordinator=home_battery_coordinator,
                    entity_description=desc,
                    device_kind=QuattDeviceKind.SERVICE,
                )
            )

    async_add_devices(sensors)
