"""Custom integration to integrate quatt with Home Assistant.

For more details about this integration, please refer to
https://github.com/marcoboers/home-assistant-quatt
"""

from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import (
    async_create_clientsession,
    async_get_clientsession,
)
import homeassistant.helpers.device_registry as dr
import homeassistant.helpers.entity_registry as er
from homeassistant.helpers.storage import Store

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
]


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""
    hass.data.setdefault(DOMAIN, {})

    has_remote = CONF_REMOTE_CIC in entry.data

    coordinators = {
        "local": None,
        "remote": None,
    }

    local_client = QuattLocalApiClient(
        ip_address=entry.data[CONF_LOCAL_CIC],
        session=async_get_clientsession(hass),
    )

    local_coordinator = QuattLocalDataUpdateCoordinator(
        hass=hass,
        update_interval=entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_LOCAL_SCAN_INTERVAL
        ),
        client=local_client,
    )

    await local_coordinator.async_config_entry_first_refresh()
    coordinators["local"] = local_coordinator

    # Set up remote coordinator if configured
    if has_remote:
        cic = entry.data[CONF_REMOTE_CIC]

        # Create storage for tokens
        store = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY}_{entry.entry_id}")

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

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener."""
    await hass.config_entries.async_reload(entry.entry_id)


async def _get_cic_hostname(hass: HomeAssistant, ip_address: str) -> str:
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
        hostname_unique_id = await _get_cic_hostname(
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
    for device_id, device_identifier, is_hub in device_info:
        # Update the device identifiers and via_device_id (if not hub)
        device_reg.async_update_device(
            device_id,
            new_identifiers={
                (DOMAIN, hub_id if is_hub else f"{hub_id}:{device_identifier}")
            },
            via_device_id=None if is_hub else (DOMAIN, hub_id),
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

    return True
