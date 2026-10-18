"""Fetch Baku lap references from the official F1 timing archive via FastF1."""
import json
from datetime import datetime, timezone
from pathlib import Path

import fastf1
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EXPORTS = ROOT / "F1_Pipeline_Assets" / "exports"
fastf1.Cache.set_disabled()

for year, session_name, suffix in [
    (2025, "Qualifying", "2025_baku_q"),
    (2026, "Practice 1", "2026_baku_fp1"),
    (2026, "Practice 2", "2026_baku_fp2"),
]:
    out = EXPORTS / f"reference_{suffix}.csv"
    provenance = ROOT / "cache" / f"reference_{suffix}_provenance.json"
    position_out = ROOT / "cache/baku_2025_q_position.csv" if year == 2025 else None
    complete = out.exists() and provenance.exists()
    if complete and (position_out is None or position_out.exists()):
        print(f"[baku] exists: {out.name}", flush=True)
        continue
    session = fastf1.get_session(year, "Azerbaijan", session_name, backend="f1timing")
    print(f"[baku] loading {session.api_path}", flush=True)
    session.load(laps=True, telemetry=True, weather=False, messages=False)
    lap = session.laps.pick_fastest()
    if position_out is not None and not position_out.exists():
        lap.get_pos_data().to_csv(position_out, index=False)
        print(f"[baku] wrote {position_out.name}", flush=True)
    if complete:
        continue
    tel = lap.get_telemetry()
    ref = pd.DataFrame(dict(
        frame=np.arange(len(tel)),
        time_s=tel["Time"].dt.total_seconds().round(3),
        distance=tel["Distance"].round(3),
        speed=tel["Speed"].round(3),
        throttle=tel["Throttle"].round(1),
        brake=tel["Brake"].astype(float) * 100.0,
        gear=tel["nGear"].round().astype(int),
        rpm=tel["RPM"].round().astype(int),
        ers_deploy=0,
    ))
    ref.to_csv(out, index=False)
    meta = dict(source="F1 official timing archive via FastF1", api_path=session.api_path,
                session=session_name, driver=str(lap["Driver"]),
                lap_number=int(lap["LapNumber"]),
                lap_duration_s=float(lap["LapTime"].total_seconds()),
                distance_m=float(ref.distance.iloc[-1]), samples=len(ref),
                fetched_utc=datetime.now(timezone.utc).isoformat(),
                fastf1_version=fastf1.__version__)
    provenance.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"[baku] {suffix}: {meta['driver']} {meta['lap_duration_s']:.3f}s, "
          f"{meta['distance_m']:.0f}m, {len(ref)} samples", flush=True)
