#!/usr/bin/python3
"""Reuse the project's grid router with low-voltage geometry and complete pad routing."""
from pathlib import Path
import math,json
import pcbnew as p
ROOT=Path(__file__).resolve().parents[2]/'remote_controller'
# Load router algorithms, without the dimmer board setup or routing instructions.
import numpy as np,heapq
b=p.LoadBoard(str(ROOT/'esp32c3_remote.kicad_pcb'))
for t in list(b.GetTracks()):b.Remove(t)
S=.2;N=501;Y,X=np.mgrid[0:N,0:N]*S
fps={f.GetReference():f for f in b.GetFootprints()}
nets={n.GetNetname():n for n in b.GetNetsByNetcode().values()}
lv=set(nets)
exec((ROOT.parent/'scripts/grid_router.py').read_text(), globals())
def blocks(net,width):
    margin=width/2+.25+.11
    base=(X<1+width/2)|(X>39-width/2)|(Y<1+width/2)|(Y>99-width/2)
    base|=(X>23.8-width/2)&(Y>79.1-width/2)
    bad=np.stack([base.copy(),base.copy()])
    for f in features:
        typ,n,ls,a=f[:4]
        if n==net:continue
        if typ=='rect':
            sx,sy=f[4];dx=np.maximum(np.abs(X-a[0])-sx/2,0);dy=np.maximum(np.abs(Y-a[1])-sy/2,0);mask=dx*dx+dy*dy<margin*margin
        else:mask=segdist(a,f[4])<(margin+f[5]/2)**2
        for l in ls:bad[l]|=mask
    return bad
groups={}
for fp in b.GetFootprints():
    for z in fp.Pads():
        if z.GetNetname():groups.setdefault(z.GetNetname(),[]).append(z)
def ep(z):return pos(z.GetPosition()),([0] if z.GetAttribute()==p.PAD_ATTRIB_SMD else [0,1])
# Short, symmetric bridges for the paired contacts of the tactile switches.
for ref in ['SW2','SW3','SW4']:
    for number in ['1','2']:
        pair=[z for z in fps[ref].Pads() if z.GetNumber()==number]
        assert len(pair)==2
        assert route(pair[0].GetNetname(),ep(pair[0]),ep(pair[1]),.3,True)
failed=[]
priority=['/JOY_X','/JOY_Y','/BAT_ADC','/LIGHT_ADC','/SDA','/SCL','/BTN_ON','/BTN_OFF','/BTN_PRESET','/X_RAW','/Y_RAW','/VBAT','/VBUS','/+3V3','/GND']
for net in sorted(groups,key=lambda n:priority.index(n)):
    remaining=sorted(groups[net],key=lambda z:(z.GetParentFootprint().GetReference()!='U1',z.GetParentFootprint().GetReference(),z.GetNumber(),pos(z.GetPosition())))
    tree=[remaining.pop(0)]
    while remaining:
        a,z=min(((a,z) for a in tree for z in remaining),key=lambda pair:math.dist(ep(pair[0])[0],ep(pair[1])[0]))
        if z.GetParentFootprint().GetReference() in ['SW2','SW3','SW4'] and any(a.GetParentFootprint().GetReference()==z.GetParentFootprint().GetReference() and a.GetNumber()==z.GetNumber() for a in tree):
            remaining.remove(z);tree.append(z);continue
        width=.5 if net in ['/VBAT','/VBUS','/+3V3','/GND'] else .3
        if not route(net,ep(a),ep(z),width,True):
            if not route(net,ep(a),ep(z),.25,True):failed.append((net,pos(z.GetPosition())))
        remaining.remove(z);tree.append(z)
# Merge same-net vias whose drills would violate hole-to-hole clearance.
# Add copper on both layers to retain every branch endpoint after the merge.
kept=[]
for t in list(b.GetTracks()):
    if not isinstance(t,p.PCB_VIA):continue
    near=next((v for v in kept if v.GetNetCode()==t.GetNetCode() and math.dist(pos(v.GetPosition()),pos(t.GetPosition()))<.71),None)
    if near is None:kept.append(t);continue
    if t.GetPosition()!=near.GetPosition():
        for layer in [p.F_Cu,p.B_Cu]:
            link=p.PCB_TRACK(b);link.SetStart(t.GetPosition());link.SetEnd(near.GetPosition());link.SetWidth(p.FromMM(.25));link.SetLayer(layer);link.SetNetCode(t.GetNetCode());b.Add(link)
    b.Remove(t)
p.SaveBoard(str(ROOT/'esp32c3_remote.kicad_pcb'),b)
(ROOT/'outputs/routing.json').write_text(json.dumps({'failed':failed,'tracks':len(list(b.GetTracks()))},indent=2))
if failed:raise RuntimeError(failed)
