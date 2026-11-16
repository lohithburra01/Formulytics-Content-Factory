"""Build the golden dataset: every shipped 2026 optimal lap vs what really happened.

Shipped values come from the project's run logs (memory notes, make_*.bat). Real values are
fetched from OpenF1 (qualifying classification, laps, weather). A dry simulation is only
scored against a dry lap: if qualifying was wet, the comparable reference is the fastest
dry lap of the weekend and the row says so.

    python evals/build_golden.py   ->  evals/golden.json
"""
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

OPENF1 = "https://api.openf1.org/v1/"

# stage = how much 2026 session data the prediction had seen before it shipped
SHIPPED = [
    {"id": "bahrain_2026", "location": "Sakhir", "sim_s": 92.186, "stage": "pre-FP1"},
    {"id": "spa_2026", "location": "Spa", "sim_s": 101.91, "stage": "pre-FP1"},
    {"id": "silverstone_2026", "location": "Silverstone", "sim_s": 87.97, "stage": "post-FP1"},
    {"id": "monaco_2026", "location": "Monte Carlo", "sim_s": 71.77, "stage": "post-FP1"},
    {"id": "madring_2026", "location": "Madrid", "sim_s": 92.363, "stage": "post-FP2"},
    {"id": "singapore_2026", "location": "Marina Bay", "sim_s": 93.01, "stage": "pre-FP1"},
    {"id": "sepang_2026", "location": "Kuala Lumpur", "sim_s": 91.838, "stage": "pre-FP1 (no-reference method)"},
    {"id": "mexico_2026", "location": "Mexico City", "sim_s": 76.758, "stage": "pre-FP1", "label_s": 77.265},
    {"id": "sao_paulo_2026", "location": "Paulo", "sim_s": 70.772, "stage": "pre-FP1"},
]


def get(ep, **params):
    url = OPENF1 + ep + "?" + urllib.parse.urlencode(params)
    for attempt in range(6):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "formulytics-factory/0.1"})
            with urllib.request.urlopen(req, timeout=60) as r:
                d = json.load(r)
            if isinstance(d, list):
                return d
        except Exception:  # noqa: BLE001 - rate limit / transient
            pass
        time.sleep(2 + 3 * attempt)
    raise RuntimeError(f"OpenF1 failed: {url}")


def session_facts(s):
    laps = [l for l in get("laps", session_key=s["session_key"]) if l.get("lap_duration")]
    wx = get("weather", session_key=s["session_key"])
    rain = sum(1 for w in wx if w.get("rainfall"))
    best = min(laps, key=lambda l: l["lap_duration"]) if laps else None
    return {"session": s["session_name"], "session_key": s["session_key"],
            "best_lap_s": best["lap_duration"] if best else None,
            "best_driver_number": best["driver_number"] if best else None,
            "rain_frac": round(rain / len(wx), 2) if wx else None}


def main():
    rows = []
    sessions = get("sessions", year=2026)
    for w in SHIPPED:
        ss = [s for s in sessions if w["location"].lower() in (s["location"] + "|" + s["circuit_short_name"]).lower()
              and s["session_name"] in ("Practice 1", "Practice 2", "Practice 3", "Qualifying")
              and not s.get("is_cancelled")]
        row = dict(w)
        if not ss:
            row.update(real=None, note="no real 2026 session in OpenF1 (event cancelled or not held)")
            rows.append(row)
            continue
        facts = [session_facts(s) for s in sorted(ss, key=lambda s: s["date_start"])]
        q = next((f for f in facts if f["session"] == "Qualifying"), None)
        pole = None
        if q:
            res = [r for r in get("session_result", session_key=q["session_key"]) if str(r.get("position")) == "1"]
            if res:
                dur = res[0].get("duration")
                pole = {"driver_number": res[0]["driver_number"],
                        "lap_s": min(x for x in dur if x) if isinstance(dur, list) else dur}
        q_dry = q is not None and (q["rain_frac"] or 0) < 0.1
        dry = [f for f in facts if f["best_lap_s"] and (f["rain_frac"] or 0) < 0.1]
        best_dry = min(dry, key=lambda f: f["best_lap_s"]) if dry else None
        if q_dry and pole:
            ref, ref_kind = pole["lap_s"], "qualifying pole (dry)"
        elif best_dry:
            ref, ref_kind = best_dry["best_lap_s"], f"fastest dry lap of the weekend ({best_dry['session']}); qualifying was wet"
        else:
            ref, ref_kind = None, "no dry lap to compare"
        row.update(real={"sessions": facts, "q_pole": pole, "q_wet": not q_dry},
                   ref_s=ref, ref_kind=ref_kind,
                   err_s=round(w["sim_s"] - ref, 3) if ref else None,
                   err_pct=round(100 * (w["sim_s"] - ref) / ref, 2) if ref else None)
        rows.append(row)
        print(w["id"], row.get("ref_s"), row.get("err_s"), ref_kind)
    out = Path(__file__).with_name("golden.json")
    out.write_text(json.dumps({"built": time.strftime("%Y-%m-%d"), "source": "OpenF1", "rows": rows}, indent=1))
    print("wrote", out)


if __name__ == "__main__":
    main()
