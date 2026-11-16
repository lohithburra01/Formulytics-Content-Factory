"""Knowledge store over the YAML notes (grill D10). The YAML files in git are the only truth;
links live inside the notes; meaning search is a rebuildable cache. The MCP server
(weekend/mcp_server.py) exposes exactly these four functions.

  find_node(id)               one note
  neighbours(id)              notes it links to + notes that link to it
  search(query, k)            notes by meaning (local sentence-transformers, CPU)
  add_node(note, replace)     Pydantic-checked write of one note (refuses same-layer clashes)
"""
from __future__ import annotations

import hashlib
import json
import os

import yaml

from weekend.schema import LAYERS, Note

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOTES_DIR = os.path.join(ROOT, "weekend", "notes")
CACHE_DIR = os.path.join(ROOT, "weekend", ".search_cache")
MODEL = "intfloat/multilingual-e5-small"


def _path_for(note_id: str, notes_dir: str) -> str:
    layer, _, name = note_id.partition("/")
    if layer not in LAYERS or not name or "/" in name or ".." in name:
        raise ValueError(f"note id must be '<layer>/<name>' with layer in {LAYERS}: {note_id!r}")
    return os.path.join(notes_dir, layer, f"{name}.yaml")


def all_notes(notes_dir: str = NOTES_DIR) -> dict[str, dict]:
    out = {}
    for dirpath, _, files in os.walk(notes_dir):
        for f in sorted(files):
            if f.endswith((".yaml", ".yml")):
                with open(os.path.join(dirpath, f), encoding="utf-8") as fh:
                    d = yaml.safe_load(fh)
                out[d["id"]] = d
    return out


def find_node(note_id: str, notes_dir: str = NOTES_DIR) -> dict | None:
    return all_notes(notes_dir).get(note_id)


def neighbours(note_id: str, notes_dir: str = NOTES_DIR) -> dict:
    notes = all_notes(notes_dir)
    if note_id not in notes:
        raise KeyError(note_id)
    out_links = [l for l in notes[note_id].get("links", []) if l in notes]
    in_links = [i for i, n in notes.items() if note_id in n.get("links", [])]
    return dict(links_to=out_links, linked_from=in_links)


def _scopes_overlap(a: dict, b: dict) -> bool:
    return all(a[k] == b[k] for k in set(a) & set(b))


def add_node(note: dict, replace: bool = False, notes_dir: str = NOTES_DIR) -> str:
    """Validate and write one note. Refuses: invalid shape/origins, an existing id unless replace,
    and a value already set by another note of the same layer with an overlapping scope."""
    n = Note.model_validate(note)
    path = _path_for(n.id, notes_dir)
    notes = all_notes(notes_dir)
    if n.id in notes and not replace:
        raise ValueError(f"note {n.id} exists (pass replace=True to update it)")
    for oid, o in notes.items():
        if oid == n.id or o["layer"] != n.layer or not _scopes_overlap(o.get("scope", {}), n.scope):
            continue
        clash = set(o["values"]) & set(n.values)
        if clash:
            raise ValueError(f"{sorted(clash)} already set in layer '{n.layer}' by {oid}")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = json.loads(n.model_dump_json(exclude_none=True, exclude_defaults=True))
    data = {k: data[k] for k in ("id", "layer", "scope", "links", "values") if k in data}
    data.setdefault("scope", {})
    with open(path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, sort_keys=False, allow_unicode=True, width=200)
    try:
        return os.path.relpath(path, ROOT)
    except ValueError:            # different drive (e.g. a temp folder on C:)
        return path


# ---- meaning search (rebuildable cache) --------------------------------------------------

def _doc_texts(notes: dict) -> list[tuple[str, str]]:
    docs = []
    for nid, n in notes.items():
        for name, v in n["values"].items():
            words = " ".join(str(v.get(k, "")) for k in ("reason", "source", "note", "fit_target") if v.get(k))
            docs.append((f"{nid}#{name}", f"{name.replace('_', ' ').replace('.', ' ')} = {v.get('value')}. {words}"))
    return docs


def _model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODEL, device="cpu")


def _index(notes_dir: str):
    import numpy as np
    docs = _doc_texts(all_notes(notes_dir))
    key = hashlib.sha256(json.dumps(docs).encode()).hexdigest()[:16]
    os.makedirs(CACHE_DIR, exist_ok=True)
    f = os.path.join(CACHE_DIR, f"{key}.npz")
    if os.path.exists(f):
        return docs, np.load(f)["emb"], None
    m = _model()
    emb = m.encode([f"passage: {t}" for _, t in docs], normalize_embeddings=True)
    np.savez(f, emb=emb)
    return docs, emb, m


def search(query: str, k: int = 5, notes_dir: str = NOTES_DIR) -> list[dict]:
    import numpy as np
    docs, emb, m = _index(notes_dir)
    m = m or _model()
    q = m.encode([f"query: {query}"], normalize_embeddings=True)[0]
    s = emb @ q
    top = np.argsort(-s)[:k]
    return [dict(ref=docs[i][0], score=round(float(s[i]), 3), text=docs[i][1]) for i in top]
