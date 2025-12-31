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
from .api_local import QuattLocalApiClient
from .api_remote import QuattRemoteApiClient
from .const import (
    CARD_FILE,
    CARD_MOUNT,
    CONF_LOCAL_CIC,
    CONF_POWER_SENSOR,
    CONF_REMOTE_CIC,
    DEFAULT_LOCAL_SCAN_INTERVAL,
    DEFAULT_REMOTE_SCAN_INTERVAL,
    DEVICE_CIC_ID,
    DOMAIN,
    LOGGER,
    REMOTE_CONF_SCAN_INTERVAL,
    STORAGE_KEY,
    STORAGE_VERSION,
)
from .coordinator_local import QuattLocalDataUpdateCoordinator
from .coordinator_remote import QuattRemoteDataUpdateCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]


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


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""
    hass.data.setdefault(DOMAIN, {})

    has_remote = CONF_REMOTE_CIC in entry.data

    coordinators: dict[
        str, QuattLocalDataUpdateCoordinator | QuattRemoteDataUpdateCoordinator | None
    ] = {"local": None, "remote": None}

    local_client = QuattLocalApiClient(
        ip_address=entry.data[CONF_LOCAL_CIC],
        session=async_get_clientsession(hass),
    )

    local_coordinator = QuattLocalDataUpdateCoordinator(
        hass=hass,
        update_interval=timedelta(
            seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_LOCAL_SCAN_INTERVAL)
        ),
        client=local_client,
    )

    await local_coordinator.async_config_entry_first_refresh()
    coordinators["local"] = local_coordinator

    # Set up remote coordinator if configured
    if has_remote:
        cic = entry.data[CONF_REMOTE_CIC]

        # Create storage for tokens
        store = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY}_{entry.unique_id}")

        # Load stored tokens
        stored_data = await store.async_load()

        # Create remote API client
        session = async_get_clientsession(hass)
        remote_client = QuattRemoteApiClient(cic, session, store)

        # Load tokens if they exist
        if stored_data:
            remote_client.load_tokens(
                stored_data.get("id_token"),
                stored_data.get("refresh_token"),
                stored_data.get("installation_id"),
            )
            LOGGER.debug("Loaded stored tokens for CIC %s", cic)

        # Authenticate (will use existing tokens if available, or do full auth)
        if await remote_client.authenticate():
            # Create remote coordinator only if authentication succeeded
            remote_coordinator = QuattRemoteDataUpdateCoordinator(
                hass=hass,
                update_interval=timedelta(
                    minutes=entry.options.get(
                        REMOTE_CONF_SCAN_INTERVAL, DEFAULT_REMOTE_SCAN_INTERVAL
                    )
                ),
                client=remote_client,
            )

            await remote_coordinator.async_config_entry_first_refresh()
            coordinators["remote"] = remote_coordinator
        else:
            LOGGER.error("Failed to authenticate with Quatt remote API")

    # Store coordinators
    hass.data[DOMAIN][entry.entry_id] = coordinators

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # On update of the options reload the entry which reloads the coordinator
    entry.async_on_unload(entry.add_update_listener(update_listener))

    # Register services (only once, not per config entry)
    if not hass.services.has_service(DOMAIN, "get_insights"):

        async def handle_get_insights(call: ServiceCall) -> ServiceResponse:
            """Handle the get_insights service call."""
            from_date = call.data.get("from_date")
            timeframe = call.data.get("timeframe", "all")
            advanced_insights = call.data.get("advanced_insights", True)

            # Find a remote coordinator to use for the service call
            remote_coordinator = None
            for coordinators_dict in hass.data[DOMAIN].values():
                if coordinators_dict.get("remote"):
                    remote_coordinator = coordinators_dict["remote"]
                    break

            if not remote_coordinator:
                LOGGER.error("No remote coordinator available for insights service")
                return {
                    "error": "No remote connection available. Please configure remote API access."
                }

            # Get insights data
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
            "get_insights",
            handle_get_insights,
            supports_response=SupportsResponse.ONLY,
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener."""
    await hass.config_entries.async_reload(entry.entry_id)


async def _async_get_cic_name(hass: HomeAssistant, ip_address: str) -> str:
    """Validate credentials."""
    client = QuattLocalApiClient(
        ip_address=ip_address,
        session=async_create_clientsession(hass),
    )
    data = await client.async_get_data()
    return data["system"]["hostName"]


async def _migrate_v1_to_v2(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate v1 entry to v2 entry."""

    # Migrate CONF_POWER_SENSOR from data to options
    # Set the unique_id of the cic
    LOGGER.debug("Migrating config entry from version '%s'", config_entry.version)

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
            hostname_unique_id = hostname_unique_id[:3].upper() + hostname_unique_id[3:]

            new_data = {**config_entry.data}
            new_options = {**config_entry.options}

            if CONF_POWER_SENSOR in new_data:
                # Move the CONF_POWER_SENSOR to the options
                new_options[CONF_POWER_SENSOR] = new_data.pop(CONF_POWER_SENSOR)

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
    LOGGER.debug("Migrating config entry from version '%s'", config_entry.version)

    entity_reg = er.async_get(hass)
    device_reg = dr.async_get(hass)

    # Clear the old Heatpump device from the device registry
    # This should only be one device, but we loop through all devices
    devices = dr.async_entries_for_config_entry(device_reg, config_entry.entry_id)
    for device in devices:
        for entity in er.async_entries_for_device(
            entity_reg, device.id, include_disabled_entities=True
        ):
            if entity.platform == DOMAIN:
                entity_reg.async_update_entity(entity.entity_id, device_id=None)

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
    LOGGER.debug("Migrating config entry from version '%s'", config_entry.version)

    entity_reg = er.async_get(hass)
    device_reg = dr.async_get(hass)

    hub_id = config_entry.unique_id
    if not hub_id:
        LOGGER.error("Cannot migrate v3->v4: config entry unique_id is missing")
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

            sensor_key = entity.unique_id[len(config_entry.entry_id) :]
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
    LOGGER.debug("Migrating config entry from version '%s'", config_entry.version)

    # Update the config entry to version 5
    hass.config_entries.async_update_entry(
        config_entry,
        version=5,
    )

    return True


async def _migrate_v5_to_v6(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate v5 entry to v6 entry."""

    # Migrate remote token storage key from entry_id-based to CIC-based
    LOGGER.debug("Migrating config entry from version '%s'", config_entry.version)

    # We require a unique_id (no fallbacks).
    if not config_entry.unique_id:
        LOGGER.error("Cannot migrate v5->v6: config entry unique_id is missing")
        return False

    # Always bump the entry version, even if no remote is configured
    if CONF_REMOTE_CIC in config_entry.data:
        old_store = Store(
            hass, STORAGE_VERSION, f"{STORAGE_KEY}_{config_entry.entry_id}"
        )
        new_store = Store(
            hass, STORAGE_VERSION, f"{STORAGE_KEY}_{config_entry.unique_id}"
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

    return True
