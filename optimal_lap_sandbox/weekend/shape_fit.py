"""Speed-pattern fit to the real lap, section by section (user rule 2026-10-24, spec D25/D28).

The sim's track is a flat 2-D band: it cannot see camber, crests, gradient or the real car's energy
strategy, so corner by corner its speed shape differs from FP1. On a FIXED line this fits three maps
(20 m bins along the lap) plus braking grip so the sim's speed follows the target shape:

  GRIP_MAP   cornering speed (and the matching lateral capacity) in curved bins
  ACCEL_MAP  forward acceleration where the car accelerates or coasts
  BRAKE_MAP  braking grip in each braking zone
  MU_LONG    braking grip, picked from candidates by score

Target shape = the reference lap uniformly K x faster (D25: "FP1 pattern a bit faster"); K is solved so
the lap lands on the decided time. Real clip zones are moved onto the sim's distance axis with the same
alignment, so SUPERCLIP sits where the real car clipped. All of it is FITTED (not physics).

Alignment: the two laps' distance axes drift apart (different line lengths, GPS distance), so the
reference is warped piecewise-linearly onto the sim at matched speed minima and peaks.
"""
from __future__ import annotations

import json

import numpy as np
from scipy.signal import find_peaks

from weekend import simdoor


def _grid(sim_d, n=5000):
    L = float(sim_d[-1])
    return L, np.linspace(0.0, L, n, endpoint=False)


def warp(sim_d, sim_v, ref_d, ref_v, prominence=5.0, max_shift_m=80.0):
    """Reference distance -> sim distance, anchored at matched speed minima and peaks."""
    L, g = _grid(sim_d)
    rd = np.asarray(ref_d, float) / float(ref_d[-1]) * L
    vs, vr = np.interp(g, sim_d, sim_v), np.interp(g, rd, ref_v)
    ms = np.sort(np.r_[find_peaks(-vs, prominence=prominence)[0], find_peaks(vs, prominence=prominence)[0]])
    mr = np.sort(np.r_[find_peaks(-vr, prominence=prominence)[0], find_peaks(vr, prominence=prominence)[0]])
    is_min_s = {int(i): vs[i] < vs[max(i - 20, 0)] for i in ms}
    src, dst = [0.0], [0.0]
    for i in mr:
        is_min = vr[i] < vr[max(i - 20, 0)]
        cand = [j for j in ms if is_min_s[int(j)] == is_min]
        if not cand:
            continue
        j = cand[int(np.argmin(np.abs(g[cand] - g[i])))]
        if abs(g[j] - g[i]) < max_shift_m and g[j] > dst[-1] + 20 and g[i] > src[-1] + 20:
            src.append(float(g[i])); dst.append(float(g[j]))
    src.append(L); dst.append(L)
    return lambda x: np.interp(np.asarray(x, float) / float(ref_d[-1]) * L, src, dst)


def on_sim_axis(sim, ref, k=1.0):
    """(g, v_sim, v_target, t_sim, t_target, L): target = reference x k on the sim's distance grid."""
    sd = np.asarray(sim["distance"], float)
    L, g = _grid(sd)
    w = warp(sd, sim["speed"], np.asarray(ref["distance"], float), ref["speed"])(ref["distance"])
    return (g, np.interp(g, sd, sim["speed"]), np.interp(g, w, ref["speed"]) * k,
            np.interp(g, sd, sim["time_s"]), np.interp(g, w, ref["time_s"]) / k, L)


def sections(sim, ref, k, prominence_kmh, tol_rmse_kmh):
    """Per section between the target's straight peaks: RMSE / worst gap (km/h) vs the target shape."""
    g, vs, vr, _, _, _ = on_sim_axis(sim, ref, k)
    pk, _ = find_peaks(vr, prominence=prominence_kmh)
    cuts = [0] + [int(p) for p in pk if 0 < p < len(g) - 1] + [len(g) - 1]
    out = []
    for a, b in zip(cuts[:-1], cuts[1:]):
        if b - a < 5:
            continue
        d = vs[a:b] - vr[a:b]
        w = int(np.argmax(np.abs(d)))
        e = float(np.sqrt(np.mean(d ** 2)))
        out.append(dict(start_m=round(float(g[a])), end_m=round(float(g[b])), rmse_kmh=round(e, 1),
                        worst_kmh=round(float(d[w]), 1), worst_at_m=round(float(g[a + w])), ok=bool(e <= tol_rmse_kmh)))
    return out


def _radius(P, k=8):
    n = len(P); out = np.zeros(n)
    for i in range(n):
        a, b, c = P[(i - k) % n], P[i], P[(i + k) % n]
        ab, bc, ac = b - a, c - b, c - a
        cr = abs(ab[0] * bc[1] - ab[1] * bc[0])
        out[i] = np.linalg.norm(ab) * np.linalg.norm(bc) * np.linalg.norm(ac) / (2 * cr) if cr > 1e-9 else 1e6
    return out


class Fit:
    def __init__(self, vals, raceline, ref, cfg):
        import pandas as pd
        self.pd = pd
        self.vals, self.rl, self.ref, self.cfg = dict(vals), np.asarray(raceline, float)[:, :2], ref, cfg
        arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(self.rl, axis=0), axis=1))]
        self.L0 = arc[-1] + np.linalg.norm(self.rl[0] - self.rl[-1])
        R = _radius(self.rl)
        self.nb = int(np.ceil(self.L0 / cfg["bin_m"]))
        self.edges = np.linspace(0, self.L0, self.nb + 1)
        self.curved = np.array([bool(((arc >= self.edges[j]) & (arc < self.edges[j + 1])).any())
                                and R[(arc >= self.edges[j]) & (arc < self.edges[j + 1])].min() < cfg["curved_r_m"]
                                for j in range(self.nb)])

    def lap(self, v):
        import io
        sim = simdoor.configure(v)
        buf = io.StringIO()
        vv, t, arc, L, mode = simdoor.final_lap(sim, self.rl, v, check=False)
        d = np.asarray(arc) - arc[0]
        s = self.pd.DataFrame(dict(distance=d, speed=np.asarray(vv) * 3.6, time_s=np.asarray(t) - t[0], mode=mode))
        return s, float(t[-1] + (arc[0] + L - arc[-1]) / max(vv[-1], 1.0))

    def _map(self, sx):
        m = [[round(self.edges[j] / self.L0, 5), round(self.edges[j + 1] / self.L0, 5), round(float(sx[j]), 4)]
             for j in range(self.nb) if abs(sx[j] - 1) > 1e-4]
        return json.dumps(m) if m else ""

    def clip_zones_on_sim(self, zones_ref, s):
        """Real clip zones [frac_start, frac_end, rate] (reference lap fractions) -> sim lap fractions."""
        if not zones_ref:
            return ""
        sd = s["distance"].to_numpy(float)
        rd = np.asarray(self.ref["distance"], float)
        w = warp(sd, s["speed"], rd, self.ref["speed"])
        L = float(sd[-1])
        return json.dumps([[round(float(w(a * rd[-1]) / L), 5), round(float(w(b * rd[-1]) / L), 5), r] for a, b, r in zones_ref])

    def run(self, v0, k, passes):
        cfg = self.cfg
        sg, sa, sb = np.ones(self.nb), np.ones(self.nb), np.ones(self.nb)
        best = None
        for _ in range(passes):
            v = dict(v0, GRIP_MAP=self._map(sg), ACCEL_MAP=self._map(sa), BRAKE_MAP=self._map(sb))
            s, lap_s = self.lap(v)
            rows = sections(s, self.ref, k, cfg["prominence_kmh"], cfg["tol_rmse_kmh"])
            score = sum(x["rmse_kmh"] ** 2 for x in rows)
            if best is None or score < best[0]:
                best = (score, v, rows, lap_s)
            g, vs, vr, ts, tr, L = on_sim_axis(s, self.ref, k)
            a_s, a_r = np.gradient(vs, ts), np.gradient(vr, tr)
            idx = np.clip(np.searchsorted(s["distance"].to_numpy(), g), 0, len(s) - 1)
            mode = np.asarray(s["mode"])[idx]
            brk = (mode == "REGEN").astype(float)
            for j in range(self.nb):
                m = (g >= self.edges[j] / self.L0 * L) & (g < self.edges[j + 1] / self.L0 * L)
                if not m.any():
                    continue
                ds, dr = vs[m].mean(), vr[m].mean()
                clip_zone = (mode[m] == "SUPERCLIP").any()
                ref_brakes = a_r[m].mean() < -10
                sim_brakes = brk[m].max() > 0
                if self.curved[j] and abs(ds - dr) > 1.0:   # corner speed limit follows the target both ways
                    sg[j] = float(np.clip(sg[j] * (dr / ds) ** 0.7, *cfg["grip_range"]))
                if (ref_brakes or sim_brakes) and a_s[m].mean() < -5:
                    mu = (g >= self.edges[max(j - 2, 0)] / self.L0 * L) & (g < self.edges[j + 1] / self.L0 * L)
                    dsu, dru = vs[mu].mean(), vr[mu].mean()       # braking here sets the speed just before it
                    if abs(dsu - dru) > 1.0:
                        sb[j] = float(np.clip(sb[j] * np.clip((dru / dsu) ** 2, 0.95, 1.05), *cfg["brake_range"]))
                if not ref_brakes and not clip_zone and (a_r[m].mean() > 0.5 or ds > dr + 1.0) and abs(ds - dr) > 1.0:
                    e = 3 if (ds > dr and a_r[m].mean() <= 0.5) else 1   # coasting where the real car lifts
                    sa[j] = float(np.clip(sa[j] * np.clip(dr / ds, 0.95, 1.05) ** e, *cfg["accel_range"]))
        return best


def fit(vals, raceline, ref, ref_lap_s, target_s, zones_ref, cfg, log=print):
    """Returns (fitted values to merge into the car, report)."""
    F = Fit(vals, raceline, ref, cfg)
    cur, _ = F.lap(vals)
    k = ref_lap_s / target_s
    tried = []
    best = None
    for it in range(cfg["k_iters"]):
        # real clip zones re-placed with the CURRENT lap's alignment (corners move as the fit converges)
        base = dict(vals, CLIP_ZONES=F.clip_zones_on_sim(zones_ref, cur)) if zones_ref else dict(vals)
        cands = []
        for mu in cfg["mu_long"]:
            b = F.run(dict(base, MU_LONG=mu), k, cfg["passes"])
            cands.append((b[0], mu, b))
        cands.sort(key=lambda x: x[0])
        score, mu, b = cands[0]
        lap_s = b[3]
        tried.append(dict(k=round(k, 5), mu_long=mu, lap_s=round(lap_s, 3), score=round(score, 1),
                          failing=sum(not x["ok"] for x in b[2])))
        log(f"[shape_fit] K {k:.4f} MU_LONG {mu}: lap {lap_s:.3f} (target {target_s}), "
            f"sections failing {tried[-1]['failing']}/{len(b[2])}")
        if best is None or abs(lap_s - target_s) < abs(best[3] - target_s) or (
                abs(lap_s - target_s) <= cfg["lap_tol_s"] and score < best[0]):
            best = (score, b[1], b[2], lap_s, k, mu)
        cur, _ = F.lap(b[1])
        if abs(lap_s - target_s) <= cfg["lap_tol_s"] and it > 0:
            break
        k *= (lap_s / target_s) ** 1.0
    score, v, rows, lap_s, k, mu = best
    out = {n: v[n] for n in ("GRIP_MAP", "ACCEL_MAP", "BRAKE_MAP", "MU_LONG", "CLIP_ZONES")}
    return out, dict(k=round(k, 5), mu_long=mu, lap_s=round(lap_s, 3), sections=rows, tried=tried,
                     origin="FITTED", note="maps fitted to the real lap's speed shape (x K), not physics")


def clip_match(sim, ref, tol_m):
    """Spec D28: the sim's SUPERCLIP stretches vs the real clip zones (speed falling at full throttle),
    both on the sim's distance axis (reference warped). A real zone is matched by a sim zone ending within
    tol_m and covering at least half of it; a sim zone with no real partner is 'extra'."""
    from weekend import features as F
    sd = np.asarray(sim["distance"], float)
    rd = np.asarray(ref["distance"], float)
    w = warp(sd, sim["speed"], rd, ref["speed"])
    zr = [(float(w(a)), float(w(b)), va, vb) for a, b, va, vb in F.clip_zones(rd, ref["time_s"], ref["speed"], ref["throttle"])]
    m = np.asarray(sim["mode"]) == "SUPERCLIP"
    sv = np.asarray(sim["speed"], float)
    zs, i = [], 0
    while i < len(m):
        if m[i]:
            j = i
            while j + 1 < len(m) and m[j + 1]:
                j += 1
            if zs and sd[i] - zs[-1][1] <= 40.0:          # same zone, label dropped for a few metres
                zs[-1] = (zs[-1][0], float(sd[j]), zs[-1][2], float(sv[j]))
            else:
                zs.append((float(sd[i]), float(sd[j]), float(sv[i]), float(sv[j])))
            i = j + 1
        else:
            i += 1
    used, rows = set(), []
    for z in zr:
        jj = next((k for k, x in enumerate(zs) if k not in used and abs(x[1] - z[1]) <= tol_m
                   and min(x[1], z[1]) - max(x[0], z[0]) >= 0.5 * (z[1] - z[0])), None)
        if jj is not None:
            used.add(jj)
        x = zs[jj] if jj is not None else None
        rows.append(dict(ref_m=[round(z[0]), round(z[1])], ref_drop_kmh=round(z[3] - z[2], 1),
                         sim_m=[round(x[0]), round(x[1])] if x else None,
                         sim_drop_kmh=round(x[3] - x[2], 1) if x else None, ok=x is not None))
    extra = [dict(sim_m=[round(x[0]), round(x[1])], sim_drop_kmh=round(x[3] - x[2], 1))
             for k, x in enumerate(zs) if k not in used]
    return dict(zones=rows, extra=extra, ok=all(z["ok"] for z in rows) and not extra)
