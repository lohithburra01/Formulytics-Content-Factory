"""Shipped 2026 Mexico lap (sim 76.758) uniformly slowed to the user's chosen label 1:17.265: time x k, speed / k,
same distances, so the dual video's clock and live gap agree with the 1:17.265 shown. Shipped CSV untouched."""
import csv, os
H = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(H))
SRC = os.path.join(ROOT, "F1_Pipeline_Assets", "exports", "mexico_2026_synthetic.csv"); LABEL = 77.265
rows = list(csv.DictReader(open(SRC, encoding="utf-8"))); k = LABEL / float(rows[-1]["time_s"])
with open(os.path.join(H, "mexico_2026_at_77265.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader()
    for r in rows:
        r["time_s"] = f"{float(r['time_s']) * k:.4f}"; r["speed"] = f"{float(r['speed']) / k:.3f}"; w.writerow(r)
print(f"k {k:.5f}: {rows[-1]['time_s']} -> {LABEL}")
