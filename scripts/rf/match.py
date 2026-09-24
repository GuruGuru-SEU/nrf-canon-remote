"""Ideal 50-ohm L-network synthesis at the exported one-port reference plane."""
from pathlib import Path
import json
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'output/rf'

def network(z,f,series,shunt):
    w=2*np.pi*f
    def impedance(c):
        kind,value=c
        return 0*w if kind=='short' else 1j*w*value if kind=='L' else 1/(1j*w*value)
    y=0*w if shunt[0]=='open' else 1/impedance(shunt)
    return impedance(series)+1/(1/z+y)

def reflection(z):return (z-50)/(z+50)

def select(z,f):
    caps=np.array([.2,.3,.4,.5,.6,.7,.8,.9,1,1.2,1.5,1.8,2.2,2.7,3.3,3.9,4.7,5.6,6.8,8.2,10])*1e-12
    inds=np.array([.5,.8,1,1.2,1.5,1.8,2.2,2.7,3.3,3.9,4.3,4.7,5.6,6.8,8.2,10,12,15,18,22])*1e-9
    elems=[('C',float(v)) for v in caps]+[('L',float(v)) for v in inds]
    best=None
    for s in [('short',0),*elems]:
        for h in [('open',0),*elems]:
            gamma=reflection(network(z,f,s,h));score=float(np.max(abs(gamma)))
            # Prefer fewer parts when worst-case performance is effectively identical.
            rank=(score, int(s[0]!='short')+int(h[0]!='open'))
            if best is None or rank<best[0]:best=(rank,s,h)
    return best[1:]

def label(c):
    kind,value=c
    return kind if kind in ['open','short'] else f'{value/(1e-12 if kind=="C" else 1e-9):g} '+('pF' if kind=='C' else 'nH')

# Verify circuit equations against cases with known exact solutions.
f=np.array([2.45e9]);assert abs(reflection(network(np.array([50+0j]),f,('short',0),('open',0)))[0])<1e-12
assert abs(network(np.array([50+20j]),f,('C',1/(2*np.pi*f[0]*20)),('open',0))[0]-50)<1e-10
assert select(np.array([50+0j]),f)==(('short',0),('open',0))

runnames=['nominal-16','housed-16']
runs={name:np.loadtxt(OUT/(name+'.csv'),delimiter=',',skiprows=1) for name in runnames if (OUT/(name+'.csv')).exists()}
base='nominal-16' if 'nominal-16' in runs else ('refined' if 'refined' in runs else 'nominal');d=runs[base];f=d[:,0];band=(f>=2402e6)&(f<=2480e6);z=d[:,1]+1j*d[:,2];series,shunt=select(z[band],f[band]);chosen={'series':{'type':series[0],'value_si':series[1],'label':label(series)},'shunt_at_load':{'type':shunt[0],'value_si':shunt[1],'label':label(shunt)},'reference_plane':'L220 output pad, ideal additional 50-ohm L-network; not replacement of Nordic chip network','selected_against':base,'qualification':'ideal candidate only, not a production BOM'}
summary={'candidate':chosen,'runs':{}}
fig,axs=plt.subplots(2,1,figsize=(10,8),layout='constrained');colors=['#445d52','#976a9b','#b06038','#597fa0','#8b6f47','#6e6e6e']
for (name,data),color in zip(runs.items(),colors):
    f=data[:,0];z=data[:,1]+1j*data[:,2];matched=network(z,f,series,shunt);mask=(f>=2402e6)&(f<=2480e6)
    summary['runs'][name]={'unmatched_worst_s11_db':float(np.max(20*np.log10(abs(reflection(z[mask]))))),'matched_worst_s11_db':float(np.max(20*np.log10(abs(reflection(matched[mask]))))),'z_2441_ohm':[float(data[241,1]),float(data[241,2])]}
    axs[0].plot(f/1e9,20*np.log10(abs(reflection(z))),label=name+' / no added match',color=color)
    axs[1].plot(f/1e9,20*np.log10(abs(reflection(matched))),label=name+' / same ideal match',color=color)
for ax in axs:
    ax.axvspan(2.402,2.480,color='#81926d',alpha=.13);ax.set(xlim=(2.3,2.6),ylim=(-35,0),xlabel='Frequency / GHz',ylabel='S11 / dB');ax.grid(alpha=.2);ax.legend(fontsize=9)
axs[0].set_title('Preliminary openEMS: IFA + feed, 50 ohm port at L220 output')
axs[1].set_title('Ideal candidate: series '+label(series)+'; shunt '+label(shunt)+' at load')
fig.savefig(OUT/'comparison.png',dpi=160)
if 'housed-16' in runs:
    hd=runs['housed-16'];hf=hd[:,0];hz=hd[:,1]+1j*hd[:,2];hb=(hf>=2402e6)&(hf<=2480e6)
    hs,hh=select(hz[hb],hf[hb]);hm=network(hz,hf,hs,hh)
    summary['hypothetical_housed_candidate']={
        'series':{'type':hs[0],'value_si':hs[1],'label':label(hs)},
        'shunt_at_load':{'type':hh[0],'value_si':hh[1],'label':label(hh)},
        'matched_worst_s11_db':float(np.max(20*np.log10(abs(reflection(hm[hb]))))),
        'qualification':'sensitivity study only; assumed enclosure dielectric, coarse mesh, no parasitic models'
    }
    fig2,ax=plt.subplots(figsize=(10,4.5),layout='constrained')
    ax.plot(hf/1e9,20*np.log10(abs(reflection(hz))),label='Housed / no added match',color='#976a9b')
    ax.plot(hf/1e9,20*np.log10(abs(reflection(network(hz,hf,series,shunt)))),label='Housed / bare-PCB candidate',color='#b06038',linestyle='--')
    ax.plot(hf/1e9,20*np.log10(abs(reflection(hm))),label='Housed / own ideal candidate',color='#445d52')
    ax.axvspan(2.402,2.480,color='#81926d',alpha=.13)
    ax.set(xlim=(2.3,2.6),ylim=(-35,0),xlabel='Frequency / GHz',ylabel='S11 / dB',title='Assumed housing + battery: series '+label(hs)+'; shunt '+label(hh))
    ax.grid(alpha=.2);ax.legend(fontsize=9);fig2.savefig(OUT/'housed-comparison.png',dpi=160)
if 'refined' in runs:
    zn=runs['nominal'][:,1]+1j*runs['nominal'][:,2];zr=runs['refined'][:,1]+1j*runs['refined'][:,2]
    summary['mesh_comparison']={'max_abs_z_delta_ohm_in_band':float(np.max(abs(zn[band]-zr[band]))),'max_abs_gamma_delta_in_band':float(np.max(abs(reflection(zn[band])-reflection(zr[band])))),'relative_z_delta_at_2441':float(abs(zn[241]-zr[241])/abs(zr[241]))}
(OUT/'matching.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
