"""Chill sensor descriptions for Quatt."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import EntityCategory, UnitOfTemperature

from .entity import QuattFeatureFlags, QuattSensorEntityDescription
from .entity_sensor import QuattChillSensor


def create_chill_sensor_entity_descriptions(
    index: int,
) -> list[QuattSensorEntityDescription]:
    """Create the Chill sensor entity descriptions based on the index."""
    return [
        QuattSensorEntityDescription(
            name="Name",
            key=f"chills.{index}.name",
            icon="mdi:label",
            entity_category=EntityCategory.DIAGNOSTIC,
            quatt_features=QuattFeatureFlags(
                mobile_api=True,
            ),
            quatt_entity_class=QuattChillSensor,
        ),
        QuattSensorEntityDescription(
            name="Color",
            key=f"chills.{index}.color",
            icon="mdi:palette",
            entity_category=EntityCategory.DIAGNOSTIC,
            quatt_features=QuattFeatureFlags(
                mobile_api=True,
            ),
            quatt_entity_class=QuattChillSensor,
        ),
        QuattSensorEntityDescription(
            name="Mode",
            key=f"chills.{index}.mode",
            icon="mdi:autorenew",
            quatt_features=QuattFeatureFlags(
                mobile_api=True,
            ),
            quatt_entity_class=QuattChillSensor,
        ),
        QuattSensorEntityDescription(
            name="Fan mode",
            key=f"chills.{index}.fanMode",
            icon="mdi:fan",
            quatt_features=QuattFeatureFlags(
                mobile_api=True,
            ),
            quatt_entity_class=QuattChillSensor,
        ),
        QuattSensorEntityDescription(
            name="Ambient temperature",
            key=f"chills.{index}.ambientTemperature",
            icon="mdi:thermometer",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            suggested_display_precision=1,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_features=QuattFeatureFlags(
                mobile_api=True,
            ),
            quatt_entity_class=QuattChillSensor,
        ),
        QuattSensorEntityDescription(
            name="Minimum target temperature",
            key=f"chills.{index}.minTargetTemperature",
            icon="mdi:thermometer-chevron-down",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            suggested_display_precision=0,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
            quatt_features=QuattFeatureFlags(
                mobile_api=True,
            ),
            quatt_entity_class=QuattChillSensor,
        ),
        QuattSensorEntityDescription(
            name="Maximum target temperature",
            key=f"chills.{index}.maxTargetTemperature",
            icon="mdi:thermometer-chevron-up",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            suggested_display_precision=0,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
            quatt_features=QuattFeatureFlags(
                mobile_api=True,
            ),
            quatt_entity_class=QuattChillSensor,
        ),
        QuattSensorEntityDescription(
            name="Status",
            key=f"chills.{index}.status",
            icon="mdi:information",
            quatt_features=QuattFeatureFlags(
                mobile_api=True,
            ),
            quatt_entity_class=QuattChillSensor,
        ),
        QuattSensorEntityDescription(
            name="Update state",
            key=f"chills.{index}.updateState",
            icon="mdi:cloud-check",
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
            quatt_features=QuattFeatureFlags(
                mobile_api=True,
            ),
            quatt_entity_class=QuattChillSensor,
        ),
        QuattSensorEntityDescription(
            name="Last updated",
            key=f"chills.{index}.lastUpdatedAt",
            icon="mdi:clock-outline",
            device_class=SensorDeviceClass.TIMESTAMP,
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
            quatt_features=QuattFeatureFlags(
                mobile_api=True,
            ),
            quatt_entity_class=QuattChillSensor,
        ),
    ]
