"""Constants for quatt."""

from enum import IntEnum
from logging import Logger, getLogger
from typing import Final

LOGGER: Logger = getLogger(__package__)

NAME = "Quatt"
DOMAIN = "quatt"
ATTRIBUTION = "marcoboers"

CONF_POWER_SENSOR = "power_sensor"

# Device IDs
DEVICE_BOILER_ID = "boiler"
DEVICE_CIC_ID = "cic"
DEVICE_FLOWMETER_ID = "flowmeter"
DEVICE_HEAT_CHARGER_ID = "heat_charger"
DEVICE_HEATPUMP_1_ID = "heatpump_1"
DEVICE_HEATPUMP_2_ID = "heatpump_2"
DEVICE_THERMOSTAT_ID = "thermostat"

DEVICE_LIST = [
    {"name": "Boiler", "id": DEVICE_BOILER_ID},
    {"name": "CIC", "id": DEVICE_CIC_ID},
    {"name": "Flowmeter", "id": DEVICE_FLOWMETER_ID},
    {"name": "Heat charger", "id": DEVICE_HEAT_CHARGER_ID},
    {"name": "Heatpump 1", "id": DEVICE_HEATPUMP_1_ID},
    {"name": "Heatpump 2", "id": DEVICE_HEATPUMP_2_ID},
    {"name": "Thermostat", "id": DEVICE_THERMOSTAT_ID},
]


# Supervisory Control Modes
class SupervisoryControlMode(IntEnum):
    """Enumerates the supervisory control modes for the Quatt system."""

    STANDBY = 0
    STANDBY_HEATING = 1
    HEATING_HEATPUMP_ONLY = 2
    HEATING_HEATPUMP_PLUS_BOILER = 3
    HEATING_BOILER_ONLY = 4
    ANTIFREEZE_BOILER_ON = 96
    ANTIFREEZE_BOILER_PREPUMP = 97
    ANTIFREEZE_WATER_CIRCULATION = 98
    FAULT_CIRCULATION_PUMP_ON = 99

    @property
    def description(self) -> str:
        """Return a human-readable description of the supervisory control mode."""
        return {
            self.STANDBY: "Standby",
            self.STANDBY_HEATING: "Standby - heating",
            self.HEATING_HEATPUMP_ONLY: "Heating - heatpump only",
            self.HEATING_HEATPUMP_PLUS_BOILER: "Heating - heatpump + boiler",
            self.HEATING_BOILER_ONLY: "Heating - boiler only",
            self.ANTIFREEZE_BOILER_ON: "Anti-freeze protection - boiler on",
            self.ANTIFREEZE_BOILER_PREPUMP: "Anti-freeze protection - boiler pre-pump",
            self.ANTIFREEZE_WATER_CIRCULATION: "Anti-freeze protection - water circulation",
            self.FAULT_CIRCULATION_PUMP_ON: "Fault - circulation pump on",
        }[self]


# Defaults
DEFAULT_SCAN_INTERVAL: Final = 10
MIN_SCAN_INTERVAL: Final = 5
MAX_SCAN_INTERVAL: Final = 600

# Temperature-dependent conversion factors for water in a central heating system at 2 bar pressure.
# The table below provides specific heat capacity (c_p), density (rho), and conversion factors (k)
# for temperatures ranging from 5°C to 80°C in steps of 5°C.

# Temperature (C) | c_p (J/kg.C) | rho (kg/m^3) | Conversion Factor (k)
# -------------------------------------------------------------------------
# 5               | 4200.0       | 999.97       | 1.166667
# 10              | 4192.0       | 999.70       | 1.164444
# 15              | 4187.6       | 999.10       | 1.162889
# 20              | 4184.1       | 998.00       | 1.161111
# 25              | 4181.8       | 997.05       | 1.157438
# 30              | 4184.0       | 995.67       | 1.157753
# 35              | 4186.2       | 994.06       | 1.157931
# 40              | 4188.4       | 992.22       | 1.157964
# 45              | 4190.6       | 990.25       | 1.157859
# 50              | 4192.8       | 988.05       | 1.157617
# 55              | 4195.0       | 985.65       | 1.157243
# 60              | 4197.2       | 983.15       | 1.156742
# 65              | 4199.4       | 980.44       | 1.156117
# 70              | 4201.6       | 977.63       | 1.155369
# 75              | 4203.8       | 974.71       | 1.154503
# 80              | 4206.0       | 971.80       | 1.153528
# The specific heat capacity (c_p) and density (ρ) values are from the NIST Chemistry WebBook.
CONVERSION_FACTORS = {
    5: 1.166667,
    10: 1.164444,
    15: 1.162889,
    20: 1.161111,
    25: 1.157438,
    30: 1.157753,
    35: 1.157931,
    40: 1.157964,
    45: 1.157859,
    50: 1.157617,
    55: 1.157243,
    60: 1.156742,
    65: 1.156117,
    70: 1.155369,
    75: 1.154503,
    80: 1.153528,
}
