import {
    LitElement,
    html,
} from "https://unpkg.com/lit-element@2.0.1/lit-element.js?module";

class QuattDashboardCardEditor extends LitElement {
    static get properties() {
        return { _config: {}, hass: {} };
    }

    setConfig(config) {
        this._config = config || {};
    }

    set hass(hass) {
        this._hass = hass;
        this.requestUpdate();
    }

    _isTrue(value) {
        return value === true || value === 'true';
    }

    _isFalse(value) {
        return value === false || value === 'false';
    }

    // Helper for an expandable section with a grid inside
    _section(title, expanded, innerSchema) {
        return {
            type: "expandable",
            title,
            expanded: expanded,
            schema: [innerSchema]
        };
    }

    // Dynamic schema
    _schema(data, hass) {
        const SYSTEM_SETUP = {
            type: "grid",
            name: "system_setup",
            columns: 1,
            column_min_width: "100%",
            schema: [
                { name: "house_label", required: true, selector: { text: { max_length: 32 } } },
                { name: "system", required: true, selector: { entity: { integration: "quatt", domain: "sensor" } } },
            ],
        };
        const HP1_GRID = {
            type: "grid",
            name: "hp1",
            schema: [
                { name: "hp1_odu_type", required: true, selector: { entity: { integration: "quatt", domain: "sensor" } } },
                { name: "hp1_workingmode", required: true, selector: { entity: { integration: "quatt", domain: "sensor" } } },
                { name: "hp1_waterdelta", required: true, selector: { entity: { integration: "quatt", domain: "sensor", device_class: "temperature" } } },
                { name: "hp1_temperatureoutside", required: true, selector: { entity: { integration: "quatt", domain: "sensor", device_class: "temperature" } } },
                { name: "hp1_temperaturewaterin", required: true, selector: { entity: { integration: "quatt", domain: "sensor", device_class: "temperature" } } },
                { name: "hp1_temperaturewaterout", required: true, selector: { entity: { integration: "quatt", domain: "sensor", device_class: "temperature" } } },
                { name: "hp1_powerinput", required: true, selector: { entity: { integration: "quatt", domain: "sensor", device_class: "power" } } },
                { name: "hp1_power", required: true, selector: { entity: { integration: "quatt", domain: "sensor", device_class: "power" } } },
                { name: "hp1_cop", required: true, selector: { entity: { integration: "quatt", domain: "sensor" } } },
            ],
        };
        const HP2_GRID = {
            type: "grid",
            name: "hp2",
            schema: [
                { name: "hp2_workingmode", selector: { entity: { integration: "quatt", domain: "sensor" } } },
                { name: "hp2_waterdelta", selector: { entity: { integration: "quatt", domain: "sensor", device_class: "temperature" } } },
                { name: "hp2_temperatureoutside", selector: { entity: { integration: "quatt", domain: "sensor", device_class: "temperature" } } },
                { name: "hp2_temperaturewaterin", selector: { entity: { integration: "quatt", domain: "sensor", device_class: "temperature" } } },
                { name: "hp2_temperaturewaterout", selector: { entity: { integration: "quatt", domain: "sensor", device_class: "temperature" } } },
                { name: "hp2_powerinput", selector: { entity: { integration: "quatt", domain: "sensor", device_class: "power" } } },
                { name: "hp2_power", selector: { entity: { integration: "quatt", domain: "sensor", device_class: "power" } } },
                { name: "hp2_cop", selector: { entity: { integration: "quatt", domain: "sensor" } } },
            ],
        };
        const THERMOSTAT = {
            type: "grid",
            name: "thermostat",
            schema: [
                { name: "thermostat_room_temperature", required: true, selector: { entity: { integration: "quatt", domain: "sensor", device_class: "temperature" } } },
                { name: "thermostat_room_setpoint", required: true, selector: { entity: { integration: "quatt", domain: "sensor", device_class: "temperature" } } },
                { name: "thermostat_control_setpoint", required: true, selector: { entity: { integration: "quatt", domain: "sensor", device_class: "temperature" } } },
                { name: "thermostat_heating", required: true, selector: { entity: { integration: "quatt", domain: "binary_sensor" } } },
            ],
        };
        const CIC = {
            type: "grid",
            name: "cic",
            schema: [
                { name: "total_power", required: true, selector: { entity: { integration: "quatt", domain: "sensor", device_class: "power" } } },
                { name: "total_powerinput", required: true, selector: { entity: { integration: "quatt", domain: "sensor", device_class: "power" } } },
                { name: "cic_central_heating_on", required: true, selector: { entity: { integration: "quatt", domain: "binary_sensor" } } },
            ],
        };
        const FLOWMETER = {
            type: "grid",
            name: "flowmeter",
            schema: [
                { name: "flowmeter_temperature", required: true, selector: { entity: { integration: "quatt", domain: "sensor", device_class: "temperature" } } },
                { name: "flowmeter_flowrate", required: true, selector: { entity: { integration: "quatt", domain: "sensor" } } },
            ],
        };
        const BOILER = {
            type: "grid",
            name: "boiler",
            schema: [
                { name: "boiler_heating", selector: { entity: { integration: "quatt", domain: "binary_sensor" } } },
            ],
        };
        const BOILER_OPENTHERM = {
            type: "grid",
            name: "boiler",
            schema: [
                { name: "boiler_heating", selector: { entity: { integration: "quatt", domain: "binary_sensor" } } },
                { name: "boiler_water_pressure", selector: { entity: { integration: "quatt", domain: "sensor" } } },
            ],
        };
        const HEAT_BATTERY = {
            type: "grid",
            name: "heat_battery",
            schema: [
                { name: "heat_battery_charging", selector: { entity: { integration: "quatt", domain: "binary_sensor" } } },
                { name: "heat_battery_percentage", selector: { entity: { integration: "quatt", domain: "sensor" } } },
                { name: "heat_battery_shower_minutes_remaining", selector: { entity: { integration: "quatt", domain: "sensor" } } },
                { name: "heat_battery_domestic_hot_water_on", selector: { entity: { integration: "quatt", domain: "binary_sensor" } } },
                { name: "heat_battery_top_temperature", selector: { entity: { integration: "quatt", domain: "sensor", device_class: "temperature" } } },
                { name: "heat_battery_middle_temperature", selector: { entity: { integration: "quatt", domain: "sensor", device_class: "temperature" } } },
                { name: "heat_battery_bottom_temperature", selector: { entity: { integration: "quatt", domain: "sensor", device_class: "temperature" } } },
            ],
        };
        const HEAT_CHARGER = {
            type: "grid",
            name: "heat_charger",
            schema: [
                { name: "heat_charger_heating_system_pressure", selector: { entity: { integration: "quatt", domain: "sensor" } } },
            ],
        };
        const OTHER = {
            type: "grid",
            name: "other",
            schema: [
                { name: "thermostat_room", selector: { entity: { domain: "climate" } } },
                { name: "thermostat_airco", selector: { entity: { domain: "climate" } } },
                { name: "sun", selector: { entity: { domain: "sun" } } },
                { name: "solar_power", selector: { entity: { domain: "sensor", device_class: "power" } } },
                { name: "home_battery_soc", selector: { entity: { domain: "sensor" } } },
                { name: "hot_water_cylinder_temperature", selector: { entity: { domain: "sensor", device_class: "temperature" } } },
                { name: "has_solar_collector", selector: { boolean: {} } },
                {
                    name: "heatpump_metric",
                    selector: {
                        select: {
                            mode: "dropdown",
                            options: [
                                { value: "delta",      label: "ΔT" },
                                { value: "cop",        label: "COP" },
                                { value: "power",      label: "Power" },
                                { value: "powerinput", label: "Power input" },
                            ],
                        },
                    },
                },
            ],
        };

        // Determine the flags from the system entity
        const system_id = data?.system_setup?.system;
        const system_state = system_id ? hass?.states?.[system_id] : undefined;
        const system_attributes = system_state?.attributes ?? {};
        const attrIsSet = (key) =>
            this._isTrue(system_attributes?.[key]) || this._isFalse(system_attributes?.[key]);
        const hasAllElec = attrIsSet("All electric system");
        const hasDuoAttr = attrIsSet("Duo heatpump system");
        const hasSystem = !!system_state && hasAllElec && hasDuoAttr;
        const isAllElectric = hasSystem ? this._isTrue(system_attributes["All electric system"]) : undefined;
        const isDuo         = hasSystem ? this._isTrue(system_attributes["Duo heatpump system"]) : undefined;
        const isOpentherm   = hasSystem ? this._isTrue(system_attributes["Opentherm system"]) : undefined;

        // Conditionally build the sections in the schema
        const base = [];
        base.push(this._section("System", true, SYSTEM_SETUP));
        if (hasSystem) {
            base.push(this._section("Heatpump 1", false, HP1_GRID));
            if (isDuo) {
                base.push(this._section("Heatpump 2", false, HP2_GRID));
            }

            base.push(this._section("Thermostat", false, THERMOSTAT));
            base.push(this._section("CIC", false, CIC));
            base.push(this._section("Flowmeter", false, FLOWMETER));

            if (isAllElectric) {
                base.push(this._section("Heat battery", false, HEAT_BATTERY));
                base.push(this._section("Heat charger", false, HEAT_CHARGER));
            } else {
                if (isOpentherm) {
                    base.push(this._section("Boiler", false, BOILER_OPENTHERM));
                } else {
                    base.push(this._section("Boiler", false, BOILER));
                }
            }
        }
        base.push(this._section("Other", false, OTHER));

        return base;
    }

    // Labels shown next to fields
    _computeLabel = (schema) => {
        const name = schema.name;
        const map = {
            // System setup
            house_label: "House label",
            system: "The CIC systemname to determine your Quatt setup",

            // Heatpump 1
            hp1_odu_type: "HP1 version (ODU type)",
            hp1_workingmode: "HP1 working mode",
            hp1_waterdelta: "HP1 water delta",
            hp1_temperatureoutside: "HP1 outside temperature",
            hp1_temperaturewaterin: "HP1 water temperature in",
            hp1_temperaturewaterout: "HP1 water temperature out",
            hp1_powerinput: "HP1 power input",
            hp1_power: "HP1 power",
            hp1_cop: "HP1 COP",

            // Heatpump 2
            hp2_workingmode: "HP2 working mode",
            hp2_waterdelta: "HP2 water delta",
            hp2_temperatureoutside: "HP2 outside temperature",
            hp2_temperaturewaterin: "HP2 water temperature in",
            hp2_temperaturewaterout: "HP2 water temperature out",
            hp2_powerinput: "HP2 power input",
            hp2_power: "HP2 power",
            hp2_cop: "HP2 COP",

            // Thermostat
            thermostat_room_temperature: "Thermostat room temperature",
            thermostat_room_setpoint: "Thermostat room setpoint",
            thermostat_control_setpoint: "Thermostat control setpoint",
            thermostat_heating: "Thermostat heating",

            // CIC
            total_power: "Total power",
            total_powerinput: "Total power input",
            cic_central_heating_on: "Central heating on",

            // Flowmeter
            flowmeter_temperature: "Flowmeter temperature",
            flowmeter_flowrate: "Flowmeter flowrate",

            // Heat changer
            heat_charger_heating_system_pressure: "Heating system pressure",

            // Heat battery
            heat_battery_charging: "Heat battery charging",
            heat_battery_percentage: "Heat battery percentage",
            heat_battery_shower_minutes_remaining: "Shower minutes remaining",
            heat_battery_domestic_hot_water_on: "DHW on",
            heat_battery_top_temperature: "Top temperature",
            heat_battery_middle_temperature: "Middle temperature",
            heat_battery_bottom_temperature: "Bottom temperature",

            // Boiler (opentherm)
            boiler_heating: "Boiler heating",
            boiler_water_pressure: "Water pressure",

            // Other
            thermostat_room: "Thermostat room",
            thermostat_airco: "Thermostat airco",
            sun: "Sun",
            solar_power: "Solar current production",
            home_battery_soc: "Home battery state of charge",
            hot_water_cylinder_temperature: "Hot water cylinder temperature",
            has_solar_collector: "Solar collector",
            heatpump_metric: "Heat pump metric to display",
        };
        return map[name] ?? name;
    };

    // Helper text under fields
    _computeHelper = (schema) => {
        const name = schema.name;
        const map = {
            // System setup
            system: "Provided by local API",

            // Heatpump 1
            hp1_odu_type: "Provided by remote API",
            hp1_workingmode: "Provided by local API",
            hp1_waterdelta: "Provided by local API",
            hp1_temperatureoutside: "Provided by local API",
            hp1_temperaturewaterin: "Provided by local API",
            hp1_temperaturewaterout: "Provided by local API",
            hp1_powerinput: "Provided by local API",
            hp1_power: "Provided by local API",
            hp1_cop: "Provided by local API",

            // Heatpump 2
            hp2_workingmode: "Provided by local API",
            hp2_waterdelta: "Provided by local API",
            hp2_temperatureoutside: "Provided by local API",
            hp2_temperaturewaterin: "Provided by local API",
            hp2_temperaturewaterout: "Provided by local API",
            hp2_powerinput: "Provided by local API",
            hp2_power: "Provided by local API",
            hp2_cop: "Provided by local API",

            // Thermostat
            thermostat_room_temperature: "Provided by local API",
            thermostat_room_setpoint: "Provided by local API",
            thermostat_control_setpoint: "Provided by local API",
            thermostat_heating: "Provided by local API",

            // CIC
            total_power: "Provided by local API",
            total_powerinput: "Provided by local API",
            cic_central_heating_on: "Provided by local API",

            // Flowmeter
            flowmeter_temperature: "Provided by local API",
            flowmeter_flowrate: "Provided by local API",

            // Heat battery
            heat_battery_charging: "Provided by remote API",
            heat_battery_percentage: "Provided by remote API",
            heat_battery_shower_minutes_remaining: "Provided by local API",
            heat_battery_domestic_hot_water_on: "Provided by remote API",
            heat_battery_top_temperature: "Provided by local API",
            heat_battery_middle_temperature: "Provided by local API",
            heat_battery_bottom_temperature: "Provided by local API",

            // Heat changer
            heat_charger_heating_system_pressure: "Provided by local API",

            // Boiler (opentherm)
            boiler_heating: "Provided by local API",
            boiler_water_pressure: "Provided by local API",

            // Other
            thermostat_room: "Provided by another integration",
            thermostat_airco: "Provided by another integration",
            sun: "Provided by Home Assistant",
            solar_power: "Provided by another integration",
            home_battery_soc: "Provided by another integration",
            hot_water_cylinder_temperature: "Provided by another integration",
            has_solar_collector: "Provided by another integration",
            heatpump_metric: "User selection",
        };
        return map[name];
  };

    // When a value changes in the editor trigger the config-changed event
    _valueChanged(ev) {
        const config = ev.detail.value;
        this._config = config;
        this.dispatchEvent(new CustomEvent("config-changed", { detail: { config } }));
    }

    // Render the editor
    render() {
        if (!this._hass)
            return html``;

        const raw = this._schema?.(this._config || {}, this._hass) ?? [];
        const schema = Array.isArray(raw) ? raw : Object.values(raw);
        return html`
            <ha-form
                .hass=${this._hass}
                .data=${this._config}
                .schema=${schema}
                .computeLabel=${(s) => this._computeLabel(s)}
                .computeHelper=${(s) => this._computeHelper(s)}
                @value-changed=${this._valueChanged}
            ></ha-form>
        `;
    }
}

if (!customElements.get("quatt-dashboard-card-editor")) {
    customElements.define("quatt-dashboard-card-editor", QuattDashboardCardEditor);
}
