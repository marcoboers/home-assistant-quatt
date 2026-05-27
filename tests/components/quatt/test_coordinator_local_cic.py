"""Tests for local CIC coordinator value lookup behaviour."""
# pylint: disable=import-error,wrong-import-position

from __future__ import annotations

import pytest

from custom_components.quatt.binary_sensor import (
    create_heatpump_sensor_entity_descriptions as create_heatpump_binary_sensor_descriptions,
)
from custom_components.quatt.coordinator_local_cic import (
    QuattCicLocalDataUpdateCoordinator,
)
from custom_components.quatt.entity import QuattSensor, QuattSensorEntityDescription
from custom_components.quatt.sensor_descriptions_cic import BOILER_SENSORS, CIC_SENSORS
from custom_components.quatt.sensor_descriptions_heat import (
    create_heatpump_sensor_entity_descriptions,
)


def _make_coordinator() -> QuattCicLocalDataUpdateCoordinator:
    """Create a coordinator instance without calling __init__."""
    coordinator = object.__new__(QuattCicLocalDataUpdateCoordinator)
    coordinator.data = {}
    return coordinator


def test_get_value_reads_raw_data_only() -> None:
    """get_value should read raw API data and not invoke computed methods."""
    coordinator = _make_coordinator()
    coordinator.data = {"hp1": {"power": 1200, "powerInput": 400}}

    default = object()

    assert coordinator.get_value("hp1.power") == 1200
    assert coordinator.get_value("hp1.computed_quatt_cop", default) is default


def test_get_computed_value_uses_parent_key_for_heatpump_calculation() -> None:
    """Computed paths with a parent should pass that parent to the calculation."""
    coordinator = _make_coordinator()
    coordinator.data = {
        "hp1": {
            "temperatureWaterIn": 30.0,
            "temperatureWaterOut": 35.5,
        }
    }

    assert coordinator.get_computed_value("hp1.computed_water_delta") == 5.5


def test_get_computed_value_uses_top_level_calculation() -> None:
    """Top-level computed paths should call the matching calculation."""
    coordinator = _make_coordinator()
    coordinator.data = {
        "hp1": {"power": 3000, "powerInput": 1000},
    }

    assert coordinator.get_computed_value("computed_quatt_cop") == 3.0


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        (None, None),
        (0, "Standby"),
        (1, "Standby - heating"),
        (2, "Heating - heatpump only"),
        (3, "Heating - heatpump + boiler"),
        (4, "Heating - boiler only"),
        (5, "Standby - cooling"),
        (6, "Cooling"),
        (95, None),
        (96, "Anti-freeze protection - boiler on"),
        (97, "Anti-freeze protection - boiler pre-pump"),
        (98, "Anti-freeze protection - water circulation"),
        (99, "Fault - circulation pump on"),
        (100, "Commissioning modes"),
        (101, "Commissioning modes"),
    ],
)
def test_computed_supervisory_control_mode_maps_known_and_failsafe_codes(
    mode: int | None, expected: str | None
) -> None:
    """Supervisory control modes should map known codes and fallback states."""
    coordinator = _make_coordinator()
    coordinator.data = {"qc": {"supervisoryControlMode": mode}}

    assert coordinator.computed_supervisory_control_mode() == expected


def test_entity_current_value_uses_computed_key() -> None:
    """Entities should keep legacy keys while reading computed values."""
    coordinator = _make_coordinator()
    coordinator.data = {
        "hp1": {"power": 3000, "powerInput": 1000},
    }
    description = QuattSensorEntityDescription(
        key="computedQuattCop",
        computed_key="computed_quatt_cop",
    )
    sensor = object.__new__(QuattSensor)
    sensor.coordinator = coordinator
    sensor.entity_description = description

    assert sensor.native_value == 3.0


def test_entity_descriptions_computed_keys_map_to_coordinator_methods() -> None:
    """All computed keys should resolve to coordinator methods."""
    coordinator = _make_coordinator()

    descriptions = list(CIC_SENSORS) + list(BOILER_SENSORS)
    descriptions += create_heatpump_sensor_entity_descriptions(0)
    descriptions += create_heatpump_sensor_entity_descriptions(1)
    descriptions += create_heatpump_binary_sensor_descriptions(0)
    descriptions += create_heatpump_binary_sensor_descriptions(1)

    computed_descriptions = [
        description
        for description in descriptions
        if description.computed_key is not None
    ]

    assert computed_descriptions, (
        "No computed keys were found in the entity descriptions"
    )

    for description in computed_descriptions:
        computed_key = description.computed_key
        assert computed_key is not None
        method_name = computed_key.split(".")[-1]
        assert hasattr(
            coordinator,
            method_name,
        ), (
            f"Computed entity key {computed_key} does not map to "
            f"{method_name} on {coordinator.__class__.__name__}"
        )
