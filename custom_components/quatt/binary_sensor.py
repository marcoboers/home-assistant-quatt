"""Binary sensor platform for quatt."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator_local import QuattLocalDataUpdateCoordinator
from .coordinator_remote import QuattRemoteDataUpdateCoordinator


async def async_setup_entry(hass: HomeAssistant, entry, async_add_devices):
    """Set up the binary_sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    # Route to appropriate binary sensor implementation based on coordinator type
    if isinstance(coordinator, QuattRemoteDataUpdateCoordinator):
        from . import binary_sensor_remote
        return await binary_sensor_remote.async_setup_entry(hass, entry, async_add_devices)

    if isinstance(coordinator, QuattLocalDataUpdateCoordinator):
        from . import binary_sensor_local
        return await binary_sensor_local.async_setup_entry(hass, entry, async_add_devices)
