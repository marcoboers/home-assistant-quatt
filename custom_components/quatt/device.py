"""Device registry compatibility helpers for Quatt."""

from typing import cast

from homeassistant.const import MAJOR_VERSION, MINOR_VERSION
from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN


def hub_link_info(hub_identifier: str, hub_device_id: str) -> DeviceInfo:
    """Return the hub link supported by this Home Assistant version."""
    if (MAJOR_VERSION, MINOR_VERSION) >= (2026, 8):
        return DeviceInfo(via_device_id=hub_device_id)

    return cast(DeviceInfo, {"via_device": (DOMAIN, hub_identifier)})


@callback
def async_get_device_by_identifier(
    registry: dr.DeviceRegistry,
    identifier: tuple[str, str],
    config_entry_id: str,
) -> dr.DeviceEntry | None:
    """Look up a device within its config entry across supported HA versions."""
    if (MAJOR_VERSION, MINOR_VERSION) >= (2026, 8):
        return registry.async_get_device_by_identifier(identifier, config_entry_id)

    return next(
        (
            device
            for device in dr.async_entries_for_config_entry(registry, config_entry_id)
            if identifier in device.identifiers
        ),
        None,
    )
