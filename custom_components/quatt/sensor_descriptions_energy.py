"""Energy (mijnenergie) sensor descriptions for Quatt."""

from __future__ import annotations

from homeassistant.components.sensor import SensorStateClass
from homeassistant.const import EntityCategory

from .entity import QuattSensorEntityDescription
from .entity_sensor import (
    QuattEnergyCheapestPriceSensor,
    QuattEnergyCurrentPriceSensor,
    QuattEnergyMostExpensivePriceSensor,
)


ENERGY_SENSORS: list[QuattSensorEntityDescription] = [
    QuattSensorEntityDescription(
        key="ean",
        name="EAN",
        icon="mdi:identifier",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    QuattSensorEntityDescription(
        key="prices.current.price",
        name="Current energy price",
        icon="mdi:cash",
        native_unit_of_measurement="EUR/kWh",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=4,
        quatt_entity_class=QuattEnergyCurrentPriceSensor,
    ),
    QuattSensorEntityDescription(
        key="prices.cheapest.price",
        name="Cheapest energy price today",
        icon="mdi:trending-down",
        native_unit_of_measurement="EUR/kWh",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=4,
        quatt_entity_class=QuattEnergyCheapestPriceSensor,
    ),
    QuattSensorEntityDescription(
        key="prices.mostExpensive.price",
        name="Most expensive energy price today",
        icon="mdi:trending-up",
        native_unit_of_measurement="EUR/kWh",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=4,
        quatt_entity_class=QuattEnergyMostExpensivePriceSensor,
    ),
    QuattSensorEntityDescription(
        key="prices.dayAverage",
        name="Average energy price today",
        icon="mdi:chart-line",
        native_unit_of_measurement="EUR/kWh",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=4,
    ),
]
