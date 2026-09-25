[Quatt integration](../README.md) › [Documentation](README.md) › Installation

# Installation

## Requirements

- Home Assistant **2025.5.0** or newer.
- For the heat pump: a Quatt CIC (Commander In Chief) that Home Assistant can reach on your local network.
- For the [Remote Mobile API](remote-mobile-api.md), the [Home battery](home-battery.md) and [Quatt Energy](quatt-energy.md): internet access from Home Assistant.

## Install with HACS (recommended)

Do you have [HACS](https://hacs.xyz/) installed?

1. [Click here](https://my.home-assistant.io/redirect/hacs_repository/?owner=marcoboers&repository=home-assistant-quatt&category=integration) or add repository manually
   - Select Integrations, then select the 3-dots in the upper-right corner, then select Custom Repositories.
   - Put the Repository URL in the Repository field, then select Integration in the Category dropdown list and click Add.
2. Search integrations for **Quatt**
3. Click `Install`
4. Restart Home Assistant

## Install manually

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory (folder) there, you need to create it.
3. In the `custom_components` directory (folder) create a new folder called `quatt`.
4. Download in the [Releases](https://github.com/marcoboers/home-assistant-quatt/releases) section the `quatt.zip` file for the version of the integration you want to install and extract the files. Alternatively, download _all_ the files from the [`custom_components/quatt/`](../custom_components/quatt) directory (folder) in this repository. Note that the version number will not be updated if you choose the latter.
5. Place the files you downloaded in the new directory (folder) you created.
6. Restart Home Assistant

## Next steps

Add your Quatt devices to Home Assistant — see [Configuration](configuration.md).
