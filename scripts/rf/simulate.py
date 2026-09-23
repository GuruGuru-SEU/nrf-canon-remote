"""openEMS preliminary one-port model. See output/rf/README.md for limits and reference plane."""
from pathlib import Path
import argparse,json,time
import numpy as np
from CSXCAD import ContinuousStructure
from openEMS import openEMS
from openEMS.physical_constants import EPS0
ROOT=Path(__file__).resolve().parents[2]
ap=argparse.ArgumentParser();ap.add_argument('--name',default='nominal');ap.add_argument('--mesh',type=float,default=.2);ap.add_argument('--eps',type=float,default=4.3);ap.add_argument('--thickness',type=float,default=1.0);ap.add_argument('--shell-eps',type=float,default=0);ap.add_argument('--post',action='store_true');a=ap.parse_args()
g=json.loads((ROOT/'reference/rf/pcb-20260923.json').read_text());run=ROOT/'tmp/rf'/a.name;run.mkdir(parents=True,exist_ok=True)
out=ROOT/'output/rf';out.mkdir(exist_ok=True)
h=a.thickness-.055 # Copper-sheet centre separation, after 2x10 um mask + 35 um copper allowance.
fdtd=openEMS(NrTS=120000,EndCriteria=1e-4);fdtd.SetGaussExcite(2.45e9,.8e9);fdtd.SetBoundaryCond(['PML_8']*6)
csx=ContinuousStructure();fdtd.SetCSX(csx);grid=csx.GetGrid();grid.SetDeltaUnit(1e-3)
fr4=csx.AddMaterial('FR4_assumed',epsilon=a.eps,kappa=2*np.pi*2.45e9*EPS0*a.eps*.02)
air=csx.AddMaterial('air_cutouts',epsilon=1)
ground=csx.AddMetal('GND');antenna=csx.AddMetal('IFA_and_feed')

def poly(prop,ring,z,priority):
    prop.AddPolygon(points=np.asarray(ring[:-1]).T,norm_dir='z',elevation=z,priority=priority)
for p in g['board']:
    fr4.AddLinPoly(points=np.asarray(p['outer'][:-1]).T,norm_dir='z',elevation=0,length=h,priority=0)
    for hole in p['holes']:air.AddLinPoly(points=np.asarray(hole[:-1]).T,norm_dir='z',elevation=-.02,length=h+.04,priority=5)
for layer,z in [('1',h),('2',0)]:
    for p in g['ground'][layer]:
        poly(ground,p['outer'],z,10)
        for hole in p['holes']:poly(air,hole,z,11)
for p in g['antenna_and_feed']:
    poly(antenna,p['outer'],0,30)
    for hole in p['holes']:poly(air,hole,0,31)
for x,y,r in g['ground_vias']:
    ground.AddCylinder(start=[x,y,0],stop=[x,y,h],radius=r,priority=12)
if a.shell_eps:
    shell=csx.AddMaterial('enclosure_assumed',epsilon=a.shell_eps,kappa=2*np.pi*2.45e9*EPS0*a.shell_eps*.01)
    # Imported mechanical meshes are in mm. Translate actual PCB bottom to RF z=0.
    for name in ['shell_top','shell_bottom']:
        reader=shell.AddPolyhedronReader(str(ROOT/'output/models'/f'{name}.stl'),priority=2)
        reader.ReadFile();reader.AddTransform('Translate',[0,0,8.45])
    batt=csx.AddMetal('floating_battery_envelope')
    batt.AddBox(start=[-12.75,-18,-6.95],stop=[12.75,18,-2.65],priority=15)
# Uniform fine mesh aligned to the port in RF region. Coarser graded cells elsewhere.
px,py=g['port_xy'];res=a.mesh
xcore=px+np.arange(np.floor((-8-px)/res),np.ceil((11-px)/res)+1)*res
ycore=py+np.arange(np.floor((26-py)/res),np.ceil((37-py)/res)+1)*res
# Fine region merges to board cells without very small sliver cells.
def coarse(lo,hi,left,right,step):
    return np.r_[np.arange(lo,left-step/2,step),np.arange(right+step,hi,step)]
grid.AddLine('x',np.r_[xcore,coarse(-20,20,xcore[0],xcore[-1],.7),-70,70])
grid.AddLine('y',np.r_[ycore,np.arange(-40,ycore[0]-.7,.7),-90,90])
grid.AddLine('z',np.r_[np.linspace(0,h,6),-55,55,(-8 if a.shell_eps else -1.5),(8 if a.shell_eps else 2.5)])
grid.SmoothMeshLines('all',2.5,1.3)
# Vertical 50-ohm test port from top-layer ground to the bottom RF pad, not the nRF ANT pin.
port=fdtd.AddLumpedPort(1,50,start=[px,py,h],stop=[px,py,0],p_dir='z',excite=1,priority=50)
lines={axis:grid.GetLines(axis) for axis in 'xyz'}
meta={'name':a.name,'engine':'openEMS 0.37.0 / CSXCAD 0.7.0','eps_r':a.eps,'tan_delta':.02,'nominal_board_thickness_mm':a.thickness,'copper_plane_separation_mm':h,'mesh_fine_mm':res,'shell_eps':a.shell_eps,'mesh_cells':[len(x)-1 for x in lines.values()],'minimum_step_mm':{k:float(np.min(np.diff(v))) for k,v in lines.items()},'source':g['source'],'reference_plane':g['reference_plane'],'port_start':[px,py,h],'port_stop':[px,py,0]}
csx.Write2XML(str(run/'model.xml'))
(run/'metadata.json').write_text(json.dumps(meta,indent=2)+'\n')
print(json.dumps(meta,indent=2),flush=True)
if not a.post:
    started=time.monotonic();fdtd.Run(str(run),cleanup=False,verbose=0,numThreads=8);meta['runtime_seconds']=time.monotonic()-started
f=np.linspace(2.2e9,2.7e9,501);port.CalcPort(str(run),f)
s11=port.uf_ref/port.uf_inc;zin=port.uf_tot/port.if_tot
assert np.all(np.isfinite(zin)) and np.all(np.real(zin)>0),'Invalid passive impedance'
np.savetxt(out/(a.name+'.csv'),np.c_[f,zin.real,zin.imag,s11.real,s11.imag,20*np.log10(np.abs(s11))],delimiter=',',header='frequency_hz,z_real_ohm,z_imag_ohm,s11_real,s11_imag,s11_db',comments='')
with (out/(a.name+'.s1p')).open('w') as file:
    file.write('! PRELIMINARY bare PCB unless shell_eps > 0; see README.md\n! '+g['reference_plane']+'\n# Hz S RI R 50\n')
    np.savetxt(file,np.c_[f,s11.real,s11.imag],fmt='%.10g')
for mhz in [2402,2441,2480]:
    i=np.argmin(abs(f-mhz*1e6));print(mhz,'MHz',zin[i],20*np.log10(abs(s11[i])),flush=True)
meta['samples']=[{'mhz':mhz,'z_real':float(zin[int(mhz-2200)].real),'z_imag':float(zin[int(mhz-2200)].imag),'s11_db':float(20*np.log10(abs(s11[int(mhz-2200)])))} for mhz in [2402,2441,2480]]
(out/(a.name+'.json')).write_text(json.dumps(meta,indent=2)+'\n')
