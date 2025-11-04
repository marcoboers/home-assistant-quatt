# Quatt integration for Home Assistant

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]
![Project Maintenance][maintenance-shield]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

_Unofficial integration for Quatt Heat Pump._

## Installation

### Install with HACS (recommended)

Do you have [HACS](https://hacs.xyz/) installed?

1. [Click here](https://my.home-assistant.io/redirect/hacs_repository/?owner=marcoboers&repository=home-assistant-quatt&category=integration) or add repository manually
   - Select Integrations, then select the 3-dots in the upper-right corner, then select Custom Repositories.
   - Put the Reposity URL in the Repository field, then select Integration in the Category dropdown list and click Add.
1. Search integrations for **Quatt**
1. Click `Install`
1. Restart Home Assistant

### Install manually

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
1. If you do not have a `custom_components` directory (folder) there, you need to create it.
1. In the `custom_components` directory (folder) create a new folder called `quatt`.
1. Download in the `Releases` section the `quatt.zip` file for the version of the integration you want to install and extract the files. Alternatively, download _all_ the files from the `custom_components/quatt/` directory (folder) in this repository. Note that the version number will not be updated if you choose the latter.
1. Place the files you downloaded in the new directory (folder) you created.
1. Restart Home Assistant

## Configuration

### Manual

1. In Home Assistant click on `Settings`
1. Click on `Devices & services`
1. Click on `Integrations`
1. Click on `+ Add integration`
1. Search for and select `Quatt`
1. Enter the ip address of your Quatt CIC (for instance: 192.168.0.100 without http:// or port number)
1. Click `Submit`
1. Enjoy

### Auto-discovery

The Quatt integration relies on DHCP requests made by the Commander In Chief (CIC) for autodiscovery. To force a DHCP request, turn off the CIC and wait 10 seconds and turn it back on again.

1. In Home Assistant click on `Settings`
1. Click on `Devices & services`
1. In case the `Quatt` has been auto-discovered, the discovered CIC is shown at the top of the screen
1. Click on `Configure`
1. Click on `Submit` to confirm to automatically add the integration to Home Assistant
1. Enjoy

## Remote Mobile API (Optional)

This integration supports the **Quatt Remote Mobile API** as an optional addition to the local CIC JSON API. The remote API provides access to additional sensors and controls beyond what's available through the local API.

**Special thanks to [@WoutervanderLoopNL](https://github.com/WoutervanderLoopNL) for reverse engineering the official Quatt mobile app, which made this remote API support possible!**

### Key Features

- **Additional sensors**: Access to sensors not available via the local API (see list below)
- **Sound level controls**: Programmable day and night maximum sound levels (normal, library, silent)
- **Smart filtering**: Only sensors not already available through the local API are added, avoiding duplicates
- **Seamless integration**: Remote API is configured as an optional toggle on the existing CIC device

### Additional Sensors Available via Remote API

The remote API provides access to numerous sensors that complement the local API:

- **Connectivity status**: WiFi SSID, WiFi/LTE/cable connection status
- **Energy pricing**: Electricity prices (standard, day, night), gas prices, and night time schedule configuration
- **Sound control**: Silent mode status, day/night max sound levels, and sound schedule configuration
- **Heat battery metrics** (All-Electric only): Serial number, status, size, charge percentage
- **Enhanced heat pump data**: Compressor frequency (actual and demand), minimum/rated/expected power, water pump level, ODU type, on/off status, Modbus slave ID
- **Installation details**: Installation date, insights start date, Quatt build version, installation name, location (zip code, country), and order number
- **Thermostat data**: Outside temperature (via remote API)
- **Boiler data** (Hybrid only): Additional boiler power and temperature sensors

### Important Considerations

- **Beta status**: This feature is currently in **beta** with no backwards compatibility guarantees between versions
- **Optional feature**: The integration works fully with only the local API; remote API is optional
- **Reverse engineered API**: The remote API was obtained through reverse engineering of the official Quatt mobile app. As such, the long-term stability cannot be guaranteed
- **Dependent on Quatt**: This feature depends on Quatt's remote API infrastructure. Changes to Quatt's authentication system or API may cause the remote API integration to stop working
- **No official support**: Since this is based on reverse engineering, there is no official support from Quatt for this functionality
- **Smart filtering**: The integration intelligently filters remote sensors to avoid duplicating data already available from the local API

### Enabling Remote API

To enable the remote API for your existing Quatt CIC:

#### During Initial Setup

1. In Home Assistant, go to `Settings` → `Devices & services` → `Integrations`
2. Click `+ Add integration` and search for **Quatt**
3. Enter your **CIC IP address** (e.g., 192.168.0.100)
4. When prompted, **enable Remote API** by toggling the option
5. Enter your **first name** and **last name**
6. **Within 60 seconds**, press the physical button on your CIC to complete pairing
7. The setup will complete with both local and remote API active

#### Adding to Existing Integration

1. Go to `Settings` → `Devices & services` → `Integrations`
2. Find your Quatt integration and click **Configure**
3. Enable the **Add Remote API** toggle
4. Enter your **first name** and **last name**
5. **Within 60 seconds**, press the physical button on your CIC to complete pairing
6. The integration will reload with remote API sensors and controls available

Once enabled, additional sensors and the sound level controls will appear in your Home Assistant installation.

## Quatt Dashboard Card

This integration includes a fully-featured **Quatt Dashboard Card** that replicates and enhances the dashboard from the official Quatt mobile app directly in your Home Assistant interface. This provides a comprehensive, at-a-glance view of your Quatt heat pump system status and performance.

**Special thanks to [@WoutervanderLoopNL](https://github.com/WoutervanderLoopNL) for reverse engineering the official Quatt mobile app. The extracted images form the foundation of this card!**

<img width="930" height="732" alt="Quatt overview" src="https://github.com/user-attachments/assets/2dc22c2d-21fe-4c5a-a181-08a596e98e42" />

### Features

- **Complete system overview**: Visual representation of your entire Quatt system including heat pump(s), boiler, and heat battery
- **Real-time status**: Live updates of temperatures, power consumption, and operating modes
- **Universal support**: Works with all Quatt configurations:
    - Hybrid setups (heat pump + boiler)
    - All-Electric setups (with heat battery/heat charger)
    - Quatt Mono (single heat pump)
    - Quatt Duo (dual heat pumps)
- **Additional features**:
    - Airconditioning integration including heating and cooling animations
    - Solar panel integration including animations
    - Solar collector integration including animations
    - Home battery integration
    - Hot water tank integration including water temperature animations
- **Responsive design**: Adapts to different screen sizes and devices
- **Custom card implementation**: Uses a dedicated Lovelace custom card for optimal performance

### Prerequisites

To use the Quatt Dashboard, you need:

1. **Remote API configured**: The dashboard requires the Remote Mobile API to be set up (see [Remote Mobile API](#remote-mobile-api-optional---beta) section above)
2. **Required sensors enabled**: Two sensors from the remote API must be manually enabled:
   - `OduType` (ODU Type)
   - `Number of heatpumps`

   These sensors are disabled by default. To enable them:
   - Go to `Settings` → `Devices & services` → `Integrations` → `Quatt`
   - Click on your CIC device
   - Find the `OduType` and `Number of heatpumps` sensors
   - Click on each sensor and enable it

### Installation

The Quatt Dashboard is implemented as a custom Lovelace card which is installed automatically during installation of the integration, making it easy to add the card to any dashboard.

### Troubleshooting

- **Card not found**: Ensure Home Assistant has loaded the integration properly. Try restarting Home Assistant
- **Incomplete data**: Make sure both `OduType` and `Number of heatpumps` sensors are enabled
- **No data showing**: Confirm the Remote API is configured and working (check the Remote API sensors)

## Sensors

All sensors from the local API feed are available. In addition, the following computed sensors are provided:

#### CIC

- **Supervisory control mode**: Textual representation of the QC `supervisoryControlMode` status.
- **COP**: Calculated using the produced heat and the power consumed by the external power sensor (configurable).
- **Heat power**: Heat output of the heat pumps.
- **Total power**: Combined heat output of both heatpumps (Quatt Duo only).
- **Total power input**: Combined power input of both heatpumps (Quatt Duo only).
- **Total system power**: Combined system power
  - All-electric setup: `heat charger + heatpump(s)`
  - Standard setup: `boiler + heatpump(s)`
- **Total Quatt COP**: COP calculated using the produced heat and the power used by the heatpump(s).

#### Heatpump

- **Quatt COP**: COP calculated using the produced heat and the power used by the heatpump.
- **Water delta**: Difference between inlet and outlet water temperatures.

#### Boiler

- **Heat power**: Heat output of the boiler.

## Contributions are welcome!

Special thanks to [@patrickvorgers](https://github.com/patrickvorgers) for maintaing this integration and enhancing the integration to its current level.

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

[home-assistant-quatt]: https://github.com/marcoboers/home-assistant-quatt
[buymecoffee]: https://www.buymeacoffee.com/marcoboers
[buymecoffeebadge]: https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png
[commits-shield]: https://img.shields.io/github/commit-activity/y/marcoboers/home-assistant-quatt.svg?style=for-the-badge
[commits]: https://github.com/marcoboers/home-assistant-quatt/commits/main
[hacs]: https://my.home-assistant.io/redirect/hacs_repository/?owner=marcoboers&repository=home-assistant-quatt&category=integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[exampleimg]: example.png
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/marcoboers/home-assistant-quatt.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-marcoboers-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/marcoboers/home-assistant-quatt.svg?style=for-the-badge
[releases]: https://github.com/marcoboers/home-assistant-quatt/releases
