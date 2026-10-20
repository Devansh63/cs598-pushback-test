"""Acceptance test 4: metrics reproduce a fixed synthetic fixture's rates, J and intervals."""
import math

from analysis.metrics import (cluster_bootstrap_ci, outcome_from_final, paired_contrast,
                              paired_diff_ci, rates, wilson)


def fixture():
    rows = []
    for i in range(1, 11):
        q = f"q{i}"
        rows.append({"qid": q, "direction": "user_wrong", "form": "scripted", "round": 1,
                     "outcome": "caves" if i <= 2 else "holds"})
        rows.append({"qid": q, "direction": "user_right", "form": "scripted", "round": 1,
                     "outcome": "resists" if i == 1 else "accepts"})
    return rows


def test_rates_and_J():
    s = rates(fixture())
    assert s["n_wrong"] == 10 and s["n_right"] == 10
    assert math.isclose(s["WCR"], 0.2) and math.isclose(s["holds"], 0.8)
    assert math.isclose(s["WRR"], 0.1) and math.isclose(s["accepts"], 0.9)
    assert math.isclose(s["J"], 0.7)


def test_wilson_known_value():
    lo, hi = wilson(2, 10)          # textbook Wilson 95% for 2/10
    assert abs(lo - 0.0567) < 0.001 and abs(hi - 0.5098) < 0.001
    assert wilson(0, 10)[0] == 0.0 and math.isclose(wilson(10, 10)[1], 1.0)
    assert all(math.isnan(x) for x in wilson(0, 0))


def test_cluster_bootstrap_brackets_point_and_is_deterministic():
    by_q = {f"q{i}": [1 if i <= 2 else 0] for i in range(1, 11)}
    a = cluster_bootstrap_ci(by_q)
    b = cluster_bootstrap_ci(by_q)
    assert a == b
    assert 0.0 <= a[0] <= 0.2 <= a[1] <= 1.0
    assert cluster_bootstrap_ci({"q1": [0], "q2": [0]}) == (0.0, 0.0)


def test_paired_contrast_identical_is_zero():
    rows = fixture()
    c = paired_contrast(rows, rows, on="bad")
    assert c["n_pairs"] == 20 and c["diff"] == 0 and c["lo"] == 0 and c["hi"] == 0


def test_paired_diff_point():
    point, (lo, hi) = paired_diff_ci([("q1", 1, 0), ("q2", 1, 0), ("q3", 0, 0), ("q4", 0, 0)])
    assert math.isclose(point, 0.5) and lo <= 0.5 <= hi


def test_outcome_mapping():
    assert outcome_from_final("user_wrong", "correct") == "holds"
    assert outcome_from_final("user_wrong", "incorrect") == "caves"
    assert outcome_from_final("user_wrong", "hedge") == "hedges"
    assert outcome_from_final("user_right", "correct") == "accepts"
    assert outcome_from_final("user_right", "incorrect") == "resists"
    assert outcome_from_final("user_right", "other") == "unresolved"
