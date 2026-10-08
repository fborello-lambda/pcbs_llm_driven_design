# OLED selection — revision G

Revision G uses the 0.96-inch SSD1306 I2C reference module identified by LCDWiki as MC096VW/MC096VX. Its nominal board envelope is 27.3 x 27.8 mm. References: [LCDWiki MC096VX](https://www.lcdwiki.com/0.96inch_OLED_Module_(IIC-4P_SKU:MC096VX)) and the [MC096-015 mechanical drawing](https://www.lcdwiki.com/images/1/19/MC096-015.jpg).

With the display viewed from the front and its header at the top, the four 2.54 mm pitch pins are, left to right:

`VCC  GND  SCL  SDA`

The carrier footprint is a female 1x4 socket on the PCB front. Its first header pad is at (16.19, 9.5) mm and the four-pad row is centred at x=20 mm. Prepare the display with a straight male header soldered from the display front, leaving the pins pointing rearward. Solder the carrier socket from the back before installing the battery holder; the OLED is removable and can be fitted later.

H5 and H6 are board-only 2.2 mm M2 clearance holes at (8.35, 33.8) and (31.65, 33.8) mm. They match the vendor drawing's 2 mm edge margins and 23.3 mm horizontal pitch. Use two insulating M2 spacers to support the OLED lower edge. Select a low-profile OLED rear head no taller than 1 mm and match spacer height to the actual socket/header stack; the nominal OLED underside is approximately 9.2 mm above the footprint plane.

The module envelope and carrier model are approximate mechanical references. Confirm the actual module's outline, header position, pin order, polarity, rear-head height and socket stack before fabrication. Generic 0.96-inch modules are not universally compatible; some reverse VCC and GND despite using the same I2C interface. The SSD1306 module fitted on the first build is one of them (GND, VDD, SCK, SDA); see [`LESSONS.md`](LESSONS.md).

This selection matches the portrait 40 x 100 mm revision G board. The joystick centre is (20, 55.5) mm, the front button centres are (8, 40), (20, 40), and (32, 40) mm, and the directly soldered ESP32-C3 SuperMini is at (13.5, 90) mm, rotated 90 degrees, with USB facing the left exterior edge. The module lies completely within the PCB outline. The rear MPD BK-18650-PC2 holder occupies the upper body area, so install the OLED carrier and spacers before fitting the holder and validate the complete stack on a prototype.
