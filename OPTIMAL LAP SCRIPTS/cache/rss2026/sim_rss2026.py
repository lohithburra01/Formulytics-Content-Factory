"""Our lap simulator (sim_2026_lap.py, untouched) with its car replaced by the RSS Formula Hybrid X 2026 data.

Patched in memory only (sim_2026_lap.py on disk is unchanged):
  grip / braking / traction  -> rss_car (tyres.ini load-sensitive mu, aero.ini maps, axle loads)
  power                       -> rss_car.power_at (power.lut x turbo x map + kers_torque x ctrl_ers_4 'Qualy')
  energy                      -> deploy stops once ers.ini MAX_KJ_PER_LAP (9 MJ) has been deployed this lap
Removed (they were our own tuning, not car data): deploy-speed taper, superclip block, 1.65 g accel cap,
trail-brake release, MU_* constants. Kept: raceline, aero-mode switch by curvature, closure loop, smoothing.
Run: python sim_rss2026.py  -> rss_laps.json (9 shipped racelines)."""
import os, sys, json, math
import numpy as np
H = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(H, '..', '..'))
sys.path.insert(0, ROOT); sys.path.insert(0, H)
import sim_2026_lap as S
import rss_car as R

S.MASS_KG = R.MASS
S.CL_CORNER_M2, S.CDA_CORNER_M2 = R.CORNER[0], R.CORNER[1]
S.CL_STRAIGHT_M2, S.CDA_STRAIGHT_M2 = R.STRAIGHT[0], R.STRAIGHT[1]


def a_lat_max_banked(v, mode, bank_rad=0.0):
    a = R.a_lat_max(v, S.RHO, mode)
    if bank_rad == 0.0:
        return a
    mu = a / (S.G + S.downforce(v, mode) / S.MASS_KG)          # same banking algebra as the simulator
    ct, st = math.cos(bank_rad), math.sin(bank_rad); den = ct - mu * st
    return 1e4 if den <= S.BANK_DENOM_FLOOR else (S.G * (mu * ct + st) + mu * S.downforce(v, mode) / S.MASS_KG) / den


def v_grip_static(kappa, bank_rad=0.0):
    k = abs(kappa)
    if k < 1e-6:
        return 300.0
    lo, hi = 5.0, 120.0
    if a_lat_max_banked(hi, 'CORNER', bank_rad) >= k * hi * hi:
        return 300.0
    for _ in range(50):
        m = 0.5 * (lo + hi)
        if a_lat_max_banked(m, 'CORNER', bank_rad) >= k * m * m:
            lo = m
        else:
            hi = m
    return lo


def compute_v_brake_backward(v_grip, kappa, arc, track_length_m, n_iters=3):
    n = len(v_grip); ds = np.diff(np.concatenate([arc, [track_length_m]])); v = v_grip.copy()
    for _ in range(n_iters):
        for i in range(n - 1, -1, -1):
            ip = (i + 1) % n
            al_used = abs(kappa[ip]) * v[ip] ** 2; al_max = a_lat_max_banked(v[ip], 'CORNER', S._bank_at(ip))
            r2 = min(1.0, (al_used / max(al_max, 1e-6)) ** 2)
            a = R.a_brake_max(v[ip], S.RHO, 'CORNER') * math.sqrt(1 - r2) + S.drag_force(v[ip], 'CORNER') / S.MASS_KG
            vp = math.sqrt(max(0.0, v[ip] ** 2 + 2 * a * ds[i]))
            if vp < v[i]:
                v[i] = vp
    return v


def forward_pass_energy_aware(v_grip, v_brake, kappa, arc, track_length_m, v0=None, soc0=1.0, superclip_mask=None):
    n = len(v_grip); ds = np.diff(np.concatenate([arc, [track_length_m]]))
    v_init = v0 if v0 is not None else min(v_grip[0], v_brake[0])
    braking = S._braking_zones(v_grip, v_brake, kappa, ds, v_init)
    v = np.full(n, v_init); soc_arr = np.zeros(n); mode_arr = ['NORMAL'] * n; p_kw = np.zeros(n); t_arr = np.zeros(n)
    t = 0.0; used = 0.0
    for i in range(n):
        v[i] = min(v[i], v_grip[i], v_brake[i]); ip = (i + 1) % n
        soc_arr[i] = 1.0 - used / R.DEPLOY_J_PER_LAP
        if braking[i]:
            mode_arr[i] = 'REGEN'; vn = min(v[i], v_grip[ip], v_brake[ip]); v[ip] = vn
            dt = 2 * ds[i] / max(v[i] + vn, 1e-3); t += dt; t_arr[i] = t; continue
        am = S.aero_mode(kappa[i])
        p_ice, p_k, _ = R.power_at(v[i])
        if used >= R.DEPLOY_J_PER_LAP:
            p_k = 0.0
        al_used = abs(kappa[i]) * v[i] ** 2; al_max = a_lat_max_banked(v[i], am, S._bank_at(i))
        r2 = min(1.0, (al_used / max(al_max, 1e-6)) ** 2)
        a_grip = R.a_trac_max(v[i], S.RHO, am) * math.sqrt(1 - r2)
        a_pow = (p_ice + p_k) / (S.MASS_KG * max(v[i], S.V_FLOOR_MS))
        a = min(a_grip, a_pow) - S.drag_force(v[i], am) / S.MASS_KG
        vn = min(math.sqrt(max(S.V_FLOOR_MS ** 2, v[i] ** 2 + 2 * a * ds[i])), v_grip[ip], v_brake[ip]); v[ip] = vn
        dt = 2 * ds[i] / max(v[i] + vn, 1e-3)
        frac_k = 0.0 if a_pow <= a_grip else a_grip / a_pow                 # traction-limited: only what is used
        k_used = p_k * (1.0 if a_pow <= a_grip else frac_k)
        used += k_used * dt
        mode_arr[i] = 'DEPLOY' if p_k > 0 else 'CLIPPING'; p_kw[i] = (p_ice + p_k) / 1e3
        t += dt; t_arr[i] = t
    return v, soc_arr, mode_arr, p_kw, t_arr


S.a_lat_max_banked = a_lat_max_banked; S.v_grip_static = v_grip_static
S.compute_v_brake_backward = compute_v_brake_backward; S.forward_pass_energy_aware = forward_pass_energy_aware
S._superclip_mask = lambda *a, **k: np.zeros(len(a[0]), bool)

SHIPPED = {'austria': ('Spielberg', 'austrian'), 'canada': ('Montreal', 'canadian'), 'catalunya': ('Catalunya', 'catalunya'),
           'hungary': ('Hungaroring', 'hungarian'), 'monaco': ('Monte Carlo', 'monaco'), 'monza': ('Monza', 'italian'),
           'silverstone': ('Silverstone', 'british'), 'spa': ('Spa-Francorchamps', 'belgian'), 'zandvoort': ('Zandvoort', 'dutch')}
ALT = {'Spielberg': 680, 'Hungaroring': 250, 'Spa-Francorchamps': 400, 'Monza': 160, 'Silverstone': 150}


def run(key):
    c, name = SHIPPED[key]; S.RHO = 1.18 * math.exp(-ALT.get(c, 10) / 8500)
    r = json.load(open(os.path.join(ROOT, 'F1_Pipeline_Assets', 'tracks', f'{name}_grand_prix_raceline.json')))
    rl = np.array(r['raceline']); arc = np.array(r['arc_length']); kap = np.array(r['kappa']); L = float(r['track_length_m'])
    v, soc, mode, p, t = S.simulate_lap(rl, arc, kap, L)
    vs, _ = S.smooth_longitudinal(v, arc, L)
    lap = float(np.sum(np.diff(np.r_[arc, L]) / np.maximum(0.5 * (vs + np.roll(vs, -1)), 1)))
    return dict(key=key, circuit=c, lap=lap, s=list(np.round(arc, 1)), v=list(np.round(vs * 3.6, 2)), mode=mode,
                deployed_MJ=round((1 - soc[-1]) * R.DEPLOY_J_PER_LAP / 1e6, 2))


if __name__ == '__main__':
    from multiprocessing import Pool
    res = Pool(9).map(run, list(SHIPPED))
    json.dump(res, open(os.path.join(H, 'rss_laps.json'), 'w'))
    for o in res:
        print(o['key'], round(o['lap'], 3), 'vmax', max(o['v']), 'deployed MJ', o['deployed_MJ'])
