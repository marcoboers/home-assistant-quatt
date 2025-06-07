"""Adds config flow for Quatt."""

from __future__ import annotations

import ipaddress

import voluptuous as vol

from homeassistant import config_entries, data_entry_flow
from homeassistant.components import dhcp
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
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


# pylint: disable=abstract-method
class QuattFlowHandler(ConfigFlow, domain=DOMAIN):
    """Config flow for Quatt."""

    VERSION = 3

    def __init__(self) -> None:
        """Initialize a Quatt flow."""
        self.ip_address: str | None = None
        self.hostname: str | None = None

    async def _test_credentials(self, ip_address: str) -> str:
        """Validate credentials."""
        client = QuattApiClient(
            ip_address=ip_address,
            session=async_create_clientsession(self.hass),
        )
        data = await client.async_get_data()
        return data["system"]["hostName"]

    def is_valid_ip(self, ip_str) -> bool:
        """Check for valid ip."""
        try:
            # Attempt to create an IPv4 or IPv6 address object
            ipaddress.ip_address(ip_str)
        except ValueError:
            # If a ValueError is raised, the IP address is invalid
            return False
        return True

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
                if cic_hostname is not None:
                    # Check if this cic has already been configured
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

    async def async_step_dhcp(
        self, discovery_info: dhcp.DhcpServiceInfo
    ) -> ConfigFlowResult:
        """Handle DHCP discovery."""
        LOGGER.debug(
            "DHCP discovery detected Quatt CIC (hostname): %s with ip-address: %s",
            discovery_info.hostname,
            discovery_info.ip,
        )

        # Get the status page to validate that we are dealing with a Quatt because
        # the DHCP match is only on "cic-*"
        try:
            await self._test_credentials(ip_address=discovery_info.ip)
        except (
            QuattApiClientAuthenticationError,
            QuattApiClientCommunicationError,
            QuattApiClientError,
        ):
            # For all exceptions we abort the flow
            LOGGER.debug(
                "DHCP discovery no match: %s with ip-address: %s",
                discovery_info.hostname,
                discovery_info.ip,
            )
            return self.async_abort(reason="no_match")
        else:
            LOGGER.debug(
                "DHCP discovery validated detected Quatt CIC: %s with ip-address: %s",
                discovery_info.hostname,
                discovery_info.ip,
            )

            # Uppercase the first 3 characters CIC-xxxxxxxx-xxxx-xxxx-xxxxxxxxxxxx
            # This enables the correct match on DHCP hostname
            hostname_unique_id = discovery_info.hostname
            if len(hostname_unique_id) >= 3:
                hostname_unique_id = (
                    hostname_unique_id[:3].upper() + hostname_unique_id[3:]
                )

            # Loop through existing config entries to check for a match with prefix
            for entry in self.hass.config_entries.async_entries(self.handler):
                # Hostnames could be shortened by routers so the check is done on a partial match
                # Both directions have to be checked because routers can be switched
                if entry.unique_id.startswith(
                    hostname_unique_id
                ) or hostname_unique_id.startswith(entry.unique_id):
                    # Use the found entry unique_id
                    await self.async_set_unique_id(entry.unique_id)
                    self.ip_address = discovery_info.ip
                    self.hostname = discovery_info.hostname

                    if self.is_valid_ip(ip_str=entry.data.get(CONF_IP_ADDRESS, "")):
                        # Configuration is an ip-address, update it
                        LOGGER.debug(
                            "DHCP discovery detected existing Quatt CIC: %s with ip-address: %s, "
                            "updating ip for existing entry",
                            discovery_info.hostname,
                            discovery_info.ip,
                        )

                        self._abort_if_unique_id_configured(
                            updates={CONF_IP_ADDRESS: discovery_info.ip},
                        )
                    else:
                        self._abort_if_unique_id_configured()

                    # Config found so terminate the loop
                    break

            # No match found, so this is a new CIC
            await self.async_set_unique_id(hostname_unique_id)
            self.ip_address = discovery_info.ip
            self.hostname = discovery_info.hostname

            self.context.update({"title_placeholders": {"name": hostname_unique_id}})
            return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input=None
    ) -> data_entry_flow.ConfigFlowResult:
        """Allow the user to confirm adding the device."""
        if user_input is not None:
            # Use the hostname instead of the ip
            return self.async_create_entry(
                title=self.hostname, data={CONF_IP_ADDRESS: self.ip_address}
            )

        return self.async_show_form(step_id="confirm")

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> QuattOptionsFlowHandler:
        """Return the options flow handler for this config entry."""
        return QuattOptionsFlowHandler()


class QuattOptionsFlowHandler(OptionsFlow):
    """Options flow for Quatt."""

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        _errors = {}

        # Retrieve the current value of CONF_POWER_SENSOR from options
        current_power_sensor = (
            self.config_entry.options.get(CONF_POWER_SENSOR, "")
            if self.config_entry.options is not None
            else ""
        )

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
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                    ),
                    vol.Optional(
                        CONF_POWER_SENSOR,
                        description={
                            "suggested_value": current_power_sensor
                            if self.hass.states.get(current_power_sensor)
                            else ""
                        },
                    ): selector.EntitySelector(
                        selector.EntityFilterSelectorConfig(
                            device_class=SensorDeviceClass.POWER
                        )
                    ),
                }
            ),
            errors=_errors,
        )
