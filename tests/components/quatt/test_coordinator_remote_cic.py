"""Tests for the remote (mobile API) CIC coordinator lookups."""
# pylint: disable=import-error,wrong-import-position

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from custom_components.quatt.coordinator_remote_cic import (
    QuattCicRemoteDataUpdateCoordinator,
)

FIXTURES = Path(__file__).parent / "fixtures"


def make_coordinator(data: Any) -> QuattCicRemoteDataUpdateCoordinator:
    """Create a coordinator instance without calling __init__."""
    coordinator = object.__new__(QuattCicRemoteDataUpdateCoordinator)
    coordinator.data = data
    return coordinator


@pytest.fixture(name="coordinator")
def coordinator_fixture() -> QuattCicRemoteDataUpdateCoordinator:
    """Return a coordinator loaded with the duo all-electric remote payload."""
    data = json.loads(
        (FIXTURES / "remote_cic_duo_all_electric.json").read_text()
    )
    return make_coordinator(data)


def test_get_value_unwraps_result(coordinator) -> None:
    """Top-level lookups transparently unwrap the meta/result envelope."""
    assert coordinator.get_value("quattBuild") == "4.11.1"
    assert coordinator.get_value("supervisoryControlMode") == 0


def test_get_value_nested_dict(coordinator) -> None:
    """Nested dict paths resolve."""
    assert coordinator.get_value("allEStatus.heatBatteryPercentage") == 80
    assert coordinator.get_value("chMaxWaterTemperature.value") == 40
    assert (
        coordinator.get_value("avoidNighttimeCharging.nighttimeChargingStartTime")
        == "19:00"
    )


def test_get_value_list_index(coordinator) -> None:
    """Numeric path segments index into lists such as heatPumps."""
    assert coordinator.get_value("heatPumps.0.temperatureWaterOut") == 21.41
    assert coordinator.get_value("heatPumps.1.modbusSlaveId") == 2
    assert coordinator.get_value("supportedTariffTypes.1") == "double"


@pytest.mark.parametrize(
    "value_path",
    [
        "heatPumps.5.power",  # index out of range
        "heatPumps.first.power",  # non-numeric index
        "doesNotExist",  # missing key
        "allEStatus.doesNotExist",  # missing nested key
        "quattBuild.nested",  # walking into a scalar
    ],
)
def test_get_value_invalid_paths_return_default(coordinator, value_path) -> None:
    """Invalid paths return the provided default."""
    sentinel = object()
    assert coordinator.get_value(value_path, sentinel) is sentinel


def test_get_value_empty_data() -> None:
    """A coordinator without data returns the default."""
    coordinator = make_coordinator(None)
    assert coordinator.get_value("quattBuild", "fallback") == "fallback"


def test_heatpump_counts_duo(coordinator) -> None:
    """Two heat pumps in the payload activate hp1 and hp2."""
    assert coordinator.heatpump_count() == 2
    assert coordinator.heatpump_1_active() is True
    assert coordinator.heatpump_2_active() is True


def test_heatpump_counts_empty() -> None:
    """Without heat pump data the counts are zero."""
    coordinator = make_coordinator({"result": {}})
    assert coordinator.heatpump_count() == 0
    assert coordinator.heatpump_1_active() is False
    assert coordinator.heatpump_2_active() is False


def test_all_electric_active(coordinator) -> None:
    """A present allEStatus section marks the system all-electric."""
    assert bool(coordinator.all_electric_active()) is True

    hybrid = make_coordinator({"result": {"allEStatus": None}})
    assert hybrid.all_electric_active() is False


def test_is_boiler_opentherm(coordinator) -> None:
    """Approximated by isBoilerConnected; False in the all-electric payload."""
    assert coordinator.is_boiler_opentherm() is False

    connected = make_coordinator({"result": {"isBoilerConnected": True}})
    assert connected.is_boiler_opentherm() is True
