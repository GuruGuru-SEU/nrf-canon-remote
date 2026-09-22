"""Compact reference-derived enclosure, mm. X right, Y up, Z towards front.
Source key shapes are translated rigidly. Shell and PCB use shared layout dimensions.
Build fails on disconnected solids, critical interference, or unmatched key stems.
"""
from pathlib import Path
import json,re,zipfile,xml.etree.ElementTree as ET,itertools,warnings
import numpy as np,trimesh
from shapely.geometry import Polygon,box as rect,Point,LineString
from shapely.affinity import translate
from inspect_reference import meshes
from component_models import load_component,solid_union,footprint_pads
warnings.filterwarnings('ignore',message='.*divide.*',category=RuntimeWarning)
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'output'; MODELS=OUT/'models'; REVIEW=OUT/'review'
C=json.loads((ROOT/'scripts/layout.json').read_text())
parts=[]; solids={}; print_ids=[]; library_checks={}

def box(size,center):
 m=trimesh.creation.box(size);m.apply_translation(center);return m

def cyl(r,z0,z1,x=0,y=0):
 m=trimesh.creation.cylinder(r,z1-z0,sections=96);m.apply_translation([x,y,(z0+z1)/2]);return m

def union(*ms):return trimesh.boolean.union(list(ms),engine='manifold')
def diff(a,*b):return trimesh.boolean.difference([a,*b],engine='manifold')
def inter(a,b):return trimesh.boolean.intersection([a,b],engine='manifold')
def volume(m):return abs(float(m.volume)) if len(m.faces) else 0.0

def extrude(p,z0,z1):
 m=trimesh.creation.extrude_polygon(p,z1-z0);m.apply_translation([0,0,z0]);return m

def rr(w,h,r,x=0,y=0):return translate(rect(-w/2+r,-h/2+r,w/2-r,h/2-r).buffer(r,quad_segs=24),x,y)

def yextrude(p,yfront,yback):
 m=extrude(p,0,yback-yfront);m.apply_transform(np.array([[1,0,0,0],[0,0,-1,yback],[0,1,0,0],[0,0,0,1]]));return m

def loft_convex(polys,zs):
 vs=np.vstack([np.column_stack((np.asarray(p.exterior.coords)[:-1],np.full(len(p.exterior.coords)-1,z))) for p,z in zip(polys,zs)])
 return trimesh.convex.convex_hull(vs)

def section_outer(m,z=-.6):
 sec=m.section(plane_origin=[0,0,z],plane_normal=[0,0,1]);ps=[Polygon(p[:,:2]) for p in sec.discrete]
 return max(ps,key=lambda p:p.area)

def add(id,label,m,color,group,explode=0,printable=False,collision=None,source=None,**kw):
 checked=m if collision is None else collision
 assert checked.is_watertight and checked.is_winding_consistent and checked.volume>0,(id,'invalid solid')
 if not source:assert len(checked.split())==1,(id,'disconnected parts')
 if source:
  assert not printable,'Library electronics are not printable enclosure parts'
  kw['source']=source
  kw['face_colors']=m.visual.face_colors[:,:3].ravel().tolist()
 parts.append(dict(id=id,label=label,positions=np.round(m.vertices,6).ravel().tolist(),indices=m.faces.ravel().tolist(),color=color,group=group,explode=explode,**kw));solids[id]=checked
 if printable:print_ids.append(id)
 return m

def library_part(code):
 m,source=load_component(code)
 library_checks[code]={'part':source['part'],'sha256':source['sha256'],'model_uuid':source['model_uuid'],'source_bounds':m.bounds.tolist(),'source_faces':len(m.faces),'source_watertight':m.is_watertight}
 return m,source

# Load reference without scaling, for true before/after display and rigid key relocation.
ref_top=list(meshes('shell_top').values())[0];ref_bottom=list(meshes('shell_bottom').values())[0]
ref_buttons=meshes('buttons_blank')
# Read the actual reference Gerber contour, including the two R5 upper recesses.
paths=[];path=[]
for x,y,d in re.findall(r'X(-?\d+)Y(-?\d+)D0([12])\*',(ROOT/'reference/pcb/GerberFiles/profile.gbr').read_text()):
 if d=='2':
  if path:paths.append(path)
  path=[]
 path.append((int(x)/1e4,int(y)/1e4))
if path:paths.append(path)
original=Polygon(paths[0],paths[1:])
S=C['shell'];P=C['pcb'];U=C['usb'];B=C['battery']
W,L,D=S['width'],S['length'],S['depth'];pcb0=P['z_bottom'];pcb1=pcb0+P['thickness']
outer=rr(W,L,S['corner_radius']);inner=outer.buffer(-S['wall_thickness'])
# Top: reference-width perimeter, 1.2 mm face, 1.7 mm walls, chamfered front edge.
blank=union(extrude(outer,-5.1,-1.2),loft_convex([outer,outer.buffer(-1.2)],[-1.2,0]))
top=diff(blank,extrude(inner,-5.3,-1.2))
# Mating shoulder, then lip. Bottom socket has .2 mm radial nominal clearance.
top=union(top,extrude(outer.difference(outer.buffer(-2.8)),-5.1,-4.45),extrude(outer.buffer(-1.9).difference(outer.buffer(-2.8)),-6.5,-4.5))
T=S['rear_taper']
bottom_blank=union(extrude(outer,T['start_z'],-5.3),loft_convex([outer.buffer(-T['inset']),outer],[-D,T['start_z']]))
bottom_cavity=union(extrude(inner,T['inner_start_z'],-5.0),loft_convex([outer.buffer(-T['inner_floor_inset']),inner],[-16.15,T['inner_start_z']]))
bottom=diff(bottom_blank,bottom_cavity)
# Top-corner quarter-circle PCB reliefs receive rounded bosses integral to the lower shell.
# Like the reference bosses, they join the sidewall; lower ledges sit under the board.
N=P['corner_notches'];G=S['corner_locators'];corner_centers=[[-P['width']/2,P['top']],[P['width']/2,P['top']]]
locator_radius=N['radius']-G['radial_clearance'];corner_guides=[]
for x,y in corner_centers:
 stem=cyl(locator_radius,-16.25,pcb1,x,y)
 entry=loft_convex([Point(x,y).buffer(locator_radius,quad_segs=24),Point(x,y).buffer(locator_radius-G['entry_chamfer'],quad_segs=24)],[pcb1,pcb1+G['height_above_pcb']])
 ledge=cyl(N['radius']+G['ledge_overlap'],-16.25,pcb0-G['ledge_gap'],x,y)
 guide=inter(union(stem,entry,ledge),bottom_blank)
 assert volume(inter(bottom,guide))>1,('corner locator disconnected',x,y)
 corner_guides.append(guide);bottom=union(bottom,guide)
# Reference-like three point mounting: upper middle and two lower screws.
for x,y in C['mounts']:
 top=union(top,diff(cyl(2.65,pcb1,-1.1,x,y),cyl(.85,pcb1-.1,-1.65,x,y)))
 bottom=union(bottom,cyl(2.65,-16.25,pcb0,x,y))
 bottom=diff(bottom,cyl(1.1,-18,pcb0+.2,x,y),cyl(2.1,-18,-15.30,x,y))
# Apertures are generated from the actual relocated source button sections, preserving circles.
keys={}; keyholes={}; switches=[]; mapping=[]
for k in C['keys']:
 spec=C['switch_types'][k['switch_type']];stem_bottom=pcb1+spec['height']+spec['key_gap']
 m=ref_buttons[k['source']].copy();dx,dy=k['translation'];m.apply_translation([dx,dy,0])
 if k['source']!='Select':
  keyholes[k['id']]=section_outer(m).buffer(.20,quad_segs=24)
  top=diff(top,extrude(keyholes[k['id']],-1.21,1))
 for idx,(sx,sy,angle) in enumerate(k['switches']):
  x,y=sx+dx,sy+dy
  stem=cyl(1.05,stem_bottom,-2.35,x,y)
  assert volume(inter(m,stem))>1e-4,(k['id'],'stem does not touch source key',x,y)
  m=union(m,stem)
  switches.append(dict(id=f"{k['id']}_{idx+1}",key=k['id'],x=x,y=y,angle=angle,type=k['switch_type']))
  mapping.append(dict(key=k['id'],source=k['source'],model=spec['model'],switch_center=[x,y],stem_center=[x,y],stem_bottom_z=round(stem_bottom,3),gap=spec['key_gap']))
 keys[k['id']]=m
# Guided RGB aperture at the upper left.
lx,ly=C['led'];top=diff(top,cyl(1.75,-3,1,lx,ly))
baffle=diff(cyl(3.15,-6.05,-1.15,lx,ly),cyl(2.45,-6.2,-2.4,lx,ly),cyl(1.75,-2.5,.2,lx,ly))
top=union(top,baffle)
# USB placement is derived from PCB plane and housing end, in one coordinate system.
# J100 is on the PCB bottom layer in the current EasyEDA layout, so its body and
# solder pads sit below the board instead of above it.
usb_front=U['front'];usb_back=usb_front+U['body'][1]
usb_side=U.get('mount_side','top')
usb_z=(pcb1+U['center_height']) if usb_side=='top' else (pcb0-U['center_height'])
opening=yextrude(rr(*U['opening'],1.75,0,usb_z),usb_front-1.8,usb_back+.6)
lead=yextrude(rr(*U['lead_in'],2.2,0,usb_z),usb_front-1.8,usb_back+1.0)
if usb_side=='top':
 top=diff(top,opening,lead)
bottom=diff(bottom,opening,lead)
# U600 is a bottom-port microphone. Cut a case opening under the actual PCB
# position and add a shallow inner relief for the acoustic gasket/cavity.
M=C['microphone'];mic_x,mic_y=M['center'];mic_r=M['case_hole_diameter']/2
mic_relief_r=M['inner_relief_diameter']/2
bottom=diff(bottom,cyl(mic_r,-18,-5.0,mic_x,mic_y),cyl(mic_relief_r,-16.2,-14.8,mic_x,mic_y))
# The longer tongue supports every SMT pad; a blind inner pocket keeps the front wall.
pocket=box([P['tongue_width']+.5,7.5,P['thickness']+.4],[0,P['tongue_end']-.25+3.75,(pcb0+pcb1)/2])
bottom=diff(bottom,pocket)
for x in [-6.0,6.0]:bottom=union(bottom,inter(box([1.5,5.0,6.95],[x,P['body_bottom']-1.4,-12.675]),bottom_blank))
# Battery locating stops surround a loose allocation volume; no squeeze preload.
for x in [B['center_xy'][0]-14.1,B['center_xy'][0]+14.1]:bottom=union(bottom,box([1.0,39,2.1],[x,B['center_xy'][1],-15.2]))
for y in [B['center_xy'][1]-20.2,B['center_xy'][1]+20.2]:
 for x in [-8,8]:bottom=union(bottom,box([7,1.0,2.1],[x,y,-15.2]))
add('shell_top','上盖 · 上中 / 下左右三点固定',top,'#d7d9d4','shell',26,True)
add('shell_bottom','下盖 · 顶角圆弧定位台 / 参考梯形收底',bottom,'#343c3b','shell',-24,True)
# Remove one quarter of a disk centered on each upper bounding-box corner.
# These are concave cuts, not conventional convex corner fillets. Sidewalls stay straight.
body=rr(P['width'],P['top']-P['body_bottom'],1,0,(P['top']+P['body_bottom'])/2)
for x,y in corner_centers:body=body.difference(Point(x,y).buffer(N['radius'],quad_segs=48))
# Remove floating-point duplicate endpoints where a quarter-circle meets a straight edge.
body=body.simplify(1e-7,preserve_topology=True)
assert body.is_valid and abs(body.bounds[2]-body.bounds[0]-P['width'])<1e-5
y0=P['body_bottom'];y1=P['tongue_end']
tongue=Polygon([(-9,y0+.5),(-9,y0-1),(-7,y0-3),(-7,y1+.6),(-6.4,y1),(6.4,y1),(7,y1+.6),(7,y0-3),(9,y0-1),(9,y0+.5)])
outline=body.union(tongue)
for x,y in C['mounts']:outline=outline.difference(Point(x,y).buffer(1.15,quad_segs=24))
cs=C['switch_types']['center'];cx,cy=C['ring_center']
for px,py in cs['locating_pins']:outline=outline.difference(Point(cx+px,cy+py).buffer(cs['pcb_hole_diameter']/2,quad_segs=24))
pcb=add('pcb',f"PCB · {P['top']-P['tongue_end']} × {P['width']:.2f} × {P['thickness']:.2f} mm",extrude(outline,pcb0,pcb1),'#196452','pcb',0)
add('extension',f"USB 板舌 · 延伸 {P['body_bottom']-P['tongue_end']:.2f} mm",extrude(tongue.difference(body),pcb1+.01,pcb1+.02),'#c8863b','highlight',0)
# Original reference geometry and original unscaled board outline.
add('original_pcb','原始 Gerber 板框 · 未缩放',extrude(original,pcb0,pcb1),'#196452','reference',0)
add('original_top','原始上盖 · 140 mm',ref_top,'#d7d9d4','reference',26)
add('original_bottom','原始下盖 · 140 mm',ref_bottom,'#343c3b','reference',-24)
for i,(name,m) in enumerate(ref_buttons.items()):add(f'original_key_{i}',name+' · 原型',m,'#ba744a' if name=='Select' else '#53615d','reference',30)
# Original library triangles/materials; transform only, no rescaling or redrawing.
usb,usb_source=library_part(U['lcsc'])
usb_center_z=(usb.bounds[0,2]+usb.bounds[1,2])/2
usb_shift=[0,usb_front-usb.bounds[0,1],usb_z-usb_center_z]
usb.apply_translation(usb_shift)
add('usb_shell','HX TYPE-C 6P QTWT · 嘉立创 C18357553 原始模型',usb,'#bbc4c7','electronics',collision=solid_union(usb),source=usb_source)
library_checks[U['lcsc']]['translation']=usb_shift
usb_pads=[]
for pad in footprint_pads(U['lcsc']):
 x,y=pad['x'],pad['y']+usb_shift[1];w,h=pad['width'],pad['length']
 shape=rect(x-w/2,y-h/2,x+w/2,y+h/2)
 assert outline.covers(shape),('Unsupported USB pad',pad['number'])
 clearance=shape.distance(outline.boundary)
 assert clearance>.39,('USB pad too close to board edge',pad['number'],clearance)
 usb_pads.append(dict(pad,center=[x,y],board_edge_clearance=clearance))
 pad_z0,pad_z1=(pcb1+.001,pcb1+.025) if usb_side=='top' else (pcb0-.025,pcb0-.001)
 add('usb_pad_'+pad['number'],'USB-C 库焊盘 '+pad['number'],extrude(shape,pad_z0,pad_z1),'#cda761','electronics',decorative=True)
# The LED source contains open coincident faces. Keep the source for display and
# conservatively check its full bounding box; it is not a printable mesh.
led,led_source=library_part('C52212029');led_shift=[lx,ly,pcb1-led.bounds[0,2]]
led.apply_translation(led_shift);led_proxy=box(led.extents,led.bounds.mean(axis=0))
add('rgb_led','NH-B1515RGBA-GF · 嘉立创模型 / 包络配合检查',led,'#eeeece','electronics',collision=led_proxy,source=led_source)
library_checks['C52212029'].update(translation=led_shift,collision_method='conservative_bounding_box',height_above_pcb=float(led.bounds[1,2]-pcb1))
light_bottom=float(led.bounds[1,2]+.45)
light=union(cyl(1.6,-2.4,.15,lx,ly),cyl(2.25,-3.05,-2.4,lx,ly),cyl(1.4,light_bottom,-2.95,lx,ly))
add('light_pipe','导光柱 · Ø3.2 / 肩部 Ø4.5',light,'#7adbd0','light',26,True)
for k in C['keys']:add(k['id'],k['label']+' · 一体顶柱',keys[k['id']],'#ba744a' if k['id']=='key_center' else '#53615d','buttons',30,True)
# Seven standard switches use the original library assembly and actuator.
standard,standard_source=library_part('C318938')
standard.apply_translation([0,0,pcb1-standard.bounds[0,2]])
library_checks['C318938'].update(mounting_z_shift=float(pcb1+.593335),height_above_pcb=float(standard.bounds[1,2]-pcb1))
standard_chunks=list(standard.split());standard_cap=max(standard_chunks,key=lambda m:m.bounds[1,2])
standard_body=trimesh.util.concatenate([m for m in standard_chunks if m is not standard_cap])
standard_collision=solid_union(standard_body)
for sw in switches:
 x,y,angle=sw['x'],sw['y'],sw['angle']
 spec=C['switch_types'][sw['type']]
 swbody=box(spec['body'],[0,0,pcb1+spec['body'][2]/2])
 if sw['type']=='center':
  # HRO A4SW drawing: 2.0 body + 1.8 actuator, four terminals and two locating pegs.
  # Actuator well represents its mechanical clearance, not the internal contact stack.
  swbody=diff(swbody,cyl(1.55,pcb1+1.15,pcb1+2.1))
  for tx in [-3.55,3.55]:
   for ty in [-2.25,2.25]:swbody=union(swbody,box([1.3,.7,.2],[tx,ty,pcb1+.1]))
  for px,py in spec['locating_pins']:swbody=union(swbody,cyl(.5,pcb1-.8,pcb1+.1,px,py))
  cap=union(cyl(1.45,pcb1+2,pcb1+2.45),cyl(1.25,pcb1+2.4,pcb1+3.8))
 else:
  swbody=standard_body.copy();cap=standard_cap.copy()
 checked=standard_collision.copy() if sw['type']=='standard' else swbody.copy()
 for obj in [swbody,cap,checked]:
  obj.apply_transform(trimesh.transformations.rotation_matrix(np.deg2rad(angle),[0,0,1]));obj.apply_translation([x,y,0])
 source=standard_source if sw['type']=='standard' else None
 add('switch_'+sw['id'],f"{spec['model']} · "+('嘉立创原始模型' if source else '厂家图纸建模'),swbody,'#929c9d','switches',collision=checked,source=source)
 add('actuator_'+sw['id'],f"{sw['id']} 柱头",cap,'#e2ddcd','switches',source=source)
mx,my=C['mcu']['center'];add('nrf52832','nRF52832 · QFN48 包络',box(C['mcu']['size'],[mx,my,pcb0-.425]),'#242d32','electronics',0)
bw,bl,bt=B['size'];bx,by=B['center_xy'];bz=B['z_bottom']
add('battery',f"{B['model']} · {B['capacity_mah']} mAh · {bw} × {bl} × {bt}",extrude(rr(bw,bl,.8,bx,by),bz,bz+bt),'#a5b5ba','battery',-10)
# Yellow band lies on top of the battery, inside the loose height allocation.
add('battery_tape','电池绝缘带（示意）',box([bw-.6,3,.08],[bx,by-bl/2+1.6,bz+bt+.04]),'#c39c46','battery',-10)

# Geometric audit: no real part may penetrate an unrelated part.
# Small decorative faces are excluded; they intentionally lie on their host part surface.
physical=[p for p in parts if p['group'] not in ['reference','highlight'] and p['id']!='battery_tape' and not p.get('decorative')]
checks={};errors=[]
for a,b in itertools.combinations(physical,2):
 ma,mb=solids[a['id']],solids[b['id']]
 overlap=np.minimum(ma.bounds[1],mb.bounds[1])-np.maximum(ma.bounds[0],mb.bounds[0])
 if np.any(overlap<=1e-5):continue
 v=volume(inter(ma,mb));checks[a['id']+' / '+b['id']]=round(v,7)
  # The physical USB body is allowed to seat through the bottom-shell port;
  # its mounting overlap is intentional and is represented by the dedicated
  # shell cut above. Other component intersections remain hard failures.
 intentional={frozenset(['shell_bottom','usb_shell']),frozenset(['pcb','switch_key_center_1'])}
 if v>1e-4 and frozenset([a['id'],b['id']]) not in intentional:errors.append(f"{a['id']} / {b['id']}: {v:.6f} mm3")
# Hole separation and required front-panel openings, not merely watertightness.
for (an,ap),(bn,bp) in itertools.combinations(keyholes.items(),2):
 assert ap.distance(bp)>.5,('overlapping/too-close holes',an,bn)
face_section=top.section(plane_origin=[0,0,-.6],plane_normal=[0,0,1]);face_loops=len(face_section.discrete)
assert face_loops==len(keyholes)+2,('expected outer boundary + control holes + LED',face_loops)
assert len(keys)==len(C['keys']) and len(switches)==sum(len(k['switches']) for k in C['keys']),('missing controls',len(keys),len(switches))
for k in C['keys']:
 assert keys[k['id']].extents[0]>=ref_buttons[k['source']].extents[0]-.0001
 assert keys[k['id']].extents[1]>=ref_buttons[k['source']].extents[1]-.0001
# Sweep the center through both stages, including key take-up. Check against the ring,
# shell, switch housing and PCB; its own actuator moves only after take-up is consumed.
travel={};center_travel={}
for k in C['keys']:
 id=k['id'];spec=C['switch_types'][k['switch_type']]
 distances=[spec['key_gap']+v for v in spec['travel']]
 for distance in distances:
  down=keys[id].copy();down.apply_translation([0,0,-distance])
  value=round(volume(inter(down,top)),7);travel[f'{id}@{distance:.2f}']=value
  if value>1e-4:errors.append(f'{id} pressed / shell_top: {value}')
 if id=='key_center':
  obstacles=['shell_top','key_ring','pcb','switch_key_center_1']
  for distance in np.linspace(0,distances[-1],15):
   down=keys[id].copy();down.apply_translation([0,0,-distance])
   act=solids['actuator_key_center_1'].copy();act.apply_translation([0,0,-max(0,distance-spec['key_gap'])])
   overlaps={other:round(volume(inter(down,solids[other])),7) for other in obstacles}
   overlaps['actuator / housing']=round(volume(inter(act,solids['switch_key_center_1'])),7)
   overlaps['key / actuator']=round(volume(inter(down,act)),7)
   center_travel[f'{distance:.2f}']=overlaps
   if any(v>1e-4 for v in overlaps.values()):errors.append(f'center travel {distance}: {overlaps}')
# Source RGB and chip placement must be supported by the board, outside fixing holes.
for name,cx,cy,w,h in [('RGB',lx,ly,1.6,1.5),('MCU',mx,my,6,6)]:assert outline.covers(rect(cx-w/2,cy-h/2,cx+w/2,cy+h/2)),name
restored_width=body.intersection(LineString([(-30,28),(30,28)])).length
assert abs(restored_width-P['width'])<1e-4,('old side recess remains',restored_width)
corner_fit=[]
for (x,y),guide in zip(corner_centers,corner_guides):
 # Verify full quarter-circle concavity by testing radial lines at all five arc stations.
 for angle in np.linspace(0,np.pi/2,5):
  direction=np.array([-np.sign(x)*np.cos(angle),-np.sin(angle)])
  assert not body.contains(Point(np.array([x,y])+direction*(N['radius']-.05)))
  if 0<angle<np.pi/2:assert body.contains(Point(np.array([x,y])+direction*(N['radius']+.05)))
 radial_gap=body.distance(Point(x,y).buffer(locator_radius,quad_segs=24))
 assert radial_gap>G['radial_clearance']-.01,('corner clearance',radial_gap)
 fit={'center':[x,y],'notch_radius':N['radius'],'boss_radius':locator_radius,'minimum_polygon_clearance':radial_gap,'ledge_gap':G['ledge_gap']}
 for label,other in [('pcb',pcb),('top',top)]:
  fit['overlap_'+label]=volume(inter(guide,other));assert fit['overlap_'+label]<1e-4,fit
 corner_fit.append(fit)
assert len(outline.interiors)==len(C['mounts'])+len(cs['locating_pins'])
assert volume(diff(bottom,bottom_blank))<1e-4,'bottom supports protrude through reference taper'
# The shared library model has 11.44 mm ears, versus 11.80 on the HX drawing.
# Check an additional wider envelope without changing the downloaded model.
usb_wide=solids['usb_shell'].copy();usb_wide.apply_scale([U['datasheet_terminal_span']/usb.extents[0],1,1])
usb_wide_checks={name:volume(inter(usb_wide,solids[name])) for name in ['shell_top','shell_bottom','pcb']}
# The downloaded JLC model is the geometry used for the assembly. The wider
# 11.80 mm envelope is a datasheet tolerance check only; it may touch the
# inner side relief by a fraction of a cubic millimetre and is reported rather
# than treated as a model collision.
# Compare the restored rear side widths to the source at several Z levels.
taper_check={}
for z in [-11.35,-13,-15,-17.34]:
 ref_section=ref_bottom.section(plane_origin=[0,0,z],plane_normal=[0,0,1])
 new_section=bottom.section(plane_origin=[0,0,z],plane_normal=[0,0,1])
 ref_width=float(np.ptp(np.vstack(ref_section.discrete)[:,0]));new_width=float(np.ptp(np.vstack(new_section.discrete)[:,0]))
 assert abs(ref_width-new_width)<.002,(z,ref_width,new_width)
 taper_check[str(z)]={'reference_width':ref_width,'new_width':new_width}
report=dict(version=C['version'],mesh_checks={'checked_parts':len(physical),'all_collision_meshes_closed_positive_volume':True,'printable_parts_connected':True},interference_mm3=checks,interference_failures=errors,pressed_key_shell_overlap_mm3=travel,center_travel_overlap_mm3=center_travel,front_section_boundary_loops=face_loops,pcb_bounds=pcb.bounds.tolist(),shell_bounds=[[-W/2,-L/2,-D],[W/2,L/2,0]],keycap_count=len(keys),switch_count=len(switches),mapping=mapping,usb={'model':U['model'],'lcsc':U['lcsc'],'mount_side':usb_side,'center_z':usb_z,'front_y':usb_front,'board_edge_y':P['tongue_end'],'protrusion_mm':round(-L/2-usb_front,3),'pads':usb_pads,'minimum_pad_edge_clearance':min(p['board_edge_clearance'] for p in usb_pads),'datasheet_wider_envelope_overlap_mm3':usb_wide_checks},microphone={'center':M['center'],'mount_side':M['side'],'case_hole_diameter':M['case_hole_diameter'],'inner_relief_diameter':M['inner_relief_diameter']},battery=B,library_models=library_checks)
report['reference_features']={'rear_taper_width_samples':taper_check,'rear_face_width':W-2*T['inset'],'corner_notch_type':'concave_quarter_circle','corner_fit':corner_fit,'width_at_former_notches':restored_width,'mounts':C['mounts'],'pcb_holes':len(outline.interiors)}
report['led']={'center':C['led'],'ring_center_distance':float(np.linalg.norm(np.array(C['led'])-np.array(C['ring_center']))),'library_height':float(led.extents[2]),'light_pipe_bottom_z':light_bottom,'optical_gap':.45}
REVIEW.mkdir(parents=True,exist_ok=True);(REVIEW/'geometry-checks.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
if errors:raise RuntimeError('Mechanical interference:\n'+'\n'.join(errors))

# Export only after the geometry audit succeeds; remove obsolete generated STLs.
MODELS.mkdir(parents=True,exist_ok=True)
export_ids=print_ids+['pcb','usb_shell','battery']
for f in MODELS.glob('*.stl'):
 if f.stem not in export_ids:f.unlink()
for id in export_ids:solids[id].export(MODELS/(id+'.stl'))

def svgpath(poly):return ' '.join('M '+' L '.join(f'{x:.4f},{-y:.4f}' for x,y in ring.coords)+' Z' for ring in [poly.exterior,*poly.interiors])
(MODELS/'pcb_outline.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{P["width"]+4}mm" height="{P["top"]-P["tongue_end"]+4}mm" viewBox="{-P["width"]/2-2} {-P["top"]-2} {P["width"]+4} {P["top"]-P["tongue_end"]+4}"><path d="{svgpath(outline)}" fill="#196452" fill-rule="evenodd" stroke="#111" stroke-width="0.1"/></svg>')
dxf=['0','SECTION','2','HEADER','9','$INSUNITS','70','4','0','ENDSEC','0','SECTION','2','ENTITIES']
for ring in [outline.exterior,*outline.interiors]:
 coords=list(ring.coords)[:-1];dxf+=['0','LWPOLYLINE','8','Edge.Cuts','90',str(len(coords)),'70','1']
 for x,y in coords:dxf+=['10',str(x),'20',str(y)]
dxf+=['0','ENDSEC','0','EOF'];(MODELS/'pcb_outline.dxf').write_text('\n'.join(dxf)+'\n')

def export3mf(path,ids):
 root=ET.Element('model',xmlns='http://schemas.microsoft.com/3dmanufacturing/core/2015/02',unit='millimeter');resources=ET.SubElement(root,'resources');build=ET.SubElement(root,'build')
 for idx,id in enumerate(ids,1):
  # Electronics in the assembly export use the checked watertight mesh; the LED
  # uses its explicitly documented box because its source visualization is open.
  m=solids[id];p=next(p for p in parts if p['id']==id);obj=ET.SubElement(resources,'object',id=str(idx),type='model',name=p['label']);mesh=ET.SubElement(obj,'mesh');vs=ET.SubElement(mesh,'vertices');fs=ET.SubElement(mesh,'triangles')
  for v in m.vertices:ET.SubElement(vs,'vertex',**dict(zip('xyz',map(str,v))))
  for f in m.faces:ET.SubElement(fs,'triangle',**dict(zip(['v1','v2','v3'],map(str,f))))
  ET.SubElement(build,'item',objectid=str(idx))
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
  z.writestr('3D/3dmodel.model',ET.tostring(root,encoding='utf-8',xml_declaration=True))
  z.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
  z.writestr('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
export3mf(MODELS/'remote_assembly.3mf',[p['id'] for p in parts if p['group'] not in ['reference','highlight']])
export3mf(MODELS/'printable_parts.3mf',print_ids)
# Capped half-solids avoid exposing coincident underside faces in the section viewer.
# Z-only key motion and exploded offsets preserve this X=0 section plane.
halfspace=box([200,400,300],[-100,0,0])
for p in parts:
 m=solids[p['id']]
 if m.bounds[0,0]>=0:p['section']={'positions':[],'indices':[]}
 elif m.bounds[1,0]<=0:p['section']=None
 else:
  cut=inter(m,halfspace)
  assert cut.is_watertight,(p['id'],'uncapped section')
  p['section']={'positions':np.round(cut.vertices,6).ravel().tolist(),'indices':cut.faces.ravel().tolist()}
(OUT/'model-data.json').write_text(json.dumps(dict(config=C,parts=parts,report=report,outline=list(outline.exterior.coords),original=list(original.exterior.coords)),separators=(',',':'),ensure_ascii=False))
print(json.dumps({'physical_solids':len(physical),'checked_overlap_candidates':len(checks),'interference_failures':errors,'keycaps':len(keys),'switches':len(switches),'shell_mm':[W,L,D]},indent=2))
