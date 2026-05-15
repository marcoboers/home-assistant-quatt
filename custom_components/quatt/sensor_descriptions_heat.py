"""Heat-related sensor descriptions for Quatt."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    EntityCategory,
    PERCENTAGE,
    UnitOfPower,
    UnitOfPressure,
    UnitOfTemperature,
)

from .entity import QuattFeatureFlags, QuattSensorEntityDescription


def create_heatpump_sensor_entity_descriptions(
    index: int, is_duo: bool = False
) -> list[QuattSensorEntityDescription]:
    """Create the heat pump sensor entity descriptions based on the index."""
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


HEAT_BATTERY_SENSORS: list[QuattSensorEntityDescription] = [
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
]


HEAT_CHARGER_SENSORS: list[QuattSensorEntityDescription] = [
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
]
