"""Client for engine_bridge.py: runs the deterministic toolkit in the engine's interpreter."""
import json
import subprocess

from . import config

BRIDGE = config.FACTORY / "engine_bridge.py"


class EngineError(RuntimeError):
    pass


def call(command: str, timeout: int = 1800, **args) -> dict:
    r = subprocess.run([config.ENGINE_PYTHON, str(BRIDGE), command, json.dumps(args)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=timeout, env={**__import__("os").environ, "ENGINE_ROOT": str(config.ENGINE_ROOT)})
    lines = [l for l in r.stdout.splitlines() if l.strip().startswith("{")]
    if not lines:
        raise EngineError(f"{command}: no JSON from bridge (exit {r.returncode}): {r.stderr[-800:]}")
    return json.loads(lines[-1])


def weekend(wid: str) -> dict:
    return json.loads((config.WEEKENDS / f"{wid}.json").read_text(encoding="utf-8"))
