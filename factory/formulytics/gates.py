"""Procedural memory -> automated gates.

Each gate encodes one piece of feedback the human gave early on (see memory/procedural/
feedback_rules.md). Gates are deterministic, run on the run's artifacts, and FAIL CLOSED:
a missing artifact is a failure, and nothing reaches publish/ unless every blocking gate passes.
"""
import json
import math
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import config


@dataclass
class GateResult:
    gate: str
    rule: str
    passed: bool
    detail: str
    blocking: bool = True
    evidence: dict = field(default_factory=dict)


def _load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def gate_realism(state) -> GateResult:
    g = state.get("gate")
    if not g:
        return GateResult("realism", "R1", False, "engine realism gate never ran")
    fails = [c["check"] for c in g["checks"] if not c["pass"]]
    return GateResult("realism", "R1", bool(g["all_pass"]),
                      f"{len(g['checks']) - len(fails)}/{len(g['checks'])} engine checks pass"
                      + (f"; failing: {fails}" if fails else ""), evidence={"checks": g["checks"]})


def gate_no_api_xy(state) -> GateResult:
    """Track geometry must come from the SVG-derived outline, never from API car x/y."""
    w = state.get("weekend") or {}
    src = json.dumps(w.get("sim", {})).lower()
    bad = [k for k in ("position", "location_xy", "openf1_xy", "car_xy") if k in src]
    ok = bool(w) and "outline" in w.get("sim", {}) and not bad
    return GateResult("no_api_xy", "R2", ok, "geometry from SVG outline" if ok else f"API x/y source found: {bad}")


def _nearest(poly, p):
    best = (1e18, None)
    for q in poly:
        d = (q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2
        if d < best[0]:
            best = (d, q)
    return math.sqrt(best[0]), best[1]


def _inside_gap(pts, kap_sign, i, edges):
    n = len(pts)
    a, b = pts[(i - 2) % n], pts[(i + 2) % n]
    nx, ny = -(b[1] - a[1]), b[0] - a[0]  # left normal = inside of a left turn (kappa > 0)
    if kap_sign < 0:
        nx, ny = -nx, -ny
    inside = None
    for edge in edges:
        d, q = _nearest(edge, pts[i])
        if (q[0] - pts[i][0]) * nx + (q[1] - pts[i][1]) * ny > 0:
            inside = d if inside is None else min(inside, d)
    return inside


def apex_distances(raceline_json, outline_json, kappa_min=1 / 120, window=25, search=15):
    """Per corner (local max of |kappa|): closest approach of the line centre to the INSIDE
    edge within +-search points (~+-30 m) of the curvature peak = the apex."""
    rl, ol = _load(raceline_json), _load(outline_json)
    pts, kap = rl["raceline"], rl["kappa"]
    edges = (ol["outer"], ol["inner"])
    n, out = len(pts), []
    for i in range(n):
        k = abs(kap[i])
        if k < kappa_min or k < max(abs(kap[(i + j) % n]) for j in range(-window, window + 1)):
            continue
        gaps = [(g, (i + j) % n) for j in range(-search, search + 1)
                if (g := _inside_gap(pts, kap[i], (i + j) % n, edges)) is not None]
        if gaps:
            g, at = min(gaps)
            out.append({"idx": i, "apex_idx": at, "radius_m": round(1 / k, 1), "inside_gap_m": round(g, 2)})
    return out


def gate_apex_touch(state, max_gap_m=1.5, min_frac=0.8) -> GateResult:
    """User rejects wide/mid-track apexes: the line must touch the inside kerb."""
    s, w = state.get("sim"), state.get("weekend")
    if not s or not s.get("raceline_sim_frame") or not w:
        return GateResult("apex_touch", "R3", False, "no raceline to check")
    outline = config.ENGINE_ROOT / w["sim"]["outline"]
    ap = apex_distances(s["raceline_sim_frame"], outline)
    if not ap:
        return GateResult("apex_touch", "R3", False, "no apexes detected")
    touch = [a for a in ap if a["inside_gap_m"] <= max_gap_m]
    frac = len(touch) / len(ap)
    return GateResult("apex_touch", "R3", frac >= min_frac,
                      f"{len(touch)}/{len(ap)} apexes within {max_gap_m} m of the inside edge "
                      f"(want >= {int(min_frac * 100)}%)", evidence={"apexes": ap})


def gate_real_trace(state, min_corr=0.94) -> GateResult:
    """Car must be measured from real traces, not fitted to lap time alone: the speed TRACE
    must correlate with the real reference trace, not just the lap number."""
    c = state.get("trace_check")
    if not c:
        return GateResult("real_trace", "R4", False, "no trace comparison ran")
    return GateResult("real_trace", "R4", c["speed_corr"] >= min_corr,
                      f"speed-trace corr {c['speed_corr']} vs {c.get('reference', 'reference')} (want >= {min_corr})",
                      evidence=c)


def gate_zoom(state) -> GateResult:
    """Videos render at zoom 28 unless the human set a per-track exception (documented note)."""
    w = state.get("weekend") or {}
    r = w.get("render", {})
    z = state.get("render_zoom", r.get("zoom", 28))
    ok = z == 28 or (z == r.get("zoom") and bool(r.get("zoom_note")))
    return GateResult("zoom", "R5", ok, f"zoom {z}" + (f" (exception: {r.get('zoom_note')})" if z != 28 else ""))


def gate_no_inflation(state) -> GateResult:
    """Displayed lap time = simulated lap time unless a human decision says otherwise."""
    s, label = state.get("sim"), state.get("label_s")
    if not s or label is None:
        return GateResult("no_inflation", "R6", False, "no label to check")
    ok = abs(label - s["lap_s"]) < 0.0005
    return GateResult("no_inflation", "R6", ok, f"label {label} vs sim {s['lap_s']}")


# every number, including single digits; numbers glued to letters ("F1", "MGU-K2") are names, not claims
_NUM = re.compile(r"(?<![A-Za-z\d.:])(?:\d+:\d{2}\.\d{1,3}|\d+\.\d+|\d+)(?!\d|[.:]\d)")


def _fmt_variants(x: float):
    out = {f"{x:.3f}", f"{x:.2f}", f"{x:.1f}", f"{x:.0f}"}
    if x >= 60:
        m, s = divmod(x, 60)
        out |= {f"{int(m)}:{s:06.3f}", f"{int(m)}:{s:05.2f}"}
    return out


def gate_claims_supported(state) -> GateResult:
    """Guardrail: every number in the caption must exist in the run's verified facts."""
    cap = state.get("caption")
    if not cap:
        return GateResult("claims_supported", "R7", False, "no caption")
    allowed = set()
    for v in state.get("facts", {}).values():
        if isinstance(v, (int, float)):
            allowed |= _fmt_variants(float(v))
    y = state.get("weekend", {}).get("year")
    if y:  # the season and the reference season are context, not claims
        allowed |= {str(y), str(y - 1)}
    nums = _NUM.findall(cap["text"] + " " + " ".join(cap.get("tags", [])))
    unsupported = [n for n in nums if n not in allowed]
    return GateResult("claims_supported", "R7", not unsupported,
                      "all numbers trace to run facts" if not unsupported else f"unsupported numbers: {unsupported}",
                      evidence={"numbers": nums})


def gate_delta_engine(state) -> GateResult:
    """Driver comparisons use hifi_delta_v2.py, never the old notebook-cell delta_engine_v2.py."""
    d = state.get("delta")
    if d is None:
        return GateResult("delta_engine", "R8", True, "no driver comparison in this run", blocking=False)
    ok = d.get("engine", "").endswith("hifi_delta_v2.py")
    return GateResult("delta_engine", "R8", ok, f"engine {d.get('engine')}")


GATES = [gate_realism, gate_no_api_xy, gate_apex_touch, gate_real_trace, gate_zoom,
         gate_no_inflation, gate_claims_supported, gate_delta_engine]


def run_all(state) -> dict:
    res = [g(state) for g in GATES]
    blocking_fail = [r.gate for r in res if r.blocking and not r.passed]
    return {"all_pass": not blocking_fail, "blocking_failures": blocking_fail, "results": [asdict(r) for r in res]}
