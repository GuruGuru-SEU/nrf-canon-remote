"""Manufacturing Gerber/Excellon -> mm geometry for openEMS. No old footprint copper used."""
from pathlib import Path
import json,hashlib,zipfile,warnings
import numpy as np
from shapely.geometry import Polygon,Point,LineString,box
from shapely.ops import unary_union,polygonize
from shapely import make_valid
from gerbonara.rs274x import GerberFile
from gerbonara.excellon import ExcellonFile
from gerbonara import graphic_primitives as gp
from gerbonara.utils import MM,approximate_arc
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch
from matplotlib.path import Path as MPath
ROOT=Path(__file__).resolve().parents[2]
ZIP=ROOT/'Gerber_nRF52832遥控器_2026-09-24.zip'
DEST=ROOT/'tmp/gerber-20260924';OUT=ROOT/'output/rf';DEST.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(ZIP) as z:
    for entry in z.infolist():
        assert not Path(entry.filename).is_absolute() and '..' not in Path(entry.filename).parts
        z.extract(entry,DEST)

def polys(g):
    if g.geom_type=='Polygon':return [g]
    return [p for c in getattr(g,'geoms',[]) for p in polys(c)]

def shape(p):
    if isinstance(p,gp.Circle):return Point(p.x,p.y).buffer(p.r,quad_segs=32)
    if isinstance(p,gp.Line):return LineString([(p.x1,p.y1),(p.x2,p.y2)]).buffer(p.width/2,quad_segs=16)
    if isinstance(p,gp.Arc):
        if p.is_circle:
            r=np.hypot(p.x1-p.cx,p.y1-p.cy)
            return Point(p.cx,p.cy).buffer(r+p.width/2,quad_segs=64).difference(Point(p.cx,p.cy).buffer(max(0,r-p.width/2),quad_segs=64))
        points=list(approximate_arc(p.cx,p.cy,p.x1,p.y1,p.x2,p.y2,p.clockwise,max_error=.001))
        return LineString(points).buffer(p.width/2,quad_segs=16)
    a=p.to_arc_poly().approximate_arcs(max_error=.001)
    return make_valid(Polygon(a.outline))

def read_artwork(name):
    f=GerberFile.open(DEST/name);result=Polygon();batch=[];count=0
    for obj in f.objects:
        for p in obj.to_primitives(unit=MM):
            s=shape(p);count+=1
            if p.polarity_dark:batch.append(s)
            else:
                result=unary_union([result,*batch]).difference(s);batch=[]
    result=unary_union([result,*batch]);assert result.is_valid
    print(name,len(f.objects),'objects,',count,'primitives, area',result.area,flush=True)
    return result
outline=GerberFile.open(DEST/'Gerber_BoardOutlineLayer.GKO')
lines=[]
for o in outline.objects:
    assert type(o).__name__=='Line','Review unsupported outline primitive'
    lines.append(LineString([(o.x1,o.y1),(o.x2,o.y2)]))
board=max(polygonize(unary_union(lines)),key=lambda p:p.area)
assert np.allclose(board.bounds,[-18.3787,-37.55,18.3787,35.8787],atol=.001)
npth=[];pth=[]
with warnings.catch_warnings():
    warnings.simplefilter('ignore',SyntaxWarning)
    for name,dest in [('Drill_NPTH_Through.DRL',npth),('Drill_PTH_Through.DRL',pth)]:
        for obj in ExcellonFile.open(DEST/name).objects:
            p=list(obj.to_primitives(unit=MM));assert len(p)==1 and isinstance(p[0],gp.Circle)
            c=p[0];dest.append([c.x,c.y,c.r])
for x,y,r in npth:board=board.difference(Point(x,y).buffer(r,quad_segs=32))
assert len(npth)==6 and len(pth)==101
copper={str(k):read_artwork(name).intersection(board).simplify(.001,preserve_topology=True) for k,name in [(1,'Gerber_TopLayer.GTL'),(2,'Gerber_BottomLayer.GBL')]}
mask_openings={str(k):read_artwork(name).intersection(board) for k,name in [(1,'Gerber_TopSolderMaskLayer.GTS'),(2,'Gerber_BottomSolderMaskLayer.GBS')]}
flying=json.loads((DEST/'FlyingProbeTesting.json').read_text());assert flying['lengthUnit']=='mil'
pins={row[1]:dict(zip(flying['pins']['fields'],row)) for row in flying['pins']['rows']}
def xy(pin):return [pin['PIN_X']*.0254,pin['PIN_Y']*.0254]
port=xy(pins['L220_2']);assert pins['L220_2']['NET_NAME']=='$1N324'
assert copper['2'].covers(Point(*port)) and copper['1'].covers(Point(*port))
rf_poly=next(q for q in polys(copper['2']) if q.covers(Point(*port)))
assert rf_poly.covers(Point(*xy(pins['ANT1_FEED'])))
assert rf_poly.covers(Point(*xy(pins['ANT1_GND']))) # IFA DC short is intentional.
assert not rf_poly.covers(Point(*xy(pins['L220_1']))) # Series part is omitted.
npth_mounts=sorted([p for p in npth if abs(p[2]-1.15)<1e-6]);assert np.allclose(npth_mounts,[[-14,-27,1.15],[14,-27,1.15],[14,28,1.15]])
old=json.loads((ROOT/'reference/rf/pcb-20260923.json').read_text())
def decode(items):return unary_union([Polygon(x['outer'],x['holes']) for x in items])
roi=box(-8,30.6,11,36)
old_rf=decode(old['antenna_and_feed']).intersection(roi);new_rf=copper['2'].intersection(roi)
comparison={'antenna_region_y_gt_30_6_symmetric_difference_mm2':old_rf.symmetric_difference(new_rf).area,'old_antenna_region_area_mm2':old_rf.area,'gerber_antenna_region_area_mm2':new_rf.area}

def encode(g):return [{'outer':list(p.exterior.coords),'holes':[list(r.coords) for r in p.interiors]} for p in polys(g)]
data={'source':{'kind':'manufacturing Gerber + Excellon + FlyingProbeTesting','zip_sha256':hashlib.sha256(ZIP.read_bytes()).hexdigest(),'exported_at':'2026-09-24 14:07:48','files_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(DEST.iterdir()) if p.is_file()},'antenna_source':'Gerber_BottomLayer.GBL; no previous footprint used'},'board':encode(board),'copper':{k:encode(v) for k,v in copper.items()},'mask_openings':{k:encode(v) for k,v in mask_openings.items()},'plated_drills':pth,'nonplated_drills':npth,'port_xy':port,'assumptions':{'thickness_mm':1.6,'thickness_source':'user confirmed','eps_r':4.5,'tan_delta':.02,'components':'unpopulated; no chip impedance or component load models','conductor':'PEC sheets; plated through holes approximated as solid posts of drill radius + 25 um','solder_mask':'openings extracted for audit; dielectric omitted in solver'},'reference_plane':'L220 output ($1N324); all Gerber copper, components omitted (C216/L220/C217 not populated)','comparison_with_previous_snapshot':comparison}
(ROOT/'reference/rf/gerber-20260924.json').write_text(json.dumps(data,separators=(',',':'))+'\n')
fig,axs=plt.subplots(1,2,figsize=(11,7),layout='constrained')
def draw(ax,g,color):
    from shapely.geometry.polygon import orient
    for q in polys(g):
        q=orient(q,sign=1);vs=[];codes=[]
        for ring in [q.exterior,*q.interiors]:
            vs.extend(ring.coords);codes.extend([MPath.MOVETO]+[MPath.LINETO]*(len(ring.coords)-2)+[MPath.CLOSEPOLY])
        ax.add_patch(PathPatch(MPath(vs,codes),facecolor=color,edgecolor='none'))
for ax in axs:
    draw(ax,board,'#e7ddd0');draw(ax,copper['1'],'#cad6dc');draw(ax,copper['2'],'#557d6e')
    for x,y,r in pth:draw(ax,Point(x,y).buffer(r),'#f6f3ec')
    ax.plot(*port,'o',color='#be5935',ms=5);ax.set_aspect('equal');ax.set_xlabel('X / mm');ax.set_ylabel('Y / mm');ax.grid(alpha=.15)
axs[0].set(xlim=(-22,22),ylim=(-40,39),title='Final manufacturing Gerber: all copper + drills')
axs[1].set(xlim=(-9,11),ylim=(24,37),title='Actual IFA and feed / L220 output test port')
fig.savefig(OUT/'gerber-geometry.png',dpi=160)
(OUT/'gerber-audit.json').write_text(json.dumps({'zip_sha256':data['source']['zip_sha256'],'outline_bounds_mm':board.bounds,'npth_count':len(npth),'pth_count':len(pth),'mounts':npth_mounts,'port_xy':port,'port_both_copper_layers':True,'ifa_feed_ground_connected':True,'chip_side_isolated':True,'copper_area_mm2':{k:g.area for k,g in copper.items()},'comparison':comparison},indent=2)+'\n')
print(json.dumps(comparison),flush=True)
