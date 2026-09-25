[Quatt integration](../README.md) › Documentation

# Documentation

Documentation for the unofficial Quatt integration for Home Assistant. New here? Start with [Installation](installation.md) and [Configuration](configuration.md).

## Getting started

| Page | Covers |
|---|---|
| [Installation](installation.md) | Requirements, installing with HACS, installing manually |
| [Configuration](configuration.md) | Adding a CIC, a home battery or a Quatt Energy hub; the Quatt mobile API sign-in; integration options |

## Devices and features

| Page | Covers | Built on |
|---|---|---|
| [Heat pump](heat-pump.md) | Devices, sensors from the local CIC API and the computed sensors | Local CIC API |
| [Remote Mobile API](remote-mobile-api.md) | Additional sensors and controls, heat battery boost, observed compressor starts, enabling it | Quatt mobile API¹ |
| [Quatt Chill](chill.md) | Climate control, status and diagnostics for Chill devices | Quatt mobile API¹ |
| [Home battery](home-battery.md) | Live status, savings, insights, energy flow, solar capacity | Quatt mobile API¹ |
| [Quatt Energy](quatt-energy.md) | Live tariff prices, surcharge toggles, price/usage/cost history | Quatt Energy portal¹ |

¹ Reverse-engineered — see [About reverse-engineered features](../README.md#about-reverse-engineered-features).

## Dashboards

| Page | Covers | Status |
|---|---|---|
| [Dashboard card](dashboard-card.md) | The Quatt Dashboard Card: features, prerequisites, adding it, troubleshooting | Beta |
| [Usage graphs with ApexCharts](usage-graphs.md) | Recreating the app's usage graphs from the on-demand actions | Beta |

## Reference

| Page | Covers |
|---|---|
| [Actions reference](actions.md) | All `quatt.*` actions, their fields and scopes |
| [Example files](../examples/README.md) | Python scripts, automations and ApexCharts cards used by the usage graphs |

## Help and contributing

- Found a bug or missing a feature? [Open an issue](https://github.com/marcoboers/home-assistant-quatt/issues/new/choose).
- Want to contribute? Read the [Contribution guidelines](../CONTRIBUTING.md). Changed a feature? Update the page for it in this folder.
