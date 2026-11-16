"""Unit tests: no network, no LLM, no engine interpreter needed."""
import json
from types import SimpleNamespace

import pytest

from formulytics import config, gates, memory
from formulytics.ledger import Ledger
from formulytics.llm import BudgetExceeded, CostTracker

W = json.loads((config.WEEKENDS / "sao_paulo_2026.json").read_text(encoding="utf-8"))


def base_state(**kw):
    s = {"weekend": W, "sim": {"lap_s": 70.772, "vmax_kmh": 339, "vmin_kmh": 82},
         "gate": {"all_pass": True, "checks": [{"pass": True, "check": "x"}]},
         "trace_check": {"speed_corr": 0.97}, "label_s": 70.772,
         "facts": {"sim_lap_s": 70.772, "t2025_pole_s": 69.799, "vmax_kmh": 339}}
    s.update(kw)
    return s


# ---- gates fail closed -------------------------------------------------------
def test_realism_missing_is_failure():
    assert not gates.gate_realism({}).passed


def test_realism_engine_failure_propagates():
    st = base_state(gate={"all_pass": False, "checks": [{"pass": False, "check": "lap below rail"}]})
    r = gates.gate_realism(st)
    assert not r.passed and "lap below rail" in r.detail


def test_no_inflation_catches_label_bump():
    assert gates.gate_no_inflation(base_state()).passed
    assert not gates.gate_no_inflation(base_state(label_s=71.272)).passed  # the Mexico-style +0.5 s inflation


def test_real_trace_threshold():
    assert gates.gate_real_trace(base_state()).passed
    assert not gates.gate_real_trace(base_state(trace_check={"speed_corr": 0.90})).passed


def test_zoom_rule_and_documented_exception():
    assert gates.gate_zoom(base_state()).passed  # Interlagos zoom 20 has a documented exception
    w = json.loads(json.dumps(W))
    w["render"] = {"zoom": 18}
    assert not gates.gate_zoom(base_state(weekend=w)).passed
    w["render"] = {"zoom": 28}
    assert gates.gate_zoom(base_state(weekend=w)).passed


def test_no_api_xy():
    assert gates.gate_no_api_xy(base_state()).passed
    w = json.loads(json.dumps(W))
    w["sim"]["outline"] = "openf1_xy_position_feed.json"
    assert not gates.gate_no_api_xy(base_state(weekend=w)).passed


@pytest.mark.parametrize("text,ok", [
    ("Interlagos 2026 optimal lap: 1:10.772", True),
    ("1:10.772, about 0.973 s slower than the 2025 pole", True),
    ("Top speed 339 km/h", True),
    ("1:09.900, faster than 2025!", False),          # invented lap time
    ("Top speed 352 km/h", False),                    # invented speed
    ("on this 7-corner circuit", False),              # single-digit invented count (caught in a live run)
    ("#F1 #SaoPauloGP #2026", True),
    ("0.973s slower, 339km/h", True),                # units glued to numbers
    ("0.5s faster", False),                  # names and season tags are not claims
])
def test_claims_supported(text, ok):
    st = base_state(caption={"hook": "x", "text": text, "tags": ["#F1"]})
    st["facts"]["slower_than_2025_s"] = 0.973
    assert gates.gate_claims_supported(st).passed is ok


def test_delta_engine_rule():
    assert gates.gate_delta_engine(base_state(delta={"engine": "LAP COMPARISON/hifi_delta_v2.py"})).passed
    assert not gates.gate_delta_engine(base_state(delta={"engine": "delta_engine_v2.py"})).passed


def test_apex_geometry_on_synthetic_corner(tmp_path):
    """A circle of radius 50 m inside a 12 m wide ring: a line hugging the inner edge passes,
    a centre line (6 m from each edge) fails."""
    import math
    n = 400
    ring = lambda r: [[r * math.cos(2 * math.pi * i / n), r * math.sin(2 * math.pi * i / n)] for i in range(n)]  # noqa: E731
    outline = tmp_path / "o.json"
    outline.write_text(json.dumps({"outer": ring(62), "inner": ring(50)}))
    for r_line, expect in ((51.0, True), (56.0, False)):
        pts = ring(r_line)
        kap = [1 / r_line * (1 + 0.05 * math.cos(2 * math.pi * 3 * i / n)) for i in range(n)]  # 3 apex peaks
        rl = tmp_path / f"rl_{r_line}.json"
        rl.write_text(json.dumps({"raceline": pts, "kappa": kap}))
        ap = gates.apex_distances(rl, outline)
        assert ap, "apexes detected"
        assert all((a["inside_gap_m"] <= 1.5) is expect for a in ap)


def test_run_all_blocks_on_any_failure():
    st = base_state(caption={"hook": "x", "text": "1:09.000", "tags": []})
    rep = gates.run_all(st)
    assert not rep["all_pass"] and "claims_supported" in rep["blocking_failures"]


# ---- budget cap ---------------------------------------------------------------
def test_budget_cap_stops_calls(tmp_path):
    t = CostTracker(run_cap=0.0001, total_file=tmp_path / "spend.json")
    msg = SimpleNamespace(response_metadata={"model_name": "deepseek/deepseek-v4-pro"},
                          usage_metadata={"input_tokens": 100000, "output_tokens": 1000})
    t.on_chat_model_start({}, [], run_id="a")
    t.on_llm_end(SimpleNamespace(generations=[[SimpleNamespace(message=msg)]], llm_output={}), run_id="a")
    assert t.usd == pytest.approx((100000 * 0.90 + 1000 * 1.50) / 1e6)
    with pytest.raises(BudgetExceeded):
        t.on_chat_model_start({}, [], run_id="b")


# ---- memory + ledger --------------------------------------------------------------
def test_memory_recall_scores():
    memory.build_graph()
    ids = {n["id"] for n in memory.recall("mexico")["nodes"]}
    assert "result:mexico_2026" in ids


def test_ledger_roundtrip(tmp_path):
    lg = Ledger(tmp_path / "l.jsonl")
    lg.log("tool", tool="run_simulation", lap=70.772)
    lg.log("gate", gate="zoom")
    assert [r["kind"] for r in lg.read()] == ["tool", "gate"] and lg.read("gate")[0]["gate"] == "zoom"


# ---- API ------------------------------------------------------------------------
def test_api_rejects_unknown_weekend():
    from fastapi.testclient import TestClient
    from formulytics.api import app
    c = TestClient(app)
    assert c.get("/health").json() == {"ok": True}
    assert c.post("/runs", json={"weekend": "atlantis_2026"}).status_code == 404
