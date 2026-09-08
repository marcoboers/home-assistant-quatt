"""Device registry compatibility helpers for Quatt."""

from typing import cast

from homeassistant.const import MAJOR_VERSION, MINOR_VERSION
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN


def hub_link_info(hub_identifier: str, hub_device_id: str) -> DeviceInfo:
    """Return the hub link supported by this Home Assistant version."""
    if (MAJOR_VERSION, MINOR_VERSION) >= (2026, 8):
        return DeviceInfo(via_device_id=hub_device_id)

    return cast(DeviceInfo, {"via_device": (DOMAIN, hub_identifier)})
