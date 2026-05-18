"""Home battery sensor descriptions for Quatt."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    CURRENCY_EURO,
    PERCENTAGE,
    EntityCategory,
    UnitOfEnergy,
    UnitOfPower,
)

from .entity import QuattSensorEntityDescription


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
    state_class: SensorStateClass = SensorStateClass.TOTAL,
    enabled: bool = True,
    diagnostic: bool = False,
) -> QuattSensorEntityDescription:
    """Build a monetary savings sensor description."""
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
    _savings_money_sensor(
        "savings.yesterday.totalSavingsEurInclVat",
        "Yesterday total savings",
    ),
    _savings_money_sensor(
        "savings.yesterday.homeBatterySavingsEurInclVat",
        "Yesterday home battery savings",
    ),
    _savings_money_sensor(
        "savings.yesterday.solarSavingsEurInclVat",
        "Yesterday solar savings",
    ),
    _savings_money_sensor(
        "savings.yesterday.imbalanceSavingsEurInclVat",
        "Yesterday imbalance savings",
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
    """Build a kWh energy-flow sensor description."""
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
