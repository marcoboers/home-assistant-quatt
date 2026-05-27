"""Switch entity implementations for Quatt."""

from __future__ import annotations

import logging

from .api_remote_cic import QuattCicRemoteApiClient
from .api_remote_energy import QuattEnergyApiClient
from .entity import QuattSwitch

_LOGGER = logging.getLogger(__name__)


class QuattSettingSwitch(QuattSwitch):
    """Switch entity for Quatt boolean settings."""

    def turn_on(self, **kwargs) -> None:
        """Implement required base class method but do not use it."""
        raise NotImplementedError("Use async_turn_on instead")

    def turn_off(self, **kwargs) -> None:
        """Implement required base class method but do not use it."""
        raise NotImplementedError("Use async_turn_off instead")

    async def _perform_api_update(self, state: bool) -> bool:
        """Perform boolean setting update."""
        remote_client = self.coordinator.client
        if not isinstance(remote_client, QuattCicRemoteApiClient):
            _LOGGER.error(
                "Cannot update %s: remote client required", self.entity_description.key
            )
            return False

        key_parts = self.entity_description.key.split(".")
        settings = {}
        current = settings
        for i, part in enumerate(key_parts):
            if i == len(key_parts) - 1:
                current[part] = state
            else:
                current[part] = {}
                current = current[part]

        _LOGGER.debug("Updating CIC setting: %s", settings)
        return await remote_client.update_cic_settings(settings)


class QuattEnergyPriceFlagSwitch(QuattSwitch):
    """Switch backing a Quatt Energy price-display flag (VAT / tax / markup).

    The entity_description.key maps to the corresponding API client kwarg
    (``include_vat``/``include_tax``/``include_markup``). State lives on the
    client - persisted in the per-hub Store - so toggling does not require
    an entry reload. After updating the flag the coordinator is refreshed
    so the next call to the prices endpoint immediately reflects the new
    set of surcharges.
    """

    @property
    def is_on(self) -> bool:
        """Read the current flag value from the API client."""
        client = self.coordinator.client
        if not isinstance(client, QuattEnergyApiClient):
            return False
        return bool(getattr(client, self.entity_description.key, False))

    async def async_turn_on(self, **kwargs) -> None:
        """Enable the flag."""
        await self._async_apply(True)

    async def async_turn_off(self, **kwargs) -> None:
        """Disable the flag."""
        await self._async_apply(False)

    async def _async_apply(self, value: bool) -> None:
        client = self.coordinator.client
        if not isinstance(client, QuattEnergyApiClient):
            raise TypeError(
                "QuattEnergyPriceFlagSwitch requires a Quatt Energy client",
            )
        changed = await client.set_price_flags(**{self.entity_description.key: value})
        self.async_write_ha_state()
        if changed:
            await self.coordinator.async_request_refresh()

    async def _perform_api_update(self, state: bool) -> bool:
        """Unused - turn_on/off override the base ``QuattSwitch`` flow."""
        raise NotImplementedError
