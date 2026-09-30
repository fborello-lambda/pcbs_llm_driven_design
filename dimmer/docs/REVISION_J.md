# Revision J — snubberless triac

The design uses ST's **BTA16-800BW**. `BTA` identifies the insulated-tab package, `16` the series current class, `800` the repetitive peak off-state voltage rating, `B` the 50 mA trigger-current class, and `W` the Snubberless™ family. The `W` suffix is essential: BTA16-800B without `W` is the standard family, while BTA16-800BW is the snubberless one. Do not substitute the standard part without reviewing the RC network and commutation margins.

For the present 1000 W halogen load, which is principally resistive, the snubberless part allows the RC snubber to be omitted. This does not remove the MOV or F1. The triac remains a switching device rather than a safety disconnect, and it requires its external heatsink.

## Mains topology

`J2.1 (L_IN) -> F1 -> L_PROT -> Q2 MT2 -> Q2 MT1 (L_OUT) -> J3.1` is the switched conductor. `J2.2 (N) -> J3.2` is the direct neutral. This is equivalent to the supplied reference drawing: its `AC IN` connection feeds MT2 through the trigger resistors and its `AC OUT` is MT1/load output. R13 is the gate-to-MT1 resistor.

The MOC3052M is a random-phase optotriac. R11 and R12 feed its output from the protected live conductor; its output reaches the Q2 gate. U3/H11AA1 receives mains through R7 and R8 and reports the zero crossing on the isolated 3.3 V side.

## Pending hardware validation

- Select and test the exact T6.3AH / 250 V HBC 5x20 fuse against cold-filament inrush and prospective fault current.
- Test Q2 case and heatsink temperature at the actual enclosure temperature; the working target is heatsink thermal resistance <=4 C/W plus interface <=0.5 C/W.
- Validate the actual R11/R12 pulse rating, the BTA16 gate margin over temperature, MOV coordination with the 600 V MOC3052M, and the final insulation system.
- The BTA16-800BW data sheet specifies 50 mA maximum trigger current and a 14 A/ms minimum commutation capability without a snubber at 125 C. This is device capability, not a complete-system qualification.

## Manufacturing status

The board passes the current KiCad checks: 0 ERC violations, 0 DRC violations, 0 unconnected pads, and 0 schematic/PCB parity differences. Those checks validate the CAD geometry, not electrical safety or the 1000 W rating.
