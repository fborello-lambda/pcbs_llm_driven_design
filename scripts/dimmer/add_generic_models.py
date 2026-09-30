#!/usr/bin/python3
"""Attach the manufacturer STEP to its matching KiCad header footprint."""
from pathlib import Path
import pcbnew as p
ROOT=Path(__file__).resolve().parents[2]/'dimmer'
assert (ROOT/'libraries/3d/691311400102.stp').read_text().startswith('ISO-10303-21;')
b=p.LoadBoard(str(ROOT/'esp32_dimmer.kicad_pcb'))
for fp in b.GetFootprints():
    if fp.GetReference() not in ['J2','J3']: continue
    fp.Models().clear()
    m=p.FP_3DMODEL(); m.m_Filename='${KIPRJMOD}/libraries/3d/691311400102.stp'
    # Manufacturer origin is body centre; normalize seating plane and pin centres.
    m.m_Offset=p.VECTOR3D(3.81,0.25,6.0)
    m.m_Rotation=p.VECTOR3D(0,0,180)
    fp.Add3DModel(m)
    clone=p.FOOTPRINT(fp); clone.SetOrientationDegrees(0); clone.SetPosition(p.VECTOR2I(0,0))
    p.FootprintSave(str(ROOT/'libraries/Dimmer.pretty'),clone)
p.SaveBoard(str(ROOT/'esp32_dimmer.kicad_pcb'),b)
