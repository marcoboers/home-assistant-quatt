"""Tests for Quatt device links and hub registration."""

from collections.abc import Iterator
from contextlib import ExitStack
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from pytest import FixtureRequest, LogCaptureFixture, MonkeyPatch

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

# tests/conftest.py exposes the core test helpers at runtime.
from tests.common import MockConfigEntry  # pylint: disable=import-error,no-name-in-module

from custom_components import quatt
from custom_components.quatt import device
from custom_components.quatt.const import (
    CONF_ENERGY_PASSWORD,
    CONF_ENERGY_USERNAME,
    CONF_HOME_BATTERY_SERIAL,
    CONF_LOCAL_CIC,
    CONF_REMOTE_CIC,
    DOMAIN,
    QuattDeviceKind,
)
from custom_components.quatt.entity import QuattEntity


@pytest.mark.parametrize(
    ("major", "minor", "expected"),
    [
        pytest.param(2025, 5, {"via_device": (DOMAIN, "CIC-test")}, id="minimum"),
        pytest.param(2026, 7, {"via_device": (DOMAIN, "CIC-test")}, id="last-legacy"),
        pytest.param(2026, 8, {"via_device_id": "registry-id"}, id="first-modern"),
        pytest.param(2026, 9, {"via_device_id": "registry-id"}, id="modern"),
        pytest.param(2027, 1, {"via_device_id": "registry-id"}, id="next-year"),
        pytest.param(2027, 8, {"via_device_id": "registry-id"}, id="legacy-removed"),
    ],
)
def test_hub_link_info(
    monkeypatch: MonkeyPatch,
    major: int,
    minor: int,
    expected: dict[str, str | tuple[str, str]],
) -> None:
    """Pass exactly the device link parameter supported by the running version."""
    monkeypatch.setattr(device, "MAJOR_VERSION", major)
    monkeypatch.setattr(device, "MINOR_VERSION", minor)

    assert device.hub_link_info("CIC-test", "registry-id") == expected


@pytest.fixture(name="mock_coordinators")
def mock_coordinators_fixture(
    config_entry: MockConfigEntry,
) -> Iterator[dict[str, MagicMock]]:
    """Replace API I/O while exercising the real config entry setup."""
    coordinator_classes = {
        "cic_local": "QuattCicLocalDataUpdateCoordinator",
        "cic_remote": "QuattCicRemoteDataUpdateCoordinator",
        "home_battery": "QuattHomeBatteryDataUpdateCoordinator",
        "energy": "QuattEnergyDataUpdateCoordinator",
    }
    with ExitStack() as stack:
        coordinators = {}
        for key, class_name in coordinator_classes.items():
            coordinator = MagicMock(spec=getattr(quatt, class_name))
            coordinator.config_entry = config_entry
            coordinators[key] = coordinator
            stack.enter_context(
                patch.object(quatt, class_name, return_value=coordinator)
            )
        stack.enter_context(patch.object(quatt.Store, "async_load", return_value={}))
        stack.enter_context(patch.object(quatt, "async_get_clientsession"))
        stack.enter_context(patch.object(quatt, "async_create_clientsession"))
        stack.enter_context(patch.object(quatt, "_get_or_create_auth_client"))
        stack.enter_context(patch.object(quatt, "_register_services"))
        remote_client = stack.enter_context(
            patch.object(quatt, "QuattCicRemoteApiClient")
        )
        remote_client.return_value.authenticate = AsyncMock(return_value=True)
        yield coordinators


@dataclass(frozen=True)
class HubSetup:
    """Config entry settings and coordinators expected for a hub."""

    entry_data: dict[str, str]
    unique_id: str | None
    active_coordinators: tuple[str, ...]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "hub_setup",
    [
        pytest.param(
            HubSetup({CONF_LOCAL_CIC: "192.0.2.1"}, "CIC-test", ("cic_local",)),
            id="local-cic",
        ),
        pytest.param(
            HubSetup(
                {CONF_LOCAL_CIC: "192.0.2.1", CONF_REMOTE_CIC: "CIC-test"},
                "CIC-test",
                ("cic_local", "cic_remote"),
            ),
            id="local-and-remote-cic",
        ),
        pytest.param(
            HubSetup(
                {CONF_HOME_BATTERY_SERIAL: "battery-test"},
                "BAT-test",
                ("home_battery",),
            ),
            id="home-battery",
        ),
        pytest.param(
            HubSetup(
                {
                    CONF_ENERGY_USERNAME: "test@example.com",
                    CONF_ENERGY_PASSWORD: "test",
                },
                "energy-test",
                ("energy",),
            ),
            id="energy",
        ),
        pytest.param(
            HubSetup({CONF_LOCAL_CIC: "192.0.2.1"}, None, ("cic_local",)),
            id="entry-id-fallback",
        ),
        pytest.param(
            HubSetup({CONF_LOCAL_CIC: "192.0.2.1"}, " CIC-test ", ("cic_local",)),
            id="trimmed-id",
        ),
    ],
)
async def test_hub_registered_before_platforms_and_reused_on_reload(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_coordinators: dict[str, MagicMock],
    caplog: LogCaptureFixture,
    hub_setup: HubSetup,
) -> None:
    """Fresh setup and reload preserve device IDs, entity IDs and hub metadata."""
    hass.config_entries.async_update_entry(
        config_entry, data=hub_setup.entry_data, unique_id=hub_setup.unique_id
    )
    registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    hub_identifier = (hub_setup.unique_id or config_entry.entry_id).strip()
    device_ids: list[str] = []
    entity_ids: list[str] = []
    unrelated_entry = MockConfigEntry(domain=DOMAIN, unique_id="CIC-other", data={})
    unrelated_entry.add_to_hass(hass)
    unrelated_hub = registry.async_get_or_create(
        config_entry_id=unrelated_entry.entry_id,
        identifiers={(DOMAIN, "CIC-other")},
    )

    async def setup_platforms(entry: ConfigEntry, platforms: list[Platform]) -> None:
        assert entry is config_entry
        assert platforms == quatt.PLATFORMS
        coordinator = hass.data[DOMAIN][entry.entry_id][
            hub_setup.active_coordinators[0]
        ]
        hub = registry.async_get(coordinator.hub_device_id)
        assert hub is not None
        assert hub.identifiers == {(DOMAIN, hub_identifier)}
        assert hub.id != unrelated_hub.id
        assert hub.via_device_id is None
        for key in hub_setup.active_coordinators:
            assert mock_coordinators[key].hub_device_id == hub.id
        for kind in (
            QuattDeviceKind.DEVICE,
            QuattDeviceKind.SERVICE,
            QuattDeviceKind.HUB,
        ):
            entity = QuattEntity(
                device_name=kind.value,
                device_id=kind.value,
                sensor_key="value",
                coordinator=coordinator,
                device_kind=kind,
            )
            assert entity.unique_id == f"{hub_identifier}:{kind.value}:value"
            registered_device = registry.async_get_or_create(
                config_entry_id=entry.entry_id, **entity.device_info
            )
            device_ids.append(registered_device.id)
            registered_entity = entity_registry.async_get_or_create(
                "sensor",
                DOMAIN,
                entity.unique_id,
                config_entry=entry,
                device_id=registered_device.id,
            )
            entity_ids.append(registered_entity.entity_id)
        assert registry.async_get(device_ids[-3]).via_device_id == hub.id
        assert registry.async_get(device_ids[-2]).via_device_id == hub.id
        assert (
            registry.async_get(device_ids[-2]).entry_type is dr.DeviceEntryType.SERVICE
        )
        assert device_ids[-1] == hub.id

    with (
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            side_effect=setup_platforms,
        ),
        patch.object(hass.config_entries, "async_unload_platforms", return_value=True),
    ):
        assert await quatt.async_setup_entry(hass, config_entry)
        hub_id = device_ids[-1]
        registry.async_update_device(hub_id, name_by_user="My Quatt")
        assert await quatt.async_unload_entry(hass, config_entry)
        assert await quatt.async_setup_entry(hass, config_entry)

    assert device_ids[:3] == device_ids[3:]
    assert entity_ids[:3] == entity_ids[3:]
    assert len(dr.async_entries_for_config_entry(registry, config_entry.entry_id)) == 3
    assert registry.async_get(hub_id).name_by_user == "My Quatt"
    assert registry.async_get(hub_id).via_device_id is None
    assert "deprecated `via_device`" not in caplog.text


@pytest.fixture(
    name="expected_modern_lookup_calls",
    params=[
        pytest.param((2025, 5, 0), id="minimum"),
        pytest.param((2026, 7, 0), id="last-legacy"),
        pytest.param((2026, 8, 1), id="first-modern"),
        pytest.param((2027, 1, 1), id="next-year"),
    ],
)
def expected_modern_lookup_calls_fixture(
    request: FixtureRequest, monkeypatch: MonkeyPatch
) -> int:
    """Select the HA lookup API for each supported version boundary."""
    major, minor, expected_calls = request.param
    monkeypatch.setattr(device, "MAJOR_VERSION", major)
    monkeypatch.setattr(device, "MINOR_VERSION", minor)
    return expected_calls


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("identifier", "expected_name"),
    [
        pytest.param("owned", "Bedroom", id="found"),
        pytest.param("foreign", None, id="other-config-entry"),
        pytest.param("missing", None, id="missing"),
    ],
)
async def test_device_lookup_uses_supported_api_and_own_config_entry(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    expected_modern_lookup_calls: int,
    identifier: str,
    expected_name: str | None,
) -> None:
    """Both APIs find owned devices and exclude missing or foreign devices."""
    registry = dr.async_get(hass)
    registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, "owned")},
        name="Bedroom",
    )
    other_entry = MockConfigEntry(domain=DOMAIN, unique_id="CIC-other", data={})
    other_entry.add_to_hass(hass)
    registry.async_get_or_create(
        config_entry_id=other_entry.entry_id,
        identifiers={(DOMAIN, "foreign")},
        name="Other bedroom",
    )

    with patch.object(
        registry,
        "async_get_device_by_identifier",
        wraps=registry.async_get_device_by_identifier,
    ) as modern_lookup:
        result = device.async_get_device_by_identifier(
            registry, (DOMAIN, identifier), config_entry.entry_id
        )

    assert getattr(result, "name", None) == expected_name
    assert (
        modern_lookup.call_args_list
        == [call((DOMAIN, identifier), config_entry.entry_id)]
        * expected_modern_lookup_calls
    )
