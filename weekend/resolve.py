"""Resolve the layered notes for one weekend into a Weekend Pack.

  python -m weekend.resolve singapore 2026          -> weekend/packs/singapore_2026.json

A value nobody can source (origin ASSUMED) is not defaulted: it is returned as a
question and no pack is written until it is answered (grill D2).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

import yaml

from weekend.schema import LAYERS, Note, PackValue, WeekendPack

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOTES_DIR = os.path.join(ROOT, "weekend", "notes")
PACKS_DIR = os.path.join(ROOT, "weekend", "packs")


class Unresolved(Exception):
    def __init__(self, questions: list[dict]):
        self.questions = questions
        super().__init__(f"{len(questions)} value(s) have no origin")


def load_notes(notes_dir: str = NOTES_DIR) -> list[Note]:
    notes = []
    for dirpath, _, files in os.walk(notes_dir):
        for f in sorted(files):
            if f.endswith((".yaml", ".yml")):
                with open(os.path.join(dirpath, f), encoding="utf-8") as fh:
                    notes.append(Note.model_validate(yaml.safe_load(fh)))
    return notes


def _in_scope(note: Note, weekend: dict) -> bool:
    return all(weekend.get(k) == v for k, v in note.scope.items())


def _sha256(rel_path: str, root: str) -> str:
    with open(os.path.join(root, rel_path), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def resolve_pack(notes: list[Note], weekend: dict, root: str = ROOT) -> WeekendPack:
    chosen: dict[str, tuple[int, Note]] = {}
    for note in notes:
        if not _in_scope(note, weekend):
            continue
        rank = LAYERS.index(note.layer)
        for name in note.values:
            prev = chosen.get(name)
            if prev and prev[0] == rank:
                raise ValueError(f"{name}: set twice in layer '{note.layer}' "
                                 f"({prev[1].id}, {note.id})")
            if not prev or rank > prev[0]:
                chosen[name] = (rank, note)

    values, questions = {}, []
    for name in sorted(chosen):
        _, note = chosen[name]
        v = note.values[name]
        if v.origin == "ASSUMED":
            questions.append(dict(name=name, value=v.value, unit=v.unit,
                                  note_id=note.id, note=v.note))
            continue
        pv = PackValue(**v.model_dump(), layer=note.layer, note_id=note.id)
        if v.file:
            pv.sha256 = _sha256(str(v.value), root)
        values[name] = pv
    if questions:
        raise Unresolved(questions)
    return WeekendPack(weekend=weekend, values=values)


def pack_path(weekend: dict) -> str:
    return os.path.join(PACKS_DIR, f"{weekend['track']}_{weekend['year']}.json")


def main(argv: list[str]) -> int:
    weekend = dict(track=argv[0], year=int(argv[1]))
    try:
        pack = resolve_pack(load_notes(), weekend)
    except Unresolved as e:
        print(f"[resolve] {len(e.questions)} value(s) need an origin before a pack can be written:")
        for q in e.questions:
            print(f"  {q['name']} = {q['value']} {q['unit']}  ({q['note_id']})")
        return 2
    os.makedirs(PACKS_DIR, exist_ok=True)
    with open(pack_path(weekend), "w", encoding="utf-8") as fh:
        fh.write(pack.model_dump_json(indent=1, exclude_none=True))
    by_origin = {}
    for v in pack.values.values():
        by_origin[v.origin] = by_origin.get(v.origin, 0) + 1
    print(f"[resolve] {len(pack.values)} values -> {pack_path(weekend)}  {by_origin}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
