"""Summarize the supplied JLC laminate options and synthesize L/pi networks."""
from pathlib import Path
import hashlib,json,re,zipfile,html
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from match_networks import scan,evaluate,gamma,self_check,CAP_PF,IND_NH
ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/'output/rf'
CASES=[('np140f','NP-140F',4.1,.013),('hy8101','HY-8101',4.3,.022),('ny2140-rc55','NY2140 / RC55%',4.15,.0166),('ny2140-rc70','NY2140 / RC70%',3.7,.0178)]

def check_run(name,dk,df,state):
    d=np.loadtxt(OUT/(name+'.csv'),delimiter=',',skiprows=1)
    meta=json.loads((OUT/(name+'.json')).read_text())
    assert meta['eps_r']==dk and meta['tan_delta']==df and meta['mesh_fine_mm']==.1
    assert meta['nominal_board_thickness_mm']==1.6
    assert meta['shell_eps']==(2.8 if state=='housed' else 0)
    assert meta['geometry_sha256']==hashlib.sha256((ROOT/'reference/rf/gerber-20260924.json').read_bytes()).hexdigest()
    assert d.shape==(501,6) and np.all(np.isfinite(d)) and np.all(d[:,1]>0)
    assert np.array_equal(d[:,0],np.linspace(2.2e9,2.7e9,501))
    assert np.allclose(gamma(d[:,1]+1j*d[:,2]),d[:,3]+1j*d[:,4],atol=1e-9)
    sp=np.loadtxt(OUT/(name+'.s1p'),comments=('!','#'))
    assert np.allclose(sp[:,1:],d[:,3:5],atol=1e-9)
    log=(ROOT/f'tmp/rf-{name}.log').read_text()
    stop=re.search(r'end-criteria of -40.00dB reached after (\d+) timesteps \(([-\d.]+)dB\)',log)
    rt=re.search(r'Time for (\d+) iterations with ([\d.]+) cells : ([\d.]+) sec',log)
    assert stop and rt,name+' failed time-domain termination check'
    meta['termination']={'timesteps':int(stop[1]),'energy_db':float(stop[2]),'cells':int(float(rt[2])),'iteration_seconds':float(rt[3]),'unused_primitive_warnings':log.count('Unused primitive')}
    (OUT/(name+'.json')).write_text(json.dumps(meta,indent=2)+'\n')
    return d,meta

def draw_topologies():
    # SVG-native explanatory circuit; branch names map exactly to JSON/table order.
    parts=['<svg xmlns="http://www.w3.org/2000/svg" width="960" height="470" viewBox="0 0 960 470">',
      '<rect width="960" height="470" rx="18" fill="#f3f5ef"/>',
      '<g font-family="-apple-system,BlinkMacSystemFont,Arial,sans-serif" fill="#263e35">',
      '<text x="38" y="42" font-size="22" font-weight="600">π network / branch order: P1 → Zs → P2</text>',
      '<text x="38" y="78" font-size="17">P1 and P2: shunt to GND · Zs: series · each may be C or L</text>',
      '<text x="38" y="143" font-size="18">50 Ω input</text><text x="752" y="143" font-size="18">Antenna load</text>',
      '<text x="736" y="177" font-size="15">L220 output reference</text>',
      '<g stroke="#315e4c" stroke-width="3" fill="none">',
      '<path d="M60 170H420 M540 170H710"/>',
      '<rect x="420" y="150" width="120" height="40" rx="4"/>',
      '<path d="M250 170V210 M250 270V304 M650 170V210 M650 270V304"/>',
      '<rect x="230" y="210" width="40" height="60" rx="4"/><rect x="630" y="210" width="40" height="60" rx="4"/>',
      '<path d="M232 304H268 M238 312H262 M245 320H255 M632 304H668 M638 312H662 M645 320H655"/>',
      '</g><circle cx="250" cy="170" r="5"/><circle cx="650" cy="170" r="5"/>',
      '<text x="469" y="140" font-size="18">Zs</text><text x="283" y="248" font-size="18">P1</text><text x="683" y="248" font-size="18">P2</text>',
      '<text x="38" y="374" font-size="18">L-input: populate P1 + Zs; leave P2 open.</text>',
      '<text x="38" y="405" font-size="18">L-load: populate Zs + P2; leave P1 open.</text>',
      '<text x="38" y="438" font-size="18">Common low-pass π: P1 = C, Zs = L, P2 = C.</text>',
      '</g></svg>']
    (OUT/'matching-topologies.svg').write_text(''.join(parts))

def main():
    self_check(); out={'date':'2026-09-28','source_manifest':json.loads((ROOT/'reference/rf/materials-20260928.json').read_text()),'reference_plane':'L220 antenna-side pad, 50 ohm; not chip ANT','branch_order':['input shunt P1','series Zs','load shunt P2'],'search':{'capacitors_pf':CAP_PF,'inductors_nh':IND_NH,'frequency_hz':[2402e6,2480e6],'frequency_step_hz':1e6,'objective':'minimax absolute reflection over frequency and, for common networks, all four material cases','component_model':'ideal; no loss or SRF, not a production BOM'},'cases':{},'common':{}}
    arrays={}; metas={};mask=None
    for key,label,dk,df in CASES:
        out['cases'][key]={'label':label,'eps_r':dk,'tan_delta':df}
        for state in ['bare','housed']:
            name=key+'-'+state;d,meta=check_run(name,dk,df,state);arrays[name]=d;metas[name]=meta
            mask=(d[:,0]>=2402e6)&(d[:,0]<=2480e6);f=d[mask,0];z=d[mask,1]+1j*d[mask,2]
            out['cases'][key][state]={'z2441':[float(d[241,1]),float(d[241,2])],'raw_worst_s11_db':float(max(d[mask,5])),'networks':scan(z,f),'termination':meta['termination']}
    for state in ['bare','housed']:
        z=np.asarray([arrays[k+'-'+state][mask,1]+1j*arrays[k+'-'+state][mask,2] for k,*_ in CASES])
        out['common'][state]={'case_order':[k for k,*_ in CASES],'networks':scan(z,f)}
        # Cross-evaluate individually selected C-L-C networks on all material cases.
        cross=[]
        for key,*_ in CASES:
            candidate=out['cases'][key][state]['networks']['pi_CLC']
            values=20*np.log10(np.max(abs(gamma(evaluate(z,f,candidate['parts']))),axis=1))
            cross.append({'selected_for':key,'worst_s11_per_case_db':values.tolist()})
        out['common'][state]['individual_CLC_cross_evaluation']=cross
        # Illustrative value tolerance, not sourced component specifications.
        choice=out['common'][state]['networks']['pi_CLC']; allscores=[]
        from itertools import product
        for signs in product([-1,0,1],repeat=3):
            parts=[]
            for (kind,value),sign in zip(choice['parts'],signs):
                delta=max(value*.05, .05e-12 if kind=='C' else 0)
                parts.append((kind,value+sign*delta))
            allscores.append(float(np.max(abs(gamma(evaluate(z,f,parts))))))
        out['common'][state]['CLC_illustrative_tolerance']={'assumption':'C: +/-max(5%,0.05pF); L: +/-5%; 27 combinations; ideal components only','worst_s11_db':float(20*np.log10(max(allscores)))}
    fig,axs=plt.subplots(2,2,figsize=(12,8),layout='constrained');colors=['#225f52','#b17430','#4266a1','#955277']
    for col,state in enumerate(['bare','housed']):
        choice=out['common'][state]['networks']['pi_CLC']
        for (key,label,dk,df),color in zip(CASES,colors):
            d=arrays[key+'-'+state];f=d[:,0];z=d[:,1]+1j*d[:,2]
            axs[0,col].plot(f/1e9,d[:,5],color=color,label=label)
            axs[1,col].plot(f/1e9,20*np.log10(abs(gamma(evaluate(z,f,choice['parts'])))),color=color,label=label)
        axs[0,col].set_title(state.title()+' / unmatched');axs[0,col].set_ylim(-8,0)
        axs[1,col].set_title(state.title()+' / same C-L-C per material\n'+choice['input_shunt']+' | '+choice['series']+' | '+choice['load_shunt'],fontsize=11);axs[1,col].set_ylim(-30,0)
    for ax in axs.flat:
        ax.axvspan(2.402,2.480,color='#739578',alpha=.13);ax.grid(alpha=.2);ax.set(xlim=(2.36,2.53),xlabel='Frequency / GHz',ylabel='S11 / dB');ax.legend(fontsize=8,loc='lower right')
    fig.savefig(OUT/'materials-comparison.png',dpi=160);plt.close(fig);draw_topologies()
    (OUT/'materials-matching.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    with zipfile.ZipFile(OUT/'materials-solver-evidence.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
        for name in arrays:
            archive.writestr(name+'/solver.log',(ROOT/f'tmp/rf-{name}.log').read_text().replace(str(ROOT),'<REPOSITORY>'))
            archive.write(OUT/(name+'.json'),name+'/metadata.json')
            for fn in ['port_ut_1','port_it_1']:archive.write(ROOT/'tmp/rf'/name/fn,name+'/'+fn)
        archive.writestr('README.txt','Eight actual openEMS runs for three named laminate grades. NY2140 has two conditional resin-content cases. All values are approximations at 2.4 GHz. See materials-20260928.html for limitations.\n')
    print(json.dumps({k:{s:out['cases'][k][s]['networks']['pi_CLC'] for s in ['bare','housed']} for k,*_ in CASES},indent=2))

if __name__=='__main__':main()
