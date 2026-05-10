"""Adds config flow for Quatt."""

from __future__ import annotations

import ipaddress
from urllib.parse import urlparse

import voluptuous as vol

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
from homeassistant.helpers.storage import Store

try:
    from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo
except ImportError:
    # import fallback for Home Assistant versions < 2025.2
    from homeassistant.components.dhcp import (
        DhcpServiceInfo,  # type: ignore  # noqa: PGH003
    )

from .api import (
    QuattApiClientAuthenticationError,
    QuattApiClientCommunicationError,
    QuattApiClientError,
)
from .api_local_cic import QuattCicLocalApiClient
from .api_remote_cic import QuattCicRemoteApiClient
from .api_remote_home_battery import QuattHomeBatteryApiClient
from .const import (
    CONF_HOME_BATTERY_CHECK_CODE,
    CONF_HOME_BATTERY_QR_URL,
    CONF_HOME_BATTERY_SERIAL,
    CONF_HOME_BATTERY_UUID,
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
    REMOTE_STORAGE_KEY_PREFIX,
    STORAGE_VERSION,
)

CONF_FIRST_NAME = "first_name"
CONF_LAST_NAME = "last_name"

# After the shared auth step succeeds, route to one of these follow-up steps.
_AFTER_AUTH_PAIR_CIC = "pair"
_AFTER_AUTH_HOME_BATTERY = "home_battery_pair"


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


async def _async_resolve_default_names(flow) -> tuple[str, str]:
    """Pick defaults for the first/last-name form.

    Prefers previously stored names on the shared auth client, falls back to
    the current Home Assistant user's display name.
    """
    # Local import to avoid a circular import at module load time.
    from . import _get_or_create_auth_client  # noqa: PLC0415

    auth = await _get_or_create_auth_client(flow.hass)
    if auth.first_name or auth.last_name:
        return auth.first_name or "", auth.last_name or ""

    user_id = flow.context.get("user_id")
    if user_id:
        user = await flow.hass.auth.async_get_user(user_id)
        if user and user.name:
            parts = user.name.split(" ", 1)
            return (
                parts[0] if len(parts) > 0 else "",
                parts[1] if len(parts) > 1 else "",
            )

    return "", ""


async def _async_step_auth_common(
    flow,
    user_input: dict | None = None,
) -> ConfigFlowResult:
    """Shared auth step: ask first/last name, run signup, save tokens+names.

    Skipped automatically when the shared auth client already has valid tokens
    and a stored profile. On success, routes to ``flow._after_auth_step`` which
    handles the device-specific pairing follow-up.
    """
    await _async_register_static_resources(flow.hass)

    # Local import to avoid a circular import at module load time.
    from . import _get_or_create_auth_client  # noqa: PLC0415

    auth = await _get_or_create_auth_client(flow.hass)

    # Fast path: tokens + profile already stored. A refresh confirms the
    # tokens are still usable before we proceed to pairing.
    if (
        user_input is None
        and auth.is_authenticated
        and auth.first_name
        and auth.last_name
        and await auth.refresh_token()
    ):
        await auth.save_tokens()
        return await _async_continue_after_auth(flow)

    _errors: dict[str, str] = {}
    if user_input is not None:
        first_name = user_input[CONF_FIRST_NAME].strip()
        last_name = user_input[CONF_LAST_NAME].strip()
        if await auth.ensure_authenticated(
            first_name=first_name, last_name=last_name
        ):
            return await _async_continue_after_auth(flow)
        _errors["base"] = "auth"

    default_first, default_last = await _async_resolve_default_names(flow)

    return flow.async_show_form(
        step_id="auth",
        data_schema=vol.Schema(
            {
                vol.Required(
                    CONF_FIRST_NAME,
                    default=(user_input or {}).get(CONF_FIRST_NAME, default_first),
                ): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT),
                ),
                vol.Required(
                    CONF_LAST_NAME,
                    default=(user_input or {}).get(CONF_LAST_NAME, default_last),
                ): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT),
                ),
            }
        ),
        errors=_errors,
    )


async def _async_continue_after_auth(flow) -> ConfigFlowResult:
    """Dispatch to the device-specific step after the auth step finishes."""
    target = getattr(flow, "_after_auth_step", _AFTER_AUTH_PAIR_CIC)
    if target == _AFTER_AUTH_HOME_BATTERY:
        return await flow.async_step_home_battery()
    return await flow.async_step_pair()


async def _async_step_pair_common(
    flow,
    config_update: bool,
    user_input: dict | None = None,
) -> ConfigFlowResult:
    """Handle the CIC pairing confirmation + handshake.

    By the time this step runs the shared auth client is already authenticated
    (see :func:`_async_step_auth_common`), so this step only needs to confirm
    the user is ready to press the button and then complete the CIC-specific
    pairing handshake.
    """
    await _async_register_static_resources(flow.hass)

    _errors: dict[str, str] = {}
    if user_input is not None:
        session = async_create_clientsession(flow.hass)

        # Use the HA-assigned unique_id as stable store key.
        # - Config flow: flow.unique_id
        # - Options flow: flow.config_entry.unique_id
        store_key = flow.config_entry.unique_id if config_update else flow.unique_id
        store = Store(
            flow.hass,
            STORAGE_VERSION,
            f"{REMOTE_STORAGE_KEY_PREFIX}_{store_key}",
        )
        # Local import to avoid a circular import at module load time.
        from . import _get_or_create_auth_client  # noqa: PLC0415

        auth = await _get_or_create_auth_client(flow.hass)
        api = QuattCicRemoteApiClient(
            flow.cic_name, session, store=store, auth=auth
        )

        if not await api.authenticate():
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

    return flow.async_show_form(
        step_id="pair",
        data_schema=vol.Schema({}),
        errors=_errors,
        description_placeholders={
            "cic": flow.cic_name,
        },
    )


async def _async_get_cic_name(
    hass: HomeAssistant, ip_address: str, retry_on_client_error: bool = False
) -> str:
    """Validate device and return the CIC id/name (system.hostName)."""
    client = QuattCicLocalApiClient(
        ip_address=ip_address,
        session=async_create_clientsession(hass),
    )
    data = await client.async_get_data(retry_on_client_error=retry_on_client_error)
    return data["system"]["hostName"]


def _parse_battery_qr_url(url: str) -> tuple[str, str, str] | None:
    """Parse battery QR URL and return (uuid, serial, check_code) or None.

    Expected: https://app.quatt.io/battery/{uuid}/{serial}/{checkCode}/{macAddress}
    """
    try:
        parsed = urlparse(url.strip())
        if parsed.netloc != "app.quatt.io":
            return None
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) < 4 or parts[0] != "battery":
            return None
        return parts[1], parts[2], parts[3]
    except Exception:  # noqa: BLE001
        return None


# pylint: disable=abstract-method
class QuattFlowHandler(ConfigFlow, domain=DOMAIN):
    """Config flow for Quatt."""

    VERSION = 7

    def __init__(self) -> None:
        """Initialize a Quatt flow."""
        self.ip_address: str | None = None
        self.cic_name: str | None = None
        self.connection_type: str | None = None
        self._after_auth_step: str = _AFTER_AUTH_PAIR_CIC
        self._home_battery_auth_done: bool = False

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
    ) -> ConfigFlowResult:
        """Handle a flow initialized by the user - pick heatpump or home battery."""
        return self.async_show_menu(
            step_id="user",
            menu_options=["local", "home_battery"],
        )

    async def async_step_local(
        self,
        user_input: dict | None = None,
    ) -> ConfigFlowResult:
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
                        # Route through shared auth before the CIC pair step
                        self._after_auth_step = _AFTER_AUTH_PAIR_CIC
                        return await self.async_step_auth()

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

    async def async_step_auth(self, user_input=None) -> ConfigFlowResult:
        """Shared auth step - asks first/last name and runs the signup flow."""
        return await _async_step_auth_common(self, user_input=user_input)

    async def async_step_pair(self, user_input=None) -> ConfigFlowResult:
        """Handle pairing step in the config flow."""
        return await _async_step_pair_common(
            self, config_update=False, user_input=user_input
        )

    async def async_step_home_battery(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Route through auth then show pairing method menu."""
        if not getattr(self, "_home_battery_auth_done", False):
            self._after_auth_step = _AFTER_AUTH_HOME_BATTERY
            self._home_battery_auth_done = True
            return await self.async_step_auth()

        return self.async_show_menu(
            step_id="home_battery",
            menu_options=["home_battery_qr", "home_battery_manual"],
        )

    async def async_step_home_battery_qr(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Pair via QR code URL (single-field step)."""
        await _async_register_static_resources(self.hass)

        _errors: dict[str, str] = {}
        if user_input is not None:
            qr_url = user_input[CONF_HOME_BATTERY_QR_URL].strip()
            parsed = _parse_battery_qr_url(qr_url)
            if parsed is None:
                _errors[CONF_HOME_BATTERY_QR_URL] = "home_battery_qr_invalid"
            else:
                uuid, serial, check_code = parsed
                error = await self._async_pair_home_battery(uuid, serial, check_code)
                if error:
                    _errors["base"] = error
                else:
                    return self.async_create_entry(
                        title=uuid, data={CONF_HOME_BATTERY_SERIAL: serial}
                    )

        return self.async_show_form(
            step_id="home_battery_qr",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOME_BATTERY_QR_URL,
                        default=(user_input or {}).get(CONF_HOME_BATTERY_QR_URL, ""),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.URL)
                    ),
                }
            ),
            errors=_errors,
        )

    async def async_step_home_battery_manual(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Pair by entering UUID / serial / check-code manually."""
        await _async_register_static_resources(self.hass)

        _errors: dict[str, str] = {}
        if user_input is not None:
            uuid = user_input[CONF_HOME_BATTERY_UUID].strip()
            serial = user_input[CONF_HOME_BATTERY_SERIAL].strip()
            check_code = user_input[CONF_HOME_BATTERY_CHECK_CODE].strip()

            error = await self._async_pair_home_battery(uuid, serial, check_code)
            if error:
                _errors["base"] = error
            else:
                return self.async_create_entry(
                    title=uuid, data={CONF_HOME_BATTERY_SERIAL: serial}
                )

        prev = user_input or {}
        return self.async_show_form(
            step_id="home_battery_manual",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOME_BATTERY_UUID,
                        default=prev.get(CONF_HOME_BATTERY_UUID, ""),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                    ),
                    vol.Required(
                        CONF_HOME_BATTERY_SERIAL,
                        default=prev.get(CONF_HOME_BATTERY_SERIAL, ""),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                    ),
                    vol.Required(
                        CONF_HOME_BATTERY_CHECK_CODE,
                        default=prev.get(CONF_HOME_BATTERY_CHECK_CODE, ""),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                    ),
                }
            ),
            errors=_errors,
        )

    async def _async_pair_home_battery(
        self, uuid: str, serial: str, check_code: str
    ) -> str | None:
        """Attempt pairing via the remote API. Returns an error key or None on success."""
        # The access-key UUID (already ``BAT-...`` prefixed) serves as the
        # stable unique id, so the per-hub store key stays uniform with
        # CIC entries: quatt_remote_storage_{unique_id}.
        await self.async_set_unique_id(uuid)
        self._abort_if_unique_id_configured()

        session = async_create_clientsession(self.hass)
        store = Store(
            self.hass,
            STORAGE_VERSION,
            f"{REMOTE_STORAGE_KEY_PREFIX}_{uuid}",
        )
        # Local import to avoid a circular import at module load time.
        from . import _get_or_create_auth_client  # noqa: PLC0415

        auth = await _get_or_create_auth_client(self.hass)
        client = QuattHomeBatteryApiClient(session, store=store, auth=auth)

        success = await client.authenticate_and_pair(
            access_key_uuid=uuid,
            serial_number=serial,
            check_code=check_code,
        )
        return None if success else "home_battery_pair_failed"

    async def async_step_dhcp(
        self, discovery_info: DhcpServiceInfo
    ) -> ConfigFlowResult:
        """Handle DHCP discovery."""
        LOGGER.debug(
            "DHCP discovery detected Quatt CIC (hostname): %s with ip-address: %s",
            discovery_info.hostname,
            discovery_info.ip,
        )

        # Get the status page to validate that we are dealing with a Quatt because
        # the DHCP match is only on "cic-*", if available use the cic-name.
        # On client errors we retry because the CIC could be booting.
        try:
            cic_name = await _async_get_cic_name(
                hass=self.hass, ip_address=discovery_info.ip, retry_on_client_error=True
            )
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

        # Prefer the device-reported name if it's a non-empty string; otherwise fall back to DHCP hostname.
        cic_name_clean = cic_name.strip() if isinstance(cic_name, str) else ""
        preferred_name = cic_name_clean or discovery_info.hostname

        LOGGER.debug(
            "DHCP discovery validated detected Quatt CIC: %s (dhcp hostname: %s) with ip-address: %s",
            cic_name_clean,
            discovery_info.hostname,
            discovery_info.ip,
        )

        # Uppercase the first 3 characters CIC-xxxxxxxx-xxxx-xxxx-xxxxxxxxxxxx
        # This enables the correct match on DHCP hostname (if used)
        preferred_uid = preferred_name
        if len(preferred_uid) >= 3:
            preferred_uid = preferred_uid[:3].upper() + preferred_uid[3:]

        # Loop through existing config entries to check for a match with prefix
        for entry in self.hass.config_entries.async_entries(self.handler):
            entry_uid = entry.unique_id
            if not entry_uid:
                # unique_id is None or "", skip this entry
                continue

            # Hostnames could be shortened by routers so the check is done on a partial match
            # Both directions have to be checked because routers can be switched
            if entry_uid.startswith(preferred_uid) or preferred_uid.startswith(
                entry_uid
            ):
                # Use the found entry unique_id
                await self.async_set_unique_id(entry_uid)
                self.ip_address = discovery_info.ip
                self.cic_name = preferred_name

                if self.is_valid_ip(ip_str=entry.data.get(CONF_LOCAL_CIC, "")):
                    # Configuration is an ip-address, update it
                    LOGGER.debug(
                        "DHCP discovery detected existing Quatt CIC: %s with ip-address: %s, "
                        "updating ip for existing entry",
                        preferred_name,
                        discovery_info.ip,
                    )

                    self._abort_if_unique_id_configured(
                        updates={CONF_LOCAL_CIC: discovery_info.ip},
                    )
                else:
                    self._abort_if_unique_id_configured()

                # Config found so terminate the loop
                return self.async_abort(reason="already_configured")

        # No match found, so this is a new CIC
        await self.async_set_unique_id(preferred_uid)
        self.ip_address = discovery_info.ip
        self.cic_name = preferred_name

        self.context.update({"title_placeholders": {"name": preferred_uid}})
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input=None) -> ConfigFlowResult:
        """Allow the user to confirm adding the device."""
        if user_input is not None:
            if self.cic_name is None or self.ip_address is None:
                return self.async_abort(reason="unknown")

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
        self._after_auth_step: str = _AFTER_AUTH_PAIR_CIC

    async def async_step_init(self, user_input=None) -> ConfigFlowResult:
        """Manage the options."""
        # Home battery entries use a simpler options form
        if (
            CONF_HOME_BATTERY_SERIAL in self.config_entry.data
            and CONF_LOCAL_CIC not in self.config_entry.data
        ):
            return await self._async_step_init_home_battery(user_input)

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
                        # Route through shared auth before the CIC pair step
                        self._after_auth_step = _AFTER_AUTH_PAIR_CIC
                        return await self.async_step_auth()
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

    async def async_step_auth(self, user_input=None) -> ConfigFlowResult:
        """Shared auth step in the options flow."""
        return await _async_step_auth_common(self, user_input=user_input)

    async def async_step_pair(self, user_input=None) -> ConfigFlowResult:
        """Handle pairing step in the options flow."""
        return await _async_step_pair_common(
            self, config_update=True, user_input=user_input
        )

    async def _async_step_init_home_battery(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Options form for a stand-alone home battery hub."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema_dict = {
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
        }
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_dict),
        )
