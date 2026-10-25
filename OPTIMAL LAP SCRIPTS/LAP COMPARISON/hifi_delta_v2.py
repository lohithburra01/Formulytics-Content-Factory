"""
F1 LAP DELTA ENGINE

One method: F1InsightsHub's alignData, ported exactly (f1ih_port.py, next to this file),
fed from FastF1 car data (lap.get_car_data(interpolate_edges=True), the same data
their backend serves). No position data is used. It reproduces their CSV exports
exactly (checked in the DELTA RECREATION repo, experiments/r25_engine_check.py).

Usage
    from hifi_delta_v2 import get_trace, calculate_delta

    ref = get_trace(session, 'VER')       # first driver = reference (zero line)
    tgt = get_trace(session, 'LEC')
    dist, delta = calculate_delta(ref, tgt)

    # without FastF1 (F1's archive returns 401 since 2026-10-15): F1IH backend car data + OpenF1 laps
    ref = get_trace_f1ih(2026, 'United States', 'Qualifying', 'NOR')
    tgt = get_trace_f1ih(2026, 'United States', 'Qualifying', 'VER')

    dist   their distance grid along the lap, metres
    delta  seconds, + = target slower
"""

import os
import re
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f1ih_port as fp

__all__ = ['get_trace', 'get_trace_f1ih', 'f1ih_session', 'f1ih_classification', 'f1ih_ranking', 'calculate_delta']

def _secs(x):
    return x.total_seconds() if pd.notna(x) else None

def get_trace(session, driver, lap=None):
    """Trace dict for the driver's fastest lap (or the given FastF1 Lap)."""
    if lap is None:
        laps = session.laps.pick_drivers(driver)
        if laps.empty: return None
        lap = laps.pick_fastest()
    if lap is None or (hasattr(lap, 'empty') and lap.empty): return None
    if pd.isna(lap['LapTime']): return None
    car = lap.get_car_data(interpolate_edges=True)
    if car.empty: return None

    ms = (session.t0_date + car['SessionTime']).astype('datetime64[ns]').astype('int64') // 10**6
    meta = dict(lapDuration=_secs(lap['LapTime']), lapDurationS1=_secs(lap['Sector1Time']),
                lapDurationS2=_secs(lap['Sector2Time']), lapNumber=int(lap['LapNumber']), position=None)
    samples = [dict(_ms=float(t), speed=float(v), throttle=float(th), brake=int(bool(br)), rpm=float(r),
                    nGear=int(g), drs=int(dr), **meta)
               for t, v, th, br, r, g, dr in zip(ms, car['Speed'], car['Throttle'], car['Brake'],
                                                  car['RPM'], car['nGear'], car['DRS'])]

    full_name = driver
    try:
        full_name = str(session.get_driver(driver)['FullName'])
    except Exception:
        pass

    return {'driver': driver, 'full_name': full_name, 'lap_number': int(lap['LapNumber']),
            'lap_time': lap['LapTime'].total_seconds(), 'samples': samples}

OPENF1 = 'https://api.openf1.org/v1/'
F1IH_CAR = 'https://backend.f1insightshub.com/fastf1/car_data'
SESSION_CODES = {'Q': 'Qualifying', 'SQ': 'Sprint Qualifying', 'R': 'Race', 'S': 'Sprint',
                 'FP1': 'Practice 1', 'FP2': 'Practice 2', 'FP3': 'Practice 3'}

_GET_CACHE = {}

def _get(url, params):
    """GET json, memoised per run (OpenF1 allows 30 requests/minute; 429 -> wait and retry)."""
    import requests, time
    key = (url, tuple(sorted(params.items())))
    if key in _GET_CACHE: return _GET_CACHE[key]
    for i in range(8):
        r = requests.get(url, params=params, timeout=180)
        if r.status_code == 200:
            _GET_CACHE[key] = r.json(); return _GET_CACHE[key]
        time.sleep(10 if r.status_code == 429 else 3)
    raise RuntimeError(f'{url} {params} -> HTTP {r.status_code} {r.text[:120]}')

def f1ih_session(year, gp, session_name):
    """(OpenF1 session, OpenF1 meeting) for the most recent session of that name that has run.
    gp: country, location or meeting name ('United States', 'Austin', 'Singapore Grand Prix');
    session_name: 'Qualifying', 'Practice 1', ... or a code ('Q', 'SQ', 'FP1', ...)."""
    session_name = SESSION_CODES.get(str(session_name).upper(), session_name)
    all_ses = _get(OPENF1 + 'sessions', {'year': year, 'session_name': session_name})
    ses = [s for s in all_ses if gp.lower() in (s['country_name'] + '|' + s['location']).lower()]
    if not ses:   # match on meeting name instead
        keys = {m['meeting_key'] for m in _get(OPENF1 + 'meetings', {'year': year}) if gp.lower() in m['meeting_name'].lower()}
        ses = [s for s in all_ses if s['meeting_key'] in keys]
    ses = [s for s in ses if pd.Timestamp(s['date_start']) <= pd.Timestamp.now(tz='UTC')]   # 'United States' = Austin + Las Vegas
    if not ses: raise ValueError(f'no OpenF1 session {year} {gp} {session_name} (yet)')
    ses = max(ses, key=lambda s: s['date_start'])   # most recent one that has run
    return ses, _get(OPENF1 + 'meetings', {'meeting_key': ses['meeting_key']})[0]

def deleted_laps(session_key):
    """{(driver_number, lap_number)} deleted by race control (track limits etc.); OpenF1 /laps doesn't flag them.
    Race control's 'LAP n' isn't OpenF1's lap number (US GP 2026 Q: VER 'TIME 1:34.482 ... LAP 12' = OpenF1 lap 11),
    so the lap is matched by its time, or (no time given) as the driver's last lap finished before the message."""
    laps = [l for l in _get(OPENF1 + 'laps', {'session_key': session_key}) if l.get('lap_duration') and l.get('date_start')]
    out = set()
    for m in _get(OPENF1 + 'race_control', {'session_key': session_key}):
        g = re.search(r'CAR (\d+) .*DELETED', m.get('message') or '')
        if not g: continue
        mine = [l for l in laps if l['driver_number'] == int(g.group(1))]
        t = re.search(r'TIME (\d+):(\d+\.\d+)', m['message'])
        if t:
            secs = int(t.group(1)) * 60 + float(t.group(2))
            hit = [l for l in mine if abs(l['lap_duration'] - secs) < 0.0005]
        else:
            end = lambda l: pd.Timestamp(l['date_start']) + pd.Timedelta(seconds=l['lap_duration'])
            hit = sorted([l for l in mine if end(l) <= pd.Timestamp(m['date'])], key=end)[-1:]
        out.update((l['driver_number'], l['lap_number']) for l in hit)
    return out

def f1ih_classification(year, gp, session_name):
    """Driver codes in official classified order (OpenF1 /session_result; for qualifying = the grid order,
    Q3 decides the top 10, not the fastest lap of the whole session). Falls back to f1ih_ranking."""
    ses, _ = f1ih_session(year, gp, session_name)
    code = {x['driver_number']: x['name_acronym'] for x in _get(OPENF1 + 'drivers', {'session_key': ses['session_key']})}
    try:
        res = [r for r in _get(OPENF1 + 'session_result', {'session_key': ses['session_key']}) if str(r.get('position') or '').isdigit()]
    except RuntimeError:
        res = []
    if not res: return [d for d, _ in f1ih_ranking(year, gp, session_name)]
    return [code[r['driver_number']] for r in sorted(res, key=lambda r: int(r['position'])) if r['driver_number'] in code]

def f1ih_ranking(year, gp, session_name):
    """[(driver code, fastest lap s)] for the session, fastest first (OpenF1 laps)."""
    ses, _ = f1ih_session(year, gp, session_name)
    code = {x['driver_number']: x['name_acronym'] for x in _get(OPENF1 + 'drivers', {'session_key': ses['session_key']})}
    best, gone = {}, deleted_laps(ses['session_key'])
    for l in _get(OPENF1 + 'laps', {'session_key': ses['session_key']}):
        if l.get('lap_duration') and l['driver_number'] in code and (l['driver_number'], l['lap_number']) not in gone:
            best[code[l['driver_number']]] = min(best.get(code[l['driver_number']], 1e9), l['lap_duration'])
    return sorted(best.items(), key=lambda kv: kv[1])

def get_trace_f1ih(year, gp, session_name, driver, lap_number=None):
    """Same trace as get_trace, without FastF1: car data from F1InsightsHub's backend
    (backend.f1insightshub.com/fastf1/car_data, what their site uses) and lap/sector times
    from OpenF1 /laps (what their site uses). gp / session_name as in f1ih_session.
    lap_number=None picks the driver's fastest lap that wasn't deleted. Extra keys: 'car' (backend rows:
    date, distance m, speed km/h, ...), 'lap' (OpenF1 lap), 'event' (meeting name)."""
    ses, meet = f1ih_session(year, gp, session_name)
    d = [x for x in _get(OPENF1 + 'drivers', {'session_key': ses['session_key']})
         if x['name_acronym'] == driver or str(x['driver_number']) == str(driver)]
    if not d: raise ValueError(f'driver {driver} not in session')
    d = d[0]
    laps = [l for l in _get(OPENF1 + 'laps', {'session_key': ses['session_key'], 'driver_number': d['driver_number']})
            if l.get('lap_duration')]
    gone = deleted_laps(ses['session_key'])
    valid = [l for l in laps if (l['driver_number'], l['lap_number']) not in gone]
    if not valid: return None
    lap = (min(valid, key=lambda l: l['lap_duration']) if lap_number is None
           else next(l for l in laps if l['lap_number'] == lap_number))
    car = _get(F1IH_CAR, {'driver_number': d['driver_number'], 'lap_number': lap['lap_number'],
                          'session_key': f"{year}|{meet['meeting_name']}|{ses['session_name']}"})
    if not car: return None

    ms = pd.to_datetime([c['date'] for c in car]).asi8 // 10**6
    meta = dict(lapDuration=lap['lap_duration'], lapDurationS1=lap['duration_sector_1'],
                lapDurationS2=lap['duration_sector_2'], lapNumber=lap['lap_number'], position=None)
    samples = [dict(_ms=float(t), speed=c['speed'], throttle=c['throttle'], brake=c['brake'], rpm=c['rpm'],
                    nGear=c['n_gear'], drs=c['drs'], **meta) for t, c in zip(ms, car)]
    return {'driver': d['name_acronym'], 'full_name': d['full_name'], 'lap_number': lap['lap_number'],
            'lap_time': lap['lap_duration'], 'samples': samples, 'car': car, 'lap': lap, 'event': meet['meeting_name']}

def calculate_delta(ref, tgt, max_points=800):
    """Returns (dist, delta). max_points=800 is their chart/CSV downsampling
    (None keeps every grid point)."""
    aligned = fp.align_data([ref['samples'], tgt['samples']], 0)[0]
    pts = fp.chart_delta(aligned, max_points=max_points or 10**9)[1]
    dist = np.array([x for x, _ in pts], dtype=float)
    delta = np.array([np.nan if y is None else y for _, y in pts], dtype=float)
    return dist, delta
