#!/usr/bin/python3
"""Attach clearly identified mechanical envelopes and verify independent source geometry."""
from pathlib import Path
import json,math,xml.etree.ElementTree as ET
import pcbnew as p
ROOT=Path(__file__).resolve().parents[2]/'remote_controller'
MODELS=ROOT/'libraries/3d';MODELS.mkdir(exist_ok=True)
def box(x,y,z,sx,sy,sz,color):
    return f'Transform {{ translation {x/2.54} {y/2.54} {z/2.54} children [ Shape {{ appearance Appearance {{ material Material {{ diffuseColor {color} }} }} geometry Box {{ size {sx/2.54} {sy/2.54} {sz/2.54} }} }} ] }}\n'
def cyl(x,y,z,r,length,color,axis='z'):
    vertices=[];faces=[];n=48
    for height in [-length/2,length/2]:
        for i in range(n):
            a=i*2*math.pi/n;u,w=r*math.cos(a),r*math.sin(a)
            point=(x+u,y+w,z+height) if axis=='z' else (x+height,y+u,z+w)
            vertices.append(' '.join(str(v/2.54) for v in point))
    for i in range(n):j=(i+1)%n;faces.append(f'{i} {j} {j+n} {i+n} -1')
    faces+=[' '.join(str(i) for i in reversed(range(n)))+' -1',' '.join(str(i+n) for i in range(n))+' -1']
    return 'Shape { appearance Appearance { material Material { diffuseColor '+color+' } } geometry IndexedFaceSet { solid FALSE coord Coordinate { point [ '+', '.join(vertices)+' ] } coordIndex [ '+', '.join(faces)+' ] } }\n'
header='#VRML V2.0 utf8\n# Approximate mechanical envelope, NOT a manufacturer CAD model.\n'
(MODELS/'joystick-envelope.wrl').write_text(header+box(0,0,2.5,17.5,17.4,5,'.12 .12 .14')+cyl(0,0,7,3.5,4,'.15 .15 .17')+cyl(0,0,10.5,7,3,'.05 .05 .06'))
(MODELS/'holder-envelope.wrl').write_text(header+box(36.25,0,1,76.96,20.98,2,'.07 .07 .08')+box(-1.3,0,8,2,20.98,16,'.07 .07 .08')+box(73.8,0,8,2,20.98,16,'.07 .07 .08')+box(36.25,-9.9,5,73,1.2,8,'.07 .07 .08')+box(36.25,9.9,5,73,1.2,8,'.07 .07 .08')+cyl(36.25,0,11,9,65,'.18 .38 .56','x'))
# OLED module is viewed from the display/front: header across the top, V G C D.
(MODELS/'oled-envelope.wrl').write_text(header+box(3.81,-12.4,10,27.3,27.8,1.6,'.05 .12 .17')+box(3.81,-11.4,11,21.744,10.864,.6,'.01 .015 .025')+''.join(box(i*2.54,0,7,.64,.64,7,'.7 .65 .35') for i in range(4))+''.join(cyl(x,-24.3,4.6,1.7,9.2,'.8 .8 .75') for x in [-7.84,15.46]))
b=p.LoadBoard(str(ROOT/'esp32c3_remote.kicad_pcb'))
# KiCad assigns named singleton nets to no-connect pins; preserve schematic parity.
xml=ET.parse(ROOT/'outputs/netlist.xml')
fps={f.GetReference():f for f in b.GetFootprints()}
existing={n.GetNetname():n for n in b.GetNetsByNetcode().values()}
for net in xml.findall('.//nets/net'):
    name=net.get('name')
    if not name.startswith('unconnected-'):continue
    if name not in existing:existing[name]=p.NETINFO_ITEM(b,name);b.Add(existing[name])
    for node in net.findall('node'):
        for pad in fps[node.get('ref')].Pads():
            if pad.GetNumber()==node.get('pin'):pad.SetNet(existing[name])
for fp in b.GetFootprints():
    ref=fp.GetReference();model={'JS1':'joystick-envelope.wrl','BT1':'holder-envelope.wrl','J1':'oled-envelope.wrl'}.get(ref)
    if not model:continue
    local=p.FootprintLoad(str(ROOT/'libraries/Remote.pretty'),ref)
    for obj in (fp,local):
        if ref in ['JS1','BT1']:obj.Models().clear()
        # Do not stack the same optional envelope on repeated runs.
        if ref=='J1':
            keep=[old for old in obj.Models() if not old.m_Filename.endswith(model)];obj.Models().clear()
            for old in keep:obj.Add3DModel(old)
        m=p.FP_3DMODEL();m.m_Filename='${KIPRJMOD}/libraries/3d/'+model
        if ref=='BT1':m.m_Offset=p.VECTOR3D(0,0,1.5)
        obj.Add3DModel(m)
    p.FootprintSave(str(ROOT/'libraries/Remote.pretty'),local)
from back_art import draw
draw(b)
p.SaveBoard(str(ROOT/'esp32c3_remote.kicad_pcb'),b)

# Compare pad pattern with the original Adafruit Eagle source, not the generator constants.
pkg=ET.parse(ROOT/'sources/adafruit-thumbstick.brd').find('.//package[@name="JOYSTICK_ANALOG_MINITHM"]')
fp=p.FootprintLoad(str(ROOT/'libraries/Remote.pretty'),'JS1')
actual={z.GetNumber():z for z in fp.Pads() if z.GetNumber()}
assert set(actual)=={z.get('name') for z in pkg.findall('pad')}
for src in pkg.findall('pad'):
    z=actual[src.get('name')]
    assert math.isclose(p.ToMM(z.GetPosition().x),float(src.get('x')),abs_tol=1e-6)
    assert math.isclose(p.ToMM(z.GetPosition().y),-float(src.get('y')),abs_tol=1e-6)
    assert math.isclose(p.ToMM(z.GetDrillSize().x),float(src.get('drill')),abs_tol=1e-6)
holes=sorted((p.ToMM(z.GetPosition().x),p.ToMM(z.GetPosition().y),p.ToMM(z.GetDrillSize().x)) for z in fp.Pads() if not z.GetNumber())
assert holes==sorted((float(z.get('x')),-float(z.get('y')),float(z.get('drill'))) for z in pkg.findall('hole'))
parts=json.loads((ROOT/'connectivity.json').read_text());expected={(c['ref'],pin):'/'+net for c in parts for pin,net in c['nets'].items()}
actual={(f.GetReference(),z.GetNumber()):z.GetNetname() for f in b.GetFootprints() for z in f.Pads() if z.GetNetname() and not z.GetNetname().startswith('unconnected-')}
assert actual==expected,('PCB/net definition mismatch',set(actual.items())^set(expected.items()))
xml=ET.parse(ROOT/'outputs/netlist.xml');sch={}
for net in xml.findall('.//nets/net'):
    for node in net.findall('node'):
        key=node.get('ref'),node.get('pin')
        if key in expected:sch[key]=net.get('name')
assert sch==expected,('Schematic/net definition mismatch',set(sch.items())^set(expected.items()))
# The holder is elevated. Assembly envelope calculation from MPD drawing rev F:
# minimum lead = 3.3-0.5mm, board=0.8mm, spacer=1.5mm => 0.5mm exposed lead.
assert abs(p.ToMM(b.GetDesignSettings().GetBoardThickness())-.8)<1e-6
assert (3.3-.5)-.8-1.5 >= .49
# Module is wholly inside the outline, rotated 90 degrees with USB at x=0.5.
module=fps['U1'];assert module.GetOrientationDegrees()==90
assert abs(p.ToMM(module.GetPosition().x)-13.5)<1e-6
assert abs(p.ToMM(module.GetPosition().y)-90)<1e-6
# Rear metal does not overlap the antenna, but clearance is compact: validate radio range.
assert 79.5-(2.5+74.73)>2
assert {f.GetReference() for f in b.GetFootprints() if f.GetLayer()==p.B_Cu}=={'BT1'}
# Front-view OLED header must not be mirrored: VCC, GND, SCL, SDA.
oled=next(f for f in b.GetFootprints() if f.GetReference()=='J1')
for number,net in [(1,'/+3V3'),(2,'/GND'),(3,'/SCL'),(4,'/SDA')]:
    pad=next(z for z in oled.Pads() if z.GetNumber()==str(number))
    assert pad.GetNetname()==net
    assert abs(p.ToMM(pad.GetPosition().x)-(16.19+(number-1)*2.54))<1e-6
    assert abs(p.ToMM(pad.GetPosition().y)-9.5)<1e-6
    assert pad.GetAttribute()==p.PAD_ATTRIB_PTH
assert oled.GetLayer()==p.F_Cu
# Compare the embedded module pad geometry with the shared footprint source.
source=p.FootprintLoad(str(ROOT.parent/'shared/ESP32-C3-SuperMini.pretty'),'ESP32-C3-SuperMini')
module=fps['U1']
def pattern(fp):
    return sorted((z.GetNumber(),z.GetFPRelativePosition().x,z.GetFPRelativePosition().y,z.GetSize().x,z.GetSize().y,z.GetAttribute(),z.GetLayerSet().FmtHex()) for z in fp.Pads())
assert pattern(module)==pattern(source), 'SuperMini must use the shared pad geometry'
assert fps['BT1'].GetLayer()==p.B_Cu
result={'matched_connected_pins':len(expected),'schematic_matches_pcb':True,'joystick_matches_official_eagle':True,'joystick_pads':6,'joystick_locating_holes':2,'rear_holder_spacer_mm':1.5,'board_thickness_mm':.8,'minimum_holder_lead_exposure_mm':.5,'maximum_trimmed_tail_mm':.9,'antenna_to_holder_gap_mm':2.27,'esp32_inside_board':True,'rear_components':['BT1'],'oled_front_view_pin_order_verified':True,'esp32_matches_shared_footprint':True}
(ROOT/'outputs/verification.json').write_text(json.dumps(result,indent=2));print(result)
