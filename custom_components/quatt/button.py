"""Button platform for quatt."""

from __future__ import annotations

from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN
from homeassistant.core import HomeAssistant

from .const import (
    DEVICE_BOILER_ID,
    DEVICE_CIC_ID,
    DEVICE_FLOWMETER_ID,
    DEVICE_HEAT_BATTERY_ID,
    DEVICE_HEAT_CHARGER_ID,
    DEVICE_HEATPUMP_1_ID,
    DEVICE_HEATPUMP_2_ID,
    DEVICE_THERMOSTAT_ID,
    DOMAIN,
)
from .coordinator import QuattDataUpdateCoordinator
from .entity import (
    QuattButton,
    QuattButtonEntityDescription,
    QuattFeatureFlags,
)
from .entity_button import QuattNightWindowResetButton
from .entity_setup import async_setup_entities

BUTTONS = {
    # The HUB CIC sensor must be created first to ensure the HUB device is present
    DEVICE_CIC_ID: [
        QuattButtonEntityDescription(
            key="nightWindowReset",
            name="Reset night time window",
            icon="mdi:restore",
            quatt_features=QuattFeatureFlags(
                mobile_api=True,
            ),
            quatt_entity_class=QuattNightWindowResetButton,
        ),
    ],
    DEVICE_HEAT_BATTERY_ID: [],
    DEVICE_HEAT_CHARGER_ID: [],
    DEVICE_HEATPUMP_1_ID: [],
    DEVICE_HEATPUMP_2_ID: [],
    DEVICE_BOILER_ID: [],
    DEVICE_FLOWMETER_ID: [],
    DEVICE_THERMOSTAT_ID: [],
}


async def async_setup_entry(hass: HomeAssistant, entry, async_add_devices):
    """Set up the button platform."""
    coordinators = hass.data[DOMAIN][entry.entry_id]

    local_coordinator: QuattDataUpdateCoordinator | None = coordinators.get("cic_local")
    remote_coordinator: QuattDataUpdateCoordinator | None = coordinators.get(
        "cic_remote"
    )

    buttons: list[QuattButton] = []
    if local_coordinator is not None:
        buttons += await async_setup_entities(
            hass=hass,
            coordinator=local_coordinator,
            entry=entry,
            remote=False,
            entity_descriptions=BUTTONS,
            entity_domain=BUTTON_DOMAIN,
        )

    if remote_coordinator:
        buttons += await async_setup_entities(
            hass=hass,
            coordinator=remote_coordinator,
            entry=entry,
            remote=True,
            entity_descriptions=BUTTONS,
            entity_domain=BUTTON_DOMAIN,
        )

    async_add_devices(buttons)
