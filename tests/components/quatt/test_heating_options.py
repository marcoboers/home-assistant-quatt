"""Tests for the hybrid heating option switch."""  # noqa: INP001

from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio

from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

# isort: split
from custom_components.quatt.api_remote_auth import QuattRemoteAuthClient
from custom_components.quatt.api_remote_cic import QuattCicRemoteApiClient
from custom_components.quatt.const import DEVICE_CIC_ID
from custom_components.quatt.coordinator_remote_cic import (
    QuattCicRemoteDataUpdateCoordinator,
)
from custom_components.quatt.entity_setup import async_setup_entities
from custom_components.quatt.entity_switch import QuattHeatingOptionSwitch
from custom_components.quatt.switch import SWITCHES

CIC = "CIC-12345678"
INSTALLATION_ID = "INS-12345678-1234-5678-1234-567812345678"
HEATING_OPTIONS_PATH = f"/me/installation/{INSTALLATION_ID}/predictiveHeating"
OPTION = "avoidGasBoilerUse"

pytestmark = pytest.mark.asyncio


@pytest.fixture(name="auth")
def auth_fixture() -> Mock:
    """Provide an authenticated client with a mocked request method."""
    return Mock(spec=QuattRemoteAuthClient, is_authenticated=True)


@pytest.fixture(name="coordinator")
def coordinator_fixture(
    config_entry: ConfigEntry, auth: Mock
) -> QuattCicRemoteDataUpdateCoordinator:
    """Provide a coordinator backed by the actual remote API client."""
    coordinator = object.__new__(QuattCicRemoteDataUpdateCoordinator)
    coordinator.config_entry = config_entry
    coordinator.client = QuattCicRemoteApiClient(cic=CIC, session=None, auth=auth)
    coordinator.data = {OPTION: False}
    return coordinator


@pytest_asyncio.fixture(name="heating_switch")
async def heating_switch_fixture(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    coordinator: QuattCicRemoteDataUpdateCoordinator,
) -> QuattHeatingOptionSwitch:
    """Set up the heating option switch for a remote hybrid installation."""
    entities = await async_setup_entities(
        hass, coordinator, config_entry, True, SWITCHES, SWITCH_DOMAIN
    )
    return next(
        entity for entity in entities if isinstance(entity, QuattHeatingOptionSwitch)
    )


@pytest.mark.parametrize(
    ("remote", "data"),
    [
        pytest.param(False, {}, id="local-hybrid"),
        pytest.param(True, {"allEStatus": {"active": True}}, id="remote-all-electric"),
    ],
)
async def test_heating_option_hidden_for_other_setups(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    coordinator: QuattCicRemoteDataUpdateCoordinator,
    remote: bool,
    data: dict[str, object],
) -> None:
    """Only the mobile API on hybrid installations exposes the switch."""
    coordinator.data = data

    entities = await async_setup_entities(
        hass,
        coordinator,
        config_entry,
        remote,
        {DEVICE_CIC_ID: SWITCHES[DEVICE_CIC_ID]},
        SWITCH_DOMAIN,
    )

    assert not any(isinstance(entity, QuattHeatingOptionSwitch) for entity in entities)


@pytest.mark.parametrize(
    ("action", "state"),
    [
        pytest.param("async_turn_on", True, id="turn-on"),
        pytest.param("async_turn_off", False, id="turn-off"),
    ],
)
async def test_heating_option_updates_and_refreshes(
    monkeypatch: pytest.MonkeyPatch,
    coordinator: QuattCicRemoteDataUpdateCoordinator,
    heating_switch: QuattHeatingOptionSwitch,
    auth: Mock,
    action: str,
    state: bool,
) -> None:
    """Send only the requested option and read the refreshed CIC value."""
    coordinator.client.load_installation_id(INSTALLATION_ID)
    coordinator.data = {OPTION: not state}
    auth.request.return_value = (204, None)

    async def refresh() -> None:
        coordinator.data = {OPTION: state}

    refresh_mock = AsyncMock(side_effect=refresh)
    monkeypatch.setattr(coordinator, "async_request_refresh", refresh_mock)

    assert heating_switch.is_on is not state
    await getattr(heating_switch, action)()

    auth.request.assert_awaited_once_with(
        "PATCH",
        HEATING_OPTIONS_PATH,
        json_body={OPTION: state},
        expected_statuses=(200, 201, 204),
    )
    refresh_mock.assert_awaited_once()
    assert heating_switch.is_on is state


async def test_heating_option_requires_installation_id(
    coordinator: QuattCicRemoteDataUpdateCoordinator, auth: Mock
) -> None:
    """Writing requires a stored installation ID."""
    assert not await coordinator.client.update_predictive_heating({OPTION: True})

    auth.request.assert_not_awaited()


async def test_heating_option_reports_failed_write(
    monkeypatch: pytest.MonkeyPatch,
    coordinator: QuattCicRemoteDataUpdateCoordinator,
    heating_switch: QuattHeatingOptionSwitch,
    auth: Mock,
) -> None:
    """A failed request raises an error and leaves the reported state intact."""
    coordinator.client.load_installation_id(INSTALLATION_ID)
    auth.request.return_value = (500, None)
    refresh_mock = AsyncMock()
    monkeypatch.setattr(coordinator, "async_request_refresh", refresh_mock)

    with pytest.raises(RuntimeError, match="Failed to update avoidGasBoilerUse"):
        await heating_switch.async_turn_on()

    refresh_mock.assert_not_awaited()
    assert heating_switch.is_on is False
