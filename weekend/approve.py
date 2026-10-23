"""Approve the review pictures of the current run, so the next run renders the video.

  python -m weekend.approve austin 2026      # after the user said the line + speed pictures are OK

Approval is tied to the review stage key: any change to the line or the lap makes a new review that
needs a new OK. Then `python -m weekend austin 2026` continues (all stages come from cache) to the video.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date

from weekend import pipeline
from weekend.resolve import pack_path
from weekend.runner import APPROVED


def approve(track: str, year: int) -> str:
    rv = pipeline.run_stage("review", pack_path(dict(track=track, year=year)))
    path = os.path.join(rv["dir"], APPROVED)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(dict(approved=str(date.today()), by="user", review_key=rv["key"]), fh, indent=1)
    return path


if __name__ == "__main__":
    print(approve(sys.argv[1], int(sys.argv[2])))
