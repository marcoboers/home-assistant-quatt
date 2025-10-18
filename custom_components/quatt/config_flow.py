"""Adds config flow for Quatt."""

from __future__ import annotations

import ipaddress

import voluptuous as vol

from homeassistant import config_entries, data_entry_flow
from homeassistant.components import dhcp
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import (
    QuattApiClientAuthenticationError,
    QuattApiClientCommunicationError,
    QuattApiClientError,
    QuattLocalApiClient,
    QuattRemoteApiClient,
)
from .const import (
    CONF_LOCAL_CIC,
    CONF_POWER_SENSOR,
    CONF_REMOTE_CIC,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOGGER,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)

CONF_FIRST_NAME = "first_name"
CONF_LAST_NAME = "last_name"


# pylint: disable=abstract-method
class QuattFlowHandler(ConfigFlow, domain=DOMAIN):
    """Config flow for Quatt."""

    VERSION = 5

    def __init__(self) -> None:
        """Initialize a Quatt flow."""
        self.ip_address: str | None = None
        self.cic_name: str | None = None
        self.connection_type: str | None = None
        self.cic_id: str | None = None

    async def _get_cic_name(self, ip_address: str) -> str:
        """Validate device and return the CIC id/name (system.hostName)."""
        client = QuattLocalApiClient(
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

    async def _register_static_resources(self) -> None:
        """Register the static resource path once if HTTP is available."""
        # Check that the HTTP component is ready
        if not hasattr(self.hass, "http"):
            return

        # Avoid duplicate registration across reloads
        if self.hass.data.get(f"_{DOMAIN}_static_registered"):
            return

        await self.hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    f"/{DOMAIN}_static",
                    self.hass.config.path(f"custom_components/{DOMAIN}/static"),
                    cache_headers=False,
                )
            ]
        )
        self.hass.data[f"_{DOMAIN}_static_registered"] = True

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.FlowResult:
        """Handle a flow initialized by the user - start with local setup."""
        # Ensure static resources are registered for use in the form
        await self._register_static_resources()

        return await self.async_step_local()

    async def async_step_local(
        self,
        user_input: dict | None = None,
    ) -> config_entries.FlowResult:
        """Handle local connection setup with IP address."""
        _errors = {}
        if user_input is not None:
            try:
                cic_name = await self._get_cic_name(
                    ip_address=user_input[CONF_LOCAL_CIC],
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
                if cic_name is not None:
                    # Check if this cic has already been configured
                    await self.async_set_unique_id(cic_name)
                    self._abort_if_unique_id_configured()

                    # Store cic_name and ip for next step
                    self.cic_name = cic_name
                    self.ip_address = user_input[CONF_LOCAL_CIC]

                    # Ask if user wants to add remote API
                    return await self.async_step_add_remote()

        return self.async_show_form(
            step_id="local",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_LOCAL_CIC,
                        default=(user_input or {}).get(CONF_LOCAL_CIC),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT
                        ),
                    ),
                }
            ),
            errors=_errors,
        )

    async def async_step_add_remote(
        self,
        user_input: dict | None = None,
    ) -> config_entries.FlowResult:
        """Ask if user wants to add remote API access."""
        if user_input is not None:
            if user_input.get("add_remote", False):
                # User wants to add remote API
                return await self.async_step_remote()

            # User doesn't want remote API, create entry with local only
            return self.async_create_entry(
                title=self.cic_name,
                data={
                    CONF_LOCAL_CIC: self.ip_address,
                },
            )

        return self.async_show_form(
            step_id="add_remote",
            data_schema=vol.Schema(
                {
                    vol.Required("add_remote", default=False): selector.BooleanSelector(),
                }
            ),
            description_placeholders={
                "cic_name": self.cic_name,
            },
        )

    async def async_step_remote(
        self,
        user_input: dict | None = None,
    ) -> config_entries.FlowResult:
        """Handle remote connection setup - enter CIC ID."""
        _errors = {}

        if user_input is not None:
            cic_id = user_input[CONF_REMOTE_CIC]

            # Validate CIC format
            if not cic_id.startswith("CIC-") or len(cic_id) <= 4:
                _errors["cic"] = "invalid_cic"
            else:
                # Store CIC for pairing step
                self.cic_id = cic_id
                return await self.async_step_pair()

        # Pre-fill with cic_name if available (from local setup)
        default_cic = self.cic_name if self.cic_name else ""

        return self.async_show_form(
            step_id="remote",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_REMOTE_CIC, default=default_cic): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT
                        ),
                    ),
                }
            ),
            errors=_errors,
            description_placeholders={"cic_example": "CIC-xxxx-xxxx-xxxx"},
        )

    async def async_step_pair(
        self,
        user_input: dict | None = None,
    ) -> config_entries.FlowResult:
        """Handle pairing step - user presses button on CIC."""
        _errors = {}

        if user_input is not None:
            # User confirmed they are ready to pair
            try:
                # Create API client and authenticate
                session = async_create_clientsession(self.hass)
                api = QuattRemoteApiClient(self.cic_id, session)

                first_name = user_input[CONF_FIRST_NAME]
                last_name = user_input[CONF_LAST_NAME]

                if not await api.authenticate(
                    first_name=first_name, last_name=last_name
                ):
                    _errors["base"] = "pairing_timeout"
                else:
                    # Pairing successful
                    # Create entry with both local and remote
                    return self.async_create_entry(
                        title=self.cic_name,
                        data={
                            CONF_LOCAL_CIC: self.ip_address,
                            CONF_REMOTE_CIC: self.cic_id,
                        },
                    )
            except Exception:  # pylint: disable=broad-except
                LOGGER.exception("Unexpected exception during pairing")
                _errors["base"] = "unknown"

        # Try to auto-fill names from Home Assistant user
        default_first_name = ""
        default_last_name = ""

        try:
            # Get the current user from the context
            if self.context.get("user_id"):
                user = await self.hass.auth.async_get_user(self.context["user_id"])
                if user and user.name:
                    # Split on first space
                    name_parts = user.name.split(" ", 1)
                    default_first_name = name_parts[0] if len(name_parts) > 0 else ""
                    default_last_name = name_parts[1] if len(name_parts) > 1 else ""
        except Exception:  # pylint: disable=broad-except
            # If we can't get the user name, just use empty defaults
            pass

        # Show pairing instructions with name fields
        return self.async_show_form(
            step_id="pair",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_FIRST_NAME,
                        default=(user_input or {}).get(
                            CONF_FIRST_NAME, default_first_name
                        ),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT
                        ),
                    ),
                    vol.Required(
                        CONF_LAST_NAME,
                        default=(user_input or {}).get(
                            CONF_LAST_NAME, default_last_name
                        ),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT
                        ),
                    ),
                }
            ),
            errors=_errors,
            description_placeholders={
                "cic": self.cic_id,
            },
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
        # the DHCP match is only on "cic-*". We cannot use the cic-name here because
        # it is set at a later stage in the rebootprocess of the CIC.
        try:
            await self._get_cic_name(ip_address=discovery_info.ip)
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
                    self.cic_name = discovery_info.hostname

                    if self.is_valid_ip(ip_str=entry.data.get(CONF_LOCAL_CIC, "")):
                        # Configuration is an ip-address, update it
                        LOGGER.debug(
                            "DHCP discovery detected existing Quatt CIC: %s with ip-address: %s, "
                            "updating ip for existing entry",
                            discovery_info.hostname,
                            discovery_info.ip,
                        )

                        self._abort_if_unique_id_configured(
                            updates={CONF_LOCAL_CIC: discovery_info.ip},
                        )
                    else:
                        self._abort_if_unique_id_configured()

                    # Config found so terminate the loop
                    break

            # No match found, so this is a new CIC
            await self.async_set_unique_id(hostname_unique_id)
            self.ip_address = discovery_info.ip
            self.cic_name = discovery_info.hostname

            self.context.update({"title_placeholders": {"name": hostname_unique_id}})
            return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input=None
    ) -> data_entry_flow.ConfigFlowResult:
        """Allow the user to confirm adding the device."""
        if user_input is not None:
            # Use the hostname instead of the ip (DHCP discovered device - always local)
            return self.async_create_entry(
                title=self.cic_name,
                data={
                    CONF_LOCAL_CIC: self.ip_address,
                },
            )

        return self.async_show_form(step_id="confirm")

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> QuattOptionsFlowHandler:
        """Return the options flow handler for this config entry."""
        return QuattOptionsFlowHandler()


class QuattOptionsFlowHandler(OptionsFlow):
    """Options flow for Quatt."""

    def __init__(self) -> None:
        """Initialize options flow."""
        self.cic_id: str | None = None

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        _errors = {}

        # Retrieve the current value of CONF_POWER_SENSOR from options
        current_power_sensor = (
            self.config_entry.options.get(CONF_POWER_SENSOR, "")
            if self.config_entry.options is not None
            else ""
        )

        # Check if remote API is already configured
        has_remote = CONF_REMOTE_CIC in self.config_entry.data

        if user_input is not None:
            # Check if user wants to add remote API
            if not has_remote and user_input.get("add_remote", False):
                # User wants to add remote API
                return await self.async_step_add_remote()

            return self.async_create_entry(title="", data=user_input)

        # Build schema based on whether remote is already configured
        schema_dict = {
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

        # Add option to add remote API if not already configured
        if not has_remote:
            schema_dict[vol.Optional("add_remote", default=False)] = selector.BooleanSelector()

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_dict),
            errors=_errors,
        )

    async def async_step_add_remote(
        self,
        user_input: dict | None = None,
    ) -> config_entries.FlowResult:
        """Handle adding remote API via options."""
        _errors = {}

        if user_input is not None:
            cic_id = user_input[CONF_REMOTE_CIC]

            # Validate CIC format
            if not cic_id.startswith("CIC-") or len(cic_id) <= 4:
                _errors["cic"] = "invalid_cic"
            else:
                # Store CIC for pairing step
                self.cic_id = cic_id
                return await self.async_step_pair_options()

        # Pre-fill with existing CIC name if available
        default_cic = self.config_entry.unique_id or ""

        return self.async_show_form(
            step_id="add_remote",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_REMOTE_CIC, default=default_cic): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT
                        ),
                    ),
                }
            ),
            errors=_errors,
            description_placeholders={"cic_example": "CIC-xxxx-xxxx-xxxx"},
        )

    async def async_step_pair_options(
        self,
        user_input: dict | None = None,
    ) -> config_entries.FlowResult:
        """Handle pairing step in options flow."""
        _errors = {}

        if user_input is not None:
            # User confirmed they are ready to pair
            try:
                # Create API client and authenticate
                session = async_create_clientsession(self.hass)
                api = QuattRemoteApiClient(self.cic_id, session)

                first_name = user_input[CONF_FIRST_NAME]
                last_name = user_input[CONF_LAST_NAME]

                if not await api.authenticate(first_name=first_name, last_name=last_name):
                    _errors["base"] = "pairing_timeout"
                else:
                    # Pairing successful, update config entry
                    new_data = {**self.config_entry.data, CONF_REMOTE_CIC: self.cic_id}
                    self.hass.config_entries.async_update_entry(
                        self.config_entry, data=new_data
                    )
                    # Reload the integration to apply changes
                    await self.hass.config_entries.async_reload(self.config_entry.entry_id)
                    return self.async_create_entry(title="", data={})
            except Exception:  # pylint: disable=broad-except
                LOGGER.exception("Unexpected exception during pairing")
                _errors["base"] = "unknown"

        # Try to auto-fill names from Home Assistant user
        default_first_name = ""
        default_last_name = ""

        try:
            # Get the current user from the context
            if self.context.get("user_id"):
                user = await self.hass.auth.async_get_user(self.context["user_id"])
                if user and user.name:
                    # Split on first space
                    name_parts = user.name.split(" ", 1)
                    default_first_name = name_parts[0] if len(name_parts) > 0 else ""
                    default_last_name = name_parts[1] if len(name_parts) > 1 else ""
        except Exception:  # pylint: disable=broad-except
            pass

        return self.async_show_form(
            step_id="pair_options",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_FIRST_NAME,
                        default=(user_input or {}).get(CONF_FIRST_NAME, default_first_name),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT
                        ),
                    ),
                    vol.Required(
                        CONF_LAST_NAME,
                        default=(user_input or {}).get(CONF_LAST_NAME, default_last_name),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT
                        ),
                    ),
                }
            ),
            errors=_errors,
            description_placeholders={
                "cic": self.cic_id,
            },
        )
