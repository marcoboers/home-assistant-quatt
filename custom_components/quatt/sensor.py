"""Sensor platform for quatt."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    DOMAIN as SENSOR_DOMAIN,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    EntityCategory,
    UnitOfPower,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant
import homeassistant.helpers.device_registry as dr
import homeassistant.helpers.entity_registry as er
import homeassistant.util.dt as dt_util

from .const import (
    DEVICE_BOILER_ID,
    DEVICE_CIC_ID,
    DEVICE_FLOWMETER_ID,
    DEVICE_HEAT_CHARGER_ID,
    DEVICE_HEATPUMP_1_ID,
    DEVICE_HEATPUMP_2_ID,
    DEVICE_LIST,
    DEVICE_THERMOSTAT_ID,
    DOMAIN,
)
from .coordinator import QuattDataUpdateCoordinator
from .entity import QuattEntity, QuattSensorEntityDescription

def create_heatpump_sensor_entity_descriptions(
    prefix: str, is_duo: bool = False
) -> list[QuattSensorEntityDescription]:
    """Create the heatpump sensor entity descriptions based on the prefix."""
    return [
        QuattSensorEntityDescription(
            name="Workingmode",
            key=f"{prefix}.getMainWorkingMode",
            icon="mdi:auto-mode",
            quatt_duo=is_duo,
        ),
        QuattSensorEntityDescription(
            name="Temperature outside",
            key=f"{prefix}.temperatureOutside",
            icon="mdi:thermometer",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            suggested_display_precision=2,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_duo=is_duo,
        ),
        QuattSensorEntityDescription(
            name="Temperature water in",
            key=f"{prefix}.temperatureWaterIn",
            icon="mdi:thermometer",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            suggested_display_precision=2,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_duo=is_duo,
        ),
        QuattSensorEntityDescription(
            name="Temperature water out",
            key=f"{prefix}.temperatureWaterOut",
            icon="mdi:thermometer",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            suggested_display_precision=2,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_duo=is_duo,
        ),
        QuattSensorEntityDescription(
            name="Water delta",
            key=f"{prefix}.computedWaterDelta",
            icon="mdi:thermometer-water",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            suggested_display_precision=2,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_duo=is_duo,
        ),
        QuattSensorEntityDescription(
            name="Power input",
            key=f"{prefix}.powerInput",
            icon="mdi:lightning-bolt",
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            suggested_display_precision=0,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_duo=is_duo,
        ),
        QuattSensorEntityDescription(
            name="Power",
            key=f"{prefix}.power",
            icon="mdi:heat-wave",
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            suggested_display_precision=0,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_duo=is_duo,
        ),
        QuattSensorEntityDescription(
            name="Quatt COP",
            key=f"{prefix}.computedQuattCop",
            icon="mdi:heat-pump",
            native_unit_of_measurement="CoP",
            suggested_display_precision=2,
            state_class="measurement",
            quatt_duo=is_duo,
        ),
    ]


SENSORS = {
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
            quatt_duo=True,
        ),
        QuattSensorEntityDescription(
            name="Total power",
            key="computedPower",
            icon="mdi:heat-wave",
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            suggested_display_precision=0,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_duo=True,
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
            quatt_duo=True,
        ),
        QuattSensorEntityDescription(
            name="Total Quatt COP",
            key="computedQuattCop",
            icon="mdi:heat-pump",
            native_unit_of_measurement="CoP",
            suggested_display_precision=2,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_duo=True,
        ),
        QuattSensorEntityDescription(
            name="QC supervisory control mode code",
            key="qc.supervisoryControlMode",
        ),
        QuattSensorEntityDescription(
            name="QC supervisory control mode",
            key="qc.computedSupervisoryControlMode",
        ),
        # System
        QuattSensorEntityDescription(
            name="System hostname",
            key="system.hostName",
            entity_category=EntityCategory.DIAGNOSTIC,
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
            quatt_all_electric=True,
        ),
    ],
    DEVICE_HEATPUMP_1_ID: create_heatpump_sensor_entity_descriptions(
        prefix="hp1", is_duo=False
    ),
    DEVICE_HEATPUMP_2_ID: create_heatpump_sensor_entity_descriptions(
        prefix="hp2", is_duo=True
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
            quatt_hybrid=True,
            quatt_opentherm=True,
        ),
        QuattSensorEntityDescription(
            name="Temperature water outlet",
            key="boiler.otFbSupplyOutletTemperature",
            icon="mdi:thermometer",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            suggested_display_precision=2,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_hybrid=True,
            quatt_opentherm=True,
        ),
        QuattSensorEntityDescription(
            name="Water pressure",
            key="boiler.otFbWaterPressure",
            icon="mdi:gauge",
            native_unit_of_measurement=UnitOfPressure.BAR,
            suggested_display_precision=2,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_hybrid=True,
            quatt_opentherm=True,
        ),
        QuattSensorEntityDescription(
            name="Heat power",
            key="boiler.computedBoilerHeatPower",
            icon="mdi:heat-wave",
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            suggested_display_precision=0,
            state_class=SensorStateClass.MEASUREMENT,
            quatt_hybrid=True,
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
    ],
}

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_devices):
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    registry = er.async_get(hass)

    # Cache the active states
    heatpump_1_active = coordinator.heatpump_1_active()
    heatpump_2_active = coordinator.heatpump_2_active()
    all_electric_active = coordinator.all_electric_active()
    is_boiler_opentherm = coordinator.is_boiler_opentherm()

    _LOGGER.debug("Heatpump 1 active: %s", heatpump_1_active)
    _LOGGER.debug("Heatpump 2 active: %s", heatpump_2_active)
    _LOGGER.debug("All electric active: %s", all_electric_active)
    _LOGGER.debug("boiler OpenTherm: %s", is_boiler_opentherm)

    # Create only those sensors that make sense for this installation type.
    # Remove sensors that are not applicable based on the configuration.
    # This can occur when the configuration changes, e.g., from hybrid or duo to all-electric.
    device_reg = dr.async_get(hass)
    devices = dr.async_entries_for_config_entry(device_reg, entry.entry_id)
    device_ids = {dev.id for dev in devices}

    # Determine which sensors to create based on the detected configuration
    flag_conditions = [
        ("quatt_hybrid", not all_electric_active),
        ("quatt_all_electric", all_electric_active),
        ("quatt_duo", heatpump_2_active),
        ("quatt_opentherm", is_boiler_opentherm),
    ]

    # Flatten out all sensor descriptions
    flat_descriptions = [
        sensor_description
        for device_sensors in SENSORS.values()
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
            device_reg.async_remove_device(dev_id)

    # Create sensor entities based on the filtered sensor keys
    device_name_map = {d["id"]: d["name"] for d in DEVICE_LIST}
    sensors: list[QuattSensor] = []
    for device_id, sensor_descriptions in SENSORS.items():
        device_name = device_name_map.get(device_id, device_id)
        sensors.extend(
            QuattSensor(
                device_name=device_name,
                device_id=device_id,
                sensor_key=sensor_description.key,
                coordinator=coordinator,
                entity_description=sensor_description,
            )
            for sensor_description in sensor_descriptions
            if sensor_description.key in sensor_keys
        )

    async_add_devices(sensors)


class QuattSensor(QuattEntity, SensorEntity):
    """quatt Sensor class."""

    def __init__(
        self,
        device_name: str,
        device_id: str,
        sensor_key: str,
        coordinator: QuattDataUpdateCoordinator,
        entity_description: QuattSensorEntityDescription,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(device_name, device_id, sensor_key, coordinator)
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
