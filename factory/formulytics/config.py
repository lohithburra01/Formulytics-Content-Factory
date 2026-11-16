"""Single source of configuration. Swapping provider/model is one line in ROUTES."""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

FACTORY = Path(__file__).resolve().parent.parent
REPO = FACTORY.parent
ENGINE_ROOT = Path(os.environ.get("ENGINE_ROOT", REPO / "OPTIMAL LAP SCRIPTS"))
# The physics/delta/render engine keeps its own interpreter (numpy/scipy/quadprog/fastf1).
_DEV_ENGINE = r"C:\Users\91910\AppData\Local\Programs\Python\Python310\python.exe"
ENGINE_PYTHON = os.environ.get("ENGINE_PYTHON") or (_DEV_ENGINE if Path(_DEV_ENGINE).exists() else sys.executable)
RUNS = FACTORY / "runs"
PUBLISH = FACTORY / "publish"
MEMORY = FACTORY / "memory"
WEEKENDS = FACTORY / "weekends"

load_dotenv(FACTORY / ".env")

OPENROUTER_BASE = "https://openrouter.ai/api/v1"

# role -> ordered model chain (first = primary, rest = fallbacks). Ids verified against
# https://openrouter.ai/api/v1/models on 2026-11-16.
ROUTES = {
    "orchestrator": ["deepseek/deepseek-v4-pro", "deepseek/deepseek-v4-flash"],
    "critic": ["deepseek/deepseek-v4-pro", "deepseek/deepseek-v4-flash"],
    "judge": ["deepseek/deepseek-v4-pro", "deepseek/deepseek-v4-flash"],
    "worker": ["deepseek/deepseek-v4-flash", "deepseek/deepseek-v3.2"],
}

# USD per 1M tokens (prompt, completion) from the OpenRouter models endpoint, 2026-11-16.
PRICES = {
    "deepseek/deepseek-v4-pro": (0.90, 1.50),
    "deepseek/deepseek-v4-flash": (0.09, 0.18),
    "deepseek/deepseek-v3.2": (0.26, 0.38),
}

BUDGET_USD_PER_RUN = float(os.environ.get("BUDGET_USD_PER_RUN", "0.75"))
BUDGET_USD_TOTAL = float(os.environ.get("BUDGET_USD_TOTAL", "10.0"))  # hard key cap
