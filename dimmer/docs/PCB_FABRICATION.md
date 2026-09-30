# PCB fabrication review

This 100 x 100 mm board is within ordinary low-cost Chinese PCB-house capabilities. It is a two-layer through-hole design with 1.6 mm FR-4, 70 um (2 oz) copper, green solder mask, rounded 4 mm corners, four 3.2 mm NPTH M3 holes, and 2 mm routed isolation slots. Ask for routed slots from the provided Edge.Cuts Gerber; do not order the board without reviewing the board-house Gerber preview.

Recommended order parameters:

| Parameter | Request |
| --- | --- |
| Layers | 2 |
| Finished board thickness | 1.6 mm |
| Copper | 2 oz / 70 um, both layers |
| Surface finish | HASL is acceptable for through-hole assembly |
| Board outline | 100 x 100 mm, routed, 4 mm rounded corners |
| Slots | 2 mm plated-free routed slots, per Edge.Cuts |
| Holes | Four 3.2 mm NPTH mounting holes plus component drills |

The 8 mm SELV-to-mains copper separation and the routed slots are deliberate. A manufacturer can fabricate them, but fabrication does not certify the product for mains use. Do not ask for panel tabs, copper thieving, or test features that bridge the slots or reduce the separation. Inspect the Gerber preview for all slots, the 4 mm high-current tracks, the short 1.75 mm TO-220 necks required by the 2.54 mm lead pitch and 0.8 mm clearance, and the TO-220 footprint before ordering.

The order is PCB-only. The module, fuse holder, fuse, MOV, optocouplers, BTA16-800BW, terminal blocks, resistors, and heatsink require manual through-hole assembly. Verify each purchased part against its footprint before ordering a production quantity.
