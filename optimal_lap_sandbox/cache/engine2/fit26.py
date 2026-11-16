"""2026 car: regulation-fixed ERS/energy (engine2) + 7 physical knobs, fitted to real 2026 Q laps.
Track for each circuit = identified from that circuit's REAL 2025 Q lap (no SVG geometry).
Modes:  python fit26.py prior          -> score the un-fitted prior car
        python fit26.py all            -> fit on all tracks (in-sample)
        python fit26.py loo            -> leave-one-out: fit on 11, predict the 12th blind (the proof)"""
from common import *
from scipy.optimize import least_squares
from multiprocessing import Pool
POLICY = os.environ.get('POLICY', 'vcap'); TAG = os.environ.get('TAG', '')
P26 = ['mu', 'ClA', 'CdA_c', 'CdA_s', 'P_ice', 'mu_b', 'mu_d', 'fade']
X26_0 = [1.64, 4.45, 1.30, 0.65, 300e3, 1.08, 0.86, 40e3]
def car26(x, c):
    d = dict(zip(P26, x)); rc, sc = energy_rules(c)
    return Car('2026', m=775, rho=rho_of(c), recharge_MJ=rc, superclip_kw=sc, **d)
_A = {}
def target(c):
    if c not in _A:
        a, b = hlib.lap(c, 2025), hlib.lap(c, 2026); t = track(c)
        A = hlib.align(a, b, n=len(t['s'])); _A[c] = (np.interp(t['s'], A['s'], A['v26']) / 3.6, b['lap'])
    return _A[c]
def run(x, c):
    t = track(c); r, vc = {'vcap': optimise_vcap, 'vcap2': optimise_vcap2, 'greedy': optimise_energy}[POLICY](car26(x, c), t); r['vcap'] = vc if POLICY != 'greedy' else None; return r
def res_track(args):
    x, c = args; r = run(x, c); v26, lap26 = target(c)
    e = (r['v'] - v26) * 3.6
    return np.r_[e[::3] / 10.0, 3.0 * (r['lap'] - lap26)]
def score(args):
    x, c = args; r = run(x, c); v26, lap26 = target(c); e = (r['v'] - v26) * 3.6
    return dict(track=c, lap_sim=r['lap'], lap_real=lap26, err=r['lap'] - lap26, rmse=float(np.sqrt(np.mean(e ** 2))),
                corr=float(np.corrcoef(r['v'], v26)[0, 1]), vmax_sim=float(r['v'].max() * 3.6), vmax_real=float(v26.max() * 3.6),
                rech=r['rech'] / 1e6, vmax_first=float(r['v'][:len(r['v'])//4].max()*3.6), vcap=(r['vcap'] or 0) * 3.6, v=list(np.round(r['v'] * 3.6, 2)), soc=list(np.round(r['soc'] / 1e6, 3)), u=list(np.round(r['u'] / 1e3, 1)))
SC = np.array(X26_0)
LB = [0.6, 0.5, 0.4, 0.4, 0.75, 0.5, 0.5, 0.0]; UB = [1.4, 1.8, 2.0, 2.0, 1.35, 2.0, 2.0, 5.0]
def fit(pool, tracks, x0=None):
    F = lambda z: np.concatenate(pool.map(res_track, [(z * SC, c) for c in tracks]))
    sol = least_squares(F, np.ones(len(SC)) if x0 is None else x0 / SC, diff_step=0.02, bounds=(LB, UB), x_scale=0.2, max_nfev=120)
    return sol.x * SC
if __name__ == '__main__':
    mode = sys.argv[1]; pool = Pool(len(TRACKS))
    if mode == 'prior':
        S = pool.map(score, [(np.array(X26_0), c) for c in TRACKS]); out = dict(x=X26_0, scores=S)
    elif mode == 'all':
        x = fit(pool, TRACKS); S = pool.map(score, [(x, c) for c in TRACKS]); out = dict(x=list(x), scores=S)
    elif mode == 'loo':
        S, XS = [], {}
        x_all = np.array(json.load(open(f'fit26_all_{POLICY}_{PROFILE}{TAG}.json'))['x'])
        folds = sys.argv[2].split(',') if len(sys.argv) > 2 else TRACKS
        for c in folds:
            x = fit(pool, [k for k in TRACKS if k != c], x0=x_all); XS[c] = list(x); S.append(score((x, c)))
            print(c, 'blind err', round(S[-1]['err'], 3), 'rmse', round(S[-1]['rmse'], 1), flush=True)
        out = dict(x_per_fold=XS, scores=S)
        if len(sys.argv) > 2: mode = 'loo_' + str(abs(hash(sys.argv[2])) % 10**6)
    json.dump(out, open(f'fit26_{mode}_{POLICY}_{PROFILE}{TAG}.json', 'w'))
    for s in out['scores']:
        print(f"{s['track']:18s} sim {s['lap_sim']:7.3f} real {s['lap_real']:7.3f} err {s['err']:+6.3f} rmse {s['rmse']:5.1f} corr {s['corr']:.3f} vmax {s['vmax_sim']:5.1f}/{s['vmax_real']:5.1f} rech {s['rech']:.2f} vcap {s['vcap']:.0f}")
    e = np.array([s['err'] for s in out['scores']]); rm = np.array([s['rmse'] for s in out['scores']])
    print(f"median |err| {np.median(abs(e)):.3f} s  mean err {e.mean():+.3f}  median rmse {np.median(rm):.1f} km/h")
    if 'x' in out: print(dict(zip(P26, out['x'])))
