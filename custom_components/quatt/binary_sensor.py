"""Binary sensor platform for quatt."""

from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
)
from homeassistant.const import EntityCategory
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
from .entity import (
    QuattBinarySensor,
    QuattBinarySensorEntityDescription,
    QuattFeatureFlags,
)
from .entity_setup import async_setup_entities


def create_heatpump_sensor_entity_descriptions(
    index: int, is_duo: bool = False
) -> list[QuattBinarySensorEntityDescription]:
    """Create the heatpump sensor entity descriptions based on the index."""
    prefix = "hp1" if index == 0 else "hp2"

    return [
        QuattBinarySensorEntityDescription(
            name="Silentmode",
            key=f"{prefix}.silentModeStatus",
            translation_key="hp_silentModeStatus",
            icon="mdi:sleep",
            features=QuattFeatureFlags(
                quatt_duo=is_duo,
            ),
        ),
        QuattBinarySensorEntityDescription(
            name="Limited by COP",
            key=f"{prefix}.limitedByCop",
            translation_key="hp_silentModeStatus",
            icon="mdi:arrow-collapse-up",
            features=QuattFeatureFlags(
                quatt_duo=is_duo,
            ),
        ),
        QuattBinarySensorEntityDescription(
            name="Defrost",
            key=f"{prefix}.computedDefrost",
            translation_key="hp_silentModeStatus",
            icon="mdi:snowflake",
            features=QuattFeatureFlags(
                quatt_duo=is_duo,
            ),
        ),
    ]


BINARY_SENSORS = {
    # The HUB CIC sensor must be created first to ensure the HUB device is present
    DEVICE_CIC_ID: [
        QuattBinarySensorEntityDescription(
            name="QC pump protection",
            key="qc.stickyPumpProtectionEnabled",
            icon="mdi:shield-refresh-outline",
        ),
        QuattBinarySensorEntityDescription(
            name="Anti legionella active",
            key="qcAllE.isAntilegionellaActive",
            icon="mdi:shield-check",
            features=QuattFeatureFlags(
                quatt_all_electric=True,
            ),
        ),
        QuattBinarySensorEntityDescription(
            name="Scanning for WiFi",
            key="isScanningForWifi",
            icon="mdi:wifi-refresh",
            device_class=BinarySensorDeviceClass.RUNNING,
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
            features=QuattFeatureFlags(
                quatt_mobile_api=True,
            ),
        ),
        QuattBinarySensorEntityDescription(
            name="Use pricing to limit heat pump",
            key="usePricingToLimitHeatPump",
            icon="mdi:currency-eur",
            features=QuattFeatureFlags(
                quatt_mobile_api=True,
            ),
        ),
        QuattBinarySensorEntityDescription(
            name="Avoid nighttime charging",
            key="avoidNighttimeCharging",
            icon="mdi:weather-night",
            features=QuattFeatureFlags(
                quatt_mobile_api=True,
            ),
        ),
        QuattBinarySensorEntityDescription(
            name="HP1 connected",
            key="isHp1Connected",
            icon="mdi:connection",
            device_class=BinarySensorDeviceClass.CONNECTIVITY,
            entity_category=EntityCategory.DIAGNOSTIC,
            features=QuattFeatureFlags(
                quatt_mobile_api=True,
            ),
        ),
        QuattBinarySensorEntityDescription(
            name="HP2 connected",
            key="isHp2Connected",
            icon="mdi:connection",
            device_class=BinarySensorDeviceClass.CONNECTIVITY,
            entity_category=EntityCategory.DIAGNOSTIC,
            features=QuattFeatureFlags(
                quatt_duo=True,
                quatt_mobile_api=True,
            ),
        ),
        QuattBinarySensorEntityDescription(
            name="Thermostat connected",
            key="isThermostatConnected",
            icon="mdi:connection",
            entity_category=EntityCategory.DIAGNOSTIC,
            device_class=BinarySensorDeviceClass.CONNECTIVITY,
            features=QuattFeatureFlags(
                quatt_mobile_api=True,
            ),
        ),
        QuattBinarySensorEntityDescription(
            name="Boiler connected",
            key="isBoilerConnected",
            icon="mdi:connection",
            entity_category=EntityCategory.DIAGNOSTIC,
            device_class=BinarySensorDeviceClass.CONNECTIVITY,
            features=QuattFeatureFlags(
                quatt_hybrid=True,
                quatt_mobile_api=True,
            ),
        ),
        QuattBinarySensorEntityDescription(
            name="Temperature sensor connected",
            key="isTemperatureSensorConnected",
            icon="mdi:connection",
            entity_category=EntityCategory.DIAGNOSTIC,
            device_class=BinarySensorDeviceClass.CONNECTIVITY,
            features=QuattFeatureFlags(
                quatt_mobile_api=True,
            ),
        ),
        QuattBinarySensorEntityDescription(
            name="Controller alive",
            key="isControllerAlive",
            icon="mdi:check-circle",
            device_class=BinarySensorDeviceClass.RUNNING,
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
            features=QuattFeatureFlags(
                quatt_mobile_api=True,
            ),
        ),
        QuattBinarySensorEntityDescription(
            name="WiFi enabled",
            key="wifiEnabled",
            icon="mdi:wifi",
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
            features=QuattFeatureFlags(
                quatt_mobile_api=True,
            ),
        ),
        QuattBinarySensorEntityDescription(
            name="Has sound slider",
            key="hasSoundSlider",
            icon="mdi:volume-high",
            features=QuattFeatureFlags(
                quatt_mobile_api=True,
            ),
        ),
        QuattBinarySensorEntityDescription(
            name="Supports forget WiFi",
            key="supportsForgetWifi",
            icon="mdi:wifi-remove",
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
            features=QuattFeatureFlags(
                quatt_mobile_api=True,
            ),
        ),
        QuattBinarySensorEntityDescription(
            name="Central heating on",
            key="isCentralHeatingOn",
            icon="mdi:heating-coil",
            features=QuattFeatureFlags(
                quatt_mobile_api=True,
            ),
        ),
        QuattBinarySensorEntityDescription(
            name="Has dynamic pricing",
            key="hasDynamicPricing",
            icon="mdi:currency-eur",
            features=QuattFeatureFlags(
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
        QuattBinarySensorEntityDescription(
            name="Heating",
            key="boiler.otFbChModeActive",
            icon="mdi:heating-coil",
            features=QuattFeatureFlags(
                quatt_hybrid=True,
                quatt_opentherm=True,
            ),
        ),
        QuattBinarySensorEntityDescription(
            name="Domestic hot water",
            key="boiler.otFbDhwActive",
            icon="mdi:water-boiler",
            features=QuattFeatureFlags(
                quatt_hybrid=True,
                quatt_opentherm=True,
            ),
        ),
        QuattBinarySensorEntityDescription(
            name="Flame",
            key="boiler.otFbFlameOn",
            icon="mdi:fire",
            features=QuattFeatureFlags(
                quatt_hybrid=True,
                quatt_opentherm=True,
            ),
        ),
        QuattBinarySensorEntityDescription(
            name="CIC heating",
            key="boiler.otTbCH",
            icon="mdi:heating-coil",
            features=QuattFeatureFlags(
                quatt_hybrid=True,
            ),
        ),
        QuattBinarySensorEntityDescription(
            name="CIC on/off mode",
            key="boiler.oTtbTurnOnOffBoilerOn",
            icon="mdi:water-boiler",
            features=QuattFeatureFlags(
                quatt_hybrid=True,
            ),
        ),
        QuattBinarySensorEntityDescription(
            name="Boiler on",
            key="boilerOn",
            icon="mdi:water-boiler",
            features=QuattFeatureFlags(
                quatt_hybrid=True,
                quatt_mobile_api=True,
            ),
        ),
    ],
    DEVICE_THERMOSTAT_ID: [
        QuattBinarySensorEntityDescription(
            name="Heating",
            key="thermostat.otFtChEnabled",
            icon="mdi:home-thermometer",
        ),
        QuattBinarySensorEntityDescription(
            name="Domestic hot water",
            key="thermostat.otFtDhwEnabled",
            icon="mdi:water-thermometer",
            features=QuattFeatureFlags(
                quatt_hybrid=True,
            ),
        ),
        QuattBinarySensorEntityDescription(
            name="Cooling",
            key="thermostat.otFtCoolingEnabled",
            icon="mdi:snowflake-thermometer",
        ),
        QuattBinarySensorEntityDescription(
            name="Flame on",
            key="thermostatFlameOn",
            icon="mdi:fire",
            features=QuattFeatureFlags(
                quatt_mobile_api=True,
            ),
        ),
        QuattBinarySensorEntityDescription(
            name="Show thermostat temperatures",
            key="showThermostatTemperatures",
            icon="mdi:thermometer",
            features=QuattFeatureFlags(
                quatt_mobile_api=True,
            ),
        ),
    ],
    DEVICE_FLOWMETER_ID: [],
    DEVICE_HEAT_BATTERY_ID: [
        QuattBinarySensorEntityDescription(
            name="Charging",
            key="allEStatus.isHeatBatteryCharging",
            icon="mdi:battery-charging",
            device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
            features=QuattFeatureFlags(
                quatt_all_electric=True,
                quatt_mobile_api=True,
            ),
        ),
        QuattBinarySensorEntityDescription(
            name="Domestic hot water on",
            key="allEStatus.isDomesticHotWaterOn",
            icon="mdi:water-boiler",
            features=QuattFeatureFlags(
                quatt_all_electric=True,
                quatt_mobile_api=True,
            ),
        ),
        QuattBinarySensorEntityDescription(
            name="Shower minutes degraded",
            key="allEStatus.showerMinutesDegraded",
            icon="mdi:alert",
            device_class=BinarySensorDeviceClass.PROBLEM,
            features=QuattFeatureFlags(
                quatt_all_electric=True,
                quatt_mobile_api=True,
            ),
        ),
    ],
    DEVICE_HEAT_CHARGER_ID: [],
}

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_devices):
    """Set up the binary_sensor platform."""
    coordinators = hass.data[DOMAIN][entry.entry_id]

    local_coordinator: QuattDataUpdateCoordinator = coordinators["local"]
    remote_coordinator: QuattDataUpdateCoordinator = coordinators["remote"]

    sensors: list[QuattBinarySensor] = []
    sensors += await async_setup_entities(
        hass=hass,
        coordinator=local_coordinator,
        entry=entry,
        remote=False,
        entity_class=QuattBinarySensor,
        entity_descriptions=BINARY_SENSORS,
        entity_domain=BINARY_SENSOR_DOMAIN,
    )

    if remote_coordinator:
        sensors += await async_setup_entities(
            hass=hass,
            coordinator=remote_coordinator,
            entry=entry,
            remote=True,
            entity_class=QuattBinarySensor,
            entity_descriptions=BINARY_SENSORS,
            entity_domain=BINARY_SENSOR_DOMAIN,
        )

    async_add_devices(sensors)
