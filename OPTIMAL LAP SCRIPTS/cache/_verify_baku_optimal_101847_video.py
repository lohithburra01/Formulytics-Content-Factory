"""Decode and inspect the final borderless, zoom-46 Baku optimal video."""

from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
VIDEO = ROOT / "azerbaijan_grand_prix_2026_optimal_lap_101847_zoom46.mp4"
CONTACT = ROOT / "cache/baku_optimal_101847_zoom46_final_checks.png"
TITLE = ROOT / "cache/baku_optimal_101847_zoom46_title.png"

capture = cv2.VideoCapture(str(VIDEO))
assert capture.isOpened(), VIDEO
fps = float(capture.get(cv2.CAP_PROP_FPS))
declared = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
assert (fps, declared, width, height) == (30.0, 3056, 1080, 1920)

targets = {0, 25 * 30, 47 * 30, 89 * 30, declared - 1}
samples = {}
count = 0
while True:
    ok, frame = capture.read()
    if not ok:
        break
    if count in targets:
        samples[count] = frame.copy()
    count += 1
capture.release()
assert count == declared, (count, declared)
assert set(samples) == targets, (set(samples), targets)

small = [cv2.resize(samples[i], (360, 640)) for i in sorted(samples)]
cv2.imwrite(str(CONTACT), np.hstack(small))
cv2.imwrite(str(TITLE), samples[0][230:480, 120:960])
print(f"decoded {count}/{declared} frames; {fps:.1f} fps; {width}x{height}; "
      f"duration {count/fps:.3f} s; {VIDEO.stat().st_size:,} bytes")
print(f"saved {CONTACT} and {TITLE}")
