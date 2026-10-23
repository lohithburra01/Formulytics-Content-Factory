"""Nudge flow (spec stories 51-54, grill D13): plain words -> note -> one-line confirm -> commit -> rerun affected.

Claude's only job is to turn the user's words into a note (JSON/YAML, same shape as weekend/notes).
Everything after that is this script:

  python -m weekend.nudge preview <note.json> singapore 2026   # validate + the one confirmation line
  python -m weekend.nudge apply   <note.json> singapore 2026   # write note, re-resolve pack, git commit
  python -m weekend singapore 2026                               # rerun: unchanged stages come from cache

"Affected steps only" needs no extra code: a stage's cache key hashes only the values it reads, so a
note that changes line.rule.* reruns car_and_line and what comes after it, never track or refs.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import yaml

from weekend import pipeline, store
from weekend.resolve import load_notes, pack_path, resolve_pack
from weekend.schema import Note

ROOT = pipeline.ROOT


def _load(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)        # JSON is valid YAML


def affected(old: dict, new: dict) -> tuple[list[str], list[str]]:
    """Changed value names, and the stages that will rerun (direct readers + everything downstream)."""
    names = sorted(k for k in set(old) | set(new)
                   if [old.get(k, {}).get("value"), old.get(k, {}).get("sha256")]
                   != [new.get(k, {}).get("value"), new.get(k, {}).get("sha256")])
    import weekend.stages  # noqa: F401  (registers the stages)
    from weekend.runner import ORDER
    hit = set()
    for name in ORDER:
        st = pipeline.STAGES[name]
        if selected_any(names, st.reads) or hit & set(st.needs):
            hit.add(name)
    return names, [n for n in ORDER if n in hit]


def selected_any(names, reads):
    return bool(pipeline.selected({n: {} for n in names}, reads))


def preview(note: dict, weekend: dict) -> dict:
    n = Note.model_validate(note)                          # Pydantic check before anything is written
    old = json.load(open(pack_path(weekend), encoding="utf-8"))["values"]
    notes = [x for x in load_notes() if x.id != n.id] + [n]
    new = json.loads(resolve_pack(notes, weekend).model_dump_json(exclude_none=True))["values"]
    names, stages = affected(old, new)
    vals = ", ".join(f"{k} = {new[k]['value'] if k in new else '(removed)'}" for k in names) or "no value changes"
    line = f"{n.id}: {vals} -> reruns {', '.join(stages) or 'nothing'}"
    return dict(confirm=line, changed=names, reruns=stages)


def apply(note: dict, weekend: dict, replace: bool = False) -> dict:
    p = preview(note, weekend)
    note_file = store.add_node(note, replace=replace)
    pack = resolve_pack(load_notes(), weekend)
    with open(pack_path(weekend), "w", encoding="utf-8") as fh:
        fh.write(pack.model_dump_json(indent=1, exclude_none=True))
    files = [note_file, os.path.relpath(pack_path(weekend), ROOT)]
    subprocess.run(["git", "add", "--", *files], cwd=ROOT, check=True)
    msg = (f"nudge: {p['confirm']}\n\nCo-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>")
    subprocess.run(["git", "commit", "-q", "-m", msg, "--", *files], cwd=ROOT, check=True)
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    return dict(p, committed=head, note_file=note_file)


if __name__ == "__main__":
    cmd, path, track, year = sys.argv[1:5]
    w = dict(track=track, year=int(year))
    out = preview(_load(path), w) if cmd == "preview" else apply(_load(path), w, replace="--replace" in sys.argv)
    print(json.dumps(out, indent=1))
