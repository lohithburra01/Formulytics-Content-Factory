"""Extract car-behaviour signatures from a lap CSV: speed amplitude, braking
decel (g) over a 0.4s window, throttle-on accel, and the deployment-clipping
signature (full throttle but speed stops rising / drops on a straight).

Run on real 2026 references AND the Catalunya sim so we can compare car behaviour
across tracks (distributions & rates are track-portable even if absolute corner
speeds aren't)."""
import csv, sys
import numpy as np

DECEL_WINDOW_S = 0.40

def load(path):
    t, d, v, th, br = [], [], [], [], []
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            t.append(float(r.get("time_s", 0) or 0)); d.append(float(r["distance"]))
            v.append(float(r["speed"]))
            th.append(float(r.get("throttle", 0) or 0)); br.append(float(r.get("brake", 0) or 0))
    return (np.array(t), np.array(d), np.array(v), np.array(th), np.array(br))

def analyze(path, label):
    t, d, v, th, br = load(path)
    vms = v / 3.6
    # build a uniform-ish time base if time missing/constant
    if t.max() <= 0 or np.allclose(t, t[0]):
        t = d / np.maximum(vms, 1.0)
        t = np.cumsum(np.concatenate([[0], np.diff(d) / np.maximum(vms[:-1], 1.0)]))
    # peak braking decel over 0.4s windows
    decels = []
    for i in range(len(v)):
        j = i
        while j < len(v) - 1 and (t[j] - t[i]) < DECEL_WINDOW_S:
            j += 1
        if t[j] > t[i]:
            a = (vms[i] - vms[j]) / (t[j] - t[i])   # +ve = decel
            decels.append(a)
    decels = np.array(decels)
    brake_g = decels[decels > 0] / 9.81
    # clipping: full throttle (>95), not braking, yet speed flat/declining
    dv = np.gradient(vms, t)
    clip = (th > 90) & (br < 5) & (dv < -0.5) & (v > 250)
    print(f"\n=== {label} ===")
    print(f"  pts={len(v)}  lap≈{t[-1]:.2f}s  dist={d[-1]:.0f}m")
    print(f"  SPEED  top={v.max():.0f}  min={v.min():.0f}  range={v.max()-v.min():.0f}  "
          f"p5={np.percentile(v,5):.0f} p25={np.percentile(v,25):.0f} "
          f"p50={np.percentile(v,50):.0f} p75={np.percentile(v,75):.0f} p95={np.percentile(v,95):.0f} km/h")
    print(f"  frac of lap below 150 km/h: {np.mean(v<150)*100:.0f}%   below 120: {np.mean(v<120)*100:.0f}%")
    if len(brake_g):
        print(f"  BRAKING decel (0.4s window): peak={brake_g.max():.2f}g  "
              f"p95={np.percentile(brake_g,95):.2f}g  p99={np.percentile(brake_g,99):.2f}g  median(>0)={np.median(brake_g):.2f}g")
    print(f"  CLIPPING signature frames (full-throttle speed-drop >250km/h): {int(clip.sum())} "
          f"({clip.sum()/len(v)*100:.1f}% of lap)")
    if clip.any():
        print(f"     clipping speeds: {v[clip].min():.0f}-{v[clip].max():.0f} km/h")
    return dict(top=v.max(), mn=v.min(), rng=v.max()-v.min(),
                p50=np.percentile(v,50), brake_p95=np.percentile(brake_g,95) if len(brake_g) else 0)

if __name__ == "__main__":
    for path, label in [(a.split("::")[0], a.split("::")[1]) for a in sys.argv[1:]]:
        analyze(path, label)
