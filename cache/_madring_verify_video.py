"""Verify the rendered Madring optimal-lap video: full decode, metadata, contact sheet, HUD crop.

Read-only on the video; writes new PNGs under cache/madring_optimal_video_check/.
"""
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
video = ROOT / (sys.argv[1] if len(sys.argv) > 1 else "madring_2026_optimal_lap.mp4")
out_dir = ROOT / "cache/madring_optimal_video_check"
out_dir.mkdir(exist_ok=True)
sheet_p, hud_p = out_dir / "contact_sheet.png", out_dir / "final_frame_hud.png"
for p in (sheet_p, hud_p):
    if p.exists():
        raise FileExistsError(p)

cap = cv2.VideoCapture(str(video))
assert cap.isOpened(), f"cannot open {video}"
n_meta = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
fps = cap.get(cv2.CAP_PROP_FPS)
w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
wanted = {int(t * fps): t for t in (0, 15, 30, 46, 62, 78)}
tiles, last, n = {}, None, 0
while True:
    ok, frame = cap.read()
    if not ok:
        break
    if n in wanted:
        tiles[n] = cv2.resize(frame, (w // 3, h // 3), interpolation=cv2.INTER_AREA)
    last = frame
    n += 1
cap.release()
print(f"{video.name}: {video.stat().st_size} bytes | {w}x{h} @ {fps:.2f} fps | "
      f"container {n_meta} frames, decoded {n} frames = {n / fps:.2f} s")
assert n > 0 and len(tiles) == len(wanted), f"decoded {n}, tiles {sorted(tiles)}"
row = [tiles[k] for k in sorted(tiles)]
cv2.imwrite(str(sheet_p), np.vstack([np.hstack(row[:3]), np.hstack(row[3:])]))
cv2.imwrite(str(hud_p), last[960:1330, :])
print("wrote", sheet_p, "and", hud_p)
