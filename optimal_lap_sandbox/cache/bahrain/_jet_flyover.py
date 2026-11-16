"""Overlay a brief, subtle top-down fighter-jet flyover (3-ship vic, contrails + ground shadow)
on a finished lap video. Frames outside the flyover window are passed through untouched.
  python cache/bahrain/_jet_flyover.py --in a.mp4 --out b.mp4 --t0 86.0 --dur 2.8
  python cache/bahrain/_jet_flyover.py --in a.mp4 --preview 87.0 --png check.png   (one frame)"""
import argparse, subprocess
import cv2
import numpy as np

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from jet_overlay import overlay  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", required=True); ap.add_argument("--out", default=None)
    ap.add_argument("--t0", type=float, default=86.0); ap.add_argument("--dur", type=float, default=2.8,
                    help="seconds for the lead to cross from --p-from to --p-to")
    ap.add_argument("--linger", type=float, default=2.0, help="contrails fading after the crossing")
    ap.add_argument("--p-from", type=float, nargs=2, default=(-140, 1500))
    ap.add_argument("--p-to", type=float, nargs=2, default=(1240, 300))
    ap.add_argument("--scale", type=float, default=0.95); ap.add_argument("--gap", type=float, default=34)
    ap.add_argument("--trail-life", type=float, default=1.3); ap.add_argument("--jet-alpha", type=float, default=0.92)
    ap.add_argument("--shadow-off", type=float, nargs=2, default=(38, 70)); ap.add_argument("--shadow-alpha", type=float, default=0.28)
    ap.add_argument("--motion-blur", type=int, default=6)
    ap.add_argument("--preview", type=float, default=None); ap.add_argument("--png", default=None)
    a = ap.parse_args()
    cap = cv2.VideoCapture(a.src); fps = cap.get(cv2.CAP_PROP_FPS)
    W, H = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if a.preview is not None:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(round(a.preview * fps))); ok, fr = cap.read()
        cv2.imwrite(a.png, overlay(fr, a.preview, a, fps)); return
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                            "-r", f"{fps}", "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "17",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", a.out], stdin=subprocess.PIPE)
    i = 0
    while True:
        ok, fr = cap.read()
        if not ok: break
        enc.stdin.write(overlay(fr, i / fps, a, fps).tobytes()); i += 1
    enc.stdin.close(); enc.wait(); print(f"[jets] {i} frames -> {a.out}")


if __name__ == "__main__":
    main()
