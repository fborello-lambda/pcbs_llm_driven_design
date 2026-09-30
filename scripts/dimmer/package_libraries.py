#!/usr/bin/python3
"""Freeze board-specific silkscreen edits and synchronize all schematic fields."""
from pathlib import Path
import xml.etree.ElementTree as ET
import json
import pcbnew as p
from build_design import parse,dump,kids,get
ROOT=Path(__file__).resolve().parents[2]/'dimmer'
b=p.LoadBoard(str(ROOT/'esp32_dimmer.kicad_pcb'))
xml=ET.parse(ROOT/'outputs/netlist.xml')
fps={f.GetReference():f for f in b.GetFootprints()}
for comp in xml.findall('.//components/comp'):
    fp=fps[comp.attrib['ref']]
    ds=comp.findtext('datasheet','');fp.GetField(p.FIELD_T_DATASHEET).SetText(ds)
for n in xml.findall('.//nets/net'):
    if not n.attrib['name'].startswith('unconnected-'):continue
    net=p.NETINFO_ITEM(b,n.attrib['name']);b.Add(net)
    for node in n.findall('node'):
        fp=fps.get(node.attrib['ref'])
        if fp:
            for pad in fp.Pads():
                if pad.GetNumber()==node.attrib['pin']:pad.SetNet(net)
libdir=ROOT/'libraries/Dimmer.pretty';libdir.mkdir(exist_ok=True)
newids={}
for ref,fp in fps.items():
    name=ref+'_'+str(fp.GetFPID().GetLibItemName())
    # Idempotent when repeated after a documentation-only edit.
    if name.startswith(ref+'_'+ref+'_'):name=name[len(ref)+1:]
    ident=p.LIB_ID('Dimmer',name);fp.SetFPID(ident)
    clone=p.FOOTPRINT(fp);clone.SetOrientationDegrees(0);clone.SetPosition(p.VECTOR2I(0,0))
    p.FootprintSave(str(libdir),clone)
    newids[ref]='Dimmer:'+name
schpath=ROOT/'esp32_dimmer.kicad_sch';sch=parse(schpath.read_text())
for sy in kids(sch,'symbol'):
    props={v[1]:v for v in kids(sy,'property')}
    ref=props['Reference'][2]
    if ref in newids:props['Footprint'][2]=newids[ref]
schpath.write_text(dump(sch)+'\n')
p.SaveBoard(str(ROOT/'esp32_dimmer.kicad_pcb'),b)
# Assign NC pins to their physical side of the barrier as well.
projpath=ROOT/'esp32_dimmer.kicad_pro';proj=json.loads(projpath.read_text())
patterns=proj['net_settings']['netclass_patterns']
for n in xml.findall('.//nets/net'):
    name=n.attrib['name']
    if not name.startswith('unconnected-'):continue
    node=n.find('node');ref=node.attrib['ref'];pin=node.attrib['pin']
    hv=(ref=='U2' and pin=='5') or (ref=='U3' and pin=='3') or ref=='K1'
    if not any(x['pattern']==name for x in patterns):patterns.append({'netclass':'MAINS' if hv else 'SELV','pattern':name})
projpath.write_text(json.dumps(proj,indent=2))
print('Packaged',len(newids),'local footprints and synchronized NC nets/fields.')
