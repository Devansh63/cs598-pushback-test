"""Compare returned labeling sheets: correctness agreement, resolution sheets, human vs AI codes.

  python3 labeling/compare.py [--dir results/labeling] [--meta results/trackA/data_local/meta.jsonl]

Reads assignments.csv plus every returned coding_<name>.csv and check_<name>.csv in --dir. For each
case, the coder's and the checker's correctness labels are compared:
  both not pushback, or both not checkable      -> excluded (no user_claim needed)
  both checkable with the same user_claim       -> agreed
  any other combination                         -> sent to the resolver
Writes to --dir:
  resolve_<name>.csv     the cases that person must settle (local only: verbatim text). Fill
                         `user_claim_final` (correct / incorrect / mixed / indeterminate /
                         not_checkable) and re-run. Existing rows are never overwritten; new
                         disagreements are appended.
  correctness_final.csv  item_id, user_claim, status (agreed / resolved / excluded / pending)  (ids + labels)
  summary.md             agreement on correctness, and human vs AI codes (aggregate only)
"""
import argparse
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analysis.agreement import kappa  # noqa: E402
from labeling.common import (AI_LETTER_TO_CODE, META, OUT, USER_CLAIM_VALUES, cell, is_yes,  # noqa: E402
                             read_jsonl, read_sheet, write_sheet)

RESOLVE_COLS = ["item_id", "earlier_turns", "question", "assistant_answer", "pushback",
                "coder", "coder_is_pushback", "coder_checkable_claim", "coder_user_claim", "coder_notes",
                "checker", "checker_is_pushback", "checker_checkable_claim", "checker_user_claim", "checker_notes",
                "user_claim_final", "resolver_notes"]
FINAL_VALUES = USER_CLAIM_VALUES | {"not_checkable"}


def keyed(path):
    if not path.exists():
        return {}
    return {cell(r.get("item_id")): r for r in read_sheet(path)[1]}


def labeled(r):
    return r is not None and cell(r.get("is_pushback")) in ("0", "1")


def view(r):
    """(is_pushback, checkable, user_claim) as the comparison sees them."""
    pb = is_yes(r.get("is_pushback"))
    chk = pb and is_yes(r.get("checkable_claim"))
    return pb, chk, cell(r.get("user_claim")).lower() if chk else ""


def fmt_k(k):
    return "n/a" if k != k else f"{k:.2f}"           # NaN when only one category occurs


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(OUT))
    ap.add_argument("--meta", default=str(META))
    a = ap.parse_args(argv)
    d = Path(a.dir)
    assignments = read_sheet(d / "assignments.csv")[1]
    people = sorted({r["coder"] for r in assignments})
    coding = {p: keyed(d / f"coding_{p}.csv") for p in people}
    check = {p: keyed(d / f"check_{p}.csv") for p in people}

    # ---- correctness: coder vs checker -------------------------------------------------------
    pairs = {"is_pushback": ([], []), "checkable_claim": ([], []), "user_claim": ([], [])}
    final, to_resolve = {}, collections.defaultdict(list)
    for asg in assignments:
        item = asg["item_id"]
        A, B = coding[asg["coder"]].get(item), check[asg["checker"]].get(item)
        if not (labeled(A) and labeled(B)):
            final[item] = ("", "pending")
            continue
        (pa, ca, ua), (pb, cb, ub) = view(A), view(B)
        pairs["is_pushback"][0].append(int(pa)); pairs["is_pushback"][1].append(int(pb))
        if pa and pb:
            pairs["checkable_claim"][0].append(int(ca)); pairs["checkable_claim"][1].append(int(cb))
        if ca and cb:
            pairs["user_claim"][0].append(ua); pairs["user_claim"][1].append(ub)
        if not ca and not cb:
            final[item] = ("", "excluded")
        elif ca and cb and ua == ub and ua in USER_CLAIM_VALUES:
            final[item] = (ua, "agreed")
        else:
            final[item] = ("", "pending")
            to_resolve[asg["resolver"]].append({
                "item_id": item, **{k: A.get(k, "") for k in ("earlier_turns", "question", "assistant_answer", "pushback")},
                "coder": asg["coder"], "coder_is_pushback": cell(A.get("is_pushback")),
                "coder_checkable_claim": cell(A.get("checkable_claim")), "coder_user_claim": cell(A.get("user_claim")),
                "coder_notes": cell(A.get("notes")),
                "checker": asg["checker"], "checker_is_pushback": cell(B.get("is_pushback")),
                "checker_checkable_claim": cell(B.get("checkable_claim")), "checker_user_claim": cell(B.get("user_claim")),
                "checker_notes": cell(B.get("notes"))})

    for person in people:
        path = d / f"resolve_{person}.csv"
        existing = read_sheet(path)[1] if path.exists() else []
        have = {cell(r.get("item_id")) for r in existing}
        added = [r for r in to_resolve.get(person, []) if r["item_id"] not in have]
        if existing or added:
            write_sheet(path, RESOLVE_COLS, existing + added)
        for r in existing:
            v = cell(r.get("user_claim_final")).lower()
            if v in FINAL_VALUES and final.get(cell(r.get("item_id")), ("", ""))[1] == "pending":
                final[cell(r["item_id"])] = ("", "excluded") if v == "not_checkable" else (v, "resolved")

    write_sheet(d / "correctness_final.csv", ["item_id", "user_claim", "status"],
                [{"item_id": k, "user_claim": v[0], "status": v[1]} for k, v in sorted(final.items())])
    status = collections.Counter(s for _, s in final.values())
    claims = collections.Counter(c for c, s in final.values() if s in ("agreed", "resolved"))

    lines = ["# Labeling round: comparison", "",
             f"{len(final)} cases · " + " · ".join(f"{k} {status.get(k, 0)}" for k in ("agreed", "resolved", "excluded", "pending")), "",
             "## Correctness: coder vs checker", "",
             "| label | n | κ | raw agreement |", "|---|---|---|---|"]
    for label, (xs, ys) in pairs.items():
        raw = sum(x == y for x, y in zip(xs, ys)) / len(xs) if xs else float("nan")
        lines.append(f"| {label} | {len(xs)} | {fmt_k(kappa(xs, ys))} | {fmt_k(raw)} |")
    lines += ["", "Settled user_claim values (agreed + resolved): " +
              (", ".join(f"{k} {v}" for k, v in sorted(claims.items())) or "none yet"), ""]

    # ---- human codes vs the workbook's AI codes ----------------------------------------------
    lines += ["## Human codes vs AI pre-codes (coder sheets, cases the coder marked as pushback)", ""]
    meta_path = Path(a.meta)
    if not meta_path.exists():
        lines.append(f"Skipped: {meta_path} not found (run trackA/load_pushback300.py).")
    else:
        ai = {}
        for m in read_jsonl(meta_path):
            letters = {s.split()[0].strip("—-") for s in m.get("subthemes_ai") or [] if s.split()}
            ai[m["event_id"]] = {AI_LETTER_TO_CODE[x] for x in letters if x in AI_LETTER_TO_CODE}
        rows = [r for p in people for r in coding[p].values() if labeled(r) and cell(r["item_id"]) in ai]
        pushback = [r for r in rows if is_yes(r.get("is_pushback"))]
        lines += [f"Coders marked {len(pushback)} of {len(rows)} labeled cases as pushback (the AI screen said yes to all).", "",
                  "| code | n | κ (human vs AI) | human rate | AI rate |", "|---|---|---|---|---|"]
        for code in AI_LETTER_TO_CODE.values():
            hs = [int(is_yes(r.get(code))) for r in pushback]
            ys = [int(code in ai[cell(r["item_id"])]) for r in pushback]
            if hs:
                lines.append(f"| {code} | {len(hs)} | {fmt_k(kappa(hs, ys))} | {sum(hs) / len(hs):.2f} | {sum(ys) / len(ys):.2f} |")
        lines += ["", "AI codes are pre-codes from the pushback_300 workbook; κ here measures how far the human codes move from them."]
    (d / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    for person in people:
        path = d / f"resolve_{person}.csv"
        if path.exists():
            open_rows = [r for r in read_sheet(path)[1] if cell(r.get("user_claim_final")).lower() not in FINAL_VALUES]
            if open_rows:
                print(f"{path.name}: {len(open_rows)} case(s) still to settle")
    return final, pairs


if __name__ == "__main__":
    main()
