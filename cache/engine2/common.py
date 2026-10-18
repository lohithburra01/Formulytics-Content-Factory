import sys, os, math, json, numpy as np
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, '..', 'hypo')); sys.path.insert(0, H)
import hlib
from engine2 import *
TRACKS = [c for c in hlib.pairs() if c != 'Suzuka']           # Suzuka 2026 trace inconsistent (pattern study)
ALT = {'Spielberg': 680, 'Hungaroring': 250, 'Spa-Francorchamps': 400, 'Monza': 160, 'Silverstone': 150}
def rho_of(c): return 1.18 * math.exp(-ALT.get(c, 10) / 8500)
P25 = ['P_ice', 'CdA_c', 'CdA_s', 'mu_b', 'mu_d']
X25_0 = [600e3, 1.10, 0.95, 1.5, 1.1]
def car25(x, c):
    d = dict(zip(P25, x)); return Car('2025', m=805, mu=1.8, ClA=4.5, rho=rho_of(c), **d)
_cache = {}
def track(c, x25=None):
    key = (c, None if x25 is None else tuple(np.round(x25, 6)))
    if key not in _cache:
        L = hlib.lap(c, 2025); t = identify_track(L, car25(x25 or X25_0, c))
        t['straight'] = straight_zones(t['kappa'], t['ds']); t['lap25'] = L['lap']; _cache[key] = t
    return _cache[key]
