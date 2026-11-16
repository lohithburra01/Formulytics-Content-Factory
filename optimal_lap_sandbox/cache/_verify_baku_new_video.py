"""Decode every frame and save representative checks from the new Baku render."""
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / (sys.argv[1] if len(sys.argv) > 1 else
               "azerbaijan_grand_prix_2026_optimal_line_new_svg.mp4")
video = cv2.VideoCapture(str(path))
assert video.isOpened(), path
fps = video.get(cv2.CAP_PROP_FPS)
declared = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
targets = {0, int(25*fps), int(47*fps), int(89*fps), declared-1}
samples = {}
count = 0
while True:
    ok, frame = video.read()
    if not ok:
        break
    if count in targets:
        samples[count] = frame
    count += 1
video.release()
assert count == declared, (count, declared)
assert (width, height) == (1080, 1920), (width, height)
assert len(samples) == len(targets), samples.keys()
small = [cv2.resize(samples[i], (360, 640)) for i in sorted(samples)]
canvas = np.hstack(small)
if "zoom23_original_title" in path.name:
    out = ROOT / "cache/baku_zoom23_original_title_final_checks.png"
elif "original_title" in path.name:
    out = ROOT / "cache/baku_original_title_final_checks.png"
elif "zoom46" in path.name:
    out = ROOT / "cache/baku_new_svg_zoom46_final_checks.png"
else:
    out = ROOT / "cache/baku_new_svg_final_checks.png"
cv2.imwrite(str(out), canvas)
print(f"decoded {count}/{declared} frames, {fps:.1f} fps, {width}x{height}, "
      f"{path.stat().st_size:,} bytes, duration {count/fps:.3f} s")
print(f"saved {out}")
