"""engine2 - regulation-faithful quasi-steady-state (QSS) lap engine with 2026 ERS energy management.

Why a new engine: the old sim_2026_lap.py models MGU-K deployment as a fixed speed taper
(350 kW at 200 -> 0 at 300 km/h). The FIA 2026 rules do not say that. C5.2.8 profile (ii) (Overtake
active, which B7.2.3(b) makes permanent in qualifying) allows 350 kW up to 337.5 km/h:
    P_K <= min(350, 7100 - 20 v)  [kW, v in km/h], 0 above 355 km/h.
What really limits the 2026 car on a straight is ENERGY: a 4 MJ state-of-charge window (C5.2.9) and a
per-lap recharge cap (C5.2.10; 9 MJ at the start of 2026, 8 MJ from Suzuka, 7 MJ in qualifying from Miami
after the April-2026 FIA package). So the car must stop deploying ('clipping') and harvest at full
throttle ('superclipping', 250 kW, 350 kW from Miami) - the 2026 speed-trace signature. Power reductions
in a power-limited state are rate-limited (C5.12: first step <= 150 kW, then 100 kW/s).

This module solves that energy allocation as an optimal-control problem (greedy marginal-cost water
filling: cut deployment / add superclip wherever it costs the least lap time per joule, until the SoC path
stays inside [0, 4 MJ] and recharge <= cap), on top of a standard forward/backward QSS speed solver.

Sources: FIA 2026 F1 Regulations Section C (C5.2.7-C5.2.11, C5.12), Section B (B7.2); encoded the same way in
github.com/Mahdi-Kadiri/f1-2026-lap-energy-simulator (MIT, regs_2026.py, Issue 19 / 25 June 2026);
April-2026 changes: FIA via motorsport.com / autosport.com 2026-04-20.
"""
import math
import numpy as np

G = 9.80665


# ------------------------------------------------------------------ regulations
import os
PROFILE = os.environ.get('PROFILE', 'ii')   # 'ii' overtake/override, 'i' baseline, 'iii' 250 kW sector cap


def mguk_deploy_limit_kw(v_kmh, overtake=None):
    """C5.2.8 / PU regs 5.4.7. Profile (ii) = Overtake ('override') active - always on in qualifying per B7.2.3(b);
    profile (i) = baseline; profile (iii) = 250 kW below 310 km/h then (i)."""
    prof = PROFILE if overtake is None else ('ii' if overtake else 'i')
    if prof == 'iii' and v_kmh < 310.0:
        return 250.0
    if prof == 'ii':
        return 0.0 if v_kmh >= 355.0 else min(350.0, 7100.0 - 20.0 * v_kmh)
    if v_kmh < 340.0:
        return min(350.0, 1800.0 - 5.0 * v_kmh)
    return max(0.0, 6900.0 - 20.0 * v_kmh) if v_kmh < 345.0 else 0.0


# 2026 qualifying energy rules by event (public reporting of the FIA changes):
#   before Suzuka: recharge 9 MJ, superclip 250 kW; Suzuka: 8 MJ; from Miami: 7 MJ and superclip 350 kW.
EVENT_ENERGY = {
    "Melbourne": (9.0, 250.0), "Shanghai": (9.0, 250.0), "Suzuka": (8.0, 250.0),
}
DEFAULT_ENERGY = (7.0, 350.0)


def energy_rules(circuit):
    return EVENT_ENERGY.get(circuit, DEFAULT_ENERGY)


# ------------------------------------------------------------------ car
class Car:
    """Point-mass car. Lateral capability a_y(v) = mu*g + c*v^2 with c = mu*rho*ClA/(2m).
    All powers are at the wheel (W). era '2025' = constant MGU-K 120 kW, DRS from telemetry; '2026' = ERS
    energy management above and Straight/Corner-mode active aero."""

    def __init__(self, era, m, mu, ClA, CdA_c, CdA_s, P_ice, mu_b, mu_d, rho=1.18, crr=0.012,
                 recharge_MJ=7.0, superclip_kw=350.0, soc_MJ=4.0, eta=0.95, ramp_step_kw=150.0,
                 ramp_rate_kws=100.0, regen_kw=350.0, P_k=120e3, ClA_s=None, fade=0.0):
        self.era, self.m, self.mu, self.ClA, self.CdA_c, self.CdA_s = era, m, mu, ClA, CdA_c, CdA_s
        self.ClA_s = ClA if ClA_s is None else ClA_s
        self.P_ice, self.mu_b, self.mu_d, self.rho, self.crr = P_ice, mu_b, mu_d, rho, crr
        self.recharge, self.sc_kw, self.soc0, self.eta = recharge_MJ * 1e6, superclip_kw * 1e3, soc_MJ * 1e6, eta
        self.ramp_step, self.ramp_rate, self.regen = ramp_step_kw * 1e3, ramp_rate_kws * 1e3, regen_kw * 1e3
        self.P_k = P_k; self.fade = fade

    def c_lat(self, straight=False):
        return self.mu * self.rho * (self.ClA_s if straight else self.ClA) / (2 * self.m)

    def ay_max(self, v):
        return self.mu * G + self.c_lat() * v * v

    def v_corner(self, kappa):
        """Max speed at curvature kappa (corner-mode aero). inf where flat-out."""
        k = abs(kappa); c = self.c_lat()
        if k <= c * 1.0001:
            return 1e9
        return math.sqrt(self.mu * G / (k - c))


# ------------------------------------------------------------------ track from a real 2025 lap
def identify_track(lap25, car25, ds=5.0, thr_corner=95.0, trail_frac=0.5):
    """Effective curvature from a REAL 2025 quali lap seen through the 2025 car's lateral model:
    wherever the 2025 driver was off full throttle and off the brake (or at a speed minimum), the speed is
    grip-limited, so kappa = a_y25(v)/v^2. Elsewhere the track is 'straight' for the car.
    Returns dict s, kappa, v25, drs (bool), D. No XY geometry needed (and none of our SVG drawing errors)."""
    D = lap25["D"]; s = np.arange(0.0, D, ds)
    v = np.interp(s, lap25["d"], lap25["v"]) / 3.6
    thr = np.interp(s, lap25["d"], lap25["thr"]); brk = np.interp(s, lap25["d"], lap25["brk"])
    drs = np.interp(s, lap25["d"], (lap25["drs"] >= 10).astype(float)) > 0.5
    from scipy.signal import find_peaks
    p, _ = find_peaks(-v, prominence=5 / 3.6)
    # decel actually used vs the 2025 car's straight-line braking capability: a driver who is on the brake but
    # NOT braking at the limit is trail-braking into the corner, i.e. grip-limited -> part of the corner.
    from scipy.ndimage import gaussian_filter1d
    vs = gaussian_filter1d(v, 10.0 / ds, mode="wrap")
    acc = vs * np.gradient(vs, ds)
    a_cap = car25.mu_b * G + car25.mu_b * car25.rho * car25.ClA / (2 * car25.m) * vs ** 2         + 0.5 * car25.rho * car25.CdA_c * vs ** 2 / car25.m
    trail = (brk >= 0.5) & (-acc < trail_frac * a_cap)
    mask = ((thr < thr_corner) & (brk < 0.5)) | trail
    for i in p:
        mask[max(0, i - 1):i + 2] = True
    kap = np.where(mask, (car25.mu * G + car25.c_lat() * v * v) / np.maximum(v, 5.0) ** 2, 0.0)
    return dict(s=s, kappa=kap, v25=v, drs=drs, D=D, ds=ds, mask=mask)


def straight_zones(kappa, ds, v_hint=None, min_len=250.0):
    """Active-aero Straight-Mode zones (B7.1; FIA publishes them per event - here: every zero-curvature run of
    >= min_len metres, entered 0.4 s (~30 m) late per C3.10.10(o))."""
    n = len(kappa); z = np.zeros(n, bool); i = 0
    flat = kappa == 0
    while i < n:
        if flat[i]:
            j = i
            while j < n and flat[j]:
                j += 1
            if (j - i) * ds >= min_len:
                z[i + int(30 / ds):j] = True
            i = j
        else:
            i += 1
    # wrap: a run crossing the line
    return z


# ------------------------------------------------------------------ QSS core
def _backward(car, vlim, ds, straight):
    """Braking envelope: corner-mode aero while braking (2026 active aero closes on the brake)."""
    n = len(vlim); vb = list(vlim)
    m, rho, cb = car.m, car.rho, car.mu_b * car.rho * car.ClA / (2 * car.m)
    for _ in range(2):
        for i in range(n - 1, -1, -1):
            j = (i + 1) % n; vj = vb[j]
            a = car.mu_b * G + cb * vj * vj + 0.5 * rho * car.CdA_c * vj * vj / m
            vv = math.sqrt(vj * vj + 2 * a * ds)
            if vv < vb[i]:
                vb[i] = vv
    return vb


def simulate(car, trk, ctrl=None, allow_negative=False):
    """One lap. ctrl (2026 only) = (d_off, l_sc, phases): per accel phase, deploy-off distance from phase start
    and superclip length before phase end. Returns dict with v (m/s), t, soc, u (W, +deploy -harvest), lap."""
    s, kap, ds = trk["s"], trk["kappa"], trk["ds"]; n = len(s)
    straight = trk["straight"] if car.era == "2026" else trk["drs"]
    vlim = [min(car.v_corner(k), 400 / 3.6) for k in kap]
    vb = _backward(car, vlim, ds, straight)
    m, rho, crr = car.m, car.rho, car.crr
    is26 = car.era == "2026"
    # per-index control flags
    dep_on = [True] * n; sc_on = [False] * n
    vcap = None
    if is26 and ctrl is not None and ctrl[0] == 'vcap':
        vcap = ctrl[1]; ctrl = None
    vcap_i = None
    if is26 and ctrl is not None and ctrl[0] == 'vcaps':       # per-station cruise speed (per-straight caps)
        vcap_i = ctrl[1]; ctrl = None; vcap = 1e9
    if is26 and ctrl is not None:
        d_off, l_sc, phases = ctrl
        for k, (a, b) in enumerate(phases):
            idx = [(a + q) % n for q in range((b - a) % n + 1)]
            for q, i in enumerate(idx):
                if q * ds >= d_off[k]:
                    dep_on[i] = False
                if (len(idx) - 1 - q) * ds < l_sc[k]:
                    sc_on[i] = True
    v = [0.0] * n; u = [0.0] * n; soc = [0.0] * (n + 1); dt = [0.0] * n; braking = [False] * n
    v0 = vb[0]
    for _pass in range(2):                       # second pass = periodic start speed
        v[0] = min(v0, vb[0]); E = car.soc0; soc[0] = E; rech = 0.0
        pk_prev = 0.0; t_off = None
        for i in range(n):
            vi = max(v[i], 3.0); j = (i + 1) % n
            st = bool(straight[i]); CdA = car.CdA_s if st else car.CdA_c
            drag = 0.5 * rho * CdA * vi * vi + crr * (m * G + 0.5 * rho * car.ClA * vi * vi)
            if is26:
                vkmh = vi * 3.6
                pk_max = mguk_deploy_limit_kw(vkmh) * 1e3
                if dep_on[i] and (E > 0 or allow_negative):
                    pk = pk_max; t_off = None
                else:                                # C5.12 ramp-down after the deploy-off point
                    if t_off is None:
                        t_off = 0.0; pk = max(0.0, pk_prev - car.ramp_step)
                    else:
                        pk = max(0.0, pk_prev - car.ramp_rate * dt[i - 1]) if i > 0 else 0.0
                    pk = min(pk, pk_max)
                    if E <= 0 and not allow_negative:
                        pk = 0.0
                if sc_on[i] and rech < car.recharge and E < car.soc0:
                    pk = -car.sc_kw
                if vcap_i is not None:
                    vcap = vcap_i[i]
                if vcap is not None:
                    # energy-limited optimum (singular arc): full deploy below the cruise speed, then HOLD it with
                    # just the power drag needs; spare ICE power is harvested at full throttle (superclip).
                    if vi < vcap:
                        pk = pk_max if (E > 0 or allow_negative) else 0.0
                    else:
                        pk = max(-car.sc_kw, min(pk_max, drag * vi - car.P_ice - car.fade))
                        if pk < 0 and (rech >= car.recharge or E >= car.soc0):
                            pk = 0.0
                P = car.P_ice + pk
            else:
                pk = car.P_k; P = car.P_ice + pk
            a_trac = car.mu_d * (G + car.c_lat() * vi * vi)
            F = min(P / vi, m * a_trac) if P > 0 else P / vi
            a = (F - drag) / m
            vn = math.sqrt(max(vi * vi + 2 * a * ds, 1.0))
            vn = min(vn, vlim[j]) if vn > vlim[j] else vn
            if vn >= vb[j]:                          # braking-limited
                vn = vb[j]; brk = vn < vi - 1e-6
            else:
                brk = False
            braking[i] = brk
            dti = 2 * ds / (vi + vn); dt[i] = dti
            if is26:
                if brk:
                    # regen under braking: brake power is huge, MGU-K takes up to 350 kW (C5.2.7)
                    Pb = m * (vi * vi - vn * vn) / (2 * ds) * vi
                    h = min(car.regen, 0.5 * Pb)
                    gain = min(h * dti * car.eta, car.soc0 - E, car.recharge - rech)
                    E += gain; rech += gain; u[i] = -h; pk_prev = 0.0
                else:
                    if pk > 0:
                        # only the electric power actually needed (speed-capped corners need little)
                        need = (m * (vn * vn - vi * vi) / (2 * ds) + drag) * vi - car.P_ice
                        used = max(0.0, min(pk, need))
                        E -= used * dti / car.eta; u[i] = used
                    elif pk < 0:
                        gain = min(-pk * dti * car.eta, car.soc0 - E, car.recharge - rech)
                        E += gain; rech += gain; u[i] = pk
                    pk_prev = pk if pk > 0 else 0.0
            soc[i + 1] = E
            v[j if j else 0] = vn if j else v[0]
            if j == 0:
                v0 = vn
        # loop closes
    lap = sum(dt)
    out = dict(v=np.array(v), lap=lap, dt=np.array(dt), soc=np.array(soc[:n]), u=np.array(u),
               braking=np.array(braking), vb=np.array(vb), vlim=np.array(vlim), rech=rech)
    out["t"] = np.r_[0.0, np.cumsum(out["dt"])[:-1]]
    return out


def accel_phases(res, n):
    """Accel phases = maximal runs of non-braking stations (from braking end/apex to next braking start)."""
    br = res["braking"]; ph = []
    starts = [i for i in range(n) if not br[i] and br[i - 1]]
    for a in starts:
        b = a
        while not br[(b + 1) % n] and (b + 1) % n != a:
            b = (b + 1) % n
        ph.append((a, b))
    if not ph:
        ph = [(0, n - 1)]
    return ph


def optimise_energy(car, trk, step_m=40.0, max_iter=400, verbose=False):
    """Greedy marginal-cost energy allocation (see module doc). Returns (result, ctrl)."""
    n = len(trk["s"]); ds = trk["ds"]
    base = simulate(car, trk, None)
    phases = accel_phases(base, n)
    plen = [((b - a) % n + 1) * ds for a, b in phases]
    d_off = list(plen); l_sc = [0.0] * len(phases)
    ctrl = (d_off, l_sc, phases)
    cur = simulate(car, trk, ctrl, True)
    for it in range(max_iter):
        E = cur["soc"]; viol = np.nonzero(E < -1.0)[0]
        if not len(viol):
            break
        iv = int(viol[0]); best = None
        for k, (a, b) in enumerate(phases):
            if a > iv:
                continue
            for kind in ("dep", "sc"):
                d2, l2 = list(d_off), list(l_sc)
                if kind == "dep":
                    if d2[k] <= 0:
                        continue
                    d2[k] = max(0.0, d2[k] - step_m)
                else:
                    if l2[k] + step_m > plen[k] or b > iv or cur["rech"] >= car.recharge - 1e3:
                        continue
                    l2[k] = l2[k] + step_m
                r = simulate(car, trk, (d2, l2, phases), True)
                gain = r["soc"][iv] - E[iv]
                if gain <= 1e3:
                    continue
                cost = (r["lap"] - cur["lap"]) / gain
                if best is None or cost < best[0]:
                    best = (cost, d2, l2, r)
        if best is None:
            break
        _, d_off, l_sc, cur = best
        if verbose and it % 10 == 0:
            print(it, round(cur["lap"], 3), round(float(cur["soc"].min()) / 1e6, 3))
    return cur, (d_off, l_sc, phases)


def optimise_vcap(car, trk, lo=60.0, hi=100.0, iters=18):
    """Bisection on the lap-wide cruise speed (m/s) so the SoC path stays >= 0 (4 MJ window, recharge cap).
    One energy multiplier for the whole lap = one cruise speed (Pontryagin singular arc, same aero everywhere)."""
    r = simulate(car, trk, ('vcap', hi), True)
    if r['soc'].min() >= 0:
        return r, hi
    for _ in range(iters):
        mid = 0.5 * (lo + hi); r = simulate(car, trk, ('vcap', mid), True)
        if r['soc'].min() >= 0:
            lo = mid
        else:
            hi = mid
    return simulate(car, trk, ('vcap', lo), True), lo


def optimise_vcap2(car, trk, step=1.0, max_up=12):
    """Global cruise speed (optimise_vcap), then per-straight refinement in lap order: raise a straight's cruise
    speed while the SoC path stays >= 0 and the lap gets faster. Captures the full battery at the start of a
    qualifying lap (harvest while full is wasted, so early straights can spend more)."""
    r, vc = optimise_vcap(car, trk)
    n = len(trk['s']); ph = []
    for a, b in accel_phases(r, n):            # split a straight that crosses the line: post-line part has a full battery
        ph += [(a, n - 1), (0, b)] if b < a else [(a, b)]
    ph.sort(key=lambda p: p[0])
    caps = np.full(n, vc)
    best = simulate(car, trk, ('vcaps', caps), True)
    for a, b in ph:
        idx = np.array([(a + q) % n for q in range((b - a) % n + 1)])
        for _ in range(max_up):
            c2 = caps.copy(); c2[idx] += step
            r2 = simulate(car, trk, ('vcaps', c2), True)
            if r2['soc'].min() >= 0 and r2['lap'] < best['lap'] - 1e-4:
                caps, best = c2, r2
            else:
                break
    best['caps'] = caps
    return best, vc
