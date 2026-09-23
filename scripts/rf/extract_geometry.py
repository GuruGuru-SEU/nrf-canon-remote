"""Extract an RF study from the read-only EasyEDA snapshot (all output coordinates in mm)."""
import json, math, hashlib
from pathlib import Path
import numpy as np
from shapely.geometry import Polygon, Point, LineString, box, mapping
from shapely import make_valid
from shapely.ops import unary_union
from shapely.affinity import rotate, translate
ROOT=Path(__file__).resolve().parents[2]
p=json.loads((ROOT/'tmp/easyeda-20260923/pcb.json').read_text())
fp_path=ROOT/'tmp/easyeda-20260922/0d27b0b8c28874d1.efoo'

def path_points(a,scale=1):
    pts=[np.array(a[:2],float)];i=2;mode='L'
    while i<len(a):
        if isinstance(a[i],str):mode=a[i];i+=1
        if mode=='L':pts.append(np.array(a[i:i+2],float));i+=2
        elif mode=='ARC':
            angle=math.radians(a[i]);end=np.array(a[i+1:i+3],float);start=pts[-1];i+=3
            delta=end-start
            if np.linalg.norm(delta)<1e-8:continue
            center=(start+end)/2+np.array([-delta[1],delta[0]])/(2*math.tan(angle/2))
            vec=start-center
            for t in np.linspace(0,angle,max(3,int(abs(angle)/.05)+1))[1:]:
                pts.append(center+np.array([[math.cos(t),-math.sin(t)],[math.sin(t),math.cos(t)]])@vec)
        else:raise ValueError(mode)
    return np.asarray(pts)*scale

def polygons(g):
    if g.geom_type=='Polygon':return [g]
    if hasattr(g,'geoms'):return [x for part in g.geoms for x in polygons(part)]
    return []

def pad_shape(pad):
    x,y=pad['x']*.0254,pad['y']*.0254
    if pad['pad'][0]=='POLYGON':return Polygon(path_points(pad['pad'][1],.0254))
    kind,w,h=pad['pad'][:3];w*=.0254;h*=.0254
    if kind=='ELLIPSE':
        from shapely.affinity import scale
        shape=scale(Point(0,0).buffer(1,quad_segs=8),w/2,h/2)
    elif kind=='RECT':shape=box(-w/2,-h/2,w/2,h/2)
    else:raise ValueError(pad['pad'])
    return translate(rotate(shape,pad['rotation'],origin=(0,0)),x,y)

records=[]
for line in p['source'].splitlines():
    try:
        h,b=line.rstrip('|').split('||');records.append((json.loads(h),json.loads(b)))
    except ValueError:pass
board=Polygon(path_points(next(b['path'] for h,b in records if h['type']=='POLY'),.0254))
mounts=[]
for fill in p['fills']:
    a=fill['complexPolygon']['polygon']
    if fill['layer']==12 and a[0]=='CIRCLE':
        x,y,r=np.asarray(a[1:])*.0254;board=board.difference(Point(x,y).buffer(r));mounts.append([x,y,r])

layers={1:[],2:[]}
pour_layers={a['primitiveId']:a['layer'] for a in p['pours']}
for pour in p['poured']:
    for fill in pour['pourFills']:
        contours=fill['path']['complexPolygon'];shape=Polygon()
        if not isinstance(contours[0],list):contours=[contours]
        # Poured paths use EasyEDA internal 10 mil coordinates (unlike primitive positions).
        for contour in contours:
            points=path_points(contour,.254)
            if fill['fill']:
                shape=shape.symmetric_difference(make_valid(Polygon(points)))
            else:
                shape=shape.union(LineString(points).buffer(fill['lineWidth']*.254/2,quad_segs=4))
        layers[pour_layers[pour['pourPrimitiveId']]].append(shape)
for pad in p['pads']:
    if pad['net']=='GND' and pad['layer'] in [1,2,12]:
        for layer in ([1,2] if pad['layer']==12 else [pad['layer']]):layers[layer].append(pad_shape(pad))
for line in p['lines']:
    if line.get('net')=='GND' and line['layer'] in layers:
        layers[line['layer']].append(LineString([(line['startX']*.0254,line['startY']*.0254),(line['endX']*.0254,line['endY']*.0254)]).buffer(line['lineWidth']*.0254/2,quad_segs=4))
for fill in p['fills']:
    a=fill['complexPolygon']['polygon']
    if fill['net']=='GND' and a[0]=='R':
        _,x,y,w,h,*_=a;layers[fill['layer']].append(box(x*.0254,(y-h)*.0254,(x+w)*.0254,y*.0254))
vias=[]
for via in p['vias']:
    if via['net']=='GND':
        x,y,r=via['x']*.0254,via['y']*.0254,via['diameter']*.0254/2
        vias.append([x,y,r]);shape=Point(x,y).buffer(r,quad_segs=8)
        for layer in layers:layers[layer].append(shape)

ant=next(c for c in p['components'] if c['designator']=='ANT1')
assert ant['footprint']['uuid']=='0d27b0b8c28874d1' and ant['rotation']==180 and ant['layer']==2
fp=[json.loads(line) for line in fp_path.read_text().splitlines()]
shape=next(row[7][0] for row in fp if row[0]=='FILL')
coords=path_points(shape,.0254);coords[:,0]*=-1;coords += [ant['x']*.0254,ant['y']*.0254]
antenna=Polygon(coords)
for row in fp:
    if row[0]=='PAD':
        expected=np.array([-row[6]+ant['x'],row[7]+ant['y']])*.0254
        actual=next(x for x in p['pads'] if x['primitiveId'].startswith(ant['primitiveId']) and x['padNumber']==row[5])
        assert np.linalg.norm(expected-np.array([actual['x'],actual['y']])*.0254)<.004
        antenna=antenna.union(pad_shape(actual))
# Feed reference: output pad of L220. Remove chip-side copper and leave C217 DNP.
feed=[]
for line in p['lines']:
    if line.get('net')=='$1N324':feed.append(LineString([(line['startX']*.0254,line['startY']*.0254),(line['endX']*.0254,line['endY']*.0254)]).buffer(line['lineWidth']*.0254/2,quad_segs=8))
for pad in p['pads']:
    if pad['net']=='$1N324':feed.append(pad_shape(pad))
rf=unary_union([antenna,*feed]);ground={str(k):unary_union(v).intersection(board).simplify(.008,preserve_topology=True) for k,v in layers.items()}
port_pad=next(a for a in p['pads'] if a['primitiveId'].startswith('85b6d7a564edbb1b') and a['net']=='$1N324')
port=[port_pad['x']*.0254,port_pad['y']*.0254]
assert ground['1'].contains(Point(*port)), 'Port needs opposite ground'
assert ground['2'].distance(rf)<.001,'IFA short must join ground'
assert board.buffer(.01).covers(rf),'Antenna copper outside outline'

def encode(g):return [{'outer':list(s.exterior.coords),'holes':[list(r.coords) for r in s.interiors]} for s in polygons(g)]
data={'source':{'captured_at':p['capturedAt'],'pcb_uuid':p['doc']['uuid'],'snapshot_sha256':hashlib.sha256((ROOT/'tmp/easyeda-20260923/pcb.json').read_bytes()).hexdigest(),'antenna_footprint_uuid':ant['footprint']['uuid'],'antenna_copper_source':'2026-09-22 export of same footprint UUID; 2026-09-23 placement verified against both live pads','antenna_footprint_sha256':hashlib.sha256(fp_path.read_bytes()).hexdigest(),'status':'preliminary; footprint copper not freshly exported, fabrication Dk/Df unconfirmed'},'board':encode(board),'ground':{k:encode(v) for k,v in ground.items()},'antenna_and_feed':encode(rf),'port_xy':port,'ground_vias':vias,'mount_holes':mounts,'assumptions':{'thickness_mm':1.0,'eps_r':4.3,'tan_delta':.02,'copper':'PEC sheet','solder_mask':'omitted','other_signal_copper':'omitted','components':'omitted','enclosure_and_battery':'separate optional variant'},'reference_plane':'L220 output ($1N324), with L220 and C216 excluded and C217 DNP'}
(ROOT/'reference/rf/pcb-20260923.json').write_text(json.dumps(data,separators=(',',':'))+'\n')
# Geometry preview: top-view XY even for bottom copper, no mirrored screenshot guessing.
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch
from matplotlib.path import Path as MPath
fig,axs=plt.subplots(1,2,figsize=(11,7),layout='constrained')
def draw(ax,g,color):
    for q in polygons(g):
        from shapely.geometry.polygon import orient
        q=orient(q,sign=1);rings=[q.exterior,*q.interiors];points=[];codes=[]
        for r in rings:
            points.extend(r.coords);codes.extend([MPath.MOVETO]+[MPath.LINETO]*(len(r.coords)-2)+[MPath.CLOSEPOLY])
        ax.add_patch(PathPatch(MPath(points,codes),facecolor=color,edgecolor='none'))
for ax in axs:
    draw(ax,board,'#e7ddd0');draw(ax,ground['1'],'#cad6dc');draw(ax,ground['2'],'#6f8f84');draw(ax,rf,'#b55c35');ax.plot(*port,'ko',ms=4);ax.set_aspect('equal');ax.set_xlabel('X / mm');ax.set_ylabel('Y / mm');ax.grid(alpha=.15)
axs[0].set(xlim=(-22,22),ylim=(-40,39),title='Extracted PCB / mount holes')
axs[1].set(xlim=(-10,11),ylim=(24,37),title='IFA + feed / copper used in openEMS')
fig.savefig(ROOT/'output/rf/geometry.png',dpi=180)
print('board',board.bounds,'antenna',rf.bounds,'port',port,'ground vias',len(vias),'ground area',{k:v.area for k,v in ground.items()})
