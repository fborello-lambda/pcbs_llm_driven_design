# Debugging notes: Wi-Fi missing on a phone charger

A look back at the first bring-up of this firmware, where the fix was one line but the search took many flashes.

## The symptom

On the laptop's USB everything worked. On a phone charger the red power LED was on but the `esp32-dimmer` network never appeared.

## The cause

The firmware printed status with Rust's `println!`. With no USB host attached, the ESP-IDF USB serial console returns an error on every write, and `println!` panics when a write fails:

```
panicked at .../std/src/io/stdio.rs:1166:9:
failed printing to stdout: Success (os error 0)
```

The board panicked during start-up, rebooted, and did it again, forever. The fix was to log with `log::info!` (ESP-IDF's logger ignores write errors, like C's `printf`) and never use `println!` in this firmware.

## How the search went

1. **Antenna.** The laptop could not see the network, so the TX power was capped at 8.5 dBm, a known SuperMini workaround. This may or may not have mattered; the phone already saw the network on the laptop before the change.
2. **Charger power.** A brownout from a weak charger was assumed next. A boot/heartbeat LED was added, and the start-up TX power was lowered.
3. **USB data lines.** Then a chip reset from the charger's D+/D- signalling. The LED was made to blink the reset reason.
4. **Evidence.** Only then was a reset log written to flash. It showed `4/1`: a *panic* during start-up, not a power or USB reset. One more flash to save the panic message gave the answer immediately.

## What should have happened

- **Read the clue first.** "Works with a computer, fails without one" points straight at the one thing a computer provides besides power: a USB host. The first question should have been "what does the firmware do with the USB console?", and a search for `println!` would have found it in a minute.
- **Collect evidence before fixing.** Three changes (TX power, start-up power, LED patterns) were made on guesses. Recording the reset reason and the panic message should have been step one, not step four. A reset reason alone already rules out whole classes of causes.
- **Don't filter the evidence.** The first reset-reason blink skipped "normal" reasons, so the panic stayed hidden behind a pattern that looked like a power loop.
- **Know the language's failure modes.** `println!` panicking on a write error is documented Rust behaviour. On a microcontroller where stdout can disappear, it is a trap; firmware should log through a path that cannot fail.

## Kept from the session

- Status output uses `log::info!`.
- The blue LED shows three quick flashes at boot and one short flash per second when Wi-Fi is up, so the state is visible without a cable.
- The Wi-Fi TX power stays capped (8.5 dBm, 10 dBm at start-up); it is enough for a phone in the same room.

The photodiode lab and remote controller firmware also use `println!` and carry the same latent bug.

## Second bug: trusting the design estimate

On mains the frequency jumped between 25 and 50 Hz and the lamp never fired. The firmware rejected zero-cross pulses shorter than 300 µs as noise because the design calculation predicted 2.2 ms. The real pulses were 30–100 µs, so almost every one was thrown away.

This time the evidence came first: per-second counters for edges, pulses, noise, invalid pulses and the width and half-period range went onto the status page before any fix. The first reading showed about 270 edges per second but **0 accepted pulses**, which pointed at the width limit in one step. The lesson is the same as above, from the other side: measure the signal before writing limits around an estimate of it.
