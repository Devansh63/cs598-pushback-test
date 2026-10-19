"""Inter-coder agreement for two filled coding sheets.

Reports, per label: Cohen's kappa, raw agreement, and each coder's frequency.
Binary columns (s_*, t_*, is_pushback, checkable_claim) are compared as 0/1; 'user_claim'
is compared as a nominal label. Rows either coder left blank on is_pushback are dropped.
Kappa is computed only on rows both coders marked as pushback (is_pushback = 1), except for
is_pushback itself.

Also writes a disagreements CSV for adjudication.

Usage: python3 -I phase1/agreement.py outputs/phase1/pilot50_sahil.csv outputs/phase1/pilot50_devansh.csv
"""
import sys
from pathlib import Path

import pandas as pd
from sklearn.metrics import cohen_kappa_score

YES = {"1", "y", "yes", "true", "x"}


def as_bin(s):
    return s.fillna("").astype(str).str.strip().str.lower().isin(YES).astype(int)


def main(a_path, b_path):
    a, b = pd.read_csv(a_path, dtype=str), pd.read_csv(b_path, dtype=str)
    m = a.merge(b, on="item_id", suffixes=("_a", "_b"))
    filled = m["is_pushback_a"].notna() & m["is_pushback_b"].notna()
    m = m[filled]
    labels = [c for c in a.columns if c.startswith(("s_", "t_"))]
    rows = []

    def add(name, x, y, n):
        agree = (x == y).mean()
        kappa = cohen_kappa_score(x, y) if len(set(x) | set(y)) > 1 else float("nan")
        rows.append({"label": name, "n": n, "kappa": round(kappa, 3), "raw_agreement": round(agree, 3),
                     "freq_a": round(pd.Series(x).astype(str).isin(["1"]).mean(), 3) if name != "user_claim" else "",
                     "freq_b": round(pd.Series(y).astype(str).isin(["1"]).mean(), 3) if name != "user_claim" else ""})

    add("is_pushback", as_bin(m["is_pushback_a"]), as_bin(m["is_pushback_b"]), len(m))
    both = m[(as_bin(m["is_pushback_a"]) == 1) & (as_bin(m["is_pushback_b"]) == 1)]
    for col in ["checkable_claim"] + labels:
        add(col, as_bin(both[f"{col}_a"]), as_bin(both[f"{col}_b"]), len(both))
    ua = both["user_claim_a"].fillna("").str.strip().str.lower()
    ub = both["user_claim_b"].fillna("").str.strip().str.lower()
    add("user_claim", ua, ub, len(both))

    report = pd.DataFrame(rows)
    print(report.to_string(index=False))
    out = Path(a_path).with_name("agreement_report.csv")
    report.to_csv(out, index=False)

    diff_cols = ["is_pushback", "checkable_claim", "user_claim"] + labels
    mask = pd.Series(False, index=m.index)
    for c in diff_cols:
        mask |= m[f"{c}_a"].fillna("").str.strip().str.lower() != m[f"{c}_b"].fillna("").str.strip().str.lower()
    keep = ["item_id", "pushback_a"] + [f"{c}_{s}" for c in diff_cols for s in "ab"]
    m.loc[mask, keep].to_csv(out.with_name("disagreements.csv"), index=False)
    print(f"\n{int(mask.sum())} items with any disagreement -> {out.with_name('disagreements.csv')}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
