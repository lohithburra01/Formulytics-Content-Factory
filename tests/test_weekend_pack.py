"""Weekend Pack: resolver rules (seam 1) and Singapore golden run (seam 2)."""
import json
import os

import pytest
import yaml
from pydantic import ValidationError

from weekend.resolve import ROOT, Unresolved, load_notes, pack_path, resolve_pack
from weekend import pipeline


def _sha256(p):
    import hashlib
    with open(p, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()
from weekend.schema import Note, Value

SG = dict(track="singapore", year=2026)


def _write(tmp_path, layer, note):
    d = tmp_path / layer
    d.mkdir(exist_ok=True)
    (d / f"{note['id'].replace('/', '_')}.yaml").write_text(yaml.safe_dump(note))


def _note(id, layer, scope, **values):
    return dict(id=id, layer=layer, scope=scope, values=values)


K = dict(origin="KNOWLEDGE", source="test")


# ---- seam 1: resolve_pack ------------------------------------------------

def test_most_specific_layer_wins(tmp_path):
    _write(tmp_path, "car", _note("car/x", "car", {"year": 2026}, CDA={"value": 0.8, **K}))
    _write(tmp_path, "weekend", _note("weekend/sg", "weekend", SG, CDA={
        "value": 0.5581, "origin": "FITTED", "source": "fit", "fit_target": "top speed",
        "fit_range": [0.45, 1.3]}))
    pack = resolve_pack(load_notes(str(tmp_path)), SG)
    assert pack.values["CDA"].value == 0.5581
    assert pack.values["CDA"].origin == "FITTED"
    assert pack.values["CDA"].layer == "weekend"


def test_other_track_note_never_leaks_in(tmp_path):
    _write(tmp_path, "track", _note("track/canada", "track", {"track": "canada", "year": 2026},
                                    INSET={"value": 0.0, **K}))
    _write(tmp_path, "track", _note("track/sg", "track", SG, OTHER={"value": 1.0, **K}))
    pack = resolve_pack(load_notes(str(tmp_path)), SG)
    assert "INSET" not in pack.values


def test_assumed_value_becomes_a_question_not_a_default(tmp_path):
    _write(tmp_path, "car", _note("car/x", "car", {}, MU_LONG={"value": 1.35, "origin": "ASSUMED"}))
    with pytest.raises(Unresolved) as e:
        resolve_pack(load_notes(str(tmp_path)), SG)
    assert [q["name"] for q in e.value.questions] == ["MU_LONG"]


def test_same_value_twice_in_one_layer_is_a_conflict(tmp_path):
    _write(tmp_path, "car", _note("car/a", "car", {}, W={"value": 2.0, **K}))
    _write(tmp_path, "car", _note("car/b", "car", {}, W={"value": 1.9, **K}))
    with pytest.raises(ValueError, match="set twice"):
        resolve_pack(load_notes(str(tmp_path)), SG)


@pytest.mark.parametrize("bad", [
    dict(value=1.0, origin="KNOWLEDGE"),                                   # no source
    dict(value=1.0, origin="USER_DECISION", reason="because"),             # no date
    dict(value=9.0, origin="FITTED", source="fit", fit_target="t", fit_range=[0, 1]),  # out of range
    dict(value=1.0, origin="FITTED", source="fit"),                        # no range/target
    dict(value=1.0, origin="GUESS", source="x"),                           # not an origin
])
def test_invalid_values_are_rejected(bad):
    with pytest.raises(ValidationError):
        Value(**bad)


def test_real_notes_are_valid_and_every_pack_value_has_an_origin():
    notes = load_notes()
    assert all(isinstance(n, Note) for n in notes)
    pack = resolve_pack(notes, SG)
    assert pack.values and all(v.origin != "ASSUMED" for v in pack.values.values())


# ---- seam 2: run(pack) ---------------------------------------------------

GOLDEN = os.path.join(ROOT, "weekend", "golden", "singapore_2026.json")


def test_committed_pack_matches_the_notes():
    with open(pack_path(SG), encoding="utf-8") as fh:
        committed = json.load(fh)
    fresh = json.loads(resolve_pack(load_notes(), SG).model_dump_json(exclude_none=True))
    assert committed == fresh, "notes changed: re-run `python -m weekend.resolve singapore 2026`"


def test_shipped_final_step_still_byte_identical(tmp_path, monkeypatch):
    """The ported v4b final step (fixed shipped line, shipped car) through the stage framework
    reproduces the shipped lap exactly, with stale pipeline env-vars in the shell."""
    monkeypatch.setenv("SG_MECH", "0.9")
    monkeypatch.setenv("KGRIP_STENCIL", "9")
    with open(GOLDEN, encoding="utf-8") as fh:
        golden = json.load(fh)
    keys = set()
    for sub in ("a", "b"):
        monkeypatch.setattr(pipeline, "RUNS", str(tmp_path / sub))
        r = pipeline.run_stage("final_fixed", pack_path(SG))
        keys.add(r["key"])
        assert _sha256(os.path.join(r["dir"], "lap.csv")) == golden["lap_csv_sha256"]
        assert _sha256(os.path.join(r["dir"], "raceline.json")) == golden["raceline_sha256"]
        assert r["result"]["lap_s"] == golden["lap_s"]
    assert len(keys) == 1


def test_changed_input_file_is_refused(tmp_path, monkeypatch):
    with open(pack_path(SG), encoding="utf-8") as fh:
        pack = json.load(fh)
    pack["values"]["line.fixed_raceline_file"]["sha256"] = "0" * 64
    p = tmp_path / "pack.json"
    p.write_text(json.dumps(pack))
    monkeypatch.setattr(pipeline, "RUNS", str(tmp_path / "runs"))
    with pytest.raises(RuntimeError):
        pipeline.run_stage("final_fixed", str(p))


def test_stage_key_ignores_note_text_but_not_numbers():
    """Rewording a note's reason must not rerun a stage; changing its number must."""
    import copy
    import weekend.stages  # noqa: F401
    pack = pipeline._load_pack(pack_path(SG))
    st = pipeline.STAGES["final_fixed"]
    k0 = pipeline.stage_key(st, pack, {})
    worded = copy.deepcopy(pack)
    worded["values"]["MASS_KG"]["reason"] = "reworded"
    assert pipeline.stage_key(st, worded, {}) == k0
    moved = copy.deepcopy(pack)
    moved["values"]["MASS_KG"]["value"] += 1
    assert pipeline.stage_key(st, moved, {}) != k0
