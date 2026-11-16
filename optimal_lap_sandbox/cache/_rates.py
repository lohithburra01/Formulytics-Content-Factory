"""Rate-of-change comparison: how fast speed GAINS under throttle, DROPS under
braking, and BLEEDS during superclip. Measured over a common 0.5s window so the
sim (30fps) and OpenF1 real (~3.7Hz) are compared apples-to-apples.

This is what matters for 'ups too up / downs too down / superclip drops too much'
— the SLOPES, not the absolute speeds (FP1 isn't a pushing lap)."""
import csv, sys
import numpy as np

WIN_S = 0.5

def load(path):
    t, v, th, br = [], [], [], []
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            t.append(float(r["time_s"])); v.append(float(r["speed"]))
            th.append(float(r.get("throttle", 0) or 0)); br.append(float(r.get("brake", 0) or 0))
    return np.array(t), np.array(v), np.array(th), np.array(br)

def rate_kmh_s(t, v):
    """dv/dt in km/h per second over a forward WIN_S window."""
    out = np.full(len(v), np.nan)
    for i in range(len(v)):
        j = i
        while j < len(v)-1 and (t[j]-t[i]) < WIN_S:
            j += 1
        if t[j] > t[i]:
            out[i] = (v[j]-v[i])/(t[j]-t[i])
    return out

def analyze(path, label):
    t, v, th, br = load(path)
    r = rate_kmh_s(t, v)
    top = v.max()
    accel = r[(th>80)&(br<5)&(v<0.88*top)&(r>2)]      # genuine throttle-on gain
    brake = r[(br>15)&(r<-2)]                           # braking drop
    clip  = r[(th>90)&(br<5)&(v>0.85*top)&(r<-1)]       # superclip speed-bleed
    print(f"\n=== {label} ===  (top={top:.0f} km/h)")
    def desc(a, name, unit="km/h/s"):
        if len(a)==0: print(f"  {name}: (none)"); return
        print(f"  {name}: median={np.median(np.abs(a)):.1f}  p90={np.percentile(np.abs(a),90):.1f}  "
              f"max={np.max(np.abs(a)):.1f} {unit}   (n={len(a)})")
    desc(accel, "GAIN rate (throttle on)   ")
    desc(brake, "DROP rate (braking)       ")
    desc(clip,  "SUPERCLIP bleed rate      ")

if __name__ == "__main__":
    for a in sys.argv[1:]:
        p, l = a.split("::"); analyze(p, l)
