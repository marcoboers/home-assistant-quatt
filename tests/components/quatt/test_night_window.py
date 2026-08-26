"""Tests for the CIC night time window controls."""
# pylint: disable=import-error

from __future__ import annotations

from datetime import time
from typing import Any

import pytest
from pytest import MonkeyPatch

from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ServiceValidationError

from custom_components.quatt import entity as quatt_entity
from custom_components.quatt import entity_button, entity_time
from custom_components.quatt.api_remote_cic import QuattCicRemoteApiClient
from custom_components.quatt.button import BUTTONS
from custom_components.quatt.const import DEVICE_CIC_ID, QuattDeviceKind
from custom_components.quatt.entity_button import QuattNightWindowResetButton
from custom_components.quatt.entity_time import (
    NIGHT_WINDOW_END_KEY,
    NIGHT_WINDOW_START_KEY,
    QuattNightWindowTime,
)
from custom_components.quatt.time import TIMES


class FakeAuth:
    """Minimal auth client recording requests and replaying queued responses."""

    def __init__(
        self,
        responses: list[tuple[int, Any]] | None = None,
        authenticated: bool = True,
    ) -> None:
        """Initialize the fake auth client."""
        self.requests: list[dict[str, Any]] = []
        self._responses = list(responses or [])
        self.is_authenticated = authenticated

    async def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any | None = None,
        params: dict[str, Any] | None = None,
        expected_statuses: tuple[int, ...] = (200, 201, 204),
        retry_on_auth_error: bool = True,
    ) -> tuple[int, Any | None]:
        """Record the request and return the next queued response."""
        self.requests.append({"method": method, "path": path, "json_body": json_body})
        if self._responses:
            return self._responses.pop(0)
        return (200, {})


# ---------------------------------------------------------------------------
# API client
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_night_window_sends_both_boundaries() -> None:
    """Setting the night window should PUT all four values in one request."""
    auth = FakeAuth(responses=[(204, None)])
    client = QuattCicRemoteApiClient(cic="CIC-12345678", session=None, auth=auth)

    assert await client.update_night_window(21, 30, 7, 0) is True
    assert auth.requests == [
        {
            "method": "PUT",
            "path": "/me/cic/CIC-12345678/nightWindow",
            "json_body": {
                "nightTimeStartHour": 21,
                "nightTimeStartMinute": 30,
                "nightTimeEndHour": 7,
                "nightTimeEndMinute": 0,
            },
        }
    ]


@pytest.mark.asyncio
async def test_update_night_window_reset_sends_nulls() -> None:
    """Resetting the night window should send null for all values."""
    auth = FakeAuth(responses=[(200, None)])
    client = QuattCicRemoteApiClient(cic="CIC-12345678", session=None, auth=auth)

    assert await client.update_night_window(None, None, None, None) is True
    assert auth.requests[0]["json_body"] == {
        "nightTimeStartHour": None,
        "nightTimeStartMinute": None,
        "nightTimeEndHour": None,
        "nightTimeEndMinute": None,
    }


@pytest.mark.asyncio
async def test_update_night_window_reports_failure_status() -> None:
    """A non-success API status should be reported as failure."""
    auth = FakeAuth(responses=[(500, None)])
    client = QuattCicRemoteApiClient(cic="CIC-12345678", session=None, auth=auth)

    assert await client.update_night_window(21, 0, 7, 0) is False


@pytest.mark.asyncio
async def test_update_night_window_requires_authentication() -> None:
    """Without authentication no request should be made."""
    auth = FakeAuth(authenticated=False)
    client = QuattCicRemoteApiClient(cic="CIC-12345678", session=None, auth=auth)

    assert await client.update_night_window(21, 0, 7, 0) is False
    assert auth.requests == []


# ---------------------------------------------------------------------------
# Entity fakes
# ---------------------------------------------------------------------------


class FakeNightWindowClient:
    """Minimal remote client recording night window updates."""

    def __init__(self, success: bool = True) -> None:
        """Initialize the fake remote client."""
        self.updates: list[tuple[int | None, int | None, int | None, int | None]] = []
        self._success = success

    async def update_night_window(
        self,
        start_hour: int | None,
        start_minute: int | None,
        end_hour: int | None,
        end_minute: int | None,
    ) -> bool:
        """Record the night window update and report the configured result."""
        self.updates.append((start_hour, start_minute, end_hour, end_minute))
        return self._success


class FakeRemoteCoordinator:
    """Minimal remote coordinator for night window behavior tests."""

    def __init__(
        self,
        config_entry: ConfigEntry,
        data: dict[str, Any],
        client: FakeNightWindowClient | None = None,
    ) -> None:
        """Initialize the fake coordinator."""
        self.config_entry = config_entry
        self.data = data
        self.client = client
        self.last_update_success = True
        self.refresh_requests = 0

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
            return default

        return current_node

    async def async_request_refresh(self) -> None:
        """Record the refresh request."""
        self.refresh_requests += 1


def _window_data(
    start_hour: int | None = 21,
    start_minute: int | None = 0,
    end_hour: int | None = 7,
    end_minute: int | None = 0,
) -> dict[str, Any]:
    """Return remote API data holding the current night window."""
    return {
        "result": {
            f"{NIGHT_WINDOW_START_KEY}Hour": start_hour,
            f"{NIGHT_WINDOW_START_KEY}Min": start_minute,
            f"{NIGHT_WINDOW_END_KEY}Hour": end_hour,
            f"{NIGHT_WINDOW_END_KEY}Min": end_minute,
        }
    }


def _time_description(key: str):
    """Return the time entity description for the given boundary key."""
    for description in TIMES[DEVICE_CIC_ID]:
        if description.key == key:
            return description
    raise AssertionError(f"No time description for {key}")


def _make_time_entity(
    coordinator: FakeRemoteCoordinator, key: str
) -> QuattNightWindowTime:
    """Create a night window time entity on the fake coordinator."""
    description = _time_description(key)
    return QuattNightWindowTime(
        device_name="CIC",
        device_id=DEVICE_CIC_ID,
        sensor_key=description.key,
        coordinator=coordinator,
        entity_description=description,
        device_kind=QuattDeviceKind.HUB,
    )


def _make_reset_button(
    coordinator: FakeRemoteCoordinator,
) -> QuattNightWindowResetButton:
    """Create the night window reset button on the fake coordinator."""
    description = BUTTONS[DEVICE_CIC_ID][0]
    assert description.key == "nightWindowReset"
    return QuattNightWindowResetButton(
        device_name="CIC",
        device_id=DEVICE_CIC_ID,
        sensor_key=description.key,
        coordinator=coordinator,
        entity_description=description,
        device_kind=QuattDeviceKind.HUB,
    )


@pytest.fixture(name="remote_classes")
def remote_classes_fixture(monkeypatch: MonkeyPatch) -> None:
    """Let the fakes pass the remote coordinator/client isinstance checks."""
    monkeypatch.setattr(
        quatt_entity, "QuattCicRemoteDataUpdateCoordinator", FakeRemoteCoordinator
    )
    monkeypatch.setattr(entity_time, "QuattCicRemoteApiClient", FakeNightWindowClient)
    monkeypatch.setattr(entity_button, "QuattCicRemoteApiClient", FakeNightWindowClient)


# ---------------------------------------------------------------------------
# Night window time entities
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_time_native_value_combines_hour_and_minute(
    config_entry: ConfigEntry,
) -> None:
    """The time value should combine the separate hour/minute fields."""
    coordinator = FakeRemoteCoordinator(
        config_entry, _window_data(start_hour=21, start_minute=30)
    )

    entity = _make_time_entity(coordinator, NIGHT_WINDOW_START_KEY)

    assert entity.native_value == time(hour=21, minute=30)


@pytest.mark.asyncio
async def test_time_native_value_none_without_hour(
    config_entry: ConfigEntry,
) -> None:
    """Without an hour value the time entity should report unknown."""
    coordinator = FakeRemoteCoordinator(
        config_entry, _window_data(start_hour=None, start_minute=None)
    )

    entity = _make_time_entity(coordinator, NIGHT_WINDOW_START_KEY)

    assert entity.native_value is None


@pytest.mark.asyncio
async def test_time_native_value_defaults_minute_to_zero(
    config_entry: ConfigEntry,
) -> None:
    """A missing minute field should default to zero."""
    coordinator = FakeRemoteCoordinator(
        config_entry, _window_data(end_hour=7, end_minute=None)
    )

    entity = _make_time_entity(coordinator, NIGHT_WINDOW_END_KEY)

    assert entity.native_value == time(hour=7, minute=0)


@pytest.mark.parametrize(
    "value",
    [
        time(hour=21, minute=15),
        time(hour=21, minute=1),
        time(hour=21, minute=0, second=30),
        time(hour=21, minute=30, microsecond=1),
    ],
)
@pytest.mark.asyncio
async def test_time_rejects_values_off_the_half_hour(
    remote_classes: None,
    config_entry: ConfigEntry,
    value: time,
) -> None:
    """Values not on a 30-minute boundary should be rejected before the API."""
    client = FakeNightWindowClient()
    coordinator = FakeRemoteCoordinator(config_entry, _window_data(), client=client)
    entity = _make_time_entity(coordinator, NIGHT_WINDOW_START_KEY)

    with pytest.raises(ServiceValidationError):
        await entity.async_set_value(value)

    assert client.updates == []
    assert coordinator.refresh_requests == 0


@pytest.mark.asyncio
async def test_time_start_updates_start_and_keeps_end(
    remote_classes: None, config_entry: ConfigEntry
) -> None:
    """Setting the start time should keep the current end boundary."""
    client = FakeNightWindowClient()
    coordinator = FakeRemoteCoordinator(
        config_entry,
        _window_data(start_hour=21, start_minute=0, end_hour=7, end_minute=30),
        client=client,
    )
    entity = _make_time_entity(coordinator, NIGHT_WINDOW_START_KEY)

    await entity.async_set_value(time(hour=22, minute=30))

    assert client.updates == [(22, 30, 7, 30)]
    assert coordinator.refresh_requests == 1


@pytest.mark.asyncio
async def test_time_end_updates_end_and_keeps_start(
    remote_classes: None, config_entry: ConfigEntry
) -> None:
    """Setting the end time should keep the current start boundary."""
    client = FakeNightWindowClient()
    coordinator = FakeRemoteCoordinator(
        config_entry,
        _window_data(start_hour=21, start_minute=30, end_hour=7, end_minute=0),
        client=client,
    )
    entity = _make_time_entity(coordinator, NIGHT_WINDOW_END_KEY)

    await entity.async_set_value(time(hour=6, minute=0))

    assert client.updates == [(21, 30, 6, 0)]
    assert coordinator.refresh_requests == 1


@pytest.mark.asyncio
async def test_time_fails_without_current_window(
    remote_classes: None, config_entry: ConfigEntry
) -> None:
    """Without the other boundary's current values the update should fail."""
    client = FakeNightWindowClient()
    coordinator = FakeRemoteCoordinator(
        config_entry,
        _window_data(end_hour=None, end_minute=None),
        client=client,
    )
    entity = _make_time_entity(coordinator, NIGHT_WINDOW_START_KEY)

    with pytest.raises(RuntimeError):
        await entity.async_set_value(time(hour=22, minute=0))

    assert client.updates == []
    assert coordinator.refresh_requests == 0


@pytest.mark.asyncio
async def test_time_raises_on_api_failure(
    remote_classes: None, config_entry: ConfigEntry
) -> None:
    """A rejected night window update should raise and not request a refresh."""
    client = FakeNightWindowClient(success=False)
    coordinator = FakeRemoteCoordinator(config_entry, _window_data(), client=client)
    entity = _make_time_entity(coordinator, NIGHT_WINDOW_START_KEY)

    with pytest.raises(RuntimeError):
        await entity.async_set_value(time(hour=22, minute=0))

    assert coordinator.refresh_requests == 0


# ---------------------------------------------------------------------------
# Night window reset button
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reset_button_posts_null_window(
    remote_classes: None, config_entry: ConfigEntry
) -> None:
    """Pressing the reset button should send an all-null window."""
    client = FakeNightWindowClient()
    coordinator = FakeRemoteCoordinator(config_entry, _window_data(), client=client)
    button = _make_reset_button(coordinator)

    await button.async_press()

    assert client.updates == [(None, None, None, None)]
    assert coordinator.refresh_requests == 1


@pytest.mark.asyncio
async def test_reset_button_raises_on_api_failure(
    remote_classes: None, config_entry: ConfigEntry
) -> None:
    """A rejected reset should raise and not request a refresh."""
    client = FakeNightWindowClient(success=False)
    coordinator = FakeRemoteCoordinator(config_entry, _window_data(), client=client)
    button = _make_reset_button(coordinator)

    with pytest.raises(RuntimeError):
        await button.async_press()

    assert coordinator.refresh_requests == 0


# ---------------------------------------------------------------------------
# Entity descriptions
# ---------------------------------------------------------------------------


def test_night_window_entity_descriptions() -> None:
    """The CIC device should expose both time entities and the reset button."""
    time_keys = [description.key for description in TIMES[DEVICE_CIC_ID]]
    assert time_keys == [NIGHT_WINDOW_START_KEY, NIGHT_WINDOW_END_KEY]
    for description in TIMES[DEVICE_CIC_ID]:
        assert description.quatt_features.mobile_api is True

    button = BUTTONS[DEVICE_CIC_ID][0]
    assert button.key == "nightWindowReset"
    assert button.quatt_features.mobile_api is True
