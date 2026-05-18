"""Functional tests for Quatt entity setup helpers."""
# pylint: disable=import-error

from __future__ import annotations

import logging
from typing import Any

import pytest
from _pytest.logging import LogCaptureFixture

from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.number import NumberDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from custom_components.quatt.__init__ import _sync_chill_device_names
from custom_components.quatt.climate import (
    CLIMATES,
    create_chill_climate_entity_descriptions,
)
from custom_components.quatt.const import DOMAIN, DEVICE_CIC_ID, QuattDeviceKind
from custom_components.quatt.entity_setup import (
    async_setup_entities,
    create_chill_entity_descriptions,
)

pytestmark = pytest.mark.asyncio


class FakeRemoteCoordinator:
    """Minimal remote coordinator for setup tests."""

    def __init__(self, data: dict[str, Any]) -> None:
        """Initialize the fake coordinator."""
        self.data = data

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

    def heatpump_1_active(self) -> bool:
        """Return whether heat pump 1 is active."""
        return False

    def heatpump_2_active(self) -> bool:
        """Return whether heat pump 2 is active."""
        return False

    def all_electric_active(self) -> bool:
        """Return whether the installation is all electric."""
        return False

    def is_boiler_opentherm(self) -> bool:
        """Return whether the boiler uses OpenTherm."""
        return False


def _remote_data(chills: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a minimal remote API payload with the provided chills."""
    return {"result": {"chills": chills}}


async def test_create_chill_entity_descriptions_strip_list_index() -> None:
    """Chill unique IDs should stay stable when the list index changes."""
    coordinator = FakeRemoteCoordinator(
        _remote_data([{"uuid": "uuid-a", "name": "Bedroom"}])
    )

    entity_descriptions, device_names, device_kinds = create_chill_entity_descriptions(
        coordinator,
        CLIMATES,
        create_chill_climate_entity_descriptions,
    )

    description = entity_descriptions["uuid-a"][0]
    assert description.key == "chills.0"
    assert description.quatt_unique_id_key == "chills"
    assert device_names == {"uuid-a": "Bedroom"}
    assert device_kinds == {"uuid-a": QuattDeviceKind.DEVICE}


async def test_create_chill_entity_descriptions_skip_missing_uuid(
    caplog: LogCaptureFixture,
) -> None:
    """A Chill without UUID should be skipped and logged."""
    coordinator = FakeRemoteCoordinator(_remote_data([{"name": "Bedroom"}]))

    with caplog.at_level(logging.ERROR):
        entity_descriptions, device_names, device_kinds = (
            create_chill_entity_descriptions(
                coordinator,
                CLIMATES,
                create_chill_climate_entity_descriptions,
            )
        )

    assert "Cannot set up Chill at index 0: missing UUID" in caplog.text
    assert "Bedroom" not in device_names.values()
    assert device_kinds == {}
    assert "uuid-a" not in entity_descriptions


async def test_async_setup_entities_removes_obsolete_chill_device(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> None:
    """Removing a Chill from the API should remove its entities and device."""
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)

    device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, config_entry.unique_id)},
        name="Quatt",
    )
    chill_device = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, f"{config_entry.unique_id}:uuid-gone")},
        via_device=(DOMAIN, config_entry.unique_id),
        name="Old bedroom",
    )
    entity_registry.async_get_or_create(
        CLIMATE_DOMAIN,
        DOMAIN,
        f"{config_entry.unique_id}:uuid-gone:chills",
        config_entry=config_entry,
        device_id=chill_device.id,
        suggested_object_id="old_bedroom",
    )

    coordinator = FakeRemoteCoordinator(_remote_data([]))
    entities = await async_setup_entities(
        hass=hass,
        coordinator=coordinator,
        entry=config_entry,
        remote=True,
        entity_descriptions=CLIMATES,
        entity_domain=CLIMATE_DOMAIN,
    )

    assert entities == []
    assert (
        device_registry.async_get_device(
            identifiers={(DOMAIN, f"{config_entry.unique_id}:uuid-gone")}
        )
        is None
    )
    assert (
        entity_registry.async_get_entity_id(
            CLIMATE_DOMAIN,
            DOMAIN,
            f"{config_entry.unique_id}:uuid-gone:chills",
        )
        is None
    )


async def test_sync_chill_device_names_updates_registry_name(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> None:
    """Refreshing remote data should rename the Chill device in HA."""
    device_registry = dr.async_get(hass)
    device = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, f"{config_entry.unique_id}:uuid-a")},
        name="Old bedroom",
    )
    coordinator = FakeRemoteCoordinator(
        _remote_data([{"uuid": "uuid-a", "name": "Bedroom chill"}])
    )

    _sync_chill_device_names(hass, config_entry, coordinator)

    assert device_registry.async_get(device.id).name == "Bedroom chill"


async def test_max_water_temperature_number_has_device_class() -> None:
    """The Max water temperature number sensor should be classified as temperature."""
    from custom_components.quatt.number import NUMBERS

    description = NUMBERS[DEVICE_CIC_ID][0]

    assert description.key == "chMaxWaterTemperature"
    assert description.device_class == NumberDeviceClass.TEMPERATURE
