from pathlib import Path
import pcbnew as p
root=Path(__file__).resolve().parents[2]/'dimmer';b=p.LoadBoard(str(root/'esp32_dimmer.kicad_pcb'))
for f in b.GetFootprints():
 xy={'R11':(50,56),'R12':(50,66)}.get(f.GetReference())
 if xy:f.Reference().SetPosition(p.VECTOR2I(p.FromMM(xy[0]),p.FromMM(xy[1])))
for t in b.GetDrawings():
 if isinstance(t,p.PCB_TEXT) and 'DANGER' in t.GetText():t.SetPosition(p.VECTOR2I(p.FromMM(15),p.FromMM(40.6)))
p.SaveBoard(str(root/'esp32_dimmer.kicad_pcb'),b)
