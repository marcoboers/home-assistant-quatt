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
