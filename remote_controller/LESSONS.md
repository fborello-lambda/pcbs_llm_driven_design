# Lessons from the first revision G build

Notes from assembling and bringing up the first remote controller. Read these before building another one or starting the next revision.

## 1. The OLED module's power pins were reversed

The board's OLED socket (J1) expects this order, viewed from the front with the header at the top:

| Pin | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| Board socket J1 | VCC | GND | SCL | SDA |
| SSD1306 module used | **GND** | **VDD** | SCK (SCL) | SDA |

The data pins match (SCK is the I2C clock, SCL), but **VCC and GND are swapped**. Plugged straight in, the module receives 3.3 V on its ground pin and ground on its supply pin, which shorts the 3.3 V rail through the module.

What happened on this build: a short on the 3.3 V rail made the SuperMini's regulator very hot. The board then kept resetting, so USB connected and disconnected every couple of seconds, and flashing failed. It worked again once the short was removed.

For this module:

- Do not plug it directly into J1. Cross the first two wires (module GND to J1 pin 2, module VDD to J1 pin 1) with an adapter or jumper wires.
- Check the pin labels printed on every new module before powering it. Generic 0.96-inch SSD1306 modules come in both orders.
- With power off, measure 3V3 to GND on the SuperMini after fitting the OLED. It should not read close to 0 Ω.

For the next revision, consider:

- matching the footprint to the module actually bought (GND, VCC, SCL, SDA is very common);
- or adding solder jumpers to choose the power-pin order;
- and printing the expected pin order next to J1 on the silkscreen.

## 2. Telling a power fault from a firmware fault

A shorted or sagging 3.3 V rail looks like a USB problem:

- the Espressif USB device appears and disappears every ~2 s, with a new device number each time;
- `esptool`/`espflash` fails with `Errno 71 Protocol error`, `Write timeout` or `Input/output error`.

The test is download mode: hold BOOT while plugging in USB. The ESP32-C3 ROM then handles USB without running any firmware. If it still drops out, the fault is power or wiring, not firmware, and erasing the flash will not help. Unplug it and find the short before the regulator is damaged.

## 3. Thumbstick

- Fitting 10k for all the divider resistors (R3–R6) works: the ADC sees 0–1.65 V, inside the 12 dB range. The design value is 10k/22k (0–2.27 V); either is fine because the firmware calibrates.
- On this board the JOY_X channel (GPIO0) follows up/down and JOY_Y (GPIO1) follows left/right, both reversed. The firmware handles this with `SWAP_AXES`, `INVERT_X` and `INVERT_Y`.
- The stick does not return to exactly the same rest position after a large movement. A 10 % dead zone around the centre hides this.

## 4. Firmware pins

GPIO20 and GPIO21 are the ESP32-C3's default UART0 console pins, and on this board they are buttons. The firmware moves the console to the built-in USB serial port (`CONFIG_ESP_CONSOLE_USB_SERIAL_JTAG=y`). Keep that setting in any new firmware for this board.
