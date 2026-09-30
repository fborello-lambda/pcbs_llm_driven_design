#!/usr/bin/python3
"""Place legible silkscreen, normalize net names, and check schematic connectivity."""
from pathlib import Path
import json, math, xml.etree.ElementTree as ET
import pcbnew as p
ROOT=Path(__file__).resolve().parents[2]/'dimmer'
b=p.LoadBoard(str(ROOT/'esp32_dimmer.kicad_pcb'))
def rect(item,margin=0):
    bb=item.GetBoundingBox();return [p.ToMM(bb.GetX())-margin,p.ToMM(bb.GetY())-margin,p.ToMM(bb.GetRight())+margin,p.ToMM(bb.GetBottom())+margin]
def overlaps(a,z):return a[0]<z[2] and a[2]>z[0] and a[1]<z[3] and a[3]>z[1]
pads=[rect(pad,.22) for fp in b.GetFootprints() for pad in fp.Pads()]
obstacles=list(pads)+[[0,36.7,100,39.3]]
for fp in b.GetFootprints():
    if fp.GetReference().startswith('H'):
        fp.SetAttributes(fp.GetAttributes()|p.FP_BOARD_ONLY|p.FP_EXCLUDE_FROM_BOM|p.FP_EXCLUDE_FROM_POS_FILES)
    for it in fp.GraphicalItems():
        if it.GetLayer()!=p.F_SilkS:continue
        rr=rect(it,.1)
        if any(overlaps(rr,pp) for pp in pads) or overlaps(rr,[0,36.7,100,39.3]):
            it.SetLayer(p.F_Fab)
        else:obstacles.append(rr)
texts=[it for it in b.GetDrawings() if isinstance(it,p.PCB_TEXT) and it.GetLayer()==p.F_SilkS]
texts += [fp.Reference() for fp in b.GetFootprints() if fp.Reference().IsVisible()]
log=[]
for t in texts:
    old=t.GetPosition(); x=p.ToMM(old.x);y=p.ToMM(old.y)
    options=[(0,0)]+sorted([(i*.5,j*.5) for i in range(-20,21) for j in range(-16,17)],key=lambda a:a[0]**2+a[1]**2)
    found=False
    for dx,dy in options:
        t.SetPosition(p.VECTOR2I(p.FromMM(x+dx),p.FromMM(y+dy)));rr=rect(t,.13)
        if rr[0]<1 or rr[2]>99 or rr[1]<1 or rr[3]>99:continue
        if any(overlaps(rr,r) for r in obstacles):continue
        found=True;obstacles.append(rr);break
    if not found:t.SetPosition(old);log.append('No silkscreen position: '+t.GetText())
for net in b.GetNetsByNetcode().values():
    name=net.GetNetname()
    if name and not name.startswith('/') and not name.startswith('unconnected-'):
        net.SetNetname('/'+name)
p.SaveBoard(str(ROOT/'esp32_dimmer.kicad_pcb'),b)
parts=json.loads((ROOT/'docs/connectivity.json').read_text());expected={(c['ref'],pin):net for c in parts for pin,net in c['nets'].items()}
actual={(fp.GetReference(),pad.GetNumber()):pad.GetNetname().lstrip('/') for fp in b.GetFootprints() for pad in fp.Pads() if pad.GetNetname() and not pad.GetNetname().lstrip('/').startswith('unconnected-')}
xml=ET.parse(ROOT/'outputs/netlist.xml');schematic={}
for net in xml.findall('.//nets/net'):
    for node in net.findall('node'):
        key=node.attrib['ref'],node.attrib['pin']
        if key in expected:schematic[key]=net.attrib['name'].lstrip('/')
assert expected==actual, ('PCB mismatch',set(expected.items())^set(actual.items()))
assert expected==schematic, ('Schematic mismatch',set(expected.items())^set(schematic.items()))
result={'connected_pins_checked':len(expected),'schematic_pcb_match':True,'silkscreen_notes':log}
(ROOT/'outputs/connectivity-check.json').write_text(json.dumps(result,indent=2));print(result)
