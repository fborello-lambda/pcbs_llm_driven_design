from pathlib import Path
import csv,json,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[2]/'dimmer'
parts=json.loads((ROOT/'docs/connectivity.json').read_text());xml=ET.parse(ROOT/'outputs/netlist.xml');fps={c.attrib['ref']:c.findtext('footprint','') for c in xml.findall('.//components/comp')}
with (ROOT/'docs/BOM.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['Reference','Value','Footprint','Notes'])
 for c in parts:w.writerow([c['ref'],c['value'],fps[c['ref']],c['notes']])
 for r in [('J2-J3 mating connectors','2 compatible WR-TBL 3114 7.62 mm cable connectors','EXTERNAL','Required; headers alone do not connect a cable.'),('HS1','Heatsink <=4 C/W','EXTERNAL','Thermal interface <=0.5 C/W.'),('F1 cartridge','T6.3AH/250V ceramic HBC','F1','Validate inrush.'),('H1-H4','4 M3 screws and insulating spacers','NPTH 3.2 mm',''),('PE','Certified protective-earth terminal','EXTERNAL','Directly to reflector PE; never logic GND.'),('JP1 shunt','2.54 mm shunt','JP1','Remove and disconnect J1 for USB flashing.')]:w.writerow(r)
