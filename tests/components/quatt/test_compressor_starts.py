"""Tests for observed compressor starts and their persistent state."""
# pylint: disable=import-error,no-name-in-module

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
import json
import logging
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import current_entry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import frame, device_registry as dr, entity_registry as er
from homeassistant.helpers.entity_platform import EntityPlatform
from homeassistant.helpers.storage import Store
from homeassistant.loader import DATA_CUSTOM_COMPONENTS, Integration

from tests.common import MockConfigEntry, async_test_home_assistant

from custom_components.quatt.api import QuattApiClient, QuattApiClientCommunicationError
from custom_components.quatt.compressor_starts import (
    CompressorStartCounter,
    CompressorStartState,
)
from custom_components.quatt import async_remove_entry
from custom_components.quatt.const import (
    DOMAIN,
    DEVICE_HEATPUMP_1_ID,
    DEVICE_HEATPUMP_2_ID,
    QuattDeviceKind,
)
from custom_components.quatt.entity_setup import async_setup_entities
from custom_components.quatt.sensor import SENSORS
from custom_components.quatt.sensor_compressor_starts import (
    QuattCompressorTrackingSensor,
    QuattCompressorTrackingSinceSensor,
    QuattObservedCompressorStartsSensor,
)
from custom_components.quatt.sensor_descriptions_heat import (
    create_heatpump_sensor_entity_descriptions,
)
from custom_components.quatt.coordinator_remote_cic import (
    QuattCicRemoteDataUpdateCoordinator,
)

NOW = datetime(2026, 9, 8, 12, tzinfo=UTC)


def payload(hp1: object, hp2: object = None) -> dict:
    """Return a duo remote API response with independent frequencies."""
    return {
        "result": {
            "heatPumps": [{"compressorFrequency": hp1}, {"compressorFrequency": hp2}]
        }
    }


@pytest.mark.parametrize(
    ("frequency", "count", "running"),
    [
        pytest.param(0, 0, False, id="stopped"),
        pytest.param(0.9, 0, False, id="residual-frequency"),
        pytest.param(1, 1, True, id="threshold"),
        pytest.param(30, 1, True, id="already-running"),
        pytest.param("30", 1, True, id="numeric-string"),
    ],
)
def test_first_measurement(frequency: object, count: int, running: bool) -> None:
    """The first valid observation starts tracking and counts a running unit."""
    state = CompressorStartState()
    assert state.update(frequency, NOW)
    assert state == CompressorStartState(count, running, NOW.isoformat())


@pytest.mark.parametrize(
    "frequency",
    [
        pytest.param(None, id="missing"),
        pytest.param("unavailable", id="unavailable"),
        pytest.param("unknown", id="unknown"),
        pytest.param("", id="empty"),
        pytest.param(True, id="boolean"),
        pytest.param(-1, id="negative"),
        pytest.param(float("nan"), id="nan"),
        pytest.param(float("inf"), id="infinity"),
        pytest.param("NaN", id="nan-string"),
        pytest.param([], id="list"),
        pytest.param({}, id="mapping"),
    ],
)
def test_invalid_measurements_preserve_state(frequency: object) -> None:
    """Invalid readings neither initialize tracking nor manufacture stops."""
    uninitialized = CompressorStartState()
    assert not uninitialized.update(frequency, NOW)
    assert uninitialized == CompressorStartState()
    running = CompressorStartState(4, True, NOW.isoformat())
    assert not running.update(frequency, NOW + timedelta(minutes=1))
    assert not running.update(40, NOW + timedelta(minutes=2))
    assert running == CompressorStartState(4, True, NOW.isoformat())


def test_only_transitions_count() -> None:
    """Modulation does not count; even a short observed stop remains a stop."""
    state = CompressorStartState()
    state.update(0, NOW)
    state.update(30, NOW + timedelta(minutes=1))
    assert not state.update(50, NOW + timedelta(minutes=2))
    state.update(0, NOW + timedelta(minutes=3))
    state.update(30, NOW + timedelta(minutes=3, seconds=30))
    assert state == CompressorStartState(2, True, NOW.isoformat())


@pytest.fixture(name="counter")
def counter_fixture(hass: HomeAssistant, tmp_path: Path) -> CompressorStartCounter:
    """Use actual HA storage in a temporary configuration directory."""
    hass.config.config_dir = str(tmp_path)
    return CompressorStartCounter(hass, "test-entry")


@pytest.mark.asyncio
async def test_independent_counters_and_reload(
    hass: HomeAssistant, counter: CompressorStartCounter, tmp_path: Path
) -> None:
    """Persist starts and stops before reloading, including tracking timestamps."""
    await counter.async_update(payload(30, 0), NOW)
    await counter.async_update(payload(40, 30), NOW + timedelta(minutes=1))
    await counter.async_update(payload(0, None), NOW + timedelta(minutes=2))
    path = tmp_path / ".storage" / "quatt.compressor_starts.test-entry"
    saved = json.loads(path.read_text())["data"]
    assert saved == {
        "hp1": {"count": 1, "running": False, "tracking_since": NOW.isoformat()},
        "hp2": {"count": 1, "running": True, "tracking_since": NOW.isoformat()},
    }

    reloaded = CompressorStartCounter(hass, "test-entry")
    await reloaded.async_update(payload(30, 45), NOW + timedelta(minutes=3))
    assert reloaded.states == [
        CompressorStartState(2, True, NOW.isoformat()),
        CompressorStartState(1, True, NOW.isoformat()),
    ]


@pytest.mark.asyncio
async def test_saves_only_changes(counter: CompressorStartCounter) -> None:
    """Unchanged polls and missing data do not write storage repeatedly."""
    with patch.object(Store, "async_save") as save:
        await counter.async_update(payload(0), NOW)
        await counter.async_update(payload(0), NOW)
        await counter.async_update(payload(None), NOW)
        assert save.call_count == 1
        await counter.async_update(payload(30), NOW)
        await counter.async_update(payload(40), NOW)
        assert save.call_count == 2
        await counter.async_update(payload(0), NOW)
        assert save.call_count == 3


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "data",
    [
        pytest.param(None, id="no-response"),
        pytest.param({}, id="missing-pumps"),
        pytest.param({"result": None}, id="null-result"),
        pytest.param({"heatPumps": None}, id="null-pumps"),
        pytest.param({"heatPumps": {}}, id="invalid-pumps"),
        pytest.param({"heatPumps": [None, {}]}, id="missing-frequency"),
    ],
)
async def test_incomplete_response_preserves_counts(
    counter: CompressorStartCounter, data: object
) -> None:
    """Missing pumps or invalid payloads cannot reset or initialize counters."""
    await counter.async_update(payload(30), NOW)
    await counter.async_update(data, NOW + timedelta(minutes=1))
    await counter.async_update(payload(30), NOW + timedelta(minutes=2))
    assert counter.states == [
        CompressorStartState(1, True, NOW.isoformat()),
        CompressorStartState(),
    ]


@pytest.mark.asyncio
async def test_config_entries_do_not_share_storage(
    hass: HomeAssistant, counter: CompressorStartCounter
) -> None:
    """Separate CICs retain their own counts even when both expose HP1."""
    other = CompressorStartCounter(hass, "other-entry")
    await counter.async_update(payload(30), NOW)
    await other.async_update(payload(0), NOW)
    await other.async_load()
    assert other.states[0].count == 0
    await counter.async_remove()
    restored_other = CompressorStartCounter(hass, "other-entry")
    await restored_other.async_load()
    assert restored_other.states[0] == CompressorStartState(0, False, NOW.isoformat())
    removed = CompressorStartCounter(hass, "test-entry")
    await removed.async_update(payload(30), NOW + timedelta(days=1))
    assert removed.states[0].tracking_since == (NOW + timedelta(days=1)).isoformat()


@asynccontextmanager
async def running_home_assistant(config_dir: Path) -> AsyncIterator[HomeAssistant]:
    """Start a test instance and shut it down before reopening its storage."""
    async with async_test_home_assistant(config_dir=str(config_dir)) as hass:
        try:
            yield hass
        finally:
            await hass.async_stop(force=True)


@pytest.mark.asyncio
async def test_restart_and_backup_restore(tmp_path: Path) -> None:
    """A new HA instance restores disk data, including an older backup snapshot."""
    original_dir = tmp_path / "original"
    restore_dir = tmp_path / "restored"
    async with running_home_assistant(original_dir) as first_hass:
        counter = CompressorStartCounter(first_hass, "saved-entry")
        await counter.async_update(payload(30, 0), NOW)
        storage_file = original_dir / ".storage" / "quatt.compressor_starts.saved-entry"
        backup_bytes = storage_file.read_bytes()
        await counter.async_update(payload(0, 0), NOW + timedelta(minutes=1))
        await counter.async_update(payload(30, 0), NOW + timedelta(minutes=2))

    async with running_home_assistant(original_dir) as restarted_hass:
        counter = CompressorStartCounter(restarted_hass, "saved-entry")
        await counter.async_update(payload(40, 0), NOW + timedelta(minutes=3))
        assert counter.states[0] == CompressorStartState(2, True, NOW.isoformat())

    restored_file = restore_dir / ".storage" / storage_file.name
    restored_file.parent.mkdir(parents=True)
    restored_file.write_bytes(backup_bytes)
    async with running_home_assistant(restore_dir) as restored_hass:
        counter = CompressorStartCounter(restored_hass, "saved-entry")
        await counter.async_update(payload(40, 0), NOW + timedelta(days=1))
        assert counter.states[0] == CompressorStartState(1, True, NOW.isoformat())


@pytest.fixture(name="remote_coordinator")
def remote_coordinator_fixture(
    hass: HomeAssistant, config_entry: MockConfigEntry, tmp_path: Path
) -> Iterator[QuattCicRemoteDataUpdateCoordinator]:
    """Run a real remote coordinator with only network I/O mocked."""
    hass.config.config_dir = str(tmp_path)
    frame.async_setup(hass)
    token = current_entry.set(config_entry)
    client = AsyncMock(spec=QuattApiClient)
    try:
        coordinator = QuattCicRemoteDataUpdateCoordinator(
            hass, timedelta(minutes=1), client
        )
        coordinator.hub_device_id = "hub-registry-id"
        yield coordinator
    finally:
        current_entry.reset(token)


@pytest.mark.asyncio
async def test_coordinator_counts_without_entities_or_extra_requests(
    remote_coordinator: QuattCicRemoteDataUpdateCoordinator,
) -> None:
    """Counting uses existing polls, including the first, without sensor listeners."""
    remote_coordinator.client.async_get_data.side_effect = [
        payload(30, 0),
        payload(40, 0),
        payload(0, 30),
        payload(30, 40),
    ]
    await remote_coordinator.async_refresh()
    await remote_coordinator.async_refresh()
    await remote_coordinator.async_refresh()
    await remote_coordinator.async_refresh()
    assert [state.count for state in remote_coordinator.compressor_starts.states] == [
        2,
        1,
    ]
    assert remote_coordinator.client.async_get_data.await_count == 4
    assert remote_coordinator.update_interval == timedelta(minutes=1)


@pytest.mark.asyncio
async def test_api_failure_does_not_create_a_stop(
    remote_coordinator: QuattCicRemoteDataUpdateCoordinator,
) -> None:
    """A connection outage cannot cause a continuously running unit to count twice."""
    remote_coordinator.client.async_get_data.side_effect = [
        payload(30),
        QuattApiClientCommunicationError("offline"),
        payload(40),
    ]
    await remote_coordinator.async_refresh()
    await remote_coordinator.async_refresh()
    assert not remote_coordinator.last_update_success
    await remote_coordinator.async_refresh()
    assert remote_coordinator.last_update_success
    assert remote_coordinator.compressor_starts.states[0].count == 1


def make_sensor(
    coordinator: QuattCicRemoteDataUpdateCoordinator,
    index: int,
    translation_key: str = "observed_compressor_starts",
) -> QuattCompressorTrackingSensor:
    """Construct a tracking sensor using the production description and factory."""
    description = next(
        desc
        for desc in create_heatpump_sensor_entity_descriptions(index, index == 1)
        if desc.translation_key == translation_key
    )
    return description.quatt_entity_class(
        device_name=f"Heatpump {index + 1}",
        device_id=(DEVICE_HEATPUMP_1_ID, DEVICE_HEATPUMP_2_ID)[index],
        sensor_key=description.key,
        coordinator=coordinator,
        entity_description=description,
        device_kind=QuattDeviceKind.DEVICE,
    )


@pytest.mark.asyncio
async def test_sensor_reading_is_passive(
    remote_coordinator: QuattCicRemoteDataUpdateCoordinator,
) -> None:
    """Reading a sensor cannot count starts or initialize an unseen compressor."""
    hp1 = make_sensor(remote_coordinator, 0)
    hp2 = make_sensor(remote_coordinator, 1)
    assert hp1.native_value is None
    assert hp1.extra_state_attributes == {"tracking_since": None}
    await remote_coordinator.compressor_starts.async_update(payload(30), NOW)
    assert hp1.native_value == 1
    assert hp1.native_value == 1
    assert hp2.native_value is None
    assert hp1.extra_state_attributes == {"tracking_since": NOW.isoformat()}
    recreated = make_sensor(remote_coordinator, 0)
    assert recreated.native_value == 1
    assert recreated.unique_id == hp1.unique_id


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "index",
    [pytest.param(0, id="hp1"), pytest.param(1, id="hp2")],
)
@pytest.mark.parametrize(
    ("translation_key", "expected"),
    [
        pytest.param("observed_compressor_starts", 1, id="count"),
        pytest.param("compressor_tracking_since", NOW, id="tracking-since"),
    ],
)
async def test_tracking_sensors_do_not_query_api_values(
    remote_coordinator: QuattCicRemoteDataUpdateCoordinator,
    index: int,
    translation_key: str,
    expected: int | datetime,
) -> None:
    """Tracking values come from persisted state without raw or computed lookup."""
    await remote_coordinator.compressor_starts.async_update(payload(30, 40), NOW)
    sensor = make_sensor(remote_coordinator, index, translation_key)
    with (
        patch.object(remote_coordinator, "get_value") as raw_lookup,
        patch.object(remote_coordinator, "get_computed_value") as computed_lookup,
    ):
        assert sensor.native_value == expected
        raw_lookup.assert_not_called()
        computed_lookup.assert_not_called()


@pytest.mark.asyncio
async def test_tracking_since_sensor_uses_each_pumps_first_valid_reading(
    hass: HomeAssistant,
    remote_coordinator: QuattCicRemoteDataUpdateCoordinator,
) -> None:
    """Dates start independently, remain fixed on new starts and survive reload."""
    hp1 = make_sensor(remote_coordinator, 0, "compressor_tracking_since")
    hp2 = make_sensor(remote_coordinator, 1, "compressor_tracking_since")
    assert hp1.native_value is None
    assert hp2.native_value is None
    await remote_coordinator.compressor_starts.async_update(payload(30, None), NOW)
    assert hp1.native_value == NOW
    assert hp2.native_value is None
    later = NOW + timedelta(minutes=1)
    await remote_coordinator.compressor_starts.async_update(payload(0, 0), later)
    await remote_coordinator.compressor_starts.async_update(
        payload(30, 30), NOW + timedelta(minutes=2)
    )
    assert hp1.native_value == NOW
    assert hp2.native_value == later
    remote_coordinator.compressor_starts = CompressorStartCounter(
        hass, remote_coordinator.config_entry.entry_id
    )
    await remote_coordinator.compressor_starts.async_load()
    assert hp1.native_value == NOW
    assert hp2.native_value == later
    assert hp1.device_class == SensorDeviceClass.TIMESTAMP
    assert hp1.entity_registry_enabled_default
    assert hp1.entity_description.entity_category is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("count", "remote", "expected"),
    [
        pytest.param(1, True, ["heatpump_1"], id="remote-mono"),
        pytest.param(2, True, ["heatpump_1", "heatpump_2"], id="remote-duo"),
        pytest.param(2, False, [], id="local-only"),
    ],
)
async def test_counter_entity_selection(
    hass: HomeAssistant,
    remote_coordinator: QuattCicRemoteDataUpdateCoordinator,
    count: int,
    remote: bool,
    expected: list[str],
) -> None:
    """Counter sensors follow the existing mono/duo and remote feature flags."""
    config_entry = remote_coordinator.config_entry
    remote_coordinator.data = {"heatPumps": [{"compressorFrequency": 0}] * count}
    entities = await async_setup_entities(
        hass, remote_coordinator, config_entry, remote, SENSORS, "sensor"
    )
    for sensor_type in (
        QuattObservedCompressorStartsSensor,
        QuattCompressorTrackingSinceSensor,
    ):
        identifiers = []
        for entity in entities:
            if isinstance(entity, sensor_type):
                info = entity.device_info
                assert info is not None
                identifiers.append(
                    info["identifiers"] if isinstance(info, dict) else info.identifiers
                )
        assert identifiers == [
            {(DOMAIN, f"{config_entry.unique_id}:{device_id}")}
            for device_id in expected
        ]


def make_entity_platform(
    hass: HomeAssistant,
    remote_coordinator: QuattCicRemoteDataUpdateCoordinator,
    language: str,
) -> EntityPlatform:
    """Load real integration metadata and attach a sensor platform to the CIC."""
    config_entry = remote_coordinator.config_entry
    hass.config.language = language
    integration_path = (
        Path(__file__).resolve().parents[3] / "custom_components" / DOMAIN
    )
    hass.data[DATA_CUSTOM_COMPONENTS] = {
        DOMAIN: Integration(
            hass,
            "custom_components.quatt",
            integration_path,
            json.loads((integration_path / "manifest.json").read_text()),
            top_level_files={"translations"},
        )
    }
    hub = dr.async_get(hass).async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, config_entry.unique_id)},
    )
    remote_coordinator.hub_device_id = hub.id
    platform = EntityPlatform(
        hass=hass,
        logger=logging.getLogger(__name__),
        domain="sensor",
        platform_name=DOMAIN,
        platform=None,
        scan_interval=timedelta(minutes=1),
        entity_namespace=None,
    )
    platform.config_entry = config_entry
    return platform


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("language", "expected_name", "expected_since_name"),
    [
        pytest.param(
            "en",
            "Observed compressor starts",
            "Compressor starts tracked since",
            id="english",
        ),
        pytest.param(
            "nl",
            "Waargenomen compressorstarts",
            "Compressorstarts bijgehouden sinds",
            id="dutch",
        ),
    ],
)
async def test_entity_reload_preserves_name_id_and_counter(
    hass: HomeAssistant,
    remote_coordinator: QuattCicRemoteDataUpdateCoordinator,
    language: str,
    expected_name: str,
    expected_since_name: str,
) -> None:
    """Real entity registration survives setup cleanup, renaming and reloading."""
    platform = make_entity_platform(hass, remote_coordinator, language)
    remote_coordinator.client.async_get_data.return_value = payload(30, 0)
    await remote_coordinator.async_refresh()
    sensor = make_sensor(remote_coordinator, 0)
    tracking_date = make_sensor(remote_coordinator, 0, "compressor_tracking_since")
    await platform.platform_data.async_load_translations()
    await platform.async_add_entities([sensor, tracking_date])
    assert tracking_date.name == expected_since_name
    assert sensor.name == expected_name
    entity_id = sensor.entity_id
    assert hass.states.get(entity_id).state == "1"
    since = hass.states.get(entity_id).attributes["tracking_since"]
    date_entity_id = tracking_date.entity_id
    assert tracking_date.native_value == datetime.fromisoformat(since)
    assert (
        hass.states.get(date_entity_id).state
        == datetime.fromisoformat(since).replace(microsecond=0).isoformat()
    )
    assert hass.states.get(date_entity_id).attributes["device_class"] == "timestamp"
    registry = er.async_get(hass)
    original_ids = (
        registry.async_get(entity_id).id,
        registry.async_get(date_entity_id).id,
    )
    custom_name = "My compressor counter"
    registry.async_update_entity(entity_id, name=custom_name)
    await hass.async_block_till_done()
    friendly_name = hass.states.get(entity_id).attributes["friendly_name"]
    assert friendly_name.endswith(custom_name)
    await platform.async_reset()

    # Both local and remote setup perform registry cleanup on a real reload.
    await async_setup_entities(
        hass,
        remote_coordinator,
        remote_coordinator.config_entry,
        False,
        SENSORS,
        "sensor",
    )
    await async_setup_entities(
        hass,
        remote_coordinator,
        remote_coordinator.config_entry,
        True,
        SENSORS,
        "sensor",
    )
    assert registry.async_get(entity_id).id == original_ids[0]
    assert registry.async_get(date_entity_id).id == original_ids[1]
    assert registry.async_get(entity_id).name == custom_name
    remote_coordinator.compressor_starts = CompressorStartCounter(
        hass, remote_coordinator.config_entry.entry_id
    )
    await remote_coordinator.async_refresh()
    recreated = make_sensor(remote_coordinator, 0)
    restored_date = make_sensor(remote_coordinator, 0, "compressor_tracking_since")
    await platform.async_add_entities([recreated, restored_date])
    assert restored_date.entity_id == date_entity_id
    assert (
        hass.states.get(date_entity_id).state
        == datetime.fromisoformat(since).replace(microsecond=0).isoformat()
    )
    assert recreated.entity_id == entity_id
    assert hass.states.get(entity_id).state == "1"
    assert hass.states.get(entity_id).attributes["tracking_since"] == since
    assert hass.states.get(entity_id).attributes["friendly_name"] == friendly_name
    await platform.async_reset()


@pytest.mark.asyncio
async def test_removing_entry_removes_its_counter(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    remote_coordinator: QuattCicRemoteDataUpdateCoordinator,
    tmp_path: Path,
) -> None:
    """Deleting the integration removes its store, unlike unloading it."""
    await remote_coordinator.compressor_starts.async_update(payload(30), NOW)
    storage_path = (
        tmp_path / ".storage" / f"quatt.compressor_starts.{config_entry.entry_id}"
    )
    assert storage_path.exists()
    await async_remove_entry(hass, config_entry)
    assert not storage_path.exists()
