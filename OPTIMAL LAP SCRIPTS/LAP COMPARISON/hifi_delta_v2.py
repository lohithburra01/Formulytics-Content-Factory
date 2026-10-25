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
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f1ih_port as fp

__all__ = ['get_trace', 'get_trace_f1ih', 'calculate_delta']

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

def _get(url, params):
    import requests, time
    for _ in range(4):
        r = requests.get(url, params=params, timeout=180)
        if r.status_code == 200: return r.json()
        time.sleep(3)
    raise RuntimeError(f'{url} {params} -> HTTP {r.status_code} {r.text[:120]}')

def get_trace_f1ih(year, gp, session_name, driver, lap_number=None):
    """Same trace as get_trace, without FastF1: car data from F1InsightsHub's backend
    (backend.f1insightshub.com/fastf1/car_data, what their site uses) and lap/sector times
    from OpenF1 /laps (what their site uses). gp: OpenF1 country or meeting name, e.g.
    'United States'; session_name: 'Qualifying', 'Practice 1', 'Sprint Qualifying', ...
    lap_number=None picks the driver's fastest timed lap."""
    O = 'https://api.openf1.org/v1/'
    ses = [s for s in _get(O + 'sessions', {'year': year, 'session_name': session_name})
           if gp.lower() in (s['country_name'] + '|' + s['location']).lower()]
    meet = None
    if not ses:   # match on meeting name instead
        meet = [m for m in _get(O + 'meetings', {'year': year}) if gp.lower() in m['meeting_name'].lower()]
        ses = [s for s in _get(O + 'sessions', {'year': year, 'session_name': session_name})
               if meet and s['meeting_key'] == meet[0]['meeting_key']]
    ses = [s for s in ses if pd.Timestamp(s['date_start']) <= pd.Timestamp.now(tz='UTC')]   # 'United States' = Austin + Las Vegas
    if not ses: raise ValueError(f'no OpenF1 session {year} {gp} {session_name} (yet)')
    ses = max(ses, key=lambda s: s['date_start'])   # most recent one that has run
    meet = _get(O + 'meetings', {'meeting_key': ses['meeting_key']})[0]
    d = [x for x in _get(O + 'drivers', {'session_key': ses['session_key']})
         if x['name_acronym'] == driver or str(x['driver_number']) == str(driver)]
    if not d: raise ValueError(f'driver {driver} not in session')
    d = d[0]
    laps = [l for l in _get(O + 'laps', {'session_key': ses['session_key'], 'driver_number': d['driver_number']})
            if l.get('lap_duration')]
    if not laps: return None
    lap = (min(laps, key=lambda l: l['lap_duration']) if lap_number is None
           else next(l for l in laps if l['lap_number'] == lap_number))
    car = _get('https://backend.f1insightshub.com/fastf1/car_data',
               {'driver_number': d['driver_number'], 'lap_number': lap['lap_number'],
                'session_key': f"{year}|{meet['meeting_name']}|{ses['session_name']}"})
    if not car: return None

    ms = pd.to_datetime([c['date'] for c in car]).asi8 // 10**6
    meta = dict(lapDuration=lap['lap_duration'], lapDurationS1=lap['duration_sector_1'],
                lapDurationS2=lap['duration_sector_2'], lapNumber=lap['lap_number'], position=None)
    samples = [dict(_ms=float(t), speed=c['speed'], throttle=c['throttle'], brake=c['brake'], rpm=c['rpm'],
                    nGear=c['n_gear'], drs=c['drs'], **meta) for t, c in zip(ms, car)]
    return {'driver': d['name_acronym'], 'full_name': d['full_name'], 'lap_number': lap['lap_number'],
            'lap_time': lap['lap_duration'], 'samples': samples}

def calculate_delta(ref, tgt, max_points=800):
    """Returns (dist, delta). max_points=800 is their chart/CSV downsampling
    (None keeps every grid point)."""
    aligned = fp.align_data([ref['samples'], tgt['samples']], 0)[0]
    pts = fp.chart_delta(aligned, max_points=max_points or 10**9)[1]
    dist = np.array([x for x, _ in pts], dtype=float)
    delta = np.array([np.nan if y is None else y for _, y in pts], dtype=float)
    return dist, delta
