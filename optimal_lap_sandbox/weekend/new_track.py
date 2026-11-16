"""A new track writes its own notes (ticket 15): card + fetched facts + formulas -> two note files.

  python -m weekend.new_track austin 2026          # writes the notes if missing (fetches first if needed)

Inputs, and nothing else:
  weekend/cards/<track>.yaml      hand-written facts (name, length, direction, altitude, street), each with a source
  cache/<track>/fetch_facts.json  OpenF1 facts from weekend/fetch_weekend.py (run here if missing)
Outputs (never overwritten - an existing note is the user's or an earlier run's):
  weekend/notes/track/<track>_<year>_layout.yaml   track layer
  weekend/notes/weekend/<track>_<year>.yaml        weekend layer
Car numbers (CdA, CL) come from the car note and grip from 1.0; the tune stage fits them (FITTED in its output).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import date

import numpy as np
import yaml

from weekend import features as F
from weekend.resolve import ROOT

SIM_GAIN_GUARD = 32.0      # sim_2026_lap.py fixed GAIN-median guard upper bound [12, 32] km/h/s
SIM_REAL_GAIN_RATIO = 1.52  # max shipped sim/real gain ratio (cache/_sim_singapore.py)


def paths(track, year):
    return (os.path.join(ROOT, "weekend", "notes", "track", f"{track}_{year}_layout.yaml"),
            os.path.join(ROOT, "weekend", "notes", "weekend", f"{track}_{year}.yaml"))


def load_card(track):
    with open(os.path.join(ROOT, "weekend", "cards", f"{track}.yaml"), encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def ensure_facts(track, year, card):
    f = os.path.join(ROOT, "cache", track, "fetch_facts.json")
    if not os.path.exists(f) or f"q{year - 1}" not in json.load(open(f, encoding="utf-8")):
        o = card["openf1"]
        subprocess.run([sys.executable, "-m", "weekend.fetch_weekend", track, str(year), "--country", o["country"],
                        "--circuit", o["circuit"]], cwd=ROOT, check=True)
    with open(f, encoding="utf-8") as fh:
        return json.load(fh)


def _rel(p):
    return os.path.relpath(p, ROOT).replace("\\", "/")


def clip_zones_ref(csv_path):
    """Real clip zones as the sim reads them: [frac_start, frac_end, rate_kmh_s], rounded (stable notes)."""
    import pandas as pd
    r = pd.read_csv(csv_path)
    L = float(r.distance.iloc[-1])
    out = []
    for a, b, va, vb in F.clip_zones(r.distance, r.time_s, r.speed, r.throttle):
        ta, tb = (float(np.interp(x, r.distance, r.time_s)) for x in (a, b))
        out.append([round(a / L, 4), round(b / L, 4), round((vb - va) / (tb - ta), 2)])
    return out


def notes_for(track, year, card, facts):
    """Return (track_note, weekend_note) dicts. Pure: no file writes."""
    prev = year - 1
    q, fp1 = facts[f"q{prev}"], facts.get(f"fp1_{year}")
    q_csv = os.path.join(ROOT, "F1_Pipeline_Assets", "exports", f"reference_{prev}_{track}_q.csv")
    fetched = f"weekend/fetch_weekend.py, fetched {facts.get('fetched', '?')}"
    street = bool(card["street"]["value"])
    gain_med = F.signature(q_csv)["gain_med"]
    gain_cap = round(max(SIM_GAIN_GUARD, gain_med * SIM_REAL_GAIN_RATIO), 1)
    alt = float(card["altitude_m"]["value"])
    rho = round(1.225 * (1 - 2.25577e-5 * alt) ** 4.2561, 4)
    tv = {
        "track.path_samples_file": dict(value=f"cache/{track}/path_samples.json", file=True, origin="MEASURED",
            source=f"OpenF1 location, {prev} {track} Q (session {q['session_key']}), fastest valid lap of the top-10 drivers ({fetched})"),
        "track.path_ref_driver": dict(value=q["driver"], origin="MEASURED",
            source=f"driver of the fastest {prev} Q lap ({q['lap_s']} s); his lap start = the official timing line"),
        "ref.q2025_csv_file": dict(value=_rel(q_csv), file=True, origin="MEASURED",
            source=f"OpenF1 {prev} {track} Q fastest lap, driver {q['driver']} ({fetched})"),
        "ref.q2025_lap_s": dict(value=q["lap_s"], unit="s", origin="MEASURED",
            source=f"OpenF1 lap_duration, {prev} {track} Q pole lap (session {q['session_key']}, lap {q['lap_number']})"),
        "track.length_m": dict(value=float(card["length_m"]["value"]), unit="m", origin="KNOWLEDGE",
            source=card["length_m"]["source"]),
        "track.mirror_x": dict(value=card["direction"]["value"] == "anticlockwise", origin="COMPUTED",
            source=f"{card['direction']['value']} ({card['direction']['source']}); the engine drives clockwise, "
                   "so an anticlockwise track runs on the x-mirror (physics is left/right symmetric)"),
        "track.width_m": dict(value=12.0, unit="m", origin="COMPUTED",
            source="no width fit for this track yet: the as-built width (season track.asbuilt_width_m)"),
        "line.base_inset_m": dict(value=1.0 if street else 0.0, unit="m", origin="COMPUTED",
            source="raceline_video.build_centerline_and_widths: 1.0 wall-safe for street circuits, "
                   "0.0 for run-off circuits" + f" ({card['street']['source']})"),
        "track.street_grip_k": dict(value=1.0, origin="COMPUTED",
            source="start value 1.0 = the sim's own grip; the tune stage fits it against the slow corners"),
        "sim.gain_cap_kmh_s": dict(value=gain_cap, unit="km/h/s", origin="COMPUTED",
            source=f"max(sim guard {SIM_GAIN_GUARD}, real {prev} Q gain median {gain_med:.1f} x {SIM_REAL_GAIN_RATIO}) "
                   "(weekend.features.signature)"),
        "video.track_name": dict(value=card["event_name"]["value"], origin="KNOWLEDGE",
            source=card["event_name"]["source"]),
    }
    wv = {
        "RHO": dict(value=rho, unit="kg/m^3", origin="COMPUTED",
            source=f"ISA at altitude {alt:g} m ({card['altitude_m']['source']}): 1.225*(1-2.25577e-5 h)^4.2561"),
        "WARM_RHO": dict(value=rho, unit="kg/m^3", origin="COMPUTED", source="the sim forces WARM_RHO = RHO"),
    }
    if not street:
        tv["fit.range.track.street_grip_k"] = dict(value=[1.0, 1.0], origin="COMPUTED",
            source="street-grip factor applies to street circuits only (spec ticket 17); fixed at 1.0 here "
                   f"({card['street']['source']})")
    if fp1:
        fp1_csv = os.path.join(ROOT, "F1_Pipeline_Assets", "exports", f"reference_{year}_{track}_fp1.csv")
        wv["shape.enabled"] = dict(value=True, origin="USER_DECISION", decided="2026-10-24",
            reason="user 2026-10-24: with FP1, fit the speed pattern section by section (shape_fit stage)")
        wv["CLIP_ZONES"] = dict(value=json.dumps(clip_zones_ref(fp1_csv)), origin="COMPUTED",
            source=f"weekend.features.clip_zones on the {year} FP1 speed trace (full throttle, speed falling): "
                   "[lap fraction start, end, km/h per s] per zone (spec D28)")
        wv.update({
            "ref.fp1_csv_file": dict(value=_rel(fp1_csv), file=True, origin="MEASURED",
                source=f"OpenF1 car_data, {year} {track} FP1 fastest lap, driver {fp1['driver']} ({fetched})"),
            "ref.fp1_lap_s": dict(value=fp1["lap_s"], unit="s", origin="MEASURED",
                source=f"OpenF1 lap_duration, {year} {track} FP1 fastest lap (session {fp1['session_key']}, lap {fp1['lap_number']})"),
            "ref.fp1_sectors_s": dict(value=fp1["sectors_s"], unit="s", origin="MEASURED",
                source=f"OpenF1 laps, {year} {track} FP1 (session {fp1['session_key']}) sector times"),
        })
    scope = dict(track=track, year=year)
    tn = dict(id=f"track/{track}_{year}_layout", layer="track", scope=scope, links=[f"weekend/{track}_{year}"], values=tv)
    wn = dict(id=f"weekend/{track}_{year}", layer="weekend", scope=scope,
              links=[f"track/{track}_{year}_layout", "car/f1_2026_car"], values=wv)
    return tn, wn


def ensure_notes(track, year) -> list[str]:
    """Write the two notes for a track that has none. Returns the files written (empty if both exist)."""
    targets = paths(track, year)
    if all(os.path.exists(p) for p in targets):
        return []
    card = load_card(track)
    notes = notes_for(track, year, card, ensure_facts(track, year, card))
    written = []
    for p, note in zip(targets, notes):
        if os.path.exists(p):
            continue
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(f"# generated by weekend/new_track.py on {date.today()} "
                     f"from weekend/cards/{track}.yaml + cache/{track}/fetch_facts.json\n")
            yaml.safe_dump(note, fh, sort_keys=False, allow_unicode=True, width=200)
        written.append(_rel(p))
    return written


if __name__ == "__main__":
    print(ensure_notes(sys.argv[1], int(sys.argv[2])))
