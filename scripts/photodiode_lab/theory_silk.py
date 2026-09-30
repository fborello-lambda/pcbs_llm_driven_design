"""Front-side functional diagram aligned with the real teaching components."""
import math
import pcbnew as p

def draw(board):
    def pt(x,y):return p.VECTOR2I(p.FromMM(x),p.FromMM(y))
    obstacles=[]
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            bb=pad.GetBoundingBox();obstacles.append(tuple(p.ToMM(v) for v in (bb.GetX(),bb.GetY(),bb.GetRight(),bb.GetBottom())))
        for item in fp.GraphicalItems():
            if item.GetLayer()==p.F_SilkS and not hasattr(item,'GetText'):
                bb=item.GetBoundingBox();obstacles.append(tuple(p.ToMM(v) for v in (bb.GetX(),bb.GetY(),bb.GetRight(),bb.GetBottom())))
    def clear(x,y,w):
        d=.22+w/2
        return not any(a-d<x<c+d and b-d<y<e+d for a,b,c,e in obstacles)
    def line(a,z,w=.26):
        # End printed wires just before solder mask openings; do not print on pads.
        n=max(1,math.ceil(math.dist(a,z)/.06));start=None;prev=a
        def emit(v,t):
            if math.dist(v,t)<.05:return
            sh=p.PCB_SHAPE();sh.SetShape(p.SHAPE_T_SEGMENT);sh.SetStart(pt(*v));sh.SetEnd(pt(*t));sh.SetWidth(p.FromMM(w));sh.SetLayer(p.F_SilkS);board.Add(sh)
        for i in range(n+1):
            v=(a[0]+(z[0]-a[0])*i/n,a[1]+(z[1]-a[1])*i/n)
            if clear(*v,w):
                if start is None:start=v
            elif start is not None:emit(start,prev);start=None
            prev=v
        if start is not None:emit(start,z)
    def text(s,x,y,size=1):
        t=p.PCB_TEXT(board);t.SetText(s);t.SetPosition(pt(x,y));t.SetTextSize(pt(size,size));t.SetTextThickness(p.FromMM(.16 if size>=1.2 else .14));t.SetLayer(p.F_SilkS);board.Add(t)
    def arrow(a,z):
        line(a,z,.22);dx,dy=z[0]-a[0],z[1]-a[1];r=math.hypot(dx,dy);dx/=r;dy/=r
        for sign in [-1,1]:line(z,(z[0]-1.4*dx+sign*.7*dy,z[1]-1.4*dy-sign*.7*dx),.22)
    text('LIGHT TO VOLTAGE',33,9,2)
    text('TRANSIMPEDANCE LAB',33,13,1.1)
    text('VOUT = VREF + IPH x RF1',52,79,1.1)
    text('VREF = 1.65V',52,82,1)
    # The actual RF1 and CF1 bodies occupy their respective feedback branches.
    for a,z in [((32,57.54),(32,30)),((32,30),(47.5,30)),((52.5,30),(78,30)),((32,37),(45,37)),((55.16,37),(78,37)),((78,30),(78,60))]:line(a,z)
    text('CF1',59,27.5);text('RF1',62,34.7)
    # Main signal path: the real photodiode is the input component.
    for a,z in [((10,57.54),(20,57.54)),((25.1,57.54),(35,57.54)),((35,43),(35,77)),((35,43),(72,60)),((35,77),(72,60)),((72,60),(78,60)),((29,69),(29,60.08)),((29,60.08),(35,60.08))]:line(a,z,.30)
    text('GND',12,54.5);text('-',37,57.54,1.2);text('+',37,60.08,1.2)
    text('BPW34',19,65);text('MCP6002 / A',53,74,1.1)
    text('TP1 VOUT',88,60,1.1);text('TP2 VREF',27,73,1)
    # A small sun and incoming light rays make the input visually recognizable.
    center=(13,45);r=2
    for i in range(48):
        a=i*math.tau/48;b=(i+1)*math.tau/48
        line((center[0]+r*math.cos(a),center[1]+r*math.sin(a)),(center[0]+r*math.cos(b),center[1]+r*math.sin(b)),.22)
    for i in range(8):
        a=i*math.tau/8;line((13+2.8*math.cos(a),45+2.8*math.sin(a)),(13+3.8*math.cos(a),45+3.8*math.sin(a)),.22)
    text('LIGHT',13,39,1.1);arrow((16,49),(20,53));arrow((20,49),(24,53))
    # ADC divider and test points follow their printed circuit branches.
    for a,z in [((78,60),(78,68)),((78,78.16),(78,83)),((78,78.16),(88,78.16)),((88,78.16),(88,83)),((78,93.16),(88,93.16)),((88,88),(88,93.16))]:line(a,z)
    for a,z in [((78,93.16),(72,93.16)),((72,93.16),(72,95)),((70.5,95),(73.5,95)),((71,95.8),(73,95.8)),((71.5,96.6),(72.5,96.6))]:line(a,z,.22)
    text('TP3 ADC',88,74.5,1);text('TP4 GND',88,96.5,1)
    text('VADC = VOUT x R4/(R3+R4)',52,87,1)
    text('MORE LIGHT',52,92,1.1);text('HIGHER VOUT',52,95,1.1)
    text('1.65V REFERENCE',21,77,1)

    text('SMD PRACTICE / JP1 ON TO TEST',34,17,.85)
    for name,x in [('1206 / 1k',22),('0805 / 0R',32),('0603 / 0R',42),('RED LED',54)]:text(name,x,25,.8)
    for name,x in [('A',17),('B',27),('C',37),('D',47),('GND',60)]:text(name,x,19.5,.8)
