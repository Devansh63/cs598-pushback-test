"""Inter-coder agreement for two filled coding sheets (codebook v2 columns).

  python3 analysis/agreement.py sheet_coderA.csv sheet_coderB.csv [--out agreement_report.csv]

Per label: Cohen's kappa, raw agreement, each coder's frequency. Binary columns (s_*, t_*, x_*,
is_pushback, checkable_claim) are compared as 0/1; `user_claim` and `pbc_type` as nominal.
Kappa for everything except is_pushback is computed on rows BOTH coders marked is_pushback = 1.
Rows either coder left blank on is_pushback are dropped. A disagreements CSV is written beside
the report for adjudication.
"""
import argparse
import csv
from pathlib import Path

YES = {"1", "y", "yes", "true", "x"}


def as_bin(v):
    return 1 if str(v or "").strip().lower() in YES else 0


def kappa(xs, ys):
    n = len(xs)
    if n == 0:
        return float("nan")
    cats = sorted(set(xs) | set(ys))
    if len(cats) < 2:
        return float("nan")
    po = sum(1 for x, y in zip(xs, ys) if x == y) / n
    pe = sum((xs.count(c) / n) * (ys.count(c) / n) for c in cats)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def read(path):
    with open(path, newline="", encoding="utf-8") as f:
        return {r["item_id"]: r for r in csv.DictReader(f)}


def main(a_path, b_path, out_path=None):
    A, B = read(a_path), read(b_path)
    common = [i for i in A if i in B and str(A[i].get("is_pushback", "")).strip() and str(B[i].get("is_pushback", "")).strip()]
    labels = [c for c in next(iter(A.values())).keys() if c.startswith(("s_", "t_", "x_"))]
    rows = []

    def add(name, xs, ys, binary=True):
        raw = sum(1 for x, y in zip(xs, ys) if x == y) / len(xs) if xs else float("nan")
        rows.append({"label": name, "n": len(xs), "kappa": round(kappa(xs, ys), 3), "raw_agreement": round(raw, 3),
                     "freq_a": round(sum(xs) / len(xs), 3) if binary and xs else "",
                     "freq_b": round(sum(ys) / len(ys), 3) if binary and ys else ""})

    add("is_pushback", [as_bin(A[i]["is_pushback"]) for i in common], [as_bin(B[i]["is_pushback"]) for i in common])
    both = [i for i in common if as_bin(A[i]["is_pushback"]) and as_bin(B[i]["is_pushback"])]
    for col in ["checkable_claim"] + labels:
        add(col, [as_bin(A[i].get(col)) for i in both], [as_bin(B[i].get(col)) for i in both])
    for col in ("user_claim", "pbc_type"):
        if col in next(iter(A.values())):
            add(col, [str(A[i].get(col, "")).strip().lower() for i in both],
                [str(B[i].get(col, "")).strip().lower() for i in both], binary=False)

    out = Path(out_path) if out_path else Path(a_path).with_name("agreement_report.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    diff_cols = ["is_pushback", "checkable_claim", "user_claim", "pbc_type"] + labels
    dis = []
    for i in common:
        d = {c: (A[i].get(c, ""), B[i].get(c, "")) for c in diff_cols if c in A[i]
             and str(A[i].get(c, "")).strip().lower() != str(B[i].get(c, "")).strip().lower()}
        if d:
            dis.append({"item_id": i, "pushback": A[i].get("pushback", "")[:300],
                        **{f"{c}_a": v[0] for c, v in d.items()}, **{f"{c}_b": v[1] for c, v in d.items()}})
    dis_path = out.with_name("disagreements_coding.csv")
    if dis:
        keys = sorted({k for r in dis for k in r}, key=lambda k: (k not in ("item_id", "pushback"), k))
        with open(dis_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            w.writerows(dis)
    for r in rows:
        print(f"{r['label']:>22} n={r['n']:<4} κ={r['kappa']:<7} raw={r['raw_agreement']}")
    print(f"{len(dis)} items with any disagreement -> {dis_path if dis else '(none)'}")
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet_a")
    ap.add_argument("sheet_b")
    ap.add_argument("--out")
    args = ap.parse_args()
    main(args.sheet_a, args.sheet_b, args.out)
