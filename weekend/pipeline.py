"""Stage framework: each stage is a function of (pack values it reads, outputs of the stages it
needs, its code). It runs in a fresh child process with a clean environment and writes ONLY
into its own folder  runs/<track>_<year>/<stage>/<key>/ , where key = hash of all three.
A finished folder (done.json) is reused, so a changed note reruns only the stages it reaches.

  python -m weekend.pipeline <stage> <pack.json>     # run one stage (and what it needs)
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Callable

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = os.environ.get("WEEKEND_RUNS_DIR") or os.path.join(ROOT, "runs")  # override = a clean second proof run
ENV_KEEP = ("SYSTEMROOT", "PATH", "TEMP", "TMP", "USERPROFILE", "LOCALAPPDATA", "APPDATA",
            "PROCESSOR_ARCHITECTURE", "NUMBER_OF_PROCESSORS", "OS", "WINDIR", "COMSPEC")
SIM = "@sim"   # read-spec meaning: every value the sim door needs


@dataclass
class Stage:
    name: str
    fn: Callable
    reads: list[str]
    needs: list[str] = field(default_factory=list)
    code: list[str] = field(default_factory=list)   # repo-relative files whose content is the code version


STAGES: dict[str, Stage] = {}
COMMON_CODE = ["weekend/pipeline.py", "weekend/simdoor.py", "sim_2026_lap.py",
               "cache/singapore/_sg_grip.py"]


def stage(name, reads, needs=(), code=()):
    def deco(fn):
        # the file defining the stage is part of its key: editing a stage's code reruns it
        own = os.path.relpath(sys.modules[fn.__module__].__file__, ROOT).replace(os.sep, "/")
        STAGES[name] = Stage(name, fn, list(reads), list(needs), list(code) + [own])
        return fn
    return deco


def _sha(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def is_sim_name(k: str) -> bool:
    return k.isupper() or k.startswith("env.") or k in ("track.street_grip_k", "sim.gain_cap_kmh_s", "sim.brake_preserve")


def selected(values: dict, reads: list[str]) -> dict:
    out = {}
    for k, v in values.items():
        for r in reads:
            if (r == SIM and is_sim_name(k)) or k == r or (r.endswith(".") and k.startswith(r)):
                out[k] = v
    return out


class P:
    """What a stage sees of the pack: only the values it declared."""

    def __init__(self, values: dict):
        self._v = values

    def __getitem__(self, name):
        if name not in self._v:
            raise KeyError(f"stage did not declare / pack lacks: {name}")
        return self._v[name].get("value")   # null values are dropped from the pack file

    def __contains__(self, name):
        return name in self._v

    def file(self, name) -> str:
        v = self._v[name]
        path = os.path.join(ROOT, v["value"])
        if _sha(path) != v["sha256"]:
            raise SystemExit(f"[pipeline] {name} changed since the pack was resolved: {path}")
        return path

    def sim_vals(self) -> dict:
        return {k: v.get("value") for k, v in self._v.items() if is_sim_name(k)}

    def prefixed(self, prefix) -> dict:
        return {k[len(prefix):]: v.get("value") for k, v in self._v.items() if k.startswith(prefix)}


def _load_pack(pack_file):
    with open(pack_file, encoding="utf-8") as fh:
        return json.load(fh)


def stage_key(st: Stage, pack: dict, up_keys: dict) -> str:
    # only what changes the output: the number and (for files) the content hash; note text
    # (reason, source, ...) is lineage, kept in inputs.json, and must not force a rerun
    vals = {k: [v.get("value"), v.get("sha256")] for k, v in selected(pack["values"], st.reads).items()}
    files = sorted(set(COMMON_CODE + st.code))
    blob = json.dumps(dict(vals=vals, up=up_keys,
                           code={f: _sha(os.path.join(ROOT, f)) for f in files}), sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def run_root(pack: dict) -> str:
    w = pack["weekend"]
    return os.path.join(RUNS, f"{w['track']}_{w['year']}")


def run_stage(name: str, pack_file: str, _memo=None) -> dict:
    """Run `name` (after what it needs). Returns {"key", "dir", "result"}."""
    import weekend.stages  # noqa: F401  (registers the stages)
    memo = {} if _memo is None else _memo
    if name in memo:
        return memo[name]
    st = STAGES[name]
    pack = _load_pack(pack_file)
    ups = {n: run_stage(n, pack_file, memo) for n in st.needs}
    key = stage_key(st, pack, {n: u["key"] for n, u in ups.items()})
    out = os.path.join(run_root(pack), name, key)
    done = os.path.join(out, "done.json")
    if not os.path.exists(done):
        tmp = out + ".partial"
        if os.path.exists(tmp):   # a crashed earlier attempt: set aside, never delete
            os.replace(tmp, f"{tmp}.{int(time.time())}")
        os.makedirs(tmp)
        sub = dict(values=selected(pack["values"], st.reads), weekend=pack["weekend"],
                   up={n: u["dir"] for n, u in ups.items()})
        with open(os.path.join(tmp, "inputs.json"), "w", encoding="utf-8") as fh:
            json.dump(sub, fh, indent=1, sort_keys=True)
        env = {k: os.environ[k] for k in ENV_KEEP if k in os.environ}
        t0 = time.time()
        print(f"[pipeline] {name} ({key}) ...", flush=True)
        with open(os.path.join(tmp, "log.txt"), "w", encoding="utf-8") as log:
            r = subprocess.run([sys.executable, "-m", "weekend.pipeline", "--child", name, tmp],
                               cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        if r.returncode != 0:
            raise RuntimeError(f"stage {name} failed (rc={r.returncode}); see {tmp}/log.txt")
        os.replace(tmp, out)
        print(f"[pipeline] {name} done in {time.time() - t0:.0f}s", flush=True)
    with open(done, encoding="utf-8") as fh:
        res = dict(key=key, dir=out, result=json.load(fh))
    memo[name] = res
    return res


def _child(name: str, out: str):
    sys.path.insert(0, ROOT)
    import weekend.stages  # noqa: F401
    with open(os.path.join(out, "inputs.json"), encoding="utf-8") as fh:
        sub = json.load(fh)
    result = STAGES[name].fn(P(sub["values"]), out, sub["up"], sub["weekend"]) or {}
    with open(os.path.join(out, "done.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1, sort_keys=True)


if __name__ == "__main__":
    # run through the importable module so stages register in the same STAGES dict
    sys.path.insert(0, ROOT)
    from weekend import pipeline as _pl
    if sys.argv[1] == "--child":
        _pl._child(sys.argv[2], sys.argv[3])
    else:
        print(json.dumps(_pl.run_stage(sys.argv[1], os.path.abspath(sys.argv[2])), indent=1))
