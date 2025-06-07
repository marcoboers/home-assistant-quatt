"""Custom integration to integrate quatt with Home Assistant.

For more details about this integration, please refer to
https://github.com/marcoboers/home-assistant-quatt
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_IP_ADDRESS, CONF_SCAN_INTERVAL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import (
    async_create_clientsession,
    async_get_clientsession,
)
import homeassistant.helpers.device_registry as dr
import homeassistant.helpers.entity_registry as er

from .api import (
    QuattApiClient,
    QuattApiClientAuthenticationError,
    QuattApiClientCommunicationError,
    QuattApiClientError,
)
from .const import CONF_POWER_SENSOR, DEFAULT_SCAN_INTERVAL, DOMAIN, LOGGER
from .coordinator import QuattDataUpdateCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
]


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator = QuattDataUpdateCoordinator(
        hass=hass,
        update_interval=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        client=QuattApiClient(
            ip_address=entry.data[CONF_IP_ADDRESS],
            session=async_get_clientsession(hass),
        ),
    )
    # https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
    await coordinator.async_config_entry_first_refresh()

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
    client = QuattApiClient(
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
            hass=hass, ip_address=config_entry.data[CONF_IP_ADDRESS]
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


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""

    if config_entry.version == 1:
        if not await _migrate_v1_to_v2(hass, config_entry):
            return False

    if config_entry.version == 2:
        if not await _migrate_v2_to_v3(hass, config_entry):
            return False

    return True
