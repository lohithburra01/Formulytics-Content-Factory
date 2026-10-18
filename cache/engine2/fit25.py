"""Fit the 2025 BASELINE car (power, drag DRS-closed/open, braking, traction) to the 12 real 2025 Q laps.
Corners come from the laps themselves (identify_track), so this only fits straights + braking."""
from common import *
from scipy.optimize import least_squares
from multiprocessing import Pool
def res_track(args):
    x, c = args; t = track(c); car = car25(x, c); r = simulate(car, t)
    e = (r['v'] - t['v25']) * 3.6
    return np.r_[e[::3] / 10.0, 3.0 * (r['lap'] - t['lap25'])]
def F(x):
    x = np.asarray(x) * SC
    return np.concatenate(POOL.map(res_track, [(x, c) for c in TRACKS]))
SC = np.array(X25_0)
if __name__ == '__main__':
    POOL = Pool(len(TRACKS))
    sol = least_squares(F, np.ones(len(X25_0)), diff_step=1e-3, bounds=([0.6, 0.5, 0.4, 0.5, 0.5], [1.6, 2.0, 2.0, 3.0, 3.0]), x_scale=0.2)
    x = sol.x * SC; print(dict(zip(P25, x)))
    out = {}
    for c in TRACKS:
        t = track(c); r = simulate(car25(x, c), t); e = (r['v'] - t['v25']) * 3.6
        out[c] = dict(lap_sim=r['lap'], lap_real=t['lap25'], rmse=float(np.sqrt(np.mean(e**2))), vmax_sim=float(r['v'].max()*3.6), vmax_real=float(t['v25'].max()*3.6))
        print(f"{c:18s} sim {r['lap']:7.3f} real {t['lap25']:7.3f} err {r['lap']-t['lap25']:+6.3f}  rmse {out[c]['rmse']:5.1f}  vmax {out[c]['vmax_sim']:5.1f}/{out[c]['vmax_real']:5.1f}")
    json.dump(dict(x=list(x), names=P25, tracks=out), open('fit25.json', 'w'), indent=1)
