"""Tests for the Quatt repairs platform."""
# pylint: disable=import-error

from __future__ import annotations

from unittest.mock import Mock

import pytest

from homeassistant.components.repairs import ConfirmRepairFlow
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
import homeassistant.helpers.issue_registry as ir

from custom_components.quatt.const import DOMAIN
from custom_components.quatt.repairs import (
    RemoteAuthFailedRepairFlow,
    async_create_fix_flow,
    async_create_remote_auth_issue,
    async_delete_remote_auth_issue,
    remote_auth_issue_id,
)

pytestmark = pytest.mark.asyncio


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
