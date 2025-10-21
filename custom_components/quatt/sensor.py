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
    DEVICE_THERMOSTAT_ID,
    DOMAIN,
)
from .coordinator import QuattDataUpdateCoordinator
from .entity import QuattFeatureFlags, QuattSensor, QuattSensorEntityDescription
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
            features=QuattFeatureFlags(
                quatt_duo=is_duo,
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
            features=QuattFeatureFlags(
                quatt_duo=is_duo,
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
            features=QuattFeatureFlags(
                quatt_duo=is_duo,
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
            features=QuattFeatureFlags(
                quatt_duo=is_duo,
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
            features=QuattFeatureFlags(
                quatt_duo=is_duo,
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
            features=QuattFeatureFlags(
                quatt_duo=is_duo,
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
            features=QuattFeatureFlags(
                quatt_duo=is_duo,
            ),
        ),
        QuattSensorEntityDescription(
            name="Quatt COP",
            key=f"{prefix}.computedQuattCop",
            icon="mdi:heat-pump",
            native_unit_of_measurement="CoP",
            suggested_display_precision=2,
            state_class="measurement",
            features=QuattFeatureFlags(
                quatt_duo=is_duo,
            ),
        ),
        QuattSensorEntityDescription(
            name="Modbus slave ID",
            key=f"{prefix}.modbusSlaveId",
            icon="mdi:identifier",
            entity_category=EntityCategory.DIAGNOSTIC,
            features=QuattFeatureFlags(
                quatt_duo=is_duo,
            ),
        ),
        QuattSensorEntityDescription(
            name="On",
            key=f"heatPumps.{index}.on",
            icon="mdi:power",
            features=QuattFeatureFlags(
                quatt_duo=is_duo,
                quatt_mobile_api=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Compressor frequency",
            key=f"heatPumps.{index}.compressorFrequency",
            icon="mdi:sine-wave",
            native_unit_of_measurement="Hz",
            suggested_display_precision=0,
            state_class=SensorStateClass.MEASUREMENT,
            features=QuattFeatureFlags(
                quatt_duo=is_duo,
                quatt_mobile_api=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Compressor frequency demand",
            key=f"heatPumps.{index}.compressorFrequencyDemand",
            icon="mdi:sine-wave",
            native_unit_of_measurement="Hz",
            suggested_display_precision=0,
            state_class=SensorStateClass.MEASUREMENT,
            features=QuattFeatureFlags(
                quatt_duo=is_duo,
                quatt_mobile_api=True,
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
            features=QuattFeatureFlags(
                quatt_duo=is_duo,
                quatt_mobile_api=True,
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
            features=QuattFeatureFlags(
                quatt_duo=is_duo,
                quatt_mobile_api=True,
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
            features=QuattFeatureFlags(
                quatt_duo=is_duo,
                quatt_mobile_api=True,
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
            features=QuattFeatureFlags(
                quatt_duo=is_duo,
                quatt_mobile_api=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Status",
            key=f"heatPumps.{index}.status",
            icon="mdi:information",
            entity_category=EntityCategory.DIAGNOSTIC,
            features=QuattFeatureFlags(
                quatt_duo=is_duo,
                quatt_mobile_api=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Water pump level",
            key=f"heatPumps.{index}.waterPumpLevel",
            icon="mdi:pump",
            suggested_display_precision=0,
            state_class=SensorStateClass.MEASUREMENT,
            features=QuattFeatureFlags(
                quatt_duo=is_duo,
                quatt_mobile_api=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="ODU type",
            key=f"heatPumps.{index}.oduType",
            icon="mdi:hvac",
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
            features=QuattFeatureFlags(
                quatt_duo=is_duo,
                quatt_mobile_api=True,
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
            features=QuattFeatureFlags(
                quatt_duo=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Total power",
            key="computedPower",
            icon="mdi:heat-wave",
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            suggested_display_precision=0,
            state_class=SensorStateClass.MEASUREMENT,
            features=QuattFeatureFlags(
                quatt_duo=True,
            ),
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
            features=QuattFeatureFlags(
                quatt_duo=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Total Quatt COP",
            key="computedQuattCop",
            icon="mdi:heat-pump",
            native_unit_of_measurement="CoP",
            suggested_display_precision=2,
            state_class=SensorStateClass.MEASUREMENT,
            features=QuattFeatureFlags(
                quatt_duo=True,
            ),
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
            features=QuattFeatureFlags(
                quatt_all_electric=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="QC All-Electric supervisory control mode",
            key="qcAllE.computedAllESupervisoryControlMode",
            features=QuattFeatureFlags(
                quatt_all_electric=True,
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
            name="System hostname",
            key="system.hostName",
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        QuattSensorEntityDescription(
            name="Installation ID",
            key="installationId",
            icon="mdi:identifier",
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
            features=QuattFeatureFlags(
                quatt_mobile_api=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Installed at",
            key="installedAt",
            device_class=SensorDeviceClass.TIMESTAMP,
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
            features=QuattFeatureFlags(
                quatt_mobile_api=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Status",
            key="status",
            icon="mdi:information",
            entity_category=EntityCategory.DIAGNOSTIC,
            features=QuattFeatureFlags(
                quatt_mobile_api=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Cable connection status",
            key="cableConnectionStatus",
            icon="mdi:ethernet",
            entity_category=EntityCategory.DIAGNOSTIC,
            features=QuattFeatureFlags(
                quatt_mobile_api=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="LTE connection status",
            key="lteConnectionStatus",
            icon="mdi:signal",
            entity_category=EntityCategory.DIAGNOSTIC,
            features=QuattFeatureFlags(
                quatt_mobile_api=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="WiFi connection status",
            key="wifiConnectionStatus",
            icon="mdi:wifi",
            entity_category=EntityCategory.DIAGNOSTIC,
            features=QuattFeatureFlags(
                quatt_mobile_api=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="WiFi SSID",
            key="wifiSSID",
            icon="mdi:wifi",
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
            features=QuattFeatureFlags(
                quatt_mobile_api=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Electricity price",
            key="electricityPrice",
            icon="mdi:currency-eur",
            native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
            suggested_display_precision=2,
            state_class=SensorStateClass.MEASUREMENT,
            features=QuattFeatureFlags(
                quatt_mobile_api=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Day electricity price",
            key="dayElectricityPrice",
            icon="mdi:currency-eur",
            native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
            suggested_display_precision=2,
            state_class=SensorStateClass.MEASUREMENT,
            features=QuattFeatureFlags(
                quatt_mobile_api=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Night electricity price",
            key="nightElectricityPrice",
            icon="mdi:currency-eur",
            native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
            suggested_display_precision=2,
            state_class=SensorStateClass.MEASUREMENT,
            features=QuattFeatureFlags(
                quatt_mobile_api=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Gas price",
            key="gasPrice",
            icon="mdi:currency-eur",
            native_unit_of_measurement=f"{CURRENCY_EURO}/m³",
            suggested_display_precision=2,
            state_class=SensorStateClass.MEASUREMENT,
            features=QuattFeatureFlags(
                quatt_mobile_api=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Silent mode",
            key="silentMode",
            icon="mdi:sleep",
            features=QuattFeatureFlags(
                quatt_mobile_api=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Supervisory control mode",
            key="supervisoryControlMode",
            icon="mdi:cog",
            features=QuattFeatureFlags(
                quatt_mobile_api=True,
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
            features=QuattFeatureFlags(
                quatt_mobile_api=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Insights start at",
            key="insightsStartAt",
            device_class=SensorDeviceClass.TIMESTAMP,
            entity_category=EntityCategory.DIAGNOSTIC,
            features=QuattFeatureFlags(
                quatt_mobile_api=True,
            ),
            entity_registry_enabled_default=False,
        ),
        QuattSensorEntityDescription(
            name="Quatt build",
            key="quattBuild",
            icon="mdi:package-variant",
            entity_category=EntityCategory.DIAGNOSTIC,
            features=QuattFeatureFlags(
                quatt_mobile_api=True,
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
            features=QuattFeatureFlags(
                quatt_mobile_api=True,
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
            features=QuattFeatureFlags(
                quatt_mobile_api=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Name",
            key="name",
            icon="mdi:label",
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
            features=QuattFeatureFlags(
                quatt_mobile_api=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Zip code",
            key="zipCode",
            icon="mdi:map-marker",
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
            features=QuattFeatureFlags(
                quatt_mobile_api=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Country",
            key="country",
            icon="mdi:flag",
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
            features=QuattFeatureFlags(
                quatt_mobile_api=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Order number",
            key="orderNumber",
            icon="mdi:receipt",
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
            features=QuattFeatureFlags(
                quatt_mobile_api=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Electricity night time start hour",
            key="electricityNightTimeStartHour",
            icon="mdi:clock-start",
            native_unit_of_measurement=UnitOfTime.HOURS,
            suggested_display_precision=0,
            features=QuattFeatureFlags(
                quatt_mobile_api=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Electricity night time end hour",
            key="electricityNightTimeEndHour",
            icon="mdi:clock-end",
            native_unit_of_measurement=UnitOfTime.HOURS,
            suggested_display_precision=0,
            features=QuattFeatureFlags(
                quatt_mobile_api=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Sound night time start hour",
            key="soundNightTimeStartHour",
            icon="mdi:clock-start",
            native_unit_of_measurement=UnitOfTime.HOURS,
            suggested_display_precision=0,
            features=QuattFeatureFlags(
                quatt_mobile_api=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Sound night time end hour",
            key="soundNightTimeEndHour",
            icon="mdi:clock-end",
            native_unit_of_measurement=UnitOfTime.HOURS,
            suggested_display_precision=0,
            features=QuattFeatureFlags(
                quatt_mobile_api=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Sound night time start min",
            key="soundNightTimeStartMin",
            icon="mdi:clock-start",
            native_unit_of_measurement=UnitOfTime.MINUTES,
            suggested_display_precision=0,
            features=QuattFeatureFlags(
                quatt_mobile_api=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Sound night time end min",
            key="soundNightTimeEndMin",
            icon="mdi:clock-end",
            native_unit_of_measurement=UnitOfTime.MINUTES,
            suggested_display_precision=0,
            features=QuattFeatureFlags(
                quatt_mobile_api=True,
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
            features=QuattFeatureFlags(
                quatt_all_electric=True,
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
            features=QuattFeatureFlags(
                quatt_all_electric=True,
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
            features=QuattFeatureFlags(
                quatt_all_electric=True,
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
            features=QuattFeatureFlags(
                quatt_all_electric=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Serial number",
            key="allEStatus.heatBatterySerialNumber",
            icon="mdi:identifier",
            entity_category=EntityCategory.DIAGNOSTIC,
            features=QuattFeatureFlags(
                quatt_all_electric=True,
                quatt_mobile_api=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Status",
            key="allEStatus.heatBatteryStatus",
            icon="mdi:battery",
            entity_category=EntityCategory.DIAGNOSTIC,
            features=QuattFeatureFlags(
                quatt_all_electric=True,
                quatt_mobile_api=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Size",
            key="allEStatus.heatBatterySize",
            icon="mdi:battery-high",
            entity_category=EntityCategory.DIAGNOSTIC,
            features=QuattFeatureFlags(
                quatt_all_electric=True,
                quatt_mobile_api=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Percentage",
            key="allEStatus.heatBatteryPercentage",
            device_class=SensorDeviceClass.BATTERY,
            native_unit_of_measurement=PERCENTAGE,
            suggested_display_precision=0,
            state_class=SensorStateClass.MEASUREMENT,
            features=QuattFeatureFlags(
                quatt_all_electric=True,
                quatt_mobile_api=True,
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
            features=QuattFeatureFlags(
                quatt_all_electric=True,
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
            features=QuattFeatureFlags(
                quatt_all_electric=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Heating system pressure",
            key="hc.heatingSystemPressure",
            icon="mdi:gauge",
            native_unit_of_measurement=UnitOfPressure.BAR,
            suggested_display_precision=2,
            state_class=SensorStateClass.MEASUREMENT,
            features=QuattFeatureFlags(
                quatt_all_electric=True,
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
            features=QuattFeatureFlags(
                quatt_all_electric=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Serial number",
            key="allEStatus.heatChargerSerialNumber",
            icon="mdi:identifier",
            entity_category=EntityCategory.DIAGNOSTIC,
            features=QuattFeatureFlags(
                quatt_all_electric=True,
                quatt_mobile_api=True,
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
            features=QuattFeatureFlags(
                quatt_hybrid=True,
                quatt_opentherm=True,
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
            features=QuattFeatureFlags(
                quatt_hybrid=True,
                quatt_opentherm=True,
            ),
        ),
        QuattSensorEntityDescription(
            name="Water pressure",
            key="boiler.otFbWaterPressure",
            icon="mdi:gauge",
            native_unit_of_measurement=UnitOfPressure.BAR,
            suggested_display_precision=2,
            state_class=SensorStateClass.MEASUREMENT,
            features=QuattFeatureFlags(
                quatt_hybrid=True,
                quatt_opentherm=True,
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
            features=QuattFeatureFlags(
                quatt_hybrid=True,
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
            features=QuattFeatureFlags(
                quatt_hybrid=True,
                quatt_mobile_api=True,
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
            features=QuattFeatureFlags(
                quatt_hybrid=True,
                quatt_mobile_api=True,
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
            features=QuattFeatureFlags(
                quatt_hybrid=True,
                quatt_mobile_api=True,
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
            features=QuattFeatureFlags(
                quatt_mobile_api=True,
            ),
        ),
    ],
}

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_devices):
    """Set up the sensor platform."""
    coordinators = hass.data[DOMAIN][entry.entry_id]

    local_coordinator: QuattDataUpdateCoordinator = coordinators["local"]
    remote_coordinator: QuattDataUpdateCoordinator = coordinators["remote"]

    sensors: list[QuattSensor] = []
    sensors += await async_setup_entities(
        hass=hass,
        coordinator=local_coordinator,
        entry=entry,
        remote=False,
        entity_class=QuattSensor,
        entity_descriptions=SENSORS,
        entity_domain=SENSOR_DOMAIN,
    )

    if remote_coordinator:
        sensors += await async_setup_entities(
            hass=hass,
            coordinator=remote_coordinator,
            entry=entry,
            remote=True,
            entity_class=QuattSensor,
            entity_descriptions=SENSORS,
            entity_domain=SENSOR_DOMAIN,
        )

    async_add_devices(sensors)
