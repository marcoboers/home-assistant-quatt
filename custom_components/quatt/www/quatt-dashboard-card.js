import {
    LitElement,
    svg,
    html,
    css,
} from "https://unpkg.com/lit-element@2.0.1/lit-element.js?module";

class QuattDashboardCard extends LitElement {
    // Determine the base url and version of this card <script src=".../quatt-dashboard-card.js?v=...">
    static _getBaseUrlAndVersion() {
        // e.g. /quatt-dashboard-card/quatt-dashboard-card.js?v=1.2.3
        const url = new URL(import.meta.url);
        const base = url.pathname.slice(0, url.pathname.lastIndexOf("/"));
        const version = url.searchParams.get("v") || "0";
        return { base, version };
    }

   constructor() {
        super();
        const { base, version } = QuattDashboardCard._getBaseUrlAndVersion();
        this._BASE_URL = base;
        this._VERSION = version;
    }

    static get properties() {
        return {
            hass: {},
            config: {},
        };
    }

    _isTrue(value) {
        return value === true || value === 'true';
    }

    _isFalse(value) {
        return value === false || value === 'false';
    }

    jsonValueUsingPath(rec, path, index = 0) {
        let item = rec?.[path[index]];

        return ['string', 'number', 'bigint', 'boolean', 'undefined', 'symbol', 'null'].includes((typeof item).toLowerCase()) ? item : this.jsonValueUsingPath(item, path, index + 1)
    }

    /**
     * Get HA state (or a direct attribute) by config path.
     * Default: returns the full state object
     * If options.attribute is set (string key), returns that attribute (or number-formatted when options.number===true).
     *
     * @param {string} path - dot path into this.config (e.g. 'boiler.boiler_water_pressure')
     * @param {object}  [options]
     * @param {string}  [options.attribute]     - direct attribute key
     * @param {boolean} [options.number=true]   - format value as number
     * @param {number}  [options.decimals=2]    - fraction digits
     * @param {number}  [options.scale=1]       - multiply value by this factor (e.g. 1/1000 for W→kW)
     * @param {string}  [options.locale=navigator.language||'en-US'] - for toLocaleString
     * @param {boolean} [options.asString=true] - when number=true: return string; if false returns Number
     * @param {*}       [options.fallback]      - used when missing/non-numeric (string if asString, number if !asString)
     */
    getSensorState(path, options = {}) {
        const entityId = this.jsonValueUsingPath(this.config, path.split('.'));
        const stateObject = this.hass?.states?.[entityId];
        const hasAttr = typeof options.attribute === 'string' && options.attribute.length > 0;

        // If no numeric formatting requested, return the full state object or the requested attribute
        if (!options.number) {
            if (hasAttr) {
                return stateObject ? stateObject.attributes?.[options.attribute] : options.fallback;
            }
            return stateObject;
        }

        // If not found, return fallback
        if (!stateObject) {
            return options.asString !== false
                ? (typeof options.fallback === 'string' ? options.fallback : '0.00')
                : (typeof options.fallback === 'number' ? options.fallback : 0);
        }

        // Numeric formatting
        const rawValue = hasAttr ? stateObject.attributes?.[options.attribute] : stateObject.state;
        const num = typeof rawValue === 'number' ? rawValue : Number(rawValue);
        const decimals = Number.isInteger(options.decimals) ? options.decimals : 2;
        const scale = (typeof options.scale === 'number') ? options.scale : 1;
        const locale = options.locale || (typeof navigator !== 'undefined' && navigator.language) || 'en-US';
        const asString = options.asString !== false;

        if (Number.isFinite(num)) {
            const numScaled = num * scale;
            if (asString) {
                return numScaled.toLocaleString(locale, {
                    minimumFractionDigits: decimals,
                    maximumFractionDigits: decimals,
                });
            }
            // Numeric result rounded to requested decimals
            return Number(numScaled.toFixed(decimals));
        }


        // Fallbacks when value is missing or non-numeric
        if (asString) {
            if (typeof options.fallback === 'string')
                return options.fallback;
            return (0).toLocaleString(locale, {
                minimumFractionDigits: decimals,
                maximumFractionDigits: decimals,
            });
        }
        return (typeof options.fallback === 'number') ? options.fallback : 0;
    }

    isReady() {
        return this.hass
                && this.config
                && this.getSensorState('system_setup.system')
    }

    isHybrid() {
        return this._isFalse(this.getSensorState('system_setup.system', {attribute: 'All electric system'}));
    }
    isAllElectric() {
        return this._isTrue(this.getSensorState('system_setup.system', {attribute: 'All electric system'}));
    }
    hasAirco() {
        return !!this.getSensorState('other.thermostat_airco')?.state
    }
    hasSolarPanels() {
        return !!this.getSensorState('other.solar_power')?.state
    }
    hasSolarCollector() {
        return !!(this.config?.[`other`]?.[`has_solar_collector`] ?? false)
    }
    hasBattery() {
        return !!(this.config?.[`other`]?.[`home_battery_soc`] ?? false)
    }
    hasHotWaterCylinder() {
        return !!this.getSensorState('other.hot_water_cylinder_temperature')?.state
    }
    isMonoHeatpump() {
        return this._isFalse(this.getSensorState('system_setup.system', {attribute: 'Duo heatpump system'}));
    }
    isDuoHeatpump() {
        return this._isTrue(this.getSensorState('system_setup.system', {attribute: 'Duo heatpump system'}));
    }
    isBoilerOpentherm() {
        return this._isTrue(this.getSensorState('system_setup.system', {attribute: 'Opentherm system'}));
    }
    getSystemVersion() {
        switch (this.getSensorState('hp1.hp1_odu_type')?.state) {
            case 'AMM4-V2.0':
                return 'V2';
            default:
                return 'V1';
        }
    }

    firstUpdated() {
        const tank = this.shadowRoot.querySelector('#tankPercentage');
        const room = this.shadowRoot.querySelector('#roomTemperature');
        const ac = this.shadowRoot.querySelector('#aircoTemperature');
        const waterPipe = this.shadowRoot.querySelector('#waterPipeTemperature');
        const hp1Delta = this.shadowRoot.querySelector('#hp1DeltaTemperature');
        const hp2Delta = this.shadowRoot.querySelector('#hp2DeltaTemperature');

        if (tank) {
            tank.addEventListener('mouseenter', () => {
                this.shadowRoot.querySelector('#tooltipTankPercentage').classList.add('tooltip-show');
            });

            tank.addEventListener('mouseleave', () => {
                this.shadowRoot.querySelector('#tooltipTankPercentage').classList.remove('tooltip-show');
            });
        }
        if (room) {
            room.addEventListener('mouseenter', () => {
                this.shadowRoot.querySelector('#tooltipRoomTemperature').classList.add('tooltip-show');
            });

            room.addEventListener('mouseleave', () => {
                this.shadowRoot.querySelector('#tooltipRoomTemperature').classList.remove('tooltip-show');
            });

            room.addEventListener('click', () => {
                const thermostatEntity = this.config?.other?.thermostat_room;

                if (thermostatEntity) {
                    this._openMoreInfo(thermostatEntity);
                }
            });
        }
        if (ac) {
            ac.addEventListener('mouseenter', () => {
                this.shadowRoot.querySelector('#tooltipAircoTemperature').classList.add('tooltip-show');
            });

            ac.addEventListener('mouseleave', () => {
                this.shadowRoot.querySelector('#tooltipAircoTemperature').classList.remove('tooltip-show');
            });

            ac.addEventListener('click', () => {
                const aircoEntity = this.config?.other?.thermostat_airco;

                if (aircoEntity) {
                    this._openMoreInfo(aircoEntity);
                }
            });
        }
        if (waterPipe) {
            waterPipe.addEventListener('mouseenter', () => {
                this.shadowRoot.querySelector('#tooltipWaterPipeTemperature').classList.add('tooltip-show');
            });

            waterPipe.addEventListener('mouseleave', () => {
                this.shadowRoot.querySelector('#tooltipWaterPipeTemperature').classList.remove('tooltip-show');
            });
        }
        if (hp1Delta) {
            hp1Delta.addEventListener('mouseenter', () => {
                this.shadowRoot.querySelector('#tooltipHp1DeltaTemperature').classList.add('tooltip-show');
            });

            hp1Delta.addEventListener('mouseleave', () => {
                this.shadowRoot.querySelector('#tooltipHp1DeltaTemperature').classList.remove('tooltip-show');
            });
        }
        if (hp2Delta) {
            hp2Delta.addEventListener('mouseenter', () => {
                this.shadowRoot.querySelector('#tooltipHp2DeltaTemperature').classList.add('tooltip-show');
            });

            hp2Delta.addEventListener('mouseleave', () => {
                this.shadowRoot.querySelector('#tooltipHp2DeltaTemperature').classList.remove('tooltip-show');
            });
        }
    }

    _openMoreInfo(entityId) {
        const event = new Event('hass-more-info', {
            bubbles: true,
            composed: true,
        });
        event.detail = { entityId };
        this.dispatchEvent(event);
    }

    render() {
        if (!this.isReady()) {
            return html`
              <ha-card>
                  <svg viewBox="0 0 1920 1920" preserveAspectRatio="xMidYMid meet">
                      <image href="${this._BASE_URL}/src_assets_images_houseallev2.png?v=${this._VERSION}" x="0" y="0" width="1920" height="1920" preserveAspectRatio="xMidYMid meet"/>
                      <image href="${this._BASE_URL}/src_assets_images_houseairco.png?v=${this._VERSION}" x="0" y="0" width="1920" height="1920" preserveAspectRatio="xMidYMid meet"/>
                      <image href="${this._BASE_URL}/src_assets_images_housesolarpanels.png?v=${this._VERSION}" x="0" y="0" width="1920" height="1920" preserveAspectRatio="xMidYMid meet"/>
                      <image href="${this._BASE_URL}/src_assets_images_housesolarcollector.png?v=${this._VERSION}" x="0" y="0" width="1920" height="1920" preserveAspectRatio="xMidYMid meet"/>
                      <image href="${this._BASE_URL}/src_assets_images_housebattery.png?v=${this._VERSION}" x="0" y="0" width="1920" height="1920" preserveAspectRatio="xMidYMid meet"/>
                  </svg>
              </ha-card>
            `;
        }

        return html`
      <ha-card>
          <svg viewBox="0 0 1920 1920" preserveAspectRatio="xMidYMid meet">
              ${!this.isAllElectric()
                 ? svg`<image href="${this._BASE_URL}/src_assets_images_housechimney.png?v=${this._VERSION}" x="0" y="0" width="1920" height="1920" preserveAspectRatio="xMidYMid meet"/>` : svg``
              }

              ${this.isAllElectric()
                  ? (this.isMonoHeatpump()
                      ? (this.getSystemVersion() === 'V2'
                          ? svg`<image href="${this._BASE_URL}/src_assets_images_houseallev2.png?v=${this._VERSION}" x="0" y="0" width="1920" height="1920" preserveAspectRatio="xMidYMid meet"/>`
                          : svg`<image href="${this._BASE_URL}/src_assets_images_houseallev1.png?v=${this._VERSION}" x="0" y="0" width="1920" height="1920" preserveAspectRatio="xMidYMid meet"/>`
                      )
                      : (this.getSystemVersion() === 'V2'
                          ? svg`<image href="${this._BASE_URL}/src_assets_images_houseallev2duo.png?v=${this._VERSION}" x="0" y="0" width="1920" height="1920" preserveAspectRatio="xMidYMid meet"/>`
                          : svg`<image href="${this._BASE_URL}/src_assets_images_houseallev1duo.png?v=${this._VERSION}" x="0" y="0" width="1920" height="1920" preserveAspectRatio="xMidYMid meet"/>`
                      )
                  )
                  : (this.isMonoHeatpump()
                      ? (this.getSystemVersion() === 'V2'
                          ? svg`<image href="${this._BASE_URL}/src_assets_images_househybridv2.png?v=${this._VERSION}" x="0" y="0" width="1920" height="1920" preserveAspectRatio="xMidYMid meet"/>`
                          : svg`<image href="${this._BASE_URL}/src_assets_images_househybridv1.png?v=${this._VERSION}" x="0" y="0" width="1920" height="1920" preserveAspectRatio="xMidYMid meet"/>`
                      )
                      : (this.getSystemVersion() === 'V2'
                          ? svg`<image href="${this._BASE_URL}/src_assets_images_househybridv2duo.png?v=${this._VERSION}" x="0" y="0" width="1920" height="1920" preserveAspectRatio="xMidYMid meet"/>`
                          : svg`<image href="${this._BASE_URL}/src_assets_images_househybridv1duo.png?v=${this._VERSION}" x="0" y="0" width="1920" height="1920" preserveAspectRatio="xMidYMid meet"/>`
                      )
                  )
              }

              ${this.hasAirco()
                  ? svg`<image href="${this._BASE_URL}/src_assets_images_houseairco.png?v=${this._VERSION}" x="0" y="0" width="1920" height="1920" preserveAspectRatio="xMidYMid meet"/>` : svg``
              }

              ${this.hasSolarPanels()
                  ? svg`<image href="${this._BASE_URL}/src_assets_images_housesolarpanels.png?v=${this._VERSION}" x="0" y="0" width="1920" height="1920" preserveAspectRatio="xMidYMid meet"/>` : svg``
              }

              ${this.hasSolarCollector()
                  ? svg`<image href="${this._BASE_URL}/src_assets_images_housesolarcollector.png?v=${this._VERSION}" x="0" y="0" width="1920" height="1920" preserveAspectRatio="xMidYMid meet"/>` : svg``
              }

              ${this.hasBattery()
                  ? svg`<image href="${this._BASE_URL}/src_assets_images_housebattery.png?v=${this._VERSION}" x="0" y="0" width="1920" height="1920" preserveAspectRatio="xMidYMid meet"/>` : svg``
              }

              ${this.hasHotWaterCylinder()
                  ? svg`<image href="${this._BASE_URL}/src_assets_images_houseboilercylinder.png?v=${this._VERSION}" x="0" y="0" width="1920" height="1920" preserveAspectRatio="xMidYMid meet"/>` : svg``
              }

              <defs>
                  <linearGradient id="waterGradientToLeft" x1="0%" y1="0%" x2="100%" y2="0%">
                      <stop offset="0%" style="stop-color:#FF8C00;stop-opacity:1">
                          <animate attributeName="offset" values="1.5;-0.5" dur="2s" repeatCount="indefinite" />
                      </stop>
                      <stop offset="25%" style="stop-color:#FF6B35;stop-opacity:1">
                          <animate attributeName="offset" values="1.75;-0.25" dur="2s" repeatCount="indefinite" />
                      </stop>
                      <stop offset="50%" style="stop-color:#FF4500;stop-opacity:1">
                          <animate attributeName="offset" values="2;0" dur="2s" repeatCount="indefinite" />
                      </stop>
                      <stop offset="75%" style="stop-color:#FF6B35;stop-opacity:1">
                          <animate attributeName="offset" values="2.25;0.25" dur="2s" repeatCount="indefinite" />
                      </stop>
                      <stop offset="100%" style="stop-color:#FF8C00;stop-opacity:1">
                          <animate attributeName="offset" values="2.5;0.5" dur="2s" repeatCount="indefinite" />
                      </stop>
                  </linearGradient>
                  <linearGradient id="waterGradientToRight" x1="0%" y1="0%" x2="100%" y2="0%">
                      <stop offset="0%" style="stop-color:#FF8C00;stop-opacity:1">
                          <animate attributeName="offset" values="-0.5;1.5" dur="2s" repeatCount="indefinite" />
                      </stop>
                      <stop offset="25%" style="stop-color:#FF6B35;stop-opacity:1">
                          <animate attributeName="offset" values="-0.25;1.75" dur="2s" repeatCount="indefinite" />
                      </stop>
                      <stop offset="50%" style="stop-color:#FF4500;stop-opacity:1">
                          <animate attributeName="offset" values="0;2" dur="2s" repeatCount="indefinite" />
                      </stop>
                      <stop offset="75%" style="stop-color:#FF6B35;stop-opacity:1">
                          <animate attributeName="offset" values="0.25;2.25" dur="2s" repeatCount="indefinite" />
                      </stop>
                      <stop offset="100%" style="stop-color:#FF8C00;stop-opacity:1">
                          <animate attributeName="offset" values="0.5;2.5" dur="2s" repeatCount="indefinite" />
                      </stop>
                  </linearGradient>
                  <linearGradient id="waterGradientUp" x1="0%" y1="100%" x2="0%" y2="0%">
                      <stop offset="0%" style="stop-color:#FF8C00;stop-opacity:1">
                          <animate attributeName="offset" values="-0.5;1.5" dur="2s" repeatCount="indefinite" />
                      </stop>
                      <stop offset="25%" style="stop-color:#FF6B35;stop-opacity:1">
                          <animate attributeName="offset" values="-0.25;1.75" dur="2s" repeatCount="indefinite" />
                      </stop>
                      <stop offset="50%" style="stop-color:#FF4500;stop-opacity:1">
                          <animate attributeName="offset" values="0;2" dur="2s" repeatCount="indefinite" />
                      </stop>
                      <stop offset="75%" style="stop-color:#FF6B35;stop-opacity:1">
                          <animate attributeName="offset" values="0.25;2.25" dur="2s" repeatCount="indefinite" />
                      </stop>
                      <stop offset="100%" style="stop-color:#FF8C00;stop-opacity:1">
                          <animate attributeName="offset" values="0.5;2.5" dur="2s" repeatCount="indefinite" />
                      </stop>
                  </linearGradient>
                  <linearGradient id="waterGradientDown" x1="0%" y1="100%" x2="0%" y2="0%">
                      <stop offset="0%" style="stop-color:#FF8C00;stop-opacity:1">
                          <animate attributeName="offset" values="1.5;-0.5" dur="2s" repeatCount="indefinite" />
                      </stop>
                      <stop offset="25%" style="stop-color:#FF6B35;stop-opacity:1">
                          <animate attributeName="offset" values="1.75;-0.25" dur="2s" repeatCount="indefinite" />
                      </stop>
                      <stop offset="50%" style="stop-color:#FF4500;stop-opacity:1">
                          <animate attributeName="offset" values="2;0" dur="2s" repeatCount="indefinite" />
                      </stop>
                      <stop offset="75%" style="stop-color:#FF6B35;stop-opacity:1">
                          <animate attributeName="offset" values="2.25;0.25" dur="2s" repeatCount="indefinite" />
                      </stop>
                      <stop offset="100%" style="stop-color:#FF8C00;stop-opacity:1">
                          <animate attributeName="offset" values="2.5;0.5" dur="2s" repeatCount="indefinite" />
                      </stop>
                  </linearGradient>

                  <clipPath id="outsidePipe">
                      <rect x="250" y="1245" width="181" height="100"></rect>
                      <rect x="555" y="1387" width="12" height="20"></rect>

                      ${this.isMonoHeatpump()
                          ? svg`<rect id="quatt.mono" x="431" y="1300" width="124" height="100"></rect>` : svg``
                      }
                  </clipPath>
                  <clipPath id="bottomPipe">
                      ${this.isHybrid()
                          ? svg`<rect id="quatt.hybrid" x="250" y="1175" width="181" height="100"></rect>`
                          : svg`<rect id="quatt.alle1" x="250" y="1175" width="51" height="100"></rect>
                                <rect id="quatt.alle2" x="378" y="1100" width="151" height="125"></rect>`
                      }
                  </clipPath>

                  <filter id="softGlow" x="-200%" y="-200%" width="400%" height="400%">
                      <feGaussianBlur stdDeviation="8" result="b"/>
                      <feMerge>
                          <feMergeNode in="b"/>
                          <feMergeNode in="SourceGraphic"/>
                      </feMerge>
                  </filter>
                  <linearGradient id="sweep" x1="0" y1="0" x2="1" y2="0" gradientUnits="objectBoundingBox">
                      <stop offset="0%" stop-color="#ffffff" stop-opacity="0" />
                      <stop offset="45%" stop-color="#ffffff" stop-opacity="0.9" />
                      <stop offset="55%" stop-color="#ffffff" stop-opacity="0.9" />
                      <stop offset="100%" stop-color="#ffffff" stop-opacity="0" />
                  </linearGradient>
                  <clipPath id="solarGlare">
                      ${this.hasSolarCollector()
                        && this.getSensorState('other.sun')?.state == 'above_horizon'
                          ? svg`<polygon points="684 1001,744 1093,945 990,887 902" style=" fill: blue; stroke:black;"/>`
                          : svg``
                      }

                      ${this.hasSolarPanels()
                        && this.getSensorState('other.solar_power')?.state >= 0.001
                          ? svg`<polygon points="1002 610,1110 762,1212 712,1103 560" style=" fill: blue; stroke:black;"/>
                                <polygon points="1117 553,1224 705,1315 657,1207 508" style=" fill: blue; stroke:black;"/>
                                <polygon points="1220 502,1327 650,1425 602,1317 453" style=" fill: blue; stroke:black;"/>
                                <polygon points="1331 446,1437 595,1528 547,1423 401" style=" fill: blue; stroke:black;"/>`
                          : svg``
                      }
                  </clipPath>

                  <filter id="smokeBlur">
                      <feGaussianBlur in="SourceGraphic" stdDeviation="8"/>
                  </filter>
              </defs>

              <!-- Sunshine -->
              <g clip-path="url(#solarGlare)" filter="url(#softGlow)">
                  <rect x="500" y="220" width="1200" height="900" fill="#7ad6ff" opacity="0.15">
                      <animate attributeName="opacity" values="0.08;0.18;0.10;0.18;0.08" dur="6s" repeatCount="indefinite"></animate>
                  </rect>
                  <rect id="sweepBar" x="100" y="0" width="300" height="1400" fill="url(#sweep)" opacity="0.6">
                      <animateTransform attributeName="transform" type="translate" from="100 0" to="1500 0" dur="5.5s" repeatCount="indefinite"></animateTransform>
                  </rect>
              </g>

              <g id="quatt.legend">
                  <rect x="50" y="300" width="300" height="330" fill="#1a1a1a" opacity="0.85" rx="20"/>

                  <!-- Title -->
                  <text x="70" y="345" font-family="Arial, sans-serif" font-size="32" font-weight="bold" fill="#ffffff">${this.config?.system_setup?.house_label}</text>

                  <!-- Heat -->
                  <text x="70" y="400" font-family="Arial, sans-serif" font-size="22" fill="#999999">Heat</text>
                  <text x="70" y="435" font-family="Arial, sans-serif" font-size="28" font-weight="bold" fill="#ffffff">
                      ${this.getSensorState('cic.total_power', {number: true, decimals: 2, scale: 1/1000})} kW
                  </text>

                  <!-- Electricity -->
                  <text x="70" y="480" font-family="Arial, sans-serif" font-size="22" fill="#999999">Electricity</text>
                  <text x="70" y="515" font-family="Arial, sans-serif" font-size="28" font-weight="bold" fill="#ffffff">
                      ${this.getSensorState('cic.total_powerinput', {number: true, decimals: 2, scale: 1/1000})} kW
                  </text>

                  <!-- Boiler -->
                  ${this.isHybrid()
                       ? svg`<text x="70" y="560" font-family="Arial, sans-serif" font-size="22" fill="#999999">Boiler</text>
                            ${(() => {
                              if (this.getSensorState('boiler.boiler_heating')?.state == 'on')
                                  return svg`<g id="quatt.cic.boilerIcon.flame">
                                                 <path d="M 80 595 Q 77 590, 77 585 Q 77 580, 80 577 Q 81 574, 80 571 Q 79 569, 80 567 Q 82 565, 83 567 Q 84 569, 83 571 Q 82 574, 83 577 Q 86 580, 86 585 Q 86 590, 83 595 Q 81.5 597, 80 595 Z" fill="#FF6B35" stroke="#FF4500" stroke-width="0.5"/>
                                                 <ellipse cx="81.5" cy="587" rx="2" ry="3" fill="#FFD700"/>
                                             </g>
                                             <text x="100" y="595" font-family="Arial, sans-serif" font-size="28" font-weight="bold" fill="#ffffff">
                                                 ${this.getSensorState('boiler.boiler_heating')?.state || 'Off'}
                                             </text>`
                                  return svg`<g id="quatt.cic.boilerIcon.euro" class="quatt-show">
                                                <circle cx="80" cy="585" r="11" fill="none" stroke="#FFA500" stroke-width="2"/>
                                                <path d="M 86 579 Q 82 577, 78 579 Q 74 581, 74 585 Q 74 589, 78 591 Q 82 593, 86 591" fill="none" stroke="#FFA500" stroke-width="2" stroke-linecap="round"/>
                                                <line x1="72" y1="583" x2="84" y2="583" stroke="#FFA500" stroke-width="2" stroke-linecap="round"/>
                                                <line x1="72" y1="587" x2="84" y2="587" stroke="#FFA500" stroke-width="2" stroke-linecap="round"/>
                                            </g>
                                             <text x="100" y="595" font-family="Arial, sans-serif" font-size="28" font-weight="bold" fill="#ffffff">
                                                 ${this.getSensorState('boiler.boiler_heating')?.state || 'Off'}
                                             </text>`
                          })()}`
                      : svg``
                  }

                  <!-- Shower -->
                  ${this.isAllElectric()
                      ? svg`<text x="70" y="560" font-family="Arial, sans-serif" font-size="22" fill="#999999">Shower time</text>
                            ${(() => {
                                if (this.getSensorState('heat_battery.heat_battery_domestic_hot_water_on')?.state == 'on')
                                  return svg`<g id="quatt.cic.showerIcon.down">
                                                 <path d="M 80 577 L 80 593 M 80 593 L 74 587 M 80 593 L 86 587" fill="none" stroke="#FF4444" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
                                             </g>
                                             <text x="100" y="595" font-family="Arial, sans-serif" font-size="28" font-weight="bold" fill="#ffffff">
                                                 ${this.getSensorState('heat_battery.heat_battery_shower_minutes_remaining', {number: true, decimals: 0})} min
                                             </text>`
                                if (this.getSensorState('heat_battery.heat_battery_charging')?.state == 'on')
                                  return svg`<g id="quatt.cic.showerIcon.up">
                                                <path d="M 80 593 L 80 577 M 80 577 L 74 583 M 80 577 L 86 583" fill="none" stroke="#44FF44" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
                                             </g>
                                             <text x="100" y="595" font-family="Arial, sans-serif" font-size="28" font-weight="bold" fill="#ffffff">
                                                 ${this.getSensorState('heat_battery.heat_battery_shower_minutes_remaining', {number: true, decimals: 0})} min
                                             </text>`

                                return svg`<text x="70" y="595" font-family="Arial, sans-serif" font-size="28" font-weight="bold" fill="#ffffff">
                                               ${this.getSensorState('heat_battery.heat_battery_shower_minutes_remaining', {number: true, decimals: 0})} min
                                           </text>`
                            })()}`
                      : svg``
                  }
              </g>

              <g clip-path="url(#outsidePipe)">
              ${(this.getSensorState('hp1.hp1_workingmode')?.state >= 1
                || this.getSensorState('hp2.hp2_workingmode')?.state >= 1)
                  ? svg`<path id="quatt.outsidePipe" d="M 274 1253 L 567 1400" stroke="url(#waterGradientToLeft)" stroke-width="8" fill="none" stroke-linecap="round"/>`
                  : svg``
              }
              </g>
              <g clip-path="url(#bottomPipe)">
                  ${(this.getSensorState('hp1.hp1_workingmode')?.state >= 1
                    || this.getSensorState('hp2.hp2_workingmode')?.state >= 1)
                      ? svg`<path id="quatt.bottomPipe" d="M 275 1250 L 404 1185" stroke="url(#waterGradientToRight)" stroke-width="8" fill="none" stroke-linecap="round"/>`
                      : svg``
                  }

                  ${this.isAllElectric()
                    && (this.getSensorState('hp1.hp1_workingmode')?.state >= 1
                        || this.getSensorState('hp2.hp2_workingmode')?.state >= 1)
                      ? svg`<path id="quatt.alle.bottomPipe" d="M 405 1185 L 406 1117" stroke="url(#waterGradientUp)" stroke-width="8" fill="none" stroke-linecap="round"/>`
                      : svg``
                  }

                  ${this.isAllElectric()
                    && this.getSensorState('cic.cic_central_heating_on')?.state == 'on'
                      ? svg`<path id="quatt.alle.radiatorPipe1" d="M 434 1121 L 435 1167" stroke="url(#waterGradientDown)" stroke-width="8" fill="none" stroke-linecap="round"/>
                            <path id="quatt.alle.radiatorPipe2" d="M 435 1167 L 495 1139" stroke="url(#waterGradientToRight)" stroke-width="8" fill="none" stroke-linecap="round"/>`
                      : svg``
                  }
              </g>

              ${this.getSensorState('hp1.hp1_workingmode')?.state >= 1
                  ? svg`<g id="quatt.hp1Flow">
                          <path class="fog-line" pathLength="100" style="animation-duration: 4.2s; animation-delay: 0s; stroke: #E8F4F8; stroke-width: 3;"
                                d="M 425 1415 Q 435 1408, 445 1415 Q 455 1422, 465 1415 Q 475 1408, 485 1415 Q 495 1422, 505 1415 Q 515 1408, 525 1415 Q 535 1422, 545 1415 Q 555 1408, 565 1415 Q 575 1422, 585 1415 Q 595 1408, 605 1415 Q 615 1422, 625 1415 Q 635 1408, 645 1415 Q 655 1422, 665 1415"/>
                          <path class="fog-line" pathLength="100" style="animation-duration: 3.8s; animation-delay: -1.2s; stroke: #D4E8F0; stroke-width: 4;"
                                d="M 435 1430 Q 445 1423, 455 1430 Q 465 1437, 475 1430 Q 485 1423, 495 1430 Q 505 1437, 515 1430 Q 525 1423, 535 1430 Q 545 1437, 555 1430 Q 565 1423, 575 1430 Q 585 1437, 595 1430 Q 605 1423, 615 1430 Q 625 1437, 635 1430 Q 645 1423, 655 1430 Q 665 1437, 675 1430"/>
                          <path class="fog-line" pathLength="100" style="animation-duration: 4.5s; animation-delay: -2.5s; stroke: #E0EDF5; stroke-width: 2.5;"
                                d="M 430 1445 Q 440 1438, 450 1445 Q 460 1452, 470 1445 Q 480 1438, 490 1445 Q 500 1452, 510 1445 Q 520 1438, 530 1445 Q 540 1452, 550 1445 Q 560 1438, 570 1445 Q 580 1452, 590 1445 Q 600 1438, 610 1445 Q 620 1452, 630 1445 Q 640 1438, 650 1445 Q 660 1452, 670 1445"/>
                          <path class="fog-line" pathLength="100" style="animation-duration: 4.0s; animation-delay: -3.7s; stroke: #DCE9F2; stroke-width: 3;"
                                d="M 440 1460 Q 450 1453, 460 1460 Q 470 1467, 480 1460 Q 490 1453, 500 1460 Q 510 1467, 520 1460 Q 530 1453, 540 1460 Q 550 1467, 560 1460 Q 570 1453, 580 1460 Q 590 1467, 600 1460 Q 610 1453, 620 1460 Q 630 1467, 640 1460 Q 650 1453, 660 1460 Q 670 1467, 680 1460"/>
                        </g>`
                  : svg``
              }

              ${this.getSensorState('hp2.hp2_workingmode')?.state >= 1
                  ? svg`<g id="quatt.hp2Flow">
                          <path class="fog-line" pathLength="100" style="animation-duration: 4.3s; animation-delay: -0.5s; stroke: #E8F4F8; stroke-width: 3;"
                                d="M 295 1350 Q 305 1343, 315 1350 Q 325 1357, 335 1350 Q 345 1343, 355 1350 Q 365 1357, 375 1350 Q 385 1343, 395 1350 Q 405 1357, 415 1350 Q 425 1343, 435 1350 Q 445 1357, 455 1350 Q 465 1343, 475 1350 Q 485 1357, 495 1350 Q 505 1343, 515 1350 Q 525 1357, 535 1350"/>
                          <path class="fog-line" pathLength="100" style="animation-duration: 3.9s; animation-delay: -1.8s; stroke: #D4E8F0; stroke-width: 4;"
                                d="M 305 1365 Q 315 1358, 325 1365 Q 335 1372, 345 1365 Q 355 1358, 365 1365 Q 375 1372, 385 1365 Q 395 1358, 405 1365 Q 415 1372, 425 1365 Q 435 1358, 445 1365 Q 455 1372, 465 1365 Q 475 1358, 485 1365 Q 495 1372, 505 1365 Q 515 1358, 525 1365 Q 535 1372, 545 1365"/>
                          <path class="fog-line" pathLength="100" style="animation-duration: 4.6s; animation-delay: -3.1s; stroke: #E0EDF5; stroke-width: 2.5;"
                                d="M 300 1380 Q 310 1373, 320 1380 Q 330 1387, 340 1380 Q 350 1373, 360 1380 Q 370 1387, 380 1380 Q 390 1373, 400 1380 Q 410 1387, 420 1380 Q 430 1373, 440 1380 Q 450 1387, 460 1380 Q 470 1373, 480 1380 Q 490 1387, 500 1380 Q 510 1373, 520 1380 Q 530 1387, 540 1380"/>
                          <path class="fog-line" pathLength="100" style="animation-duration: 4.1s; animation-delay: -2.2s; stroke: #DCE9F2; stroke-width: 3;"
                                d="M 310 1395 Q 320 1388, 330 1395 Q 340 1402, 350 1395 Q 360 1388, 370 1395 Q 380 1402, 390 1395 Q 400 1388, 410 1395 Q 420 1402, 430 1395 Q 440 1388, 450 1395 Q 460 1402, 470 1395 Q 480 1388, 490 1395 Q 500 1402, 510 1395 Q 520 1388, 530 1395 Q 540 1402, 550 1395"/>
                        </g>`
                  : svg``
              }

              ${(this.isAllElectric() && this.getSensorState('cic.cic_central_heating_on')?.state == 'on')
                || (this.isHybrid() && (this.getSensorState('hp1.hp1_workingmode')?.state >= 1 || this.getSensorState('hp2.hp2_workingmode')?.state >= 1))
                  ? svg`<g id="quatt.radiatorHeat" transform="${this.isAllElectric() ? 'translate(100,-40)' : ''}">
                          <path class="radiator-heat-line" pathLength="100" transform="translate(0,-12)"
                                style="animation-duration:6.77s; animation-delay:-2.13s"
                                d="M415 1186.1 C427 1176.1,403 1168.1,415 1158.1 C427 1148.1,403 1140.1,415 1130.1 C427 1120.1,403 1112.1,415 1102.1 C427 1092.1,403 1084.1,415 1074.1 C427 1064.1,403 1056.1,415 1046.1 C427 1036.1,403 1030.1,415 1025.1"/>
                          <path class="radiator-heat-line" pathLength="100" transform="translate(0,-28)"
                                style="animation-duration:7.09s; animation-delay:-5.04s"
                                d="M425 1181.3 C437 1171.3,413 1163.3,425 1153.3 C437 1143.3,413 1135.3,425 1125.3 C437 1115.3,413 1107.3,425 1097.3 C437 1087.3,413 1079.3,425 1069.3 C437 1059.3,413 1051.3,425 1041.3 C437 1031.3,413 1025.3,425 1020.3"/>
                          <path class="radiator-heat-line" pathLength="100" transform="translate(0,-40)"
                                style="animation-duration:6.61s; animation-delay:-0.41s"
                                d="M435 1176.4 C447 1166.4,423 1158.4,435 1148.4 C447 1138.4,423 1130.4,435 1120.4 C447 1110.4,423 1102.4,435 1092.4 C447 1082.4,423 1074.4,435 1064.4 C447 1054.4,423 1046.4,435 1036.4 C447 1026.4,423 1020.4,435 1015.4"/>
                          <path class="radiator-heat-line" pathLength="100" transform="translate(0,-16)"
                                style="animation-duration:7.21s; animation-delay:-3.57s"
                                d="M445 1171.5 C457 1161.5,433 1153.5,445 1143.5 C457 1133.5,433 1125.5,445 1115.5 C457 1105.5,433 1097.5,445 1087.5 C457 1077.5,433 1069.5,445 1059.5 C457 1049.5,433 1041.5,445 1031.5 C457 1021.5,433 1015.5,445 1010.5"/>
                          <path class="radiator-heat-line" pathLength="100" transform="translate(0,-32)"
                                style="animation-duration:6.47s; animation-delay:-1.89s"
                                d="M455 1161.8 C477 1151.8,453 1143.8,465 1133.8 C477 1123.8,453 1115.8,465 1105.8 C477 1095.8,453 1087.8,465 1077.8 C477 1067.8,453 1059.8,465 1049.8 C477 1039.8,453 1031.8,465 1021.8 C477 1011.8,453 1005.8,465 1000.8"/>
                          <path class="radiator-heat-line" pathLength="100" transform="translate(0,-10)"
                                style="animation-duration:6.93s; animation-delay:-6.28s"
                                d="M465 1166.6 C467 1156.6,443 1148.6,455 1138.6 C467 1128.6,443 1120.6,455 1110.6 C467 1100.6,443 1092.6,455 1082.6 C467 1072.6,443 1064.6,455 1054.6 C467 1044.6,443 1036.6,455 1026.6 C467 1016.6,443 1010.6,455 1005.6"/>
                          <path class="radiator-heat-line" pathLength="100" transform="translate(0,-24)"
                                style="animation-duration:7.37s; animation-delay:-4.46s"
                                d="M474 1157.4 C486 1147.4,462 1139.4,474 1129.4 C486 1119.4,462 1111.4,474 1101.4 C486 1091.4,462 1083.4,474 1073.4 C486 1035.4,462 1027.4,474 1017.4 C486 1007.4,462 1002.4,474  997.4"/>
                      </g>`
                  : svg``
              }

              ${this.hasAirco()
                  && this.getSensorState('other.thermostat_airco')?.state !== 'off'
                  ? svg`<g id="quatt.acFlow" transform="translate(380, 15)">
                          <path class="fog-line-reverse" pathLength="100"
                                style="animation-duration: 4.2s; animation-delay: 0s; stroke-width: 3;
                                    stroke:  ${(() => {
                                          switch (this.getSensorState('other.thermostat_airco')?.state) {
                                              case 'heat':
                                                  return '#DCE9F2';
                                              default:
                                                  return '#ff8a00';
                                          }
                                      })()};"
                                d="M 425 1415 Q 435 1408, 445 1415 Q 455 1422, 465 1415 Q 475 1408, 485 1415 Q 495 1422, 505 1415 Q 515 1408, 525 1415 Q 535 1422, 545 1415 Q 555 1408, 565 1415 Q 575 1422, 585 1415 Q 595 1408, 605 1415 Q 615 1422, 625 1415 Q 635 1408, 645 1415 Q 655 1422, 665 1415"/>
                          <path class="fog-line-reverse" pathLength="100"
                                style="animation-duration: 3.8s; animation-delay: -1.2s; stroke-width: 4;
                                    stroke:  ${(() => {
                                          switch (this.getSensorState('other.thermostat_airco')?.state) {
                                              case 'heat':
                                                  return '#DCE9F2';
                                              default:
                                                  return '#ff8a00';
                                          }
                                      })()};"
                                d="M 435 1430 Q 445 1423, 455 1430 Q 465 1437, 475 1430 Q 485 1423, 495 1430 Q 505 1437, 515 1430 Q 525 1423, 535 1430 Q 545 1437, 555 1430 Q 565 1423, 575 1430 Q 585 1437, 595 1430 Q 605 1423, 615 1430 Q 625 1437, 635 1430 Q 645 1423, 655 1430 Q 665 1437, 675 1430"/>
                          <path class="fog-line-reverse" pathLength="100"
                                style="animation-duration: 4.5s; animation-delay: -2.5s; stroke-width: 2.5;
                                    stroke:  ${(() => {
                                          switch (this.getSensorState('other.thermostat_airco')?.state) {
                                              case 'heat':
                                                  return '#DCE9F2';
                                              default:
                                                  return '#ff8a00';
                                          }
                                      })()};"
                                d="M 430 1445 Q 440 1438, 450 1445 Q 460 1452, 470 1445 Q 480 1438, 490 1445 Q 500 1452, 510 1445 Q 520 1438, 530 1445 Q 540 1452, 550 1445 Q 560 1438, 570 1445 Q 580 1452, 590 1445 Q 600 1438, 610 1445 Q 620 1452, 630 1445 Q 640 1438, 650 1445 Q 660 1452, 670 1445"/>
                          <path class="fog-line-reverse" pathLength="100"
                                style="animation-duration: 4.0s; animation-delay: -3.7s; stroke-width: 3;
                                    stroke:  ${(() => {
                                          switch (this.getSensorState('other.thermostat_airco')?.state) {
                                              case 'heat':
                                                  return '#DCE9F2';
                                              default:
                                                  return '#ff8a00';
                                          }
                                      })()};"
                                d="M 440 1460 Q 450 1453, 460 1460 Q 470 1467, 480 1460 Q 490 1453, 500 1460 Q 510 1467, 520 1460 Q 530 1453, 540 1460 Q 550 1467, 560 1460 Q 570 1453, 580 1460 Q 590 1467, 600 1460 Q 610 1453, 620 1460 Q 630 1467, 640 1460 Q 650 1453, 660 1460 Q 670 1467, 680 1460"/>
                      </g>
                      <g id="quatt.acHeat" class="quatt-show" transform="translate(420, -70) rotate(67.5, 545, 945)">
                          <path class="fog-line-reverse" pathLength="100"
                                style="animation-duration: 4.2s; animation-delay: 0s; stroke-width: 3;
                                    stroke:  ${(() => {
                                          switch (this.getSensorState('other.thermostat_airco')?.state) {
                                              case 'heat':
                                                  return '#ff8a00';
                                              default:
                                                  return '#DCE9F2';
                                          }
                                      })()};"
                                d="M 425 1415 Q 435 1408, 445 1415 Q 455 1422, 465 1415 Q 475 1408, 485 1415 Q 495 1422, 505 1415 Q 515 1408, 525 1415 Q 535 1422, 545 1415 Q 555 1408, 565 1415 Q 575 1422, 585 1415 Q 595 1408, 605 1415 Q 615 1422, 625 1415 Q 635 1408, 645 1415 Q 655 1422, 665 1415"/>
                          <path class="fog-line-reverse" pathLength="100"
                                style="animation-duration: 3.8s; animation-delay: -1.2s; stroke-width: 4;
                                    stroke:  ${(() => {
                                          switch (this.getSensorState('other.thermostat_airco')?.state) {
                                              case 'heat':
                                                  return '#ff8a00';
                                              default:
                                                  return '#DCE9F2';
                                          }
                                      })()};"
                                d="M 435 1430 Q 445 1423, 455 1430 Q 465 1437, 475 1430 Q 485 1423, 495 1430 Q 505 1437, 515 1430 Q 525 1423, 535 1430 Q 545 1437, 555 1430 Q 565 1423, 575 1430 Q 585 1437, 595 1430 Q 605 1423, 615 1430 Q 625 1437, 635 1430 Q 645 1423, 655 1430 Q 665 1437, 675 1430"/>
                          <path class="fog-line-reverse" pathLength="100"
                                style="animation-duration: 4.5s; animation-delay: -2.5s; stroke-width: 2.5;
                                    stroke:  ${(() => {
                                          switch (this.getSensorState('other.thermostat_airco')?.state) {
                                              case 'heat':
                                                  return '#ff8a00';
                                              default:
                                                  return '#DCE9F2';
                                          }
                                      })()};"
                                d="M 430 1445 Q 440 1438, 450 1445 Q 460 1452, 470 1445 Q 480 1438, 490 1445 Q 500 1452, 510 1445 Q 520 1438, 530 1445 Q 540 1452, 550 1445 Q 560 1438, 570 1445 Q 580 1452, 590 1445 Q 600 1438, 610 1445 Q 620 1452, 630 1445 Q 640 1438, 650 1445 Q 660 1452, 670 1445"/>
                          <path class="fog-line-reverse" pathLength="100"
                                style="animation-duration: 4.0s; animation-delay: -3.7s; stroke-width: 3;
                                    stroke:  ${(() => {
                                          switch (this.getSensorState('other.thermostat_airco')?.state) {
                                              case 'heat':
                                                  return '#ff8a00';
                                              default:
                                                  return '#DCE9F2';
                                          }
                                      })()};"
                                d="M 440 1460 Q 450 1453, 460 1460 Q 470 1467, 480 1460 Q 490 1453, 500 1460 Q 510 1467, 520 1460 Q 530 1453, 540 1460 Q 550 1467, 560 1460 Q 570 1453, 580 1460 Q 590 1467, 600 1460 Q 610 1453, 620 1460 Q 630 1467, 640 1460 Q 650 1453, 660 1460 Q 670 1467, 680 1460"/>
                      </g>` : svg``
              }

              ${this.isHybrid()
                && this.getSensorState('boiler.boiler_heating')?.state == 'on'
                  ? svg`<g id="quatt.chimneyPipe">
                          <path d="M 347 1125 L 348 1205" stroke="url(#waterGradientDown)" stroke-width="8" fill="none" stroke-linecap="round"/>
                      </g>
                      <g id="quatt.chimneySmoke">
                          <ellipse cx="400" cy="675" rx="12" ry="15" fill="#6B6B6B" filter="url(#smokeBlur)">
                              <animate attributeName="cy" values="675;555;435" dur="4s" repeatCount="indefinite"/>
                              <animate attributeName="opacity" values="0.8;0.5;0" dur="4s" repeatCount="indefinite"/>
                              <animate attributeName="rx" values="12;17;22" dur="4s" repeatCount="indefinite"/>
                              <animate attributeName="ry" values="15;21;27" dur="4s" repeatCount="indefinite"/>
                          </ellipse>
                          <ellipse cx="408" cy="670" rx="14" ry="16" fill="#7A7A7A" filter="url(#smokeBlur)">
                              <animate attributeName="cy" values="670;550;430" dur="4s" begin="0.8s" repeatCount="indefinite"/>
                              <animate attributeName="opacity" values="0.8;0.5;0" dur="4s" begin="0.8s" repeatCount="indefinite"/>
                              <animate attributeName="rx" values="14;19;24" dur="4s" begin="0.8s" repeatCount="indefinite"/>
                              <animate attributeName="ry" values="16;22;28" dur="4s" begin="0.8s" repeatCount="indefinite"/>
                          </ellipse>
                          <ellipse cx="395" cy="680" rx="13" ry="14" fill="#656565" filter="url(#smokeBlur)">
                              <animate attributeName="cy" values="680;560;440" dur="4s" begin="1.6s" repeatCount="indefinite"/>
                              <animate attributeName="opacity" values="0.8;0.5;0" dur="4s" begin="1.6s" repeatCount="indefinite"/>
                              <animate attributeName="rx" values="13;18;23" dur="4s" begin="1.6s" repeatCount="indefinite"/>
                              <animate attributeName="ry" values="14;20;26" dur="4s" begin="1.6s" repeatCount="indefinite"/>
                          </ellipse>
                          <ellipse cx="403" cy="673" rx="15" ry="17" fill="#707070" filter="url(#smokeBlur)">
                              <animate attributeName="cy" values="673;553;433" dur="4s" begin="2.4s" repeatCount="indefinite"/>
                              <animate attributeName="opacity" values="0.8;0.5;0" dur="4s" begin="2.4s" repeatCount="indefinite"/>
                              <animate attributeName="rx" values="15;20;25" dur="4s" begin="2.4s" repeatCount="indefinite"/>
                              <animate attributeName="ry" values="17;23;29" dur="4s" begin="2.4s" repeatCount="indefinite"/>
                          </ellipse>
                          <ellipse cx="397" cy="677" rx="11" ry="13" fill="#6F6F6F" filter="url(#smokeBlur)">
                              <animate attributeName="cy" values="677;557;437" dur="4s" begin="3.2s" repeatCount="indefinite"/>
                              <animate attributeName="opacity" values="0.8;0.5;0" dur="4s" begin="3.2s" repeatCount="indefinite"/>
                              <animate attributeName="rx" values="11;16;21" dur="4s" begin="3.2s" repeatCount="indefinite"/>
                              <animate attributeName="ry" values="13;19;25" dur="4s" begin="3.2s" repeatCount="indefinite"/>
                          </ellipse>
                      </g>`
                  : svg``
              }

              ${this.isAllElectric()
                && this.getSensorState('heat_battery.heat_battery_domestic_hot_water_on')?.state == 'on'
                  ? svg`<g id="quatt.waterPipe">
                        <path d="M 421 1119 L 422 1186" stroke="url(#waterGradientDown)" stroke-width="5" fill="none" stroke-linecap="round"/>
                    </g>
                    <g id="quatt.shower">
                        <g id="showerWater" transform="translate(620, 880)">
                            <ellipse class="water-droplet" cx="20" cy="0" rx="3" ry="6" fill="#4DB8FF" opacity="0.7"/>
                            <ellipse class="water-droplet" cx="35" cy="0" rx="2.5" ry="5" fill="#6EC9FF" opacity="0.7"/>
                            <ellipse class="water-droplet" cx="50" cy="0" rx="3" ry="6" fill="#4DB8FF" opacity="0.7"/>
                            <ellipse class="water-droplet" cx="65" cy="0" rx="2.5" ry="5" fill="#6EC9FF" opacity="0.7"/>
                            <ellipse class="water-droplet" cx="80" cy="0" rx="3" ry="6" fill="#4DB8FF" opacity="0.7"/>
                        </g>
                    </g>`
                    : svg``
              }

              ${this.isAllElectric()
                && this.getSensorState('heat_battery.heat_battery_charging')?.state == 'on'
                  ? svg`<g id="quatt.boilerSteam">
                        <circle class="steam-ring" cx="400" cy="993" r="8" fill="none" stroke="#E8F4F8" stroke-width="2" opacity="0"/>
                        <circle class="steam-ring" cx="400" cy="993" r="8" fill="none" stroke="#D4E8F0" stroke-width="2" opacity="0"/>
                        <circle class="steam-ring" cx="400" cy="993" r="8" fill="none" stroke="#E8F4F8" stroke-width="2" opacity="0"/>
                        <circle class="steam-ring" cx="400" cy="993" r="8" fill="none" stroke="#D4E8F0" stroke-width="2" opacity="0"/>
                        <circle class="steam-ring" cx="400" cy="993" r="8" fill="none" stroke="#E8F4F8" stroke-width="2" opacity="0"/>
                    </g>`
                    : svg``
              }

              ${this.isAllElectric() || this.hasHotWaterCylinder()
                    ? svg`<g id="quatt.waterTankIndicator">
                          <defs>
                              ${this.isAllElectric()
                                ? svg`<linearGradient id="tankWaterGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                                      <stop id="gradientStop1" offset="0%" style="stop-color:#FF4444;stop-opacity:0.5"/>
                                      <stop id="gradientStop2" offset="${Math.max(0, this.getSensorState('heat_battery.heat_battery_percentage', {number: true, asString: false, decimals: 1, fallback: 0}) - 12.5)} %" style="stop-color:#FF4444;stop-opacity:0.5"/>
                                      <stop id="gradientStop3" offset="${Math.min(100, this.getSensorState('heat_battery.heat_battery_percentage', {number: true, asString: false, decimals: 1, fallback: 0}) + 12.5)} %" style="stop-color:#0066FF;stop-opacity:0.5"/>
                                      <stop id="gradientStop4" offset="100%" style="stop-color:#0066FF;stop-opacity:0.5"/>
                                    </linearGradient>`
                                : svg``
                              }

                              <!-- Inner shadow for depth -->
                              <filter id="waterDepth" x="-50%" y="-50%" width="200%" height="200%">
                                  <feGaussianBlur in="SourceAlpha" stdDeviation="3"/>
                                  <feOffset dx="0" dy="2" result="offsetblur"/>
                                  <feComponentTransfer>
                                      <feFuncA type="linear" slope="0.3"/>
                                  </feComponentTransfer>
                                  <feMerge>
                                      <feMergeNode/>
                                      <feMergeNode in="SourceGraphic"/>
                                  </feMerge>
                              </filter>

                              <!-- Glossy highlight effect -->
                              <linearGradient id="waterGloss" x1="0%" y1="0%" x2="100%" y2="0%">
                                  <stop offset="0%" style="stop-color:#ffffff;stop-opacity:0"/>
                                  <stop offset="30%" style="stop-color:#ffffff;stop-opacity:0.15"/>
                                  <stop offset="70%" style="stop-color:#ffffff;stop-opacity:0.15"/>
                                  <stop offset="100%" style="stop-color:#ffffff;stop-opacity:0"/>
                              </linearGradient>
                          </defs>

                          <!-- Main water fill -->
                          ${this.isAllElectric()
                            ? svg`<rect x="305" y="1070" width="70" height="195" fill="url(#tankWaterGradient)" rx="28" filter="url(#waterDepth)"/>`
                            : svg`<rect x="508" y="990" width="79" height="165"
                                        fill="${(() => {switch (true) {
                                              case ( 0 >= (this.getSensorState('other.hot_water_cylinder_temperature', {number: true, asString: false, fallback: 0}))):
                                                  return '#0066FF';
                                              case (18 >= (this.getSensorState('other.hot_water_cylinder_temperature', {number: true, asString: false, fallback: 0}))):
                                                  return '#2461E4';
                                              case (25 >= (this.getSensorState('other.hot_water_cylinder_temperature', {number: true, asString: false, fallback: 0}))):
                                                  return '#495CCA';
                                              case (32 >= (this.getSensorState('other.hot_water_cylinder_temperature', {number: true, asString: false, fallback: 0}))):
                                                  return '#6D57AF';
                                              case (39 >= (this.getSensorState('other.hot_water_cylinder_temperature', {number: true, asString: false, fallback: 0}))):
                                                  return '#925394';
                                              case (46 >= (this.getSensorState('other.hot_water_cylinder_temperature', {number: true, asString: false, fallback: 0}))):
                                                  return '#B64E79';
                                              case (53 >= (this.getSensorState('other.hot_water_cylinder_temperature', {number: true, asString: false, fallback: 0}))):
                                                  return '#DB495F';
                                              case (60 >= (this.getSensorState('other.hot_water_cylinder_temperature', {number: true, asString: false, fallback: 0}))):
                                                  return '#FF4444';
                                        }})()}"
                                        opacity="0.5"
                                        rx="28" filter="url(#waterDepth)"/>`
                          }

                          <!-- Glossy highlight overlay -->
                          ${this.isAllElectric()
                            ? svg`<rect x="310" y="1075" width="25" height="180" fill="url(#waterGloss)" rx="20" opacity="0.6"/>`
                            : svg`<rect x="513" y="995" width="28" height="150" fill="url(#waterGloss)" rx="20" opacity="0.6"/>`
                          }

                          <!-- Subtle shine on edges -->
                          ${this.isAllElectric()
                            ? svg`<rect x="305" y="1070" width="70" height="195" fill="none" stroke="rgba(255,255,255,0.2)" stroke-width="1" rx="28"/>`
                            : svg`<rect x="508" y="990" width="79" height="165" fill="none" stroke="rgba(255,255,255,0.2)" stroke-width="1" rx="28"/>`
                          }

                          <!-- Percentage text -->
                          <text
                            x="${(() => this.isAllElectric() ? '340' : '547')()}"
                            y="${(() => this.isAllElectric() ? '1172' : '1080')()}"
                            id="tankPercentage" text-anchor="middle" font-size="24" font-family="Arial, sans-serif" font-weight="bold" fill="#ffffff">
                              ${(() => this.isAllElectric()
                                  ? this.getSensorState('heat_battery.heat_battery_percentage', {number: true, decimals: 0})+' %'
                                  : this.getSensorState('other.hot_water_cylinder_temperature', {number: true, decimals: 0})+' °C'
                                )()
                              }
                          </text>
                      </g>`
                      : svg``
              }

              ${this.hasSolarPanels()
                  ? svg`<g id="solarPower" transform="translate(350, 230) rotate(-26.5, 545, 945)">
                            <rect x="1100" y="675" width="140" height="40" fill="#1a1a1a" opacity="0.8" rx="5"/>
                            <text x="1105" y="690" font-size="14" font-family="Arial" fill="#999999">Solar</text>
                            <text id="temp.solarPower" x="1170" y="708"
                                  text-anchor="middle"
                                  font-size="18"
                                  font-family="Arial, sans-serif"
                                  font-weight="bold"
                                  fill="#ffffff">
                              ${this.getSensorState('other.solar_power', {number: true, decimals: this.getSensorState('other.solar_power', {attribute: 'unit_of_measurement'}) == 'kW' ? 3 : 0})}
                              ${this.getSensorState('other.solar_power', {attribute: 'unit_of_measurement'})}
                            </text>
                        </g>`
                  : svg``
                }

              <!-- Temperature displays -->
              <g id="quatt.temperatures" class="quatt-show">
                  <g id="waterPipeTemperature">
                      <rect x="300" y="1275" width="140" height="40" fill="#1a1a1a" opacity="0.8" rx="5"/>
                      <text x="305" y="1290" font-size="14" font-family="Arial" fill="#999999">Pipe</text>
                      <text id="temp.waterPipe" x="370" y="1308"
                            text-anchor="middle"
                            font-size="18"
                            font-family="Arial, sans-serif"
                            font-weight="bold"
                            fill="#ffffff">
                          ${this.getSensorState('flowmeter.flowmeter_temperature', {number: true, decimals: 1})} °C
                      </text>
                  </g>
                  <g id="roomTemperature" style="cursor: pointer;">
                      <rect x="550" y="1200" width="140" height="40" fill="#1a1a1a" opacity="0.8" rx="5"/>
                      <text x="555" y="1215" font-size="14" font-family="Arial" fill="#999999">Room</text>
                      <text id="temp.room" x="620" y="1233"
                            text-anchor="middle"
                            font-size="18"
                            font-family="Arial, sans-serif"
                            font-weight="bold"
                            fill="#ffffff">
                          ${this.getSensorState('thermostat.thermostat_room_temperature', {number: true, decimals: 1})} °C
                      </text>
                  </g>
                  ${this.hasAirco()
                    ? svg`<g id="aircoTemperature" style="cursor: pointer;">
                          <rect x="350" y="875" width="140" height="40" fill="#1a1a1a" opacity="0.8" rx="5"/>
                          <text x="355" y="890" font-size="14" font-family="Arial" fill="#999999">Airco</text>
                          <text id="temp.airco" x="420" y="908"
                                text-anchor="middle"
                                font-size="18"
                                font-family="Arial, sans-serif"
                                font-weight="bold"
                                fill="#ffffff">
                              ${this.getSensorState('other.thermostat_airco', {number: true, decimals: 1, attribute: 'current_temperature'})} °C
                          </text>
                      </g>`
                    : svg``
                  }
                  ${this.hasBattery()
                    ? svg`<g id="homeBatterySOC">
                          <rect x="930" y="740" width="140" height="40" fill="#1a1a1a" opacity="0.8" rx="5"/>
                          <text x="935" y="755" font-size="14" font-family="Arial" fill="#999999">Battery</text>
                          <text id="temp.homebatterysoc" x="1000" y="773"
                                text-anchor="middle"
                                font-size="18"
                                font-family="Arial, sans-serif"
                                font-weight="bold"
                                fill="#ffffff">
                              ${this.getSensorState('other.home_battery_soc', {number: true, decimals: 0})} %
                          </text>
                      </g>`
                    : svg``
                  }
                  <g id="outsideTemperature">
                      <rect x="560" y="1545" width="140" height="40" fill="#1a1a1a" opacity="0.8" rx="5"/>
                      <text x="565" y="1560" font-size="14" font-family="Arial" fill="#999999">Outside</text>
                      <text id="temp.outside" x="630" y="1578"
                            text-anchor="middle"
                            font-size="18"
                            font-family="Arial, sans-serif"
                            font-weight="bold"
                            fill="#ffffff">
                          ${this.getSensorState('hp1.hp1_temperatureoutside', {number: true, decimals: 1})} °C
                      </text>
                  </g>
                  <g id="hp1DeltaTemperature">
                      <rect x="560" y="1500" width="140" height="40" fill="#1a1a1a" opacity="0.8" rx="5"/>
                      <text x="565" y="1515" font-size="14" font-family="Arial" fill="#999999">HP1 Δ</text>
                      <text id="temp.hp1.delta" x="630" y="1533"
                            text-anchor="middle"
                            font-size="18"
                            font-family="Arial, sans-serif"
                            font-weight="bold"
                            fill="#ffffff">
                          ${this.getSensorState('hp1.hp1_workingmode')?.state >= 1
                                  ? this.getSensorState('hp1.hp1_waterdelta', {number: true, decimals: 1})+' °C'
                                  : 'Off'}
                      </text>
                  </g>

                  ${this.isDuoHeatpump()
                      ? svg`<g id="hp2DeltaTemperature">
                              <rect x="420" y="1435" width="140" height="40" fill="#1a1a1a" opacity="0.8" rx="5"/>
                              <text x="425" y="1450" font-size="14" font-family="Arial" fill="#999999">HP2 Δ</text>
                              <text id="temp.hp2.delta" x="490" y="1468"
                                    text-anchor="middle"
                                    font-size="18"
                                    font-family="Arial, sans-serif"
                                    font-weight="bold"
                                    fill="#ffffff">
                          ${this.getSensorState('hp2.hp2_workingmode')?.state >= 1
                                    ? this.getSensorState('hp2.hp2_waterdelta', {number: true, decimals: 1})+' °C'
                                    : 'Off'}
                              </text>
                          </g>`
                      : svg``
                  }

                  <g id="tooltipTankPercentage" transform="translate(80, -108)">
                      <rect x="290" y="1155" width="400" height="200" fill="#2d2d2d" opacity="0.95" rx="8" stroke="#4a4a4a" stroke-width="2"/>
                      <text x="305" y="1190" font-size="16" font-family="Arial, sans-serif" fill="#999999">Charging:</text>
                      <text x="660" y="1190" font-size="16" font-family="Arial, sans-serif" font-weight="bold" fill="#ffffff" text-anchor="end">${this.getSensorState('heat_battery.heat_battery_charging')?.state}</text>
                      <text x="305" y="1225" font-size="16" font-family="Arial, sans-serif" fill="#999999">Top temperature:</text>
                      <text x="660" y="1225" font-size="16" font-family="Arial, sans-serif" font-weight="bold" fill="#ffffff" text-anchor="end">${this.getSensorState('heat_battery.heat_battery_top_temperature', {number: true, decimals: 0})} °C</text>
                      <text x="305" y="1260" font-size="16" font-family="Arial, sans-serif" fill="#999999">Middle temperature:</text>
                      <text x="660" y="1260" font-size="16" font-family="Arial, sans-serif" font-weight="bold" fill="#ffffff" text-anchor="end">${this.getSensorState('heat_battery.heat_battery_middle_temperature', {number: true, decimals: 0})} °C</text>
                      <text x="305" y="1295" font-size="16" font-family="Arial, sans-serif" fill="#999999">Bottom temperature:</text>
                      <text x="660" y="1295" font-size="16" font-family="Arial, sans-serif" font-weight="bold" fill="#ffffff" text-anchor="end">${this.getSensorState('heat_battery.heat_battery_bottom_temperature', {number: true, decimals: 0})} °C</text>
                      <text x="305" y="1330" font-size="16" font-family="Arial, sans-serif" fill="#999999">Shower minutes remaining:</text>
                      <text x="660" y="1330" font-size="16" font-family="Arial, sans-serif" font-weight="bold" fill="#ffffff" text-anchor="end">${this.getSensorState('heat_battery.heat_battery_shower_minutes_remaining', {number: true, decimals: 0})}</text>
                  </g>
                  <g id="tooltipWaterPipeTemperature" transform="translate(55, -68)">
                      <rect x="370" y="1295" width="400" height="95" fill="#2d2d2d" opacity="0.95" rx="8" stroke="#4a4a4a" stroke-width="2"/>
                      <text x="385" y="1330" font-size="16" font-family="Arial, sans-serif" fill="#999999">Flowrate:</text>
                      <text x="740" y="1330" font-size="16" font-family="Arial, sans-serif" font-weight="bold" fill="#ffffff" text-anchor="end">${this.getSensorState('flowmeter.flowmeter_flowrate', {number: true, decimals: 1})} L/h</text>
                      ${this.isAllElectric() ? svg`
                            <text x="385" y="1365" font-size="16" font-family="Arial, sans-serif" fill="#999999">System pressure:</text>
                            <text x="740" y="1365" font-size="16" font-family="Arial, sans-serif" font-weight="bold" fill="#ffffff" text-anchor="end">
                                ${this.getSensorState('cic.heat_charger_heating_system_pressure', {number: true, decimals: 2})} bar
                            </text>
                            `
                        : (this.isBoilerOpentherm()
                            ? svg`
                                <text x="385" y="1365" font-size="16" font-family="Arial, sans-serif" fill="#999999">Water pressure:</text>
                                <text x="740" y="1365" font-size="16" font-family="Arial, sans-serif" font-weight="bold" fill="#ffffff" text-anchor="end">
                                    ${this.getSensorState('boiler.boiler_water_pressure', {number: true, decimals: 2})} bar
                                </text>
                                `
                            : svg``)
                      }
                  </g>
                  <g id="tooltipRoomTemperature" transform="translate(120, -108)">
                      <rect x="550" y="1200" width="400" height="165" fill="#2d2d2d" opacity="0.95" rx="8" stroke="#4a4a4a" stroke-width="2"/>
                      <text x="565" y="1235" font-size="16" font-family="Arial, sans-serif" fill="#999999">Room temperature:</text>
                      <text x="920" y="1235" font-size="16" font-family="Arial, sans-serif" font-weight="bold" fill="#ffffff" text-anchor="end">${this.getSensorState('thermostat.thermostat_room_temperature', {number: true, decimals: 1})} °C</text>
                      <text x="565" y="1270" font-size="16" font-family="Arial, sans-serif" fill="#999999">Room setpoint:</text>
                      <text x="920" y="1270" font-size="16" font-family="Arial, sans-serif" font-weight="bold" fill="#ffffff" text-anchor="end">${this.getSensorState('thermostat.thermostat_room_setpoint', {number: true, decimals: 1})} °C</text>
                      <text x="565" y="1305" font-size="16" font-family="Arial, sans-serif" fill="#999999">Control setpoint:</text>
                      <text x="920" y="1305" font-size="16" font-family="Arial, sans-serif" font-weight="bold" fill="#ffffff" text-anchor="end">${this.getSensorState('thermostat.thermostat_control_setpoint', {number: true, decimals: 1})} °C</text>
                      <text x="565" y="1340" font-size="16" font-family="Arial, sans-serif" fill="#999999">Heating:</text>
                      <text x="920" y="1340" font-size="16" font-family="Arial, sans-serif" font-weight="bold" fill="#ffffff" text-anchor="end">${this.getSensorState('thermostat.thermostat_heating')?.state}</text>
                  </g>
                  ${this.hasAirco()
                    ? svg`<g id="tooltipAircoTemperature" transform="translate(120, -108)">
                              <rect x="350" y="875" width="400" height="130" fill="#2d2d2d" opacity="0.95" rx="8" stroke="#4a4a4a" stroke-width="2"/>
                              <text x="365" y="910" font-size="16" font-family="Arial, sans-serif" fill="#999999">Room temperature:</text>
                              <text x="720" y="910" font-size="16" font-family="Arial, sans-serif" font-weight="bold" fill="#ffffff" text-anchor="end">${this.getSensorState('other.thermostat_airco', {number: true, decimals: 1, attribute: 'current_temperature'})} °C</text>
                              <text x="365" y="945" font-size="16" font-family="Arial, sans-serif" fill="#999999">Room setpoint:</text>
                              <text x="720" y="945" font-size="16" font-family="Arial, sans-serif" font-weight="bold" fill="#ffffff" text-anchor="end">${this.getSensorState('other.thermostat_airco', {number: true, decimals: 1, attribute: 'temperature'})} °C</text>
                              <text x="365" y="980" font-size="16" font-family="Arial, sans-serif" fill="#999999">Mode:</text>
                              <text x="720" y="980" font-size="16" font-family="Arial, sans-serif" font-weight="bold" fill="#ffffff" text-anchor="end">${this.getSensorState('other.thermostat_airco')?.state}</text>
                          </g>`
                    : svg``
                  }
                  <g id="tooltipHp1DeltaTemperature" transform="translate(120, -108)">
                      <rect x="560" y="1500" width="400" height="235" fill="#2d2d2d" opacity="0.95" rx="8" stroke="#4a4a4a" stroke-width="2"/>
                      <text x="575" y="1535" font-size="16" font-family="Arial, sans-serif" fill="#999999">Temperature water in:</text>
                      <text x="930" y="1535" font-size="16" font-family="Arial, sans-serif" font-weight="bold" fill="#ffffff" text-anchor="end">${this.getSensorState('hp1.hp1_temperaturewaterin', {number: true, decimals: 1})} °C</text>
                      <text x="575" y="1570" font-size="16" font-family="Arial, sans-serif" fill="#999999">Temperature water out:</text>
                      <text x="930" y="1570" font-size="16" font-family="Arial, sans-serif" font-weight="bold" fill="#ffffff" text-anchor="end">${this.getSensorState('hp1.hp1_temperaturewaterout', {number: true, decimals: 1})} °C</text>
                      <text x="575" y="1605" font-size="16" font-family="Arial, sans-serif" fill="#999999">Working mode:</text>
                      <text x="930" y="1605" font-size="16" font-family="Arial, sans-serif" font-weight="bold" fill="#ffffff" text-anchor="end">${this.getSensorState('hp1.hp1_workingmode')?.state}</text>
                      <text x="575" y="1640" font-size="16" font-family="Arial, sans-serif" fill="#999999">COP:</text>
                      <text x="930" y="1640" font-size="16" font-family="Arial, sans-serif" font-weight="bold" fill="#ffffff" text-anchor="end">${this.getSensorState('hp1.hp1_cop')?.state}</text>
                      <text x="575" y="1675" font-size="16" font-family="Arial, sans-serif" fill="#999999">Power:</text>
                      <text x="930" y="1675" font-size="16" font-family="Arial, sans-serif" font-weight="bold" fill="#ffffff" text-anchor="end"> ${this.getSensorState('hp1.hp1_powerinput', {number: true, decimals: 0})} W</text>
                      <text x="575" y="1710" font-size="16" font-family="Arial, sans-serif" fill="#999999">Power input:</text>
                      <text x="930" y="1710" font-size="16" font-family="Arial, sans-serif" font-weight="bold" fill="#ffffff" text-anchor="end">${this.getSensorState('hp1.hp1_power', {number: true, decimals: 0})} W</text>
                  </g>

                  ${this.isDuoHeatpump()
                      ? svg`<g id="tooltipHp2DeltaTemperature" transform="translate(120, -108)">
                                <rect x="420" y="1435" width="400" height="235" fill="#2d2d2d" opacity="0.95" rx="8" stroke="#4a4a4a" stroke-width="2"/>
                                <text x="435" y="1470" font-size="16" font-family="Arial, sans-serif" fill="#999999">Temperature water in:</text>
                                <text x="790" y="1470" font-size="16" font-family="Arial, sans-serif" font-weight="bold" fill="#ffffff" text-anchor="end">${this.getSensorState('hp2.hp2_temperaturewaterin', {number: true, decimals: 1})} °C</text>
                                <text x="435" y="1505" font-size="16" font-family="Arial, sans-serif" fill="#999999">Temperature water out:</text>
                                <text x="790" y="1505" font-size="16" font-family="Arial, sans-serif" font-weight="bold" fill="#ffffff" text-anchor="end">${this.getSensorState('hp2.hp2_temperaturewaterout', {number: true, decimals: 1})} °C</text>
                                <text x="435" y="1540" font-size="16" font-family="Arial, sans-serif" fill="#999999">Working mode:</text>
                                <text x="790" y="1540" font-size="16" font-family="Arial, sans-serif" font-weight="bold" fill="#ffffff" text-anchor="end">${this.getSensorState('hp2.hp2_workingmode')?.state}</text>
                                <text x="435" y="1575" font-size="16" font-family="Arial, sans-serif" fill="#999999">COP:</text>
                                <text x="790" y="1575" font-size="16" font-family="Arial, sans-serif" font-weight="bold" fill="#ffffff" text-anchor="end">${this.getSensorState('hp2.hp2_cop')?.state}</text>
                                <text x="435" y="1610" font-size="16" font-family="Arial, sans-serif" fill="#999999">Power:</text>
                                <text x="790" y="1610" font-size="16" font-family="Arial, sans-serif" font-weight="bold" fill="#ffffff" text-anchor="end">${this.getSensorState('hp2.hp2_powerinput', {number: true, decimals: 0})} W</text>
                                <text x="435" y="1645" font-size="16" font-family="Arial, sans-serif" fill="#999999">Power input:</text>
                                <text x="790" y="1645" font-size="16" font-family="Arial, sans-serif" font-weight="bold" fill="#ffffff" text-anchor="end">${this.getSensorState('hp2.hp2_power', {number: true, decimals: 0})} W</text>
                          </g>`
                      : svg``
                  }

              </g>
          </svg>
      </ha-card>
    `;
    }

    setConfig(config) {
        this.config = config;
    }

    // Provide default config with auto-detected entities
    static getStubConfig() {
        return {
            type: "custom:quatt-dashboard-card",
            system_setup: {
                house_label: "My house",
            },
        };
    }

    // Return the editor element for the card
    static async getConfigElement() {
        const { base, version } = QuattDashboardCard._getBaseUrlAndVersion();
        // Lazy load the editor and include version for cache busting
        await import(`${base}/quatt-dashboard-card-editor.js?v=${version}`);
        return document.createElement("quatt-dashboard-card-editor");
    }

    _toggle(state) {
        this.hass.callService("homeassistant", "toggle", {
            entity_id: state.entity_id,
        });
    }

    static get styles() {
        return css`
            [id*="tooltip"].tooltip-show{
                opacity: 1;
                pointer-events: auto;
                transition: opacity 0.3s ease-in-out;
            }

            [id*="tooltip"]{
                opacity: 0;
                pointer-events: none;
                transition: opacity 0.3s ease-in-out;
            }

            @keyframes fogFlow {
                0%   { stroke-dasharray: 0 200;  stroke-dashoffset: -64;  opacity: 0.60; }
                40%  { stroke-dasharray: 45 200; stroke-dashoffset: -20;  opacity: 0.50; }
                100% { stroke-dasharray: 45 200; stroke-dashoffset: 64; opacity: 0.10; }
            }

            @keyframes fogFlowReverse {
                0%   { stroke-dasharray: 0 200;  stroke-dashoffset: 64;  opacity: 0.60; }
                40%  { stroke-dasharray: 45 200; stroke-dashoffset: 20;  opacity: 0.50; }
                100% { stroke-dasharray: 45 200; stroke-dashoffset: -64; opacity: 0.10; }
            }

            .fog-line {
                animation-name: fogFlow;
                animation-timing-function: linear;
                animation-iteration-count: infinite;
                filter: blur(2px);
                stroke-width: 3;
                fill: none;
                stroke-linecap: round;
                stroke-dasharray: 0 200;
                stroke-dashoffset: 0;
            }

            .fog-line-reverse {
                animation-name: fogFlowReverse;
                animation-timing-function: linear;
                animation-iteration-count: infinite;
                filter: blur(2px);
                stroke-width: 3;
                fill: none;
                stroke-linecap: round;
                stroke-dasharray: 0 200;
                stroke-dashoffset: 0;
            }

            @keyframes waterDrop {
                0% {
                    opacity: 0.7;
                    transform: translateY(0);
                }
                100% {
                    opacity: 0;
                    transform: translateY(50px);
                }
            }

            .water-droplet {
                animation: waterDrop 0.5s ease-in infinite;
            }
            .water-droplet:nth-child(2) { animation-delay: 0.2s; }
            .water-droplet:nth-child(3) { animation-delay: 0.4s; }
            .water-droplet:nth-child(4) { animation-delay: 0.6s; }
            .water-droplet:nth-child(5) { animation-delay: 0.8s; }

            @keyframes steamFlow {
                0% {
                    opacity: 0;
                    transform: translate(0, 0);
                }
                10% {
                    opacity: 0.6;
                }
                90% {
                    opacity: 0.6;
                }
                100% {
                    opacity: 0;
                    transform: translate(-80px, 40px);
                }
            }

            .steam-ring {
                animation: steamFlow 2s ease-in-out infinite;
            }
            .steam-ring:nth-child(1) { animation-delay: 0s; }
            .steam-ring:nth-child(2) { animation-delay: 0.4s; }
            .steam-ring:nth-child(3) { animation-delay: 0.8s; }
            .steam-ring:nth-child(4) { animation-delay: 1.2s; }
            .steam-ring:nth-child(5) { animation-delay: 1.6s; }

            @keyframes smokeRise {
                0% {
                    opacity: 0.8;
                    transform: translate(0, 0) scale(1);
                }
                50% {
                    opacity: 0.5;
                    transform: translate(8px, -60px) scale(1.4);
                }
                100% {
                    opacity: 0;
                    transform: translate(15px, -120px) scale(1.8);
                }
            }

            .smoke-puff {
                animation: smokeRise 4s ease-out infinite;
                filter: blur(8px);
            }
            .smoke-puff:nth-child(1) { animation-delay: 0s; }
            .smoke-puff:nth-child(2) { animation-delay: 0.8s; }
            .smoke-puff:nth-child(3) { animation-delay: 1.6s; }
            .smoke-puff:nth-child(4) { animation-delay: 2.4s; }
            .smoke-puff:nth-child(5) { animation-delay: 3.2s; }

            @keyframes heatRise {
                0%   { stroke-dasharray: 0 200;  stroke-dashoffset: 0;   opacity: 0.70; }
                40%  { stroke-dasharray: 45 200; stroke-dashoffset: -5;  opacity: 0.60; }
                100% { stroke-dasharray: 45 200; stroke-dashoffset: -64; opacity: 0.06; }
            }

            .radiator-heat-line {
                animation-name: heatRise;
                animation-timing-function: linear;
                animation-iteration-count: infinite;
                filter: blur(2px);
                stroke: #ff8a00;
                stroke-width: 2;
                fill: none;
                stroke-linecap: round;
                stroke-dasharray: 0 200;
                stroke-dashoffset: 0;
            }
        `;
    }
}

if (!customElements.get("quatt-dashboard-card")) {
    customElements.define("quatt-dashboard-card", QuattDashboardCard);
}

// Register for the card picker (run once at module load)
window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === "quatt-dashboard-card")) {
    window.customCards.push({
        type: "quatt-dashboard-card",
        name: "Quatt Dashboard Card",
        description: "Quatt heat pump dashboard card",
        preview: true,
    });
}
