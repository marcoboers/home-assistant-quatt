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

## Remote Mobile API (Beta)

Starting from recent versions, this integration supports the **Quatt Remote Mobile API** in addition to the local CIC JSON API. This remote API has been reverse-engineered from the official Quatt mobile app and is currently in **beta** with no backwards compatibility guarantees.

### Advantages

- **Enhanced data**: Access to more detailed sensors and data about your Quatt products that are not available via the local CIC JSON
- **Remote control capabilities**: Enables future features like boosting the heat charger and heat battery when these controls are released in the official app
- **Additional controls**: Ability to programmatically adjust sound settings and configure electricity and gas prices (implementation pending)
- **Statistics access**: Retrieve long-term statistics available in the official Quatt app (though limited use case in Home Assistant)

#### Additional Sensors Available via Remote API

The remote API provides access to numerous sensors that are not available through the local CIC JSON API, including:

- **Connectivity status**: WiFi SSID, WiFi/LTE/cable connection status
- **Energy pricing**: Electricity prices (standard, day, night), gas prices, and night time schedule configuration
- **Sound control**: Silent mode status, day/night max sound levels, and sound schedule configuration
- **Heat battery metrics** (All-Electric only): Serial number, status, size, charge percentage, and estimated shower minutes
- **Enhanced heat pump data**: Compressor frequency (actual and demand), minimum/rated/expected power, water pump level, ODU type
- **Installation details**: Installation date, insights start date, Quatt build version, installation name, location (zip code, country), and order number
- **Thermostat data**: Control and room temperature set points, current room temperature

### Disadvantages and Considerations

- **No backwards compatibility**: The beta implementation does not guarantee backwards compatibility with previous versions
- **Authorization uncertainty**: Since the API was reverse-engineered, the long-term stability of the authorization mechanism is unknown. We cannot confirm if all authentication parameters are correctly implemented
- **Potential for changes**: The remote API may change or stop working if Quatt modifies their authentication system

**Note**: The integration currently requires the remote API for operation. If you experience authentication issues or the remote API becomes unavailable, this may affect the integration's functionality.

### Connecting the Remote API to Home Assistant

To add the remote API to your Home Assistant:

1. In Home Assistant, go to `Settings` → `Devices & services` → `Integrations`
2. Click `+ Add integration` (or if you already have a Quatt integration, click `Configure` and then `Add hub`)
3. Search for and select `Quatt`
4. Select **Remote API** as the connection type
5. Enter your **CIC ID**. You can find this:
   - In the Quatt mobile app (at the CIC QR code section)
   - In the local CIC JSON API output
6. Enter your **first name** and **last name**
7. Click `Submit`
8. **Within 60 seconds**, press the physical button on your CIC to complete the pairing process
9. Once paired, the setup will complete and the remote API sensors will become available
10. Optionally assign rooms/locations to the entities, or skip this step

The remote API will now be active and all available sensors will be added to your Home Assistant installation.

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
