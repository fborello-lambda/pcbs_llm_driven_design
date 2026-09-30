#!/usr/bin/python3
"""Build schematic and PCB from shared connectivity. Run route_board.py next."""
from pathlib import Path
import importlib.util,json,uuid,math,copy,csv,xml.etree.ElementTree as ET
import pcbnew as p
ROOT=Path(__file__).resolve().parents[2]/'photodiode_lab'
spec=importlib.util.spec_from_file_location('helpers',ROOT.parent/'scripts/kicad_helpers.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
get,kids,parse,dump,q=h.get,h.kids,h.parse,h.dump,h.q
def uid(s):return str(uuid.uuid5(uuid.NAMESPACE_URL,'photodiode-lab-v1/'+s))
def mm(x,y):return p.VECTOR2I(p.FromMM(x),p.FromMM(y))
LIB=ROOT/'libraries/Lab.pretty';LIB.mkdir(parents=True,exist_ok=True)
(ROOT/'outputs').mkdir(exist_ok=True)
parts=[]
def add(ref,lib,value,fp,nets,sch,pcb,side='F',notes=''):
    footprint='Shared:ESP32-C3-SuperMini' if ref=='U1' else 'Lab:'+ref
    parts.append(dict(ref=ref,lib=lib,value=value,source_fp=fp,fp=footprint,nets={str(k):v for k,v in nets.items()},sch=sch,pcb=pcb,side=side,notes=notes))
R='Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal'
C='Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm'
BTN='Button_Switch_THT:SW_PUSH_6mm'
add('U1','ESP32C3_SuperMini:ESP32-C3-SuperMini','ESP32-C3 SuperMini','Shared:ESP32-C3-SuperMini',{9:'ADC_OUT',14:'+3V3',15:'GND',16:'VBUS'},(55.88,48.26),(80,14,0),notes='Shared direct-solder landing pattern. USB at top edge; antenna keepout x70..90 y24.7..38. GPIO0 ADC1.')
add('U2','Lab:MCP6002','MCP6002-I/P','Package_DIP:DIP-8_W7.62mm_Socket',{1:'VOUT',2:'SUM',3:'VREF',4:'GND',5:'REF_DIV',6:'VREF',7:'VREF',8:'+3V3'},(144.78,71.12),(45,55,0),notes='DIP8: A=transimpedance; B=reference buffer. 1 MHz, RRIO, 1.8-6V supply.')
add('D1','Device:D_Photo','BPW34','Lab:BPW34_Vishay',{1:'SUM',2:'GND'},(96.52,71.12),(25.1,57.54,180),notes='Vishay drawing 96 12186: 5.1mm pitch. Pad1 cathode to SUM (right); pad2 anode to GND (left). More light raises VOUT.')
add('RF1','Device:R','100k 1%',R,{1:'SUM',2:'VOUT'},(121.92,38.1),(45,37,0),notes='Standard soldered axial resistor, 10.16mm pitch. Start at 100k; any later variable-resistance arrangement is user-defined.')
add('CF1','Device:C','1n C0G',C,{1:'SUM',2:'VOUT'},(160.02,38.1),(47.5,30,0),notes='Fixed feedback compensation. For low-speed teaching; 159Hz at RF=1M.')
add('R1','Device:R','10k 1%',R,{1:'+3V3',2:'REF_DIV'},(96.52,116.84),(12,82,0))
add('R2','Device:R','10k 1%',R,{1:'REF_DIV',2:'GND'},(121.92,116.84),(12,90,0))
add('C1','Device:C','100n',C,{1:'REF_DIV',2:'GND'},(149.86,116.84),(29,84,270))
add('C2','Device:C','100n',C,{1:'+3V3',2:'GND'},(177.8,116.84),(61,49,0),notes='Local supply bypass next to U2 pin8; THT ceramic.')
add('C3','Device:C_Polarized','10u / 10V','Capacitor_THT:CP_Radial_D5.0mm_P2.00mm',{1:'+3V3',2:'GND'},(203.2,116.84),(62,42,0))
add('R3','Device:R','10k 1%',R,{1:'VOUT',2:'ADC_OUT'},(205.74,58.42),(78,68,270),notes='ADC divider top; protect useful ADC range even if VOUT saturates high.')
add('R4','Device:R','22k 1%',R,{1:'ADC_OUT',2:'GND'},(233.68,58.42),(78,83,270))
add('C4','Device:C','100n',C,{1:'ADC_OUT',2:'GND'},(259.08,58.42),(88,83,270))
for ref,net,x,y in [('TP1','VOUT',78,60),('TP2','VREF',29,69),('TP3','ADC_OUT',88,78.16),('TP4','GND',88,93.16)]:
 add(ref,'Connector:TestPoint',net,'TestPoint:TestPoint_Loop_D2.50mm_Drill1.0mm',{1:net},(50.8+int(ref[-1])*38.1,154.94),(x,y,0),notes='Accessible multimeter/scope point. Do not probe the sensitive SUM node.')

# Optional static soldering exercise; remove JP1 during photodiode measurements.
add('JP1','Jumper:Jumper_2_Open','PRACTICE ENABLE','Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical',{1:'+3V3',2:'PRACT_A'},(33.02,111.76),(9,22,90),notes='Normally open. Fit a shunt only after checking the practice circuit; remove during TIA measurements.')
for ref,value,fp,left,right,x,sch in [
 ('R5','1k','R_1206_3216Metric','PRACT_A','PRACT_B',22,(25.4,137.16)),
 ('R6','0R','R_0805_2012Metric','PRACT_B','PRACT_C',32,(50.8,137.16)),
 ('R7','0R','R_0603_1608Metric','PRACT_C','PRACT_D',42,(25.4,162.56))]:
 add(ref,'Device:R',value,'Resistor_SMD:'+fp,{1:left,2:right},sch,(x,22,0),notes='Optional soldering practice. R5 limits LED current; R6/R7 are zero-ohm assembly exercises.')
add('D2','Device:LED','RED','LED_SMD:LED_0805_2012Metric',{1:'GND',2:'PRACT_D'},(50.8,162.56),(54,22,180),notes='Optional red LED. Cathode K on the right. About 1-2mA with 3.3V and R5=1k; no firmware required.')
for ref,net,x in [('TP5','PRACT_A',17),('TP6','PRACT_B',27),('TP7','PRACT_C',37),('TP8','PRACT_D',47),('TP9','GND',60)]:
 add(ref,'Connector:TestPoint',net,'TestPoint:TestPoint_Pad_D2.0mm',{1:net},(17.78+int(ref[-1])*7.62,91.44),(x,22,0),notes='Practice measurement pad. Use continuity mode only with power disconnected.')

def symbols():
    out={}
    for c in parts:
        if c['lib'] in out:continue
        if c['lib']=='Lab:MCP6002':
            pinout=[('1','OUT A','output',15.24,10.16,180),('2','IN A-','input',-15.24,10.16,0),('3','IN A+','input',-15.24,5.08,0),('4','VSS','power_in',-15.24,-12.7,0),('5','IN B+','input',-15.24,-2.54,0),('6','IN B-','input',-15.24,-7.62,0),('7','OUT B','output',15.24,-5.08,180),('8','VDD','power_in',15.24,-12.7,180)]
            pins=[f'(pin {typ} line (at {x} {y} {angle}) (length 5.08) (name {q(name)} (effects (font (size 1 1)))) (number {q(num)} (effects (font (size 1 1)))))' for num,name,typ,x,y,angle in pinout]
            a=parse('(symbol "MCP6002" (pin_names (offset 1)) (in_bom yes) (on_board yes) (property "Reference" "U" (at 0 0 0) (effects (font (size 1 1)))) (property "Value" "MCP6002" (at 0 0 0) (effects (font (size 1 1)))) (symbol "MCP6002_0_1" (rectangle (start -10.16 15.24) (end 10.16 -15.24) (stroke (width .254) (type default)) (fill (type background)))) (symbol "MCP6002_1_1" '+' '.join(pins)+'))')
        else:lib,name=c['lib'].split(':');a=h.resolve(lib,name)
        out[c['lib']]=a
    return out

def schematic():
    libs=symbols();root=uid('sheet');libs['power:PWR_FLAG']=h.resolve('power','PWR_FLAG');lt=[]
    for name,a in libs.items():t=copy.deepcopy(a);t[1]=name;lt.append(dump(t))
    out=[f'(kicad_sch (version 20250114) (generator "eeschema") (uuid {root}) (paper "A4")','(title_block (title "PHOTODIODE TRANSIMPEDANCE LAB") (rev "D") (date "2026-09-20"))','(lib_symbols '+' '.join(lt)+')']
    def label(net,x,y,angle=0):out.append(f'(label {q(net)} (at {x} {y} 0) (effects (font (size 1 1)) (justify {"right" if angle==180 else "left"} bottom)) (uuid {uid(net+str(x)+str(y))}))')
    for c in parts:
        in_bom='no' if c['ref'] in ['TP5','TP6','TP7','TP8','TP9'] else 'yes'
        x,y=c['sch'];pins=[pin for sub in kids(libs[c['lib']],'symbol') for pin in kids(sub,'pin')]
        out.append(f'(symbol (lib_id {q(c["lib"])}) (at {x} {y} 0) (unit 1) (in_bom {in_bom}) (on_board yes) (dnp no) (uuid {uid(c["ref"])})')
        for name,val,dy in [('Reference',c['ref'],-23 if c['ref']=='U2' else -19 if c['ref']=='U1' else -12 if c['ref']=='J1' else -7),('Value',c['value'],-20 if c['ref']=='U2' else -16 if c['ref']=='U1' else -9 if c['ref']=='J1' else -4),('Footprint',c['fp'],0)]:
            small=c['ref'].startswith(('R','C','BT'));px=x+4 if small else x;py=y+(-2 if name=='Reference' else 1) if small else y+dy
            out.append(f'(property {q(name)} {q(val)} (at {px} {py} 0) (effects (font (size 1 1)) {"(justify left)" if small else ""} {"(hide yes)" if name=="Footprint" else ""}))')
        for pin in pins:out.append(f'(pin {q(get(pin,"number")[1])} (uuid {uid(c["ref"]+get(pin,"number")[1])}))')
        out.append(f'(instances (project "photodiode_lab" (path "/{root}" (reference {q(c["ref"])}) (unit 1)))))')
        for pin in pins:
            num=get(pin,'number')[1];dx,dy,ang=map(float,get(pin,'at')[1:]);px,py=round(x+dx,5),round(y-dy,5);net=c['nets'].get(num)
            if not net:out.append(f'(no_connect (at {px} {py}) (uuid {uid(c["ref"]+num+"nc")}))');continue
            rad=math.radians(ang);xx,yy=round(px-5.08*math.cos(rad),5),round(py+5.08*math.sin(rad),5)
            out.append(f'(wire (pts (xy {px} {py}) (xy {xx} {yy})) (stroke (width .254) (type default)) (uuid {uid(c["ref"]+num+"wire")}))');label(net,xx,yy,180 if ang==0 else 0)
    for i,(net,x,y) in enumerate([('VBUS',243.84,40.64),('GND',269.24,40.64),('+3V3',294.64,40.64)],1):
        ref=f'#FLG0{i}';out.append(f'(symbol (lib_id "power:PWR_FLAG") (at {x} {y} 0) (unit 1) (in_bom no) (on_board yes) (uuid {uid(ref)}) (property "Reference" {q(ref)} (at {x} {y} 0) (effects (font (size 1 1)) (hide yes))) (property "Value" "PWR_FLAG" (at {x} {y-4} 0) (effects (font (size 1 1)))) (instances (project "photodiode_lab" (path "/{root}" (reference {q(ref)}) (unit 1)))))');label(net,x,y)
    for text,x,y in [('USB POWER / ESP32 ADC',17.78,17.78),('PHOTODIODE / TRANSIMPEDANCE',91.44,17.78),('ADC RANGE DIVIDER',198.12,30.48),('BUFFERED MIDRAIL / DECOUPLING',88.9,96.52),('MEASUREMENT POINTS',88.9,139.7),('OPTIONAL SMD PRACTICE',17.78,80)]:out.append(f'(text {q(text)} (at {x} {y} 0) (effects (font (size 1.3 1.3)) (justify left)) (uuid {uid(text)}))')
    notes='VREF = 3.3V / 2.  VOUT = VREF + IPH * RF1 (before clipping).  BPW34 cathode = SUM, anode = GND.\nRF1 is a soldered axial resistor. Power OFF before modifying feedback.\nFeedback pole: f = 1/(2*pi*RF1*CF1). Measure settling and clipping.\nVADC = VOUT * R4/(R3+R4); GPIO0, ADC1, 12dB attenuation. Calibrate ADC and dark output.\nMCP6002 DIP8: A = TIA, B = VREF buffer. USB only; no external supply connected.'
    out.append(f'(text {q(notes)} (at 17.78 180.34 0) (effects (font (size 1.05 1.05)) (justify left)) (uuid {uid("notes")})) (embedded_fonts no))')
    (ROOT/'photodiode_lab.kicad_sch').write_text('\n'.join(out));entries=[]
    for lib in sorted({x.split(':')[0] for x in libs}):
        if lib=='ESP32C3_SuperMini':
            entries.append('(lib (name "ESP32C3_SuperMini") (type "KiCad") (uri "${KIPRJMOD}/../shared/ESP32C3_SuperMini.kicad_sym") (options "") (descr "Shared ESP32-C3 SuperMini symbol"))')
            continue
        syms=[dump(a) for name,a in libs.items() if name.split(':')[0]==lib];(ROOT/f'libraries/{lib}.kicad_sym').write_text('(kicad_symbol_lib (version 20250114) (generator "kicad_symbol_editor") '+' '.join(syms)+')')
        entries.append(f'(lib (name {q(lib)}) (type "KiCad") (uri "${{KIPRJMOD}}/libraries/{lib}.kicad_sym") (options "") (descr "Local symbols"))')
    (ROOT/'sym-lib-table').write_text('(sym_lib_table (version 7) '+' '.join(entries)+')')

def local_footprints():
    (LIB/'BPW34_Vishay.kicad_mod').write_text('''(footprint "BPW34_Vishay" (version 20250108) (generator "pcbnew") (layer "F.Cu") (property "Reference" "REF**" (at 2.55 -4 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness .15)))) (property "Value" "BPW34" (at 2.55 2.6 0) (layer "F.Fab") (effects (font (size 1 1) (thickness .15)))) (fp_rect (start -1.2 -2) (end 6.3 2) (stroke (width .15) (type solid)) (fill none) (layer "F.SilkS")) (fp_text user "K" (at 0 -3.5) (layer "F.SilkS") (effects (font (size .8 .8) (thickness .13)))) (fp_rect (start -1.7 -2.5) (end 6.8 2.5) (stroke (width .05) (type solid)) (fill none) (layer "F.CrtYd")) (pad "1" thru_hole rect (at 0 0) (size 2 2) (drill .9) (layers "*.Cu" "*.Mask")) (pad "2" thru_hole circle (at 5.1 0) (size 2 2) (drill .9) (layers "*.Cu" "*.Mask")))''')

def board():
    b=p.BOARD();b.SetCopperLayerCount(2);nets={}
    for name in sorted({n for c in parts for n in c['nets'].values()}): n=p.NETINFO_ITEM(b,'/'+name);b.Add(n);nets[name]=n
    for c in parts:
        lib,name=c['source_fp'].split(':');base=LIB if lib=='Lab' else ROOT.parent/'shared/ESP32-C3-SuperMini.pretty' if lib=='Shared' else Path('/usr/share/kicad/footprints')/(lib+'.pretty')
        fp=p.FootprintLoad(str(base),name)
        if fp is None: raise RuntimeError(c['source_fp'])
        if c['ref']=='U1':
            models=list(fp.Models());fp.Models().clear()
            for m in models:fp.Add3DModel(m)
            for field in fp.GetFields():
                if field.GetName()=='Datasheet':field.SetText('')
        fp.SetReference(c['ref']);fp.SetValue(c['value'])
        if c['ref']=='U1':fp.SetFPID(p.LIB_ID('Shared','ESP32-C3-SuperMini'))
        else:fp.SetFPID(p.LIB_ID('Lab',c['ref']))
        fp.SetPath(p.KIID_PATH('/'+uid('sheet')+'/'+uid(c['ref'])))
        if c['ref']!='U1':p.FootprintSave(str(LIB),fp)
        fp.SetPosition(mm(*c['pcb'][:2]));fp.SetOrientationDegrees(c['pcb'][2]);b.Add(fp)
        for pad in fp.Pads():
            if pad.GetNumber() in c['nets']:pad.SetNet(nets[c['nets'][pad.GetNumber()]])
        fp.Value().SetVisible(False);fp.Reference().SetTextSize(mm(.85,.85));fp.Reference().SetTextThickness(p.FromMM(.13))
        if c['ref']=='U1' or c['ref'].startswith('TP'):fp.Reference().SetVisible(False)
    for i,(x,y) in enumerate([(5,5),(95,5),(5,95),(95,95)],1):
        fp=p.FootprintLoad('/usr/share/kicad/footprints/MountingHole.pretty','MountingHole_3.2mm_M3');fp.SetReference(f'H{i}');fp.SetPosition(mm(x,y));fp.SetAttributes(p.FP_BOARD_ONLY|p.FP_EXCLUDE_FROM_BOM|p.FP_EXCLUDE_FROM_POS_FILES);fp.Reference().SetVisible(False);fp.Value().SetVisible(False);b.Add(fp)
    def line(a,z):s=p.PCB_SHAPE();s.SetShape(p.SHAPE_T_SEGMENT);s.SetStart(mm(*a));s.SetEnd(mm(*z));s.SetLayer(p.Edge_Cuts);s.SetWidth(p.FromMM(.05));b.Add(s)
    def arc(a,m,z):s=p.PCB_SHAPE();s.SetShape(p.SHAPE_T_ARC);s.SetArcGeometry(mm(*a),mm(*m),mm(*z));s.SetLayer(p.Edge_Cuts);s.SetWidth(p.FromMM(.05));b.Add(s)
    for a,z in [((8,0),(92,0)),((100,8),(100,92)),((92,100),(8,100)),((0,92),(0,8))]:line(a,z)
    for a,m,z in [((92,0),(97.657,2.343),(100,8)),((100,92),(97.657,97.657),(92,100)),((8,100),(2.343,97.657),(0,92)),((0,8),(2.343,2.343),(8,0))]:arc(a,m,z)
    def txt(s,x,y,size=.9,layer=p.F_SilkS):
        t=p.PCB_TEXT(b);t.SetText(s);t.SetPosition(mm(x,y));t.SetTextSize(mm(size,size));t.SetTextThickness(p.FromMM(.13));t.SetLayer(layer);t.SetMirrored(layer==p.B_SilkS);b.Add(t)
    from theory_silk import draw
    draw(b)
    z=p.ZONE(b);z.SetIsRuleArea(True);z.SetLayerSet(p.LSET.AllCuMask());z.SetDoNotAllowTracks(True);z.SetDoNotAllowVias(True);z.SetDoNotAllowCopperPour(True) if hasattr(z,'SetDoNotAllowCopperPour') else z.SetDoNotAllowZoneFills(True);z.SetZoneName('ANTENNA KEEP CLEAR');o=z.Outline();o.NewOutline()
    for x,y in [(70,24.7),(90,24.7),(90,38),(70,38)]:o.Append(p.FromMM(x),p.FromMM(y))
    b.Add(z);p.SaveBoard(str(ROOT/'photodiode_lab.kicad_pcb'),b)

def project():
    proj={'meta':{'filename':'photodiode_lab.kicad_pro','version':1},'net_settings':{'meta':{'version':4},'classes':[dict(name='Default',clearance=.25,track_width=.3,via_diameter=.8,via_drill=.4)]},'board':{'design_settings':{'rules':{'min_clearance':.25,'min_track_width':.25,'min_copper_edge_clearance':.5,'min_hole_clearance':.25,'min_through_hole_diameter':.3,'min_via_diameter':.6,'min_via_annular_width':.15,'min_silk_clearance':.1,'min_silk_text_height':.8,'min_silk_text_thickness':.12},'rule_severities':{},'drc_exclusions':[]}}}
    (ROOT/'photodiode_lab.kicad_pro').write_text(json.dumps(proj,indent=2));(ROOT/'connectivity.json').write_text(json.dumps(parts,indent=2))
    (ROOT/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "Lab") (type "KiCad") (uri "${KIPRJMOD}/libraries/Lab.pretty") (options "") (descr "Photodiode lab footprints")) (lib (name "Shared") (type "KiCad") (uri "${KIPRJMOD}/../shared/ESP32-C3-SuperMini.pretty") (options "") (descr "Shared ESP32-C3 SuperMini footprint")))')
    with (ROOT/'BOM.csv').open('w') as f:
        w=csv.writer(f);w.writerow(['Reference','Value','Footprint','Notes'])
        for c in parts:
            if c['ref'] not in ['TP5','TP6','TP7','TP8','TP9']:w.writerow([c['ref'],c['value'],c['source_fp'],c['notes']])

if __name__=='__main__': local_footprints();schematic();board();project();print('Generated',len(parts),'parts')
