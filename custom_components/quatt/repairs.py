"""Repairs support for the Quatt integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import data_entry_flow
from homeassistant.components.repairs import ConfirmRepairFlow, RepairsFlow
from homeassistant.core import HomeAssistant

ISSUE_REMOTE_AUTH_FAILED_PREFIX = "remote_auth_failed"


class RemoteAuthFailedRepairFlow(RepairsFlow):
    """Handler to re-pair with the CIC after remote API authentication failed.

    Confirming the flow reloads the config entry, which restarts the
    pairing process. The user then has 60 seconds to press the physical
    button on the CIC to complete pairing.
    """

    def __init__(self, entry_id: str) -> None:
        """Initialize the repair flow."""
        self._entry_id = entry_id

    async def async_step_init(
        self, user_input: dict[str, str] | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle the first step of the repair flow."""
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, str] | None = None
    ) -> data_entry_flow.FlowResult:
        """Ask the user to confirm they are ready to pair, then reload."""
        if user_input is not None:
            self.hass.config_entries.async_schedule_reload(self._entry_id)
            return self.async_create_entry(title="", data={})

        return self.async_show_form(step_id="confirm", data_schema=vol.Schema({}))


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, str] | None,
) -> RepairsFlow:
    """Create a fix flow for a Quatt repair issue."""
    if (
        issue_id.startswith(ISSUE_REMOTE_AUTH_FAILED_PREFIX)
        and data is not None
        and (entry_id := data.get("entry_id"))
    ):
        return RemoteAuthFailedRepairFlow(entry_id)
    return ConfirmRepairFlow()
