"""Tests for the all-electric heat battery boost feature."""
# pylint: disable=import-error,protected-access

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from pytest import MonkeyPatch

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import ConfigEntry

from custom_components.quatt import entity as quatt_entity
from custom_components.quatt import entity_switch
from custom_components.quatt.api_remote_cic import QuattCicRemoteApiClient
from custom_components.quatt.const import (
    BOOST_FAST_SCAN_INTERVAL,
    BOOST_FAST_SCAN_TAIL,
    DEVICE_HEAT_BATTERY_ID,
    QuattDeviceKind,
)
from custom_components.quatt.coordinator_remote_cic import (
    QuattCicRemoteDataUpdateCoordinator,
)
from custom_components.quatt.entity_switch import QuattAllElectricBoostSwitch
from custom_components.quatt.sensor_descriptions_heat import HEAT_BATTERY_SENSORS
from custom_components.quatt.switch import SWITCHES

CONFIGURED_INTERVAL = timedelta(minutes=1)
FAST_INTERVAL = timedelta(seconds=BOOST_FAST_SCAN_INTERVAL)
NOW = datetime(2026, 8, 21, 12, 0, 0, tzinfo=timezone.utc)  # noqa: UP017


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


def _make_client(auth: FakeAuth) -> QuattCicRemoteApiClient:
    """Create a remote API client backed by the fake auth client."""
    return QuattCicRemoteApiClient(cic="CIC-12345678", session=None, auth=auth)


# ---------------------------------------------------------------------------
# API client
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_boost_start_posts_start_action() -> None:
    """Starting the boost should POST a START action to the boost endpoint."""
    auth = FakeAuth(responses=[(202, None)])
    client = _make_client(auth)

    assert await client.set_all_electric_boost(True) is True
    assert auth.requests == [
        {
            "method": "POST",
            "path": "/me/cic/CIC-12345678/allElectricBoost/actions",
            "json_body": {"type": "START"},
        }
    ]


@pytest.mark.asyncio
async def test_set_boost_cancel_posts_cancel_action() -> None:
    """Canceling the boost should POST a CANCEL action."""
    auth = FakeAuth(responses=[(200, None)])
    client = _make_client(auth)

    assert await client.set_all_electric_boost(False) is True
    assert auth.requests[0]["json_body"] == {"type": "CANCEL"}


@pytest.mark.asyncio
async def test_set_boost_reports_failure_status() -> None:
    """A non-success API status should be reported as failure."""
    auth = FakeAuth(responses=[(500, None)])
    client = _make_client(auth)

    assert await client.set_all_electric_boost(True) is False


@pytest.mark.asyncio
async def test_set_boost_requires_authentication() -> None:
    """Without authentication no request should be made."""
    auth = FakeAuth(authenticated=False)
    client = _make_client(auth)

    assert await client.set_all_electric_boost(True) is False
    assert auth.requests == []


@pytest.mark.asyncio
async def test_get_boost_returns_result() -> None:
    """The boost status fetch should unwrap the result payload."""
    boost = {"status": "ACTIVE", "endTime": "2026-08-21T14:00:00Z"}
    auth = FakeAuth(responses=[(200, {"result": boost})])
    client = _make_client(auth)

    assert await client.get_all_electric_boost() == boost
    assert auth.requests[0]["method"] == "GET"
    assert auth.requests[0]["path"] == "/me/cic/CIC-12345678/allElectricBoost"


@pytest.mark.asyncio
async def test_get_boost_returns_none_on_error() -> None:
    """A failed boost status fetch should return None."""
    auth = FakeAuth(responses=[(503, None)])
    client = _make_client(auth)

    assert await client.get_all_electric_boost() is None


@pytest.mark.asyncio
async def test_async_get_data_includes_boost_for_all_electric() -> None:
    """All-electric installations should get the boost status merged in."""
    boost = {"status": "STARTING"}
    auth = FakeAuth(
        responses=[
            (200, {"result": {"allEStatus": True}}),
            (200, {"result": boost}),
        ]
    )
    client = _make_client(auth)

    data = await client.async_get_data()

    assert data["allElectricBoost"] == boost
    assert [request["path"] for request in auth.requests] == [
        "/me/cic/CIC-12345678",
        "/me/cic/CIC-12345678/allElectricBoost",
    ]


@pytest.mark.asyncio
async def test_async_get_data_skips_boost_for_hybrid() -> None:
    """Non-all-electric installations should not fetch the boost status."""
    auth = FakeAuth(responses=[(200, {"result": {"allEStatus": False}})])
    client = _make_client(auth)

    data = await client.async_get_data()

    assert "allElectricBoost" not in data
    assert [request["path"] for request in auth.requests] == ["/me/cic/CIC-12345678"]


@pytest.mark.asyncio
async def test_async_get_data_survives_boost_fetch_failure() -> None:
    """A failed boost fetch should not fail the whole coordinator update."""
    auth = FakeAuth(
        responses=[
            (200, {"result": {"allEStatus": True, "hpStatus": 2}}),
            (503, None),
        ]
    )
    client = _make_client(auth)

    data = await client.async_get_data()

    assert data["hpStatus"] == 2
    assert "allElectricBoost" not in data


# ---------------------------------------------------------------------------
# Coordinator adaptive polling
# ---------------------------------------------------------------------------


def _make_coordinator(
    fast_scan_until: datetime | None = None,
) -> QuattCicRemoteDataUpdateCoordinator:
    """Create a remote coordinator instance without calling __init__."""
    coordinator = object.__new__(QuattCicRemoteDataUpdateCoordinator)
    coordinator._configured_update_interval = CONFIGURED_INTERVAL
    coordinator._boost_fast_scan_until = fast_scan_until
    return coordinator


@pytest.fixture(name="frozen_now")
def frozen_now_fixture(monkeypatch: MonkeyPatch) -> datetime:
    """Freeze the coordinator's clock at NOW."""
    from custom_components.quatt import coordinator_remote_cic

    monkeypatch.setattr(coordinator_remote_cic.dt_util, "utcnow", lambda: NOW)
    return NOW


@pytest.mark.parametrize(
    "status", ["AWAITING_CIC_STATE", "STARTING", "ACTIVE", "active"]
)
def test_active_boost_switches_to_fast_polling(
    frozen_now: datetime, status: str
) -> None:
    """Any starting/active boost status should trigger fast polling."""
    coordinator = _make_coordinator()

    interval = coordinator._next_update_interval(
        {"allElectricBoost": {"status": status}}
    )

    assert interval == FAST_INTERVAL
    assert coordinator._boost_fast_scan_until == NOW + timedelta(
        minutes=BOOST_FAST_SCAN_TAIL
    )


@pytest.mark.parametrize(
    "data",
    [
        None,
        {},
        {"allElectricBoost": None},
        {"allElectricBoost": {}},
        {"allElectricBoost": {"status": "FINISHED"}},
        {"allElectricBoost": {"status": 5}},
    ],
)
def test_no_boost_keeps_configured_interval(frozen_now: datetime, data: Any) -> None:
    """Without an active boost the configured scan interval applies."""
    coordinator = _make_coordinator()

    assert coordinator._next_update_interval(data) == CONFIGURED_INTERVAL
    assert coordinator._boost_fast_scan_until is None


def test_fast_polling_continues_during_tail(frozen_now: datetime) -> None:
    """After the boost ended, fast polling should continue during the tail."""
    coordinator = _make_coordinator(fast_scan_until=NOW + timedelta(seconds=1))

    interval = coordinator._next_update_interval(
        {"allElectricBoost": {"status": "FINISHED"}}
    )

    assert interval == FAST_INTERVAL
    assert coordinator._boost_fast_scan_until is not None


def test_fast_polling_ends_after_tail(frozen_now: datetime) -> None:
    """Once the tail has passed, polling should return to the configured interval."""
    coordinator = _make_coordinator(fast_scan_until=NOW - timedelta(seconds=1))

    interval = coordinator._next_update_interval(
        {"allElectricBoost": {"status": "FINISHED"}}
    )

    assert interval == CONFIGURED_INTERVAL
    assert coordinator._boost_fast_scan_until is None


def test_boost_seen_active_extends_tail(frozen_now: datetime) -> None:
    """Every poll that sees an active boost should push the tail forward."""
    coordinator = _make_coordinator(fast_scan_until=NOW - timedelta(minutes=10))

    interval = coordinator._next_update_interval(
        {"allElectricBoost": {"status": "ACTIVE"}}
    )

    assert interval == FAST_INTERVAL
    assert coordinator._boost_fast_scan_until == NOW + timedelta(
        minutes=BOOST_FAST_SCAN_TAIL
    )


# ---------------------------------------------------------------------------
# Boost switch entity
# ---------------------------------------------------------------------------


class FakeBoostClient:
    """Minimal remote client recording boost actions."""

    def __init__(self, success: bool = True) -> None:
        """Initialize the fake remote client."""
        self.actions: list[bool] = []
        self._success = success

    async def set_all_electric_boost(self, start: bool) -> bool:
        """Record the boost action and report the configured result."""
        self.actions.append(start)
        return self._success


class FakeRemoteCoordinator:
    """Minimal remote coordinator for boost switch behavior tests."""

    def __init__(
        self,
        config_entry: ConfigEntry,
        data: dict[str, Any],
        client: FakeBoostClient | None = None,
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


def _boost_switch_description():
    """Return the boost switch entity description."""
    description = SWITCHES[DEVICE_HEAT_BATTERY_ID][0]
    assert description.key == "allElectricBoost"
    return description


def _make_switch(coordinator: FakeRemoteCoordinator) -> QuattAllElectricBoostSwitch:
    """Create a boost switch entity on the fake coordinator."""
    description = _boost_switch_description()
    return QuattAllElectricBoostSwitch(
        device_name="Heat battery",
        device_id=DEVICE_HEAT_BATTERY_ID,
        sensor_key=description.key,
        coordinator=coordinator,
        entity_description=description,
        device_kind=QuattDeviceKind.DEVICE,
    )


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("AWAITING_CIC_STATE", True),
        ("STARTING", True),
        ("ACTIVE", True),
        ("active", True),
        ("FINISHED", False),
        ("USER_CANCELED", False),
        (None, False),
        (5, False),
    ],
)
@pytest.mark.asyncio
async def test_boost_switch_is_on_follows_status(
    config_entry: ConfigEntry, status: Any, expected: bool
) -> None:
    """The switch should be on for starting and active boost statuses."""
    coordinator = FakeRemoteCoordinator(
        config_entry, {"result": {"allElectricBoost": {"status": status}}}
    )
    switch = _make_switch(coordinator)

    assert switch.is_on is expected


@pytest.mark.parametrize(
    ("turn_on", "expected_action"),
    [(True, True), (False, False)],
)
@pytest.mark.asyncio
async def test_boost_switch_sends_boost_action(
    monkeypatch: MonkeyPatch,
    config_entry: ConfigEntry,
    turn_on: bool,
    expected_action: bool,
) -> None:
    """Turning the switch on/off should send the matching boost action."""
    monkeypatch.setattr(
        quatt_entity, "QuattCicRemoteDataUpdateCoordinator", FakeRemoteCoordinator
    )
    monkeypatch.setattr(entity_switch, "QuattCicRemoteApiClient", FakeBoostClient)
    client = FakeBoostClient()
    coordinator = FakeRemoteCoordinator(
        config_entry,
        {"result": {"allElectricBoost": {"status": "FINISHED"}}},
        client=client,
    )
    switch = _make_switch(coordinator)

    if turn_on:
        await switch.async_turn_on()
    else:
        await switch.async_turn_off()

    assert client.actions == [expected_action]
    assert coordinator.refresh_requests == 1


@pytest.mark.asyncio
async def test_boost_switch_raises_on_api_failure(
    monkeypatch: MonkeyPatch, config_entry: ConfigEntry
) -> None:
    """A rejected boost action should raise and not request a refresh."""
    monkeypatch.setattr(
        quatt_entity, "QuattCicRemoteDataUpdateCoordinator", FakeRemoteCoordinator
    )
    monkeypatch.setattr(entity_switch, "QuattCicRemoteApiClient", FakeBoostClient)
    client = FakeBoostClient(success=False)
    coordinator = FakeRemoteCoordinator(
        config_entry,
        {"result": {"allElectricBoost": {"status": "FINISHED"}}},
        client=client,
    )
    switch = _make_switch(coordinator)

    with pytest.raises(RuntimeError):
        await switch.async_turn_on()

    assert coordinator.refresh_requests == 0


# ---------------------------------------------------------------------------
# Sensor descriptions
# ---------------------------------------------------------------------------


def test_heat_battery_boost_sensor_descriptions() -> None:
    """The heat battery should expose the boost sensors for all-electric setups."""
    by_key = {description.key: description for description in HEAT_BATTERY_SENSORS}

    for key in (
        "allElectricBoost.status",
        "allElectricBoost.endTime",
        "allElectricBoost.exitReason",
    ):
        description = by_key[key]
        assert description.quatt_features.all_electric is True
        assert description.quatt_features.mobile_api is True

    assert by_key["allElectricBoost.endTime"].device_class == (
        SensorDeviceClass.TIMESTAMP
    )
