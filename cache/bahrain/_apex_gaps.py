"""Per-corner inside-apex gap of an _opt_line_2026 knot vector: corners = |kappa| peaks (R<250 m) of the line;
gap = min over a +-W m window of the distance from the line to the INSIDE corridor bound (road - margin).
Used both as a report and (apex_terms) as the optimiser's apex-touch penalty."""
import numpy as np, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "era2017"))
import _opt_line_2017 as O


def corners(rl, arc, L, rmax=250.0, sep=120.0, st=8):
    n = len(rl); kap = np.zeros(n)
    for i in range(n):
        p0, p1, p2 = rl[i - st], rl[i], rl[(i + st) % n]; u, v = p1 - p0, p2 - p1
        kap[i] = 2*(u[0]*v[1]-u[1]*v[0])/(np.linalg.norm(u)*np.linalg.norm(v)*np.linalg.norm(p2-p0))
    peaks = []
    for i in np.argsort(-np.abs(kap)):
        if abs(kap[i]) < 1/rmax: break
        if all(min(abs(arc[i]-arc[j]), L-abs(arc[i]-arc[j])) > sep for j in peaks): peaks.append(i)
    return sorted(peaks), kap


def apex_terms(off, peaks, kap, win):
    """gap per corner: inside = +N (hi) for kappa>0 else -N (lo)."""
    G = O.G; out = []
    for i in peaks:
        idx = np.arange(i - win, i + win + 1) % len(off)
        g = (G["hi"][idx] - off[idx]) if kap[i] > 0 else (off[idx] - G["lo"][idx])
        out.append(float(g.min()))
    return np.array(out)
