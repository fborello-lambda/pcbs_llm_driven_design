# Dimmer firmware

Rust (ESP-IDF `std`) phase-control firmware for the 220 Vac halogen dimmer, controlled from a phone over Wi-Fi.

> **Mains voltage.** The dimmer is an uncertified prototype. Read the [design calculations](../docs/DESIGN_CALCULATIONS.md) and follow the bring-up order below. Never touch the board, the lamp terminals or any probe while it is connected to mains.

## What it does

- **Zero-cross (ZC, GPIO3):** the H11AA1 output is low while the mains voltage is high and pulses high around each zero crossing. The firmware takes the middle of each pulse as the true zero crossing, so the opto delay cancels out. The design estimate was about 2.2 ms, but on the first board the pulses are only **30–100 µs** wide; any width from 10 µs to 5 ms is accepted.
- **Noise filter:** GPIO3 has only the weak internal pull-up, so its edges are slow and noisy (about 70–100 false edges per second on the first board). After each edge the line is sampled four times over about 8 µs, and the edge is ignored if the level did not really change.
- **Lock:** firing starts only after 8 valid half-cycles in a row. Valid means 40–62.5 Hz and a pulse narrower than 5 ms. A single missed pulse (a gap of exactly two half-cycles) keeps the lock, because the crossing that ends it is real. Any other bad crossing stops firing at once; no edge for 30 ms counts as mains lost.
- **Firing (FIRE, GPIO4):** a 150 µs pulse to the MOC3052 at the delay that gives the requested **power** (not phase angle), using P = 1 − α/π + sin(2α)/(2π). 50 % power fires 5.0 ms after the crossing, 10 % at 7.4 ms. The delay is limited to 1.4–8.5 ms, so 99 % becomes 98.3 % and 1 % becomes 2 %. 100 % holds FIRE high (full on); 0 % never fires.
- **Never late:** a pulse that would land less than 1 ms before the next crossing is skipped and counted, so a delayed pulse can never turn on the following half-cycle.
- **Off at boot:** the level is not stored. Wi-Fi runs without NVS, so nothing is written to flash while the lamp runs.
- **Logging:** status goes to the USB serial port through `log::info!`. Never use `println!` in this firmware: it panics when no USB host is attached (see [debugging notes](DEBUGGING_NOTES.md)).
- **Wi-Fi power** is capped at 8.5 dBm, which works around the SuperMini's poorly matched antenna and is enough for a phone in the same room.

## Build and flash

Prerequisites are the same as the [photodiode lab firmware](../../photodiode_lab/firmware/README.md).

**Flash with mains disconnected.** Unplug J2, disconnect J1 and remove the JP1 shunt (as printed on the board), then connect USB:

```sh
cd dimmer/firmware
cargo run --release
```

## Control

The SuperMini's blue LED shows the state without a cable: three quick flashes at boot, then one short flash per second once the Wi-Fi network is up. Repeated triple flashes mean the board keeps resetting, usually from a weak supply.

The board creates the Wi-Fi network `esp32-dimmer` (password `dimmer-lab`). Open http://192.168.71.1 on the phone. The page shows:

- mains status (none, locking, locked), frequency, ZC pulse width, firing delay and angle;
- a power slider with Off / 25 / 50 / 75 / Full buttons;
- the expected lamp voltage for a true-RMS meter: V<sub>lamp</sub> = V<sub>in</sub> × √(power);
- an optocoupler LED test (mains disconnected only).

`GET /status` returns the same data as JSON; `POST /level?p=0..100` sets the power.

## Bring-up and testing

Do the steps in order. Each step only adds one hazard.

### 1. SELV only, no mains

USB power only (J2 unplugged, J1 disconnected, JP1 open).

- The page should say **No mains detected: firing disabled**. With a multimeter on the SELV side, FIRE (GPIO4) stays at 0 V at any slider position.
- Press **Start LED test** and measure across R3 (82 Ω): about 1.6–2.0 V, which is 20–25 mA in the MOC3052 LED. It drops back to 0 V after 30 s or when you press **Stop**. Short glitches from touching the probes do not end the test; a real zero-cross pulse does.
- An oscilloscope may be used on the SELV side (GPIO3, GPIO4, R3) in this step.

### 2. Zero-cross with an isolated low-voltage AC source (recommended)

Feed J2 from an isolated low-voltage AC transformer instead of mains. R7 + R8 (94 kΩ) are sized for 220 Vac, so at low voltage the H11AA1 gets very little current: the pulses are much wider, the firmware may not lock, and below roughly 48 Vac the opto may not switch at all. This step only checks that ZC edges arrive; the timing is checked on mains in step 3.

### 3. Mains, lamp, no instruments on the mains side

- Close the board in its enclosure, with the heatsink fitted, the fuse in F1 and a **small resistive lamp** (for example 40–100 W incandescent or halogen) on J3.
- Power the ESP32 from a certified isolated 3.3 V supply on J1 with JP1 fitted, **not** from the laptop's USB.
- Control it only from the phone. The page should show **Locked to mains** and about 50 Hz. Under *Zero-cross, last second* expect about 100 pulses, 0 invalid and a half-period near 10 000 µs.
- **A load is required.** The TRIAC only stays on when the load draws its latching current (roughly 50–80 mA for the BTA16). With only a voltmeter, or an open lamp filament, Full still shows about 220 V (FIRE is held on) but partial levels show only leakage, around 13–60 V. A 47 kΩ resistor (4.7 mA) is far too little.
- Step through 25 / 50 / 75 / Full. The lamp should brighten smoothly and *skipped* should stay near 0.
- Above about 100 W the TRIAC needs its heatsink: a 1 kW load is about 4.4 A and 4 W in Q2, which a bare TO-220 cannot shed.

### 4. Measure the output voltage

With the mains disconnected, connect a **true-RMS** multimeter rated **CAT III 300 V** (or better) across J3, in parallel with the lamp. Then power up and read it at each level against *Expected lamp voltage* on the page. A non-true-RMS meter reads a chopped sine wave wrongly.

### 5. Waveform (optional, only with the right equipment)

See *Oscilloscopes and isolation* below before connecting any oscilloscope to the mains side.

## Results on the first board

- R3 fitted as 100 Ω instead of 82 Ω: 1.9 V across it, 19 mA in the MOC3052 LED (10 mA maximum trigger current).
- Zero-cross pulses 30–100 µs wide, 101 per second, half-period 9983–10008 µs, locked at 49.9–50.0 Hz.
- With a 50 Ω (about 1 kW) iron on J3, the firmware stayed locked through repeated level changes: delays of 6.32 ms at 25 % and 3.68 ms at 75 %, 100 firings per second, and 1 skipped firing in about 3 500.
- Suggested hardware change: a 10 kΩ pull-up from GPIO3 to 3V3. It needs more opto current to pull the line low, so the pulses get wider and the edges faster, with far less noise.

## Oscilloscopes and isolation

**A normal bench oscilloscope is not isolated.** Its probe ground clips are connected to the mains protective earth through the power cord. Clipping one onto the dimmer's mains side shorts the mains through the probe and the scope, which can destroy both and is dangerous. Removing the scope's earth or running it from an isolation transformer makes its metal case live; do not do it.

Safe ways to see the mains-side waveform:

- a **high-voltage differential probe**, CAT-rated for 300 V or more, into an ordinary earthed oscilloscope;
- a handheld oscilloscope with **isolated channels** rated for the job, for example OWON's HDS1022M-I. OWON's standard HDS…-N handhelds and SDS bench scopes do not have isolated inputs; check the CAT rating and "isolated channels" in the manual of your exact model;
- otherwise, measure the SELV side only. The ZC (GPIO3) and FIRE (GPIO4) pins are on the isolated low-voltage side and can be probed with any scope grounded to the board's SELV GND. That shows the zero-cross pulses and the firing delay without touching mains. This relies on the board's own isolation barrier, so keep the probe and scope away from the mains side and the enclosure closed.
