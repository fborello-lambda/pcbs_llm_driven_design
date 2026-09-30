"""Convert the original Argentina SVG into mirrored, pad-cleared B.Silkscreen."""
from pathlib import Path
import math,re,xml.etree.ElementTree as ET
import pcbnew as p
ROOT=Path(__file__).resolve().parents[2]/'remote_controller'

def draw(board):
    for item in list(board.GetDrawings()):
        if item.GetLayer()==p.B_SilkS:board.Remove(item)
    def xy(x,y):return (40-(20+(x-12)*.65),82+(y-4.8)*.65)
    def mm(pt):return p.VECTOR2I(p.FromMM(pt[0]),p.FromMM(pt[1]))
    obstacles=[]
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if not pad.IsOnLayer(p.B_Mask):continue
            bb=pad.GetBoundingBox();obstacles.append(tuple(p.ToMM(v) for v in (bb.GetX(),bb.GetY(),bb.GetRight(),bb.GetBottom())))
    for via in board.GetTracks():
        if isinstance(via,p.PCB_VIA):
            x,y=p.ToMM(via.GetPosition().x),p.ToMM(via.GetPosition().y);r=p.ToMM(via.GetWidth(p.B_Cu))/2
            obstacles.append((x-r,y-r,x+r,y+r))
    def clear(pt,width):
        x,y=pt;m=.22+width/2
        return not any(a-m<x<c+m and d-m<y<e+m for a,d,c,e in obstacles)
    def line(a,z,width):
        a,z=xy(*a),xy(*z);n=max(1,math.ceil(math.dist(a,z)/.1));start=None
        pts=[(a[0]+(z[0]-a[0])*i/n,a[1]+(z[1]-a[1])*i/n) for i in range(n+1)]
        def emit(v,w):
            if math.dist(v,w)<.01:return
            shape=p.PCB_SHAPE();shape.SetShape(p.SHAPE_T_SEGMENT);shape.SetStart(mm(v));shape.SetEnd(mm(w));shape.SetWidth(p.FromMM(width));shape.SetLayer(p.B_SilkS);board.Add(shape)
        for i,pt in enumerate(pts):
            if clear(pt,width):
                if start is None:start=pt
            elif start is not None:
                emit(start,pts[max(0,i-1)]);start=None
        if start is not None:emit(start,pts[-1])
    for label,pt,size in [('+ BAT',(34,11),.9),('HORNERO',(20,98.5),.8)]:
        t=p.PCB_TEXT(board);t.SetText(label);t.SetPosition(mm(pt));t.SetTextSize(mm((size,size)));t.SetTextThickness(p.FromMM(.13));t.SetLayer(p.B_SilkS);t.SetMirrored(True);board.Add(t)
    for e in ET.parse(ROOT/'art/argentina_hornero.svg').getroot():
        tag=e.tag.split('}')[-1];a=e.attrib;w=float(a.get('stroke-width','.22'))
        if tag=='line':points=[(float(a['x1']),float(a['y1'])),(float(a['x2']),float(a['y2']))]
        elif tag=='polyline':points=[tuple(map(float,pair.split(','))) for pair in a['points'].split()]
        elif tag in ['circle','ellipse']:
            cx,cy=float(a['cx']),float(a['cy']);rx=float(a.get('rx',a.get('r')));ry=float(a.get('ry',a.get('r')))
            n=max(16,math.ceil(2*math.pi*max(rx,ry)/.25));points=[(cx+rx*math.cos(i*2*math.pi/n),cy+ry*math.sin(i*2*math.pi/n)) for i in range(n+1)]
        elif tag=='text':continue
        else:continue
        for v,wpt in zip(points,points[1:]):line(v,wpt,w)

if __name__=='__main__':
    path=ROOT/'esp32c3_remote.kicad_pcb';board=p.LoadBoard(str(path));draw(board);p.SaveBoard(str(path),board)
