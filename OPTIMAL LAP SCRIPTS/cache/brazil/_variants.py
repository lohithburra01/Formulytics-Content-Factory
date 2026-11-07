"""Interlagos direction probe: write orig / reversed / mirrored / mirrored+reversed outlines."""
import json, os, numpy as np
D = os.path.dirname(os.path.abspath(__file__))
o = json.load(open(os.path.join(D, "outline_raw.json")))
out, inn = np.array(o["outer"]), np.array(o["inner"])
m = np.array([-1.0, 1.0])
V = {"orig": (out, inn), "rev": (out[::-1], inn[::-1]),
     "mir": (out * m, inn * m), "mirrev": ((out * m)[::-1], (inn * m)[::-1])}
for k, (a, b) in V.items():
    d = dict(o); d["outer"], d["inner"] = a.tolist(), b.tolist()
    json.dump(d, open(os.path.join(D, f"outline_{k}.json"), "w"))
    print(k, len(a))
