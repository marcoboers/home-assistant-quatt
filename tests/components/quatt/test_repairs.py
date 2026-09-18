"""Tests for the Quatt repairs platform."""
# pylint: disable=import-error

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from homeassistant.components.repairs import ConfirmRepairFlow
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
import homeassistant.helpers.issue_registry as ir

from custom_components.quatt.api_remote_auth import QuattRemoteAuthClient
from custom_components.quatt.api_remote_cic import QuattCicRemoteApiClient
from custom_components.quatt.const import DOMAIN
from custom_components.quatt.repairs import (
    RemoteAuthFailedRepairFlow,
    async_create_fix_flow,
    async_create_remote_auth_issue,
    async_delete_remote_auth_issue,
    remote_auth_issue_id,
)

pytestmark = pytest.mark.asyncio


async def test_remote_auth_issue_uses_cic_name_in_translation() -> None:
    """Repair text should clearly identify which CIC needs to be re-paired."""
    await asyncio.sleep(0)

    strings = json.loads(
        (
            Path(__file__).resolve().parents[3]
            / "custom_components"
            / "quatt"
            / "strings.json"
        ).read_text(encoding="utf-8")
    )
    issue = strings["issues"]["remote_auth_failed"]

    assert "{name}" in issue["title"]
    assert "{name}" in issue["fix_flow"]["step"]["confirm"]["description"]


async def test_auth_recovery_does_not_clear_shared_cic_tokens() -> None:
    """A failed validation on one CIC must not invalidate the shared account auth."""
    auth = QuattRemoteAuthClient(session=Mock())
    auth.load_tokens("id-token", "refresh-token")
    auth.refresh_token = AsyncMock(return_value=False)
    auth.ensure_authenticated = AsyncMock(return_value=True)

    client = QuattCicRemoteApiClient("CIC-1", session=Mock(), auth=auth)
    client.get_cic_data = AsyncMock(return_value=None)
    client._request_pair = AsyncMock(return_value=True)
    client._wait_for_pairing = AsyncMock(return_value=True)
    client._resolve_installation_id = AsyncMock(return_value=True)
    client._save_installation_id = AsyncMock()

    assert await client.authenticate() is True
    assert auth.id_token == "id-token"
    assert auth._refresh_token == "refresh-token"


async def test_two_cic_clients_share_auth_without_cross_reset() -> None:
    """A failed auth validation for the first CIC must not wipe the shared auth for the second CIC."""
    auth = QuattRemoteAuthClient(session=Mock())
    auth.load_tokens("id-token", "refresh-token")

    first = QuattCicRemoteApiClient("CIC-1", session=Mock(), auth=auth)
    second = QuattCicRemoteApiClient("CIC-2", session=Mock(), auth=auth)

    first.get_cic_data = AsyncMock(return_value=None)
    first._request_pair = AsyncMock(return_value=True)
    first._wait_for_pairing = AsyncMock(return_value=True)
    first._resolve_installation_id = AsyncMock(return_value=True)
    first._save_installation_id = AsyncMock()
    first._auth.refresh_token = AsyncMock(return_value=False)
    first._auth.ensure_authenticated = AsyncMock(return_value=True)

    second.get_cic_data = AsyncMock(return_value={"result": {"status": "ok"}})

    assert await first.authenticate() is True
    assert auth.id_token == "id-token"
    assert auth._refresh_token == "refresh-token"
    assert await second.get_cic_data() == {"result": {"status": "ok"}}


async def test_create_remote_auth_issue(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> None:
    """A fixable repair issue should be registered for the config entry."""
    async_create_remote_auth_issue(hass, config_entry)

    issue_registry = ir.async_get(hass)
    issue = issue_registry.async_get_issue(
        DOMAIN, remote_auth_issue_id(config_entry.entry_id)
    )

    assert issue is not None
    assert issue.is_fixable is True
    assert issue.severity == ir.IssueSeverity.ERROR
    assert issue.translation_key == "remote_auth_failed"
    assert issue.translation_placeholders == {"name": config_entry.title}
    assert issue.data == {"entry_id": config_entry.entry_id}


async def test_delete_remote_auth_issue(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> None:
    """The repair issue should be removed again on successful authentication."""
    async_create_remote_auth_issue(hass, config_entry)
    async_delete_remote_auth_issue(hass, config_entry)

    issue_registry = ir.async_get(hass)
    assert (
        issue_registry.async_get_issue(
            DOMAIN, remote_auth_issue_id(config_entry.entry_id)
        )
        is None
    )


async def test_delete_remote_auth_issue_when_absent(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> None:
    """Deleting a non-existing issue should be a harmless no-op."""
    async_delete_remote_auth_issue(hass, config_entry)

    issue_registry = ir.async_get(hass)
    assert (
        issue_registry.async_get_issue(
            DOMAIN, remote_auth_issue_id(config_entry.entry_id)
        )
        is None
    )


async def test_create_fix_flow_returns_remote_auth_flow(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> None:
    """The remote auth issue should get the dedicated re-pair fix flow."""
    flow = await async_create_fix_flow(
        hass,
        remote_auth_issue_id(config_entry.entry_id),
        {"entry_id": config_entry.entry_id},
    )

    assert isinstance(flow, RemoteAuthFailedRepairFlow)


@pytest.mark.parametrize(
    ("issue_id", "data"),
    [
        pytest.param("some_other_issue", {"entry_id": "abc"}, id="unknown-issue"),
        pytest.param("remote_auth_failed_abc", None, id="missing-data"),
        pytest.param("remote_auth_failed_abc", {}, id="missing-entry-id"),
    ],
)
async def test_create_fix_flow_fallback(
    hass: HomeAssistant, issue_id: str, data: dict[str, str] | None
) -> None:
    """Unknown or incomplete issues should fall back to a confirm flow."""
    flow = await async_create_fix_flow(hass, issue_id, data)

    assert isinstance(flow, ConfirmRepairFlow)
    assert not isinstance(flow, RemoteAuthFailedRepairFlow)


async def test_repair_flow_shows_confirm_form(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> None:
    """The first step of the fix flow should show the confirm form."""
    flow = RemoteAuthFailedRepairFlow(config_entry.entry_id)
    flow.hass = hass

    result = await flow.async_step_init()

    assert result["type"] == "form"
    assert result["step_id"] == "confirm"


async def test_repair_flow_confirm_reloads_entry(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> None:
    """Confirming the fix flow should schedule a reload of the config entry."""
    flow = RemoteAuthFailedRepairFlow(config_entry.entry_id)
    flow.hass = hass
    hass.config_entries.async_schedule_reload = Mock()

    result = await flow.async_step_confirm(user_input={})

    assert result["type"] == "create_entry"
    hass.config_entries.async_schedule_reload.assert_called_once_with(
        config_entry.entry_id
    )
