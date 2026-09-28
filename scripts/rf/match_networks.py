"""Enumerate ideal L and pi matching networks at an explicitly defined 50-ohm port.

Element order is always [input shunt, series, load shunt]. Impedances may
contain multiple material cases; the objective is worst |Gamma| over all
cases and frequencies. This is circuit post-processing, not an EM rerun.
"""
from itertools import product
import numpy as np

CAP_PF = [.2,.3,.4,.5,.6,.7,.8,.9,1,1.1,1.2,1.3,1.5,1.6,1.8,2,2.2,2.4,2.7,3,3.3,3.6,3.9,4.3,4.7,5.1,5.6,6.2,6.8,7.5,8.2,9.1,10,12,15,18,22]
IND_NH = [.5,.6,.7,.8,.9,1,1.1,1.2,1.3,1.5,1.6,1.8,2,2.2,2.4,2.7,3,3.3,3.6,3.9,4.3,4.7,5.1,5.6,6.2,6.8,7.5,8.2,9.1,10,12,15,18,22,27,33,39,47]
PARTS = [('C', x*1e-12) for x in CAP_PF]+[('L', x*1e-9) for x in IND_NH]

def impedance(part, f):
    kind, val = part; w = 2*np.pi*np.asarray(f)
    if kind == 'short': return np.zeros_like(w, dtype=complex)
    if kind == 'L': return 1j*w*val
    if kind == 'C': return 1/(1j*w*val)
    raise ValueError(kind)

def admittance(part, f):
    if part[0] == 'open': return np.zeros_like(f, dtype=complex)
    return 1/impedance(part, f)

def gamma(z): return (z-50)/(z+50)

def evaluate(load, f, parts):
    pin, series, pout = parts
    yout = admittance(pout, f)
    branch = impedance(series, f)+1/(1/load+yout)
    return 1/(1/branch+admittance(pin, f))

def label(part):
    k,v=part
    if k in ('open','short'): return k
    return f'{k} {v/(1e-12 if k=="C" else 1e-9):g} '+('pF' if k=='C' else 'nH')

def record(parts, family, load, f):
    zin = evaluate(load, f, parts)
    refl = abs(gamma(zin))
    return {'family': family, 'parts': [list(p) for p in parts],
            'input_shunt': label(parts[0]), 'series': label(parts[1]), 'load_shunt': label(parts[2]),
            'worst_s11_db': float(20*np.log10(np.max(refl))),
            'per_case_worst_s11_db': (20*np.log10(np.max(refl,axis=-1))).tolist(),
            'contains_L_and_C': {'L','C'}.issubset({p[0] for p in parts})}

def scan(load, f):
    load = np.atleast_2d(load)
    assert load.shape[-1] == len(f) and np.all(load.real>0)
    result=[]
    # Exact finite-grid enumeration; vectorize input shunt choices, enumerate
    # the other two branches. Keep one best per populated C/L family.
    for topology in ('L-input','L-load','pi'):
        kinds = list(product('CL',repeat=3 if topology=='pi' else 2))
        for ks in kinds:
            ki,ksr,ko = ks if topology=='pi' else ((ks[0],ks[1],'open') if topology=='L-input' else ('open',ks[0],ks[1]))
            inputs=[p for p in PARTS if p[0]==ki] if ki!='open' else [('open',0)]
            serial=[p for p in PARTS if p[0]==ksr]
            outputs=[p for p in PARTS if p[0]==ko] if ko!='open' else [('open',0)]
            yi=np.asarray([admittance(p,f) for p in inputs])[:,None,:]
            best=(float('inf'),None)
            for pout in outputs:
                zout=1/(1/load+admittance(pout,f))
                for ser in serial:
                    zin=1/(1/(zout+impedance(ser,f))[None,:,:]+yi)
                    scores=np.max(abs(gamma(zin)),axis=(1,2))
                    ix=int(np.argmin(scores)); score=float(scores[ix])
                    if score<best[0]: best=(score,[inputs[ix],ser,pout])
            family=topology+':'+ki+'-'+ksr+'-'+ko
            result.append(record(best[1],family,load,f))
    result.sort(key=lambda d:d['worst_s11_db'])
    l=[d for d in result if d['family'].startswith('L-')]
    pi=[d for d in result if d['family'].startswith('pi:')]
    return {'best_L_any':l[0], 'best_L_mixed_LC':next(d for d in l if d['contains_L_and_C']),
            'best_pi_any':pi[0], 'best_pi_mixed_LC':next(d for d in pi if d['contains_L_and_C']),
            'pi_CLC':next(d for d in pi if d['family']=='pi:C-L-C'),
            'pi_LCL':next(d for d in pi if d['family']=='pi:L-C-L'),
            'family_results':result}

def self_check():
    # Independently cascade ABCD matrices for all branch choices and compare.
    rng=np.random.default_rng(52832); f=np.linspace(2.402e9,2.480e9,7)
    for _ in range(60):
        parts=[PARTS[int(rng.integers(len(PARTS)))] for _ in range(3)]
        z=5+rng.random(7)*100+1j*(rng.random(7)-.5)*200
        yi=admittance(parts[0],f);zs=impedance(parts[1],f);yo=admittance(parts[2],f)
        abc=[]
        for i in range(len(f)):
            m=np.array([[1,0],[yi[i],1]])@np.array([[1,zs[i]],[0,1]])@np.array([[1,0],[yo[i],1]])
            abc.append((m[0,0]*z[i]+m[0,1])/(m[1,0]*z[i]+m[1,1]))
        assert np.allclose(evaluate(z,f,parts),abc,rtol=1e-11,atol=1e-10)
    w=2*np.pi*f
    assert np.allclose(evaluate(np.full(7,50+0j),f,[('open',0),('short',0),('open',0)]),50)
    # 25 ohms -> 50 ohms at one frequency: input shunt C, series L.
    f0=np.array([2.441e9]);w0=2*np.pi*f0[0]
    assert np.allclose(evaluate(np.array([25+0j]),f0,[('C',.02/w0),('L',25/w0),('open',0)]),50)
    # Reverse-oriented L network: 100 ohms -> 50 ohms.
    assert np.allclose(evaluate(np.array([100+0j]),f0,[('open',0),('C',1/(50*w0)),('L',100/w0)]),50)
    # An inductive complex load can be transformed with two capacitors.
    parts=[('C',.02/w0),('C',1/(75*w0)),('open',0)]
    assert np.allclose(evaluate(np.array([25+100j]),f0,parts),50)

if __name__=='__main__':
    self_check(); print('L/pi network identities and independent ABCD checks passed.')
