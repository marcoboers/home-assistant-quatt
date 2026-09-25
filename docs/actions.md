[Quatt integration](../README.md) › [Documentation](README.md) › Actions reference

# Actions reference

The integration provides on-demand actions that fetch history from Quatt. They are the building blocks of the [usage graphs](usage-graphs.md).

| Action | Returns | Requires |
|---|---|---|
| [`quatt.get_cic_insights`](#quattget_cic_insights) | Heat pump insights | [Remote Mobile API](remote-mobile-api.md) |
| [`quatt.get_home_battery_insights`](#quattget_home_battery_insights) | Home battery 15-minute timeseries | [Home battery](home-battery.md) |
| [`quatt.get_home_battery_energy_flow`](#quattget_home_battery_energy_flow) | Home battery energy flow | [Home battery](home-battery.md) |
| [`quatt.get_home_battery_savings`](#quattget_home_battery_savings) | Home battery savings | [Home battery](home-battery.md) |
| [`quatt.get_energy_prices`](#quattget_energy_prices) | Tariff prices | [Quatt Energy](quatt-energy.md) |
| [`quatt.get_energy_power`](#quattget_energy_power) | Electricity or gas usage | [Quatt Energy](quatt-energy.md) |
| [`quatt.get_energy_costs`](#quattget_energy_costs) | Electricity or gas costs | [Quatt Energy](quatt-energy.md) |

All actions only return data: try them in `Developer tools` → `Actions`, or store the result in a script or automation with `response_variable`:

```yaml
action: quatt.get_home_battery_savings
data:
  year: 2026
response_variable: savings
```

## `quatt.get_cic_insights`

Retrieves insights data for a specific time period from the Quatt installation. The end date is automatically calculated based on `from_date` and `timeframe`.

| Field | Required | Default | Description |
|---|---|---|---|
| `from_date` | no | `2020-01-01` | Start date in ISO format (`YYYY-MM-DD`) |
| `timeframe` | no | `all` | One of `all`, `day`, `week`, `month`, `year` |
| `advanced_insights` | no | `true` | Include advanced insights data |

CIC insights are refreshed by Quatt **roughly once per hour** — do not poll more frequently.

## `quatt.get_home_battery_insights`

Retrieves home battery insights as a 15-minute timeseries (power, charge state, control action and control mode) from the Quatt mobile API.

| Field | Required | Description |
|---|---|---|
| `year` | no¹ | Year (e.g. `2026`) |
| `month` | no¹ | Month, 1-12 |
| `day` | no¹ | Day of month, 1-31 |

¹ Provide all three for a specific date, or none for today.

## `quatt.get_home_battery_energy_flow`

Retrieves the home battery energy-flow timeseries and aggregated totals (battery charge/discharge, solar, house, grid import/export). The scope is determined by which fields you provide:

| Fields provided | Scope |
|---|---|
| (none) | Today |
| `year` + `month` + `day` | A specific day |
| `year` + `month` | A specific month |
| `year` | A specific year |

## `quatt.get_home_battery_savings`

Retrieves the home battery savings timeseries and aggregated totals (home battery, solar, imbalance and total savings, in cents incl. and excl. VAT).

| Fields provided | Scope (granularity) |
|---|---|
| (none) | Current month (daily granularity) |
| `year` + `month` | A specific month (daily granularity) |
| `year` | A specific year (monthly granularity) |

## `quatt.get_energy_prices`

Retrieves tariff prices from the Quatt Energy portal. Whether VAT, energy tax and supplier markup are included is controlled by the surcharge switches on the [Quatt Energy](quatt-energy.md#features) hub.

| Field | Required | Default | Description |
|---|---|---|---|
| `period` | no | `day` | One of `day`, `month`, `year` |
| `product` | no | `electricity` | One of `electricity`, `gas` |
| `year` | no | current | Year (e.g. `2026`) |
| `month` | no | current | Month, 1-12 |
| `day` | no | today | Day of month, 1-31 (only used when `period=day`) |

Prices are published by the portal roughly **once per day** — do not poll more frequently.

## `quatt.get_energy_power`

Retrieves electricity or gas usage from the Quatt Energy portal. Scope is determined by which fields you provide:

| Fields provided | Scope |
|---|---|
| (none) / `year` only | Whole-year monthly aggregate |
| `year` + `month` + `day` | Hourly drilldown of that day |

| Field | Required | Default | Description |
|---|---|---|---|
| `product` | no | `electricity` | One of `electricity`, `gas` |
| `year` | no | current | Year (e.g. `2026`) |
| `month` | no | — | Month, 1-12 (only used together with `day`) |
| `day` | no | — | Day of month, 1-31 |

Power data lags the portal by roughly **two days**.

## `quatt.get_energy_costs`

Retrieves electricity or gas costs from the Quatt Energy portal. Scope and refresh cadence match [`quatt.get_energy_power`](#quattget_energy_power):

| Fields provided | Scope |
|---|---|
| (none) / `year` only | Whole-year monthly aggregate |
| `year` + `month` + `day` | Hourly drilldown of that day |

| Field | Required | Default | Description |
|---|---|---|---|
| `product` | no | `electricity` | One of `electricity`, `gas` |
| `year` | no | current | Year (e.g. `2026`) |
| `month` | no | — | Month, 1-12 (only used together with `day`) |
| `day` | no | — | Day of month, 1-31 |
