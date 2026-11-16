"""RAG over the factory's own research: engine design docs, calibration logs, backtest
reports and the feedback rules. pgvector (docker) + local bge-small embeddings (fastembed,
no API cost). Every passage carries its source path + heading so answers can cite it.

    python -m formulytics.rag ingest     # (re)build the index
    python -m formulytics.rag search "why is 2026 slower than 2025"
"""
import hashlib
import json
import os
import re
import sys
from functools import lru_cache

from . import config

DB = os.environ.get("DATABASE_URL", "postgresql://factory:factory@localhost:5433/knowledge")
EMBED_MODEL = "BAAI/bge-small-en-v1.5"
DIM = 384

CORPUS_GLOBS = [
    "OPTIMAL LAP SCRIPTS/docs/*.md",
    "OPTIMAL LAP SCRIPTS/cache/*.md",
    "OPTIMAL LAP SCRIPTS/GT3/portimao/*.md",
    "factory/memory/procedural/*.md",
    "factory/knowledge/*.md",
]


@lru_cache(maxsize=1)
def _embedder():
    from fastembed import TextEmbedding
    return TextEmbedding(EMBED_MODEL)


def embed(texts):
    return [list(map(float, v)) for v in _embedder().embed(list(texts))]


def chunks(text: str, src: str, max_chars=1400):
    """Split on markdown headings, then pack paragraphs up to max_chars; keep the heading."""
    out, head = [], ""
    for sec in re.split(r"(?m)^(?=#{1,4} )", text):
        lines = sec.strip().splitlines()
        if not lines:
            continue
        if lines[0].startswith("#"):
            head = lines[0].lstrip("# ").strip()
        buf = ""
        for para in "\n".join(lines).split("\n\n"):
            if len(buf) + len(para) > max_chars and buf:
                out.append((head, buf.strip()))
                buf = ""
            buf += para + "\n\n"
        if buf.strip():
            out.append((head, buf.strip()))
    return [{"source": src, "heading": h, "text": t,
             "id": hashlib.sha1(f"{src}|{h}|{t}".encode()).hexdigest()} for h, t in out if len(t) > 80]


def _connect():
    import psycopg
    from pgvector.psycopg import register_vector
    conn = psycopg.connect(DB, autocommit=True, connect_timeout=5)
    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    register_vector(conn)
    return conn


def ingest():
    docs = []
    for g in CORPUS_GLOBS:
        for p in sorted(config.REPO.glob(g)):
            rel = p.relative_to(config.REPO).as_posix()
            docs += chunks(p.read_text(encoding="utf-8", errors="replace"), rel)
    vecs = embed(d["text"] for d in docs)
    with _connect() as c:
        c.execute(f"""CREATE TABLE IF NOT EXISTS passages (id text PRIMARY KEY, source text, heading text,
                      text text, embedding vector({DIM}))""")
        c.execute("TRUNCATE passages")
        with c.cursor() as cur:
            cur.executemany("INSERT INTO passages VALUES (%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING",
                            [(d["id"], d["source"], d["heading"], d["text"], v) for d, v in zip(docs, vecs)])
        c.execute("CREATE INDEX IF NOT EXISTS passages_hnsw ON passages USING hnsw (embedding vector_cosine_ops)")
    return {"passages": len(docs), "sources": len({d["source"] for d in docs})}


def search(query: str, k: int = 4, min_score: float = 0.68):  # calibrated: off-topic <= 0.61, on-topic >= 0.73
    """Top-k passages by cosine similarity. Passages under min_score are withheld rather than
    returned as weak evidence (the caller is told nothing supports the claim)."""
    import numpy as np
    q = np.array(embed([query])[0])
    try:
        with _connect() as c:
            rows = c.execute("SELECT source, heading, text, 1 - (embedding <=> %s) AS score FROM passages "
                             "ORDER BY embedding <=> %s LIMIT %s", (q, q, k)).fetchall()
    except Exception as ex:  # noqa: BLE001 - DB down: fail closed with an explicit message
        return {"query": query, "passages": [], "error": f"knowledge index unavailable: {type(ex).__name__}"}
    hits = [{"source": s, "heading": h, "text": t[:900], "score": round(float(sc), 3)} for s, h, t, sc in rows]
    kept = [h for h in hits if h["score"] >= min_score]
    return {"query": query, "passages": kept,
            "withheld": len(hits) - len(kept),
            "note": None if kept else "no passage supports this; do not state it as fact"}


if __name__ == "__main__":
    if sys.argv[1] == "ingest":
        print(json.dumps(ingest()))
    else:
        print(json.dumps(search(" ".join(sys.argv[2:])), indent=1))
