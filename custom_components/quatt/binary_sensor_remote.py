"""Binary sensor platform for quatt remote API."""

from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
import homeassistant.helpers.device_registry as dr
import homeassistant.helpers.entity_registry as er

from .const import (
    DEVICE_CIC_ID,
    DEVICE_BOILER_ID,
    DEVICE_FLOWMETER_ID,
    DEVICE_HEAT_BATTERY_ID,
    DEVICE_HEAT_CHARGER_ID,
    DEVICE_HEATPUMP_1_ID,
    DEVICE_HEATPUMP_2_ID,
    DEVICE_THERMOSTAT_ID,
    DEVICE_LIST,
    DOMAIN,
)
from .coordinator_remote import QuattRemoteDataUpdateCoordinator
from .entity import QuattBinarySensorEntityDescription, QuattEntity


def create_remote_heatpump_binary_sensor_entity_descriptions(
    index: int, is_duo: bool = False
) -> list[QuattBinarySensorEntityDescription]:
    """Create the remote heatpump binary sensor entity descriptions based on the index."""
    return [
        QuattBinarySensorEntityDescription(
            name="Silent mode status",
            key=f"heatPumps.{index}.silentModeStatus",
            icon="mdi:sleep",
            quatt_duo=is_duo,
        ),
        QuattBinarySensorEntityDescription(
            name="Limited by COP",
            key=f"heatPumps.{index}.limitedByCop",
            icon="mdi:arrow-collapse-up",
            quatt_duo=is_duo,
        ),
    ]


REMOTE_BINARY_SENSORS = {
    # The HUB CIC sensor must be created first to ensure the HUB device is present
    DEVICE_CIC_ID: [
        QuattBinarySensorEntityDescription(
            name="Scanning for WiFi",
            key="isScanningForWifi",
            icon="mdi:wifi-refresh",
            device_class=BinarySensorDeviceClass.RUNNING,
        ),
        QuattBinarySensorEntityDescription(
            name="Use pricing to limit heat pump",
            key="usePricingToLimitHeatPump",
            icon="mdi:currency-eur",
        ),
        QuattBinarySensorEntityDescription(
            name="Avoid nighttime charging",
            key="avoidNighttimeCharging",
            icon="mdi:weather-night",
        ),
        QuattBinarySensorEntityDescription(
            name="HP1 connected",
            key="isHp1Connected",
            icon="mdi:connection",
            device_class=BinarySensorDeviceClass.CONNECTIVITY,
        ),
        QuattBinarySensorEntityDescription(
            name="HP2 connected",
            key="isHp2Connected",
            icon="mdi:connection",
            device_class=BinarySensorDeviceClass.CONNECTIVITY,
            quatt_duo=True,
        ),
        QuattBinarySensorEntityDescription(
            name="Thermostat connected",
            key="isThermostatConnected",
            icon="mdi:connection",
            device_class=BinarySensorDeviceClass.CONNECTIVITY,
        ),
        QuattBinarySensorEntityDescription(
            name="Boiler connected",
            key="isBoilerConnected",
            icon="mdi:connection",
            device_class=BinarySensorDeviceClass.CONNECTIVITY,
        ),
        QuattBinarySensorEntityDescription(
            name="Temperature sensor connected",
            key="isTemperatureSensorConnected",
            icon="mdi:connection",
            device_class=BinarySensorDeviceClass.CONNECTIVITY,
        ),
        QuattBinarySensorEntityDescription(
            name="Controller alive",
            key="isControllerAlive",
            icon="mdi:check-circle",
            device_class=BinarySensorDeviceClass.RUNNING,
        ),
        QuattBinarySensorEntityDescription(
            name="WiFi enabled",
            key="wifiEnabled",
            icon="mdi:wifi",
        ),
        QuattBinarySensorEntityDescription(
            name="Has sound slider",
            key="hasSoundSlider",
            icon="mdi:volume-high",
        ),
        QuattBinarySensorEntityDescription(
            name="Supports forget WiFi",
            key="supportsForgetWifi",
            icon="mdi:wifi-remove",
        ),
        QuattBinarySensorEntityDescription(
            name="Central heating on",
            key="isCentralHeatingOn",
            icon="mdi:heating-coil",
        ),
        QuattBinarySensorEntityDescription(
            name="Has dynamic pricing",
            key="hasDynamicPricing",
            icon="mdi:currency-eur",
        ),
    ],
    DEVICE_BOILER_ID: [
        QuattBinarySensorEntityDescription(
            name="Boiler on",
            key="boilerOn",
            icon="mdi:water-boiler",
        ),
    ],
    DEVICE_FLOWMETER_ID: [],
    DEVICE_HEAT_BATTERY_ID: [
        QuattBinarySensorEntityDescription(
            name="Charging",
            key="allEStatus.isHeatBatteryCharging",
            icon="mdi:battery-charging",
            device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
            quatt_all_electric=True,
        ),
        QuattBinarySensorEntityDescription(
            name="Domestic hot water on",
            key="allEStatus.isDomesticHotWaterOn",
            icon="mdi:water-boiler",
            quatt_all_electric=True,
        ),
        QuattBinarySensorEntityDescription(
            name="Shower minutes degraded",
            key="allEStatus.showerMinutesDegraded",
            icon="mdi:alert",
            device_class=BinarySensorDeviceClass.PROBLEM,
            quatt_all_electric=True,
        ),
    ],
    DEVICE_HEAT_CHARGER_ID: [],
    DEVICE_HEATPUMP_1_ID: create_remote_heatpump_binary_sensor_entity_descriptions(
        index=0, is_duo=False
    ),
    DEVICE_HEATPUMP_2_ID: create_remote_heatpump_binary_sensor_entity_descriptions(
        index=1, is_duo=True
    ),
    DEVICE_THERMOSTAT_ID: [
        QuattBinarySensorEntityDescription(
            name="Flame on",
            key="thermostatFlameOn",
            icon="mdi:fire",
        ),
        QuattBinarySensorEntityDescription(
            name="Show thermostat temperatures",
            key="showThermostatTemperatures",
            icon="mdi:thermometer",
        ),
    ],
}

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_devices):
    """Set up the remote binary_sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    registry = er.async_get(hass)

    # Cache the active states
    heatpump_1_active = coordinator.heatpump_1_active()
    heatpump_2_active = coordinator.heatpump_2_active()
    all_electric_active = coordinator.all_electric_active()

    _LOGGER.debug("Remote - Heatpump 1 active: %s", heatpump_1_active)
    _LOGGER.debug("Remote - Heatpump 2 active: %s", heatpump_2_active)
    _LOGGER.debug("Remote - All electric active: %s", all_electric_active)

    # Create only those sensors that make sense for this installation type.
    # Remove sensors that are not applicable based on the configuration.
    device_reg = dr.async_get(hass)
    devices = dr.async_entries_for_config_entry(device_reg, entry.entry_id)
    device_ids = {dev.id for dev in devices}

    # Determine which sensors to create based on the detected configuration
    flag_conditions = [
        ("quatt_all_electric", all_electric_active),
        ("quatt_duo", heatpump_2_active),
    ]

    # Flatten out all sensor descriptions
    flat_descriptions = [
        sensor_description
        for device_sensors in REMOTE_BINARY_SENSORS.values()
        for sensor_description in device_sensors
    ]

    # Determine which sensors to create based on the flags
    sensor_keys = {
        sensor_description.key
        for sensor_description in flat_descriptions
        if not any(getattr(sensor_description, flag) for flag, _ in flag_conditions)
        or all(
            condition
            for flag, condition in flag_conditions
            if getattr(sensor_description, flag)
        )
    }

    # Remove not applicable sensors
    hub_id = (entry.unique_id or entry.entry_id).strip()
    for dev_id in device_ids:
        for entry_reg in er.async_entries_for_device(
            registry, dev_id, include_disabled_entities=True
        ):
            if (
                entry_reg.config_entry_id == entry.entry_id
                and entry_reg.domain == BINARY_SENSOR_DOMAIN
                and entry_reg.platform == DOMAIN
                and not any(entry_reg.unique_id.endswith(key) for key in sensor_keys)
            ):
                registry.async_remove(entry_reg.entity_id)

        # Remove the device in case it has no remaining entities
        if not any(er.async_entries_for_device(registry, dev_id)):
            # Do not remove the hub device
            dev = device_reg.async_get(dev_id)
            if dev and (DOMAIN, hub_id) in dev.identifiers:
                continue
            device_reg.async_remove_device(dev_id)

    # Create sensor entities based on the filtered sensor keys
    device_name_map = {d["id"]: d["name"] for d in DEVICE_LIST}
    sensors: list[QuattRemoteBinarySensor] = []
    for device_id, sensor_descriptions in REMOTE_BINARY_SENSORS.items():
        sensors.extend(
            QuattRemoteBinarySensor(
                device_name=device_name_map.get(device_id, device_id),
                device_id=device_id,
                sensor_key=sensor_description.key,
                coordinator=coordinator,
                entity_description=sensor_description,
                attach_to_hub=(device_id == DEVICE_CIC_ID),
            )
            for sensor_description in sensor_descriptions
            if sensor_description.key in sensor_keys
        )

    async_add_devices(sensors)


class QuattRemoteBinarySensor(QuattEntity, BinarySensorEntity):
    """quatt remote binary_sensor class."""

    def __init__(
        self,
        device_name: str,
        device_id: str,
        sensor_key: str,
        coordinator: QuattRemoteDataUpdateCoordinator,
        entity_description: QuattBinarySensorEntityDescription,
        attach_to_hub: bool,
    ) -> None:
        """Initialize the binary_sensor class."""
        super().__init__(device_name, device_id, sensor_key, coordinator, attach_to_hub)
        self.entity_description = entity_description

    @property
    def entity_registry_enabled_default(self):
        """Return whether the sensor should be enabled by default."""
        return self.entity_description.entity_registry_enabled_default

    @property
    def is_on(self) -> bool:
        """Return true if the binary_sensor is on."""
        return self.coordinator.get_value(self.entity_description.key)
