#!/usr/bin/python3
"""Build schematic and PCB from shared connectivity. Run route_board.py next."""
from pathlib import Path
import importlib.util,json,uuid,math,copy,csv,xml.etree.ElementTree as ET
import pcbnew as p
ROOT=Path(__file__).resolve().parents[2]/'remote_controller'
spec=importlib.util.spec_from_file_location('helpers',ROOT.parent/'scripts/kicad_helpers.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
get,kids,parse,dump,q=h.get,h.kids,h.parse,h.dump,h.q
def uid(s):return str(uuid.uuid5(uuid.NAMESPACE_URL,'remote-v2/'+s))
def mm(x,y):return p.VECTOR2I(p.FromMM(x),p.FromMM(y))
LIB=ROOT/'libraries/Remote.pretty';LIB.mkdir(parents=True,exist_ok=True)
(ROOT/'outputs').mkdir(exist_ok=True)
parts=[]
def add(ref,lib,value,fp,nets,sch,pcb,side='F',notes=''):
    footprint='Shared:ESP32-C3-SuperMini' if ref=='U1' else 'Remote:'+ref
    parts.append(dict(ref=ref,lib=lib,value=value,source_fp=fp,fp=footprint,nets={str(k):v for k,v in nets.items()},sch=sch,pcb=pcb,side=side,notes=notes))
R='Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal'
C='Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm'
BTN='Button_Switch_THT:SW_PUSH_6mm'
add('U1','ESP32C3_SuperMini:ESP32-C3-SuperMini','ESP32-C3 SuperMini','Shared:ESP32-C3-SuperMini',{9:'JOY_X',10:'JOY_Y',12:'BAT_ADC',2:'SDA',3:'SCL',6:'BTN_ON',7:'BTN_OFF',8:'BTN_PRESET',14:'+3V3',15:'GND',16:'VBUS'},(139.7,60.96),(13.5,90,90),notes='USB faces outward through the left PCB edge; the complete module stays within the outline. GPIO0/1=ADC1; GPIO2/8/9 unused. Direct-solder module to the shared SMD landing pattern; no socket strips.')
add('JS1','Remote:Thumbstick_2765','2765 / 2x10k','Remote:Adafruit_2765_Mini_Thumbstick',{'X+':'+3V3','X-':'GND','X':'X_RAW','Y+':'+3V3','Y-':'GND','Y':'Y_RAW'},(55.88,137.16),(20,55.5,0),notes='Direct-solder 2765. Official six-pad footprint, 0.9mm drills and 1.6mm locating holes; no push switch. Breakout 3246 not required.')
for ref,value,net,sch,pcb in [('SW2','ON / SELECT','BTN_ON',(177.8,129.54),(4.75,37.75,0)),('SW3','OFF / BACK','BTN_OFF',(215.9,129.54),(28.75,37.75,0)),('SW4','PRESET','BTN_PRESET',(254,129.54),(16.75,37.75,0))]:add(ref,'Switch:SW_Push',value,BTN,{1:net,2:'GND'},sch,pcb)
add('BT1','Device:Battery_Cell','18650','Battery:BatteryHolder_MPD_BK-18650-PC2',{1:'VBAT',2:'GND'},(27.94,40.64),(20,2.5,-90),'B',notes='Exact MPD BK-18650-PC2 vertically on rear, elevated 1.5mm over 0.8mm PCB. 72.9mm terminal pitch; adhesive-backed insulating spacer, no holder screw holes. Verify cell length; external charging only.')
add('SW1','Switch:SW_SPDT','BATTERY POWER','Button_Switch_THT:SW_Slide_SPDT_Straight_CK_OS102011MS2Q',{1:'VBAT',2:'VBUS'},(55.88,40.64),(3.5,52,90),notes='Pin2 common, pin3 OFF. Battery OFF and bypass removed before USB.')
add('JP1','Jumper:Jumper_2_Open','SWITCH BYPASS','Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical',{1:'VBAT',2:'VBUS'},(55.88,60.96),(34,3.3,0),'F',notes='Normally open. Remove for USB.')
add('C1','Device:C_Polarized','220u / 10V','Capacitor_THT:CP_Radial_D6.3mm_P2.50mm',{1:'VBUS',2:'GND'},(86.36,40.64),(3.75,4,0),'F',notes='Front top-left corner, clear of OLED and joystick.')
add('J1','Connector_Generic:Conn_01x04','OLED / V G C D','Remote:OLED_MC096VW_Socket',{1:'+3V3',2:'GND',3:'SCL',4:'SDA'},(185.42,50.8),(16.19,9.5,0),notes='Front view: VCC,GND,SCL,SDA left-to-right, header at TOP. LCDWiki MC096VW 27.3x27.8mm. Female socket on carrier front; OLED male pins point backwards. Verify actual module before assembly.')
add('R1','Device:R','100k',R,{1:'VBUS',2:'BAT_ADC'},(33.02,88.9),(5,18,0))
add('R2','Device:R','100k',R,{1:'BAT_ADC',2:'GND'},(58.42,88.9),(5,24,0))
add('C2','Device:C','100n',C,{1:'BAT_ADC',2:'GND'},(83.82,88.9),(27,20,90))
for ref,val,nets,sch,pcb in [('R3','10k',{1:'X_RAW',2:'JOY_X'},(86.36,121.92),(4,59,270)),('R4','22k',{1:'JOY_X',2:'GND'},(111.76,121.92),(8.5,66.5,270)),('R5','10k',{1:'Y_RAW',2:'JOY_Y'},(86.36,157.48),(36,59,270)),('R6','22k',{1:'JOY_Y',2:'GND'},(111.76,157.48),(31.5,66.5,270))]:add(ref,'Device:R',val,R,nets,sch,pcb,notes='ADC full-scale 3.3*22/32=2.27V. Calibrate endpoints/center in firmware.')
add('C3','Device:C','100n',C,{1:'JOY_X',2:'GND'},(137.16,121.92),(3,77,90))
add('C4','Device:C','100n',C,{1:'JOY_Y',2:'GND'},(137.16,157.48),(37,77,90))

def joystick():
    pkg=ET.parse(ROOT/'sources/adafruit-thumbstick.brd').find('.//package[@name="JOYSTICK_ANALOG_MINITHM"]')
    out=['(footprint "Adafruit_2765_Mini_Thumbstick" (version 20250108) (generator "pcbnew") (layer "F.Cu") (descr "Adafruit official JOYSTICK_ANALOG_MINITHM; six terminals, no switch") (attr through_hole)', '(property "Reference" "REF**" (at 0 12) (layer "F.SilkS") (effects (font (size 1 1) (thickness .15))))','(property "Value" "Adafruit 2765" (at 0 14) (layer "F.Fab") (effects (font (size 1 1) (thickness .15))))']
    for z in pkg.findall('pad'):
        a=z.attrib;sx,sy=(1.5,3) if a.get('rot')=='R90' else (3,1.5)
        out.append(f'(pad {q(a["name"])} thru_hole oval (at {a["x"]} {-float(a["y"])}) (size {sx} {sy}) (drill {a["drill"]}) (layers "*.Cu" "*.Mask"))')
    for z in pkg.findall('hole'):
        a=z.attrib;out.append(f'(pad "" np_thru_hole circle (at {a["x"]} {-float(a["y"])}) (size {a["drill"]} {a["drill"]}) (drill {a["drill"]}) (layers "*.Cu" "*.Mask"))')
    for z in pkg.findall('wire'):
        a=z.attrib;out.append(f'(fp_line (start {a["x1"]} {-float(a["y1"])}) (end {a["x2"]} {-float(a["y2"])}) (stroke (width .15) (type solid)) (layer "F.Fab"))')
    out+=['(fp_circle (center 0 0) (end 7 0) (stroke (width .15) (type solid)) (fill none) (layer "F.SilkS"))','(fp_rect (start -9.5 -11) (end 11 9.5) (stroke (width .05) (type solid)) (fill none) (layer "F.CrtYd"))',')']
    (LIB/'Adafruit_2765_Mini_Thumbstick.kicad_mod').write_text('\n'.join(out))

def oled():
    out=['(footprint "OLED_MC096VW_Socket" (version 20250108) (generator "pcbnew") (layer "F.Cu") (descr "LCDWiki MC096VW; front view VCC GND SCL SDA; female socket carrier") (attr through_hole)', '(property "Reference" "REF**" (at 3.81 -3) (layer "F.SilkS") (effects (font (size .85 .85) (thickness .13))))', '(property "Value" "SSD1306 MC096VW" (at 3.81 28) (layer "F.Fab") (effects (font (size 1 1) (thickness .15))))']
    for i in range(4):out.append(f'(pad "{i+1}" thru_hole {"rect" if i==0 else "oval"} (at {i*2.54} 0) (size 1.8 1.8) (drill 1) (layers "*.Cu" "*.Mask"))')
    out += ['(fp_rect (start -9.84 -1.5) (end 17.46 26.3) (stroke (width .15) (type solid)) (fill none) (layer "F.Fab"))','(fp_rect (start -1.4 -1.4) (end 9.02 1.4) (stroke (width .05) (type solid)) (fill none) (layer "F.CrtYd"))']
    # Bottom mounting holes are separate board-only M2 footprints.
    out+=['(model "${KICAD10_3DMODEL_DIR}/Connector_PinSocket_2.54mm.3dshapes/PinSocket_1x04_P2.54mm_Vertical.step" (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 90)))',')']
    (LIB/'OLED_MC096VW_Socket.kicad_mod').write_text('\n'.join(out))

def symbols():
    out={}
    for c in parts:
        if c['lib'] in out:continue
        if c['lib']=='Remote:Thumbstick_2765':
            pins=[]
            for i,(num,name) in enumerate([('X+','X+ / 3V3'),('X','X wiper'),('X-','X- / GND'),('Y+','Y+ / 3V3'),('Y','Y wiper'),('Y-','Y- / GND')]):pins.append(f'(pin passive line (at -15.24 {12.7-i*5.08} 0) (length 5.08) (name {q(name)} (effects (font (size 1 1)))) (number {q(num)} (effects (font (size 1 1)))))')
            a=parse('(symbol "Thumbstick_2765" (pin_names (offset 1)) (in_bom yes) (on_board yes) (property "Reference" "JS" (at 0 0 0) (effects (font (size 1 1)))) (property "Value" "Thumbstick" (at 0 0 0) (effects (font (size 1 1)))) (symbol "Thumbstick_2765_0_1" (rectangle (start -10.16 16.51) (end 10.16 -16.51) (stroke (width .254) (type default)) (fill (type background)))) (symbol "Thumbstick_2765_1_1" '+' '.join(pins)+'))')
        else:lib,name=c['lib'].split(':');a=h.resolve(lib,name)
        out[c['lib']]=a
    return out

def schematic():
    libs=symbols();root=uid('sheet');libs['power:PWR_FLAG']=h.resolve('power','PWR_FLAG');lt=[]
    for name,a in libs.items():t=copy.deepcopy(a);t[1]=name;lt.append(dump(t))
    out=[f'(kicad_sch (version 20250114) (generator "eeschema") (uuid {root}) (paper "A4")','(title_block (title "BLE REMOTE / 18650 / DIRECT THUMBSTICK") (rev "G") (date "2026-09-20"))','(lib_symbols '+' '.join(lt)+')']
    def label(net,x,y,angle=0):out.append(f'(label {q(net)} (at {x} {y} 0) (effects (font (size 1 1)) (justify {"right" if angle==180 else "left"} bottom)) (uuid {uid(net+str(x)+str(y))}))')
    for c in parts:
        x,y=c['sch'];pins=[pin for sub in kids(libs[c['lib']],'symbol') for pin in kids(sub,'pin')]
        out.append(f'(symbol (lib_id {q(c["lib"])}) (at {x} {y} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid {uid(c["ref"])})')
        for name,val,dy in [('Reference',c['ref'],-23 if c['ref']=='JS1' else -19 if c['ref']=='U1' else -12 if c['ref']=='J1' else -7),('Value',c['value'],-20 if c['ref']=='JS1' else -16 if c['ref']=='U1' else -9 if c['ref']=='J1' else -4),('Footprint',c['fp'],0)]:
            small=c['ref'].startswith(('R','C','BT'));px=x+4 if small else x;py=y+(-2 if name=='Reference' else 1) if small else y+dy
            out.append(f'(property {q(name)} {q(val)} (at {px} {py} 0) (effects (font (size 1 1)) {"(justify left)" if small else ""} {"(hide yes)" if name=="Footprint" else ""}))')
        for pin in pins:out.append(f'(pin {q(get(pin,"number")[1])} (uuid {uid(c["ref"]+get(pin,"number")[1])}))')
        out.append(f'(instances (project "esp32c3_remote" (path "/{root}" (reference {q(c["ref"])}) (unit 1)))))')
        for pin in pins:
            num=get(pin,'number')[1];dx,dy,ang=map(float,get(pin,'at')[1:]);px,py=round(x+dx,5),round(y-dy,5);net=c['nets'].get(num)
            if not net:out.append(f'(no_connect (at {px} {py}) (uuid {uid(c["ref"]+num+"nc")}))');continue
            rad=math.radians(ang);xx,yy=round(px-5.08*math.cos(rad),5),round(py+5.08*math.sin(rad),5)
            out.append(f'(wire (pts (xy {px} {py}) (xy {xx} {yy})) (stroke (width .254) (type default)) (uuid {uid(c["ref"]+num+"wire")}))');label(net,xx,yy,180 if ang==0 else 0)
    for i,(net,x,y) in enumerate([('VBUS',243.84,40.64),('GND',269.24,40.64)],1):
        ref=f'#FLG0{i}';out.append(f'(symbol (lib_id "power:PWR_FLAG") (at {x} {y} 0) (unit 1) (in_bom no) (on_board yes) (uuid {uid(ref)}) (property "Reference" {q(ref)} (at {x} {y} 0) (effects (font (size 1 1)) (hide yes))) (property "Value" "PWR_FLAG" (at {x} {y-4} 0) (effects (font (size 1 1)))) (instances (project "esp32c3_remote" (path "/{root}" (reference {q(ref)}) (unit 1)))))');label(net,x,y)
    for text,x,y in [('POWER / ONBOARD ME6211',17.78,17.78),('ESP32-C3 / BLE',119.38,17.78),('OLED / I2C',175.26,17.78),('ADC / BATTERY',17.78,73.66),('JOYSTICK / 2x10k / NO PUSH SWITCH',17.78,109.22),('THUMB BUTTONS / INTERNAL PULLUPS',172.72,109.22)]:out.append(f'(text {q(text)} (at {x} {y} 0) (effects (font (size 1.3 1.3)) (justify left)) (uuid {uid(text)}))')
    notes='Joystick: GPIO0/1, ADC 12 dB attenuation, 10k/22k dividers limit full-scale to 2.27 V.\nBattery: GPIO3 reads VBUS/2. Buttons GPIO10/20/21: internal pull-ups.\nI2C GPIO6/7: pull-ups on OLED module. No boot strapping pins used.\nBattery OFF + JP1 open before USB. Onboard diode does NOT isolate a battery sharing USB VBUS.\nSingle externally charged 18650. Test low-voltage operation with the actual SuperMini.'
    out.append(f'(text {q(notes)} (at 17.78 180.34 0) (effects (font (size 1.05 1.05)) (justify left)) (uuid {uid("notes")})) (embedded_fonts no))')
    (ROOT/'esp32c3_remote.kicad_sch').write_text('\n'.join(out));entries=[]
    for lib in sorted({x.split(':')[0] for x in libs}):
        if lib=='ESP32C3_SuperMini':
            entries.append('(lib (name "ESP32C3_SuperMini") (type "KiCad") (uri "${KIPRJMOD}/../shared/ESP32C3_SuperMini.kicad_sym") (options "") (descr "Shared ESP32-C3 SuperMini symbol"))')
            continue
        syms=[dump(a) for name,a in libs.items() if name.split(':')[0]==lib];(ROOT/f'libraries/{lib}.kicad_sym').write_text('(kicad_symbol_lib (version 20250114) (generator "kicad_symbol_editor") '+' '.join(syms)+')')
        entries.append(f'(lib (name {q(lib)}) (type "KiCad") (uri "${{KIPRJMOD}}/libraries/{lib}.kicad_sym") (options "") (descr "Local symbols"))')
    (ROOT/'sym-lib-table').write_text('(sym_lib_table (version 7) '+' '.join(entries)+')')

def board():
    b=p.BOARD();b.SetCopperLayerCount(2);b.GetDesignSettings().SetBoardThickness(p.FromMM(.8));nets={}
    for name in sorted({n for c in parts for n in c['nets'].values()}):n=p.NETINFO_ITEM(b,'/'+name);b.Add(n);nets[name]=n
    for c in parts:
        lib,name=c['source_fp'].split(':');base=LIB if lib=='Remote' else ROOT.parent/'shared/ESP32-C3-SuperMini.pretty' if lib=='Shared' else Path('/usr/share/kicad/footprints')/(lib+'.pretty')
        fp=p.FootprintLoad(str(base),name)
        if fp is None:raise RuntimeError(c['source_fp'])
        if c['ref']=='U1':
            # Preserve every pad from the dimmer's actual direct-solder footprint.
            models=list(fp.Models());fp.Models().clear()
            for model in models:fp.Add3DModel(model)
        if c['ref']=='U1':
            for field in fp.GetFields():
                if field.GetName()=='Datasheet':field.SetText('')
        if c['ref']=='BT1':
            # Holder screw holes are unused with the insulating adhesive spacer.
            # Keep them as fabrication marks, not drilled carrier holes.
            for pad in list(fp.Pads()):
                if pad.GetAttribute()==p.PAD_ATTRIB_NPTH:
                    mark=p.PCB_SHAPE();mark.SetShape(p.SHAPE_T_CIRCLE);mark.SetCenter(pad.GetPosition());mark.SetEnd(pad.GetPosition()+mm(1.6,0));mark.SetLayer(p.F_Fab);mark.SetWidth(p.FromMM(.1));fp.Add(mark);fp.Remove(pad)
            # Elevated assembly: courtyard islands describe terminal solder areas.
            # Full body remains on Fab. 1.5mm spacer and <=0.9mm tails are mandatory.
            for item in list(fp.GraphicalItems()):
                if item.GetLayer() in [p.F_CrtYd,p.F_SilkS] and not hasattr(item,'GetText'):fp.Remove(item)
                elif hasattr(item,'GetText') and item.GetText()=='+':
                    item.SetPosition(mm(-1,-4));item.SetTextSize(mm(1.2,1.2))
            for cx in [0,72.9]:
                sh=p.PCB_SHAPE();sh.SetShape(p.SHAPE_T_RECT);sh.SetStart(mm(cx-2,-2));sh.SetEnd(mm(cx+2,2));sh.SetLayer(p.F_CrtYd);sh.SetWidth(p.FromMM(.05));fp.Add(sh)
        if c['ref']=='R3':fp.Reference().SetPosition(mm(-3,0))
        fp.SetReference(c['ref']);fp.SetValue(c['value'])
        if c['ref']=='U1':fp.SetFPID(p.LIB_ID('Shared','ESP32-C3-SuperMini'))
        else:
            fp.SetFPID(p.LIB_ID('Remote',c['ref']));p.FootprintSave(str(LIB),fp)
        fp.SetPath(p.KIID_PATH('/'+uid('sheet')+'/'+uid(c['ref'])));fp.SetPosition(mm(*c['pcb'][:2]));fp.SetOrientationDegrees(c['pcb'][2]);b.Add(fp)
        if c['side']=='B':fp.Flip(fp.GetPosition(),False)
        for pad in fp.Pads():
            if pad.GetNumber() in c['nets']:pad.SetNet(nets[c['nets'][pad.GetNumber()]])
        fp.Value().SetVisible(False);fp.Reference().SetTextSize(mm(.85,.85));fp.Reference().SetTextThickness(p.FromMM(.13))
        if c['ref'] in ['U1','SW1','SW2','SW3','SW4','J1','JS1','C1','C3','C4']:fp.Reference().SetVisible(False)
    # Bottom OLED holes: vendor drawing, 2 mm from each side and bottom.
    for i,(x,y) in enumerate([(8.35,33.8),(31.65,33.8)],5):
        fp=p.FootprintLoad('/usr/share/kicad/footprints/MountingHole.pretty','MountingHole_2.2mm_M2');fp.SetReference(f'H{i}');fp.SetPosition(mm(x,y));fp.SetAttributes(p.FP_BOARD_ONLY|p.FP_EXCLUDE_FROM_BOM|p.FP_EXCLUDE_FROM_POS_FILES);fp.Reference().SetVisible(False);fp.Value().SetVisible(False);b.Add(fp)
    def line(a,z,layer=p.Edge_Cuts,w=.05):
        s=p.PCB_SHAPE();s.SetShape(p.SHAPE_T_SEGMENT);s.SetStart(mm(*a));s.SetEnd(mm(*z));s.SetLayer(layer);s.SetWidth(p.FromMM(w));b.Add(s)
    def arc(a,m,z):
        s=p.PCB_SHAPE();s.SetShape(p.SHAPE_T_ARC);s.SetArcGeometry(mm(*a),mm(*m),mm(*z));s.SetLayer(p.Edge_Cuts);s.SetWidth(p.FromMM(.05));b.Add(s)
    for a,z in [((4,0),(36,0)),((40,4),(40,96)),((36,100),(4,100)),((0,96),(0,4))]:line(a,z)
    for a,m,z in [((36,0),(38.828427,1.171573),(40,4)),((40,96),(38.828427,98.828427),(36,100)),((4,100),(1.171573,98.828427),(0,96)),((0,4),(1.171573,1.171573),(4,0))]:arc(a,m,z)
    def text(s,x,y,size=1,layer=p.F_SilkS):
        t=p.PCB_TEXT(b);t.SetText(s);t.SetPosition(mm(x,y));t.SetTextSize(mm(size,size));t.SetTextThickness(p.FromMM(.15));t.SetLayer(layer);t.SetMirrored(layer==p.B_SilkS);b.Add(t)
        if s=='POWER':t.SetTextAngle(p.EDA_ANGLE(90,p.DEGREES_T))
    for s,x,y,sz in [('SELECT',8,36,.8),('PRESET',20,36,.8),('BACK',32,36,.8),('POWER',7.5,52,.8),('USB',5,79,.9)]:text(s,x,y,sz)
    zone=p.ZONE(b);zone.SetIsRuleArea(True);zone.SetLayerSet(p.LSET.AllCuMask());zone.SetDoNotAllowTracks(True);zone.SetDoNotAllowVias(True);zone.SetDoNotAllowCopperPour(True) if hasattr(zone,'SetDoNotAllowCopperPour') else zone.SetDoNotAllowZoneFills(True);zone.SetZoneName('ANTENNA KEEP CLEAR');poly=zone.Outline();poly.NewOutline()
    for x,y in [(24.2,79.5),(40,79.5),(40,100),(24.2,100)]:poly.Append(p.FromMM(x),p.FromMM(y))
    b.Add(zone)
    p.SaveBoard(str(ROOT/'esp32c3_remote.kicad_pcb'),b)
    (ROOT/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "Remote") (type "KiCad") (uri "${KIPRJMOD}/libraries/Remote.pretty") (options "") (descr "Project footprints")) (lib (name "Shared") (type "KiCad") (uri "${KIPRJMOD}/../shared/ESP32-C3-SuperMini.pretty") (options "") (descr "Shared ESP32-C3 SuperMini footprint")) (lib (name "MountingHole") (type "KiCad") (uri "${KICAD10_FOOTPRINT_DIR}/MountingHole.pretty") (options "") (descr "")))')

def project():
    proj={'meta':{'filename':'esp32c3_remote.kicad_pro','version':1},'net_settings':{'meta':{'version':4},'classes':[dict(name='Default',clearance=.25,track_width=.35,via_diameter=.8,via_drill=.4)]},'board':{'design_settings':{'rules':{'min_clearance':.25,'min_track_width':.25,'min_copper_edge_clearance':.5,'min_hole_clearance':.25,'min_through_hole_diameter':.3,'min_via_diameter':.6,'min_via_annular_width':.15,'min_silk_clearance':.1,'min_silk_text_height':.8,'min_silk_text_thickness':.12,'solder_mask_min_width':.1},'rule_severities':{},'drc_exclusions':[]}}}
    (ROOT/'esp32c3_remote.kicad_pro').write_text(json.dumps(proj,indent=2));(ROOT/'connectivity.json').write_text(json.dumps(parts,indent=2))
    with (ROOT/'BOM.csv').open('w') as f:
        w=csv.writer(f);w.writerow(['Reference','Value','Footprint','Notes'])
        for c in parts:w.writerow([c['ref'],c['value'],c['source_fp'],c['notes']])
if __name__=='__main__':joystick();oled();schematic();board();project();print('Generated',len(parts),'parts')
