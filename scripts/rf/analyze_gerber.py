"""Compare Gerber FDTD runs and synthesize two ideal 50-ohm L-network orientations."""
from pathlib import Path
import json,re,zipfile,hashlib
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'output/rf'
RUNS=['gerber-bare','gerber-fine','gerber-finer','gerber-low-loss','gerber-housed','gerber-dk43']
def gamma(z):return (z-50)/(z+50)
def element(kind,val,f):
    w=2*np.pi*f
    return 0j*w if kind=='short' else 1j*w*val if kind=='L' else 1/(1j*w*val)
def network(z,f,s,p,orientation):
    ys=0j*f if p[0]=='open' else 1/element(*p,f)
    zs=element(*s,f)
    return zs+1/(1/z+ys) if orientation=='shunt_at_load' else 1/(1/(zs+z)+ys)
def label(part):
    k,v=part
    return k if k in ('short','open') else f'{v/(1e-12 if k=="C" else 1e-9):g} '+('pF' if k=='C' else 'nH')
def candidates(z,f):
    cs=[.2,.3,.4,.5,.6,.7,.8,.9,1,1.1,1.2,1.3,1.5,1.6,1.8,2,2.2,2.4,2.7,3,3.3,3.6,3.9,4.3,4.7,5.1,5.6,6.2,6.8,7.5,8.2,9.1,10]
    ls=[.5,.8,1,1.2,1.5,1.8,2.2,2.7,3.3,3.9,4.3,4.7,5.6,6.8,8.2,10,12,15,18,22]
    elems=[('C',v*1e-12) for v in cs]+[('L',v*1e-9) for v in ls]
    answers=[]
    for orientation in ['shunt_at_load','shunt_at_input']:
        best=None
        for s in [('short',0),*elems]:
            for p in [('open',0),*elems]:
                db=float(max(20*np.log10(abs(gamma(network(z,f,s,p,orientation))))))
                rank=(db,int(s[0]!='short')+int(p[0]!='open'))
                if best is None or rank<best[0]:best=(rank,s,p)
        _,s,p=best;answers.append({'orientation':orientation,'series':s,'shunt':p,'series_label':label(s),'shunt_label':label(p),'worst_s11_db':best[0][0]})
    return sorted(answers,key=lambda x:x['worst_s11_db'])
def main():
    runs={name:np.loadtxt(OUT/(name+'.csv'),delimiter=',',skiprows=1) for name in RUNS}
    result={'status':'Gerber-based preliminary EM, not measured','material':json.loads((ROOT/'reference/rf/materials-20260924.json').read_text()),'runs':{},'mesh_comparisons':{}}
    # Independent circuit identities verify the two orientations and source/load ordering.
    f=np.array([2.45e9]);z=np.array([50+20j]);c=1/(2*np.pi*f[0]*20)
    for orientation in ['shunt_at_load','shunt_at_input']:
        assert abs(network(z,f,('C',c),('open',0),orientation)[0]-50)<1e-10
    # Known L-network transformations verify the shunt placement independently.
    w=2*np.pi*f[0]
    assert abs(network(np.array([25+0j]),f,('L',25/w),('C',.02/w),'shunt_at_input')[0]-50)<1e-10
    assert abs(network(np.array([100+0j]),f,('C',1/(50*w)),('L',100/w),'shunt_at_load')[0]-50)<1e-10
    for name,d in runs.items():
        f=d[:,0];z=d[:,1]+1j*d[:,2];mask=(f>=2402e6)&(f<=2480e6)
        assert d.shape==(501,6) and np.all(np.isfinite(d)) and np.all(z.real>0)
        assert np.array_equal(f,np.linspace(2.2e9,2.7e9,501))
        assert np.allclose(gamma(z),d[:,3]+1j*d[:,4],atol=1e-8)
        sp=np.loadtxt(OUT/(name+'.s1p'),comments=('!','#'));assert np.allclose(sp[:,1:],d[:,3:5],atol=1e-9)
        meta=json.loads((OUT/(name+'.json')).read_text());log=(ROOT/f'tmp/rf-{name}.log').read_text()
        assert meta['geometry_sha256']==hashlib.sha256((ROOT/'reference/rf/gerber-20260924.json').read_bytes()).hexdigest()
        stop=re.search(r'end-criteria of -40.00dB reached after (\d+) timesteps \(([-\d.]+)dB\)',log)
        rt=re.search(r'Time for (\d+) iterations with ([\d.]+) cells : ([\d.]+) sec',log)
        assert stop and rt, name+' did not reach time-domain criterion'
        meta['termination']={'timesteps':int(stop[1]),'energy_db':float(stop[2]),'cells':int(float(rt[2])),'iteration_seconds':float(rt[3]),'unused_primitive_warnings':log.count('Unused primitive')}
        (OUT/(name+'.json')).write_text(json.dumps(meta,indent=2)+'\n')
        result['runs'][name]={'z2441':[float(z[241].real),float(z[241].imag)],'worst_s11_db':float(max(20*np.log10(abs(gamma(z[mask]))))),'candidates':candidates(z[mask],f[mask]),'termination':meta['termination']}
    for a,b in [('gerber-bare','gerber-fine'),('gerber-fine','gerber-finer')]:
        if a in runs and b in runs:
            za=runs[a][:,1]+1j*runs[a][:,2];zb=runs[b][:,1]+1j*runs[b][:,2]
            result['mesh_comparisons'][a+'_vs_'+b]={'max_abs_z_delta_ohm':float(max(abs(za[mask]-zb[mask]))),'relative_z_delta_2441':float(abs(za[241]-zb[241])/abs(zb[241])),'max_abs_gamma_delta':float(max(abs(gamma(za[mask])-gamma(zb[mask]))))}
    base='gerber-finer' if 'gerber-finer' in runs else 'gerber-fine';choice=result['runs'][base]['candidates'][0]
    result['selected_bare_candidate']={'selected_against':base,**choice,'reference_plane':'L220 antenna-side pad; ideal network added at this reference, not a replacement for chip-side L220/C216'}
    fig,axes=plt.subplots(2,1,figsize=(10,8),layout='constrained')
    colors=['#94a99f','#71998a','#205c48','#ad783f','#835992','#6283aa']
    titles=['Bare / 0.20 mm','Bare / 0.15 mm','Bare / 0.10 mm','Df = 0.013 / 0.15 mm','Shell + battery / 0.15 mm','Dk = 4.3 / 0.15 mm']
    styles=[':', '--', '-', '-.', '-', '-']
    for (name,d),color in zip(runs.items(),colors):
        f=d[:,0];z=d[:,1]+1j*d[:,2]
        matched=network(z,f,choice['series'],choice['shunt'],choice['orientation'])
        result['runs'][name]['with_selected_bare_match_worst_s11_db']=float(max(20*np.log10(abs(gamma(matched[mask])))))
        ix=RUNS.index(name)
        axes[0].plot(f/1e9,20*np.log10(abs(gamma(z))),label=titles[ix],color=color,linestyle=styles[ix])
        axes[1].plot(f/1e9,20*np.log10(abs(gamma(matched))),label=titles[ix],color=color,linestyle=styles[ix])
    for ax in axes:
        ax.axvspan(2.402,2.480,color='#9dab8d',alpha=.15);ax.set(xlim=(2.35,2.55),xlabel='Frequency / GHz',ylabel='S11 / dB');ax.grid(alpha=.2);ax.legend(fontsize=8,loc='lower right')
    axes[0].set_ylim(-6,0);axes[1].set_ylim(-20,0)
    axes[0].set_title('Final Gerber / 1.6 mm / unpopulated PCB / L220 output port')
    axes[1].set_title('Same ideal match: series '+choice['series_label']+'; input shunt '+choice['shunt_label'])
    fig.savefig(OUT/'gerber-comparison.png',dpi=160)
    (OUT/'gerber-matching.json').write_text(json.dumps(result,indent=2)+'\n')
    with zipfile.ZipFile(OUT/'gerber-solver-evidence.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
        for name in runs:
            archive.writestr(name+'/solver.log',(ROOT/f'tmp/rf-{name}.log').read_text().replace(str(ROOT),'<REPOSITORY>'))
            archive.write(OUT/(name+'.json'),name+'/metadata.json')
            for fn in ['port_ut_1','port_it_1']:archive.write(ROOT/'tmp/rf'/name/fn,name+'/'+fn)
        archive.writestr('README.txt','Actual Gerber-based openEMS solver logs and port data. 1.6 mm, JLCPCB nominal dielectric baseline. See report for assumptions. All data are simulation, not physical measurement.\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
