"""Read the original EasyEDA OBJ dialect (inline materials), in millimetres."""
from pathlib import Path
import hashlib
import json
import numpy as np
import trimesh

DIRECTORY = Path(__file__).resolve().parent.parent / 'reference/component-models'


def load_component(code):
    path = DIRECTORY / f'{code}.obj'
    manifest = json.loads((DIRECTORY / 'sources.json').read_text())[code]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest['sha256'], code
    vertices, faces, colors = [], [], []
    palette = {}
    material = None
    for line in path.read_text().splitlines():
        words = line.split()
        if not words:
            continue
        token, values = words[0], words[1:]
        if token == 'v':
            vertices.append([float(v) for v in values])
        elif token in ('newmtl', 'usemtl'):
            material = values[0]
        elif token == 'Kd':
            palette[material] = [round(float(v) * 255) for v in values] + [255]
        elif token == 'f':
            indices = [int(v.split('/')[0]) - 1 for v in values]
            assert len(indices) == 3, 'Expected original triangulated library mesh'
            faces.append(indices)
            colors.append(palette[material])
    mesh = trimesh.Trimesh(vertices, faces, face_colors=colors, process=True)
    assert np.isfinite(mesh.vertices).all()
    return mesh, manifest


def solid_union(mesh):
    """Union a library assembly for collision checks; keep source faces for display."""
    pieces = mesh.split(only_watertight=False)
    assert all(p.is_volume for p in pieces), 'Library mesh has open/invalid solids'
    result = trimesh.boolean.union(list(pieces), engine='manifold')
    assert result.is_volume
    return result


def footprint_pads(code):
    """Return actual library SMT pads relative to its 3D origin, Y up, mm."""
    data = json.loads((DIRECTORY / f'{code}.json').read_text())['result']['packageDetail']['dataStr']
    nodes = [json.loads(s.split('~', 1)[1]) for s in data['shape'] if s.startswith('SVGNODE~')]
    ox, oy = map(float, nodes[0]['attrs']['c_origin'].split(','))
    pads = []
    for shape in data['shape']:
        if not shape.startswith('PAD~'):
            continue
        fields = shape.split('~')
        assert fields[1] == 'RECT' and fields[6] == '1' and float(fields[9]) == 0
        pads.append(dict(number=fields[8], x=(float(fields[2])-ox)*.254,
                         y=(oy-float(fields[3]))*.254,
                         width=float(fields[4])*.254, length=float(fields[5])*.254))
    return pads
