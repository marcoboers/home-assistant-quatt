"""Sensor platform for quatt."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator_local import QuattLocalDataUpdateCoordinator
from .coordinator_remote import QuattRemoteDataUpdateCoordinator


async def async_setup_entry(hass: HomeAssistant, entry, async_add_devices):
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    # Route to appropriate sensor implementation based on coordinator type
    if isinstance(coordinator, QuattRemoteDataUpdateCoordinator):
        from . import sensor_remote
        return await sensor_remote.async_setup_entry(hass, entry, async_add_devices)

    if isinstance(coordinator, QuattLocalDataUpdateCoordinator):
        from . import sensor_local
        return await sensor_local.async_setup_entry(hass, entry, async_add_devices)
