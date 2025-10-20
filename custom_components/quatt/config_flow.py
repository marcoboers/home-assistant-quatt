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
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import (
    QuattApiClientAuthenticationError,
    QuattApiClientCommunicationError,
    QuattApiClientError,
)
from .api_local import QuattLocalApiClient
from .api_remote import QuattRemoteApiClient
from .const import (
    CONF_LOCAL_CIC,
    CONF_POWER_SENSOR,
    CONF_REMOTE_CIC,
    DEFAULT_LOCAL_SCAN_INTERVAL,
    DEFAULT_REMOTE_SCAN_INTERVAL,
    DOMAIN,
    LOCAL_MAX_SCAN_INTERVAL,
    LOCAL_MIN_SCAN_INTERVAL,
    LOGGER,
    REMOTE_CONF_SCAN_INTERVAL,
    REMOTE_MAX_SCAN_INTERVAL,
    REMOTE_MIN_SCAN_INTERVAL,
)

CONF_FIRST_NAME = "first_name"
CONF_LAST_NAME = "last_name"


async def _async_register_static_resources(hass: HomeAssistant) -> None:
    """Register the static resource path once if HTTP is available."""
    # Check that the HTTP component is ready
    if not hasattr(hass, "http"):
        return

    # Avoid duplicate registration across reloads
    if hass.data.get(f"_{DOMAIN}_static_registered"):
        return

    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                f"/{DOMAIN}_static",
                hass.config.path(f"custom_components/{DOMAIN}/static"),
                cache_headers=False,
            )
        ]
    )
    hass.data[f"_{DOMAIN}_static_registered"] = True


async def _async_step_pair_common(
    flow,
    config_update: bool,
    user_input: dict | None = None,
) -> config_entries.FlowResult:
    """Handle pairing step in config and options flow."""
    # Ensure static resources are registered for use in the form
    await _async_register_static_resources(flow.hass)

    _errors = {}
    if user_input is not None:
        # User confirmed they are ready to pair
        session = async_create_clientsession(flow.hass)
        api = QuattRemoteApiClient(flow.cic_name, session)

        first_name = user_input[CONF_FIRST_NAME]
        last_name = user_input[CONF_LAST_NAME]

        if not await api.authenticate(first_name=first_name, last_name=last_name):
            _errors["base"] = "pairing_timeout"
        else:
            if not config_update:
                # Pairing successful, create entry with both local and remote
                return flow.async_create_entry(
                    title=flow.cic_name,
                    data={
                        CONF_LOCAL_CIC: flow.ip_address,
                        CONF_REMOTE_CIC: flow.cic_name,
                    },
                )

            # Pairing successful, update config entry
            new_data = {**flow.config_entry.data, CONF_REMOTE_CIC: flow.cic_name}
            flow.hass.config_entries.async_update_entry(
                flow.config_entry, data=new_data
            )
            # Reload the integration to apply changes
            await flow.hass.config_entries.async_reload(flow.config_entry.entry_id)
            return flow.async_create_entry(title="", data={})

    # Try to auto-fill names from Home Assistant user
    default_first_name = ""
    default_last_name = ""

    # Optional: try to prefill with HA user name (if available - rarely used)
    # No try-except needed because async_get_user returns None if user not found
    user_id = flow.context.get("user_id")
    if user_id:
        user = await flow.hass.auth.async_get_user(user_id)
        if user and user.name:
            # Split on first space
            name_parts = user.name.split(" ", 1)
            default_first_name = name_parts[0] if len(name_parts) > 0 else ""
            default_last_name = name_parts[1] if len(name_parts) > 1 else ""

    return flow.async_show_form(
        step_id="pair",
        data_schema=vol.Schema(
            {
                vol.Required(
                    CONF_FIRST_NAME,
                    default=(user_input or {}).get(CONF_FIRST_NAME, default_first_name),
                ): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT),
                ),
                vol.Required(
                    CONF_LAST_NAME,
                    default=(user_input or {}).get(CONF_LAST_NAME, default_last_name),
                ): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT),
                ),
            }
        ),
        errors=_errors,
        description_placeholders={
            "cic": flow.cic_name,
        },
    )


async def _async_get_cic_name(hass: HomeAssistant, ip_address: str) -> str:
    """Validate devic:e and return the CIC id/ name (system.hostName)."""
    client = QuattLocalApiClient(
        ip_address=ip_address,
        session=async_create_clientsession(hass),
    )
    data = await client.async_get_data()
    return data["system"]["hostName"]


# pylint: disable=abstract-method
class QuattFlowHandler(ConfigFlow, domain=DOMAIN):
    """Config flow for Quatt."""

    VERSION = 5

    def __init__(self) -> None:
        """Initialize a Quatt flow."""
        self.ip_address: str | None = None
        self.cic_name: str | None = None
        self.connection_type: str | None = None

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
        """Handle a flow initialized by the user - start with local setup."""
        return await self.async_step_local()

    async def async_step_local(
        self,
        user_input: dict | None = None,
    ) -> config_entries.FlowResult:
        """Handle local connection setup with IP address."""
        _errors = {}
        if user_input is not None:
            try:
                cic_name = await _async_get_cic_name(
                    hass=self.hass,
                    ip_address=user_input[CONF_LOCAL_CIC],
                )
            except QuattApiClientAuthenticationError as exception:
                LOGGER.warning(exception)
                _errors["base"] = "auth"
            except QuattApiClientCommunicationError as exception:
                LOGGER.error(exception)
                _errors["base"] = "cannot_connect"
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

                    if user_input.get("add_remote", False):
                        # User wants to add remote API
                        return await self.async_step_pair()

                    # User doesn't want remote API, create entry with local only
                    return self.async_create_entry(
                        title=self.cic_name,
                        data={
                            CONF_LOCAL_CIC: self.ip_address,
                        },
                    )

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
                    vol.Optional(
                        "add_remote",
                        default=False,
                    ): selector.BooleanSelector(),
                }
            ),
            errors=_errors,
        )

    async def async_step_pair(self, user_input=None) -> config_entries.FlowResult:
        """Handle pairing step in the config flow."""
        return await _async_step_pair_common(
            self, config_update=False, user_input=user_input
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
            await _async_get_cic_name(hass=self.hass, ip_address=discovery_info.ip)
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
        self.cic_name: str | None = None

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
                # First retrieve the cic_name from the local API. The config_entry cannot be
                # used because it can contain the incorrect cic_name because of DHCP discovery
                try:
                    self.cic_name = await _async_get_cic_name(
                        hass=self.hass,
                        ip_address=self.config_entry.data[CONF_LOCAL_CIC],
                    )
                except QuattApiClientAuthenticationError as exception:
                    LOGGER.warning(exception)
                    _errors["base"] = "auth"
                except QuattApiClientCommunicationError as exception:
                    LOGGER.error(exception)
                    _errors["base"] = "cannot_connect"
                except QuattApiClientError as exception:
                    LOGGER.exception(exception)
                    _errors["base"] = "unknown"
                else:
                    if self.cic_name is not None:
                        # User wants to add remote API
                        return await self.async_step_pair()
            else:
                return self.async_create_entry(title="", data=user_input)

        # Build schema based on whether remote is already configured
        schema_dict = {
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=self.config_entry.options.get(
                    CONF_SCAN_INTERVAL, DEFAULT_LOCAL_SCAN_INTERVAL
                ),
            ): vol.All(
                vol.Coerce(int),
                vol.Range(min=LOCAL_MIN_SCAN_INTERVAL, max=LOCAL_MAX_SCAN_INTERVAL),
            ),
            vol.Required(
                REMOTE_CONF_SCAN_INTERVAL,
                default=self.config_entry.options.get(
                    REMOTE_CONF_SCAN_INTERVAL, DEFAULT_REMOTE_SCAN_INTERVAL
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=REMOTE_MIN_SCAN_INTERVAL,
                    max=REMOTE_MAX_SCAN_INTERVAL,
                    mode=selector.NumberSelectorMode.BOX,
                )
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
            schema_dict[vol.Optional("add_remote", default=False)] = (
                selector.BooleanSelector()
            )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_dict),
            errors=_errors,
        )

    async def async_step_pair(self, user_input=None) -> config_entries.FlowResult:
        """Handle pairing step in the options flow."""
        return await _async_step_pair_common(
            self, config_update=True, user_input=user_input
        )
