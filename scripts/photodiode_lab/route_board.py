#!/usr/bin/python3
from pathlib import Path
import math,json
import pcbnew as p
import numpy as np,heapq
ROOT=Path(__file__).resolve().parents[2]/'photodiode_lab'
b=p.LoadBoard(str(ROOT/'photodiode_lab.kicad_pcb'))
for t in list(b.GetTracks()):b.Remove(t)
S=.2;N=501;Y,X=np.mgrid[0:N,0:N]*S
fps={f.GetReference():f for f in b.GetFootprints()};nets={n.GetNetname():n for n in b.GetNetsByNetcode().values()};features=[]
exec((ROOT.parent/'scripts/grid_router.py').read_text(), globals())
def blocks(net,width):
    margin=width/2+.25+.11;base=(X<1+width/2)|(X>99-width/2)|(Y<1+width/2)|(Y>99-width/2)
    base|=(X>69.5-width/2)&(X<90.5+width/2)&(Y>24.2-width/2)&(Y<39.5+width/2)
    for hx,hy in [(5,5),(95,5),(5,95),(95,95)]:base|=(X-hx)**2+(Y-hy)**2<(3+width/2)**2
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
failed=[];priority=['/SUM','/VOUT','/VREF','/REF_DIV','/ADC_OUT','/+3V3','/GND','/VBUS']
for net in sorted(groups,key=lambda n:(priority.index(n) if n in priority else 99,n)):
    remaining=sorted(groups[net],key=lambda z:(z.GetParentFootprint().GetReference()!='U2',z.GetParentFootprint().GetReference(),z.GetNumber(),pos(z.GetPosition())))
    tree=[remaining.pop(0)]
    while remaining:
        a,z=min(((a,z) for a in tree for z in remaining),key=lambda pair:math.dist(ep(pair[0])[0],ep(pair[1])[0]))
        width=.5 if net in ['/+3V3','/GND','/VBUS'] else .3
        ok=route(net,ep(a),ep(z),width,False if net=='/SUM' else True)
        if not ok:ok=route(net,ep(a),ep(z),.25,True)
        if not ok:failed.append((net,pos(z.GetPosition())))
        remaining.remove(z);tree.append(z)
kept=[]
for t in list(b.GetTracks()):
    if not isinstance(t,p.PCB_VIA):continue
    near=next((v for v in kept if v.GetNetCode()==t.GetNetCode() and math.dist(pos(v.GetPosition()),pos(t.GetPosition()))<.71),None)
    if near is None:kept.append(t);continue
    if t.GetPosition()!=near.GetPosition():
        for layer in [p.F_Cu,p.B_Cu]:
            link=p.PCB_TRACK(b);link.SetStart(t.GetPosition());link.SetEnd(near.GetPosition());link.SetWidth(p.FromMM(.25));link.SetLayer(layer);link.SetNetCode(t.GetNetCode());b.Add(link)
    b.Remove(t)
p.SaveBoard(str(ROOT/'photodiode_lab.kicad_pcb'),b);(ROOT/'outputs/routing.json').write_text(json.dumps({'failed':failed,'tracks':len(list(b.GetTracks()))},indent=2))
if failed:raise RuntimeError(failed)
