"""Read exported meshes back and check units, topology, bounds and PCB contours."""
from pathlib import Path
import json
import zipfile
import xml.etree.ElementTree as ET
import numpy as np
import trimesh

root = Path(__file__).resolve().parent.parent
data = json.loads((root / 'output/model-data.json').read_text())
parts = {p['id']: p for p in data['parts']}
models = root / 'output/models'
printable = ['shell_top', 'shell_bottom', 'light_pipe', 'key_ring', 'key_center',
             'key_circle1', 'key_circle2', 'key_circle3']
report = {'version': data['config']['version'], 'stl': {}}


def verify(mesh, part):
    assert mesh.is_volume, part['id']
    expected = np.asarray(part['positions']).reshape(-1, 3)
    assert np.allclose(mesh.bounds, [expected.min(0), expected.max(0)], atol=2e-5), part['id']
    connected = len(mesh.split()) == 1
    if part['id'] in printable:
        assert connected, part['id']
    return {'closed_positive_volume': True, 'connected': connected, 'bounds_match': True}


for path in models.glob('*.stl'):
    report['stl'][path.name] = verify(trimesh.load_mesh(path), parts[path.stem])
assert len(report['stl']) == len(printable) + 3

ns = {'m': 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
for filename, ids in [
    ('printable_parts.3mf', printable),
    ('remote_assembly.3mf', [p['id'] for p in data['parts'] if p['group'] not in ['reference', 'highlight']]),
]:
    with zipfile.ZipFile(models / filename) as archive:
        doc = ET.fromstring(archive.read('3D/3dmodel.model'))
    assert doc.attrib['unit'] == 'millimeter'
    objects = doc.findall('m:resources/m:object', ns)
    assert len(objects) == len(ids)
    for obj, id in zip(objects, ids):
        vertices = [[float(v.get(a)) for a in ('x', 'y', 'z')] for v in obj.findall('.//m:vertex', ns)]
        faces = [[int(f.get(a)) for a in ('v1', 'v2', 'v3')] for f in obj.findall('.//m:triangle', ns)]
        verify(trimesh.Trimesh(vertices, faces), parts[id])
    report[filename] = {'objects': len(objects), 'unit': 'mm', 'roundtrip_valid': True}

svg = ET.parse(models / 'pcb_outline.svg').getroot()
path = svg.find('{http://www.w3.org/2000/svg}path').get('d')
loops = path.count('M ')
assert loops == 1 + len(data['config']['mounts']) + 2
dxf = (models / 'pcb_outline.dxf').read_text()
assert dxf.count('LWPOLYLINE') == loops
report['pcb_outline'] = {'loops': loops, 'mount_holes': 3, 'switch_locating_holes': 2}
(root / 'output/review/export-checks.json').write_text(json.dumps(report, indent=2) + '\n')
print(f'PASS: {len(report["stl"])} STL files, both 3MF assemblies and {loops} PCB contours')
