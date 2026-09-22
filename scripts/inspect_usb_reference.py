from pathlib import Path
import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from inspect_reference import meshes

output = Path('output/review')
original = {name: next(iter(meshes(name).values())) for name in ('shell_top', 'shell_bottom')}
figure, axes = plt.subplots(2, 4, figsize=(18, 7))
for row, (name, mesh) in enumerate(original.items()):
    for axis, position in zip(axes[row], (-60, -62, -65, -69)):
        section = mesh.section(plane_origin=[0, position, 0], plane_normal=[0, 1, 0])
        if section:
            for path in section.discrete:
                axis.plot(path[:, 0], path[:, 2], linewidth=1)
        axis.set(xlim=(-22, 22), ylim=(-18, 1), title=f'{name}, Y={position} mm', xlabel='X / mm', ylabel='Z / mm')
        axis.set_aspect('equal')
        axis.grid()
figure.tight_layout()
figure.savefig(output / 'reference-usb-sections.png', dpi=160)
plt.close(figure)
figure = plt.figure(figsize=(15, 8))
for index, (name, mesh) in enumerate(original.items(), 1):
    axis = figure.add_subplot(1, 2, index, projection='3d')
    cropped = mesh.slice_plane([0, -56, 0], [0, -1, 0])
    collection = Poly3DCollection(cropped.triangles, facecolor='#bccfc9', edgecolor='#3d655d', linewidth=.12, alpha=1)
    axis.add_collection3d(collection)
    axis.set(xlim=(-22, 22), ylim=(-71, -56), zlim=(-18, 1), title=name, xlabel='X', ylabel='Y', zlabel='Z')
    axis.set_box_aspect([44, 15, 19])
    axis.view_init(elev=-35 if name == 'shell_top' else 35, azim=70)
figure.tight_layout()
figure.savefig(output / 'reference-usb-structures.png', dpi=180)
plt.close(figure)
current = {name: trimesh.load_mesh(f'output/models/{name}.stl') for name in ('shell_top', 'shell_bottom', 'pcb', 'usb_shell')}
figure, axes = plt.subplots(1, 3, figsize=(16, 5))
colors = {'shell_top': '#6b9290', 'shell_bottom': '#364f44', 'pcb': '#00a572', 'usb_shell': '#b76d38'}
for axis, group, position, title in [(axes[0], original, -62, 'Reference end latches'), (axes[1], current, -31, 'Adapted end latches'), (axes[2], current, -35.8, 'Bottom-mounted USB-C')]:
    for name, mesh in group.items():
        section = mesh.section(plane_origin=[0, position, 0], plane_normal=[0, 1, 0])
        for index, path in enumerate(section.discrete if section else []):
            axis.plot(path[:, 0], path[:, 2], color=colors[name], linewidth=1.3, label=name if index == 0 else None)
    axis.set(xlim=(-22, 22), ylim=(-18, 1), title=f'{title}\nY={position} mm', xlabel='X / mm', ylabel='Z / mm')
    axis.set_aspect('equal')
    axis.grid(alpha=.3)
    axis.legend(fontsize=8)
figure.tight_layout()
figure.savefig(output / 'usb-fit-sections.png', dpi=180)
plt.close(figure)
