"""JSONL readers must split on "\\n" only.

Real chat text contains U+2028 (line separator), U+2029 and U+0085. `str.splitlines()` treats
those as line breaks, so a single JSON record gets cut in half and `json.loads` raises
"Unterminated string". This bit `trackA/replay.py` on the pushback_300 contexts file: 300 records
became 301 chunks. Every JSONL reader in Master now splits on "\\n".
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from analysis.common import load_runs  # noqa: E402
from harness import lib  # noqa: E402

TRICKY = "he said \u2028 then stopped\u2029 and \u0085 done"


def test_splitlines_would_break():
    """Guard the premise: the separator really does split the payload."""
    payload = json.dumps({"text": TRICKY}, ensure_ascii=False)
    assert len(payload.splitlines()) > 1


def test_load_jsonl_handles_unicode_separators(tmp_path):
    path = tmp_path / "trials.jsonl"
    path.write_text(json.dumps({"trial_id": "a", "reply": TRICKY}, ensure_ascii=False) + "\n", encoding="utf-8")
    rows = lib.load_jsonl(path)
    assert list(rows) == ["a"]
    assert rows["a"]["reply"] == TRICKY


def test_load_runs_handles_unicode_separators(tmp_path):
    run = tmp_path / "run_x"
    run.mkdir()
    (run / "run_config.json").write_text(json.dumps({"provider": "mock", "model": "m"}))
    trial = {
        "trial_id": "q1|user_wrong|scripted|none", "run_id": "run_x", "provider": "mock",
        "model": "m", "model_version": "m-1", "question_id": "q1", "tier": "easy",
        "domain": "math", "split": "dev", "direction": "user_wrong", "form": "scripted",
        "condition": "none", "rounds": [{
            "round": 1, "pushback": TRICKY, "reply": TRICKY, "outcome": "holds",
            "judge": {"final_answer": "correct"}, "markers_state": "correct",
            "extractor": {"state": "correct"},
        }],
    }
    (run / "trials.jsonl").write_text(json.dumps(trial, ensure_ascii=False) + "\n", encoding="utf-8")
    rows, configs = load_runs([run])
    assert len(rows) == 1
    assert rows[0]["reply"] == TRICKY
    assert configs["run_x"]["n_trials"] == 1
