#!/usr/bin/python3
"""Conservative two-layer grid router; KiCad DRC is the final geometry check."""
from pathlib import Path
import math, heapq, json, time
import numpy as np
import pcbnew as p
ROOT=Path(__file__).resolve().parents[2]/'dimmer'
(ROOT/'outputs').mkdir(exist_ok=True)
b=p.LoadBoard(str(ROOT/'esp32_dimmer.kicad_pcb'))
for t in list(b.GetTracks()): b.Remove(t)
S=.2; N=501
Y,X=np.mgrid[0:N,0:N]*S
lv={'GND','+3V3','3V3_EXT','SDA','SCL','FIRE','ZC','BASE','OPTO_A','OPTO_K','RELAY_EN','RELAY_LED','RELAY_BASE','RELAY_K','RELAY_GND','RELAY_3V3','RELAY_SINK','RELAY_PBASE','RELAY_DRIVE'}
fps={f.GetReference():f for f in b.GetFootprints()}
nets={n.GetNetname():n for n in b.GetNetsByNetcode().values()}
exec((ROOT.parent/'scripts/grid_router.py').read_text(), globals())

# Controlled short necks at the TO-220 leads; full-current paths then widen to 4 mm.
qdim=pos(pad('Q2',1).GetPosition()); qline=pos(pad('Q2',2).GetPosition())
track(qdim,(60,88),'L_OUT',1.75,0)
track(qline,(52.54,92),'L_PROT',1.75,1)

power=[('N',endpoint('J2',2),endpoint('J3',2)),('L_IN',endpoint('J2',1),endpoint('F1',1)),('L_PROT',((52.54,92),[1]),endpoint('F1',2)),('L_OUT',((60,88),[0]),endpoint('J3',1))]
fail=[]
power.sort(key=lambda x: ['L_PROT','L_DIM','L_OUT','N','L_IN'].index(x[0]))
for net,a,z in power:
    if not route(net,a,z,4.0,False): fail.append(net+' power')
connected={n:set() for n in nets}
for n,refs in {'N':[('J2',2),('J3',2)],'L_IN':[('J2',1),('F1',1)],'L_PROT':[('Q2',2),('F1',2)],'L_OUT':[('Q2',1),('J3',1)]}.items():
    connected[n]=set((r,str(i)) for r,i in refs)
groups={n:[] for n in nets}
for f in b.GetFootprints():
    for z in f.Pads():
        if z.GetNetname(): groups[z.GetNetname()].append((f.GetReference(),z.GetNumber()))
# Route point-to-point branches in nearest-neighbor order, starting at difficult SMD pins.
for net in sorted(groups,key=lambda n:(n in lv,n not in ['GATE','GATE_DRIVE','GR_MID'],len(groups[n]))):
    group=sorted(groups[net])
    if len(group)<2: continue
    tree=connected[net] or {next((x for x in group if x[0]=='U1'),group[0])}
    remaining=set(group)-tree
    while remaining:
        a,z=min(((a,z) for a in sorted(tree) for z in sorted(remaining)),key=lambda pair:math.dist(endpoint(*pair[0])[0],endpoint(*pair[1])[0]))
        width=.45 if net in lv else .75
        if not route(net,endpoint(*a),endpoint(*z),width,True): fail.append(net+' '+str(z))
        remaining.remove(z); tree.add(z)
p.SaveBoard(str(ROOT/'esp32_dimmer.kicad_pcb'),b)
(ROOT/'outputs/routing.json').write_text(json.dumps({'failed':fail,'tracks':len(list(b.GetTracks()))},indent=2))
print('DONE',fail,flush=True)
