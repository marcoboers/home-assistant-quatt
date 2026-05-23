"""Pytest fixtures for Quatt tests."""
# pylint: disable=import-error

from __future__ import annotations

from collections.abc import AsyncGenerator
from importlib import import_module
import os
from pathlib import Path
import sys
import types

import pytest
import pytest_asyncio

from homeassistant.core import HomeAssistant

QUATT_PATH = Path(__file__).resolve().parents[1]
CORE_PATH = Path(os.environ.get("HA_CORE_PATH", "/workspaces/core"))
CORE_TESTS_PATH = CORE_PATH / "tests"
if str(QUATT_PATH) not in sys.path:
    sys.path.insert(0, str(QUATT_PATH))
if str(CORE_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_PATH))

core_tests_package = types.ModuleType("tests")
core_tests_package.__path__ = [str(CORE_TESTS_PATH)]
sys.modules["tests"] = core_tests_package

core_tests_common = import_module("tests.common")
MockConfigEntry = core_tests_common.MockConfigEntry
async_test_home_assistant = core_tests_common.async_test_home_assistant


@pytest_asyncio.fixture(name="hass")
async def hass_fixture() -> AsyncGenerator[HomeAssistant]:
    """Return a Home Assistant instance for Quatt tests."""
    async with async_test_home_assistant() as test_hass:
        yield test_hass


@pytest.fixture
def config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Return a Quatt config entry added to Home Assistant."""
    entry = MockConfigEntry(
        domain="quatt",
        unique_id="CIC-12345678",
        data={},
    )
    entry.add_to_hass(hass)
    return entry
