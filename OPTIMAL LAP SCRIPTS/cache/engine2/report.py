"""One scoring function for every method, all vs the REAL 2026 Q lap:
lap-time error, speed-trace RMSE and correlation after start-line roll + corner-anchored alignment.
Methods: OLD physics (shipped synthetic CSVs), pattern HYBRID (cache/hypo LOO), NEW engine2 blind LOO on the
2025-identified track, NEW engine2 on our shipped raceline geometry. Writes metrics.json + PNGs."""
from variant_a import *
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from fit26 import target
def metric(real, L):
    L = roll_to(real, L); A = hlib.align(real, L); e = A['v26'] - A['v25']
    return dict(err=L['lap'] - real['lap'], rmse=float(np.sqrt(np.mean(e ** 2))), corr=float(np.corrcoef(A['v25'], A['v26'])[0, 1]),
                s=A['s'], v=A['v26'], vreal=A['v25'])
import glob
LOO = {s['track']: s for f in glob.glob('fit26_loo*vcap2_iii_fade.json') for s in json.load(open(f))['scores']}
VA = {o['circuit']: o for o in json.load(open('variant_a.json'))}
H3 = json.load(open(os.path.join(H, '..', 'hypo', 'loo3.json')))
INV = {v[0]: k for k, v in SHIPPED.items()}
M, traces = {}, {}
for c in TRACKS:
    real = hlib.lap(c, 2026); t = track(c); m = {}; tr = {}
    o = LOO[c]; L = lapdict(None, np.array(o['v']), t['s']); L['lap'] = o['lap_sim']; m['new_blind'] = metric(real, L)
    h = H3[c]; s = np.array(h['s']); v = np.array(h['v']) * h['model'] / h['naive']; L = lapdict(None, v, s); L['lap'] = h['naive']; m['hybrid'] = metric(real, L)
    L = hlib.lap(c, 2025); m['real2025'] = metric(real, L)
    if c in INV:
        m['old'] = metric(real, oldlap(INV[c]))
        g = VA[c]; vv = np.array(g['new_trace']); L = lapdict(None, vv, np.array(g['s'])); L['lap'] = g['new_lap']; m['new_geom'] = metric(real, L)
    traces[c] = {k: (list(np.round(v['s'], 1)), list(np.round(v['v'], 1))) for k, v in m.items()} | {'real': (list(np.round(m['new_blind']['s'], 1)), list(np.round(m['new_blind']['vreal'], 1)))}
    traces[c]['soc'] = o['soc']; traces[c]['u'] = o['u']; traces[c]['s25'] = list(np.round(t['s'], 1))
    M[c] = {k: dict(err=v['err'], rmse=v['rmse'], corr=v['corr']) for k, v in m.items()} | dict(real=real['lap'])
json.dump(dict(metrics=M, traces=traces), open('metrics.json', 'w'))
names = [('old', 'OLD physics engine (shipped)'), ('hybrid', 'Pattern hybrid (LOO)'), ('new_blind', 'NEW engine2, blind LOO'), ('new_geom', 'NEW engine2 on our raceline')]
print(f"{'track':18s} real   " + ' | '.join(f'{k:>16s}' for k, _ in names))
for c in TRACKS:
    print(f"{c:18s} {M[c]['real']:6.2f} " + ' | '.join((f"{M[c][k]['err']:+6.2f}s {M[c][k]['rmse']:5.1f}" if k in M[c] else ' ' * 13).rjust(16) for k, _ in names))
for k, lab in names:
    cs = [c for c in TRACKS if k in M[c]]; sub9 = [c for c in cs if c in INV]
    f = lambda cc, q: np.median([abs(M[c][k][q]) for c in cc])
    print(f"{lab:32s} n={len(cs):2d}  median|err| {f(cs,'err'):.2f}s  median rmse {f(cs,'rmse'):5.1f}  median corr {np.median([M[c][k]['corr'] for c in cs]):.3f}"
          f"   | on the 9 shipped: |err| {f(sub9,'err'):.2f}  rmse {f(sub9,'rmse'):.1f}")
