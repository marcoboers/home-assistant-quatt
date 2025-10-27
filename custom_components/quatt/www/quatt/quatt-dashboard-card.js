import {
    LitElement,
    svg,
    html,
    css,
} from "https://unpkg.com/lit-element@2.0.1/lit-element.js?module";

class QuattDashboardCard extends LitElement {
    static get properties() {
        return {
            hass: {},
            config: {},
        };
    }

    // Default sensor entity IDs
    static get DEFAULT_SENSORS() {
        return {
            system_hostname: 'sensor.heatpump_system_hostname',
            heatpump_1_odu_type: 'sensor.heatpump_1_odu_type',
            flowmeter_temperature: 'sensor.heatpump_flowmeter_temperature',
            total_power: 'sensor.heatpump_total_power',
            total_powerinput: 'sensor.heatpump_total_powerinput',
            shower_minutes_remaining: 'sensor.heat_battery_shower_minutes_remaining',
            hp1_workingmode: 'sensor.heatpump_hp1_workingmode',
            hp2_workingmode: 'sensor.heatpump_hp2_workingmode',
            boiler_heating: 'binary_sensor.heatpump_boiler_heating',
            cic_central_heating_on: 'binary_sensor.cic_central_heating_on',
            domestic_hot_water_on: 'binary_sensor.heat_battery_domestic_hot_water_on',
            battery_charging: 'binary_sensor.heat_battery_charging',
            heat_battery_percentage: 'sensor.heat_battery_percentage',
        };
    }

    getSensorEntity(sensorKey) {
        const defaults = QuattDashboardCard.DEFAULT_SENSORS;
        return this.config?.[`${sensorKey}_entity`] || defaults[sensorKey];
    }

    getSensorState(sensorKey) {
        const entityId = this.getSensorEntity(sensorKey);
        return this.hass.states[entityId];
    }

    isHybrid() {
        return this.getSensorState('system_hostname')?.attributes['All electric system'] === false ||
            this.getSensorState('system_hostname')?.attributes['All electric system'] === 'false';
    }
    isAllElectric() {
        return this.getSensorState('system_hostname')?.attributes['All electric system'] === true ||
            this.getSensorState('system_hostname')?.attributes['All electric system'] === 'true';
    }
    isMonoHeatpump() {
        return this.getSensorState('system_hostname')?.attributes['Duo heatpump system'] === false ||
            this.getSensorState('system_hostname')?.attributes['Duo heatpump system'] === 'false';
    }
    isDuoHeatpump() {
        return this.getSensorState('system_hostname')?.attributes['Duo heatpump system'] === true ||
            this.getSensorState('system_hostname')?.attributes['Duo heatpump system'] === 'true';
    }

    getSystemVersion() {
        switch (this.getSensorState('heatpump_1_odu_type')?.state) {
            case 'AMM4-V2.0':
                return 'V2';
            default:
                return 'V1';
        }
    }

    render() {
        if (!this.hass || !this.config) {
            return html`<ha-card>Loading...</ha-card>`;
        }

        return html`
      <wired-card elevation="2">
          <svg viewBox="0 0 1920 1920" preserveAspectRatio="xMidYMid meet">
              ${!this.isAllElectric()
                 ? svg`<image href="/local/quatt/src_assets_images_housechimney.png" x="0" y="0" width="1920" height="1920" preserveAspectRatio="xMidYMid meet"/>` : svg``
              }
              
              ${this.isAllElectric()
                  ? (this.isMonoHeatpump()
                      ? (this.getSystemVersion() === 'V2'
                          ? svg`<image href="/local/quatt/src_assets_images_houseallev2.png" x="0" y="0" width="1920" height="1920" preserveAspectRatio="xMidYMid meet"/>`
                          : svg`<image href="/local/quatt/src_assets_images_houseallev1.png" x="0" y="0" width="1920" height="1920" preserveAspectRatio="xMidYMid meet"/>`
                      )
                      : (this.getSystemVersion() === 'V2'
                          ? svg`<image href="/local/quatt/src_assets_images_houseallev2duo.png" x="0" y="0" width="1920" height="1920" preserveAspectRatio="xMidYMid meet"/>`
                          : svg`<image href="/local/quatt/src_assets_images_houseallev1duo.png" x="0" y="0" width="1920" height="1920" preserveAspectRatio="xMidYMid meet"/>`
                      )
                  )
                  : (this.isMonoHeatpump()
                      ? (this.getSystemVersion() === 'V2'
                          ? svg`<image href="/local/quatt/src_assets_images_househybridv2.png" x="0" y="0" width="1920" height="1920" preserveAspectRatio="xMidYMid meet"/>`
                          : svg`<image href="/local/quatt/src_assets_images_househybridv1.png" x="0" y="0" width="1920" height="1920" preserveAspectRatio="xMidYMid meet"/>`
                      )
                      : (this.getSystemVersion() === 'V2'
                          ? svg`<image href="/local/quatt/src_assets_images_househybridv2duo.png" x="0" y="0" width="1920" height="1920" preserveAspectRatio="xMidYMid meet"/>`
                          : svg`<image href="/local/quatt/src_assets_images_househybridv1duo.png" x="0" y="0" width="1920" height="1920" preserveAspectRatio="xMidYMid meet"/>`
                      )
                  )
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

                  ${this.getSensorState('hp1_workingmode')?.state >= 1
                      ? svg`<clipPath id="hp1FlowLines">
                              <rect id="quatt.hp1" x="305" y="1385" width="280" height="150"></rect>
                          </clipPath>`
                      : svg`<clipPath id="hp1FlowLines"></clipPath>`
                  }
                  ${this.getSensorState('hp2_workingmode')?.state >= 1
                      ? svg`<clipPath id="hp2FlowLines">
                              <rect id="quatt.hp2" x="185" y="1285" width="280" height="150"></rect>
                          </clipPath>`
                      : svg`<clipPath id="hp2FlowLines"></clipPath>`
                  }
                  
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

                  <filter id="smokeBlur">
                      <feGaussianBlur in="SourceGraphic" stdDeviation="8"/>
                  </filter>
              </defs>

              <g id="quatt.legend">
                  ${this.isHybrid()
                      ? svg`<rect id="quatt.legend.hybrid" x="50" y="300" width="300" height="330" fill="#1a1a1a" opacity="0.85" rx="20"/>`
                      : svg`<rect id="quatt.legend.alle" x="50" y="300" width="300" height="410" fill="#1a1a1a" opacity="0.85" rx="20"/>`
                  }

                  <!-- Title -->
                  <text x="70" y="345" font-family="Arial, sans-serif" font-size="32" font-weight="bold" fill="#ffffff">My house</text>

                  <!-- Water temperature -->
                  <text x="70" y="400" font-family="Arial, sans-serif" font-size="22" fill="#999999">Water temperature</text>
                  <text x="70" y="435" font-family="Arial, sans-serif" font-size="28" font-weight="bold" fill="#ffffff">
                      ${(this.getSensorState('flowmeter_temperature')?.state*1 || 0).toFixed(1)}°C
                  </text>

                  <!-- Heat -->
                  <text x="70" y="480" font-family="Arial, sans-serif" font-size="22" fill="#999999">Heat</text>
                  <text x="70" y="515" font-family="Arial, sans-serif" font-size="28" font-weight="bold" fill="#ffffff">
                      ${((this.getSensorState('total_power')?.state || 0) / 1000).toFixed(2)}kW
                  </text>

                  <!-- Electricity -->
                  <text x="70" y="560" font-family="Arial, sans-serif" font-size="22" fill="#999999">Electricity</text>
                  <text x="70" y="595" font-family="Arial, sans-serif" font-size="28" font-weight="bold" fill="#ffffff">
                      ${((this.getSensorState('total_powerinput')?.state || 0) / 1000).toFixed(2)}kW
                  </text>

                  <!-- Shower -->
                  ${this.isAllElectric()
                      ? svg`<text x="70" y="640" font-family="Arial, sans-serif" font-size="22" fill="#999999">Shower time</text>
                            <text x="70" y="675" font-family="Arial, sans-serif" font-size="28" font-weight="bold" fill="#ffffff">
                                ${this.getSensorState('shower_minutes_remaining')?.state || 0} min
                            </text>`
                      : svg``
                  }
              </g>

              <g clip-path="url(#outsidePipe)">
              ${(this.getSensorState('hp1_workingmode')?.state >= 1
                || this.getSensorState('hp2_workingmode')?.state >= 1)
                  ? svg`<path id="quatt.outsidePipe" d="M 274 1253 L 567 1400" stroke="url(#waterGradientToLeft)" stroke-width="8" fill="none" stroke-linecap="round"/>`
                  : svg``
              }
              </g>

              <g clip-path="url(#bottomPipe)">
                  ${(this.getSensorState('hp1_workingmode')?.state >= 1
                    || this.getSensorState('hp2_workingmode')?.state >= 1)
                      ? svg`<path id="quatt.bottomPipe" d="M 275 1250 L 404 1185" stroke="url(#waterGradientToRight)" stroke-width="8" fill="none" stroke-linecap="round"/>`
                      : svg``
                  }

                  ${this.isAllElectric()
                    && (this.getSensorState('hp1_workingmode')?.state >= 1
                        || this.getSensorState('hp2_workingmode')?.state >= 1)
                      ? svg`<path id="quatt.alle.bottomPipe" d="M 405 1185 L 406 1117" stroke="url(#waterGradientUp)" stroke-width="8" fill="none" stroke-linecap="round"/>`
                      : svg``
                  }

                  ${this.isAllElectric()
                    && this.getSensorState('cic_central_heating_on')?.state == 'on'
                      ? svg`<path id="quatt.alle.radiatorPipe1" d="M 434 1121 L 435 1167" stroke="url(#waterGradientDown)" stroke-width="8" fill="none" stroke-linecap="round"/>
                            <path id="quatt.alle.radiatorPipe2" d="M 435 1167 L 495 1139" stroke="url(#waterGradientToRight)" stroke-width="8" fill="none" stroke-linecap="round"/>`
                      : svg``
                  }
              </g>

              <g clip-path="url(#hp1FlowLines)">
                  <g id="hp1Flow">
                      <path class="fog-line" d="M 425 1415 Q 435 1408, 445 1415 Q 455 1422, 465 1415 Q 475 1408, 485 1415 Q 495 1422, 505 1415 Q 515 1408, 525 1415 Q 535 1422, 545 1415 Q 555 1408, 565 1415 Q 575 1422, 585 1415 Q 595 1408, 605 1415 Q 615 1422, 625 1415 Q 635 1408, 645 1415 Q 655 1422, 665 1415" stroke="#E8F4F8" stroke-width="3" fill="none" stroke-linecap="round" opacity="0"/>
                      <path class="fog-line" d="M 435 1430 Q 445 1423, 455 1430 Q 465 1437, 475 1430 Q 485 1423, 495 1430 Q 505 1437, 515 1430 Q 525 1423, 535 1430 Q 545 1437, 555 1430 Q 565 1423, 575 1430 Q 585 1437, 595 1430 Q 605 1423, 615 1430 Q 625 1437, 635 1430 Q 645 1423, 655 1430 Q 665 1437, 675 1430" stroke="#D4E8F0" stroke-width="4" fill="none" stroke-linecap="round" opacity="0"/>
                      <path class="fog-line" d="M 430 1445 Q 440 1438, 450 1445 Q 460 1452, 470 1445 Q 480 1438, 490 1445 Q 500 1452, 510 1445 Q 520 1438, 530 1445 Q 540 1452, 550 1445 Q 560 1438, 570 1445 Q 580 1452, 590 1445 Q 600 1438, 610 1445 Q 620 1452, 630 1445 Q 640 1438, 650 1445 Q 660 1452, 670 1445" stroke="#E0EDF5" stroke-width="2.5" fill="none" stroke-linecap="round" opacity="0"/>
                      <path class="fog-line" d="M 440 1460 Q 450 1453, 460 1460 Q 470 1467, 480 1460 Q 490 1453, 500 1460 Q 510 1467, 520 1460 Q 530 1453, 540 1460 Q 550 1467, 560 1460 Q 570 1453, 580 1460 Q 590 1467, 600 1460 Q 610 1453, 620 1460 Q 630 1467, 640 1460 Q 650 1453, 660 1460 Q 670 1467, 680 1460" stroke="#DCE9F2" stroke-width="3" fill="none" stroke-linecap="round" opacity="0"/>
                  </g>
              </g>
              <g clip-path="url(#hp2FlowLines)">
                  <g id="hp2Flow">
                      <path class="fog-line" d="M 295 1350 Q 305 1343, 315 1350 Q 325 1357, 335 1350 Q 345 1343, 355 1350 Q 365 1357, 375 1350 Q 385 1343, 395 1350 Q 405 1357, 415 1350 Q 425 1343, 435 1350 Q 445 1357, 455 1350 Q 465 1343, 475 1350 Q 485 1357, 495 1350 Q 505 1343, 515 1350 Q 525 1357, 535 1350" stroke="#E8F4F8" stroke-width="3" fill="none" stroke-linecap="round" opacity="0"/>
                      <path class="fog-line" d="M 305 1365 Q 315 1358, 325 1365 Q 335 1372, 345 1365 Q 355 1358, 365 1365 Q 375 1372, 385 1365 Q 395 1358, 405 1365 Q 415 1372, 425 1365 Q 435 1358, 445 1365 Q 455 1372, 465 1365 Q 475 1358, 485 1365 Q 495 1372, 505 1365 Q 515 1358, 525 1365 Q 535 1372, 545 1365" stroke="#D4E8F0" stroke-width="4" fill="none" stroke-linecap="round" opacity="0"/>
                      <path class="fog-line" d="M 300 1380 Q 310 1373, 320 1380 Q 330 1387, 340 1380 Q 350 1373, 360 1380 Q 370 1387, 380 1380 Q 390 1373, 400 1380 Q 410 1387, 420 1380 Q 430 1373, 440 1380 Q 450 1387, 460 1380 Q 470 1373, 480 1380 Q 490 1387, 500 1380 Q 510 1373, 520 1380 Q 530 1387, 540 1380" stroke="#E0EDF5" stroke-width="2.5" fill="none" stroke-linecap="round" opacity="0"/>
                      <path class="fog-line" d="M 310 1395 Q 320 1388, 330 1395 Q 340 1402, 350 1395 Q 360 1388, 370 1395 Q 380 1402, 390 1395 Q 400 1388, 410 1395 Q 420 1402, 430 1395 Q 440 1388, 450 1395 Q 460 1402, 470 1395 Q 480 1388, 490 1395 Q 500 1402, 510 1395 Q 520 1388, 530 1395 Q 540 1402, 550 1395" stroke="#DCE9F2" stroke-width="3" fill="none" stroke-linecap="round" opacity="0"/>
                  </g>
              </g>

              ${this.isHybrid() 
                && this.getSensorState('boiler_heating')?.state == 'on'
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
                && this.getSensorState('domestic_hot_water_on')?.state == 'on'
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
                && this.getSensorState('battery_charging')?.state == 'on'
                  ? svg`<g id="quatt.boilerSteam">
                        <circle class="steam-ring" cx="400" cy="993" r="8" fill="none" stroke="#E8F4F8" stroke-width="2" opacity="0"/>
                        <circle class="steam-ring" cx="400" cy="993" r="8" fill="none" stroke="#D4E8F0" stroke-width="2" opacity="0"/>
                        <circle class="steam-ring" cx="400" cy="993" r="8" fill="none" stroke="#E8F4F8" stroke-width="2" opacity="0"/>
                        <circle class="steam-ring" cx="400" cy="993" r="8" fill="none" stroke="#D4E8F0" stroke-width="2" opacity="0"/>
                        <circle class="steam-ring" cx="400" cy="993" r="8" fill="none" stroke="#E8F4F8" stroke-width="2" opacity="0"/>
                    </g>`
                    : svg``
              }
              
              ${this.isAllElectric()
                    ? svg`<g id="quatt.waterTankIndicator">
                          <defs>
                              <linearGradient id="tankWaterGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                                  <stop id="gradientStop1" offset="0%" style="stop-color:#FF4444;stop-opacity:0.5"/>
                                  <stop id="gradientStop2" offset="${Math.max(0, (this.getSensorState('heat_battery_percentage')?.state || 0) - 12.5)}%" style="stop-color:#FF4444;stop-opacity:0.5"/>
                                  <stop id="gradientStop3" offset="${Math.min(100, (this.getSensorState('heat_battery_percentage')?.state || 0) + 12.5)}%" style="stop-color:#0066FF;stop-opacity:0.5"/>
                                  <stop id="gradientStop4" offset="100%" style="stop-color:#0066FF;stop-opacity:0.5"/>
                              </linearGradient>
                          
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
                          <rect x="305" y="1070" width="70" height="195"
                                fill="url(#tankWaterGradient)" rx="28" filter="url(#waterDepth)"/>
        
                          <!-- Glossy highlight overlay -->
                          <rect x="310" y="1075" width="25" height="180"
                                fill="url(#waterGloss)" rx="20" opacity="0.6"/>
        
                          <!-- Subtle shine on edges -->
                          <rect x="305" y="1070" width="70" height="190"
                                fill="none" stroke="rgba(255,255,255,0.2)" stroke-width="1" rx="28"/>
        
                          <!-- Percentage text -->
                          <text x="340" y="1172"
                                text-anchor="middle"
                                font-size="24"
                                font-family="Arial, sans-serif"
                                font-weight="bold"
                                fill="#ffffff"
                                stroke="#000000"
                                stroke-width="0.5"
                                opacity="0.9">
                              ${Math.round(this.getSensorState('heat_battery_percentage')?.state || 0)}%
                          </text>
                      </g>`
                      : svg``
              }
          </svg>
      </wired-card>
    `;
    }

    setConfig(config) {
        this.config = config;
    }

    // Provide default config with auto-detected entities
    static getStubConfig(hass) {
        const defaults = QuattDashboardCard.DEFAULT_SENSORS;
        const config = { type: 'custom:quatt-dashboard-card' };

        // Auto-populate with defaults if entities exist
        Object.entries(defaults).forEach(([key, entityId]) => {
            if (hass.states[entityId]) {
                config[`${key}_entity`] = entityId;
            }
        });

        return config;
    }

    // Return the form schema for Home Assistant's built-in editor
    static getConfigForm() {
        return {
            schema: [
                {
                    name: "system_hostname",
                    selector: {
                        entity: {
                            integration: "quatt",
                            domain: "sensor"
                        }
                    }
                },
                {
                    name: "heatpump_1_odu_type_entity",
                    selector: {
                        entity: {
                            integration: "quatt",
                            domain: "sensor"
                        }
                    }
                },
                {
                    name: "flowmeter_temperature_entity",
                    required: true,
                    selector: {
                        entity: {
                            integration: "quatt",
                            domain: "sensor",
                            device_class: "temperature"
                        }
                    }
                },
                {
                    name: "total_power_entity",
                    required: true,
                    selector: {
                        entity: {
                            integration: "quatt",
                            domain: "sensor",
                            device_class: "power"
                        }
                    }
                },
                {
                    name: "total_powerinput_entity",
                    required: true,
                    selector: {
                        entity: {
                            integration: "quatt",
                            domain: "sensor",
                            device_class: "power"
                        }
                    }
                },
                {
                    name: "shower_minutes_remaining_entity",
                    selector: {
                        entity: {
                            integration: "quatt",
                            domain: "sensor"
                        }
                    }
                },
                {
                    name: "hp1_workingmode_entity",
                    selector: {
                        entity: {
                            integration: "quatt",
                            domain: "sensor"
                        }
                    }
                },
                {
                    name: "hp2_workingmode_entity",
                    selector: {
                        entity: {
                            integration: "quatt",
                            domain: "sensor"
                        }
                    }
                },
                {
                    name: "cic_central_heating_on_entity",
                    selector: {
                        entity: {
                            integration: "quatt",
                            domain: "binary_sensor"
                        }
                    }
                },
                {
                    name: "boiler_heating_entity",
                    selector: {
                        entity: {
                            integration: "quatt",
                            domain: "binary_sensor"
                        }
                    }
                },
                {
                    name: "domestic_hot_water_on_entity",
                    selector: {
                        entity: {
                            integration: "quatt",
                            domain: "binary_sensor"
                        }
                    }
                },
                {
                    name: "battery_charging_entity",
                    selector: {
                        entity: {
                            integration: "quatt",
                            domain: "binary_sensor"
                        }
                    }
                },
                {
                    name: "heat_battery_percentage_entity",
                    selector: {
                        entity: {
                            integration: "quatt",
                            domain: "sensor"
                        }
                    }
                }
            ]
        };
    }

    _toggle(state) {
        this.hass.callService("homeassistant", "toggle", {
            entity_id: state.entity_id,
        });
    }

    static get styles() {
        return css`
            @keyframes fogFlow {
                0% {
                    opacity: 0.6;
                    transform: translateX(200px) translateY(0px);
                }
                100% {
                    opacity: 0.1;
                    transform: translateX(-50px) translateY(0px);
                }
            }

            .fog-line {
                animation: fogFlow 5s ease-in-out infinite;
                filter: blur(2px);
            }
            .fog-line:nth-child(1) { animation-delay: 0s; }
            .fog-line:nth-child(2) { animation-delay: 2.4s; }
            .fog-line:nth-child(3) { animation-delay: 0.8s; }
            .fog-line:nth-child(4) { animation-delay: 3.2s; }

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
        `;
    }
}

customElements.define("quatt-dashboard-card", QuattDashboardCard);