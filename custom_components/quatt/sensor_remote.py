"""Sensor platform for quatt remote API."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    DOMAIN as SENSOR_DOMAIN,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    CURRENCY_EURO,
    PERCENTAGE,
    EntityCategory,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant
import homeassistant.helpers.device_registry as dr
import homeassistant.helpers.entity_registry as er
import homeassistant.util.dt as dt_util

from .const import (
    DEVICE_CIC_ID,
    DEVICE_HEAT_BATTERY_ID,
    DEVICE_HEATPUMP_1_ID,
    DEVICE_HEATPUMP_2_ID,
    DEVICE_LIST,
    DEVICE_THERMOSTAT_ID,
    DOMAIN,
)
from .coordinator_remote import QuattRemoteDataUpdateCoordinator
from .entity import QuattEntity, QuattSensorEntityDescription


def create_remote_heatpump_sensor_entity_descriptions(
    index: int, is_duo: bool = False
) -> list[QuattSensorEntityDescription]:
    """Create the remote heatpump sensor entity descriptions based on the index."""
    return [
        QuattSensorEntityDescription(
            name="On",
            key=f"heatPumps.{index}.on",
            icon="mdi:power",
            quatt_duo=is_duo,
        ),
        QuattSensorEntityDescription(
            name="Modbus slave ID",
            key=f"heatPumps.{index}.modbusSlaveId",
            icon="mdi:identifier",
            entity_category=EntityCategory.DIAGNOSTIC,
            quatt_duo=is_duo,
        ),
        QuattSensorEntityDescription(
            name="Compressor frequency",
            key=f"heatPumps.{index}.compressorFrequency",
            icon="mdi:sine-wave",
            native_unit_of_measurement="Hz",
            suggested_display_precision=0,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_duo=is_duo,
        ),
        QuattSensorEntityDescription(
            name="Compressor frequency demand",
            key=f"heatPumps.{index}.compressorFrequencyDemand",
            icon="mdi:sine-wave",
            native_unit_of_measurement="Hz",
            suggested_display_precision=0,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_duo=is_duo,
        ),
        QuattSensorEntityDescription(
            name="Minimum power",
            key=f"heatPumps.{index}.minimumPower",
            icon="mdi:lightning-bolt",
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            suggested_display_precision=0,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_duo=is_duo,
        ),
        QuattSensorEntityDescription(
            name="Power",
            key=f"heatPumps.{index}.power",
            icon="mdi:heat-wave",
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            suggested_display_precision=0,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_duo=is_duo,
        ),
        QuattSensorEntityDescription(
            name="Electrical power",
            key=f"heatPumps.{index}.electricalPower",
            icon="mdi:lightning-bolt",
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            suggested_display_precision=2,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_duo=is_duo,
        ),
        QuattSensorEntityDescription(
            name="Rated power",
            key=f"heatPumps.{index}.ratedPower",
            icon="mdi:gauge",
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            suggested_display_precision=2,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_duo=is_duo,
        ),
        QuattSensorEntityDescription(
            name="Expected power",
            key=f"heatPumps.{index}.expectedPower",
            icon="mdi:lightning-bolt-outline",
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            suggested_display_precision=0,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_duo=is_duo,
        ),
        QuattSensorEntityDescription(
            name="Status",
            key=f"heatPumps.{index}.status",
            icon="mdi:information",
            quatt_duo=is_duo,
        ),
        QuattSensorEntityDescription(
            name="Temperature outside",
            key=f"heatPumps.{index}.temperatureOutside",
            icon="mdi:thermometer",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            suggested_display_precision=2,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_duo=is_duo,
        ),
        QuattSensorEntityDescription(
            name="Temperature water in",
            key=f"heatPumps.{index}.temperatureWaterIn",
            icon="mdi:thermometer",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            suggested_display_precision=2,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_duo=is_duo,
        ),
        QuattSensorEntityDescription(
            name="Temperature water out",
            key=f"heatPumps.{index}.temperatureWaterOut",
            icon="mdi:thermometer",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            suggested_display_precision=2,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_duo=is_duo,
        ),
        QuattSensorEntityDescription(
            name="Water pump level",
            key=f"heatPumps.{index}.waterPumpLevel",
            icon="mdi:pump",
            suggested_display_precision=0,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_duo=is_duo,
        ),
        QuattSensorEntityDescription(
            name="ODU type",
            key=f"heatPumps.{index}.oduType",
            icon="mdi:hvac",
            entity_category=EntityCategory.DIAGNOSTIC,
            quatt_duo=is_duo,
        ),
    ]


REMOTE_SENSORS = {
    # The HUB CIC sensor must be created first to ensure the HUB device is present
    DEVICE_CIC_ID: [
        QuattSensorEntityDescription(
            name="Installation ID",
            key="installationId",
            icon="mdi:identifier",
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        QuattSensorEntityDescription(
            name="Installed at",
            key="installedAt",
            device_class=SensorDeviceClass.TIMESTAMP,
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        QuattSensorEntityDescription(
            name="Status",
            key="status",
            icon="mdi:information",
        ),
        QuattSensorEntityDescription(
            name="Boiler power",
            key="boilerPower",
            icon="mdi:fire",
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            suggested_display_precision=0,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        QuattSensorEntityDescription(
            name="Cable connection status",
            key="cableConnectionStatus",
            icon="mdi:ethernet",
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        QuattSensorEntityDescription(
            name="Flow rate",
            key="flowRate",
            icon="mdi:gauge",
            native_unit_of_measurement=UnitOfVolumeFlowRate.LITERS_PER_HOUR,
            suggested_display_precision=0,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        QuattSensorEntityDescription(
            name="LTE connection status",
            key="lteConnectionStatus",
            icon="mdi:signal",
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        QuattSensorEntityDescription(
            name="WiFi connection status",
            key="wifiConnectionStatus",
            icon="mdi:wifi",
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        QuattSensorEntityDescription(
            name="WiFi SSID",
            key="wifiSSID",
            icon="mdi:wifi",
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        QuattSensorEntityDescription(
            name="Electricity price",
            key="electricityPrice",
            icon="mdi:currency-eur",
            native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
            suggested_display_precision=2,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        QuattSensorEntityDescription(
            name="Day electricity price",
            key="dayElectricityPrice",
            icon="mdi:currency-eur",
            native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
            suggested_display_precision=2,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        QuattSensorEntityDescription(
            name="Night electricity price",
            key="nightElectricityPrice",
            icon="mdi:currency-eur",
            native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
            suggested_display_precision=2,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        QuattSensorEntityDescription(
            name="Gas price",
            key="gasPrice",
            icon="mdi:currency-eur",
            native_unit_of_measurement=f"{CURRENCY_EURO}/m³",
            suggested_display_precision=2,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        QuattSensorEntityDescription(
            name="Silent mode",
            key="silentMode",
            icon="mdi:sleep",
        ),
        QuattSensorEntityDescription(
            name="Boiler water temperature in",
            key="boilerWaterTemperatureIn",
            icon="mdi:thermometer",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            suggested_display_precision=2,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        QuattSensorEntityDescription(
            name="Boiler water temperature out",
            key="boilerWaterTemperatureOut",
            icon="mdi:thermometer",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            suggested_display_precision=2,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        QuattSensorEntityDescription(
            name="Heating water temperature in",
            key="heatingWaterTemperatureIn",
            icon="mdi:thermometer",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            suggested_display_precision=2,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        QuattSensorEntityDescription(
            name="Heating water temperature out",
            key="heatingWaterTemperatureOut",
            icon="mdi:thermometer",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            suggested_display_precision=2,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        QuattSensorEntityDescription(
            name="Supervisory control mode",
            key="supervisoryControlMode",
            icon="mdi:cog",
        ),
        QuattSensorEntityDescription(
            name="Number of heat pumps",
            key="numberOfHeatPumps",
            icon="mdi:heat-pump",
            suggested_display_precision=0,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        QuattSensorEntityDescription(
            name="Insights start at",
            key="insightsStartAt",
            device_class=SensorDeviceClass.TIMESTAMP,
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        QuattSensorEntityDescription(
            name="Quatt build",
            key="quattBuild",
            icon="mdi:package-variant",
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        QuattSensorEntityDescription(
            name="Day max sound level",
            key="dayMaxSoundLevel",
            icon="mdi:volume-high",
        ),
        QuattSensorEntityDescription(
            name="Night max sound level",
            key="nightMaxSoundLevel",
            icon="mdi:volume-low",
        ),
        QuattSensorEntityDescription(
            name="Temperature outside",
            key="temperatureOutside",
            icon="mdi:thermometer",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            suggested_display_precision=1,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        QuattSensorEntityDescription(
            name="Water temperature",
            key="waterTemperature",
            icon="mdi:thermometer",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            suggested_display_precision=2,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        QuattSensorEntityDescription(
            name="Quatt heating production amount",
            key="quattHeatingProductionAmount",
            icon="mdi:heat-wave",
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            suggested_display_precision=0,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        QuattSensorEntityDescription(
            name="Electricity consumption amount",
            key="electricityConsumptionAmount",
            icon="mdi:lightning-bolt",
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            suggested_display_precision=2,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        QuattSensorEntityDescription(
            name="Name",
            key="name",
            icon="mdi:label",
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        QuattSensorEntityDescription(
            name="Zip code",
            key="zipCode",
            icon="mdi:map-marker",
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        QuattSensorEntityDescription(
            name="Country",
            key="country",
            icon="mdi:flag",
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        QuattSensorEntityDescription(
            name="Order number",
            key="orderNumber",
            icon="mdi:receipt",
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        QuattSensorEntityDescription(
            name="Electricity night time start hour",
            key="electricityNightTimeStartHour",
            icon="mdi:clock-start",
            native_unit_of_measurement=UnitOfTime.HOURS,
            suggested_display_precision=0,
            entity_category=EntityCategory.CONFIG,
        ),
        QuattSensorEntityDescription(
            name="Electricity night time end hour",
            key="electricityNightTimeEndHour",
            icon="mdi:clock-end",
            native_unit_of_measurement=UnitOfTime.HOURS,
            suggested_display_precision=0,
            entity_category=EntityCategory.CONFIG,
        ),
        QuattSensorEntityDescription(
            name="Sound night time start hour",
            key="soundNightTimeStartHour",
            icon="mdi:clock-start",
            native_unit_of_measurement=UnitOfTime.HOURS,
            suggested_display_precision=0,
            entity_category=EntityCategory.CONFIG,
        ),
        QuattSensorEntityDescription(
            name="Sound night time end hour",
            key="soundNightTimeEndHour",
            icon="mdi:clock-end",
            native_unit_of_measurement=UnitOfTime.HOURS,
            suggested_display_precision=0,
            entity_category=EntityCategory.CONFIG,
        ),
        QuattSensorEntityDescription(
            name="Sound night time start min",
            key="soundNightTimeStartMin",
            icon="mdi:clock-start",
            native_unit_of_measurement=UnitOfTime.MINUTES,
            suggested_display_precision=0,
            entity_category=EntityCategory.CONFIG,
        ),
        QuattSensorEntityDescription(
            name="Sound night time end min",
            key="soundNightTimeEndMin",
            icon="mdi:clock-end",
            native_unit_of_measurement=UnitOfTime.MINUTES,
            suggested_display_precision=0,
            entity_category=EntityCategory.CONFIG,
        ),
    ],
    DEVICE_THERMOSTAT_ID: [
        QuattSensorEntityDescription(
            name="Control temperature set point",
            key="thermostatControlTemperatureSetPoint",
            icon="mdi:thermometer",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            suggested_display_precision=1,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        QuattSensorEntityDescription(
            name="Room temperature set point",
            key="thermostatRoomTemperatureSetPoint",
            icon="mdi:thermometer",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            suggested_display_precision=1,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        QuattSensorEntityDescription(
            name="Room temperature",
            key="thermostatRoomTemperature",
            icon="mdi:thermometer",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            suggested_display_precision=1,
            state_class=SensorStateClass.MEASUREMENT,
        ),
    ],
    DEVICE_HEAT_BATTERY_ID: [
        QuattSensorEntityDescription(
            name="Serial number",
            key="allEStatus.heatBatterySerialNumber",
            icon="mdi:identifier",
            entity_category=EntityCategory.DIAGNOSTIC,
            quatt_all_electric=True,
        ),
        QuattSensorEntityDescription(
            name="Status",
            key="allEStatus.heatBatteryStatus",
            icon="mdi:battery",
            quatt_all_electric=True,
        ),
        QuattSensorEntityDescription(
            name="Size",
            key="allEStatus.heatBatterySize",
            icon="mdi:battery-high",
            entity_category=EntityCategory.DIAGNOSTIC,
            quatt_all_electric=True,
        ),
        QuattSensorEntityDescription(
            name="Shower minutes",
            key="allEStatus.showerMinutes",
            icon="mdi:shower",
            native_unit_of_measurement=UnitOfTime.MINUTES,
            suggested_display_precision=0,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_all_electric=True,
        ),
        QuattSensorEntityDescription(
            name="Percentage",
            key="allEStatus.heatBatteryPercentage",
            icon="mdi:battery",
            native_unit_of_measurement=PERCENTAGE,
            suggested_display_precision=0,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_all_electric=True,
        ),
    ],
    DEVICE_HEATPUMP_1_ID: create_remote_heatpump_sensor_entity_descriptions(
        index=0, is_duo=False
    ),
    DEVICE_HEATPUMP_2_ID: create_remote_heatpump_sensor_entity_descriptions(
        index=1, is_duo=True
    ),
}

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_devices):
    """Set up the remote sensor platform."""
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
        for device_sensors in REMOTE_SENSORS.values()
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
                and entry_reg.domain == SENSOR_DOMAIN
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
    sensors: list[QuattRemoteSensor] = []
    for device_id, sensor_descriptions in REMOTE_SENSORS.items():
        sensors.extend(
            QuattRemoteSensor(
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


class QuattRemoteSensor(QuattEntity, SensorEntity):
    """quatt Remote Sensor class."""

    def __init__(
        self,
        device_name: str,
        device_id: str,
        sensor_key: str,
        coordinator: QuattRemoteDataUpdateCoordinator,
        entity_description: QuattSensorEntityDescription,
        attach_to_hub: bool,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(device_name, device_id, sensor_key, coordinator, attach_to_hub)
        self.entity_description = entity_description

    @property
    def entity_registry_enabled_default(self):
        """Return whether the sensor should be enabled by default."""
        return self.entity_description.entity_registry_enabled_default

    @property
    def native_value(self) -> str:
        """Return the native value of the sensor."""
        value = self.coordinator.get_value(self.entity_description.key)

        if not value:
            return value

        if self.entity_description.device_class == SensorDeviceClass.TIMESTAMP:
            value = dt_util.parse_datetime(value)

        return value
