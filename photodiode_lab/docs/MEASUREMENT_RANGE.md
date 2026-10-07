# Measurement range

How to choose R1/R2, RF1, R3/R4 and the ADC attenuation so the light you measure fills the ADC. The firmware page does the same calculations live (see [`../firmware/README.md`](../firmware/README.md)).

Switch power off before changing any part.

## The signal path

```
light → BPW34 → TIA (RF1) → VOUT → R3/R4 divider → ADC_OUT → ESP32-C3 ADC
                   ↑
            VREF from R1/R2
```

| Part | What it does |
|---|---|
| R1, R2 | Set the dark level VREF |
| RF1 | Sets how many volts each µA of light gives |
| R3, R4 | Scale VOUT down for the ADC (R3 on top, R4 to GND) |
| Attenuation | Sets the ADC input window (button on the page) |

## The five formulas

**1. Dark level.** R1 and R2 divide the 3.3 V supply:

$$V_{REF} = V_{DD} \cdot \frac{R_2}{R_1 + R_2}$$

**2. Light.** The photocurrent $I$ adds $I \cdot R_{F1}$ on top of the dark level:

$$V_{OUT} = V_{REF} + I \cdot R_{F1}$$

**3. Divider.** R3 and R4 pass a fraction $k$ of VOUT to the ADC:

$$k = \frac{R_4}{R_3 + R_4}$$

$$V_{ADC} = k \cdot V_{OUT}$$

**4. Fit the ADC window.** VOUT can rise to about 3.25 V (the op-amp stops just below 3.3 V). That must still fit in the window $V_{FS}$:

$$k \le \frac{V_{FS}}{3.25}$$

**5. Choose RF1.** The brightest light $I_{max}$ should just reach the top:

$$R_{F1} = \frac{3.25 - V_{REF}}{I_{max}}$$

## Step by step

### Step 1: R1 and R2 (dark level)

| R1 / R2 | VREF | Room left for light |
|---|---|---|
| 22k / 1k | 0.14 V | 3.11 V |
| **10k / 1k** | **0.30 V** | **2.95 V** |
| 10k / 2.2k | 0.59 V | 2.66 V |
| 10k / 10k | 1.65 V | 1.60 V |

More light only pushes VOUT up, so a high VREF wastes range. A little VREF is still useful: it reverse-biases the photodiode (slightly faster) and keeps the dark reading off the bottom of the op-amp. 10k / 1k is a good choice.

### Step 2: RF1 (light range)

With VREF = 0.30 V, the largest current before clipping is 2.95 V / RF1:

| RF1 | Max current | Good for |
|---|---|---|
| 10k | 295 µA | Flashlight, window light |
| 33k | 89 µA | Desk lamp |
| 100k | 30 µA | Normal room light |
| 1M | 3 µA | Dim room |

To choose by measurement: start with 10k, press **Reset** in the *Light* card, shine your brightest light, and read *RF1 for that light*. It uses formula 5 with 10 % margin. If the reading clipped, the page asks for a smaller RF1 first, because a clipped peak underestimates the light.

### Step 3: attenuation and R3/R4 (ADC fit)

Each attenuation has a window $V_{FS}$. Formula 4 gives the largest k; these E24 pairs fit with 5 % margin:

| Attenuation | Window $V_{FS}$ | Largest k | R3 / R4 |
|---|---|---|---|
| 0 dB | 0.75 V | 0.23 | 20k / 5.6k |
| 2.5 dB | 1.05 V | 0.32 | 68k / 30k |
| 6 dB | 1.3 V | 0.40 | 18k / 11k |
| 12 dB | 2.5 V | 0.77 | 10k / 27k |

Never wire VOUT straight to the ADC: 3.3 V is above every window.

When k is at its limit for the window, the smallest current step is about $3.25\ \text{V} / (4095 \cdot R_{F1})$ whatever the attenuation. So the attenuation only decides which divider you need; RF1 decides the resolution. With a smaller k the step is larger: the page shows the real value as *Smallest step*.

### Step 4: check on the page

Enter your parts in *Parts on your board*, in kΩ (`9.1`, `9,1`, `820` or `1M` all work; a red box means the value was not understood). The card *Does it use the whole ADC?* shows how much of the window your light uses. Aim for 75 % or more and never see "Clipping".

## Example: the current board

R1 = 10k, R2 = 1k, RF1 = 10k, R3 = 9.1k, R4 = 6.2k, attenuation 12 dB.

| Step | Calculation | Result |
|---|---|---|
| VREF | 3.3 × 1 / (10 + 1) | 0.30 V |
| k | 6.2 / (9.1 + 6.2) | 0.405 |
| ADC in the dark | 0.405 × 0.30 | 122 mV |
| ADC at max light | 0.405 × 3.25 | 1317 mV |
| Window used | (1317 − 122) / 2500 | 48 % |

Only half the window is used. Three ways to improve it:

1. **Press 6 dB.** No soldering. Uses about 90 %; only the brightest 1.4 % of the light range clips, and the page marks this as acceptable.
2. **Fit R3 = 10k, R4 = 27k** and stay at 12 dB. Uses 86 %.
3. **Fit RF1 = 100k** if you measure room light. Ten times finer steps; full scale becomes 30 µA.
