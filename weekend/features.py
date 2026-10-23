"""Speed-graph features of a sim lap against a real reference lap (grill D7).

Features (each is both a tuning target and a check):
  corners   per reference corner: minimum speed
  straights per reference straight: peak speed
  braking   per braking zone: onset point (5 km/h below the peak) and mean deceleration
  exits     per corner exit: mean acceleration over the first `exit_gain_kmh` above the minimum
  sectors   time per official sector (boundaries from the reference lap's sector times)
  signature GAIN / DROP / SUPERCLIP rates (cache/_gate_2026.py definitions and bands)
Positions are lap fractions (each trace normalised by its own length, then FFT-aligned).
"""
from __future__ import annotations

import os
import sys

import numpy as np
from scipy.signal import find_peaks

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "cache"))
import _gate_2026 as GATE  # noqa: E402
from _track_registry import align_pair, corner_minima  # noqa: E402


def load(csv_path):
    t, v, th, br, s = GATE.load(csv_path)
    return dict(t=t - t[0], v=v, th=th, br=br, s=s - s[0])


def pattern_score(sim, ref) -> float:
    """How closely the sim speed trace follows the real one (grill D24): correlation of speed
    against lap fraction. 1.0 = same shape."""
    vs = np.interp(_frac(ref), _frac(sim), sim["v"])
    return float(np.corrcoef(vs, ref["v"])[0, 1])


def _frac(tr):
    return tr["s"] / tr["s"][-1]


def _win(f, f0, w):
    d = np.abs(f - f0); d = np.minimum(d, 1.0 - d)
    return d <= w


def _t_at(tr, f0):
    return float(np.interp(f0, _frac(tr), tr["t"]))


def features(sim, ref, cfg) -> dict:
    """sim/ref: traces from load(). cfg: tolerances/windows (pack 'check.' values)."""
    L = float(ref["s"][-1])
    _, _, _, shift = align_pair(ref["s"], ref["v"], sim["s"], sim["v"], L)
    fs = (_frac(sim) - shift) % 1.0                   # sim positions in the reference's frame
    order = np.argsort(fs)
    S = dict(f=fs[order], v=sim["v"][order], t=sim["t"][order])
    fr = _frac(ref)
    W = cfg["window_frac"]

    def sim_min(f0):
        m = _win(S["f"], f0, W); i = np.where(m)[0][np.argmin(S["v"][m])]; return i

    def sim_max(f0):
        m = _win(S["f"], f0, W); i = np.where(m)[0][np.argmax(S["v"][m])]; return i

    mins = corner_minima(ref["s"], ref["v"], cfg["corner_prominence_kmh"], cfg["corner_sep_m"])
    pk, _ = find_peaks(ref["v"], prominence=cfg["corner_prominence_kmh"],
                       distance=max(1, int(cfg["corner_sep_m"] / np.median(np.diff(ref["s"])))))
    out = dict(shift_frac=float(shift), corners=[], straights=[], braking=[], exits=[], brake_bands=[], accel_bands=[])

    for n, (cs, cv) in enumerate(mins, 1):
        f0 = cs / L; i = sim_min(f0)
        out["corners"].append(dict(id=n, s_m=round(cs, 1), ref=round(cv, 1), sim=round(float(S["v"][i]), 1),
                                   err=round(float(S["v"][i]) - cv, 1)))
    for n, j in enumerate(pk, 1):
        f0 = fr[j]; i = sim_max(f0)
        out["straights"].append(dict(id=n, s_m=round(float(ref["s"][j]), 1), ref=round(float(ref["v"][j]), 1),
                                     sim=round(float(S["v"][i]), 1), err=round(float(S["v"][i] - ref["v"][j]), 1)))

    ref_min_idx = [int(np.argmin(np.abs(ref["s"] - cs))) for cs, _ in mins]
    for c, jm in zip(out["corners"], ref_min_idx):
        before = [j for j in pk if j < jm] or [pk[-1]]   # wrap: the last straight feeds corner 1
        jp = before[-1]
        # reference zone
        r_on = _onset(ref["v"], jp, jm, cfg["onset_drop_kmh"])
        r_dec = _rate(ref["v"][jp], ref["v"][jm], ref["t"][jp], ref["t"][jm])
        # sim zone: its own peak/min near the reference ones
        ip, im = sim_max(fr[jp]), sim_min(fr[jm])
        s_on = _onset(S["v"], ip, im, cfg["onset_drop_kmh"])
        s_dec = _rate(S["v"][ip], S["v"][im], S["t"][ip], S["t"][im])
        on_ref_f = fr[r_on] if r_on is not None else None
        on_sim_f = S["f"][s_on] if s_on is not None else None
        d_on = None if on_ref_f is None or on_sim_f is None else _dfrac(on_sim_f, on_ref_f) * L
        for lo_b, hi_b in cfg["brake_bands"]:
            rb = _band_rate(ref["v"], ref["t"], _span(jp, jm, len(ref["v"])), lo_b, hi_b, down=True)
            sb = _band_rate(S["v"], S["t"], _span(ip, im, len(S["v"])), lo_b, hi_b, down=True)
            if rb and sb:
                out["brake_bands"].append(dict(id=c["id"], band=[lo_b, hi_b], ref=round(rb, 1), sim=round(sb, 1),
                                               err_pct=round(100 * (sb / rb - 1), 1)))
        out["braking"].append(dict(id=c["id"], entry_ref=round(float(ref["v"][jp]), 1),
                                   onset_err_m=None if d_on is None else round(d_on, 1),
                                   decel_ref=round(r_dec, 1), decel_sim=round(s_dec, 1),
                                   decel_err_pct=round(100 * (s_dec / r_dec - 1), 1) if r_dec else None))
        # exit: corner minimum -> next straight peak
        after = [j for j in pk if j > jm] or [pk[0]]
        jn = after[0]
        r_acc = _gain(ref, jm, jn, cfg["exit_gain_kmh"], fr)
        in_ = sim_max(fr[jn])
        s_acc = _gain(dict(v=S["v"], t=S["t"]), im, in_, cfg["exit_gain_kmh"], S["f"])
        for lo_b, hi_b in cfg["accel_bands"]:
            ra = _band_rate(ref["v"], ref["t"], _span(jm, jn, len(ref["v"])), lo_b, hi_b, down=False)
            sa = _band_rate(S["v"], S["t"], _span(im, in_, len(S["v"])), lo_b, hi_b, down=False)
            if ra and sa:
                out["accel_bands"].append(dict(id=c["id"], band=[lo_b, hi_b], ref=round(ra, 1), sim=round(sa, 1),
                                               err_pct=round(100 * (sa / ra - 1), 1)))
        out["exits"].append(dict(id=c["id"], vmin_ref=c["ref"], acc_ref=None if r_acc is None else round(r_acc, 1),
                                 acc_sim=None if s_acc is None else round(s_acc, 1),
                                 acc_err_pct=None if not (r_acc and s_acc) else round(100 * (s_acc / r_acc - 1), 1)))
    return out


def _band_rate(v, t, idx, lo, hi, down):
    """Mean rate (km/h/s) while speed crosses the band [lo, hi] once along idx (interpolated crossings)."""
    a, b = (hi, lo) if down else (lo, hi)
    ta = tb = None
    for i0, i1 in zip(idx[:-1], idx[1:]):
        v0, v1, t0, t1 = v[i0], v[i1], t[i0], t[i1]
        if t1 <= t0:
            t1 = t0 + 1e-9
        for edge in (a, b):
            if (v0 - edge) * (v1 - edge) <= 0 and v0 != v1:
                te = t0 + (edge - v0) / (v1 - v0) * (t1 - t0)
                if edge == a and ta is None:
                    ta = te
                elif edge == b and ta is not None and tb is None and te > ta:
                    tb = te
    if ta is None or tb is None or tb <= ta:
        return None
    return (hi - lo) / (tb - ta)


def _dfrac(a, b):
    d = a - b
    return d - round(d)


def _onset(v, ip, im, drop):
    idx = _span(ip, im, len(v))
    for i in idx:
        if v[i] < v[ip] - drop:
            return i
    return None


def _span(i0, i1, n):
    return list(range(i0, i1 + 1)) if i1 >= i0 else list(range(i0, n)) + list(range(0, i1 + 1))


def _rate(v0, v1, t0, t1):
    dt = (t1 - t0) if t1 > t0 else None
    return float((v0 - v1) / dt) if dt else 0.0


def _gain(tr, im, ip, gain, f):
    """Mean acceleration from the minimum to (minimum + gain) km/h along the exit."""
    v, t = tr["v"], tr["t"]
    idx = _span(im, ip, len(v)); v0, t0 = v[im], t[im]
    for i in idx[1:]:
        if v[i] >= v0 + gain:
            dt = t[i] - t0 if t[i] > t0 else None
            return float(gain / dt) if dt else None
    return None


def sectors(sim, ref_sector_s, ref):
    """Sim time per official sector; boundaries = reference distance at the official split times."""
    fr = _frac(ref); cum = np.cumsum(ref_sector_s)[:-1]
    b = [float(np.interp(c, ref["t"], fr)) for c in cum]
    fs = _frac(sim); ts = [0.0] + [float(np.interp(x, fs, sim["t"])) for x in b] + [float(sim["t"][-1])]
    return b, [round(ts[k + 1] - ts[k], 3) for k in range(len(ts) - 1)]


def signature(csv_path):
    """GAIN / DROP / SUPERCLIP rate metrics exactly as cache/_gate_2026.py computes them."""
    t, v, th, br, s = GATE.load(csv_path)
    r = GATE.rate_kmh_s(t, v); top = v.max()
    gain = np.abs(r[(th > 80) & (br < 5) & (v < 0.88 * top) & (r > 2)])
    drop = np.abs(r[(br > 15) & (r < -2)])
    near = (th > 90) & (br < 5) & (v > 0.85 * top); clip = np.abs(r[near & (r < -1)])
    return dict(gain_med=float(np.median(gain)) if len(gain) else 0.0, gain_peak=float(gain.max()) if len(gain) else 0.0,
                drop_med=float(np.median(drop)) if len(drop) else 0.0, drop_peak=float(drop.max()) if len(drop) else 0.0,
                superclip_frac=len(clip) / max(int(near.sum()), 1), superclip_peak=float(clip.max()) if len(clip) else 0.0)


def median_abs(xs):
    xs = [abs(x) for x in xs if x is not None]
    return float(np.median(xs)) if xs else None


def median(xs):
    xs = [x for x in xs if x is not None]
    return float(np.median(xs)) if xs else None


def clip_zones(d, t, v, thr, min_len_m=20.0, join_m=40.0, v_min=200.0):
    """Where the car clips: full throttle, no lift, speed falling on a straight (the only ERS evidence in
    OpenF1 data - it publishes no deploy channel). Returns [(start_m, end_m, v_start, v_end)]."""
    d, t, v, thr = (np.asarray(x, float) for x in (d, t, v, thr))
    idx = np.where((thr >= 98) & (np.gradient(v, t) < -2) & (v > v_min))[0]
    zones = []
    if len(idx):
        a = p = idx[0]
        for j in list(idx[1:]) + [None]:
            if j is None or d[j] - d[p] > join_m:
                if d[p] - d[a] >= min_len_m:
                    zones.append((float(d[a]), float(d[p]), float(v[a]), float(v[p])))
                if j is not None:
                    a = j
            if j is not None:
                p = j
    return zones


def segment_shapes(sim_csv, ref_csv, prominence_kmh, tol_rmse_kmh):
    """User rule 2026-10-23: match the speed SHAPE corner by corner, never trust the whole-lap correlation.
    The lap is cut at the reference's straight peaks (local maxima >= prominence); each segment holds one
    braking zone + corner(s) + exit. Per segment: RMSE and worst gap (km/h) on a common lap-fraction grid,
    and the time the sim loses (+) or gains (-) there. ok = RMSE <= tol."""
    import pandas as pd
    from scipy.signal import find_peaks
    s, r = pd.read_csv(sim_csv), pd.read_csv(ref_csv)
    L = float(s.distance.iloc[-1])
    g = np.linspace(0.0, L, 4000, endpoint=False)
    rd = r.distance.to_numpy(float) / float(r.distance.iloc[-1]) * L
    vs, vr = np.interp(g, s.distance, s.speed), np.interp(g, rd, r.speed)
    ts, tr = np.interp(g, s.distance, s.time_s), np.interp(g, rd, r.time_s)
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
                        worst_kmh=round(float(d[w]), 1), worst_at_m=round(float(g[a + w])),
                        time_s=round(float((ts[b] - ts[a]) - (tr[b] - tr[a])), 3), ok=bool(e <= tol_rmse_kmh)))
    return out


def clip_match(sim_csv, ref_csv, tol_m):
    """Spec D28: every reference clip zone needs a sim clip zone ending within tol_m and covering at least half
    of it; a sim clip zone with
    no reference partner is 'extra'. Distances on the sim's lap length."""
    import pandas as pd
    s, r = pd.read_csv(sim_csv), pd.read_csv(ref_csv)
    L = float(s.distance.iloc[-1])
    rd = r.distance.to_numpy(float) / float(r.distance.iloc[-1]) * L
    zs = clip_zones(s.distance, s.time_s, s.speed, s.throttle)
    zr = clip_zones(rd, r.time_s, r.speed, r.throttle)
    used, rows = set(), []
    for z in zr:
        j = next((i for i, x in enumerate(zs) if i not in used and abs(x[1] - z[1]) <= tol_m
                  and min(x[1], z[1]) - max(x[0], z[0]) >= 0.5 * (z[1] - z[0])), None)   # covers >= half of it
        if j is not None:
            used.add(j)
        x = zs[j] if j is not None else None
        rows.append(dict(ref_m=[round(z[0]), round(z[1])], ref_drop_kmh=round(z[3] - z[2], 1),
                         sim_m=[round(x[0]), round(x[1])] if x else None,
                         sim_drop_kmh=round(x[3] - x[2], 1) if x else None, ok=x is not None))
    extra = [dict(sim_m=[round(x[0]), round(x[1])], sim_drop_kmh=round(x[3] - x[2], 1))
             for i, x in enumerate(zs) if i not in used]
    return dict(zones=rows, extra=extra, ok=all(z["ok"] for z in rows) and not extra)
