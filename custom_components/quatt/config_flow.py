"""Adds config flow for Quatt."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_IP_ADDRESS, CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import (
    QuattApiClient,
    QuattApiClientAuthenticationError,
    QuattApiClientCommunicationError,
    QuattApiClientError,
)
from .const import (
    CONF_POWER_SENSOR,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOGGER,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)


class QuattFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Quatt."""

    VERSION = 2

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
                # Check if this cic has already been configured
                # Pre-version 2 config flows are not detected!
                await self.async_set_unique_id(cic_hostname)
                self._abort_if_unique_id_configured()

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

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the options flow handler for this config entry."""
        return QuattOptionsFlowHandler(config_entry)


class QuattOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow for Quatt."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        _errors = {}

        # Retrieve the current value of CONF_POWER_SENSOR from options
        current_power_sensor = self.config_entry.options.get(CONF_POWER_SENSOR, "") if self.config_entry.options is not None else ""

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)),
                    vol.Optional(
                        CONF_POWER_SENSOR,
                        description={"suggested_value": current_power_sensor if self.hass.states.get(current_power_sensor) else ""},
                    ): selector.EntitySelector(
                        selector.EntityFilterSelectorConfig(
                            device_class=SensorDeviceClass.POWER
                        )
                    )
                }
            ),
            errors=_errors,
        )
