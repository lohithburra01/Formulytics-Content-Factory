"""HTTP API.

    uvicorn formulytics.api:app --app-dir factory
    POST /runs {"weekend": "sao_paulo_2026"}  -> 202 {"run_id": ...}
    GET  /runs/{run_id}                        -> status + manifest when done
    GET  /publish                              -> queued posts
"""
import json
import threading
import time
import uuid

from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel

from . import config

app = FastAPI(title="Formulytics content factory", version="0.1.0")
_status: dict[str, str] = {}
_lock = threading.Lock()  # one weekend at a time: the engine and the budget are shared


class RunRequest(BaseModel):
    weekend: str = "sao_paulo_2026"


def _do_run(run_id: str, weekend: str):
    from .run import run
    with _lock:
        _status[run_id] = "running"
        try:
            run(weekend, run_id=run_id)
            _status[run_id] = "done"
        except Exception as ex:  # noqa: BLE001
            _status[run_id] = f"failed: {type(ex).__name__}: {ex}"


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/runs", status_code=202)
def create_run(req: RunRequest, bg: BackgroundTasks):
    if not (config.WEEKENDS / f"{req.weekend}.json").exists():
        raise HTTPException(404, f"no toolkit for weekend {req.weekend}")
    run_id = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4]
    _status[run_id] = "queued"
    bg.add_task(_do_run, run_id, req.weekend)
    return {"run_id": run_id, "status": "queued"}


@app.get("/runs/{run_id}")
def get_run(run_id: str):
    m = config.RUNS / run_id / "manifest.json"
    if m.exists():
        return {"status": _status.get(run_id, "done"), "manifest": json.loads(m.read_text())}
    if run_id in _status:
        return {"status": _status[run_id]}
    raise HTTPException(404, "unknown run")


@app.get("/publish")
def publish_queue():
    return [json.loads(p.read_text()) for p in sorted(config.PUBLISH.glob("*/post.json"))
            if not (p.parent / "RETRACTED.md").exists()]
