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
        pytest.param(None, None, id="missing-mode"),
        pytest.param(0, "Standby", id="standby"),
        pytest.param(1, "Standby - heating", id="standby-heating"),
        pytest.param(2, "Heating - heatpump only", id="heating-heatpump-only"),
        pytest.param(
            3, "Heating - heatpump + boiler", id="heating-heatpump-and-boiler"
        ),
        pytest.param(4, "Heating - boiler only", id="heating-boiler-only"),
        pytest.param(5, "Chill circulation", id="chill-circulation"),
        pytest.param(6, "Chill cooling", id="chill-cooling"),
        pytest.param(95, "Sticky pump protection", id="sticky-pump-protection"),
        pytest.param(
            96, "Anti-freeze protection - boiler on", id="anti-freeze-boiler-on"
        ),
        pytest.param(
            97,
            "Anti-freeze protection - boiler pre-pump",
            id="anti-freeze-boiler-prepump",
        ),
        pytest.param(
            98,
            "Anti-freeze protection - water circulation",
            id="anti-freeze-water-circulation",
        ),
        pytest.param(99, "Fault - circulation pump on", id="fault-circulation-pump-on"),
        pytest.param(100, "Commissioning modes", id="commissioning-100"),
        pytest.param(101, "Commissioning modes", id="commissioning-101"),
        pytest.param(400, "Invalid configuration", id="invalid-configuration"),
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
