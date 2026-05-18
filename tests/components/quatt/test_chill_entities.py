"""Functional tests for Quatt Chill entities."""
# pylint: disable=import-error

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
from pytest import MonkeyPatch

from homeassistant.components.climate import HVACMode
from homeassistant.config_entries import ConfigEntry

from custom_components.quatt import entity_climate
from custom_components.quatt.climate import create_chill_climate_entity_descriptions
from custom_components.quatt.const import QuattDeviceKind
from custom_components.quatt.entity_climate import QuattChillClimate
from custom_components.quatt.entity_sensor import QuattChillSensor
from custom_components.quatt.sensor_descriptions_chill import (
    create_chill_sensor_entity_descriptions,
)

pytestmark = pytest.mark.asyncio


class FakeRemoteClient:
    """Minimal Chill remote client for behavior tests."""

    def __init__(self) -> None:
        """Initialize the fake remote client."""
        self.actions: list[tuple[str, dict[str, Any]]] = []

    async def update_chill_action(self, chill_uuid: str, data: dict[str, Any]) -> bool:
        """Record a Chill action and report success."""
        self.actions.append((chill_uuid, data.copy()))
        return True


class FakeRemoteCoordinator:
    """Minimal remote coordinator for Chill behavior tests."""

    def __init__(
        self,
        config_entry: ConfigEntry,
        data: dict[str, Any],
        client: FakeRemoteClient | None = None,
    ) -> None:
        """Initialize the fake coordinator."""
        self.config_entry = config_entry
        self.data = data
        self.client = client
        self.last_update_success = True

    def async_add_listener(self, _update_callback) -> Any:
        """Satisfy CoordinatorEntity construction."""
        return lambda: None

    def get_value(self, value_path: str, default: Any | None = None) -> Any:
        """Return a remote API value using Quatt's dot-notation lookup."""
        parts = value_path.split(".")
        current_node: Any = self.data

        if isinstance(current_node, dict) and "result" in current_node:
            current_node = current_node["result"]

        for part in parts:
            if current_node is None:
                return default
            if isinstance(current_node, dict) and part in current_node:
                current_node = current_node[part]
                continue
            if isinstance(current_node, list):
                try:
                    current_node = current_node[int(part)]
                except (ValueError, IndexError):
                    return default
                continue
            return default

        return current_node

    def async_set_updated_data(self, data: dict[str, Any]) -> None:
        """Store optimistic Chill updates."""
        self.data = data


def _remote_data(chills: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a minimal remote API payload with the provided chills."""
    return {"result": {"chills": chills}}


async def test_chill_sensor_tracks_uuid_after_reordering(
    config_entry: ConfigEntry,
) -> None:
    """A Chill sensor should follow the Chill UUID, not the list index."""
    coordinator = FakeRemoteCoordinator(
        config_entry,
        _remote_data(
            [
                {"uuid": "uuid-a", "status": "COOLING"},
                {"uuid": "uuid-b", "status": "HEATING"},
            ]
        ),
    )
    description = create_chill_sensor_entity_descriptions(0)[7]
    sensor = QuattChillSensor(
        device_name="Bedroom",
        device_id="uuid-a",
        sensor_key=description.key,
        coordinator=coordinator,
        entity_description=description,
        device_kind=QuattDeviceKind.DEVICE,
    )

    assert sensor.native_value == "Cooling"

    coordinator.data = _remote_data(
        [
            {"uuid": "uuid-b", "status": "OFF"},
            {"uuid": "uuid-a", "status": "HEATING"},
        ]
    )

    assert sensor.native_value == "Heating"


async def test_chill_climate_tracks_uuid_after_reordering(
    config_entry: ConfigEntry,
) -> None:
    """A Chill climate entity should read state from the matching UUID."""
    coordinator = FakeRemoteCoordinator(
        config_entry,
        _remote_data(
            [
                {
                    "uuid": "uuid-a",
                    "status": "COOLING",
                    "isOn": {"value": True},
                    "mode": "COOLING",
                    "ambientTemperature": 21.5,
                },
                {
                    "uuid": "uuid-b",
                    "status": "HEATING",
                    "isOn": {"value": True},
                    "mode": "HEATING",
                    "ambientTemperature": 19.0,
                },
            ]
        ),
    )
    description = create_chill_climate_entity_descriptions(0)[0]
    climate = QuattChillClimate(
        device_name="Bedroom",
        device_id="uuid-a",
        sensor_key=description.key,
        coordinator=coordinator,
        entity_description=description,
        device_kind=QuattDeviceKind.DEVICE,
    )

    assert climate.hvac_mode is HVACMode.COOL
    assert climate.current_temperature == 21.5

    coordinator.data = _remote_data(
        [
            {
                "uuid": "uuid-b",
                "status": "OFF",
                "isOn": {"value": False},
                "mode": "COOLING",
                "ambientTemperature": 18.0,
            },
            {
                "uuid": "uuid-a",
                "status": "HEATING",
                "isOn": {"value": True},
                "mode": "HEATING",
                "ambientTemperature": 23.0,
            },
        ]
    )

    assert climate.hvac_mode is HVACMode.HEAT
    assert climate.current_temperature == 23.0


@pytest.mark.parametrize(
    ("initial_chill", "target_mode", "expected_actions", "expected_status"),
    [
        pytest.param(
            {
                "uuid": "uuid-a",
                "status": "OFF",
                "isOn": {"value": False},
                "mode": "HEATING",
            },
            HVACMode.COOL,
            [
                ("uuid-a", {"type": "SET_ON_OFF", "on": True}),
                ("uuid-a", {"type": "SET_MODE", "mode": "COOLING"}),
            ],
            "COOLING",
            id="off-to-cool",
        ),
        pytest.param(
            {
                "uuid": "uuid-a",
                "status": "COOLING",
                "isOn": {"value": True},
                "mode": "COOLING",
            },
            HVACMode.HEAT,
            [("uuid-a", {"type": "SET_MODE", "mode": "HEATING"})],
            "HEATING",
            id="cool-to-heat",
        ),
    ],
)
async def test_chill_climate_hvac_actions_follow_user_flow(
    monkeypatch: MonkeyPatch,
    config_entry: ConfigEntry,
    initial_chill: dict[str, Any],
    target_mode: HVACMode,
    expected_actions: list[tuple[str, dict[str, Any]]],
    expected_status: str,
) -> None:
    """Setting HVAC mode should call the Chill API in user-facing order."""
    monkeypatch.setattr(entity_climate, "QuattCicRemoteApiClient", FakeRemoteClient)
    client = FakeRemoteClient()
    coordinator = FakeRemoteCoordinator(
        config_entry,
        _remote_data([deepcopy(initial_chill)]),
        client=client,
    )
    description = create_chill_climate_entity_descriptions(0)[0]
    climate = QuattChillClimate(
        device_name="Bedroom",
        device_id="uuid-a",
        sensor_key=description.key,
        coordinator=coordinator,
        entity_description=description,
        device_kind=QuattDeviceKind.DEVICE,
    )

    await climate.async_set_hvac_mode(target_mode)

    assert client.actions == expected_actions
    assert climate.hvac_mode is target_mode
    assert coordinator.get_value("chills.0.status") == expected_status
    assert coordinator.get_value("chills.0.isOn.value") is True
