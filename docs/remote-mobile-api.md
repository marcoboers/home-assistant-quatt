[Quatt integration](../README.md) › [Documentation](README.md) › Remote Mobile API

# Remote Mobile API

> [!NOTE]
> Built on the reverse-engineered Quatt mobile API — see [About reverse-engineered features](../README.md#about-reverse-engineered-features).

The Remote Mobile API extends the local CIC integration with additional sensors and controls that are only available through the Quatt mobile API. It is **opt-in**: the integration works fully with only the local API.

It also adds support for **[Quatt Chill](chill.md)** devices when they are present on your installation.

## Additional sensors via remote API

Only sensors that are not already provided by the local API are added — no duplicates.

- **Connectivity status**: WiFi SSID, WiFi/LTE/cable connection status
- **Energy pricing**: Electricity prices (standard, day, night), gas prices, and night time schedule configuration
- **Sound control**: Silent mode status, day/night max sound levels, and sound schedule configuration
- **Quatt Chill support**: Climate control for heating/cooling, target temperature and fan mode, plus Chill status and diagnostic sensors — see [Quatt Chill](chill.md)
- **Heat battery metrics** (All-Electric only): Serial number, status, size, charge percentage
- **Enhanced heat pump data**: Compressor frequency (actual and demand), minimum/rated/expected power, water pump level, ODU type, on/off status, Modbus slave ID
- **Installation details**: Installation date, insights start date, Quatt build version, installation name, location (zip code, country), and order number
- **Thermostat data**: Outside temperature (via remote API)
- **Boiler data** (Hybrid only): Additional boiler power and temperature sensors
- **Observed compressor starts**: Per heat pump — see [below](#observed-compressor-starts)

## Controls

In addition, the remote API exposes **programmable day and night maximum sound levels** (normal, library, silent) as controls, and the **night time window** (start and end time, in 30-minute steps) as time entities, including a button to reset the window to the Quatt defaults.

## Observed compressor starts

With the Remote Mobile API enabled, each heat pump has an **Observed compressor starts** sensor (**Waargenomen compressorstarts** in Dutch). HP1 and HP2 are counted independently. Each heat pump also has a **Compressor starts tracked since** timestamp sensor (**Compressorstarts bijgehouden sinds** in Dutch), showing the date and time when its tracking began. Both sensors are enabled by default.

- A measured compressor frequency of **1 Hz or higher** is treated as running. A transition from below 1 Hz to running increases the count by one.
- At the first valid measurement, a compressor already running counts as **one** start; a stopped compressor starts at **zero**. The tracking-start sensor shows when tracking began, not when that first compressor start physically occurred. It remains unknown until the first valid measurement and retains the same date after reloads, restarts and backup restores. The date also remains available as the counter's `tracking_since` attribute.
- Missing, invalid or unavailable readings do not mean the compressor stopped and do not reset its last known state. No minimum stop duration is imposed.
- The sensor uses the existing remote API updates, normally **once per minute**, without making extra API requests or changing the configured interval. Existing faster updates during heat battery boost continue to work.

> [!IMPORTANT]
> **Accuracy:** this is a count of observed starts since tracking began, not the heat pump's lifetime start count. Stop/start cycles entirely between readings, starts during Home Assistant or API downtime, and changes hidden by delayed API data may be missed. After an interruption, the last known state is compared with the next valid reading; intermediate starts cannot be reconstructed.

**Persistence and backups:** both counters, their `tracking_since` timestamps and their last known running states are stored together in Home Assistant's `.storage` directory. Changes are saved at each observed start or stop, so the values survive integration reloads and Home Assistant restarts without recounting a continuously running compressor. Renaming the sensors does not reset them. Backups that include the Home Assistant configuration also include these values; restoring that configuration restores the saved counts as of the backup, not any starts recorded afterwards. Deleting the integration entry removes its counters; adding it again starts a new tracking period.

## Enabling

The Remote Mobile API can be enabled either while adding the CIC for the first time, or on an existing CIC.

### During initial setup

1. In Home Assistant, go to `Settings` → `Devices & services` → `Integrations`
2. Click `+ Add integration` and search for **Quatt**
3. Enter your **CIC IP address** (e.g. 192.168.0.100)
4. When prompted, **enable Remote API** by toggling the option
5. Sign in to the Quatt mobile API (see [Quatt mobile API sign-in](configuration.md#quatt-mobile-api-sign-in))
6. **Within 60 seconds**, press the physical button on your CIC to complete pairing
7. Setup completes with both local and remote API active

### Adding to an existing integration

1. Go to `Settings` → `Devices & services` → `Integrations`
2. Find your Quatt integration and click **Configure**
3. Enable the **Add Remote API** toggle
4. Sign in to the Quatt mobile API (see [Quatt mobile API sign-in](configuration.md#quatt-mobile-api-sign-in))
5. **Within 60 seconds**, press the physical button on your CIC to complete pairing
6. The integration reloads with the remote API sensors and controls available

The update interval of the remote API can be changed in the [Options](configuration.md#cic-heat-pump).
