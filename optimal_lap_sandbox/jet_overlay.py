"""Top-down aircraft flyovers (B-2, SR-71, or a 3-ship fighter vic) with contrails, ground shadow and
motion blur. Drawn by raceline_video.py --flights inside the render loop (ONE encode, native quality).
Flight spec: "type:t0,dur,x0,y0,x1,y1[;type:...]"  (s, s, screen px; the aircraft flies x0,y0 -> x1,y1)."""
from types import SimpleNamespace
import cv2
import numpy as np

SS = 3  # sprite supersampling


def _mirror(half):
    """half outline (nose -> tail, +y side) -> closed symmetric polygon."""
    h = np.asarray(half, float)
    return np.vstack([h, h[::-1][1:-1] * [1, -1]]) if h[-1, 1] == 0 else np.vstack([h, h[::-1] * [1, -1]])


# Sprites: nose along +x, units = px. Sizes ~1.9x the original fighters (user: 1.5-2x).
B2 = dict(  # flying wing, 33 deg swept leading edge, double-W trailing edge; span ~92 px
    polys=[_mirror([(22, 0), (-7, 45), (-11, 44), (-1, 30), (-12, 19), (-3, 9), (-14, 0)])],
    details=[_mirror([(15, 0), (12, 3.2), (9, 3.2), (9, 0)])],              # cockpit windows
    engines=[(-10, 7.5), (-10, -7.5)], fill=(150, 150, 156), edge=(205, 205, 210), detail=(70, 70, 76))
_SX = np.array([1.15, 1.0])   # SR-71 stretched along x for its slender read at small size; length ~108 px
SR71 = dict(  # ogive chines blending into the wing, long nacelles at +-13 px with inlet spikes, wing set aft
    polys=[_mirror([(48, 0), (38, 1.6), (28, 3.2), (18, 5.2), (8, 7.6), (2, 10.4), (-36, 10.4),
                    (-36, 2.4), (-44, 1.6), (-46, 0)]) * _SX]
          + [np.array([(15, sy * 13), (9, sy * 15.4), (-40, sy * 15.4), (-40, sy * 10.6), (9, sy * 10.6)], float) * _SX
             for sy in (1, -1)]                                                       # nacelles + inlet spikes
          + [np.array([(2, sy * 15), (-27, sy * 25.5), (-33, sy * 25.5), (-36, sy * 15)], float) * _SX for sy in (1, -1)],
    details=[_mirror([(30, 0), (27, 1.3), (22, 1.3), (22, 0)]) * _SX]
            + [np.array([(-26, sy * 12.6), (-38, sy * 12.6), (-38, sy * 13.6), (-26, sy * 13.6)], float) * _SX for sy in (1, -1)],
    engines=[(-40 * 1.15, 13), (-40 * 1.15, -13)], fill=(138, 138, 144), edge=(200, 200, 205), detail=(70, 70, 76))
_F = np.array([(26, 0), (18, 2.2), (7, 3.2), (-5, 14.5), (-10, 14.5), (-7, 3.8), (-15, 3.4), (-20, 8.5),
               (-23.5, 8.5), (-21, 2.4), (-24, 1.3), (-24, -1.3), (-21, -2.4), (-23.5, -8.5), (-20, -8.5),
               (-15, -3.4), (-7, -3.8), (-10, -14.5), (-5, -14.5), (7, -3.2), (18, -2.2)], float) * 0.95
VIC = dict(polys=[_F + o for o in ((0, 0), (-70, -62), (-70, 62))], details=[], engines=[(-70 - 23, 62), (-70 - 23, -62), (-23, 0)],
           fill=(165, 172, 178), edge=None, detail=(50, 60, 70))
TYPES = {"b2": B2, "sr71": SR71, "vic": VIC}

GAP, TRAIL_LIFE, LINGER, ALPHA = 24.0, 1.3, 2.0, 0.93
SHADOW_OFF, SHADOW_ALPHA, SHUTTER = (38, 70), 0.28, 120.0


def parse(spec):
    out = []
    for item in spec.split(";"):
        typ, nums = item.split(":"); t0, dur, x0, y0, x1, y1 = map(float, nums.split(","))
        out.append(SimpleNamespace(ac=TYPES[typ.strip().lower()], t0=t0, dur=dur, p0=np.array([x0, y0]), p1=np.array([x1, y1])))
    return out


def _place(pts, ang, at, scale=1.0):
    c, s = np.cos(ang), np.sin(ang)
    return (pts * scale) @ np.array([[c, s], [-s, c]]) + at


def _one(frame, t, fl, fps):
    H, W = frame.shape[:2]; tau = t - fl.t0
    if tau < 0 or tau > fl.dur + LINGER: return frame
    d = fl.p1 - fl.p0; ang = np.arctan2(d[1], d[0]); u = d / np.linalg.norm(d); spd = np.linalg.norm(d) / fl.dur
    ac = fl.ac; head = fl.p0 + tau * spd * u
    trail = np.zeros((H, W), np.float32); shadow = np.zeros((H, W), np.float32)
    for e in ac["engines"]:                               # contrails, starting GAP px behind each exhaust
        ex = _place(np.array([e], float), ang, head)[0]
        for k in range(int(GAP), 1100, 6):
            age = k / spd
            if age > tau: break
            q = ex - u * k; fade = np.exp(-age / TRAIL_LIFE)
            cv2.circle(trail, (int(q[0]), int(q[1])), int(round(1.8 + 2.4 * age)), float(0.55 * fade), -1, cv2.LINE_AA)
    for p in ac["polys"]:
        cv2.fillPoly(shadow, [_place(p, ang, head + SHADOW_OFF).astype(np.int32)], 1.0, cv2.LINE_AA)
    body = np.zeros((H * SS, W * SS), np.uint8); edge = np.zeros_like(body); det = np.zeros_like(body)
    hs = head * SS
    for p in ac["polys"]:
        q = np.round(_place(p, ang, hs, SS)).astype(np.int32)
        cv2.fillPoly(body, [q], 255, cv2.LINE_AA)
    if ac["edge"] is not None:   # outline of the MERGED silhouette (no internal seams between parts)
        edge = cv2.subtract(body, cv2.erode(body, np.ones((2 * SS - 1, 2 * SS - 1), np.uint8)))
    for p in ac["details"]:
        cv2.fillPoly(det, [np.round(_place(p, ang, hs, SS)).astype(np.int32)], 255, cv2.LINE_AA)
    # motion blur: continuous line kernel along the flight path, length = travel over a SHUTTER-degree
    # exposure (smooth smear, no stepped ghost copies)
    blur_px = spd / fps * SHUTTER / 360.0
    K = None
    if blur_px > 1.0:
        n = int(np.ceil(blur_px)) | 1; K = np.zeros((n, n), np.float32); c = n // 2
        cv2.line(K, (int(round(c - u[0] * blur_px / 2)), int(round(c - u[1] * blur_px / 2))),
                 (int(round(c + u[0] * blur_px / 2)), int(round(c + u[1] * blur_px / 2))), 1.0, 1, cv2.LINE_AA)
        K /= K.sum()
    env = min(1.0, tau / 0.25, max(0.0, (fl.dur + LINGER - tau) / LINGER))
    def rs(a):
        a = cv2.resize(a, (W, H), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
        if K is not None: a = cv2.filter2D(a, -1, K)
        return (a * ALPHA * env)[..., None]
    jb, je, jd = rs(body), rs(edge), rs(det)
    trail = cv2.GaussianBlur(trail, (0, 0), 2.2)[..., None] * env
    shadow = cv2.GaussianBlur(shadow, (0, 0), 3.0)[..., None] * SHADOW_ALPHA * env
    f = frame.astype(np.float32) * (1 - shadow)
    f = f * (1 - trail) + 245 * trail
    f = f * (1 - jb) + np.array(ac["fill"], np.float32) * jb
    if ac["edge"] is not None: f = f * (1 - je) + np.array(ac["edge"], np.float32) * je
    f = f * (1 - jd) + np.array(ac["detail"], np.float32) * jd
    return np.clip(f, 0, 255).astype(np.uint8)


def overlay(frame, t, flights, fps=30.0):
    for fl in flights: frame = _one(frame, t, fl, fps)
    return frame
