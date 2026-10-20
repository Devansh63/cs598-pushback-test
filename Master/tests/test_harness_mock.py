"""Acceptance tests 1–3 offline: run_pilot and run_multiround produce the unified trial schema.
(The live gemini/deepseek variants of tests 1–2 are in tests/run_acceptance.sh and need keys.)"""
import json
import shutil
from pathlib import Path

from harness import run_multiround, run_pilot
from harness.lib import RESULTS

REQUIRED = {"trial_id", "run_id", "provider", "model", "model_version", "temperature", "condition",
            "question_id", "tier", "domain", "direction", "form", "claim", "initial_answer", "rounds", "ts"}
ROUND_REQUIRED = {"round", "pushback", "reply", "outcome", "markers_fired", "judge"}
OUTCOMES = {"holds", "hedges", "caves", "accepts", "unresolved", "resists"}


def _run(fn, run_id, extra):
    d = RESULTS / run_id
    shutil.rmtree(d, ignore_errors=True)
    rc = fn(["--provider", "mock", "--model", "mock-1", "--judge-provider", "mock",
             "--judge-model", "mock-judge", "--run-id", run_id] + extra)
    assert rc == 0
    rows = [json.loads(l) for l in (d / "trials.jsonl").read_text().splitlines() if l.strip()]
    cfg = json.loads((d / "run_config.json").read_text())
    shutil.rmtree(d, ignore_errors=True)
    return rows, cfg


def test_run_pilot_four_trials_unified_schema():
    rows, cfg = _run(run_pilot.main, "_test_pilot", ["--limit", "4"])
    assert len(rows) == 4
    for r in rows:
        assert REQUIRED <= set(r), REQUIRED - set(r)
        assert len(r["rounds"]) == 1 and ROUND_REQUIRED <= set(r["rounds"][0])
        assert r["rounds"][0]["outcome"] in OUTCOMES
        assert r["temperature"] == 0.0
    assert {"provider", "model", "temperature", "judge_model", "commit", "started", "n_trials_planned"} <= set(cfg)


def test_run_pilot_all_conditions_including_control():
    rows, _ = _run(run_pilot.main, "_test_conditions",
                   ["--limit", "12", "--conditions", "none,instruct,reframe,verify_only,verify_type,no_pushback"])
    conds = {r["condition"] for r in rows}
    assert conds == {"none", "instruct", "reframe", "verify_only", "verify_type", "no_pushback"}
    v = [r for r in rows if r["condition"] in ("verify_only", "verify_type")]
    assert all(r["verification"] for r in v)
    ctrl = [r for r in rows if r["condition"] == "no_pushback"]
    assert ctrl and all(r["form"] == "none" for r in ctrl)


def test_run_multiround_three_rounds_labelled():
    rows, cfg = _run(run_multiround.main, "_test_multi", ["--limit", "2"])
    assert len(rows) == 2 and cfg["rounds"] == 3
    for r in rows:
        assert [x["round"] for x in r["rounds"]] == [1, 2, 3]
        assert all(x["outcome"] in OUTCOMES for x in r["rounds"])
        assert r["rounds"][1]["pushback"] != r["rounds"][0]["pushback"]


def test_resume_skips_done():
    d = RESULTS / "_test_resume"
    shutil.rmtree(d, ignore_errors=True)
    args = ["--provider", "mock", "--model", "mock-1", "--judge-provider", "mock", "--judge-model", "mock-judge",
            "--run-id", "_test_resume", "--limit", "3"]
    run_pilot.main(args)
    n1 = len((d / "trials.jsonl").read_text().splitlines())
    run_pilot.main(args)
    n2 = len((d / "trials.jsonl").read_text().splitlines())
    shutil.rmtree(d, ignore_errors=True)
    assert n1 == n2 == 3
