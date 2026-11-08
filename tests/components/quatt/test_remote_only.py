"""Tests for loading a paired CIC through the cloud without a local connection."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import entity_registry as er

from custom_components import quatt
from custom_components.quatt.config_flow import QuattFlowHandler
from custom_components.quatt.const import (
    CONF_LOCAL_API_ENABLED,
    CONF_LOCAL_CIC,
    CONF_REMOTE_CIC,
    DOMAIN,
    REMOTE_CONF_SCAN_INTERVAL,
)

pytestmark = pytest.mark.asyncio


async def test_switching_local_connection_preserves_registered_entities(
    hass: HomeAssistant, config_entry, monkeypatch, enable_custom_integrations
) -> None:
    """Real platform reloads retain local entity IDs and restore local readings."""
    fixtures = Path(__file__).parent / "fixtures"
    local_client = Mock()
    local_client.async_get_data = AsyncMock(
        return_value=json.loads((fixtures / "local_cic_duo_all_electric.json").read_text())
    )
    remote_client = Mock()
    remote_client.authenticate = AsyncMock(return_value=True)
    remote_client.async_get_data = AsyncMock(
        return_value=json.loads((fixtures / "remote_cic_duo_all_electric.json").read_text())
    )
    remote_client.get_insights = AsyncMock(return_value={"totalHpHeat": 4200})
    local_factory = Mock(return_value=local_client)
    monkeypatch.setattr(quatt, "QuattCicLocalApiClient", local_factory)
    monkeypatch.setattr(quatt, "QuattCicRemoteApiClient", Mock(return_value=remote_client))
    monkeypatch.setattr(quatt, "_get_or_create_auth_client", AsyncMock())
    monkeypatch.setattr(quatt, "async_get_clientsession", Mock())
    monkeypatch.setattr(quatt, "async_setup", AsyncMock(return_value=True))
    store = Mock()
    store.async_load = AsyncMock(return_value={"installation_id": "installation-1"})
    monkeypatch.setattr(quatt, "Store", Mock(return_value=store))
    hass.config_entries.async_update_entry(
        config_entry,
        version=QuattFlowHandler.VERSION,
        data={CONF_LOCAL_CIC: "192.0.2.1", CONF_REMOTE_CIC: "CIC-12345678"},
    )

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    local_entity = next(
        entity
        for entity in er.async_entries_for_config_entry(registry, config_entry.entry_id)
        if entity.unique_id.endswith(":hp1.power")
    )
    local_entity_id = local_entity.entity_id
    assert hass.states.get(local_entity_id).state == "0"

    local_factory.reset_mock()
    hass.config_entries.async_update_entry(
        config_entry, options={CONF_LOCAL_API_ENABLED: False}
    )
    await hass.async_block_till_done()

    local_factory.assert_not_called()
    assert registry.async_get(local_entity_id).id == local_entity.id
    assert hass.states.get(local_entity_id).state == "unavailable"
    assert await hass.services.async_call(
        DOMAIN, "get_cic_insights", {}, blocking=True, return_response=True
    ) == {"totalHpHeat": 4200}

    local_client.async_get_data.return_value["hp1"]["power"] = 1200
    hass.config_entries.async_update_entry(
        config_entry, options={CONF_LOCAL_API_ENABLED: True}
    )
    await hass.async_block_till_done()

    local_factory.assert_called_once()
    assert registry.async_get(local_entity_id).id == local_entity.id
    assert hass.states.get(local_entity_id).state == "1200"
    assert await hass.config_entries.async_unload(config_entry.entry_id)


@pytest.fixture
def setup_clients(hass, monkeypatch):
    """Mock network clients while keeping setup and service registration real."""
    local_client = Mock()
    local_coordinator = Mock()
    local_coordinator.async_config_entry_first_refresh = AsyncMock()
    remote_client = Mock()
    remote_client.authenticate = AsyncMock(return_value=True)
    remote_client.get_insights = AsyncMock(return_value={"totalHpHeat": 4200})
    remote_coordinator = Mock(client=remote_client)
    remote_coordinator.async_config_entry_first_refresh = AsyncMock()

    local_factory = Mock(return_value=local_client)
    monkeypatch.setattr(quatt, "QuattCicLocalApiClient", local_factory)
    monkeypatch.setattr(
        quatt, "QuattCicLocalDataUpdateCoordinator", Mock(return_value=local_coordinator)
    )
    monkeypatch.setattr(
        quatt, "QuattCicRemoteApiClient", Mock(return_value=remote_client)
    )
    monkeypatch.setattr(
        quatt, "QuattCicRemoteDataUpdateCoordinator", Mock(return_value=remote_coordinator)
    )
    monkeypatch.setattr(quatt, "_get_or_create_auth_client", AsyncMock())
    store = Mock()
    store.async_load = AsyncMock(return_value={"installation_id": "installation-1"})
    monkeypatch.setattr(quatt, "Store", Mock(return_value=store))
    monkeypatch.setattr(quatt, "async_get_clientsession", Mock())
    monkeypatch.setattr(hass.config_entries, "async_forward_entry_setups", AsyncMock())
    return local_factory, local_coordinator, remote_client


async def test_remote_only_loads_with_offline_cic(
    hass: HomeAssistant, config_entry, setup_clients
) -> None:
    """An unavailable local CIC must not block the paired cloud insights service."""
    local_factory, local_coordinator, remote_client = setup_clients
    local_coordinator.async_config_entry_first_refresh.side_effect = (
        ConfigEntryNotReady("CIC is offline")
    )
    hass.config_entries.async_update_entry(
        config_entry,
        data={CONF_LOCAL_CIC: "192.0.2.1", CONF_REMOTE_CIC: "CIC-12345678"},
        options={CONF_LOCAL_API_ENABLED: False},
    )

    assert await quatt.async_setup_entry(hass, config_entry) is True

    local_factory.assert_not_called()
    local_coordinator.async_config_entry_first_refresh.assert_not_awaited()
    remote_client.load_installation_id.assert_called_once_with("installation-1")
    remote_client.authenticate.assert_awaited_once()
    assert hass.data[DOMAIN][config_entry.entry_id]["cic_local"] is None
    assert hass.services.has_service(DOMAIN, "get_cic_insights")

    response = await hass.services.async_call(
        DOMAIN,
        "get_cic_insights",
        {"from_date": "2024-01-01", "timeframe": "month", "advanced_insights": True},
        blocking=True,
        return_response=True,
    )

    assert response == {"totalHpHeat": 4200}
    remote_client.get_insights.assert_awaited_once_with(
        from_date="2024-01-01", timeframe="month", advanced_insights=True
    )


async def test_remote_only_auth_failure_does_not_enable_local_access(
    hass: HomeAssistant, config_entry, setup_clients
) -> None:
    """Invalid cloud credentials leave exports unavailable without local fallback."""
    local_factory, _, remote_client = setup_clients
    remote_client.authenticate.return_value = False
    hass.config_entries.async_update_entry(
        config_entry,
        data={CONF_LOCAL_CIC: "192.0.2.1", CONF_REMOTE_CIC: "CIC-12345678"},
        options={CONF_LOCAL_API_ENABLED: False},
    )

    assert await quatt.async_setup_entry(hass, config_entry) is True
    response = await hass.services.async_call(
        DOMAIN, "get_cic_insights", {}, blocking=True, return_response=True
    )

    local_factory.assert_not_called()
    assert hass.data[DOMAIN][config_entry.entry_id]["cic_remote"] is None
    assert "No remote connection available" in response["error"]


async def test_remote_only_cloud_failure_leaves_setup_retryable(
    hass: HomeAssistant, config_entry, setup_clients
) -> None:
    """A failed cloud refresh must not publish a partially loaded CIC entry."""
    local_factory, _, _ = setup_clients
    remote_coordinator = quatt.QuattCicRemoteDataUpdateCoordinator.return_value
    remote_coordinator.async_config_entry_first_refresh.side_effect = (
        ConfigEntryNotReady("Cloud is unavailable")
    )
    hass.config_entries.async_update_entry(
        config_entry,
        data={CONF_LOCAL_CIC: "192.0.2.1", CONF_REMOTE_CIC: "CIC-12345678"},
        options={CONF_LOCAL_API_ENABLED: False},
    )

    with pytest.raises(ConfigEntryNotReady, match="Cloud is unavailable"):
        await quatt.async_setup_entry(hass, config_entry)

    local_factory.assert_not_called()
    assert config_entry.entry_id not in hass.data[DOMAIN]
    assert not hass.services.has_service(DOMAIN, "get_cic_insights")

    remote_coordinator.async_config_entry_first_refresh.side_effect = None
    assert await quatt.async_setup_entry(hass, config_entry) is True
    local_factory.assert_not_called()
    assert hass.services.has_service(DOMAIN, "get_cic_insights")


@pytest.mark.parametrize(
    ("options", "remote_configured"),
    [
        pytest.param({}, True, id="existing-paired-entry"),
        pytest.param({CONF_LOCAL_API_ENABLED: True}, True, id="local-enabled"),
        pytest.param({}, False, id="local-only-entry"),
        pytest.param({CONF_LOCAL_API_ENABLED: False}, False, id="unpaired-entry"),
    ],
)
async def test_local_connection_is_required_unless_paired_and_disabled(
    hass: HomeAssistant, config_entry, setup_clients, options, remote_configured
) -> None:
    """Existing entries keep local startup, including failure and retry behavior."""
    local_factory, local_coordinator, remote_client = setup_clients
    local_coordinator.async_config_entry_first_refresh.side_effect = (
        ConfigEntryNotReady("CIC is offline")
    )
    data = {CONF_LOCAL_CIC: "192.0.2.1"}
    if remote_configured:
        data[CONF_REMOTE_CIC] = "CIC-12345678"
    hass.config_entries.async_update_entry(config_entry, data=data, options=options)

    with pytest.raises(ConfigEntryNotReady, match="CIC is offline"):
        await quatt.async_setup_entry(hass, config_entry)

    local_factory.assert_called_once()
    remote_client.authenticate.assert_not_awaited()
    assert not hass.services.has_service(DOMAIN, "get_cic_insights")


@pytest.mark.parametrize("remote_configured", [True, False])
async def test_local_connection_option_requires_paired_remote(
    hass: HomeAssistant, config_entry, remote_configured, enable_custom_integrations
) -> None:
    """The options form exposes the switch only after Remote API pairing."""
    data = {CONF_LOCAL_CIC: "192.0.2.1"}
    if remote_configured:
        data[CONF_REMOTE_CIC] = "CIC-12345678"
    hass.config_entries.async_update_entry(config_entry, data=data)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    assert result["type"] == "form"
    fields = {key.schema for key in result["data_schema"].schema}
    assert (CONF_LOCAL_API_ENABLED in fields) is remote_configured
    if remote_configured:
        assert result["data_schema"]({})[CONF_LOCAL_API_ENABLED] is True


async def test_local_connection_option_is_saved_and_restored(
    hass: HomeAssistant, config_entry, enable_custom_integrations
) -> None:
    """Turning local access off persists the choice and restores it on reopening."""
    hass.config_entries.async_update_entry(
        config_entry,
        data={CONF_LOCAL_CIC: "192.0.2.1", CONF_REMOTE_CIC: "CIC-12345678"},
    )
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_SCAN_INTERVAL: 10,
            REMOTE_CONF_SCAN_INTERVAL: 1,
            CONF_LOCAL_API_ENABLED: False,
        },
    )

    assert result["type"] == "create_entry"
    assert config_entry.options[CONF_LOCAL_API_ENABLED] is False
    assert config_entry.as_dict()["options"][CONF_LOCAL_API_ENABLED] is False

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["data_schema"]({})[CONF_LOCAL_API_ENABLED] is False
