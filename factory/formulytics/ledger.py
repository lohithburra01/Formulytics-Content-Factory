"""Append-only audit ledger (JSONL). Every tool call, gate verdict, model call and decision
of a run lands here with a timestamp, so any published number can be traced to its source."""
import json
import threading
import time
from pathlib import Path


class Ledger:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def log(self, kind: str, **data):
        rec = {"ts": round(time.time(), 3), "kind": kind, **data}
        with self._lock, open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, default=str) + "\n")
        return rec

    def read(self, kind: str | None = None):
        if not self.path.exists():
            return []
        rows = [json.loads(l) for l in self.path.read_text(encoding="utf-8").splitlines() if l.strip()]
        return [r for r in rows if kind is None or r["kind"] == kind]
