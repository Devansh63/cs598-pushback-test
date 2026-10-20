"""Acceptance test 5: measure_pr reproduces precision/recall from a saved fixture."""
import json
from pathlib import Path

from phase1.measure_pr import estimate

FX = Path(__file__).parent / "fixtures" / "measure_pr_fixture.json"


def expand(counts):
    return [label for label, n in counts.items() for _ in range(n)]


def test_fixture_reproduces_devansh_measurement():
    fx = json.loads(FX.read_text())
    est = estimate(fx["n_cand_frame"], fx["n_non_frame"],
                   expand(fx["cand_labels_counts"]), expand(fx["non_labels_counts"]))
    exp = fx["expected"]
    assert abs(est["precision"] - exp["precision"]) < 0.0005
    assert abs(est["recall"] - exp["recall"]) < 0.0005
    assert abs(est["n_eff_kish"] - exp["n_eff_kish"]) < 0.1
    assert abs(est["estimated_tp_in_frame"] - exp["estimated_tp_in_frame"]) < 0.01
    assert abs(est["estimated_fn_in_frame"] - exp["estimated_fn_in_frame"]) < 0.01
    lo, hi = est["precision_wilson"]
    assert lo < 0.580 < hi and abs(lo - 0.500) < 0.002 and abs(hi - 0.656) < 0.002


def test_degenerate_inputs():
    est = estimate(10, 90, ["pushback_disagreement"] * 10, ["other"] * 10)
    assert est["precision"] == 1.0 and est["recall"] == 1.0
