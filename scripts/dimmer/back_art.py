"""Reproducible bottom silkscreen waveform drawing, in bottom-view coordinates."""
import math
import pcbnew as p
from pathlib import Path

def draw(b):
    def mm(x,y): return p.VECTOR2I(p.FromMM(x),p.FromMM(y))
    for item in list(b.GetDrawings()):
        if item.GetLayer()==p.B_SilkS: b.Remove(item)
    def line(a,z,width=.18):
        s=p.PCB_SHAPE();s.SetShape(p.SHAPE_T_SEGMENT);s.SetStart(mm(100-a[0],a[1]));s.SetEnd(mm(100-z[0],z[1]));s.SetLayer(p.B_SilkS);s.SetWidth(p.FromMM(width));b.Add(s)
    def text(s,x,y,size=.8):
        t=p.PCB_TEXT(b);t.SetText(s);t.SetPosition(mm(100-x,y));t.SetTextSize(mm(size,size));t.SetTextThickness(p.FromMM(.15));t.SetLayer(p.B_SilkS);t.SetMirrored(True);b.Add(t)
    text('DIMMER / PHASE CONTROL',50,56,1)
    for start,width,chopped in [(27,22,False),(61,28,True)]:
        text('LOAD' if chopped else 'MAINS',start+width/2,63,.9)
        line((start,68),(start+width,68),.15)
        points=[]
        for i in range(241):
            a=4*math.pi*i/240
            y=68-2*math.sin(a) if not chopped or a%math.pi>=math.pi/2 else 68
            points.append((start+width*i/240,y))
        for a,z in zip(points,points[1:]):line(a,z)
        text('90 DEGREE TRIGGER' if chopped else 'MAINS / 50 Hz',start+width/2,75,.8)

if __name__=='__main__':
    path=Path(__file__).resolve().parents[2]/'dimmer'/'esp32_dimmer.kicad_pcb'
    b=p.LoadBoard(str(path));draw(b);p.SaveBoard(str(path),b)
