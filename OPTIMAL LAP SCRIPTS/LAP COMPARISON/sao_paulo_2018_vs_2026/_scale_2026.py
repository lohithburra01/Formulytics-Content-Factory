"""Shipped 2026 Sao Paulo lap CSV (last row 70.739) uniformly stretched to the shipped label 1:10.772: time x k, speed / k,
same distances, so the dual video's clock and live gap agree with the 1:10.772 shown. Shipped CSV untouched."""
import csv, os
H = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(H))
SRC = os.path.join(ROOT, "F1_Pipeline_Assets", "exports", "sao_paulo_2026_synthetic.csv"); LABEL = 70.772
rows = list(csv.DictReader(open(SRC, encoding="utf-8"))); k = LABEL / float(rows[-1]["time_s"])
with open(os.path.join(H, "sao_paulo_2026_at_70772.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader()
    for r in rows:
        r["time_s"] = f"{float(r['time_s']) * k:.4f}"; r["speed"] = f"{float(r['speed']) / k:.3f}"; w.writerow(r)
print(f"k {k:.5f}: {rows[-1]['time_s']} -> {LABEL}")
