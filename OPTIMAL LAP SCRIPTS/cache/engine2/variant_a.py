"""Recreate the SHIPPED optimal laps with engine2 on the SAME raceline geometry (our SVG racelines), and score
new engine vs old engine vs the real 2026 Q lap (corner-anchored alignment onto the real lap, as _vs_physics.py)."""
from common import *
from scipy.ndimage import gaussian_filter1d, median_filter
from fit26 import car26
ROOT = os.path.abspath(os.path.join(H, '..', '..')); E = os.path.join(ROOT, 'F1_Pipeline_Assets', 'exports'); TR = os.path.join(ROOT, 'F1_Pipeline_Assets', 'tracks')
SHIPPED = {'austria': ('Spielberg', 'austrian'), 'canada': ('Montreal', 'canadian'), 'catalunya': ('Catalunya', 'catalunya'),
           'hungary': ('Hungaroring', 'hungarian'), 'monaco': ('Monte Carlo', 'monaco'), 'monza': ('Monza', 'italian'),
           'silverstone': ('Silverstone', 'british'), 'spa': ('Spa-Francorchamps', 'belgian'), 'zandvoort': ('Zandvoort', 'dutch')}
def geom_track(name, ds=5.0):
    r = json.load(open(os.path.join(TR, f'{name}_grand_prix_raceline.json')))
    a = np.array(r['arc_length']); k = np.array(r['kappa'])
    s = np.arange(0, a[-1], ds); kk = np.interp(s, a, k)
    kk = median_filter(gaussian_filter1d(kk, 8.0 / ds, mode='wrap'), 5, mode='wrap')  # ~ the old KGRIP stencil (+-8 m)
    t = dict(s=s, kappa=np.abs(kk), ds=ds, D=a[-1]); t['straight'] = straight_zones(np.where(np.abs(kk) < 1 / 600, 0, kk), ds)
    t['drs'] = t['straight']; return t
def lapdict(t, v_kmh, s):
    dt = np.r_[0, np.diff(s)] / (np.maximum(np.r_[v_kmh[0], 0.5 * (v_kmh[1:] + v_kmh[:-1])], 5) / 3.6)
    z = np.zeros(len(s)); return dict(t=np.cumsum(dt), d=s, v=v_kmh, thr=z, brk=z, gear=z, drs=z, lap=float(np.sum(dt)), D=float(s[-1]))
def oldlap(k):
    d = np.genfromtxt(os.path.join(E, f'{k}_2026_synthetic.csv'), delimiter=',', names=True, dtype=None, encoding=None)
    t, s, v = d['time_s'].astype(float), d['distance'].astype(float), d['speed'].astype(float); z = np.zeros(len(t))
    return dict(t=t, d=s, v=v, thr=z, brk=z, gear=z, drs=z, lap=float(t[-1]), D=float(s[-1]))
def roll_to(real, L, n=2000):
    """Circularly shift lap L so its start line matches the real lap (max cross-correlation of speed vs lap fraction).
    Our raceline S/F can sit off the official line; without this the corner-anchored alignment fails."""
    g = np.linspace(0, 1, n, endpoint=False); a = np.interp(g, real['d'] / real['D'], real['v']); b = np.interp(g, L['d'] / L['D'], L['v'])
    cc = np.real(np.fft.ifft(np.fft.fft(a - a.mean()) * np.conj(np.fft.fft(b - b.mean())))); k = int(np.argmax(cc))
    vv = np.roll(b, k); s = g * L['D']
    return lapdict(None, vv, s) | dict(lap=L['lap'], shift=k / n)
def one(args):
    k, x = args; c, name = SHIPPED[k]; t = geom_track(name); r, _ = optimise_vcap2(car26(x, c), t)
    real = hlib.lap(c, 2026); new = lapdict(t, r['v'] * 3.6, t['s']); new['lap'] = r['lap']; old = oldlap(k)
    out = dict(key=k, circuit=c, real_lap=real['lap'], new_lap=r['lap'], old_lap=old['lap'])
    for tag, L in (('new', new), ('old', old)):
        L = roll_to(real, L); out[tag + '_shift'] = L['shift']
        A = hlib.align(real, L); e = A['v26'] - A['v25']
        out[tag + '_rmse'] = float(np.sqrt(np.mean(e ** 2))); out[tag + '_corr'] = float(np.corrcoef(A['v25'], A['v26'])[0, 1])
        out[tag + '_trace'] = list(np.round(A['v26'], 1)); out['real_trace'] = list(np.round(A['v25'], 1)); out['s'] = list(np.round(A['s'], 1))
        out[tag + '_vmax'] = float(np.max(L['v']))
    out['new_soc'] = list(np.round(np.interp(np.linspace(0, 1, 800), t['s'] / t['D'], r['soc'] / 1e6), 3))
    return out
if __name__ == '__main__':
    from multiprocessing import Pool
    import glob
    XF = {}
    for f in glob.glob('fit26_loo*vcap2_iii_fade.json'): XF.update(json.load(open(f))['x_per_fold'])
    xs = {k: np.array(XF[SHIPPED[k][0]]) for k in SHIPPED}          # each track uses the fold that never saw it
    res = Pool(9).map(one, [(k, xs[k]) for k in SHIPPED])
    json.dump(res, open('variant_a.json', 'w'))
    print(f"{'track':12s} real   | old engine  err  rmse | NEW engine  err  rmse")
    for o in res:
        print(f"{o['key']:12s} {o['real_lap']:6.2f} | {o['old_lap']:6.2f} {o['old_lap']-o['real_lap']:+5.2f} {o['old_rmse']:5.1f} | {o['new_lap']:6.2f} {o['new_lap']-o['real_lap']:+5.2f} {o['new_rmse']:5.1f}")
    f = lambda key: np.median([abs(o[key + '_lap'] - o['real_lap']) for o in res]); g = lambda key: np.median([o[key + '_rmse'] for o in res])
    print(f"median |err|: old {f('old'):.2f} new {f('new'):.2f};  median rmse old {g('old'):.1f} new {g('new'):.1f}")
