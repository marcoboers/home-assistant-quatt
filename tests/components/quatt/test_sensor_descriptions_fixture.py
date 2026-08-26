"""Fixture-driven invariant tests for the sensor description tables."""
# pylint: disable=import-error,wrong-import-position

from __future__ import annotations

import json
from pathlib import Path

import pytest

from custom_components.quatt.coordinator_local_cic import (
    QuattCicLocalDataUpdateCoordinator,
)
from custom_components.quatt.coordinator_remote_cic import (
    QuattCicRemoteDataUpdateCoordinator,
)
from custom_components.quatt.sensor_descriptions_cic import (
    CIC_SENSORS,
    FLOWMETER_SENSORS,
    THERMOSTAT_SENSORS,
)
from custom_components.quatt.sensor_descriptions_heat import (
    create_heatpump_sensor_entity_descriptions,
)

FIXTURES = Path(__file__).parent / "fixtures"

SENTINEL = object()


def _local_coordinator() -> QuattCicLocalDataUpdateCoordinator:
    coordinator = object.__new__(QuattCicLocalDataUpdateCoordinator)
    coordinator.data = json.loads(
        (FIXTURES / "local_cic_duo_all_electric.json").read_text()
    )
    return coordinator


def _remote_coordinator() -> QuattCicRemoteDataUpdateCoordinator:
    coordinator = object.__new__(QuattCicRemoteDataUpdateCoordinator)
    coordinator.data = json.loads(
        (FIXTURES / "remote_cic_duo_all_electric.json").read_text()
    )
    return coordinator


def _matches_duo_all_electric(description) -> bool:
    """Return True when the description applies to a duo all-electric system."""
    features = description.quatt_features
    return not features.hybrid and not features.opentherm


def _local_descriptions():
    """Yield (table, description) for every local duo all-electric sensor."""
    tables = {
        "CIC_SENSORS": CIC_SENSORS,
        "FLOWMETER_SENSORS": FLOWMETER_SENSORS,
        "THERMOSTAT_SENSORS": THERMOSTAT_SENSORS,
        "HEATPUMP_1": create_heatpump_sensor_entity_descriptions(
            index=0, is_duo=False
        ),
        "HEATPUMP_2": create_heatpump_sensor_entity_descriptions(
            index=1, is_duo=True
        ),
    }
    for table_name, descriptions in tables.items():
        for description in descriptions:
            if description.quatt_features.mobile_api:
                continue  # remote-only entity
            if not _matches_duo_all_electric(description):
                continue
            yield pytest.param(description, id=f"{table_name}:{description.key}")


@pytest.mark.parametrize("description", list(_local_descriptions()))
def test_local_description_keys_resolve_against_fixture(description) -> None:
    """Every applicable local sensor key resolves in a real API payload."""
    coordinator = _local_coordinator()
    if description.computed_key:
        # Computed keys must resolve to a callable coordinator method
        method_name = description.computed_key.rpartition(".")[2]
        assert callable(getattr(coordinator, method_name, None)), (
            f"Computed key {description.computed_key} has no coordinator method"
        )
    else:
        value = coordinator.get_value(description.raw_value_key, SENTINEL)
        assert value is not SENTINEL, (
            f"Raw key {description.raw_value_key} not present in the local payload"
        )


def _remote_descriptions():
    """Yield remote (mobile API) heatpump descriptions for the duo system."""
    tables = {
        "CIC_SENSORS": CIC_SENSORS,
        "HEATPUMP_1": create_heatpump_sensor_entity_descriptions(
            index=0, is_duo=False
        ),
        "HEATPUMP_2": create_heatpump_sensor_entity_descriptions(
            index=1, is_duo=True
        ),
    }
    for table_name, descriptions in tables.items():
        for description in descriptions:
            if not description.quatt_features.mobile_api:
                continue
            if not _matches_duo_all_electric(description):
                continue
            if description.computed_key:
                continue
            yield pytest.param(description, id=f"{table_name}:{description.key}")


@pytest.mark.parametrize("description", list(_remote_descriptions()))
def test_remote_description_keys_resolve_against_fixture(description) -> None:
    """Every applicable remote sensor key resolves in a real API payload."""
    coordinator = _remote_coordinator()
    value = coordinator.get_value(description.raw_value_key, SENTINEL)
    assert value is not SENTINEL, (
        f"Raw key {description.raw_value_key} not present in the remote payload"
    )


def test_no_duplicate_unique_id_keys_per_table() -> None:
    """Within one description table no unique id key may repeat."""
    tables = {
        "CIC_SENSORS": CIC_SENSORS,
        "FLOWMETER_SENSORS": FLOWMETER_SENSORS,
        "THERMOSTAT_SENSORS": THERMOSTAT_SENSORS,
        "HEATPUMP_1": create_heatpump_sensor_entity_descriptions(
            index=0, is_duo=False
        ),
        "HEATPUMP_2": create_heatpump_sensor_entity_descriptions(
            index=1, is_duo=True
        ),
    }
    for table_name, descriptions in tables.items():
        seen: set[str] = set()
        for description in descriptions:
            unique_key = description.quatt_unique_id_key or description.key
            assert unique_key not in seen, (
                f"Duplicate unique id key {unique_key} in {table_name}"
            )
            seen.add(unique_key)
