# Photodiode transimpedance lab — revision D

[![3D preview](docs/board-3d.png)](docs/board-3d.png)

[KiCad project](photodiode_lab.kicad_pro) · [Schematic PDF](docs/schematic.pdf) · [BOM CSV](BOM.csv)

This is a 3.3 V teaching transimpedance amplifier (TIA) for a Vishay BPW34, an MCP6002-I/P in an 8-pin DIP socket, and the shared direct-solder ESP32-C3 footprint. The ESP32-C3 GPIO0 ADC input is `ADC_OUT`.

## Wiring and functional diagram

Fit the BPW34 in the marked top-view orientation: pad 1 (`K`, cathode) goes to the MCP6002 A inverting input, net `SUM`; pad 2 (anode) goes to `GND`. On the PCB, K is on the right and the anode on the left. The photodiode is therefore reverse biased at about 1.65 V. The MCP6002 DIP-8 pinout is: 1 OUTA=`VOUT`, 2 INA−=`SUM`, 3 INA+=`VREF`, 4 VSS=`GND`, 5 INB+=`REF_DIV`, 6 INB−=`VREF`, 7 OUTB=`VREF`, 8 VDD=`+3V3`.

R1/R2 make the 1.65 V divider and MCP6002 section B buffers it. RF1 is an ordinary soldered 100 kOhm, 1% axial resistor. CF1 is the fixed 1 nF C0G capacitor in parallel with RF1. Any future resistor variation is left to the user; power must be OFF before modifying the feedback components.

The front silkscreen integrates the functional A-channel TIA diagram with the actual BPW34, RF1, CF1, MCP6002, divider, and test-point locations. The diagram surrounds the real MCP6002 package, which contains both amplifier A and the VREF buffer B. Its printed lines depict functional connections and are not the physical DIP pin map.

## Theory and ranges

Before output clipping, `VOUT = VREF + IPH × RF1`; this polarity follows from the cathode-at-SUM and anode-at-ground connection. The feedback pole is `fc ≈ 1/(2π × RF1 × CF1)`. The fitted values remain documented in the schematic and BOM, while the front silkscreen uses reference designators so it remains correct if either component changes.

To choose R1/R2, RF1, R3/R4 and the ADC attenuation for a given light range, follow [docs/MEASUREMENT_RANGE.md](docs/MEASUREMENT_RANGE.md). The Rust firmware in [firmware/](firmware/README.md) serves a phone page with live readings, an attenuation selector and the same calculations.

The feedback pole `1/(2πRF·1 nF)` is about 15.9 kHz, 1.59 kHz, and 159 Hz for those three settings. The 1 nF capacitor is intentionally much larger than the BPW34's tens-of-pF junction capacitance, giving a slow, stable teaching response.

`ADC_OUT` is the divider midpoint: `VADC = VOUT × R4/(R3+R4)`, with R3 between VOUT and ADC and R4 between ADC and GND. The fitted values R3=10 kOhm and R4=22 kOhm give a factor of 0.6875. C4 forms a low-pass with R3 in parallel with R4: `fc ≈ 1/[2π × (R3 || R4) × C4]`, approximately 232 Hz with the fitted values. Recalculate ADC headroom and filtering if either resistor changes. Calibrate the ESP32 ADC and dark offset; the ADC voltage increases with light.

## Test points and references

The actual front test-point locations are TP1=`VOUT` at (78, 60) mm, TP2=`VREF` at (29, 69) mm, TP3=`ADC_OUT` at (88, 78.16) mm, and TP4=`GND` at (88, 93.16) mm. Keep the sensitive `SUM` node short and avoid probing it during normal measurements. Revision D has no rear theory artwork; the functional diagram is on the front around the actual parts.

Primary references: [Vishay BPW34 datasheet](https://www.vishay.com/docs/81521/bpw34.pdf) and [Microchip MCP6002 datasheet](https://ww1.microchip.com/downloads/en/DeviceDoc/MCP6001-1R-1U-2-4-1-MHz-Low-Power-Op-Amp-DS20001733L.pdf).

## CAD and checks

The two-layer PCB is 100 x 100 mm with rounded corners and four M3 clearance holes. Fit the MCP6002 in U2's DIP-8 socket, matching the notch. D1's square pad is cathode K. The photodiode and other 3D renders are approximate envelopes; inspect the purchased parts before fabrication.

Rebuild from the repository root with the uv environment described in the root README:

```sh
uv run --no-sync python scripts/photodiode_lab/build_lab.py
uv run --no-sync python scripts/photodiode_lab/route_board.py
kicad-cli sch export netlist photodiode_lab/photodiode_lab.kicad_sch --format kicadxml -o photodiode_lab/outputs/netlist.xml
uv run --no-sync python scripts/photodiode_lab/finish_lab.py
kicad-cli sch erc photodiode_lab/photodiode_lab.kicad_sch --exit-code-violations -o photodiode_lab/outputs/erc.rpt
kicad-cli pcb drc photodiode_lab/photodiode_lab.kicad_pcb --schematic-parity --exit-code-violations -o photodiode_lab/outputs/drc.rpt
```

Revision D passes ERC, DRC and schematic-to-PCB parity checks with no violations or unconnected items. Independent checks verify all 53 connected pins, BPW34 polarity, the MCP6002 pin map, and the exact dimmer ESP32 pad geometry. Prototype testing must establish noise, offset, stability, clipping, and usable light range. This is a prototype teaching board, not a calibrated light meter.

## Optional SMD soldering exercise

The top strip adds a static LED circuit, enabled by the normally open JP1 header. It shares only +3V3 and ground with the laboratory circuit; it has no connection to SUM, VREF or the ADC signal. The TIA works with the entire exercise unpopulated.

Solder in increasing difficulty: R5=1k (1206), R6=0 ohm (0805), R7=0 ohm (0603), and D2=red LED (0805, cathode on the right). R5 must remain 1k: it limits LED current to roughly 1-2mA at 3.3V. Pads A, B, C, D and GND are built-in copper test pads, not purchased components.

With USB disconnected and JP1 open, check approximately 1k between A and B, continuity from B through C to D, and inspect for solder bridges. Check LED polarity with diode mode. Then connect USB and fit the JP1 shunt: the LED should light without firmware. Measure V(A)-V(B) to estimate current using I=V/R5. Remove JP1 before photodiode measurements to avoid LED illumination influencing the sensor and to remove the practice load. A dark LED with JP1 fitted can indicate an open solder joint, reversed LED, missing component, or a supply problem. Never use continuity mode on the powered board.

Revision D: dark output is approximately 1.65 V, not zero. With RF1=100k, an additional 1uA of photocurrent raises VOUT by 100mV and ADC_OUT by 68.75mV before clipping. Calibrate the actual dark output, including ambient light and offset.
