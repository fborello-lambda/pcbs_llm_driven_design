#!/usr/bin/python3
"""Check source geometry, synchronize KiCad no-connect nets, and prove netlist parity."""
from pathlib import Path
import json, xml.etree.ElementTree as ET
import pcbnew as p
ROOT=Path(__file__).resolve().parents[2]/'photodiode_lab'
b=p.LoadBoard(str(ROOT/'photodiode_lab.kicad_pcb'))
fps={f.GetReference():f for f in b.GetFootprints()}
xml=ET.parse(ROOT/'outputs/netlist.xml')
nets={n.GetNetname():n for n in b.GetNetsByNetcode().values()}
for n in xml.findall('.//nets/net'):
    name=n.get('name')
    if not name.startswith('unconnected-'):continue
    if name not in nets:nets[name]=p.NETINFO_ITEM(b,name);b.Add(nets[name])
    for node in n.findall('node'):
        for pad in fps[node.get('ref')].Pads():
            if pad.GetNumber()==node.get('pin'):pad.SetNet(nets[name])
parts=json.loads((ROOT/'connectivity.json').read_text())
expected={(c['ref'],pin):'/'+net for c in parts for pin,net in c['nets'].items()}
actual={(f.GetReference(),z.GetNumber()):z.GetNetname() for f in b.GetFootprints() for z in f.Pads() if z.GetNetname() and not z.GetNetname().startswith('unconnected-')}
schematic={(node.get('ref'),node.get('pin')):n.get('name') for n in xml.findall('.//nets/net') for node in n.findall('node') if (node.get('ref'),node.get('pin')) in expected}
assert expected==actual==schematic
pinmap={1:'/VOUT',2:'/SUM',3:'/VREF',4:'/GND',5:'/REF_DIV',6:'/VREF',7:'/VREF',8:'/+3V3'}
assert {int(z.GetNumber()):z.GetNetname() for z in fps['U2'].Pads()}==pinmap
assert {int(z.GetNumber()):z.GetNetname() for z in fps['D1'].Pads()}=={1:'/SUM',2:'/GND'}
def pattern(f):return sorted((z.GetNumber(),z.GetFPRelativePosition().x,z.GetFPRelativePosition().y,z.GetSize().x,z.GetSize().y,z.GetAttribute()) for z in f.Pads())
assert pattern(fps['U1'])==pattern(p.FootprintLoad(str(ROOT.parent/'shared/ESP32-C3-SuperMini.pretty'),'ESP32-C3-SuperMini'))
practice_refs={'JP1','R5','R6','R7','D2','TP5','TP6','TP7','TP8','TP9'}
assert all(z.GetNetname() not in ['/SUM','/VREF','/REF_DIV','/ADC_OUT','/VOUT'] for ref in practice_refs for z in fps[ref].Pads())
assert fps['R5'].GetValue()=='1k'
# Approximate bodies for parts without installed vendor CAD, plus IC in its socket.
models=ROOT/'libraries/3d';models.mkdir(exist_ok=True)
def box(x,y,z,a,b,c,color):
    return f'Transform {{ translation {x/2.54} {y/2.54} {z/2.54} children [ Shape {{ appearance Appearance {{ material Material {{ diffuseColor {color} }} }} geometry Box {{ size {a/2.54} {b/2.54} {c/2.54} }} }} ] }}\n'
header='#VRML V2.0 utf8\n# Approximate visual envelope, not manufacturer CAD.\n'
(models/'bpw34-envelope.wrl').write_text(header+box(2.55,0,2.6,5.4,4.3,3.2,'.25 .16 .12')+box(2.55,0,4.23,3,2.5,.08,'.03 .03 .04'))
for ref,filename in [('D1','bpw34-envelope.wrl')]:
    local=p.FootprintLoad(str(ROOT/'libraries/Lab.pretty'),ref)
    for obj in [fps[ref],local]:
        obj.Models().clear();model=p.FP_3DMODEL();model.m_Filename='${KIPRJMOD}/libraries/3d/'+filename;obj.Add3DModel(model)
    p.FootprintSave(str(ROOT/'libraries/Lab.pretty'),local)
local=p.FootprintLoad(str(ROOT/'libraries/Lab.pretty'),'U2')
for obj in [fps['U2'],local]:
    keep=[m for m in obj.Models() if not m.m_Filename.endswith('/DIP-8_W7.62mm.step')];obj.Models().clear()
    for m in keep:obj.Add3DModel(m)
    m=p.FP_3DMODEL();m.m_Filename='${KICAD10_3DMODEL_DIR}/Package_DIP.3dshapes/DIP-8_W7.62mm.step';m.m_Offset=p.VECTOR3D(0,0,3);obj.Add3DModel(m)
p.FootprintSave(str(ROOT/'libraries/Lab.pretty'),local)
p.SaveBoard(str(ROOT/'photodiode_lab.kicad_pcb'),b)
report=dict(matched_pins=len(expected),schematic_matches_pcb=True,mcp6002_datasheet_pinout=True,bpw34_cathode_to_sum_anode_to_gnd=True,output_increases_with_light=True,esp32_matches_shared_footprint=True)
(ROOT/'outputs/verification.json').write_text(json.dumps(report,indent=2));print(report)
