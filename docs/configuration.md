[Quatt integration](../README.md) › [Documentation](README.md) › Configuration

# Configuration

The Quatt integration supports three kinds of device. Each can be added on its own, or alongside the others:

| Device kind | What it is | You need |
|---|---|---|
| **CIC (heat pump)** | Your heat pump, read from the CIC over the local network | The CIC's IP address |
| **Home battery** | The Quatt home battery, via the Quatt mobile API | The battery's UUID, serial number and check code |
| **Energy (mijnenergie)** | Tariffs, usage and costs from the Quatt Energy portal | Your mijnenergie email address and password |

## Adding a CIC (heat pump)

### Manual

1. In Home Assistant click on `Settings`
2. Click on `Devices & services`
3. Click on `Integrations`
4. Click on `+ Add integration`
5. Search for and select `Quatt`
6. Enter the IP address of your Quatt CIC (for instance: 192.168.0.100, without `http://` or port number)
7. Click `Submit`
8. Enjoy

### Auto-discovery

The Quatt integration relies on DHCP requests made by the Commander In Chief (CIC) for autodiscovery. To force a DHCP request, turn off the CIC, wait 10 seconds and turn it back on again.

1. In Home Assistant click on `Settings`
2. Click on `Devices & services`
3. In case the `Quatt` has been auto-discovered, the discovered CIC is shown at the top of the screen
4. Click on `Configure`
5. Click on `Submit` to confirm to automatically add the integration to Home Assistant
6. Enjoy

> [!TIP]
> While adding the CIC you can also enable the [Remote Mobile API](remote-mobile-api.md) for additional sensors and controls. You can do this later as well, see [Enabling the Remote Mobile API](remote-mobile-api.md#enabling).

## Adding a home battery

To pair your home battery you need three values which you can find on the home battery label or in the Quatt mobile app:

- **UUID** (access key)
- **Serial number**
- **Check code**

Steps:

1. In Home Assistant, go to `Settings` → `Devices & services` → `Integrations`
2. Click `+ Add integration` and search for **Quatt**
3. In the "What kind of Quatt device do you want to add?" menu, select **Home battery**
4. Sign in to the Quatt mobile API (see [Quatt mobile API sign-in](#quatt-mobile-api-sign-in))
5. Enter the **UUID**, **Serial number** and **Check code** from the battery label
6. Click `Submit` — Home Assistant pairs the home battery via the Quatt mobile API
7. A new **Home battery** hub device appears with sub-devices **Savings**, **Insights** and **Energy flow** for cumulative savings, today's 15-minute insights and today's energy flow respectively

See [Home battery](home-battery.md) for what the device provides.

## Adding a Quatt Energy hub

The Quatt Energy hub connects to the separate **Quatt Energy portal** at https://mijnenergie.quatt.io. It uses its own portal credentials (email + password) — **not** the mobile-API sign-in used by the CIC and home battery.

Steps:

1. In Home Assistant, go to `Settings` → `Devices & services` → `Integrations`
2. Click `+ Add integration` and search for **Quatt**
3. In the "What kind of Quatt device do you want to add?" menu, select **Energy (mijnenergie)**
4. Enter the **email address** and **password** you use on https://mijnenergie.quatt.io
5. Click `Submit` — Home Assistant signs in to the portal, discovers your EAN and creates an **Energy** hub device

> [!NOTE]
> If sign-in succeeds but no EAN is returned, open https://mijnenergie.quatt.io once in a browser to finish onboarding, then retry.

To update the stored password later (e.g. after a portal password change), see [Options](#options).

See [Quatt Energy](quatt-energy.md) for what the hub provides.

## Quatt mobile API sign-in

Several features depend on the **Quatt mobile API**: the [Remote Mobile API](remote-mobile-api.md) on the CIC, and the [Home battery](home-battery.md). They share a single sign-in:

- The first time you add a Quatt device that needs the mobile API, you'll be asked for your **first name** and **last name** (and, for the CIC, a 60-second confirmation by pressing the physical button on the CIC).
- The credentials are stored locally in Home Assistant and reused automatically for any other Quatt device you add later — so the sign-in step is skipped on subsequent setups.

## Options

To change the options of a device, go to `Settings` → `Devices & services` → `Quatt` and click **Configure** on its entry. The options depend on the kind of device.

### CIC (heat pump)

| Option | Default | Description |
|---|---|---|
| Local update interval (seconds) | `10` | Seconds between requests to the local CIC API (5–600). |
| Remote mobile API update interval (minutes) | `1` | Minutes between requests to the Quatt mobile API (1–10). Only used when the Remote Mobile API is enabled. |
| Power sensor | — | Optional external sensor that measures the power consumption of the Quatt. Used for the **COP** sensor, see [Heat pump](heat-pump.md#cic). |
| Enable remote connection setup | off | Only shown when the Remote Mobile API is not enabled yet. See [Enabling the Remote Mobile API](remote-mobile-api.md#adding-to-an-existing-integration). |

### Home battery

| Option | Default | Description |
|---|---|---|
| Remote mobile API update interval (minutes) | `1` | Minutes between requests to the Quatt mobile API (1–10). |

### Energy (mijnenergie)

| Option | Default | Description |
|---|---|---|
| Remote mobile API update interval (minutes) | `1` | Minutes between requests to the Quatt Energy portal (1–10). |
| Quatt Energy password | — | Update this only when you changed your password on https://mijnenergie.quatt.io. |
