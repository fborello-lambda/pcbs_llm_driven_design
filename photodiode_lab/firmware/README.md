# Photodiode lab firmware

Rust (ESP-IDF `std`) firmware for the photodiode lab board. It reads `ADC_OUT` on GPIO0 (ADC1 channel 0, curve-fitting calibration), averages 32 samples every 200 ms, prints a JSON line on the serial console, and serves a phone-friendly page with:

- the ADC voltage, raw counts and noise;
- buttons to change the ADC attenuation (0, 2.5, 6 or 12 dB) while running; it starts at 12 dB after every reset;
- inputs for the fitted R1, R2, RF1, R3 and R4, with live VOUT and photocurrent estimates, window usage, clipping warnings, and suggested values;
- the range formulas, rendered with MathJax.

The calculations are explained in [`../docs/MEASUREMENT_RANGE.md`](../docs/MEASUREMENT_RANGE.md). MathJax loads from a CDN; if the phone has no internet path, the formulas show as plain TeX and everything else still works.

## Build and flash

Prerequisites are the same as any `esp-idf-svc` project: `cargo install ldproxy espflash` and the ESP-IDF build packages (`git cmake ninja-build python3-venv libudev-dev …`). `rust-toolchain.toml` pins nightly with `rust-src`.

```sh
cd photodiode_lab/firmware
cargo run --release        # build, flash and open the serial monitor
```

The first build downloads ESP-IDF v5.5.3 into `.embuild/` (several GB). To reuse an existing install, set `ESP_IDF_TOOLS_INSTALL_DIR=custom:/path/to/.embuild/espressif` when building.

If `espflash` cannot connect, put the board in download mode: hold BOOT, tap RESET, release BOOT, then flash again.

## Wi-Fi

- Default: the board creates the access point `photodiode-lab` (password `photodiode`). Connect the phone and open http://192.168.71.1.
- To join an existing network instead, build with `WIFI_SSID=... WIFI_PASS=... cargo run --release`. The assigned IP is printed on the serial console. Credentials are compiled in from the environment and are not stored in the repository.

`GET /data` returns `{"raw","raw_min","raw_max","adc_mv","atten_db","range_mv"}`; `POST /atten?db=6` selects an attenuation.

## Fitted values

The page defaults to R1 = 10k, R2 = 1k, RF1 = 10k, R3 = 9.1k, R4 = 6.2k (these differ from the CAD BOM). Change the values on the page after any rework; they are saved in the phone's browser.
