"""Constants for quatt."""

from logging import Logger, getLogger
from typing import Final

LOGGER: Logger = getLogger(__package__)

NAME = "Quatt"
DOMAIN = "quatt"
VERSION = "0.1.0"
ATTRIBUTION = "marcoboers"

CONF_POWER_SENSOR = "power_sensor"

# Defaults
DEFAULT_SCAN_INTERVAL: Final = 10
MIN_SCAN_INTERVAL: Final = 5
MAX_SCAN_INTERVAL: Final = 600
