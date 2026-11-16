"""Model routing (Pro for planning/judging, Flash for workers), fallbacks, cost + budget cap.

All models go through OpenRouter's OpenAI-compatible API, so changing provider is a ROUTES edit.
DeepSeek on OpenRouter applies automatic prompt caching; cached prompt tokens are read back
from the usage block and reported per call.
"""
import json
import os
import threading
import time
from pathlib import Path

from langchain_core.callbacks import BaseCallbackHandler
from langchain_openai import ChatOpenAI

from . import config


class BudgetExceeded(RuntimeError):
    pass


class CostTracker(BaseCallbackHandler):
    """Per-run token/cost/latency accounting with a hard stop (fail closed on budget)."""

    raise_error = True  # let BudgetExceeded propagate out of the callback

    def __init__(self, ledger=None, run_cap=config.BUDGET_USD_PER_RUN,
                 total_file: Path = config.RUNS / "_spend.json"):
        self.ledger, self.run_cap, self.total_file = ledger, run_cap, Path(total_file)
        self.calls, self.usd = [], 0.0
        self._t0, self._lock = {}, threading.Lock()

    def _total(self):
        try:
            return json.loads(self.total_file.read_text())["usd"]
        except Exception:  # noqa: BLE001
            return 0.0

    def on_chat_model_start(self, serialized, messages, *, run_id, **kw):
        self._t0[run_id] = time.time()
        if self.usd >= self.run_cap or self._total() >= config.BUDGET_USD_TOTAL:
            raise BudgetExceeded(f"budget cap reached (run ${self.usd:.4f}/{self.run_cap}, "
                                 f"total ${self._total():.4f}/{config.BUDGET_USD_TOTAL})")

    def on_llm_end(self, response, *, run_id, **kw):
        gen = response.generations[0][0]
        msg = getattr(gen, "message", None)
        meta = (getattr(msg, "response_metadata", None) or {})
        model = meta.get("model_name") or (response.llm_output or {}).get("model_name", "?")
        um = getattr(msg, "usage_metadata", None) or {}
        p_in, p_out = um.get("input_tokens", 0), um.get("output_tokens", 0)
        cached = (um.get("input_token_details") or {}).get("cache_read", 0)
        base = next((k for k in config.PRICES if model.startswith(k)), None)
        pin, pout = config.PRICES.get(base, (1.0, 2.0))
        list_usd = (p_in * pin + p_out * pout) / 1e6
        billed = (meta.get("token_usage") or {}).get("cost")  # OpenRouter's actual charge, cache discount included
        usd = float(billed) if billed is not None else list_usd
        rec = {"model": model, "in": p_in, "out": p_out, "cached_in": cached, "usd": round(usd, 6),
               "list_usd": round(list_usd, 6), "billed": billed is not None,
               "latency_s": round(time.time() - self._t0.pop(run_id, time.time()), 2)}
        with self._lock:
            self.calls.append(rec)
            self.usd += usd
            self.total_file.parent.mkdir(parents=True, exist_ok=True)
            self.total_file.write_text(json.dumps({"usd": round(self._total() + usd, 6)}))
        if self.ledger:
            self.ledger.log("llm_call", **rec)

    def summary(self):
        by = {}
        for c in self.calls:
            b = by.setdefault(c["model"], {"calls": 0, "in": 0, "out": 0, "cached_in": 0, "usd": 0.0, "list_usd": 0.0, "latency_s": 0.0})
            for k in ("in", "out", "cached_in", "usd", "list_usd", "latency_s"):
                b[k] += c[k]
            b["calls"] += 1
        return {"usd": round(self.usd, 5), "calls": len(self.calls), "by_model": by}


def _one(model_id: str, callbacks, temperature: float):
    return ChatOpenAI(model=model_id, base_url=config.OPENROUTER_BASE,
                      api_key=os.environ["OPENROUTER_API_KEY"], temperature=temperature,
                      timeout=180, max_retries=2, callbacks=callbacks,
                      default_headers={"X-Title": "formulytics-content-factory"})


def make_model(role: str, tracker: CostTracker | None = None, temperature: float = 0.2):
    """Primary chat model for the role (route = config.ROUTES[role][0])."""
    return _one(config.ROUTES[role][0], [tracker] if tracker else None, temperature)


def fallback_middleware(role: str, tracker: CostTracker | None = None, temperature: float = 0.2):
    """Agent middleware that retries a failed model call on the next model in the route."""
    from langchain.agents.middleware import ModelFallbackMiddleware
    rest = [_one(m, [tracker] if tracker else None, temperature) for m in config.ROUTES[role][1:]]
    return ModelFallbackMiddleware(*rest)
