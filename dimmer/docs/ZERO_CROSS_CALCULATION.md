# H11AA1 zero-cross detector calculation

Revision J uses two 47 kOhm, 1 W, ±5% resistors in series to feed the H11AA1 from the protected live conductor. This is a prototype value that requires measurement; it is not a guaranteed timing specification over every optocoupler, ESP32 and temperature tolerance.

## Output-current requirement

The ESP32-C3 specifies a maximum low-level input voltage of `0.25 × VDD`. At 3.3 V this is 0.825 V. With a typical 45 kOhm internal pull-up, the H11AA1 transistor must sink approximately:

`IC = (3.3 - 0.825) / 45 kOhm = 55 uA`

The internal pull-up value is typical and has no guaranteed minimum or maximum in the cited table. The design therefore cannot claim a closed worst-case margin without measuring the actual board or adding a specified external pull-up.

## Input current with 94 kOhm

For small-current estimates, take the conducting LED drop as approximately 1.2 V:

`IF(t) ≈ max(0, |sqrt(2) × Vrms × sin(2πft)| - 1.2 V) / (R7 + R8)`

At 220 Vac and 94 kOhm total, peak input current is approximately 3.30 mA. At the low-line and high-resistance corner, 198 Vac and 98.7 kOhm, peak current is approximately 2.83 mA.

Vishay guarantees H11AA1 CTR at 10 mA, 10 V VCE and 25 °C. That guaranteed value cannot be directly extrapolated to the roughly 1–3 mA and low-VCE operating region used here. If an illustrative effective CTR of 5% is assumed, 55 uA output current requires 1.10 mA LED current. The assumption must be verified on the finished hardware.

## Timing offset

The H11AA1 output pulse does not mark the exact mains zero. With a conditional 1.10 mA LED-current threshold, 94 kOhm and 1.2 V LED drop, the logic transition occurs around 104.6 V instantaneous mains voltage. At 220 Vac and 50 Hz, that is about 1.09 ms after the zero crossing. Actual timing depends on input thresholds, pull-up value, CTR, temperature, storage time and the two LEDs' mismatch.

Firmware must characterize both edges, compensate the measured delay and predict later crossings with a local timer. Loss of valid zero-cross pulses must inhibit firing.

## Resistor dissipation

Ignoring the LED drop slightly overestimates heating:

`Ptotal ≈ Vrms² / (R7 + R8)`

| Condition | Total | Each resistor |
| --- | ---: | ---: |
| 220 V, nominal values | 0.515 W | 0.257 W |
| 242 V, nominal values | 0.623 W | 0.312 W |
| 242 V, both resistors at -5% | 0.656 W | 0.328 W |

Use flameproof metal-oxide THT resistors rated at least 1 W each, with adequate pulse capability and at least 250 V working-voltage rating per component. Confirm the purchased body's dimensions against the 11.9 × 4.5 mm, 20.32 mm-pitch footprint.

## Required validation

Measure the ZC signal against the true mains zero at 198, 220 and 242 Vac, cold and hot, using appropriately isolated instrumentation. Verify both half cycles, input-high and input-low margin, delay stability, switching-noise immunity, resistor temperature and fail-safe firmware behavior.

Primary references:

- [Vishay H11AA1 data sheet](https://www.vishay.com/docs/83608/h11aa1.pdf)
- [Vishay application note AN45](https://www.vishay.com/docs/83706/applicationnote45.pdf)
- [Espressif ESP32-C3 data sheet](https://www.espressif.com/sites/default/files/documentation/esp32-c3_datasheet_en.pdf)
