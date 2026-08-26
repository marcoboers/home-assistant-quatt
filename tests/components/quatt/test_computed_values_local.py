"""Tests for the local CIC coordinator computed values (real payload fixture)."""
# pylint: disable=import-error,wrong-import-position

from __future__ import annotations

from copy import deepcopy
import json
import math
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from custom_components.quatt.const import CONVERSION_FACTORS, SupervisoryControlMode
from custom_components.quatt.coordinator_local_cic import (
    QuattCicLocalDataUpdateCoordinator,
)

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> Any:
    """Load a JSON fixture by file name."""
    return json.loads((FIXTURES / name).read_text())


def make_coordinator(
    data: dict | None = None, power_sensor_id: str | None = None
) -> QuattCicLocalDataUpdateCoordinator:
    """Create a coordinator instance without calling __init__."""
    coordinator = object.__new__(QuattCicLocalDataUpdateCoordinator)
    coordinator.data = data if data is not None else {}
    coordinator._power_sensor_id = power_sensor_id  # noqa: SLF001
    return coordinator


@pytest.fixture(name="duo_all_electric_data")
def duo_all_electric_data_fixture() -> dict:
    """Return the duo all-electric local API payload."""
    return load_fixture("local_cic_duo_all_electric.json")


@pytest.fixture(name="coordinator")
def coordinator_fixture(
    duo_all_electric_data: dict,
) -> QuattCicLocalDataUpdateCoordinator:
    """Return a coordinator loaded with the duo all-electric payload."""
    return make_coordinator(deepcopy(duo_all_electric_data))


# ---------------------------------------------------------------------------
# Feature detection
# ---------------------------------------------------------------------------


def test_feature_detection_duo_all_electric(coordinator) -> None:
    """The duo all-electric payload activates hp1, hp2 and all-electric."""
    assert coordinator.heatpump_1_active() is True
    assert coordinator.heatpump_2_active() is True
    assert coordinator.all_electric_active() is True
    # boiler is null in an all-electric installation
    assert coordinator.is_boiler_opentherm() is False


def test_feature_detection_mono_hybrid(duo_all_electric_data: dict) -> None:
    """Removing hp2/hc and adding a boiler flips the feature flags."""
    data = deepcopy(duo_all_electric_data)
    del data["hp2"]
    del data["hc"]
    data["boiler"] = {"otFbChModeActive": False}
    coordinator = make_coordinator(data)

    assert coordinator.heatpump_2_active() is False
    assert coordinator.all_electric_active() is False
    assert coordinator.is_boiler_opentherm() is True


# ---------------------------------------------------------------------------
# Conversion factor lookup
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("temperature", "expected_key"),
    [
        (40, 40),  # exact match
        (21.52, 20),  # nearest below midpoint
        (23.1, 25),  # nearest above midpoint
        (-10, 5),  # clamped to lowest table entry
        (150, 80),  # clamped to highest table entry
        (27.5, 25),  # tie resolves to the first (lower) table entry
    ],
)
def test_get_conversion_factor(coordinator, temperature, expected_key) -> None:
    """The conversion factor is looked up by nearest table temperature."""
    assert coordinator.get_conversion_factor(temperature) == pytest.approx(
        CONVERSION_FACTORS[expected_key]
    )


# ---------------------------------------------------------------------------
# Water delta
# ---------------------------------------------------------------------------


def test_computed_water_delta_duo_spans_both_pumps(coordinator) -> None:
    """Without a parent key a duo system spans hp1 inlet to hp2 outlet."""
    assert coordinator.computed_water_delta() == pytest.approx(21.52 - 18.39)


@pytest.mark.parametrize(
    ("parent_key", "expected"),
    [("hp1", 21.41 - 18.39), ("hp2", 21.52 - 18.09)],
)
def test_computed_water_delta_per_pump(coordinator, parent_key, expected) -> None:
    """A parent key computes the delta over that pump only."""
    assert coordinator.computed_water_delta(parent_key) == pytest.approx(expected)


def test_computed_water_delta_mono_defaults_to_hp1(duo_all_electric_data) -> None:
    """Without hp2 the default delta is computed over hp1."""
    data = deepcopy(duo_all_electric_data)
    del data["hp2"]
    coordinator = make_coordinator(data)
    assert coordinator.computed_water_delta() == pytest.approx(21.41 - 18.39)


def test_computed_water_delta_missing_temperature(duo_all_electric_data) -> None:
    """Missing temperatures return None."""
    data = deepcopy(duo_all_electric_data)
    del data["hp1"]["temperatureWaterIn"]
    coordinator = make_coordinator(data)
    assert coordinator.computed_water_delta("hp1") is None


# ---------------------------------------------------------------------------
# Heat power
# ---------------------------------------------------------------------------


def test_computed_heat_power_standby_is_zero(coordinator) -> None:
    """Standby (mode 0) yields 0.0 heat power."""
    assert coordinator.computed_heat_power() == 0.0


def test_computed_heat_power_unknown_mode(duo_all_electric_data) -> None:
    """A missing supervisory control mode yields None."""
    data = deepcopy(duo_all_electric_data)
    del data["qc"]["supervisoryControlMode"]
    coordinator = make_coordinator(data)
    assert coordinator.computed_heat_power() is None


def test_computed_heat_power_heating_duo(duo_all_electric_data) -> None:
    """Heating mode multiplies delta, flow rate and conversion factor."""
    data = deepcopy(duo_all_electric_data)
    data["qc"]["supervisoryControlMode"] = int(
        SupervisoryControlMode.HEATING_HEATPUMP_ONLY
    )
    data["qc"]["flowRateFiltered"] = 10.0
    coordinator = make_coordinator(data)

    delta = 21.52 - 18.39  # duo: hp2 out - hp1 in
    factor = CONVERSION_FACTORS[20]  # nearest to hp2 water out 21.52
    assert coordinator.computed_heat_power() == pytest.approx(
        round(delta * 10.0 * factor, 2)
    )


def test_computed_heat_power_clamps_negative_to_zero(duo_all_electric_data) -> None:
    """A negative delta (defrost dip) is clamped to 0.0."""
    data = deepcopy(duo_all_electric_data)
    data["qc"]["supervisoryControlMode"] = int(
        SupervisoryControlMode.HEATING_HEATPUMP_PLUS_BOILER
    )
    data["qc"]["flowRateFiltered"] = 10.0
    data["hp2"]["temperatureWaterOut"] = 15.0  # below hp1 water in
    coordinator = make_coordinator(data)
    assert coordinator.computed_heat_power() == 0.0


# ---------------------------------------------------------------------------
# Boiler heat power
# ---------------------------------------------------------------------------


def test_computed_boiler_heat_power_no_boiler(coordinator) -> None:
    """An all-electric installation without boiler yields None."""
    assert coordinator.computed_boiler_heat_power() is None


def test_computed_boiler_heat_power_inactive_boiler(duo_all_electric_data) -> None:
    """An inactive on/off boiler yields 0.0."""
    data = deepcopy(duo_all_electric_data)
    data["boiler"] = {"oTtbTurnOnOffBoilerOn": False}
    coordinator = make_coordinator(data)
    assert coordinator.computed_boiler_heat_power() == 0.0


def test_computed_boiler_heat_power_active_opentherm(duo_all_electric_data) -> None:
    """An active OpenTherm boiler adds (supply - hp out) * flow * factor."""
    data = deepcopy(duo_all_electric_data)
    data["boiler"] = {"otFbChModeActive": True, "otTbCH": True}
    data["qc"]["flowRateFiltered"] = 10.0
    coordinator = make_coordinator(data)

    supply = 24.69  # flowMeter.waterSupplyTemperature
    hp_out = 21.52  # duo: hp2 water out
    factor = CONVERSION_FACTORS[25]  # nearest to supply temperature
    assert coordinator.computed_boiler_heat_power() == pytest.approx(
        round((supply - hp_out) * 10.0 * factor, 2)
    )


# ---------------------------------------------------------------------------
# Power aggregation
# ---------------------------------------------------------------------------


def test_computed_power_input_duo(coordinator) -> None:
    """Duo installations sum both power inputs."""
    assert coordinator.computed_power_input() == pytest.approx(10.3)


def test_computed_power_input_mono(duo_all_electric_data) -> None:
    """Mono installations only count hp1."""
    data = deepcopy(duo_all_electric_data)
    del data["hp2"]
    coordinator = make_coordinator(data)
    assert coordinator.computed_power_input() == pytest.approx(5.15)


def test_computed_power_duo(coordinator) -> None:
    """Both pumps idle: total power is 0."""
    assert coordinator.computed_power() == 0.0


def test_computed_system_power_all_electric(coordinator) -> None:
    """All-electric system power is hc.electricalPower + heatpump power."""
    assert coordinator.computed_system_power() == 0.0


def test_computed_system_power_hybrid(duo_all_electric_data) -> None:
    """Hybrid system power uses the boiler heat power instead."""
    data = deepcopy(duo_all_electric_data)
    del data["hc"]
    data["boiler"] = {"oTtbTurnOnOffBoilerOn": False}
    data["hp1"]["power"] = 1500
    coordinator = make_coordinator(data)
    assert coordinator.computed_system_power() == pytest.approx(1500.0)


# ---------------------------------------------------------------------------
# COP
# ---------------------------------------------------------------------------


def test_computed_cop_without_power_sensor(coordinator) -> None:
    """Without a configured power sensor the COP is None."""
    assert coordinator.computed_cop() is None


def test_computed_cop_with_power_sensor(duo_all_electric_data) -> None:
    """COP is heat power divided by the external power sensor value."""
    data = deepcopy(duo_all_electric_data)
    data["qc"]["supervisoryControlMode"] = int(
        SupervisoryControlMode.HEATING_HEATPUMP_ONLY
    )
    data["qc"]["flowRateFiltered"] = 10.0
    coordinator = make_coordinator(data, power_sensor_id="sensor.hp_power")
    coordinator.hass = SimpleNamespace(
        states=SimpleNamespace(
            get=lambda _: SimpleNamespace(state="18.0", entity_id="sensor.hp_power")
        )
    )

    heat_power = coordinator.computed_heat_power()
    assert coordinator.computed_cop() == pytest.approx(
        round(heat_power / 18.0, 2)
    )


def test_computed_cop_zero_electrical_power(coordinator) -> None:
    """A zero power sensor reading yields None instead of dividing by zero."""
    coordinator._power_sensor_id = "sensor.hp_power"  # noqa: SLF001
    coordinator.hass = SimpleNamespace(
        states=SimpleNamespace(get=lambda _: SimpleNamespace(state="0"))
    )
    assert coordinator.computed_cop() is None


@pytest.mark.parametrize("state", ["unavailable", "unknown", "not-a-number"])
def test_electrical_power_invalid_states(coordinator, state) -> None:
    """Unavailable, unknown and non-numeric sensor states yield None."""
    coordinator._power_sensor_id = "sensor.hp_power"  # noqa: SLF001
    coordinator.hass = SimpleNamespace(
        states=SimpleNamespace(get=lambda _: SimpleNamespace(state=state))
    )
    assert coordinator.electrical_power() is None


def test_electrical_power_missing_entity(coordinator) -> None:
    """A missing sensor entity yields None."""
    coordinator._power_sensor_id = "sensor.hp_power"  # noqa: SLF001
    coordinator.hass = SimpleNamespace(states=SimpleNamespace(get=lambda _: None))
    assert coordinator.electrical_power() is None


# ---------------------------------------------------------------------------
# Quatt COP
# ---------------------------------------------------------------------------


def test_computed_quatt_cop_aggregated_zero_is_positive(coordinator) -> None:
    """0 W output over 10.3 W input yields +0.0, never -0.0."""
    value = coordinator.computed_quatt_cop()
    assert value == 0.0
    assert math.copysign(1, value) == 1.0


def test_computed_quatt_cop_per_pump(duo_all_electric_data) -> None:
    """Per-pump Quatt COP divides that pump's output by its input."""
    data = deepcopy(duo_all_electric_data)
    data["hp1"]["power"] = 3000
    data["hp1"]["powerInput"] = 1000
    coordinator = make_coordinator(data)
    assert coordinator.computed_quatt_cop("hp1") == pytest.approx(3.0)


def test_computed_quatt_cop_zero_input(duo_all_electric_data) -> None:
    """Zero power input yields None instead of dividing by zero."""
    data = deepcopy(duo_all_electric_data)
    data["hp1"]["powerInput"] = 0
    data["hp2"]["powerInput"] = 0
    coordinator = make_coordinator(data)
    assert coordinator.computed_quatt_cop() is None


# ---------------------------------------------------------------------------
# Defrost detection
# ---------------------------------------------------------------------------


def test_computed_defrost_requires_parent_key(coordinator) -> None:
    """Defrost is a per-pump computation; no parent key yields None."""
    assert coordinator.computed_defrost() is None


def test_computed_defrost_standby_is_false(coordinator) -> None:
    """Standby mode is never a defrost state."""
    assert coordinator.computed_defrost("hp1") is False


def test_computed_defrost_detected(duo_all_electric_data) -> None:
    """Heating mode + negative power + negative delta means defrosting."""
    data = deepcopy(duo_all_electric_data)
    data["qc"]["supervisoryControlMode"] = int(
        SupervisoryControlMode.HEATING_HEATPUMP_ONLY
    )
    data["hp1"]["power"] = -500
    data["hp1"]["temperatureWaterIn"] = 25.0
    data["hp1"]["temperatureWaterOut"] = 22.0
    coordinator = make_coordinator(data)
    assert coordinator.computed_defrost("hp1") is True


@pytest.mark.parametrize(
    ("power", "water_out"),
    [
        (-0.5, 22.0),  # power dip too small
        (-500, 24.5),  # delta not negative enough
    ],
)
def test_computed_defrost_boundaries(duo_all_electric_data, power, water_out) -> None:
    """Both the power and the delta threshold must be crossed."""
    data = deepcopy(duo_all_electric_data)
    data["qc"]["supervisoryControlMode"] = int(
        SupervisoryControlMode.HEATING_HEATPUMP_ONLY
    )
    data["hp1"]["power"] = power
    data["hp1"]["temperatureWaterIn"] = 25.0
    data["hp1"]["temperatureWaterOut"] = water_out
    coordinator = make_coordinator(data)
    assert coordinator.computed_defrost("hp1") is False


# ---------------------------------------------------------------------------
# Text mappings
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        (0, "Standby"),
        (2, "Heating - heatpump only"),
        (6, "Cooling"),
        (96, "Anti-freeze protection - boiler on"),
        (100, "Commissioning modes"),
        (245, "Commissioning modes"),
        (42, None),  # unknown code below 100
    ],
)
def test_computed_supervisory_control_mode(
    duo_all_electric_data, mode, expected
) -> None:
    """Numeric supervisory control modes map to their descriptions."""
    data = deepcopy(duo_all_electric_data)
    data["qc"]["supervisoryControlMode"] = mode
    coordinator = make_coordinator(data)
    assert coordinator.computed_supervisory_control_mode() == expected


@pytest.mark.parametrize(
    ("mode", "expected"),
    [(0, "Idle"), (8, "Discharge"), (99, None)],
)
def test_computed_all_e_supervisory_control_mode(
    duo_all_electric_data, mode, expected
) -> None:
    """All-electric supervisory control modes map to their descriptions."""
    data = deepcopy(duo_all_electric_data)
    data["qcAllE"]["allESupervisoryControlMode"] = mode
    coordinator = make_coordinator(data)
    assert coordinator.computed_all_e_supervisory_control_mode() == expected


def test_computed_tariff_types_dynamic(coordinator) -> None:
    """The fixture uses dynamic tariffs for electricity and gas."""
    assert coordinator.computed_electricity_tariff_type() == "Dynamic tariff"
    assert coordinator.computed_gas_tariff_type() == "Dynamic tariff"


@pytest.mark.parametrize(
    ("electricity", "gas", "expected_electricity", "expected_gas"),
    [
        (0, 0, "Single tariff", "Single tariff"),
        (1, 1, "Double tariff", None),  # gas has no double tariff
        (5, 5, None, None),
    ],
)
def test_computed_tariff_types_variants(
    duo_all_electric_data, electricity, gas, expected_electricity, expected_gas
) -> None:
    """Tariff type codes map to descriptions; unknown codes yield None."""
    data = deepcopy(duo_all_electric_data)
    data["system"]["electricityTariffType"] = electricity
    data["system"]["gasTariffType"] = gas
    coordinator = make_coordinator(data)
    assert coordinator.computed_electricity_tariff_type() == expected_electricity
    assert coordinator.computed_gas_tariff_type() == expected_gas


# ---------------------------------------------------------------------------
# get_value lookup behaviour
# ---------------------------------------------------------------------------


def test_get_value_null_section_returns_default(coordinator) -> None:
    """Dot paths through a null section (boiler) return the default."""
    sentinel = object()
    assert coordinator.get_value("boiler.otFbChModeActive", sentinel) is sentinel


def test_get_value_missing_optional_sections_stay_silent(
    duo_all_electric_data, caplog: pytest.LogCaptureFixture
) -> None:
    """Missing hp2/boiler/hc sections do not log warnings; others do."""
    data = deepcopy(duo_all_electric_data)
    del data["hp2"]
    del data["hc"]
    coordinator = make_coordinator(data)

    with caplog.at_level("WARNING"):
        assert coordinator.get_value("hp2.power") is None
        assert coordinator.get_value("hc.electricalPower") is None
    assert caplog.text == ""

    with caplog.at_level("WARNING"):
        assert coordinator.get_value("nonexistent.section") is None
    assert "nonexistent" in caplog.text
