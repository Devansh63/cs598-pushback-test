"""Acceptance test 6: agreement.py on two filled sheets gives per-label kappa."""
import csv
import math

from analysis.agreement import kappa, main as agreement_main

COLS = ["item_id", "pushback", "is_pushback", "checkable_claim", "s_bare", "s_alt_answer", "t_frustration", "user_claim", "pbc_type", "notes"]


def write(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in COLS})


def test_kappa_values():
    assert kappa([1, 1, 0, 0], [1, 1, 0, 0]) == 1.0
    assert math.isclose(kappa([1, 1, 0, 0], [1, 0, 0, 1]), 0.0)
    assert math.isnan(kappa([1, 1], [1, 1]))          # one category only: undefined


def test_two_sheets(tmp_path):
    a = [{"item_id": f"i{k}", "pushback": "x", "is_pushback": 1, "checkable_claim": 1 if k % 2 else "",
          "s_bare": "" if k % 2 else 1, "s_alt_answer": 1 if k % 2 else "", "t_frustration": 1 if k == 1 else "",
          "user_claim": "incorrect" if k % 2 else "", "pbc_type": "factual_correction"} for k in range(8)]
    b = [dict(r) for r in a]
    b[0]["s_bare"] = ""           # one disagreement on s_bare
    b[3]["t_frustration"] = 1     # one on t_frustration
    pa, pb = tmp_path / "a.csv", tmp_path / "b.csv"
    write(pa, a)
    write(pb, b)
    rows = {r["label"]: r for r in agreement_main(str(pa), str(pb), str(tmp_path / "rep.csv"))}
    assert rows["is_pushback"]["n"] == 8
    assert rows["s_alt_answer"]["kappa"] == 1.0
    assert 0 < rows["s_bare"]["kappa"] < 1
    assert rows["user_claim"]["raw_agreement"] == 1.0
    assert (tmp_path / "disagreements_coding.csv").exists()
