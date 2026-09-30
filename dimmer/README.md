# ESP32-C3 220 Vac halogen dimmer

[![3D preview](docs/board-3d.png)](docs/board-3d.png)

Two-layer 100 x 100 mm phase-control dimmer for a nominal 220 Vac, 50 Hz, 1000 W halogen load. An external SELV 3.3 V I2C connection powers the ESP32-C3 SuperMini. A MOC3052M provides random-phase optical triggering, an H11AA1 detects zero crossings, and a BTA16-800BW switches the load.

## Files

- [KiCad project](esp32_dimmer.kicad_pro)
- [Schematic PDF](docs/schematic.pdf)
- [BOM CSV](docs/BOM.csv)
- [Revision notes](docs/REVISION_J.md)
- [Zero-cross calculations](docs/ZERO_CROSS_CALCULATION.md)
- [Design calculations](docs/DESIGN_CALCULATIONS.md)
- [Fabrication requirements](docs/PCB_FABRICATION.md)

## Safety

This board switches lethal mains voltage and is not certified. It must not be treated as safe solely because ERC and DRC pass. Preserve the isolation slot and explicit MAINS/SELV constraints, and independently review creepage, clearance, fuse coordination, thermal performance, component ratings, enclosure, and fabrication capability before energizing it.
