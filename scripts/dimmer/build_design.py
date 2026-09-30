#!/usr/bin/python3
"""Rebuild the editable KiCad schematic and placed PCB from one connectivity source."""
from pathlib import Path
import importlib.util, json, uuid, copy, math, csv
import pcbnew as p
ROOT=Path(__file__).resolve().parents[2]/'dimmer'
(ROOT/'outputs').mkdir(exist_ok=True)
spec=importlib.util.spec_from_file_location('helpers',ROOT.parent/'scripts/kicad_helpers.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
Atom,dump,get,kids,parse,q=h.Atom,h.dump,h.get,h.kids,h.parse,h.q
def uid(s): return str(uuid.uuid5(uuid.NAMESPACE_URL, 'esp32-dimmer/'+s))
cache={}
def resolve(lib,name):
    if lib not in cache:
        path=ROOT.parent/'shared/ESP32C3_SuperMini.kicad_sym' if lib=='ESP32C3_SuperMini' else Path('/usr/share/kicad/symbols')/(lib+'.kicad_sym')
        cache[lib]={x[1]:x for x in kids(parse(path.read_text()),'symbol')}
    a=copy.deepcopy(cache[lib][name]); ext=get(a,'extends')
    if ext:
        b=resolve(lib,ext[1]); a.remove(ext)
        for x in b[2:]:
            if not isinstance(x,list): continue
            if x[0]=='property' and any(y[1]==x[1] for y in kids(a,'property')): continue
            if x[0]!='property' and get(a,x[0]) is not None and x[0]!='symbol': continue
            if x[0]=='symbol': x[1]=x[1].replace(b[1]+'_',name+'_')
            a.append(x)
    return a
Rsmall='Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal'
Rpower='Resistor_THT:R_Axial_DIN0414_L11.9mm_D4.5mm_P20.32mm_Horizontal'
DIP='Package_DIP:DIP-6_W10.16mm'
TERM='TerminalBlock_Wuerth:Wuerth_691311400102_P7.62mm'
parts=[]
def add(ref,lib,value,fp,nets,sch,pcb,notes=''):
    parts.append(dict(ref=ref,lib=lib,value=value,fp=fp,nets={str(k):v for k,v in nets.items()},sch=sch,pcb=pcb,notes=notes))
add('U1','ESP32C3_SuperMini:ESP32-C3-SuperMini','ESP32-C3 SuperMini','Shared:ESP32-C3-SuperMini',{2:'SDA',3:'SCL',12:'ZC',13:'FIRE',14:'+3V3',15:'GND'},(100,55),(49.495,14,0),'External 3.3 V supply for the ESP32. GPIO5 is unused; no relay or auxiliary supply. Shared direct-solder footprint.')
add('J1','Connector_Generic:Conn_01x04','I2C CONTROL / 3V3','Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical',{1:'3V3_EXT',2:'GND',3:'SDA',4:'SCL'},(40,45),(12,16,0),'JST XH 2.50 mm: 1=3V3 input, 2=GND, 3=SDA, 4=SCL. Regulated SELV supply >=1 A; available capacity must be confirmed.')
add('JP1','Jumper:Jumper_2_Open','RUN / OPEN FOR USB','Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical',{1:'3V3_EXT',2:'+3V3'},(40,75),(29,17,0),'Fit shunt for normal use. Remove shunt and disconnect J1 before USB flashing.')
add('R3','Device:R','82R / 0.25W',Rsmall,{1:'+3V3',2:'OPTO_A'},(172.72,38.1),(65,15,0),'MOC3052 LED: approximately 19 to 25 mA nominal; driven by a transistor.')
add('U2','Relay_SolidState:MOC3052M','MOC3052M','Package_DIP:DIP-6_W10.16mm',{1:'OPTO_A',2:'OPTO_K',4:'GATE',6:'GATE_DRIVE'},(220.98,55.88),(72.54,32.92,270),'600 V random-phase optotriac. Do not substitute MOC306x/MOC304x. Leads formed to 10.16 mm.')
add('Q1','Transistor_BJT:BC547','BC547','Package_TO_SOT_THT:TO-92_Inline_Wide',{1:'OPTO_K',2:'BASE',3:'GND'},(185.42,73.66),(80,17,0),'C-B-E according to the selected manufacturer; verify purchased part pinout.')
add('R4','Device:R','1k / 0.25W',Rsmall,{1:'FIRE',2:'BASE'},(154.94,73.66),(66,25,0))
add('R5','Device:R','10k / 0.25W',Rsmall,{1:'BASE',2:'GND'},(172.72,96.52),(83,26,0),'Keeps the transistor off during reset.')
add('U3','Isolator:H11AA1','H11AA1',DIP,{1:'ZC_AC',2:'N',4:'GND',5:'ZC'},(220.98,132.08),(27.46,43.08,90),'Isolated AC zero-crossing detector. Leads formed to 10.16 mm; no socket.')
add('R7','Device:R','47k / 1W / 5%',Rpower,{1:'L_PROT',2:'ZC_MID'},(155,128),(8,88,90),'Same large DIN0414 footprint as R12: 11.9 x 4.5 mm body, 20.32 mm pitch. Flameproof metal-oxide, >=250 V, pulse-capable; 0.328 W maximum. Verify the actual part.')
add('R8','Device:R','47k / 1W / 5%',Rpower,{1:'ZC_MID',2:'ZC_AC'},(182,128),(8,64,90),'Same large DIN0414 footprint as R12: 11.9 x 4.5 mm body, 20.32 mm pitch. R7+R8=94k total; 0.328 W maximum each.')
add('J2','Connector_Generic:Conn_01x02','MAINS 220 Vac',TERM,{1:'L_IN',2:'N'},(35.56,142.24),(16,94,0),'7.62 mm terminal block, >=300 Vac / 16 A, 1.5 mm2 cable; L and N.')
add('F1','Device:Fuse','T6.3AH / 250V','Dimmer:Fuseholder_Conquer_CQ-200S_P23.50mm',{1:'L_IN',2:'L_PROT'},(63.5,142.24),(24,60,270),'CICEM Conquer CQ-200S fuse holder: 6.3 A/250 V, 23.5 mm pitch, 1.8 mm blade; 2.2 mm finished drill selected with clearance. Verify sample against cq200xx.pdf. 5x20 time-delay ceramic HBC fuse; validate inrush/I2t. No verified STEP.')
add('RV1','Device:Varistor','S14K275 / 275Vac','Varistor:RV_Disc_D15.5mm_W5mm_P7.5mm',{1:'L_PROT',2:'N'},(106.68,175.26),(34,80,90),'275 Vac MOV beside F1 to minimize the protected-line surge loop. Surge coordination with the 600 V optotriac must be validated.')
add('R11','Device:R','220R / 1W pulse',Rpower,{1:'L_PROT',2:'GR_MID'},(281.94,43.18),(40,60,0),'Pulse-capable resistor, >=250 V working voltage.')
add('R12','Device:R','220R / 1W pulse',Rpower,{1:'GR_MID',2:'GATE_DRIVE'},(307.34,43.18),(40,70,0),'440 ohm nominal; approximately 0.82 A peak at 242 Vac with -5% resistors. Validate repetitive pulses.')
add('R13','Device:R','330R / 0.5W','Resistor_THT:R_Axial_DIN0309_L9.0mm_D3.2mm_P12.70mm_Horizontal',{1:'GATE',2:'L_OUT'},(279.4,91.44),(62,77,0),'Gate-to-MT1 resistor.')
add('Q2','Triac_Thyristor:BTA16-800BW','BTA16-800BW','Dimmer:TO-220-3_Vertical',{1:'L_OUT',2:'L_PROT',3:'GATE'},(337.82,68.58),(55.08,88,180),'Snubberless BTA16. Heatsink <=4 C/W, thermal interface <=0.5 C/W. MT1=1, MT2=2, G=3. Insulated tab is not a PCB safety barrier.')
add('J3','Connector_Generic:Conn_01x02','1000 W LAMP OUTPUT',TERM,{1:'L_OUT',2:'N'},(370.84,68.58),(79,92,0),'Triac-controlled L / direct N output. Functional off is not galvanic isolation. Connect reflector PE directly to external certified PE terminal.')



def schematic():
    libs={}; libtext=[]
    for c in parts:
        if c['lib'] in libs: continue
        lib,name=c['lib'].split(':'); a=resolve(lib,name)
        # The module's 3V3 rail may be supplied externally, so this pin is power_in.
        if lib=='ESP32C3_SuperMini':
            for sub in kids(a,'symbol'):
                for pin in kids(sub,'pin'):
                    if get(pin,'number')[1]=='14': pin[1]=Atom('power_in')
        libs[c['lib']]=a
        b=copy.deepcopy(a); b[1]=c['lib']; libtext.append(dump(b))
    root=uid('sheet'); out=[f'(kicad_sch (version 20250114) (generator "eeschema") (uuid {root}) (paper "A3")',
        '(title_block (title "HALOGEN DIMMER / ESP32-C3") (date "2026-09-19") (rev "J - snubberless") (company "220 Vac / 50 Hz - I2C slave") (comment 1 "Validate thermal behavior, inrush, EMC and insulation before energizing"))',
        '(lib_symbols '+'\n'.join(libtext)+')']
    def text(s,x,y,size=1.27): out.append(f'(text {q(s)} (at {x} {y} 0) (effects (font (size {size} {size})) (justify left)) (uuid {uid(s)}))')
    def label(net,x,y,angle=0): out.append(f'(label {q(net)} (at {x} {y} {angle}) (effects (font (size 1 1)) (justify left bottom)) (uuid {uid(net+str(x)+str(y))}))')
    def wire(x,y,xx,yy,key): out.append(f'(wire (pts (xy {x} {y}) (xy {xx} {yy})) (stroke (width 0) (type default)) (uuid {uid(key)}))')
    for c in parts:
        x,y=[round(v/1.27)*1.27 for v in c['sch']]; a=libs[c['lib']]; pins=[pin for sub in kids(a,'symbol') for pin in kids(sub,'pin')]
        out.append(f'(symbol (lib_id {q(c["lib"])}) (at {x} {y} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid {uid(c["ref"])})')
        # Keep reference/value above the symbol; individual compact resistor values are offset to right.
        small=c['ref'].startswith(('R','C','F')) and not c['ref'].startswith('RV')
        rx,ry=(x+4,y-2) if small else (x,y-15 if c['ref']=='U1' else y-8)
        for name,val,px,py,hide in [('Reference',c['ref'],rx,ry,False),('Value',c['value'],rx,ry+2.3,False),('Footprint',c['fp'],x,y,True),('Datasheet',('https://www.vishay.com/docs/83430/vo617a.pdf' if c['ref']=='U4' else next((v[2] for v in kids(a,'property') if v[1]=='Datasheet'),'')),x,y,True)]:
            out.append(f'(property {q(name)} {q(val)} (at {px} {py} 0) (effects (font (size 1 1)) {"(hide yes)" if hide else ""} {"(justify left)" if small else ""}))')
        for pin in pins: out.append(f'(pin {q(get(pin,"number")[1])} (uuid {uid(c["ref"]+get(pin,"number")[1])}))')
        out.append(f'(instances (project "esp32_dimmer" (path "/{root}" (reference {q(c["ref"])}) (unit 1)))))')
        for pin in pins:
            num=get(pin,'number')[1]; at=get(pin,'at'); dx,dy,ang=map(float,at[1:]); px,py=round(x+dx,5),round(y-dy,5)
            net=c['nets'].get(num)
            if not net:
                out.append(f'(no_connect (at {px} {py}) (uuid {uid(c["ref"]+num+"nc")}))'); continue
            ang=math.radians(ang); lead=5.08; xx=round(px-lead*math.cos(ang),5); yy=round(py+lead*math.sin(ang),5)
            wire(px,py,xx,yy,c['ref']+num+'wire'); label(net,xx,yy,180 if abs(math.cos(ang)-1)<.01 else 0)
    # External regulated supply drives both rails; PWR_FLAGs placed on explicit nets.
    flag=resolve('power','PWR_FLAG'); flag[1]='power:PWR_FLAG'
    out[2]=out[2][:-1]+' '+dump(flag)+')'
    for i,(net,x,y) in enumerate([('+3V3',35.56,99.06),('GND',60.96,99.06)]):
        ref='#FLG0'+str(i+1)
        out.append(f'(symbol (lib_id "power:PWR_FLAG") (at {x} {y} 0) (unit 1) (in_bom no) (on_board yes) (uuid {uid(ref)}) (property "Reference" {q(ref)} (at {x} {y} 0) (effects (font (size 1 1)) (hide yes))) (property "Value" "PWR_FLAG" (at {x} {y-4} 0) (effects (font (size 1 1)))) (instances (project "esp32_dimmer" (path "/{root}" (reference {q(ref)}) (unit 1)))))')
        label(net,x,y)
    text('01 / SELV CONTROL - EXTERNAL 3.3 V',20,20,1.8)
    text('02 / OPTICAL TRIGGER - GPIO4',155,20,1.8)
    text('03 / MAINS, FUSE AND MOV',20,119,1.8)
    text('04 / ZERO-CROSS DETECTOR',155,108,1.8)
    text('05 / TRIAC AND POWER OUTPUT',277,20,1.8)
    text('OFF: inhibit FIRE pulses; NOT galvanic isolation.',145,178,1.6)
    text('GALVANIC BARRIER: U2 and U3.\nNo relay or auxiliary supply. Output remains hazardous when OFF.',210,245)
    text('J1: 1=3V3, 2=GND, 3=SDA(GPIO6), 4=SCL(GPIO7). 3.3 V I2C slave.\nJP1 fitted: regulated external supply >=1 A; capacity must be confirmed. USB flashing: disconnect J1 and open JP1.\nGPIO3=ZC; GPIO4=FIRE; GPIO5 unused. FIRE must stay low at reset.\nFirmware: sync to 50 Hz, soft start, I2C timeout and loss of ZC => OFF.',20,221)
    text('1000 W / 220 V = 4.55 A. Two-layer PCB, 70 um copper, main power tracks 4 mm.\nTO-220 necks 1.75 mm due to 2.54 mm lead pitch and 0.8 mm clearance.\nHeatsink <=4 C/W plus <=0.5 C/W interface, outside the SELV zone.\nFuse and MOV are PCB-mounted. No external thermal cutout.\nReflector PE: direct external certified connection, never logic GND.',20,246)
    text('U2: random-phase MOC3052; do NOT use MOC3063.\nU3: pulse near zero; calibrate actual timing.\nR7+R8: 2x47k / 1W; 0.66 W total maximum at 242 Vac, R -5%.\nSee docs/ZERO_CROSS_CALCULATION.md for calculation and validation.',210,234)
    out.append('(embedded_fonts no))')
    (ROOT/'esp32_dimmer.kicad_sch').write_text('\n'.join(out))
    tables=[]
    for lib in sorted(set(c['lib'].split(':')[0] for c in parts)):
        path='${KIPRJMOD}/../shared/ESP32C3_SuperMini.kicad_sym' if lib=='ESP32C3_SuperMini' else '${KIPRJMOD}/libraries/'+lib+'.kicad_sym'
        if lib!='ESP32C3_SuperMini':
            syms=[dump(a) for name,a in libs.items() if name.startswith(lib+':')]
            (ROOT/f'libraries/{lib}.kicad_sym').write_text('(kicad_symbol_lib (version 20250114) (generator "kicad_symbol_editor") '+'\n'.join(syms)+')')
        tables.append(f'(lib (name {q(lib)}) (type "KiCad") (uri {q(path)}) (options "") (descr "Verified symbol"))')
    tables.append('(lib (name "power") (type "KiCad") (uri "${KICAD10_SYMBOL_DIR}/power.kicad_sym") (options "") (descr ""))')
    (ROOT/'sym-lib-table').write_text('(sym_lib_table (version 7) '+'\n'.join(tables)+')')

def mm(x,y): return p.VECTOR2I(p.FromMM(x),p.FromMM(y))
def board():
    b=p.BOARD(); b.SetCopperLayerCount(2)
    nets={}
    for name in sorted(set(n for c in parts for n in c['nets'].values())):
        n=p.NETINFO_ITEM(b,name); b.Add(n); nets[name]=n
    fps={}
    for c in parts:
        lib,name=c['fp'].split(':')
        base=ROOT/'libraries/Dimmer.pretty' if lib=='Dimmer' else ROOT.parent/'shared/ESP32-C3-SuperMini.pretty' if lib=='Shared' else Path('/usr/share/kicad/footprints')/(lib+'.pretty')
        fp=p.FootprintLoad(str(base),name)
        if fp is None: raise ValueError(c['fp'])
        fp.SetReference(c['ref']); fp.SetValue(c['value']); fp.SetFPID(p.LIB_ID(lib,name))
        fp.SetPath(p.KIID_PATH('/'+uid('sheet')+'/'+uid(c['ref'])))
        fp.SetPosition(mm(*c['pcb'][:2])); fp.SetOrientationDegrees(c['pcb'][2]); b.Add(fp)
        for pad in fp.Pads():
            if pad.GetNumber() in c['nets']: pad.SetNet(nets[c['nets'][pad.GetNumber()]])
        fp.Value().SetVisible(False)
        fp.Reference().SetTextSize(mm(.9,.9)); fp.Reference().SetTextThickness(p.FromMM(.15)); fp.Reference().SetTextAngle(p.EDA_ANGLE(0,p.DEGREES_T))
        fp.Reference().SetPosition(mm(c['pcb'][0]+2,c['pcb'][1]-3))
        fps[c['ref']]=fp
        refs={'J1':(24,20),'C2':(77,12),'J2':(28,92),'J3':(72,94),'U2':(76,31),'U3':(24,31),'R11':(50,56),'R12':(50,66)}
        if c['ref'] in refs: fp.Reference().SetPosition(mm(*refs[c['ref']]))
        if c['ref'] in ['U1','U2','U3']:
            for item in fp.GraphicalItems():
                if item.GetLayer()==p.F_SilkS: item.SetLayer(p.F_Fab)

    for i,(x,y) in enumerate([(5,5),(95,5),(5,95),(95,95)]):
        fp=p.FootprintLoad('/usr/share/kicad/footprints/MountingHole.pretty','MountingHole_3.2mm_M3')
        fp.SetPosition(mm(x,y)); fp.SetReference('H'+str(i+1)); fp.Value().SetVisible(False); fp.Reference().SetVisible(False); b.Add(fp)
    def line(a,z,layer=p.Edge_Cuts,width=.05):
        s=p.PCB_SHAPE(); s.SetShape(p.SHAPE_T_SEGMENT); s.SetStart(mm(*a)); s.SetEnd(mm(*z)); s.SetLayer(layer); s.SetWidth(p.FromMM(width)); b.Add(s)
    def arc(a,m,z):
        s=p.PCB_SHAPE(); s.SetShape(p.SHAPE_T_ARC); s.SetArcGeometry(mm(*a),mm(*m),mm(*z)); s.SetLayer(p.Edge_Cuts); s.SetWidth(p.FromMM(.05)); b.Add(s)
    for a,z in [((4,0),(96,0)),((100,4),(100,96)),((96,100),(4,100)),((0,96),(0,4))]: line(a,z)
    for a,m,z in [((96,0),(98.828427,1.171573),(100,4)),((100,96),(98.828427,98.828427),(96,100)),((4,100),(1.171573,98.828427),(0,96)),((0,4),(1.171573,1.171573),(4,0))]: arc(a,m,z)
    # Three 2mm milled slots. 5mm bridges preserve board stiffness.
    for x1,x2 in [(8,43),(48,52),(57,92)]:
        line((x1,37),(x2,37)); arc((x2,37),(x2+1,38),(x2,39)); line((x2,39),(x1,39)); arc((x1,39),(x1-1,38),(x1,37))
    def txt(s,x,y,size=1,layer=p.F_SilkS):
        t=p.PCB_TEXT(b); t.SetText(s); t.SetPosition(mm(x,y)); t.SetTextSize(mm(size,size)); t.SetTextThickness(p.FromMM(.15)); t.SetLayer(layer); b.Add(t)
    txt('DIMMER / ESP32-C3',80,11,1)
    txt('SELV 3.3V  |  I2C',22,12,1)
    txt('220 Vac  /  DANGER',50,55,1.2)
    txt('MAINS',15.8,98); txt('L   N',17.8,89)
    txt('LOAD',82.8,98); txt('L~   N',82.8,89)
    txt('1:3V3  2:GND',17,8,.85); txt('3:SDA  4:SCL',17,10,.85)
    txt('JP1 RUN',30,23,.8); txt('USB: J1 UNPLUGGED',75,8,.85)
    txt('HALOGEN / REV J',50,97,.8)
    from back_art import draw
    draw(b)
    txt('HEATSINK <=4 C/W',50,94,.85,p.F_Fab)
    # Mechanical envelope for heat sink, no hidden copper beneath it.
    for a,z in [((33,89),(67,89)),((67,89),(67,100)),((67,100),(33,100)),((33,100),(33,89))]: line(a,z,p.Dwgs_User,.15)
    # Exclusion areas: slots and the complete insulation belt, both copper layers.
    def keepout(x1,y1,x2,y2):
        zone=p.ZONE(b); zone.SetIsRuleArea(True); ls=p.LSET(); ls.AddLayer(p.F_Cu); ls.AddLayer(p.B_Cu); zone.SetLayerSet(ls)
        zone.SetDoNotAllowTracks(True); zone.SetDoNotAllowVias(True); zone.SetDoNotAllowZoneFills(True)
        poly=zone.Outline(); poly.NewOutline()
        for x,y in [(x1,y1),(x2,y1),(x2,y2),(x1,y2)]: poly.Append(p.FromMM(x),p.FromMM(y))
        b.Add(zone)
    keepout(0,34,100,42)
    # Keep the space under the module's lower antenna end copper-free except module pads outside this region.
    keepout(43,21,57,30)
    p.SaveBoard(str(ROOT/'esp32_dimmer.kicad_pcb'),b)
    fplibs=sorted(set(c['fp'].split(':')[0] for c in parts)|{'MountingHole'})
    entries=[]
    for lib in fplibs:
        path='${KIPRJMOD}/libraries/Dimmer.pretty' if lib=='Dimmer' else '${KIPRJMOD}/../shared/ESP32-C3-SuperMini.pretty' if lib=='Shared' else '${KICAD10_FOOTPRINT_DIR}/'+lib+'.pretty'
        entries.append(f'(lib (name {q(lib)}) (type "KiCad") (uri {q(path)}) (options "") (descr ""))')
    (ROOT/'fp-lib-table').write_text('(fp_lib_table (version 7) '+'\n'.join(entries)+')')
    return b

if __name__=='__main__':
    schematic(); board()
    (ROOT/'docs/connectivity.json').write_text(json.dumps(parts,indent=2,ensure_ascii=False))
    with (ROOT/'docs/BOM.csv').open('w') as f:
        w=csv.writer(f); w.writerow(['Reference','Value','Footprint','Notes'])
        for c in parts: w.writerow([c['ref'],c['value'],c['fp'],c['notes']])
    print('Generated',len(parts),'components, schematic and placed board.')
