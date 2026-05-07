"""Custom integration to integrate quatt with Home Assistant.

For more details about this integration, please refer to
https://github.com/marcoboers/home-assistant-quatt
"""

from __future__ import annotations

from datetime import timedelta

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL, Platform
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.helpers.aiohttp_client import (
    async_create_clientsession,
    async_get_clientsession,
)
import homeassistant.helpers.device_registry as dr
import homeassistant.helpers.entity_registry as er
from homeassistant.helpers.storage import Store
from homeassistant.loader import async_get_integration

from .api import (
    QuattApiClientAuthenticationError,
    QuattApiClientCommunicationError,
    QuattApiClientError,
)
from .api_local_cic import QuattCicLocalApiClient
from .api_remote_auth import QuattRemoteAuthClient
from .api_remote_cic import QuattCicRemoteApiClient
from .api_remote_home_battery import QuattHomeBatteryApiClient
from .const import (
    CARD_FILE,
    CARD_MOUNT,
    CONF_HOME_BATTERY_SERIAL,
    CONF_LOCAL_CIC,
    CONF_POWER_SENSOR,
    CONF_REMOTE_CIC,
    DEFAULT_LOCAL_SCAN_INTERVAL,
    DEFAULT_REMOTE_SCAN_INTERVAL,
    DEVICE_CIC_ID,
    DOMAIN,
    LOGGER,
    REMOTE_AUTH_STORAGE_KEY,
    REMOTE_CONF_SCAN_INTERVAL,
    REMOTE_STORAGE_KEY_PREFIX,
    STORAGE_VERSION,
)
from .coordinator_home_battery import QuattHomeBatteryDataUpdateCoordinator
from .coordinator_local_cic import QuattCicLocalDataUpdateCoordinator
from .coordinator_remote_cic import QuattCicRemoteDataUpdateCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

# Per-hub stores are always keyed as ``quatt_remote_storage_{unique_id}``.
# CIC unique_ids carry a ``CIC-`` prefix (hostname); battery unique_ids carry
# a ``BAT-`` prefix (access-key UUID). Auth tokens live under the ``AUTH``
# suffix in the same namespace.
_AUTH_CLIENT_DATA_KEY = "_remote_auth_client"


async def _get_or_create_auth_client(
    hass: HomeAssistant,
) -> QuattRemoteAuthClient:
    """Return the singleton remote-auth client, creating it on first use.

    A single in-memory client guarantees that refresh-token rotations are
    serialized across every CIC and battery coordinator.
    """
    domain_data = hass.data.setdefault(DOMAIN, {})
    existing = domain_data.get(_AUTH_CLIENT_DATA_KEY)
    if isinstance(existing, QuattRemoteAuthClient):
        return existing

    auth_store = Store(hass, STORAGE_VERSION, REMOTE_AUTH_STORAGE_KEY)
    stored = await auth_store.async_load() or {}
    auth_client = QuattRemoteAuthClient(
        async_get_clientsession(hass), store=auth_store
    )
    auth_client.load_tokens(
        stored.get("id_token"), stored.get("refresh_token")
    )
    auth_client.load_profile(
        stored.get("first_name"), stored.get("last_name")
    )
    domain_data[_AUTH_CLIENT_DATA_KEY] = auth_client
    return auth_client


async def async_setup(hass: HomeAssistant, _config):
    """Set up this integration."""

    # Generic mount with cache enabled
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                CARD_MOUNT,
                hass.config.path("custom_components/quatt/www"),
                cache_headers=True,
            )
        ]
    )
    # More specific mount for JS with cache disabled
    # This ensures that updated JS files are always loaded (companion app)
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                f"{CARD_MOUNT}/js",
                hass.config.path("custom_components/quatt/www/js"),
                cache_headers=False,
            )
        ]
    )

    # Determine the version of the integration
    integration = await async_get_integration(hass, DOMAIN)
    version = integration.version or "0"

    # Register the frontend card
    add_extra_js_url(hass, f"{CARD_MOUNT}/js/{CARD_FILE}?v={version}")
    return True


def _register_services(hass: HomeAssistant) -> None:
    """Register integration services if not already registered."""

    if not hass.services.has_service(DOMAIN, "get_cic_insights"):

        async def handle_get_cic_insights(call: ServiceCall) -> ServiceResponse:
            """Handle the get_cic_insights service call."""
            from_date = call.data.get("from_date")
            timeframe = call.data.get("timeframe", "all")
            advanced_insights = call.data.get("advanced_insights", True)

            remote_coordinator = None
            for coordinators_dict in hass.data[DOMAIN].values():
                if not isinstance(coordinators_dict, dict):
                    continue
                if coordinators_dict.get("cic_remote"):
                    remote_coordinator = coordinators_dict["cic_remote"]
                    break

            if not remote_coordinator:
                LOGGER.error(
                    "No remote coordinator available for insights service")
                return {
                    "error": "No remote connection available. Please configure remote API access."
                }

            insights_data = await remote_coordinator.client.get_insights(
                from_date=from_date,
                timeframe=timeframe,
                advanced_insights=advanced_insights,
            )

            if insights_data:
                return insights_data
            return {"error": "Failed to fetch insights data"}

        hass.services.async_register(
            DOMAIN,
            "get_cic_insights",
            handle_get_cic_insights,
            supports_response=SupportsResponse.ONLY,
        )

    if not hass.services.has_service(DOMAIN, "get_home_battery_insights"):

        async def handle_get_home_battery_insights(
            call: ServiceCall,
        ) -> ServiceResponse:
            """Handle the get_home_battery_insights service call."""
            year = call.data.get("year")
            month = call.data.get("month")
            day = call.data.get("day")

            home_battery_coordinator = None
            for coordinators_dict in hass.data[DOMAIN].values():
                if not isinstance(coordinators_dict, dict):
                    continue
                if coordinators_dict.get("home_battery"):
                    home_battery_coordinator = coordinators_dict["home_battery"]
                    break

            if not home_battery_coordinator:
                LOGGER.error(
                    "No home battery coordinator available for insights service"
                )
                return {
                    "error": "No home battery configured. Pair a Quatt home battery first."
                }

            insights_data = (
                await home_battery_coordinator.client.get_home_battery_insights(
                    year=year,
                    month=month,
                    day=day,
                )
            )

            if insights_data:
                return insights_data
            return {"error": "Failed to fetch home battery insights data"}

        hass.services.async_register(
            DOMAIN,
            "get_home_battery_insights",
            handle_get_home_battery_insights,
            supports_response=SupportsResponse.ONLY,
        )

    if not hass.services.has_service(DOMAIN, "get_home_battery_energy_flow"):

        async def handle_get_home_battery_energy_flow(
            call: ServiceCall,
        ) -> ServiceResponse:
            """Handle the get_home_battery_energy_flow service call."""
            year = call.data.get("year")
            month = call.data.get("month")
            day = call.data.get("day")

            home_battery_coordinator = None
            for coordinators_dict in hass.data[DOMAIN].values():
                if not isinstance(coordinators_dict, dict):
                    continue
                if coordinators_dict.get("home_battery"):
                    home_battery_coordinator = coordinators_dict["home_battery"]
                    break

            if not home_battery_coordinator:
                LOGGER.error(
                    "No home battery coordinator available for energy flow service"
                )
                return {
                    "error": "No home battery configured. Pair a Quatt home battery first."
                }

            flow_data = await home_battery_coordinator.client.get_energy_flow(
                year=year,
                month=month,
                day=day,
            )

            if flow_data:
                return flow_data
            return {"error": "Failed to fetch energy flow data"}

        hass.services.async_register(
            DOMAIN,
            "get_home_battery_energy_flow",
            handle_get_home_battery_energy_flow,
            supports_response=SupportsResponse.ONLY,
        )

    if not hass.services.has_service(DOMAIN, "get_home_battery_savings"):

        async def handle_get_home_battery_savings(
            call: ServiceCall,
        ) -> ServiceResponse:
            """Handle the get_home_battery_savings service call."""
            year = call.data.get("year")
            month = call.data.get("month")

            home_battery_coordinator = None
            for coordinators_dict in hass.data[DOMAIN].values():
                if not isinstance(coordinators_dict, dict):
                    continue
                if coordinators_dict.get("home_battery"):
                    home_battery_coordinator = coordinators_dict["home_battery"]
                    break

            if not home_battery_coordinator:
                LOGGER.error(
                    "No home battery coordinator available for savings service"
                )
                return {
                    "error": "No home battery configured. Pair a Quatt home battery first."
                }

            savings_data = await home_battery_coordinator.client.get_savings(
                year=year,
                month=month,
            )

            if savings_data:
                return savings_data
            return {"error": "Failed to fetch savings data"}

        hass.services.async_register(
            DOMAIN,
            "get_home_battery_savings",
            handle_get_home_battery_savings,
            supports_response=SupportsResponse.ONLY,
        )


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""
    hass.data.setdefault(DOMAIN, {})

    is_home_battery_hub = (
        CONF_HOME_BATTERY_SERIAL in entry.data and CONF_LOCAL_CIC not in entry.data
    )
    has_remote = CONF_REMOTE_CIC in entry.data

    coordinators: dict[
        str,
        QuattCicLocalDataUpdateCoordinator
        | QuattCicRemoteDataUpdateCoordinator
        | QuattHomeBatteryDataUpdateCoordinator
        | None,
    ] = {"cic_local": None, "cic_remote": None, "home_battery": None}

    if is_home_battery_hub:
        # Home battery only hub - no local CIC, only the remote home battery API.
        # Battery unique_id is the access-key UUID (already prefixed BAT-).
        store = Store(
            hass,
            STORAGE_VERSION,
            f"{REMOTE_STORAGE_KEY_PREFIX}_{entry.unique_id}",
        )
        stored_data = await store.async_load() or {}
        session = async_get_clientsession(hass)
        auth_client = await _get_or_create_auth_client(hass)
        home_battery_client = QuattHomeBatteryApiClient(
            session, store=store, auth=auth_client
        )
        home_battery_client.load_installation_id(
            stored_data.get("installation_id")
        )

        home_battery_coordinator = QuattHomeBatteryDataUpdateCoordinator(
            hass=hass,
            update_interval=timedelta(
                minutes=entry.options.get(
                    REMOTE_CONF_SCAN_INTERVAL, DEFAULT_REMOTE_SCAN_INTERVAL
                )
            ),
            client=home_battery_client,
        )
        await home_battery_coordinator.async_config_entry_first_refresh()
        coordinators["home_battery"] = home_battery_coordinator
    else:
        local_client = QuattCicLocalApiClient(
            ip_address=entry.data[CONF_LOCAL_CIC],
            session=async_get_clientsession(hass),
        )

        local_coordinator = QuattCicLocalDataUpdateCoordinator(
            hass=hass,
            update_interval=timedelta(
                seconds=entry.options.get(
                    CONF_SCAN_INTERVAL, DEFAULT_LOCAL_SCAN_INTERVAL
                )
            ),
            client=local_client,
        )

        await local_coordinator.async_config_entry_first_refresh()
        coordinators["cic_local"] = local_coordinator

        # Set up remote coordinator if configured
        if has_remote:
            cic = entry.data[CONF_REMOTE_CIC]

            # Per-CIC store now only holds installation_id - auth tokens live
            # in the shared REMOTE_AUTH_STORAGE_KEY store.
            store = Store(
                hass,
                STORAGE_VERSION,
                f"{REMOTE_STORAGE_KEY_PREFIX}_{entry.unique_id}",
            )
            stored_data = await store.async_load() or {}

            session = async_get_clientsession(hass)
            auth_client = await _get_or_create_auth_client(hass)
            remote_client = QuattCicRemoteApiClient(
                cic, session, store=store, auth=auth_client
            )
            remote_client.load_installation_id(
                stored_data.get("installation_id"))
            if stored_data.get("installation_id"):
                LOGGER.debug("Loaded stored installation id for CIC %s", cic)

            # Authenticate (will use existing tokens if available, or do full auth)
            if await remote_client.authenticate():
                # Create remote coordinator only if authentication succeeded
                remote_coordinator = QuattCicRemoteDataUpdateCoordinator(
                    hass=hass,
                    update_interval=timedelta(
                        minutes=entry.options.get(
                            REMOTE_CONF_SCAN_INTERVAL, DEFAULT_REMOTE_SCAN_INTERVAL
                        )
                    ),
                    client=remote_client,
                )

                await remote_coordinator.async_config_entry_first_refresh()
                coordinators["cic_remote"] = remote_coordinator
            else:
                LOGGER.error("Failed to authenticate with Quatt remote API")

    # Store coordinators
    hass.data[DOMAIN][entry.entry_id] = coordinators

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # On update of the options reload the entry which reloads the coordinator
    entry.async_on_unload(entry.add_update_listener(update_listener))

    # Register services (only once, not per config entry)
    _register_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded


def _entry_uses_remote_auth(entry: ConfigEntry) -> bool:
    """Return True if the entry talks to the Quatt mobile API."""
    is_home_battery = (
        CONF_HOME_BATTERY_SERIAL in entry.data and CONF_LOCAL_CIC not in entry.data
    )
    return is_home_battery or CONF_REMOTE_CIC in entry.data


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Clean up per-hub storage (and shared auth when the last remote hub leaves)."""
    if entry.unique_id and _entry_uses_remote_auth(entry):
        hub_store = Store(
            hass,
            STORAGE_VERSION,
            f"{REMOTE_STORAGE_KEY_PREFIX}_{entry.unique_id}",
        )
        await hub_store.async_remove()

    remaining_needs_auth = any(
        other.entry_id != entry.entry_id and _entry_uses_remote_auth(other)
        for other in hass.config_entries.async_entries(DOMAIN)
    )
    if not remaining_needs_auth:
        auth_store = Store(hass, STORAGE_VERSION, REMOTE_AUTH_STORAGE_KEY)
        await auth_store.async_remove()
        hass.data.get(DOMAIN, {}).pop(_AUTH_CLIENT_DATA_KEY, None)


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener."""
    await hass.config_entries.async_reload(entry.entry_id)


async def _async_get_cic_name(hass: HomeAssistant, ip_address: str) -> str:
    """Validate credentials."""
    client = QuattCicLocalApiClient(
        ip_address=ip_address,
        session=async_create_clientsession(hass),
    )
    data = await client.async_get_data()
    return data["system"]["hostName"]


async def _migrate_v1_to_v2(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate v1 entry to v2 entry."""

    # Migrate CONF_POWER_SENSOR from data to options
    # Set the unique_id of the cic
    LOGGER.debug("Migrating config entry from version '%s'",
                 config_entry.version)

    # The old version does not have a unique_id so we get the CIC hostname and set it
    # Return that the migration failed in case the retrieval fails
    try:
        hostname_unique_id = await _async_get_cic_name(
            hass=hass, ip_address=config_entry.data[CONF_LOCAL_CIC]
        )
    except QuattApiClientAuthenticationError as exception:
        LOGGER.warning(exception)
        return False
    except QuattApiClientCommunicationError as exception:
        LOGGER.error(exception)
        return False
    except QuattApiClientError as exception:
        LOGGER.exception(exception)
        return False
    else:
        # Validate that the hostname is found
        if (hostname_unique_id is not None) and (len(hostname_unique_id) >= 3):
            # Uppercase the first 3 characters CIC-xxxxxxxx-xxxx-xxxx-xxxxxxxxxxxx
            # This enables the correct match on DHCP hostname
            hostname_unique_id = hostname_unique_id[:3].upper(
            ) + hostname_unique_id[3:]

            new_data = {**config_entry.data}
            new_options = {**config_entry.options}

            if CONF_POWER_SENSOR in new_data:
                # Move the CONF_POWER_SENSOR to the options
                new_options[CONF_POWER_SENSOR] = new_data.pop(
                    CONF_POWER_SENSOR)

            # Update the config entry to version 2
            hass.config_entries.async_update_entry(
                config_entry,
                data=new_data,
                options=new_options,
                unique_id=hostname_unique_id,
                version=2,
            )
        else:
            return False

    return True


async def _migrate_v2_to_v3(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate v2 entry to v3 entry."""

    # Remove the generic Heatpump device from the config entry data
    # Sensors are now created for the actual devices present in the system
    LOGGER.debug("Migrating config entry from version '%s'",
                 config_entry.version)

    entity_reg = er.async_get(hass)
    device_reg = dr.async_get(hass)

    # Clear the old Heatpump device from the device registry
    # This should only be one device, but we loop through all devices
    devices = dr.async_entries_for_config_entry(
        device_reg, config_entry.entry_id)
    for device in devices:
        for entity in er.async_entries_for_device(
            entity_reg, device.id, include_disabled_entities=True
        ):
            if entity.platform == DOMAIN:
                entity_reg.async_update_entity(
                    entity.entity_id, device_id=None)

        # Remove the empty device
        device_reg.async_remove_device(device.id)

    # Update the config entry to version 3
    hass.config_entries.async_update_entry(
        config_entry,
        version=3,
    )

    return True


async def _migrate_v3_to_v4(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate v3 entry to v4 entry."""

    # Migration to hub/child layout + new unique_id format.
    # Old entity.unique_id:   entry.entry_id + sensor_key
    # New entity.unique_id:   f"{hub_id}:{device_identifier}:{sensor_key}"
    # Hub device:             (DOMAIN, hub_id)
    # Child device:           (DOMAIN, f"{hub_id}:{device_identifier}") via hub

    # include hub_id in device identifiers and entity unique_ids."
    LOGGER.debug("Migrating config entry from version '%s'",
                 config_entry.version)

    entity_reg = er.async_get(hass)
    device_reg = dr.async_get(hass)

    hub_id = config_entry.unique_id
    if not hub_id:
        LOGGER.error(
            "Cannot migrate v3->v4: config entry unique_id is missing")
        return False

    # Get the information about the devices for this config entry
    device_info: list[tuple[str, str, bool]] = []
    for device in dr.async_entries_for_config_entry(device_reg, config_entry.entry_id):
        # Check if this is the hub device or a child device
        if (DOMAIN, DEVICE_CIC_ID) in device.identifiers or (
            DOMAIN,
            hub_id,
        ) in device.identifiers:
            device_info.append((device.id, DEVICE_CIC_ID, True))
        else:
            device_identifier = next(iter(device.identifiers))[1]
            device_info.append((device.id, device_identifier, False))

    # Ensure hub comes first so via_device references a valid parent, sort on is_hub
    device_info.sort(key=lambda device_entry: 0 if device_entry[2] else 1)

    # Update devices and entities
    hub_device_id: str | None = None
    for device_id, device_identifier, is_hub in device_info:
        # Device_info is sorted so hub is first
        if is_hub:
            hub_device_id = device_id

        # Update the device identifiers and via_device_id (if not hub)
        device_reg.async_update_device(
            device_id,
            new_identifiers={
                (DOMAIN, hub_id if is_hub else f"{hub_id}:{device_identifier}")
            },
            via_device_id=None if is_hub else hub_device_id,
        )

        # Rewrite unique_ids for entities on this device: hub_id:<device_identifier>:<sensor_key>
        for entity in er.async_entries_for_device(
            entity_reg, device_id, include_disabled_entities=True
        ):
            # Checks are needed to avoid changing entities that are not part of this integration
            # or that have already been migrated.
            if (
                entity.config_entry_id != config_entry.entry_id
                or entity.platform != DOMAIN
            ):
                continue
            if entity.unique_id.startswith(f"{hub_id}:"):
                continue
            if not entity.unique_id.startswith(config_entry.entry_id):
                continue

            sensor_key = entity.unique_id[len(config_entry.entry_id):]
            entity_reg.async_update_entity(
                entity.entity_id,
                new_unique_id=f"{hub_id}:{device_identifier}:{sensor_key}",
            )

    # Update the config entry to version 4
    hass.config_entries.async_update_entry(
        config_entry,
        version=4,
    )

    return True


async def _migrate_v4_to_v5(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate v4 entry to v5 entry."""

    # No data changes, just bump the version
    LOGGER.debug("Migrating config entry from version '%s'",
                 config_entry.version)

    # Update the config entry to version 5
    hass.config_entries.async_update_entry(
        config_entry,
        version=5,
    )

    return True


async def _migrate_v5_to_v6(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate v5 entry to v6 entry."""

    # Migrate remote token storage key from entry_id-based to CIC-based
    LOGGER.debug("Migrating config entry from version '%s'",
                 config_entry.version)

    # We require a unique_id (no fallbacks).
    if not config_entry.unique_id:
        LOGGER.error(
            "Cannot migrate v5->v6: config entry unique_id is missing")
        return False

    # Always bump the entry version, even if no remote is configured
    if CONF_REMOTE_CIC in config_entry.data:
        old_store = Store(
            hass, STORAGE_VERSION, f"{REMOTE_STORAGE_KEY_PREFIX}_{config_entry.entry_id}"
        )
        new_store = Store(
            hass, STORAGE_VERSION, f"{REMOTE_STORAGE_KEY_PREFIX}_{config_entry.unique_id}"
        )

        new_data = await new_store.async_load()
        if not new_data:
            old_data = await old_store.async_load()
            if old_data:
                await new_store.async_save(old_data)
                LOGGER.debug(
                    "Migrated remote tokens from legacy store to unique_id store (%s)",
                    config_entry.unique_id,
                )

    # Update the config entry to version 6
    hass.config_entries.async_update_entry(
        config_entry,
        version=6,
    )

    return True


async def _migrate_v6_to_v7(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate v6 entry to v7 entry.

    Split the per-hub token+id stores into:
      - one shared auth store (REMOTE_AUTH_STORAGE_KEY) with id_token/refresh_token
      - per-hub stores holding only installation_id
    """
    LOGGER.debug("Migrating config entry from version '%s'",
                 config_entry.version)

    if not config_entry.unique_id:
        LOGGER.error(
            "Cannot migrate v6->v7: config entry unique_id is missing")
        return False

    auth_store = Store(hass, STORAGE_VERSION, REMOTE_AUTH_STORAGE_KEY)

    async def _promote_auth_tokens(source: dict) -> None:
        """Copy tokens into the shared auth store if it's still empty."""
        id_token = source.get("id_token")
        refresh_token = source.get("refresh_token")
        if not id_token or not refresh_token:
            return
        existing = await auth_store.async_load() or {}
        if existing.get("id_token") and existing.get("refresh_token"):
            return
        await auth_store.async_save(
            {"id_token": id_token, "refresh_token": refresh_token}
        )

    if CONF_REMOTE_CIC in config_entry.data:
        # CIC store already uses the REMOTE_STORAGE_KEY_PREFIX + unique_id
        # layout; we only need to strip tokens out of it.
        store = Store(
            hass,
            STORAGE_VERSION,
            f"{REMOTE_STORAGE_KEY_PREFIX}_{config_entry.unique_id}",
        )
        data = await store.async_load() or {}
        await _promote_auth_tokens(data)
        new_payload = {}
        if data.get("installation_id"):
            new_payload["installation_id"] = data["installation_id"]
        await store.async_save(new_payload)

    hass.config_entries.async_update_entry(config_entry, version=7)
    return True


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""

    if config_entry.version == 1:
        if not await _migrate_v1_to_v2(hass, config_entry):
            return False

    if config_entry.version == 2:
        if not await _migrate_v2_to_v3(hass, config_entry):
            return False

    if config_entry.version == 3:
        if not await _migrate_v3_to_v4(hass, config_entry):
            return False

    if config_entry.version == 4:
        if not await _migrate_v4_to_v5(hass, config_entry):
            return False

    if config_entry.version == 5:
        if not await _migrate_v5_to_v6(hass, config_entry):
            return False

    if config_entry.version == 6:
        if not await _migrate_v6_to_v7(hass, config_entry):
            return False

    return True
