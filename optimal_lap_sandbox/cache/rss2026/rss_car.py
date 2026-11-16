"""RSS Formula Hybrid X 2026 (Race Sim Studio, Assetto Corsa data) -> car functions for our lap simulator.

Every number is READ from the car's data files in cache/ext/void4age at import time (file and key noted).
Assetto Corsa conventions used to read them:
  power.lut          engine torque (Nm) vs rpm; [TURBO_0] multiplies torque by (1 + boost) above REFERENCE_RPM
  engine_map<N>.lut  torque multiplier for the setup's default engine map
  kers_torque.lut    MGU-K torque (Nm, engine-rpm referenced) vs rpm
  ctrl_ers_<N>.ini   deploy fraction = (gas_lut + brake_lut) * speed_lut * gear_lut   (COMBINATOR ADD/ADD/MULT/MULT)
  aero.ini [MAP_k]   CSP aero map: ClA = CL_MULT * MAP_CL_RH(front_rh, rear_rh); CdA = CD_MULT * MAP_CD_RH + DRAG_OFFSET
  aero.ini [WING_k]  extra ClA/CdA = lut(ANGLE) * GAIN * CHORD * SPAN
  tyres.ini          mu(Fz) = D_REF * (Fz / FZ0) ** (LS_EXP - 1)
NOT decided by the files (stated, not invented):
  * ride height: the aero maps are read at their design point (the cell where MAP_CL_RH = 1.0).
  * straight-mode trigger: drs.ini sets EFFECT=0 on the DRS wings and the CSP switch script is not in the repo;
    [MAP_2] 'Straight Mode (2026)' is the car's straight-mode map, used where our simulator already uses straight mode.
  * battery: ers.ini gives MAX_KJ_PER_LAP=9000 (deploy per lap) and no separate store size.
  * the uploader's script.lua (gear speed limiter) is NOT RSS work and is not used.
"""
import os, re, math
import numpy as np

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'ext', 'void4age')
G = 9.80665


def _ini(name):
    out, sec = {}, None
    for line in open(os.path.join(D, name), encoding='utf8', errors='replace'):
        line = line.split(';')[0].strip()
        if not line:
            continue
        m = re.match(r'\[(.+)\]', line)
        if m:
            sec = m.group(1).strip(); out.setdefault(sec, {}); continue
        if '=' in line and sec:
            k, v = line.split('=', 1); out[sec][k.strip()] = v.strip()
    return out


def _lut(name):
    xs, ys = [], []
    for line in open(os.path.join(D, name), encoding='utf8', errors='replace'):
        line = line.split(';')[0].strip()
        if '|' in line:
            a, b = line.split('|')[:2]
            try:
                xs.append(float(a)); ys.append(float(b))
            except ValueError:
                pass
    xs, ys = np.array(xs), np.array(ys); o = np.argsort(xs, kind='stable')
    return xs[o], ys[o]


def _lutf(name):
    x, y = _lut(name); return lambda q: float(np.interp(q, x, y))


def _lut2d(name):
    rows = [l.split() for l in open(os.path.join(D, name)) if l.strip()]
    cols = np.array([float(c) for c in rows[0]]); r = np.array([float(x[0]) for x in rows[1:]])
    M = np.array([[float(c) for c in x[1:]] for x in rows[1:]]); return r, cols, M


CAR = _ini('car.ini'); ENG = _ini('engine.ini'); DRV = _ini('drivetrain.ini'); ERS = _ini('ers.ini')
AERO = _ini('aero.ini'); TYR = _ini('tyres.ini'); SUSP = _ini('suspensions.ini'); SETUP = _ini('setup.ini')

MASS = float(CAR['BASIC']['TOTALMASS'])                                   # car.ini TOTALMASS
FRONT_W = float(SUSP['BASIC']['CG_LOCATION'])                             # suspensions.ini CG_LOCATION
R_WHEEL = float(TYR['REAR']['RADIUS'])                                    # tyres.ini RADIUS
LIMITER = float(ENG['ENGINE_DATA']['LIMITER'])
BOOST = float(ENG['TURBO_0']['MAX_BOOST']); BOOST_REF = float(ENG['TURBO_0']['REFERENCE_RPM'])
MAP_DEFAULT = int(SETUP.get('ENGINE_MAPS', {}).get('DEFAULT', ENG['MAP'].get('DEFAULT', '0')))
T_ENG = _lutf('power.lut'); T_MAP = _lutf(ENG['MAP'][f'MAP_{MAP_DEFAULT}'])
GEARS = [float(DRV['GEARS'][f'GEAR_{i}']) for i in range(1, int(DRV['GEARS']['COUNT']) + 1)]
FINAL = float(DRV['GEARS']['FINAL'])
T_K = _lutf(ERS['KINETIC']['TORQUE_CURVE'])
DEPLOY_J_PER_LAP = float(ERS['KINETIC']['MAX_KJ_PER_LAP']) * 1e3


def ers_mode(n):
    c = _ini(f'ctrl_ers_{n}.ini'); name = c['HEADER']['NAME']; f = {}
    for k, v in c.items():
        if k.startswith('CONTROLLER'):
            f[v['INPUT']] = _lutf(v['LUT'])
    return name, f


ERS_NAME, ERS_F = ers_mode(4)          # ctrl_ers_4 = 'Qualy' (qualifying lap)


def deploy_frac(v_kmh, gear, gas=1.0, brake=0.0):
    out = ERS_F['GAS'](gas) + ERS_F['BRAKE'](brake)
    return max(0.0, min(1.0, out * ERS_F['SPEED_KMH'](v_kmh) * ERS_F['GEAR'](gear)))


def _rpm(v, ratio):
    return v / R_WHEEL * ratio * FINAL * 60 / (2 * math.pi)


def power_at(v):
    """(P_ice W, P_mguk W, gear) at the wheel, best gear under the limiter (auto-shift)."""
    best = (0.0, 0.0, 1)
    for g, ratio in enumerate(GEARS, 1):
        rpm = _rpm(v, ratio)
        if rpm > LIMITER:
            continue
        w = rpm * 2 * math.pi / 60
        tq = T_ENG(rpm) * T_MAP(rpm) * ((1 + BOOST) if rpm >= BOOST_REF else 1.0)
        p_ice = tq * w; p_k = T_K(rpm) * w * deploy_frac(v * 3.6, g)
        if p_ice + p_k > best[0] + best[1]:
            best = (p_ice, p_k, g)
    return best


# --- aero
def _map_point():
    r, c, M = _lut2d(AERO['MAP_1']['MAP_CL_RH']); i, j = np.unravel_index(np.argmax(M), M.shape); return r[i], c[j], (r, c)


def _map_val(name, rh):
    r, c, M = _lut2d(name); return float(M[list(r).index(rh[0]), list(c).index(rh[1])])


RH = _map_point()[:2]
SETUP_MAP = int(SETUP['AEROMAP']['DEFAULT'])


def _wing_extra(skip_names=('DRS', 'DRSFW')):
    cl = cd = 0.0
    for k, w in AERO.items():
        if not k.startswith('WING_') or w.get('NAME') in skip_names:
            continue
        a = float(w.get('ANGLE', 0)); area = float(w.get('CHORD', 1)) * float(w.get('SPAN', 1))
        if float(w.get('CL_GAIN', 0)) and 'LUT_AOA_CL' in w:
            cl += _lutf(w['LUT_AOA_CL'])(a) * float(w['CL_GAIN']) * area
        if float(w.get('CD_GAIN', 0)) and 'LUT_AOA_CD' in w:
            cd += _lutf(w['LUT_AOA_CD'])(a) * float(w['CD_GAIN']) * area
    return cl, cd


def aero(map_idx):
    m = AERO[f'MAP_{map_idx}']; wcl, wcd = _wing_extra()
    off = float(m.get('DRAG_OFFSET', '0').split(',')[0])
    ClA = float(m['CL_MULT']) * _map_val(m['MAP_CL_RH'], RH) + wcl
    CdA = float(m['CD_MULT']) * _map_val(m['MAP_CD_RH'], RH) + off + wcd
    bal = _map_val(m['MAP_BALANCE_RH'], RH) + float(m.get('BALANCE_OFFSET', 0))
    return ClA, CdA, bal, m['NAME']


CORNER = aero(SETUP_MAP)                # setup.ini [AEROMAP] DEFAULT -> 'Current Concept'
STRAIGHT = aero(2)                      # [MAP_2] 'Straight Mode (2026)'

# --- tyres (setup default compound = first [FRONT]/[REAR] block)
TF, TR = TYR['FRONT'], TYR['REAR']


def _mu(t, axis, fz):
    return float(t[f'D{axis}_REF']) * (max(fz, 1.0) / float(t['FZ0'])) ** (float(t[f'LS_EXP{axis}']) - 1.0)


def axle_loads(df, bal):
    wf = MASS * G * FRONT_W + df * bal; wr = MASS * G * (1 - FRONT_W) + df * (1 - bal); return wf, wr


def a_lat_max(v, rho, mode='CORNER'):
    ClA, CdA, bal, _ = CORNER if mode == 'CORNER' else STRAIGHT
    df = 0.5 * rho * ClA * v * v; wf, wr = axle_loads(df, bal)
    gf = 2 * _mu(TF, 'Y', wf / 2) * wf / 2; gr = 2 * _mu(TR, 'Y', wr / 2) * wr / 2
    return min(gf / (MASS * FRONT_W), gr / (MASS * (1 - FRONT_W)))      # each axle carries its mass share


def a_brake_max(v, rho, mode='CORNER'):
    ClA, CdA, bal, _ = CORNER if mode == 'CORNER' else STRAIGHT
    df = 0.5 * rho * ClA * v * v; wf, wr = axle_loads(df, bal)
    return (2 * _mu(TF, 'X', wf / 2) * wf / 2 + 2 * _mu(TR, 'X', wr / 2) * wr / 2) / MASS


def a_trac_max(v, rho, mode):
    ClA, CdA, bal, _ = CORNER if mode == 'CORNER' else STRAIGHT
    df = 0.5 * rho * ClA * v * v; wf, wr = axle_loads(df, bal)
    return 2 * _mu(TR, 'X', wr / 2) * wr / 2 / MASS                        # drivetrain.ini TYPE=RWD


def summary():
    rows = [('mass kg', MASS, 'car.ini TOTALMASS'), ('front weight', FRONT_W, 'suspensions.ini CG_LOCATION'),
            ('corner ClA / CdA / balance', CORNER[:3], f"aero.ini MAP_{SETUP_MAP} '{CORNER[3]}' at RH {RH}"),
            ('straight ClA / CdA / balance', STRAIGHT[:3], f"aero.ini MAP_2 '{STRAIGHT[3]}'"),
            ('ERS mode', ERS_NAME, 'ctrl_ers_4.ini'), ('deploy per lap J', DEPLOY_J_PER_LAP, 'ers.ini MAX_KJ_PER_LAP')]
    for v in (100, 150, 200, 250, 280, 300, 320, 340):
        pi, pk, g = power_at(v / 3.6); rows.append((f'power @ {v} km/h: ICE / MGU-K kW, gear', (round(pi / 1e3), round(pk / 1e3), g), 'power.lut x turbo x map; kers_torque x ctrl_ers_4'))
    return rows


if __name__ == '__main__':
    for r in summary():
        print(f'{r[0]:42s} {str(r[1]):34s} {r[2]}')
    for v in (80, 150, 250, 300):
        print(f'grip @ {v} km/h: lat {a_lat_max(v/3.6, 1.18)/G:.2f} g, brake {a_brake_max(v/3.6, 1.18)/G:.2f} g, traction {a_trac_max(v/3.6, 1.18, "CORNER")/G:.2f} g')
