"""Shared setup logic for Quatt entities."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import replace
import logging
from typing import Any

from homeassistant.core import HomeAssistant
import homeassistant.helpers.device_registry as dr
import homeassistant.helpers.entity_registry as er

from .const import DEVICE_LIST, DOMAIN, QuattDeviceKind
from .coordinator import QuattCicDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


def _chill_unique_id_key(key: str, index: int) -> str:
    """Return a Chill entity key without the response-list index."""
    indexed_chill_key = f"chills.{index}"
    if key == indexed_chill_key:
        return "chills"
    if key.startswith(f"{indexed_chill_key}."):
        return f"chills.{key.removeprefix(f'{indexed_chill_key}.')}"
    return key


def _entity_unique_id_key(entity_description: Any) -> str:
    """Return the entity description key used for the Home Assistant unique ID."""
    return entity_description.quatt_unique_id_key or entity_description.key


def create_chill_entity_descriptions(
    coordinator: QuattCicDataUpdateCoordinator,
    base_entity_descriptions: dict[str, list],
    create_entity_descriptions: Callable[[int], list],
) -> tuple[dict[str, list], dict[str, str], dict[str, QuattDeviceKind]]:
    """Add dynamic Chill entity descriptions to a platform's base descriptions."""
    entity_descriptions = {**base_entity_descriptions}
    device_names: dict[str, str] = {}
    device_kinds: dict[str, QuattDeviceKind] = {}

    chill_list = coordinator.get_value("chills", [])
    if not isinstance(chill_list, list):
        return entity_descriptions, device_names, device_kinds

    for index, chill in enumerate(chill_list):
        if not isinstance(chill, dict) or not (chill_uuid := chill.get("uuid")):
            _LOGGER.error("Cannot set up Chill at index %s: missing UUID", index)
            continue

        device_id = chill_uuid
        entity_descriptions[device_id] = [
            replace(
                entity_description,
                quatt_unique_id_key=_chill_unique_id_key(
                    entity_description.key, index
                ),
            )
            for entity_description in create_entity_descriptions(index)
        ]
        device_names[device_id] = chill.get("name") or f"Chill {index + 1}"
        device_kinds[device_id] = QuattDeviceKind.DEVICE

    return entity_descriptions, device_names, device_kinds


async def async_setup_entities(
    hass: HomeAssistant,
    coordinator: QuattCicDataUpdateCoordinator,
    entry,
    remote: bool,
    entity_descriptions: dict[str, list],
    entity_domain: str,
    device_names: Mapping[str, str] | None = None,
    device_kinds: Mapping[str, QuattDeviceKind] | None = None,
):
    """Set up CIC entities on the given platform.

    Only CIC coordinators are accepted because this helper uses the CIC
    feature-flag methods (``heatpump_1_active``, ``all_electric_active``, ...)
    to decide which entities apply to the installation.
    """
    registry = er.async_get(hass)

    # Cache the active states
    heatpump_1_active = coordinator.heatpump_1_active()
    heatpump_2_active = coordinator.heatpump_2_active()
    all_electric_active = coordinator.all_electric_active()
    is_boiler_opentherm = coordinator.is_boiler_opentherm()

    _LOGGER.debug("Heatpump 1 active: %s", heatpump_1_active)
    _LOGGER.debug("Heatpump 2 active: %s", heatpump_2_active)
    _LOGGER.debug("All electric active: %s", all_electric_active)
    _LOGGER.debug("boiler OpenTherm: %s", is_boiler_opentherm)

    # Create only those entities that make sense for this installation type.
    # Remove entities that are not applicable based on the configuration.
    # This can occur when the configuration changes, e.g., from hybrid or duo to all-electric.
    device_reg = dr.async_get(hass)
    devices = dr.async_entries_for_config_entry(device_reg, entry.entry_id)
    device_ids = {dev.id for dev in devices}

    # Determine which entities to create based on the detected configuration
    flag_conditions = [
        ("hybrid", not all_electric_active),
        ("all_electric", all_electric_active),
        ("duo", heatpump_2_active),
        ("opentherm", is_boiler_opentherm),
    ]

    # Flatten out all entity descriptions
    flat_descriptions = [
        entity_description
        for device_entities in entity_descriptions.values()
        for entity_description in device_entities
    ]

    # Determine which entities to create based on the flags
    entity_keys: dict[str, bool] = {}
    for desc in flat_descriptions:
        features = desc.quatt_features

        # Check if it matches normal feature conditions
        if not any(getattr(features, flag) for flag, _ in flag_conditions) or all(
            condition for flag, condition in flag_conditions if getattr(features, flag)
        ):
            # Include the entity and the mobile API status
            entity_keys[desc.key] = features.mobile_api

    hub_id = (entry.unique_id or entry.entry_id).strip()
    expected_unique_ids = {
        f"{hub_id}:{device_id}:{_entity_unique_id_key(entity_description)}"
        for device_id, device_entity_descriptions in entity_descriptions.items()
        for entity_description in device_entity_descriptions
        if entity_description.key in entity_keys
    }
    expected_unique_id_prefixes = {
        f"{hub_id}:{device_id}:" for device_id in entity_descriptions
    }

    # Remove not applicable entities
    for dev_id in device_ids:
        for entry_reg in er.async_entries_for_device(
            registry, dev_id, include_disabled_entities=True
        ):
            if (
                entry_reg.config_entry_id == entry.entry_id
                and entry_reg.domain == entity_domain
                and entry_reg.platform == DOMAIN
                and entry_reg.unique_id not in expected_unique_ids
                and (
                    any(
                        entry_reg.unique_id.startswith(prefix)
                        for prefix in expected_unique_id_prefixes
                    )
                    or (
                        remote
                        and (
                            ":chills." in entry_reg.unique_id
                            or entry_reg.unique_id.endswith(":chills")
                        )
                    )
                )
            ):
                _LOGGER.info(
                    "[%s] Removing obsolete entity: %s (%s)",
                    entity_domain,
                    entry_reg.entity_id,
                    entry_reg.unique_id,
                )
                registry.async_remove(entry_reg.entity_id)

        # Remove the device in case it has no remaining entities
        if not any(er.async_entries_for_device(registry, dev_id)):
            # Do not remove the hub device
            dev = device_reg.async_get(dev_id)
            if dev and (DOMAIN, hub_id) in dev.identifiers:
                continue
            _LOGGER.info(
                "[%s] Removing obsolete device: %s (identifiers=%s)",
                entity_domain,
                (dev.name if dev else None) or dev_id,
                dev.identifiers if dev else "unknown",
            )
            device_reg.async_remove_device(dev_id)

    # Create entities based on the filtered entity keys
    device_name_map = {d["id"]: d["name"] for d in DEVICE_LIST}
    if device_names is not None:
        device_name_map.update(device_names)

    device_kind_map = {d["id"]: d["kind"] for d in DEVICE_LIST}
    if device_kinds is not None:
        device_kind_map.update(device_kinds)

    entities: list = []
    for device_id, device_entity_descriptions in entity_descriptions.items():
        device_kind = device_kind_map.get(device_id, QuattDeviceKind.DEVICE)
        for entity_description in device_entity_descriptions:
            # Skip entities that are not selected based on the installation type
            if entity_description.key not in entity_keys:
                continue

            # Skip entities that do not match the remote indicator
            if entity_keys[entity_description.key] != remote:
                continue

            entities.append(
                entity_description.quatt_entity_class(
                    device_name=device_name_map.get(device_id, device_id),
                    device_id=device_id,
                    sensor_key=entity_description.key,
                    coordinator=coordinator,
                    entity_description=entity_description,
                    device_kind=device_kind,
                )
            )

    return entities
