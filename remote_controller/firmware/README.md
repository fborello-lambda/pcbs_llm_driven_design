# Remote controller firmware

Simple Rust (ESP-IDF `std`) test firmware for the remote controller board. The SSD1306 OLED shows:

- a circle for the thumbstick range, with a dot at the current stick position;
- three squares at the bottom for ON/SELECT, PRESET and OFF/BACK (left to right, as on the board), filled while the button is pressed and outlined otherwise.

The display uses the [`ssd1306`](https://crates.io/crates/ssd1306) driver and [`embedded-graphics`](https://crates.io/crates/embedded-graphics).

## Build and flash

Prerequisites are the same as the [photodiode lab firmware](../../photodiode_lab/firmware/README.md): `cargo install ldproxy espflash` and the ESP-IDF build packages. `rust-toolchain.toml` pins nightly with `rust-src`.

```sh
cd remote_controller/firmware
cargo run --release        # build, flash and open the serial monitor
```

The first build downloads ESP-IDF v5.5.3 into `.embuild/` (several GB). To reuse an existing install, set `ESP_IDF_TOOLS_INSTALL_DIR=custom:/path/to/.embuild/espressif`. After changing `sdkconfig.defaults`, run `cargo clean` so the generated ESP-IDF configuration is rebuilt. If `espflash` cannot connect, hold BOOT, tap RESET, release BOOT and flash again.

## Pins

| Function | GPIO |
|---|---|
| Thumbstick X / Y | GPIO0 / GPIO1 (ADC1, 12 dB) |
| ON/SELECT, OFF/BACK, PRESET | GPIO10, GPIO20, GPIO21 (internal pull-ups, pressed = low) |
| OLED SDA / SCL | GPIO6 / GPIO7, I2C 400 kHz, address 0x3C |

GPIO20/21 are also UART0, so `sdkconfig.defaults` moves the console to the USB serial port.

## Calibration

At start-up the stick's rest position is taken as the centre, so leave it alone while the board powers up.

To calibrate fully, **hold all three buttons for one second**:

1. **"Release buttons and the stick"** (about 2 s): the rest position is measured as the centre.
2. **"Circle the edges"** (4 s, with a progress bar): move the stick around its full travel. Any side with less than 250 mV of travel falls back to ±500 mV. During this step the dot sits at the edge until enough travel has been seen.

A 10 % circular dead zone around the centre absorbs the small offset the stick keeps after a large movement; the rest of the travel is rescaled so the dot still reaches the edge. Adjust `DEAD_ZONE` in `src/main.rs` if needed. The measured travel only widens during use (it never shrinks), so if the stick was held at power-up or the dot stops reaching the edge evenly, run the three-button calibration again. Each reading averages 8 ADC samples.

The joystick dividers work with any values: with 10k/10k (R3–R6 all 10k) the ADC sees 0–1.65 V, inside the 12 dB window. The axis orientation is set for the assembled board (`SWAP_AXES`, `INVERT_X`, `INVERT_Y` in `src/main.rs`); change them if a different thumbstick or mounting moves the dot the wrong way. If the picture is upside down, change `DisplayRotation::Rotate0` to `Rotate180`.
