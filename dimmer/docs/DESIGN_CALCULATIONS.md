# Dimmer design calculations

These calculations apply to revision J of the 220 Vac, 50 Hz, 1000 W halogen dimmer. They check nominal operation and component sizing. They do not replace measurement of the actual lamp, fuse, enclosure, heatsink, mains supply, or surge environment.

## Load current and resistance

Treating the hot halogen filament as resistive at its 220 V, 1000 W rating:

`Rhot = V²/P = 220²/1000 = 48.4 ohm`

| Mains voltage | RMS current | Lamp power with Rhot = 48.4 ohm |
| ---: | ---: | ---: |
| 198 V (-10 %) | 4.09 A | 810 W |
| 220 V | 4.55 A | 1000 W |
| 242 V (+10 %) | 5.00 A | 1210 W |

The lamp's cold-filament resistance and turn-on surge are not specified. A typical halogen lamp can draw several times its hot current at turn-on, so the actual lamp must be measured before the fuse choice is considered final.

## TRIAC conduction loss and heatsink

For the BTA16-800BW, the ST maximum-value conduction model at maximum junction temperature is:

`VT = VTO + RD x IT`, with `VTO = 0.85 V` and `RD = 25 milliohm`.

For a full sinusoid, `Iavg(abs) = 2sqrt(2)/pi x Irms = 0.9003 x Irms`, so:

`Ptriac = VTO x Iavg(abs) + RD x Irms²`

| Condition | Calculated TRIAC loss |
| --- | ---: |
| 4.55 A at 220 V | 4.00 W |
| 5.00 A at 242 V | 4.45 W |

Allow 6 W for design margin, waveform distortion, component spread, and enclosure heating. The insulated BTA package has `Rth(j-c) = 2.1 °C/W` maximum. With a `0.5 °C/W` interface and a `4 °C/W` heatsink:

`Rth(total) = 2.1 + 0.5 + 4.0 = 6.6 °C/W`

At 4.45 W, junction rise above ambient is approximately `29.4 °C`. At the conservative 6 W allowance it is `39.6 °C`. With a 50 °C internal ambient, the corresponding estimates are about 79 °C and 90 °C, below the 125 °C maximum. These estimates require free airflow compatible with the heatsink rating. The TRIAC cannot operate at this load without the heatsink: its approximately 60 °C/W junction-to-ambient rating would exceed the junction limit.

## MOC3052 input LED and BC547 driver

R3 is 82 ohm. Using the MOC3052 LED drop and the saturated BC547 drop:

`IF = (3.3 V - VF - VCEsat) / 82 ohm`

With `VF = 1.18 to 1.50 V` and `VCEsat approximately 0.1 to 0.2 V`, nominal LED current is approximately 19.5 to 24.6 mA. The MOC3052 maximum trigger current is 10 mA, and onsemi recommends at least 15 mA for temperature and lifetime margin. The design meets that recommendation.

At a simultaneous low 3.3 V rail (-5 %), maximum LED drop, 200 mV transistor drop, and R3 at +5 %, current remains approximately 16.7 mA. At the opposite tolerance corner it remains below 30 mA, well under the MOC3052 60 mA absolute maximum.

R4 supplies approximately `(3.3 - 0.7)/1k = 2.6 mA` of base current. After the 10k base pulldown, the forced beta is below 8 at 20 mA collector current, which is adequate to saturate a genuine BC547. The purchased BC547 lead order must match the PCB C-B-E footprint.

## Main TRIAC gate circuit

The gate path is:

`L_PROT -> R11 220R -> R12 220R -> MOC3052 -> Q2 gate`, with R13 = 330 ohm from gate to MT1.

The BTA16-800BW maximum gate trigger current is 50 mA and maximum gate voltage is 1.3 V. R13 draws approximately `1.3/330 = 3.9 mA`, so the trigger network must supply about 54 mA. Taking a 2.5 V maximum MOC output drop:

`Vline(trigger) approximately 2.5 + 1.3 + 0.054 x 440 = 27.6 V`

At 220 Vac, this corresponds to approximately 5.1 electrical degrees or 0.28 ms after a zero crossing. It therefore does not materially limit the usable phase-angle range.

At 242 Vac and both 220 ohm resistors at -5 %, the theoretical current before the power TRIAC latches is:

`Ipeak = (242sqrt(2) - 2.5 - 1.3) / (440 x 0.95) = 0.81 A`

This is below the MOC3052's 1 A single-cycle surge rating and satisfies the data-sheet minimum-resistance check `R >= Vpeak/ITSM`, which gives approximately 342 ohm. It is a short trigger pulse, not a permissible continuous current. R11 and R12 must be flameproof, pulse-rated parts; their 1 W steady-state marking alone does not establish pulse suitability.

R13 dissipates only milliwatts during normal gate triggering. Its 0.5 W footprint provides ample continuous-power margin, subject to pulse rating and working voltage.

## Zero-cross detector

R7 and R8 are 47 kohm, 1 W resistors in series. Approximate input current is:

`IF(t) = max(0, (abs(Vline(t)) - 1.2 V)/94 kohm)`

Peak current is approximately 3.30 mA at 220 Vac and 3.62 mA at 242 Vac. Resistor heating is conservatively calculated without subtracting the LED voltage:

`Ptotal = Vrms²/(R7+R8)`

| Condition | Total dissipation | Dissipation per resistor |
| --- | ---: | ---: |
| 220 V, nominal | 0.515 W | 0.257 W |
| 242 V, nominal | 0.623 W | 0.312 W |
| 242 V, both resistors at -5 % | 0.656 W | 0.328 W |

The 1 W flameproof resistors therefore have good thermal margin. Each resistor must have at least a 250 V working-voltage rating.

The H11AA1 guarantees CTR only at 10 mA, while this circuit deliberately operates below that current and uses the ESP32's typical internal pull-up. With an illustrative 45 kohm internal pull-up, a low level of 0.825 V requires about 55 microampere of collector current. Assuming an effective 5 % CTR, the transition occurs near 1.1 mA LED current, about 1.09 ms from the true zero crossing at 220 V. Actual delay is device- and temperature-dependent. Firmware must measure both edges, reject missing or irregular crossings, use a timer to predict the true crossing, and inhibit firing after loss of synchronization.

## Phase-angle relationship

For a resistive load fired at angle `alpha` in each half-cycle:

`P/Pfull = 1 - alpha/pi + sin(2alpha)/(2pi)`

At 50 Hz, firing delay is `tdelay = alpha/(2pi x 50)`.

| Requested power | Firing angle | Delay after zero crossing |
| ---: | ---: | ---: |
| 10 % | 133.4 degrees | 7.41 ms |
| 25 % | 113.8 degrees | 6.32 ms |
| 50 % | 90.0 degrees | 5.00 ms |
| 75 % | 66.2 degrees | 3.68 ms |
| 90 % | 46.6 degrees | 2.59 ms |

The firmware delay must subtract the measured zero-cross detector offset. Full off is implemented by never firing the MOC3052; the TRIAC is not a safety isolation device.

## Fuse, MOV, and surge limits

The hot-load current is 4.55 A nominal and 5.00 A at +10 % line, so a time-delay 6.3 A fuse is a reasonable prototype starting point. Final selection requires the real lamp's cold inrush waveform, the fuse manufacturer's time-current curve and I²t data, ambient derating, and the available short-circuit current. Use only a 250 V ceramic high-breaking-capacity cartridge with the verified holder.

The S14K275 is correctly rated for continuous operation on 220/230 Vac mains. Its surge clamping voltage can exceed the MOC3052's 600 V off-state rating at high surge current, so the MOV does not by itself prove coordinated surge immunity. The BTA16-800BW has greater 800 V margin. Surge testing or a standards-based protection redesign is required before claiming a certified overvoltage category.

## PCB current path

The main 4 mm tracks on 70 micrometre (2 oz) copper have approximately 0.28 mm² cross-sectional area. Their resistance is about 6.2 milliohm per 100 mm, giving approximately 31 mV drop and 0.15 W per 100 mm at 5 A. The short 1.75 mm necks at the TO-220 leads are imposed by the 2.54 mm pin pitch and contribute only a small fraction of this loss.

Order the dimmer with two layers, 1.6 mm FR-4 and 2 oz copper. Verify the routed isolation slots, 8 mm SELV-to-mains copper separation, 4 mm power tracks, and NPTH mounting holes in the manufacturer's preview.

## Pre-energization checks

Before connecting mains:

1. Verify the exact pinouts of Q1, Q2, U2, U3, the terminal blocks, fuse holder, and MOV against the purchased parts.
2. Check that there is no continuity between SELV ground and any mains net.
3. Check the line path from J2 through F1 and Q2 to J3, and the direct neutral path from J2 to J3.
4. Power only the SELV side first and verify MOC LED current and the FIRE fail-off state.
5. Use an isolated low-voltage AC source to characterize ZC polarity and timing before using 220 Vac.
6. First mains tests must use a current-limited setup, the final fuse, an enclosed board, isolated instruments, and a small resistive load.
7. Measure TRIAC case and heatsink temperature at 1000 W until thermal equilibrium, including the intended enclosure and worst expected ambient.

Primary references: ST BTA16 data sheet DS2114, onsemi MOC3052M data sheet, Vishay H11AA1 data sheet, and the S14K275 manufacturer's data sheet for the actual purchased MOV.
