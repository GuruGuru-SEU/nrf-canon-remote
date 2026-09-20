"""Explicit pin/net data for the v0.1 review drawings (not an EDA netlist).

Pin names for S307 follow the manufacturer's a/b/c drawing; c1/c2 are the
two physical common pads, not guessed numeric footprint pin numbers.
"""

PARTS = {}


def part(ref, value, pins, *, kind=None, fitted=True, **extra):
    assert ref not in PARTS, ref
    PARTS[ref] = dict(value=value, pins={str(k): v for k, v in pins.items()},
                      kind=kind or ref[0], fitted=fitted, **extra)


def passive(ref, value, a, b, **extra):
    part(ref, value, {1: a, 2: b}, **extra)


part('J100', 'HX TYPE-C 6P QTWT', {
    'A9': 'VBUS_5V', 'B9': 'VBUS_5V', 'A12': 'GND', 'B12': 'GND',
    'A5': 'USB_CC1', 'B5': 'USB_CC2', **{str(i): 'GND' for i in range(17, 21)}})
for i, net in enumerate(['USB_CC1', 'USB_CC2']):
    passive(f'R{100+i}', '5.1k', net, 'GND')
passive('C100', '100nF / 16V', 'VBUS_5V', 'GND')
for i, net in enumerate(['VBUS_5V', 'USB_CC1', 'USB_CC2']):
    passive(f'D{101+i}', 'PESDNC2FD5VB', net, 'GND', kind='TVS')
part('U100', 'MSTP4054-42', {1: 'CHG_N', 2: 'GND', 3: 'VBAT', 4: 'VBUS_5V', 5: 'CHG_PROG'})
passive('C101', '2.2uF / 6.3V', 'VBUS_5V', 'GND')
passive('C102', '1uF / 16V', 'VBAT', 'GND')
passive('R105', '10k', 'CHG_PROG', 'GND')
passive('R106', '10k', 'VDD', 'CHG_N')
part('J101', 'Battery wire pads', {1: 'VBAT', 2: 'GND'}, fitted=False)
part('BAT1', '1S protected LiPo / ~320mAh', {'+': 'VBAT', '-': 'GND'}, kind='battery', external=True)
part('D100', 'BAT54H / SOD123F', {2: 'VBUS_5V', 1: 'VSYS'}, kind='schottky')
part('Q100', 'AO3401A', {1: 'BAT_PATH_GATE', 2: 'VSYS', 3: 'VBAT'}, kind='PMOS')
passive('R102', '0R', 'VBUS_5V', 'BAT_PATH_GATE')
passive('R103', '10k', 'BAT_PATH_GATE', 'GND')
part('U101', 'ME6211C33M5G-N', {1: 'VSYS', 2: 'GND', 3: 'VSYS', 4: None, 5: 'VREG_3V3'})
passive('C103', '1uF / 16V', 'VSYS', 'GND')
passive('C104', '1uF / 16V', 'VREG_3V3', 'GND')
passive('R104', '0R', 'VREG_3V3', 'VDD')
part('Q101', 'SI2302', {1: 'USB_GATE', 2: 'GND', 3: 'USB_PRESENT_N'}, kind='NMOS')
passive('R107', '10k', 'VBUS_5V', 'USB_GATE')
passive('R108', '1M', 'USB_GATE', 'GND')
passive('R109', '10k', 'VDD', 'USB_PRESENT_N')
passive('R110', '1M', 'VBAT', 'VBAT_SENSE')
passive('R111', '1M', 'VBAT_SENSE', 'GND')
passive('C105', '100nF', 'VBAT_SENSE', 'GND')

MCU = {
    1: ('DEC1', 'DEC1'), 2: ('P0.00 / XL1', 'XL1'), 3: ('P0.01 / XL2', 'XL2'),
    4: ('P0.02 / AIN0', 'VBAT_SENSE'), 5: ('P0.03 / AIN1', None),
    6: ('P0.04', 'KEY_UP'), 7: ('P0.05', 'KEY_DOWN'), 8: ('P0.06', 'KEY_LEFT'),
    9: ('P0.07', 'KEY_RIGHT'), 10: ('P0.08', 'KEY_AUX1'),
    11: ('P0.09 / NFC1', None), 12: ('P0.10 / NFC2', None), 13: ('VDD', 'VDD'),
    14: ('P0.11', 'KEY_AUX2'), 15: ('P0.12', 'KEY_AUX3'),
    16: ('P0.13', 'LED_R_PWM'), 17: ('P0.14', 'LED_G_PWM'), 18: ('P0.15', 'LED_B_PWM'),
    19: ('P0.16', 'KEY_HALF'), 20: ('P0.17', 'KEY_FULL'),
    21: ('P0.18', 'CHG_N'), 22: ('P0.19', 'USB_PRESENT_N'), 23: ('P0.20', None),
    24: ('P0.21 / nRESET', 'RESET_N'), 25: ('SWDCLK', 'SWDCLK'), 26: ('SWDIO', 'SWDIO'),
    27: ('P0.22', None), 28: ('P0.23', None), 29: ('P0.24', None),
    30: ('ANT', 'RF_ANT'), 31: ('VSS', 'GND'), 32: ('DEC2', None),
    33: ('DEC3', 'DEC3'), 34: ('XC1', 'XC1'), 35: ('XC2', 'XC2'), 36: ('VDD', 'VDD'),
    37: ('P0.25', 'P025_FILTER'), 38: ('P0.26', 'P026_FILTER'),
    39: ('P0.27', None), 40: ('P0.28 / AIN4', None), 41: ('P0.29 / AIN5', None),
    42: ('P0.30 / AIN6', None), 43: ('P0.31 / AIN7', None), 44: ('NC', None),
    45: ('VSS', 'GND'), 46: ('DEC4', 'DEC4'), 47: ('DCC', 'DCC'), 48: ('VDD', 'VDD'),
    'EP': ('EP', 'GND'),
}
part('U200', 'nRF52832-QFAA', {k: v[1] for k, v in MCU.items()})
for ref, val, net in [('C200', '100nF', 'DEC1'), ('C201', '100pF / C0G', 'DEC3'),
                      ('C202', '1uF / X5R', 'DEC4'), ('C203', '100nF', 'VDD'),
                      ('C204', '100nF', 'VDD'), ('C205', '4.7uF / 10V', 'VDD'),
                      ('C206', '100nF', 'VDD'), ('C214', '12pF / C0G', 'P025_FILTER'),
                      ('C215', '12pF / C0G', 'P026_FILTER')]:
    passive(ref, val, net, 'GND')
passive('L200', '10uH', 'DCC', 'DCDC_MID')
passive('L201', '15nH', 'DCDC_MID', 'DEC4')
passive('R200', '10k', 'VDD', 'RESET_N')
part('X200', 'YE32MDBCD2X / 32MHz', {1: 'XC1', 2: 'GND', 3: 'XC2', 4: 'GND'})
part('X201', 'KFC3276812520T / 32.768kHz', {1: 'XL1', 2: 'XL2'})
# One 12 pF capacitor to ground per crystal terminal, per the user's
# development-board feedback on 2026-09-20.
for i, net in enumerate(['XC1', 'XC2', 'XL1', 'XL2'], start=210):
    passive(f'C{i}', '12pF', net, 'GND')

KEYS = [('UP', 6, '圆环上'), ('DOWN', 7, '圆环下'), ('LEFT', 8, '圆环左'),
        ('RIGHT', 9, '圆环右'), ('AUX1', 10, '下排左'), ('AUX2', 14, '下排中'),
        ('AUX3', 15, '下排右'), ('HALF', 19, '中心半按'), ('FULL', 20, '中心全按')]
for i, (name, pin, desc) in enumerate(KEYS):
    if i < 7:
        part(f'S{300+i}', 'TS-1101-C-W', {1: f'KEY_{name}', 2: 'GND'}, kind='switch')
part('S307', 'K2-1831SL-A4SW-01', {'a': 'KEY_HALF', 'b': 'KEY_FULL', 'c1': 'GND', 'c2': 'GND'}, kind='dual-switch')

part('D400', 'NH-B1515RGBA-GF', {2: 'VDD', 1: 'LED_R_K', 4: 'LED_G_K', 3: 'LED_B_K'}, kind='RGB')
passive('C400', '100nF / 16V', 'VDD', 'GND')
for i, channel in enumerate('RGB'):
    passive(f'R{400+i}', '1.2k' if i == 0 else '1k', f'LED_{channel}_K', f'LED_{channel}_PWM')

passive('C216', '0.8pF / C0G', 'RF_ANT', 'GND')
passive('L220', '3.9nH / RF', 'RF_ANT', 'RF_50')
passive('C217', 'DNP / TBD', 'RF_50', 'GND', fitted=False)
passive('R221', '0R', 'RF_50', 'ANT_FEED')
passive('C218', 'DNP / TBD', 'ANT_FEED', 'GND', fitted=False)
part('ANT200', 'KH-2012-HM1', {1: 'ANT_FEED', 2: None}, kind='antenna')
part('J200', '1x4 / 2.54mm', {1: 'VDD', 2: 'GND', 3: 'SWDIO', 4: 'SWDCLK'})
for i, net in enumerate(['VDD', 'GND', 'VBUS_5V', 'VBAT', 'VSYS', 'RESET_N', 'CHG_N', 'USB_PRESENT_N']):
    part(f'TP{200+i}', net, {1: net}, kind='testpoint', fitted=False)

# These are display-only names for otherwise unnamed local nets in the prose.
LOCAL_NETS = ['USB_GATE', 'BAT_PATH_GATE', 'CHG_PROG', 'DCDC_MID',
              'P025_FILTER', 'P026_FILTER'] + [f'LED_{c}_K' for c in 'RGB']

# Supplier identifiers are annotations only; they do not change this circuit or
# procurement status. Existing stock IDs follow BOM-v0.1.md. Four exact-MPN
# additions were verified on the supplier's own pages on 2026-09-19.
JLC_GROUPS = {
    'C18357553': ['J100'],
    'C25905': ['R100', 'R101'],
    'C60474': ['C100', 'C105', 'C200', 'C203', 'C204', 'C206', 'C400'],
    'C5356109': ['D101', 'D102', 'D103'],
    'C49208527': ['U100'],
    'C5137560': ['C101'],
    'C1592': ['C102', 'C103', 'C104', 'C202'],
    'C2906861': ['R103', 'R105', 'R106', 'R107', 'R109', 'R200'],
    'C2906858': ['R102', 'R104', 'R221'],
    'C82942': ['U101'],
    'C2891732': ['Q101'],
    'C49196763': ['R108', 'R110', 'R111'],
    'C46614473': ['C201'],
    'C46635918': ['C205'],
    'C45359894': [f'C{i}' for i in range(210, 216)],
    'C370189': ['L201'],
    'C54427949': ['X200'],
    'C18209174': ['X201'],
    'C106235': ['R401', 'R402'],
    'C318938': [f'S{i}' for i in range(300, 307)],
    'C52212029': ['D400'],
    'C2909307': ['R400'],
    'C2925419': ['ANT200'],
    'C77540': ['U200'],
    'C15127': ['Q100'],
    'C426769': ['D100'],
    'C76798': ['L200'],
}
NO_JLC = {
    'S307': 'JLC 未核实',
    'L220': 'JLC 待选型',
    'C216': 'JLC 待选型',
    'J200': 'JLC 待选型',
    'BAT1': '电池待选型',
    'C217': 'DNP / 无料号',
    'C218': 'DNP / 无料号',
    'J101': 'PCB 焊盘 / 无料号',
    **{f'TP{i}': 'PCB 焊盘 / 无料号' for i in range(200, 208)},
}
for code, refs in JLC_GROUPS.items():
    for ref in refs:
        assert 'lcsc' not in PARTS[ref], ref
        PARTS[ref].update(lcsc=code, supplier_label=f'JLC {code}')
for ref, label in NO_JLC.items():
    assert 'lcsc' not in PARTS[ref], ref
    PARTS[ref].update(lcsc=None, supplier_label=label)
assert all('lcsc' in part for part in PARTS.values())
