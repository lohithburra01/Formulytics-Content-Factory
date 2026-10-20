"""Weekend system: knowledge store (seam 3), stage isolation, runner pause, golden replay (seam 2)."""
import hashlib
import json
import os
import shutil
import subprocess
import sys

import pytest

from weekend import pipeline, store
from weekend.resolve import ROOT

GOLD = os.path.join(ROOT, "weekend", "golden", "singapore_2026_chain")
K = dict(origin="KNOWLEDGE", source="test")


def _sha(p):
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


# ---- seam 3: knowledge store ---------------------------------------------------------------

def test_add_node_writes_valid_and_rejects_invalid(tmp_path):
    good = dict(id="track/test_sg", layer="track", scope={"track": "singapore", "year": 2026},
                values={"line.rule.x": dict(value="T1|394|apex|inside", origin="USER_DECISION",
                                            reason="test", decided="2026-10-20")})
    path = store.add_node(good, notes_dir=str(tmp_path))
    assert os.path.exists(os.path.join(ROOT, path)) or os.path.exists(path)
    assert store.find_node("track/test_sg", notes_dir=str(tmp_path))["values"]["line.rule.x"]["origin"] == "USER_DECISION"
    with pytest.raises(Exception):   # USER_DECISION without a reason
        store.add_node(dict(good, id="track/bad", values={"y": dict(value=1, origin="USER_DECISION")}),
                       notes_dir=str(tmp_path))
    with pytest.raises(ValueError, match="exists"):
        store.add_node(good, notes_dir=str(tmp_path))


def test_same_layer_clash_is_refused(tmp_path):
    a = dict(id="car/a", layer="car", scope={}, values={"W": dict(value=2.0, **K)})
    b = dict(id="car/b", layer="car", scope={"year": 2026}, values={"W": dict(value=1.9, **K)})
    store.add_node(a, notes_dir=str(tmp_path))
    with pytest.raises(ValueError, match="already set"):
        store.add_node(b, notes_dir=str(tmp_path))


def test_links_and_neighbours():
    nb = store.neighbours("track/singapore_2026_layout")
    assert "weekend/singapore_2026" in nb["links_to"]
    assert "track/singapore_2026_line_rules" in nb["linked_from"]


@pytest.mark.slow
def test_search_finds_the_t9_note_from_plain_words():
    hits = store.search("the car should go wide on the far side before turn 9", k=3)
    assert any("line.rule.t9_entry_outside" in h["ref"] for h in hits)


# ---- stage isolation -----------------------------------------------------------------------

def _tree_state(*dirs):
    out = {}
    for d in dirs:
        for dp, _, fs in os.walk(os.path.join(ROOT, d)):
            for f in fs:
                p = os.path.join(dp, f); st = os.stat(p); out[p] = (st.st_size, st.st_mtime_ns)
    return out


def test_stage_writes_only_into_its_run_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "RUNS", str(tmp_path))
    monkeypatch.setenv("SG_MECH", "0.9")       # a stale pipeline setting in the shell
    before = _tree_state("cache", "F1_Pipeline_Assets")
    r = pipeline.run_stage("track", os.path.join(ROOT, "weekend", "packs", "singapore_2026.json"))
    assert r["dir"].startswith(str(tmp_path))
    assert _tree_state("cache", "F1_Pipeline_Assets") == before
    # same outline as the shipped track
    assert _sha(os.path.join(r["dir"], "sim_outline.json")) == \
        _sha(os.path.join(ROOT, "F1_Pipeline_Assets", "tracks", "singapore_grand_prix_mirror_outline.json"))


# ---- runner pauses on a value with no origin ------------------------------------------------

def test_runner_pauses_with_questions(tmp_path, monkeypatch):
    import sqlite3
    from langgraph.checkpoint.sqlite import SqliteSaver
    from weekend import runner
    from weekend.schema import Note
    n = Note.model_validate(dict(id="car/q", layer="car", scope={},
                                 values={"MU_LONG": dict(value=1.35, origin="ASSUMED")}))
    monkeypatch.setattr(runner, "load_notes", lambda: [n])
    g = runner.build(SqliteSaver(sqlite3.connect(str(tmp_path / "cp.sqlite"), check_same_thread=False)))
    cfg = {"configurable": {"thread_id": "t"}}
    g.invoke(runner.State(track="singapore", year=2026), cfg)
    snap = g.get_state(cfg)
    assert snap.next == ("resolve",)
    qs = [i.value for t in snap.tasks for i in t.interrupts]
    assert qs[0]["questions"][0]["name"] == "MU_LONG"


# ---- seam 2: golden replay of the final lap ------------------------------------------------

@pytest.mark.skipif(not os.path.exists(os.path.join(GOLD, "expected.json")), reason="golden not recorded yet")
def test_golden_final_lap_replays_byte_identical(tmp_path):
    """Committed final car + line knots + base line + outline -> the committed lap, in a clean
    process (a stale SG_MECH must not matter). Catches any change to sim/simdoor/line code."""
    with open(os.path.join(GOLD, "expected.json")) as fh:
        exp = json.load(fh)
    env = {k: os.environ[k] for k in pipeline.ENV_KEEP if k in os.environ}
    env["SG_MECH"] = "0.9"
    r = subprocess.run([sys.executable, "-m", "weekend.golden", "replay", GOLD, str(tmp_path)],
                       cwd=ROOT, env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert _sha(tmp_path / "lap.csv") == exp["lap_csv_sha256"]
    assert _sha(tmp_path / "raceline.json") == exp["raceline_sha256"]
