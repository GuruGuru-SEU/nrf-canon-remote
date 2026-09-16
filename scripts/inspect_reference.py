from pathlib import Path
import zipfile,xml.etree.ElementTree as E
import trimesh,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
NS={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
def meshes(name):
 with zipfile.ZipFile(Path('reference/enclosure')/(name+'.3mf')) as z:r=E.fromstring(z.read('3D/3dmodel.model'))
 out={}
 for o in r.findall('.//m:object',NS):
  v=np.array([[float(e.get(a)) for a in ('x','y','z')] for e in o.findall('.//m:vertex',NS)])
  f=np.array([[int(e.get(a)) for a in ('v1','v2','v3')] for e in o.findall('.//m:triangle',NS)])
  v=np.column_stack((-v[:,0],v[:,2],v[:,1]))
  out[o.get('name')]=trimesh.Trimesh(v,f,process=True)
 return out
if __name__=='__main__':
 fig,axs=plt.subplots(2,5,figsize=(18,10))
 for row,name in enumerate(('shell_top','shell_bottom')):
  m=list(meshes(name).values())[0]
  print(name,m.bounds,m.is_watertight,m.volume)
  for ax,z in zip(axs[row],[-1,-2.4,-5,-8,-12]):
   s=m.section(plane_origin=[0,0,z],plane_normal=[0,0,1])
   if s:
    for p in s.discrete:ax.plot(p[:,0],p[:,1],lw=.7)
   ax.set_aspect('equal');ax.set_title(name+' z='+str(z));ax.set_xlim(-23,23);ax.set_ylim(-72,72);ax.grid()
 fig.tight_layout();fig.savefig('output/review/reference-sections.png',dpi=150)
 for name,m in meshes('buttons_blank').items():print(name,m.bounds.tolist(),m.is_watertight)
