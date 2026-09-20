"""Independent checks against the existing prose/BOM and archived pin mappings."""
import json
import re
from pathlib import Path
from electrical_circuit import PARTS

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/electrical'
source=(OUT/'原理图-v0.1.md').read_text()
bom=(OUT/'BOM-v0.1.md').read_text()


def references(cell):
    refs=[]
    for m in re.finditer(r'\b(ANT|TP|[RCLDJQUSX])(\d{3})(?:[～~–-]([A-Z]*)(\d{3}))?(?![A-Za-z0-9])',cell):
        prefix,num,prefix2,end=m.groups()
        if end:
            assert prefix2 in ('',prefix)
            refs.extend(f'{prefix}{i}' for i in range(int(num),int(end)+1))
        else:refs.append(prefix+num)
    return refs


def magnitude(value, kind):
    value=value.replace('µ','u').replace('μ','u').replace('Ω','R')
    unit={'R':'R','C':'F','L':'H'}[kind]
    if kind=='R' and re.fullmatch(r'[\d.]+[kM]',value):value+='R'
    m=re.search(r'(\d+(?:\.\d+)?)\s*([pnumkM]?)'+unit,value)
    if not m:return None
    return float(m[1])*{'':1,'p':1e-12,'n':1e-9,'u':1e-6,'m':1e-3,'k':1e3,'M':1e6}[m[2]]


refs=set();values=0;supplier_refs=set()
for line in bom.splitlines():
    if not line.startswith('|'):continue
    cells=[c.strip() for c in line.split('|')[1:-1]]
    if len(cells)<2:continue
    for ref in references(cells[0]):
        refs.add(ref)
        if len(cells)==6 and ref in PARTS and not cells[0].startswith('电池'):
            codes=set(re.findall(r'\bC\d{4,}\b',cells[3]))
            expected={PARTS[ref]['lcsc']} if PARTS[ref]['lcsc'] else set()
            assert codes==expected,(ref,codes,expected)
            supplier_refs.add(ref)
        if ref[0] in 'RCL' and ref in PARTS and PARTS[ref]['fitted']:
            a=magnitude(cells[1],ref[0]);b=magnitude(PARTS[ref]['value'],ref[0])
            assert a is not None and b is not None and abs(a-b)<=abs(a)*1e-9,(ref,cells[1],PARTS[ref])
            values+=1
assert refs==set(PARTS)-{'BAT1'},(refs-set(PARTS),set(PARTS)-refs-{'BAT1'})
assert sum(p['fitted'] for p in PARTS.values())==92
assert {r for r,p in PARTS.items() if p['lcsc']} <= supplier_refs

# Independently recover the MCU's connections from the complete prose pin table.
pin_table=source.split('## 8. U200 完整引脚分配表')[1].split('## 9.')[0]
all_nets={n for p in PARTS.values() for n in p['pins'].values() if n is not None}
checked=set()
for line in pin_table.splitlines():
    if not line.startswith('|'):continue
    cells=[c.strip() for c in line.split('|')[1:-1]]
    if len(cells)!=3 or not re.fullmatch(r'\d+|EP',cells[0]):continue
    pin,_,desc=cells
    if desc.startswith(('NC','不连接')):net=None
    else:
        component_pin=re.match(r'(X\d+|J\d+)\.(\d+)',desc)
        if component_pin:net=PARTS[component_pin[1]]['pins'][component_pin[2]]
        else:
            tokens=re.findall(r'\b[A-Z][A-Z0-9_]*\b',desc)
            matches=[t for t in tokens if t in all_nets]
            if matches:net=matches[0]
            elif pin in ('37','38','47'):
                ref=re.search(r'[CL]\d+',desc)[0]
                net=PARTS[ref]['pins']['1']
            else:raise AssertionError((pin,desc))
    assert PARTS['U200']['pins'][pin]==net,(pin,net,PARTS['U200']['pins'][pin])
    checked.add(pin)
assert checked==set(PARTS['U200']['pins'])

# Direct two-terminal declarations in the prose are a second independent source.
direct=0
for m in re.finditer(r'^([RCLD]\d{3})\s+[^\n:]*:\s*([A-Z][A-Z0-9_]*)\s*[—–]\s*([A-Z][A-Z0-9_]*)',source,re.M):
    ref,a,b=m.groups()
    assert set(PARTS[ref]['pins'].values())=={a,b},(ref,a,b,PARTS[ref])
    direct+=1

for ref,expected in {
    'D100':{'2':'VBUS_5V','1':'VSYS'},
    'Q100':{'1':'BAT_PATH_GATE','2':'VSYS','3':'VBAT'},
    'U100':{'1':'CHG_N','2':'GND','3':'VBAT','4':'VBUS_5V','5':'CHG_PROG'},
    'U101':{'1':'VSYS','2':'GND','3':'VSYS','4':None,'5':'VREG_3V3'},
    'D400':{'1':'LED_R_K','2':'VSYS','3':'LED_B_K','4':'LED_G_K'},
    'S307':{'a':'SW_HALF','b':'SW_FULL','c1':'GND','c2':'GND'},
    'ANT200':{'1':'ANT_FEED','2':None},
    'J200':{'1':'VDD','2':'GND','3':'SWDIO','4':'SWDCLK'},
}.items():assert PARTS[ref]['pins']==expected,ref

key_rows=0
key_table=source.split('| 开关／触点 |')[1].split('S300～S306 为')[0]
for line in key_table.splitlines():
    cells=[c.strip() for c in line.split('|')[1:-1]]
    if len(cells)!=6 or not cells[0].startswith('S3'):continue
    switch,_,sw,key,gpio,rc=cells
    resistor,capacitor=references(rc)
    pin=re.search(r'/\s*(\d+)\s*$',gpio)[1]
    assert PARTS['U200']['pins'][pin]==key
    assert PARTS[resistor]['pins']=={'1':key,'2':sw}
    assert PARTS[capacitor]['pins']=={'1':key,'2':'GND'}
    if switch.startswith('S307'):
        assert PARTS['S307']['pins']['a' if 'SW1' in switch else 'b']==sw
    else:assert PARTS[switch]['pins']=={'1':sw,'2':'GND'}
    key_rows+=1
assert key_rows==9

for ref,nets in {
    'L200':('DCC','DCDC_MID'),'L201':('DCDC_MID','DEC4'),
    'C216':('RF_ANT','GND'),'L220':('RF_ANT','RF_50'),
    'C217':('RF_50','GND'),'R221':('RF_50','ANT_FEED'),'C218':('ANT_FEED','GND'),
    'C214':('P025_FILTER','GND'),'C215':('P026_FILTER','GND'),
}.items():assert PARTS[ref]['pins']==dict(zip(['1','2'],nets)),ref
# Exactly one 12 pF load on each oscillator terminal; no residual extra branch.
for ref,net in [('C210','XC1'),('C211','XC2'),('C212','XL1'),('C213','XL2')]:
    caps={r for r,p in PARTS.items() if p['kind']=='C' and net in p['pins'].values()}
    assert caps=={ref},(net,caps)
    assert PARTS[ref]['pins']=={'1':net,'2':'GND'}
    assert abs(magnitude(PARTS[ref]['value'],'C')-12e-12)<1e-20
    assert PARTS[ref]['lcsc']=='C45359894'
for i,ch in enumerate('RGB'):
    assert PARTS[f'Q{400+i}']['pins']=={'1':f'LED_{ch}_G','2':'GND','3':f'LED_{ch}_D'}
    assert PARTS[f'R{400+i}']['pins']=={'1':f'LED_{ch}_K','2':f'LED_{ch}_D'}
    assert PARTS[f'R{403+i}']['pins']=={'1':f'LED_{ch}_PWM','2':f'LED_{ch}_G'}
    assert PARTS[f'R{406+i}']['pins']=={'1':f'LED_{ch}_G','2':'GND'}

report=json.loads((OUT/'schematic-checks.json').read_text())
report.update(bom_references=len(refs),passive_values_checked=values,prose_mcu_pins_checked=len(checked),
              supplier_bom_rows_checked=len(supplier_refs),
              components_with_jlc_code=sum(bool(p['lcsc']) for p in PARTS.values()),
              distinct_jlc_codes=len({p['lcsc'] for p in PARTS.values() if p['lcsc']}),
              direct_prose_connections_checked=direct,key_channels_checked=key_rows,
              scope='Drawing/source consistency only; not EDA ERC, RF validation, or prototype testing.')
(OUT/'schematic-checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False))
