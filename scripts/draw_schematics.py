"""Draw the reviewed v0.1 circuit with Schemdraw; run with uv run.

Every physical terminal is registered against electrical_circuit.py. The
geometry audit checks that terminals actually touch their intended wires,
that wire islands have a net label/ground, and that different nets never
intersect. This is drawing QA, not an EDA ERC or a hardware qualification.
"""
from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import schemdraw
import schemdraw.elements as elm
from schemdraw.segments import Segment, SegmentText, SegmentPoly
from shapely.geometry import LineString, Point

from electrical_circuit import PARTS, MCU, KEYS

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/electrical'
ASSETS = OUT / 'schematic-assets'
INK = '#203543'
WIRE = '#267365'
MUTED = '#687b83'
RULE = '#d5e1df'
AMBER = '#a47731'
SUPPLIER = '#4c718a'
FONT = 'Arial, PingFang SC, Microsoft YaHei, sans-serif'
SHEETS = []
DRAWN = {}


class Sheet:
    def __init__(self, number, slug, title, subtitle, notes, height=30):
        self.number, self.slug, self.title = number, slug, title
        self.notes, self.height = notes, height
        self.wires, self.ports, self.terminals, self.ncs = [], [], [], []
        self.supplier_labels = []
        self.d = schemdraw.Drawing(show=False, canvas='svg', inches_per_unit=.43,
                                  fontsize=11, font=FONT, color=INK, lw=1.35)
        self.box((.15, .15), (47.85, height-.15), color=RULE, fill='white', lw=.8)
        self.text(1.3, height-1.15, f'{number:02d} / 07', size=11, color=WIRE)
        self.text(5.0, height-1.2, title, size=21)
        self.text(46.6, height-1.1, 'nRF CANON REMOTE', size=11, align='right')
        self.text(46.6, height-1.9, 'SCHEMATIC v0.1  /  2026-09-20', size=9, color=MUTED, align='right')
        self.text(5.0, height-2.15, subtitle, size=10, color=MUTED)
        self.rule((1.3, height-2.9), (46.7, height-2.9))
        self.box((1.3, 1.65), (46.7, 6.35), color=RULE, fill='#f7faf9', lw=.7)
        self.text(2, 5.6, '连接与 LAYOUT', size=11, color=WIRE)
        for i, note in enumerate(notes):
            self.text(2, 4.65-i*.78, note, size=10, color=INK)
        self.text(1.3, .85, '同名网络跨页相连  ·  实心点为连接  ·  × 为 NC  ·  DNP 为不装  ·  JLC C… 为立创物料编号', size=9, color=MUTED)
        self.text(46.7, .85, f'设计审阅稿  /  {number:02d}', size=9, color=MUTED, align='right')
        SHEETS.append(self)

    def graphic(self, segments):
        obj = elm.Element()
        obj.segments.extend(segments)
        # Absolute page geometry must not inherit the last component's angle.
        self.d.add(obj.at((0, 0)).theta(0))

    def text(self, x, y, text, size=11, color=INK, align='left'):
        self.graphic([SegmentText((x, y), text, fontsize=size, font=FONT,
                                 color=color, align=(align, 'center'))])

    def rule(self, a, b, color=RULE, ls='-', lw=.8):
        self.graphic([Segment([a, b], color=color, lw=lw, ls=ls)])

    def box(self, a, b, color=INK, fill=None, lw=1.2, ls='-'):
        x1, y1 = a; x2, y2 = b
        self.graphic([SegmentPoly([(x1,y1),(x2,y1),(x2,y2),(x1,y2)],
                                  color=color, fill=fill, lw=lw, ls=ls, zorder=0)])

    def section(self, x, y, label):
        self.text(x, y, label, size=11, color=WIRE)

    def supplier(self, ref, x, y, align='left'):
        self.text(x, y, PARTS[ref]['supplier_label'], size=8.5,
                  color=SUPPLIER if PARTS[ref]['lcsc'] else MUTED, align=align)
        self.supplier_labels.append(dict(ref=ref, text=PARTS[ref]['supplier_label'], p=[x,y]))

    def wire(self, net, *points):
        assert net is not None
        for a, b in zip(points, points[1:]):
            if Point(a).distance(Point(b)) < 1e-7:
                continue
            assert abs(a[0]-b[0]) < 1e-6 or abs(a[1]-b[1]) < 1e-6, (a,b)
            self.d.add(elm.Line().at(a).to(b).color(WIRE).linewidth(1.2))
            self.wires.append(dict(net=net, a=list(a), b=list(b)))

    def dot(self, p):
        self.d.add(elm.Dot(radius=.065).at(p).color(WIRE))

    def port(self, net, p, direction='left', label=True):
        x,y=p
        dx,dy={'left':(-.6,0),'right':(.6,0),'up':(0,.6)}[direction]
        end=(x+dx,y+dy)
        self.wire(net,p,end)
        self.ports.append(dict(net=net, p=list(end), kind='label'))
        if label:
            if direction=='up': self.text(end[0],end[1]+.38,net,size=10,color=WIRE,align='center')
            else: self.text(end[0],end[1]+.40,net,size=10,color=WIRE,
                           align='left' if direction=='right' else 'right')

    def ground(self, p):
        self.d.add(elm.Ground().at(p).color(WIRE))
        self.ports.append(dict(net='GND', p=list(p), kind='ground'))

    def nc(self, p):
        self.d.add(elm.NoConnect().at(p).color(AMBER))
        self.ncs.append(list(p))

    def terminal(self, ref, pin, point):
        pin=str(pin)
        assert pin in PARTS[ref]['pins'], (ref,pin)
        key=f'{ref}.{pin}'
        assert key not in DRAWN, f'Duplicate physical terminal {key}'
        info=dict(ref=ref,pin=pin,net=PARTS[ref]['pins'][pin],p=list(point),sheet=self.number)
        self.terminals.append(info); DRAWN[key]=info

    def two(self, ref, a, b, *, pin1='1', pin2='2', kind=None, label=True, side='above', value=None):
        data=PARTS[ref]
        kind=kind or data['kind']
        cls={'R':elm.ResistorIEC,'C':elm.Capacitor,'L':elm.Inductor2,
             'TVS':elm.DiodeTVS,'schottky':elm.Schottky,'switch':elm.Button,
             'crystal':elm.Crystal,'LED':elm.LED}[kind]
        element=cls().at(a).to(b)
        if not data['fitted']: element.color(AMBER)
        self.d.add(element)
        self.terminal(ref,pin1,element.start);self.terminal(ref,pin2,element.end)
        x=(a[0]+b[0])/2; y=(a[1]+b[1])/2
        val=value or data['value']
        if label:
            col=AMBER if not data['fitted'] else INK
            if abs(a[0]-b[0])<1e-6:
                sign=-1 if side=='left' else 1
                self.text(x+sign*.5,y+.3,ref,size=11,color=col,align='right' if sign<0 else 'left')
                self.text(x+sign*.5,y-.35,val,size=9,color=col,align='right' if sign<0 else 'left')
                self.supplier(ref,x+sign*.5,y-.94,align='right' if sign<0 else 'left')
            else:
                sign=-1 if side=='below' else 1
                raised = .45 if kind in ('L','switch') else 0
                self.text(x,y+sign*(1.65+raised),ref,size=11,color=col,align='center')
                self.supplier(ref,x,y+sign*(1.05+raised),align='center')
                self.text(x,y+sign*(.45+raised),val,size=9,color=col,align='center')
        return element

    def cap(self, ref, x, y, length=2.4, side='right'):
        e=self.two(ref,(x,y),(x,y-length),side=side)
        self.ground(e.end)
        return e

    def ic(self, ref, a, b, pins, *, title=None, subtitle=None):
        """pins: (pin number, pin name, side, position along that side)."""
        self.box(a,b,fill='#f5f9f8')
        x1,y1=a; x2,y2=b
        self.text((x1+x2)/2,(y1+y2)/2+.4,title or ref,size=13,align='center')
        self.text((x1+x2)/2,(y1+y2)/2-.45,subtitle or PARTS[ref]['value'],size=9,align='center',color=MUTED)
        self.supplier(ref,(x1+x2)/2,(y1+y2)/2-1.12,align='center')
        anchors={}
        for numbers,name,side,pos in pins:
            nums=str(numbers).split(',')
            if side=='L':
                inside=(x1,pos);end=(x1-.65,pos)
                self.text(x1+.25,pos,name,size=10)
                self.text(x1-.3,pos+.28,str(numbers),size=8,align='right',color=MUTED)
            elif side=='R':
                inside=(x2,pos);end=(x2+.65,pos)
                self.text(x2-.25,pos,name,size=10,align='right')
                self.text(x2+.3,pos+.28,str(numbers),size=8,color=MUTED)
            elif side=='B':
                inside=(pos,y1);end=(pos,y1-.65)
                self.text(pos,y1+.4,name,size=9,align='center')
                self.text(pos+.15,y1-.35,str(numbers),size=8,color=MUTED)
            else:
                inside=(pos,y2);end=(pos,y2+.65)
                self.text(pos,y2-.4,name,size=9,align='center')
                self.text(pos+.15,y2+.35,str(numbers),size=8,color=MUTED)
            # A pin stub is part of the symbol, not an external wire.
            self.rule(inside,end,color=INK,lw=1.2)
            nets={PARTS[ref]['pins'][n] for n in nums}
            assert len(nets)==1, (ref,nums,nets)
            for n in nums: self.terminal(ref,n,end); anchors[n]=end
        return anchors

    def fet(self, ref, drain_or_source):
        cls=elm.PMos if PARTS[ref]['kind']=='PMOS' else elm.NMos
        e=self.d.add(cls(diode=True).at(drain_or_source).theta(0))
        for pin,anchor,name in [('1',e.gate,'G'),('2',e.source,'S'),('3',e.drain,'D')]:
            self.terminal(ref,pin,anchor)
            self.text(anchor.x+(.25 if name!='G' else -.15),anchor.y+.3,f'{pin} {name}',size=8,
                      align='left' if name!='G' else 'right',color=MUTED)
        self.text(drain_or_source[0]+1.2,drain_or_source[1]-1.1,ref,size=11)
        self.text(drain_or_source[0]+1.2,drain_or_source[1]-1.75,PARTS[ref]['value'],size=9)
        self.supplier(ref,drain_or_source[0]+1.2,drain_or_source[1]-2.4)
        return e

    def testpoint(self, ref, p):
        self.d.add(elm.Dot(open=True,radius=.12).at(p).color(INK))
        self.terminal(ref,'1',p)
        self.text(p[0],p[1]+.6,ref,size=10,align='center')
        self.port(PARTS[ref]['pins']['1'],p,'right')
        self.supplier(ref,p[0]-.3,p[1]-.65)

    def finish(self):
        # Add junction dots at physical wire branches and component tees.
        pts={tuple(t['p']) for t in self.terminals if t['net'] is not None}
        pts.update(tuple(w['a']) for w in self.wires)
        pts.update(tuple(w['b']) for w in self.wires)
        for p in pts:
            on=[w for w in self.wires if LineString([w['a'],w['b']]).distance(Point(p))<1e-6]
            degree=sum(1 if p in [tuple(w['a']),tuple(w['b'])] else 2 for w in on)
            degree+=sum(Point(t['p']).distance(Point(p))<1e-6 for t in self.terminals if t['net'] is not None)
            if degree>=3:self.dot(p)
        target=ASSETS/f'{self.number:02d}-{self.slug}.svg'
        self.d.save(target,transparent=False)
        svg=target.read_text()
        svg=svg.replace('<svg ',f'<svg role="img" aria-label="{html.escape(self.title)}" ',1)
        target.write_text(svg)
        self.file=target.name


def sheet_usb():
    s=Sheet(1,'usb-charge','USB-C 输入与电池充电','6Pin 电源接口 · 独立 CC 下拉 · 100 mA 线性充电',[
        'ESD 紧邻接口；线路先经过保护连接点再入板，地端就近落过孔。CC1、CC2 不短接。',
        'C101 紧邻 U100.4，C102 紧邻 U100.3；R105 靠 PROG，回地靠 U100.2，充电区铺地散热。',
        'J101 只接带保护电池包 P+/P−。MSTP4054 不含电芯保护或 NTC；最终电池须允许 100 mA 充电。',
        'CHG_N 低表示充电中；高电平需结合 USB_PRESENT_N 判断。D101～D103 为双向 ESD，不是持续过压保护。'])
    s.section(2,26,'A / USB-C 与输入旁路')
    p=s.ic('J100',(2,19),(8,24.8),[
        ('A9,B9','VBUS','R',23.5),('A5','CC1','R',21.9),('B5','CC2','R',20.3),
        ('A12,B12','GND','B',3.7),('17,18,19,20','SHIELD','B',6.6)],subtitle='HX TYPE-C 6P QTWT')
    for pin,net in [('A9','VBUS_5V'),('A5','USB_CC1'),('B5','USB_CC2')]:
        s.wire(net,p[pin],(10,p[pin][1]));s.port(net,(10,p[pin][1]),'right')
    for pin in ['A12','17']:s.ground(p[pin])
    for ref,x in [('C100',14),('D101',18)]:
        e=s.two(ref,(x,23.5),(x,20.8),value='100nF / 16V' if ref=='C100' else 'ESD, bidir.')
        s.ground(e.end)
    s.wire('VBUS_5V',(14,23.5),(18,23.5));s.port('VBUS_5V',(14,23.5),'up')
    s.section(24,26,'B / 每路 CC 独立下拉与保护')
    for i,x in enumerate([25,37]):
        net=f'USB_CC{i+1}'
        s.port(net,(x,23.5),'up')
        s.wire(net,(x,23.5),(x+4,23.5))
        for ref,xx in [(f'R{100+i}',x),(f'D{102+i}',x+4)]:
            e=s.two(ref,(xx,23.5),(xx,20.8),value='5.1k / 1%' if ref.startswith('R') else 'ESD, bidir.')
            s.ground(e.end)
    s.text(25,18.9,'D101–D103  /  PESDNC2FD5VB',size=10,color=MUTED)
    s.section(2,17,'C / 充电器与带保护软包电池')
    p=s.ic('U100',(10,9.1),(18,15.6),[
        ('4','VCC','L',14.3),('5','PROG','L',11.3),('2','GND','B',14),
        ('3','BAT','R',14.3),('1','CHRG','R',11.3)])
    s.wire('VBUS_5V',p['4'],(6,14.3));s.port('VBUS_5V',(6,14.3),'up')
    s.cap('C101',6,14.3,side='left')
    s.wire('CHG_PROG',p['5'],(8,11.3),(8,10.8))
    e=s.two('R105',(8,10.8),(8,8.3),side='left');s.ground(e.end)
    s.ground(p['2'])
    s.wire('VBAT',p['3'],(23,14.3),(29,14.3));s.port('VBAT',(29,14.3),'right')
    s.cap('C102',23,14.3)
    s.wire('CHG_N',p['1'],(20.5,11.3),(20.5,8.6));s.port('CHG_N',(20.5,8.6),'right')
    s.text(10,7.5,'RPROG = 10k → ICHG ≈ 100mA',size=10,color=MUTED)
    s.port('VDD',(28,11.5),'up')
    e=s.two('R106',(28,11.5),(28,8.5))
    s.wire('CHG_N',e.end,(31.5,8.5));s.port('CHG_N',(31.5,8.5),'right')
    p=s.ic('J101',(35,11.5),(39.7,15.5),[('1','P+','L',14.5),('2','P−','L',12.5)],subtitle='焊线焊盘')
    s.port('VBAT',p['1'],'left');s.ground(p['2'])
    e=s.d.add(elm.BatteryCell().at((43,14.5)).to((43,11.7)))
    # BatteryCell.start is the positive (long-line) terminal.
    s.terminal('BAT1','+',e.start);s.terminal('BAT1','-',e.end)
    s.port('VBAT',e.start,'up');s.ground(e.end)
    s.text(43,10.5,'1S / 4.2V',size=10,align='center')
    s.text(43,9.7,'带保护 / ~320mAh',size=9,align='center')
    s.supplier('BAT1',43,8.9,align='center')
    return s


def sheet_power():
    s=Sheet(2,'power-sense','供电切换、稳压与检测','USB / 电池自动切换 · 3.3 V MCU 电源 · 低有效 USB 检测',[
        'Q100：1=G、2=S→VSYS、3=D→VBAT；体二极管为 VBAT→VSYS。D100：2=A→VBUS、1=K→VSYS。',
        'D100、Q100、C103 与 LDO 靠近；C103 靠 VIN，C104 靠 VOUT/GND。充电支路与系统支路在电池入口分开。',
        'R110/R111/C105 靠 ADC，避开 RF、DCC、PWM；SAADC 内部参考 0.6V、增益 1/6、采集 40µs，上电等 ≥250ms。',
        'R104 用于测 MCU 支路电流，不隔离整机；RGB 取电 VSYS。电池低压时 VDD 会低于 3.3V。'])
    s.section(2,26,'A / USB 与电池通路')
    s.port('VBUS_5V',(4.5,24),'left')
    s.wire('VBUS_5V',(4.5,24),(6,24))
    e=s.two('D100',(6,24),(9,24),pin1='2',pin2='1',value='BAT54H')
    s.text(6,23.55,'2 A',size=8,color=MUTED);s.text(9,23.55,'1 K',size=8,color=MUTED,align='right')
    q=s.fet('Q100',(21,22.8))
    s.wire('VSYS',e.end,(21,24),q.source);s.port('VSYS',(21,24),'up')
    s.wire('VBAT',q.drain,(21,18.7),(22,18.7));s.port('VBAT',(22,18.7),'right')
    gy=q.gate.y
    s.port('VBUS_5V',(10.5,gy),'left');s.wire('VBUS_5V',(10.5,gy),(12,gy))
    e=s.two('R102',(12,gy),(15,gy),label=False)
    # Keep the ref below the VSYS wire; place the supplier ID below the resistor.
    s.text(13.5,gy+1.05,'R102',size=11,align='center')
    s.text(13.5,gy+.45,PARTS['R102']['value'],size=9,align='center')
    s.supplier('R102',13.5,gy-.75,align='center')
    s.wire('BAT_PATH_GATE',e.end,q.gate)
    s.wire('BAT_PATH_GATE',(17.6,gy),(17.6,gy-.6))
    e=s.two('R103',(17.6,gy-.6),(17.6,18.1),side='left');s.ground(e.end)
    s.text(3,18.4,'插线：Q100 关闭 / D100 供电',size=10,color=MUTED)
    s.section(27,26,'B / 3.3 V 稳压')
    p=s.ic('U101',(30,18.8),(36,24.7),[('1','VIN','L',23.2),('3','CE','L',21),
        ('2','VSS','B',33),('5','VOUT','R',23.2),('4','NC','R',21)],subtitle='ME6211C33M5G-N')
    s.wire('VSYS',p['1'],(28,23.2),(27,23.2));s.port('VSYS',(27,23.2),'up')
    s.wire('VSYS',p['3'],(28,21),(28,23.2));s.cap('C103',27,23.2,3.5,side='left')
    s.ground(p['2']);s.nc(p['4'])
    s.wire('VREG_3V3',p['5'],(38.5,23.2),(40,23.2));s.cap('C104',38.5,23.2,3.5)
    e=s.two('R104',(40,23.2),(43,23.2));s.wire('VDD',e.end,(44.5,23.2));s.port('VDD',(44.5,23.2),'right')
    s.text(40,18.9,'VREG_3V3 → R104 → VDD',size=9,color=MUTED,align='center')
    s.section(2,16.6,'C / USB 检测（GPIO 无 5V 直连）')
    q=s.fet('Q101',(12,12.5));s.ground(q.source)
    e=s.two('R109',(12,15.7),q.drain);s.port('VDD',e.start,'up')
    s.wire('USB_PRESENT_N',q.drain,(17,12.5));s.port('USB_PRESENT_N',(17,12.5),'right')
    gy=q.gate.y
    s.port('VBUS_5V',(4,gy),'left');s.wire('VBUS_5V',(4,gy),(5,gy))
    e=s.two('R107',(5,gy),(8,gy));s.wire('USB_GATE',e.end,q.gate)
    e=s.two('R108',(9.2,gy),(9.2,7.6),side='left');s.ground(e.end)
    s.text(15,8.1,'有 USB → USB_PRESENT_N = 0',size=9,color=MUTED)
    s.section(27,16.6,'D / 电池电压 / 2')
    e=s.two('R110',(29,15),(29,12));s.port('VBAT',e.start,'up')
    e=s.two('R111',(29,12),(29,8.7));s.ground(e.end)
    s.wire('VBAT_SENSE',(29,12),(35,12),(41,12));s.port('VBAT_SENSE',(41,12),'right')
    s.cap('C105',35,12,3.3)
    s.text(38,9,'U200.4 / P0.02 / AIN0',size=10,color=MUTED)
    return s


def sheet_mcu_power():
    s=Sheet(3,'mcu-power','nRF52832 电源与内部 DC/DC','U200 的电源分单元 · QFAA / QFN48 · DEC 网络独立',[
        'C200/C201/C202 紧贴对应 DEC 引脚；就近接地，三个 DEC 不互连，不用于外部供电。DEC2 / pin 32 不接。',
        'C203 靠 pin 13；C204 靠 pin 36；C205/C206 靠 pin 48。EP 必须连接完整地平面并设置接地过孔。',
        'DCC → 10µH → 15nH → DEC4，紧凑布局；DCC 节点避开晶体/RF。L200 采用 MLZ1608M100WT000（≥50mA）。',
        '默认装 L200/L201，固件开启 DC/DC；内部 LDO 调试时两电感 DNP、DCC 悬空、C202 保留。核对 C202/C205 的替代规格。'])
    p=s.ic('U200',(17,9.1),(27,25.6),[
        ('13','VDD','L',23.5),('36','VDD','L',19.5),('48','VDD','L',15.5),
        ('32','DEC2','L',12),('44','NC','L',10.5),
        ('1','DEC1','R',23.5),('33','DEC3','R',19.5),('46','DEC4','R',15.5),('47','DCC','R',11),
        ('31','VSS','B',19),('45','VSS','B',22),('EP','EP','B',25)],title='U200 · POWER',subtitle='nRF52832-QFAA / 6 × 6 mm')
    for pin,ref,y in [('13','C203',23.5),('36','C204',19.5)]:
        s.wire('VDD',p[pin],(10,y),(6,y));s.port('VDD',(6,y),'up');s.cap(ref,10,y,2.5)
    s.wire('VDD',p['48'],(10,15.5),(5,15.5));s.port('VDD',(5,15.5),'up')
    s.cap('C205',5,15.5,2.5);s.cap('C206',10,15.5,2.5)
    for pin in ['32','44']:s.nc(p[pin])
    for pin in ['31','45','EP']:s.ground(p[pin])
    for pin,ref,y in [('1','C200',23.5),('33','C201',19.5),('46','C202',15.5)]:
        net=PARTS['U200']['pins'][pin]
        s.wire(net,p[pin],(34,y));s.cap(ref,34,y,2.6)
        s.text(29,y+.45,net,size=10,color=WIRE)
    s.wire('DCC',p['47'],(29,11),(29,9.8),(30,9.8))
    e=s.two('L200',(30,9.8),(34,9.8))
    s.wire('DCDC_MID',e.end,(35.5,9.8))
    e=s.two('L201',(35.5,9.8),(39.5,9.8))
    s.wire('DEC4',e.end,(43,9.8),(43,15.5),(34,15.5))
    s.text(39.5,22.5,'DEC1 ≠ DEC3 ≠ DEC4',size=11,color=WIRE,align='center')
    s.text(39.5,21.3,'内部稳压节点',size=10,color=MUTED,align='center')
    s.text(39.5,20.4,'禁止与 VDD 短接',size=10,color=MUTED,align='center')
    return s


def sheet_clock_rf():
    s=Sheet(4,'clock-rf','时钟与 2.4 GHz 射频','两组晶体负载 · Nordic 芯片端参考网络 · 陶瓷天线匹配预留',[
        '晶体及负载电容紧贴对应 MCU 脚、短线/少过孔；下方不走 DCC/PWM/SWD。X200 的 2/4 为外壳接地。',
        '按已有开发板用值：HF、LF 每侧各一颗 12pF 到地，共 C210–C213 四颗；电容靠对应晶体端放置。',
        'C216 在 ANT 引脚一侧，地端紧靠 U200.31/EP；C216/L220 局部布局复制 Nordic。RF_50 以后按实际叠层定 50Ω。',
        'C217/C218 首版 DNP；装壳后调匹配。ANT200.2 为 NC；按厂家净空图放置，远离电池铝膜、USB 壳和金属件。'])
    s.section(2,26,'A / 32 MHz  ·  CL = 10 pF  ·  每侧 1 × 12 pF')
    e=s.two('X200',(9,23),(15,23),pin1='1',pin2='3',kind='crystal',value='32MHz / YE32MDBCD2X')
    s.text(9,22.55,'1',size=8,color=MUTED);s.text(15,22.55,'3',size=8,color=MUTED)
    s.wire('XC1',e.start,(5,23));s.port('XC1',(5,23),'up')
    s.wire('XC2',e.end,(19,23));s.port('XC2',(19,23),'up')
    for ref,x in [('C210',5),('C211',19)]:
        s.cap(ref,x,23,2.5,side='left' if x==19 else 'right')
    # The crystal's two case pads are separate from the resonant terminals.
    s.box((10.6,21.4),(13.4,23.8),color=RULE,ls='--',lw=.8)
    for pin,x in [('2',11.3),('4',12.7)]:
        s.rule((x,21.4),(x,20.5),color=INK)
        s.terminal('X200',pin,(x,20.5));s.ground((x,20.5))
        s.text(x,21, pin,size=8,color=MUTED)
    s.section(26,26,'B / 32.768 kHz  ·  CL = 12.5 pF  ·  每侧 1 × 12 pF')
    e=s.two('X201',(33,23),(39,23),kind='crystal',value='32.768kHz / KFC3276812520T')
    s.text(33,22.55,'1',size=8,color=MUTED);s.text(39,22.55,'2',size=8,color=MUTED)
    s.wire('XL1',e.start,(29,23));s.port('XL1',(29,23),'up')
    s.wire('XL2',e.end,(43,23));s.port('XL2',(43,23),'up')
    for ref,x in [('C212',29),('C213',43)]:
        s.cap(ref,x,23,2.5,side='left' if x==43 else 'right')
    s.section(2,18.5,'C / 主控时钟与 RF 单元')
    p=s.ic('U200',(5,8.8),(13,17.1),[
        ('34','XC1','L',15.7),('35','XC2','L',14.1),('2','P0.00 / XL1','L',12.5),('3','P0.01 / XL2','L',10.9),
        ('30','ANT','R',14.1)],title='U200 · RF / CLK',subtitle='nRF52832-QFAA')
    for pin in ['34','35','2','3']:s.port(PARTS['U200']['pins'][pin],p[pin],'left')
    s.wire('RF_ANT',p['30'],(16,14.1),(18,14.1));s.cap('C216',16,14.1,2.8)
    e=s.two('L220',(18,14.1),(23,14.1))
    s.wire('RF_50',e.end,(26,14.1),(29,14.1));s.cap('C217',26,14.1,2.8)
    e=s.two('R221',(29,14.1),(33,14.1))
    s.wire('ANT_FEED',e.end,(35,14.1),(39.35,14.1));s.cap('C218',35,14.1,2.8)
    p=s.ic('ANT200',(40,12.4),(46,16.4),[('1','INPUT','L',14.1),('2','NC','B',44)],subtitle='KH-2012-HM1')
    s.nc(p['2'])
    s.text(16,16.4,'Nordic QFN48 参考初值',size=10,color=WIRE)
    s.text(26,16.4,'天线 π 匹配预留',size=10,color=AMBER)
    s.text(24,13.5,'RF_50',size=9,color=WIRE)
    s.text(34,13.5,'ANT_FEED',size=9,color=WIRE)
    s.text(16,9.2,'ANT 侧 → C216 → L220 这一段不按普通 50Ω 长线处理',size=10,color=MUTED)
    return s


def sheet_keys():
    s=Sheet(5,'switches','按键与两段快门','7 颗普通轻触 + 1 颗两段轻触 · 9 路独立 GPIO · 按下为低',[
        'GPIO 开内部上拉，可配置 SENSE 唤醒；1k / 1nF 用于尖峰抑制，固件仍需约 5–15ms 去抖。',
        '每路 1nF 位于电阻的 MCU 侧，R/C 靠近 MCU；开关与键帽顶柱对齐，长线避开 RF/晶体。',
        'S307 是一颗器件：a=第一段、b=第二段、两个 c 公共焊脚都接地；定位孔为 NPTH，不作电气连接。',
        '按厂家焊盘视图映射 a/b/c，避免顶/底视图镜像；半按/全按闭合时序在实物上确认后用于固件。'])
    s.section(2,26,'A / 圆环与下排按键')
    s.section(26,26,'B / 下排按键与中心两段键')
    for i,(name,pin,desc) in enumerate(KEYS):
        if i<5: x=2; y=24-i*3.4
        elif i<7: x=26;y=24-(i-5)*3.4
        else: x=26;y=14-(i-7)*3.5
        net=f'KEY_{name}';sw=f'SW_{name}'
        # The label sits over a short external lead, all RC branches are explicit.
        s.port(net,(x+3,y),'left')
        s.wire(net,(x+3,y),(x+4.5,y),(x+7,y))
        s.cap(f'C{300+i}',x+4.5,y,1.6,side='left')
        e=s.two(f'R{300+i}',(x+7,y),(x+10,y))
        s.wire(sw,e.end,(x+13,y))
        s.text(x+10.7,y-.55,sw,size=8,color=WIRE)
        if i<7:
            e=s.two(f'S{300+i}',(x+13,y),(x+16,y),value=desc)
            s.wire('GND',e.end,(x+18,y));s.ground((x+18,y))
            s.text(x+13,y-.65,'1',size=8,color=MUTED);s.text(x+16,y-.65,'2',size=8,color=MUTED)
        else:
            e=s.two('S307',(x+13,y),(x+16,y),pin1='a' if i==7 else 'b',pin2='c1' if i==7 else 'c2',
                    kind='switch',label=False)
            s.text(x+14.5,y+1.05,'SW1 / 半按' if i==7 else 'SW2 / 全按',size=10,align='center')
            s.text(x+13,y-.6,'a' if i==7 else 'b',size=9,color=MUTED)
            s.text(x+16,y-.6,'c',size=9,color=MUTED)
            s.wire('GND',e.end,(44,y))
        s.text(x+.3,y-1.05,f'U200.{pin} / {MCU[pin][0]}',size=8,color=MUTED)
    s.wire('GND',(44,14),(44,10.5),(44,9.2));s.ground((44,9.2))
    s.box((38,8.4),(43,16.0),color=RULE,ls='--',lw=.9)
    s.rule((40.5,13.5),(40.5,12.0),color=MUTED,ls='--')
    s.text(35.5,17.5,'S307 · K2-1831SL-A4SW-01',size=11,align='center')
    s.supplier('S307',35.5,16.8,align='center')
    s.text(14,7.5,'S300–S306：TS-1101-C-W',size=10,color=MUTED,align='center')
    return s


def sheet_rgb():
    s=Sheet(6,'rgb','RGB 指示灯与 MOS 驱动','NH-B1515RGBA-GF · 共阳 VSYS · 三路独立限流 · GPIO 高电平点亮',[
        'D400：2=共阳，1=红阴极，4=绿阴极，3=蓝阴极；三个 LED 在同一封装内，不能共用限流电阻。',
        'C400 靠近 LED 的 VSYS；MOS 与限流电阻靠 LED，栅极下拉靠 MOS，复位时保持熄灭。',
        'PWM 走线和 LED 回流避开晶体/射频局部地；建议先用几百 Hz～1kHz，空闲关闭。',
        'VSYS 随 USB/电池变化，亮度并非恒流；低电量时绿/蓝会变暗，限流初值与混色需结合导光件实测。'])
    s.box((8.5,20),(40.5,25.5),color=RULE,ls='--',lw=.9)
    s.text(24.5,26,'D400 · NH-B1515RGBA-GF · 单一 RGB 封装',size=12,align='center')
    s.supplier('D400',24.5,25.15,align='center')
    s.port('VSYS',(5,24),'left');s.terminal('D400','2',(8.5,24))
    s.wire('VSYS',(5,24),(8.5,24),(10,24),(24,24),(38,24),(43.5,24))
    s.text(8.2,24.5,'2 / A',size=9,color=MUTED,align='right')
    s.cap('C400',43.5,24,3.0,side='left')
    for i,(ch,pin,x,col) in enumerate([('R','1',10,'#ae5050'),('G','4',24,'#397e61'),('B','3',38,'#4a74a0')]):
        # The shared pin 2 was registered once. These are the three internal junctions.
        led=s.d.add(elm.LED().at((x,24)).to((x,21)).color(col))
        s.terminal('D400',pin,led.end)
        s.text(x+1.35,22.6,ch,size=13,color=col)
        s.text(x+.5,20.65,f'{pin} / K',size=9,color=MUTED)
        s.wire(f'LED_{ch}_K',led.end,(x,19.3))
        e=s.two(f'R{400+i}',(x,19.3),(x,16.3))
        q=s.fet(f'Q{400+i}',(x,14.6))
        s.wire(f'LED_{ch}_D',e.end,q.drain);s.ground(q.source)
        gy=q.gate.y
        e=s.two(f'R{403+i}',(x-6.5,gy),(x-3.5,gy))
        s.port(f'LED_{ch}_PWM',e.start,'left')
        s.wire(f'LED_{ch}_G',e.end,q.gate)
        e=s.two(f'R{406+i}',(x-2.3,gy),(x-2.3,8.9),side='left');s.ground(e.end)
        s.text(x-6.8,gy-1.1,f'U200.{16+i} / P0.{13+i}',size=9,color=MUTED)
    return s


def sheet_gpio():
    s=Sheet(7,'gpio-swd','GPIO、SWD 与测试点','U200 的信号分单元 · 全部未用脚显式 NC · SWD 固定顺序',[
        'U200 在第 3/4/7 页拆分显示，合计 48 个封装引脚 + EP，仍然只有一颗 MCU。同名网络相连。',
        'C214/C215 紧贴 pin 37/38，沿用 Nordic errata 138 处理；不要混淆 GPIO P0.25/P0.26 与封装 pin 25/26。',
        'J200：1=VDD、2=GND、3=IO、4=CLK；VDD 仅供调试器电压参考，板子自行供电，不接 5V。RESET 配置 UICR.PSELRESET。',
        'SWD 短线带地参考；pin 1 用方焊盘/三角标记。测试点避开天线，不在晶体、DEC、ANT 节点增加长支路。'],height=36)
    left=[6,7,8,9,10,14,15,19,20,16,17,18]
    right=[4,21,22,24,26,25,37,38]
    pins=[(str(pin),MCU[pin][0],'L',31-i*1.1) for i,pin in enumerate(left)]
    pins += [(str(pin),MCU[pin][0],'R',31-i*1.5) for i,pin in enumerate(right)]
    p=s.ic('U200',(7,17.5),(19,32.3),pins,title='U200 · GPIO',subtitle='nRF52832-QFAA')
    for pin in left:s.port(PARTS['U200']['pins'][str(pin)],p[str(pin)],'left')
    for pin in right:s.port(PARTS['U200']['pins'][str(pin)],p[str(pin)],'right')
    nc=[5,11,12,23,27,28,29,39,40,41,42,43]
    pins=[]
    for i,pin in enumerate(nc):
        pins.append((str(pin),MCU[pin][0].split(' / ')[0],'T' if i<6 else 'B',3.5+(i%6)*3.5))
    p=s.ic('U200',(2,8.2),(23,14.0),pins,title='U200 · UNUSED',subtitle='NFC 脚保持默认；其余未用 GPIO 输入断开、无上下拉')
    for point in p.values():s.nc(point)
    p=s.ic('J200',(35,25.5),(44,32.7),[
        ('1','VDD / VTREF','L',31.5),('2','GND','L',29.9),('3','IO','L',28.3),('4','CLK','L',26.7)],subtitle='1 × 4 / 2.54 mm')
    for pin,point in p.items():
        if pin=='2':s.ground(point)
        else:s.port(PARTS['J200']['pins'][pin],point,'left')
    s.section(28,24,'复位上拉与 errata 138 电容')
    e=s.two('R200',(29,22.3),(29,19.3));s.port('VDD',e.start,'up');s.port('RESET_N',e.end,'left')
    for ref,net,x in [('C214','P025_FILTER',36),('C215','P026_FILTER',43)]:
        s.port(net,(x,22.3),'up');s.cap(ref,x,22.3,3)
    s.section(28,17.4,'可接触测试焊盘')
    for i in range(8):
        x=29 if i<4 else 39
        y=15.6-(i%4)*2.25
        s.testpoint(f'TP{200+i}',(x,y))
    return s


def audit_geometry():
    errors=[]
    expected={f'{r}.{p}' for r,d in PARTS.items() for p in d['pins']}
    if expected!=set(DRAWN):errors.append(f'Terminal coverage missing={expected-set(DRAWN)}, extra={set(DRAWN)-expected}')
    for s in SHEETS:
        assert {t['ref'] for t in s.terminals} == {l['ref'] for l in s.supplier_labels}, f'Sheet {s.number}: missing supplier annotations'
        segs=[LineString([w['a'],w['b']]) for w in s.wires]
        for i,(w,seg) in enumerate(zip(s.wires,segs)):
            for w2,seg2 in zip(s.wires[i+1:],segs[i+1:]):
                if w['net']!=w2['net'] and seg.intersects(seg2):
                    errors.append(f'Sheet {s.number}: crossing {w["net"]}/{w2["net"]} at {seg.intersection(seg2)}')
        for t in s.terminals:
            p=Point(t['p']);label=f'{t["ref"]}.{t["pin"]}'
            nets={w['net'] for w,seg in zip(s.wires,segs) if seg.distance(p)<1e-6}
            nets|={port['net'] for port in s.ports if Point(port['p']).distance(p)<1e-6}
            if t['net'] is None:
                if nets:errors.append(f'{label}: NC touches {nets}')
                if not any(Point(n).distance(p)<1e-6 for n in s.ncs):errors.append(f'{label}: missing NC cross')
            elif nets != {t['net']}:
                errors.append(f'{label}: drawn on {nets}, expected {t["net"]}, point={t["p"]}')
        # Each independent drawn wire island must be named/grounded, or connect
        # multiple physical terminals. This catches dangling routes and net labels.
        for net in {w['net'] for w in s.wires}:
            indices=[i for i,w in enumerate(s.wires) if w['net']==net]
            while indices:
                island={indices.pop()}
                changed=True
                while changed:
                    changed=False
                    for i in indices[:]:
                        if any(segs[i].distance(segs[j])<1e-6 for j in island):
                            island.add(i);indices.remove(i);changed=True
                ts=[t for t in s.terminals if t['net']==net and any(segs[i].distance(Point(t['p']))<1e-6 for i in island)]
                ps=[p for p in s.ports if p['net']==net and any(segs[i].distance(Point(p['p']))<1e-6 for i in island)]
                if not ps and len(ts)<2:errors.append(f'Sheet {s.number}: unnamed dangling {net} island')
    report=dict(sheets=len(SHEETS),components=len(PARTS),physical_terminals=len(DRAWN),
                fitted_units=sum(p['fitted'] for p in PARTS.values()),errors=errors)
    (OUT/'schematic-checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    if errors:raise ValueError('\n'.join(errors))
    return report


def main():
    ASSETS.mkdir(parents=True,exist_ok=True)
    for build in [sheet_usb,sheet_power,sheet_mcu_power,sheet_clock_rf,sheet_keys,sheet_rgb,sheet_gpio]:
        s=build();s.finish()
    report=audit_geometry()
    manifest=dict(version='0.1',tool=f'Schemdraw {schemdraw.__version__}',
        source_sha256={f:hashlib.sha256((OUT/f).read_bytes()).hexdigest() for f in ['原理图-v0.1.md','BOM-v0.1.md']},
        parts=PARTS,drawn_terminals=DRAWN,sheets=[dict(number=s.number,slug=s.slug,title=s.title,file=s.file,notes=s.notes,
                                                  supplier_labels=s.supplier_labels) for s in SHEETS])
    (OUT/'schematic-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    ref_sheets={ref:sorted({t['sheet']-1 for t in DRAWN.values() if t['ref']==ref})
                for ref in PARTS if not PARTS[ref].get('external')}
    nav=''.join(f'<a href="#sheet-{s.number}"><span>{s.number:02d}</span>{html.escape(s.title)}</a>' for s in SHEETS)
    options=''.join(f'<option value="{s.number-1}">{s.number:02d} / {html.escape(s.title)}</option>' for s in SHEETS)
    drawings=''.join(f'<section class="sheet" id="sheet-{s.number}" aria-label="{html.escape(s.title)}">'+
                     (ASSETS/s.file).read_text()+'</section>' for s in SHEETS)
    template=(ROOT/'scripts/schematic_viewer.html').read_text()
    for key,value in dict(NAV=nav,OPTIONS=options,DRAWINGS=drawings,
                          REFS=''.join(f'<option value="{r}"></option>' for r in ref_sheets),
                          SHEETS=json.dumps(manifest['sheets'],ensure_ascii=False),
                          REF_SHEETS=json.dumps(ref_sheets)).items():
        template=template.replace('{{'+key+'}}',value)
    (OUT/'schematic-drawing-v0.1.html').write_text(template)
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()
