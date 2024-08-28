"""Adds config flow for Quatt."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import (
    QuattApiClient,
    QuattApiClientAuthenticationError,
    QuattApiClientCommunicationError,
    QuattApiClientError,
)
from .const import (
    DOMAIN,
    LOGGER,
    CONF_POWER_SENSOR,
)


class QuattFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Quatt."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.FlowResult:
        """Handle a flow initialized by the user."""
        _errors = {}
        if user_input is not None:
            try:
                cic_hostname = await self._test_credentials(
                    ip_address=user_input[CONF_IP_ADDRESS],
                )
            except QuattApiClientAuthenticationError as exception:
                LOGGER.warning(exception)
                _errors["base"] = "auth"
            except QuattApiClientCommunicationError as exception:
                LOGGER.error(exception)
                _errors["base"] = "connection"
            except QuattApiClientError as exception:
                LOGGER.exception(exception)
                _errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=cic_hostname,
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_IP_ADDRESS,
                        default=(user_input or {}).get(CONF_IP_ADDRESS),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT
                        ),
                    ),
                    vol.Optional(CONF_POWER_SENSOR): selector.EntitySelector(
                        selector.EntityFilterSelectorConfig(
                            device_class=SensorDeviceClass.POWER
                        )
                    ),
                }
            ),
            errors=_errors,
        )

    async def _test_credentials(self, ip_address: str) -> str:
        """Validate credentials."""
        client = QuattApiClient(
            ip_address=ip_address,
            session=async_create_clientsession(self.hass),
        )
        data = await client.async_get_data()
        return data["system"]["hostName"]
