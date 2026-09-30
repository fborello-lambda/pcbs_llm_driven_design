#!/usr/bin/python3
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[2]/'dimmer'
parts=json.loads((ROOT/'docs/connectivity.json').read_text())
lv={'GND','+3V3','3V3_EXT','SDA','SCL','FIRE','ZC','BASE','OPTO_A','OPTO_K'}
act=set()
names=sorted({n for c in parts for n in c['nets'].values()})
def nc(name,clear,width):
    return dict(name=name,clearance=clear,track_width=width,via_diameter=.9,via_drill=.45,microvia_diameter=.3,microvia_drill=.1,diff_pair_width=.25,diff_pair_gap=.25,diff_pair_via_gap=.25,pcb_color='rgba(0, 0, 0, 0.000)',schematic_color='rgba(0, 0, 0, 0.000)',wire_width=6,bus_width=12,line_style=0)
proj={'meta':{'filename':'esp32_dimmer.kicad_pro','version':1},'net_settings':{'meta':{'version':4},'classes':[nc('Default',.25,.45),nc('SELV',.25,.45),nc('MAINS',.8,.75)],'netclass_patterns':[{'netclass':'SELV' if n in lv else 'ACTUATOR' if n in act else 'MAINS','pattern':'/'+n} for n in names]},'board':{'design_settings':{'rules':{'min_clearance':.25,'min_track_width':.25,'min_copper_edge_clearance':.5,'min_hole_clearance':.25,'min_through_hole_diameter':.3,'min_via_diameter':.6,'min_via_annular_width':.15,'min_silk_clearance':.15,'min_silk_text_height':.8,'min_silk_text_thickness':.12,'solder_mask_min_width':.1},'rule_severities':{},'drc_exclusions':[]}}}
(ROOT/'esp32_dimmer.kicad_pro').write_text(json.dumps(proj,indent=2))
(ROOT/'esp32_dimmer.kicad_dru').write_text('''(version 1)
(rule "MAINS-to-SELV barrier 8mm"
 (condition "(A.NetClass == 'MAINS' && B.NetClass == 'SELV') || (A.NetClass == 'SELV' && B.NetClass == 'MAINS')")
 (constraint clearance (min 8mm)))
(rule "MAINS copper clearance 0.8mm"
 (condition "A.NetClass == 'MAINS' && B.NetClass == 'MAINS'")
 (constraint clearance (min 0.8mm)))
''')
pcb=ROOT/'esp32_dimmer.kicad_pcb'; s=pcb.read_text()
if '(stackup' not in s:
    stack='''
        (stackup
            (layer "F.SilkS" (type "Top Silk Screen"))
            (layer "F.Mask" (type "Top Solder Mask") (color "Green"))
            (layer "F.Cu" (type "copper") (thickness 0.07))
            (layer "dielectric 1" (type "core") (thickness 1.46) (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02))
            (layer "B.Cu" (type "copper") (thickness 0.07))
            (layer "B.Mask" (type "Bottom Solder Mask") (color "Green"))
            (layer "B.SilkS" (type "Bottom Silk Screen"))
            (copper_finish "HASL") (dielectric_constraints no))
'''
    s=s.replace('(setup','(setup'+stack,1); pcb.write_text(s)
