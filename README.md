# Quatt integration for Home Assistant

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]
![Project Maintenance][maintenance-shield1] ![Project Maintenance][maintenance-shield2]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

_Unofficial integration for Quatt Heat Pump and Quatt Home Battery._

This integration covers the **local CIC JSON API** (heat pump telemetry) plus a number of optional features built on top of the **Quatt mobile API** (additional remote sensors, home battery support, chill support, dashboard card, ApexCharts usage graphs).

![Quatt dashboard card](docs/images/quatt-dashboard-card.png)

## Features

| Feature | What you get | Requires |
|---|---|---|
| [Heat pump](docs/heat-pump.md) | All sensors from the local CIC API, plus computed COP, heat power and system power | A CIC on your local network |
| [Remote Mobile API](docs/remote-mobile-api.md) | Extra sensors and controls: connectivity, energy pricing, sound levels, night time window, heat battery boost, observed compressor starts | Opt-in, on top of a CIC |
| [Quatt Chill](docs/chill.md) | Climate entity for heating/cooling, plus Chill status and diagnostics | Remote Mobile API |
| [Home battery](docs/home-battery.md) | Live status, savings, insights and energy flow | Quatt mobile API; no CIC needed |
| [Quatt Energy](docs/quatt-energy.md) | Live tariff prices, plus price, usage and cost history | A mijnenergie account; no CIC needed |
| [Dashboard card](docs/dashboard-card.md) | App-style overview of your whole Quatt system — **beta** | A CIC |
| [Usage graphs](docs/usage-graphs.md) | Quatt-style usage graphs with ApexCharts — **beta** | ApexCharts card |

## Installation

Requires Home Assistant **2025.5.0** or newer.

### Install with HACS (recommended)

[![Open your Home Assistant instance and open this repository inside HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)][hacs]

1. Click the button above, or add this repository to HACS as a custom repository of type **Integration**
2. Search integrations for **Quatt**
3. Click `Install`
4. Restart Home Assistant

To install without HACS, see [Manual installation](docs/installation.md#install-manually).

### Add your Quatt devices

[![Open your Home Assistant instance and start setting up the Quatt integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=quatt)

Go to `Settings` → `Devices & services` → `+ Add integration` and search for **Quatt**. You can add each kind of device on its own, or several alongside each other:

- **CIC (heat pump)** — see [Adding a CIC](docs/configuration.md#adding-a-cic-heat-pump)
- **Home battery** — see [Adding a home battery](docs/configuration.md#adding-a-home-battery)
- **Energy (mijnenergie)** — see [Adding a Quatt Energy hub](docs/configuration.md#adding-a-quatt-energy-hub)

## Documentation

The full documentation lives in [`docs/`](docs/README.md):

- [Installation](docs/installation.md)
- [Configuration](docs/configuration.md) — adding devices, mobile API sign-in, options
- [Heat pump](docs/heat-pump.md) — local sensors and computed values
- [Remote Mobile API](docs/remote-mobile-api.md) — additional sensors and controls
- [Quatt Chill](docs/chill.md)
- [Home battery](docs/home-battery.md)
- [Quatt Energy](docs/quatt-energy.md)
- [Dashboard card](docs/dashboard-card.md)
- [Usage graphs with ApexCharts](docs/usage-graphs.md)
- [Actions reference](docs/actions.md)

## About reverse-engineered features

A number of features in this integration are built on top of the **Quatt mobile API** and the **Quatt Energy portal**, which were reverse-engineered from the official Quatt mobile app and web portal: the [Remote Mobile API](docs/remote-mobile-api.md), [Quatt Chill](docs/chill.md), the [Home battery](docs/home-battery.md), [Quatt Energy](docs/quatt-energy.md), the [Dashboard card](docs/dashboard-card.md) and the [Usage graphs](docs/usage-graphs.md).

These features are **fully supported in this integration**, but the same caveats apply to all of them:

- **Reverse-engineered**: The Quatt mobile API was obtained by reverse-engineering the official Quatt mobile app. Special thanks to [@WoutervanderLoopNL](https://github.com/WoutervanderLoopNL) for the original work that made every mobile-API feature in this integration possible.
- **Dependent on Quatt**: These features rely on Quatt's mobile-API infrastructure. If Quatt changes their authentication or API on their side, the corresponding features may stop working until this integration is updated.
- **No official Quatt support**: Since these features are based on reverse-engineering, Quatt does not offer official support for them.

The **Dashboard card** and the **Usage graphs with ApexCharts** examples are additionally still in **beta**, with no backwards-compatibility guarantees between versions.

## Contributions

Contributions are welcome!

Special thanks to [@patrickvorgers](https://github.com/patrickvorgers) for maintaining this integration and enhancing it to its current level.

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md).

[buymecoffee]: https://www.buymeacoffee.com/marcoboers
[buymecoffeebadge]: https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png
[commits-shield]: https://img.shields.io/github/commit-activity/y/marcoboers/home-assistant-quatt.svg?style=for-the-badge
[commits]: https://github.com/marcoboers/home-assistant-quatt/commits/main
[hacs]: https://my.home-assistant.io/redirect/hacs_repository/?owner=marcoboers&repository=home-assistant-quatt&category=integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/marcoboers/home-assistant-quatt.svg?style=for-the-badge
[maintenance-shield1]: https://img.shields.io/badge/maintainer-patrickvorgers-blue.svg?style=for-the-badge
[maintenance-shield2]: https://img.shields.io/badge/maintainer-marcoboers-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/marcoboers/home-assistant-quatt.svg?style=for-the-badge
[releases]: https://github.com/marcoboers/home-assistant-quatt/releases
