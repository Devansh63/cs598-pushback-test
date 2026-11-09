"""Compare returned labeling sheets: pilot code agreement, correctness agreement, resolve sheets,
human vs AI codes.

  python3 labeling/compare.py [--dir results/labeling] [--meta results/trackA/data_local/meta.jsonl]

Reads assignments.csv and the returned sheets in --dir (.xlsx preferred, else .csv). For each case
the two independent correctness labels are compared: the coder's against the checker's (in the
pilot, the two labelers' pilot sheets):
  both not pushback, or both not checkable      -> excluded (no user_claim needed)
  both checkable with the same user_claim       -> agreed
  any other combination                         -> sent to the resolver
Writes to --dir:
  resolve_<name>.xlsx    cases that person must settle (local only: verbatim text). Fill
                         `user_claim_final` (correct / incorrect / mixed / indeterminate /
                         not_checkable) and re-run. Filled rows are kept; new cases are appended.
  pilot_agreement.csv    per-label kappa between the two pilot sheets (aggregate); its companion
                         disagreements_coding.csv holds text and stays local
  correctness_final.csv  item_id, user_claim, status (agreed / resolved / excluded / pending)  (ids + labels)
  summary.md             all agreement tables (aggregate only)
"""
import argparse
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analysis import agreement  # noqa: E402
from analysis.agreement import kappa  # noqa: E402
from labeling.common import (AI_LETTER_TO_CODE, META, OUT, USER_CLAIM_VALUES, cell, find_sheet,  # noqa: E402
                             is_yes, read_jsonl, read_sheet, write_sheet)

RESOLVE_COLS = ["item_id", "earlier_turns", "question", "assistant_answer", "pushback",
                "coder", "coder_is_pushback", "coder_checkable_claim", "coder_user_claim", "coder_notes",
                "checker", "checker_is_pushback", "checker_checkable_claim", "checker_user_claim", "checker_notes",
                "user_claim_final", "resolver_notes"]
FINAL_VALUES = USER_CLAIM_VALUES | {"not_checkable"}


def keyed(path):
    return {cell(r.get("item_id")): r for r in read_sheet(path)[1]} if path else {}


def labeled(r):
    return r is not None and cell(r.get("is_pushback")) in ("0", "1")


def view(r):
    """(is_pushback, checkable, user_claim) as the comparison sees them."""
    pb = is_yes(r.get("is_pushback"))
    chk = pb and is_yes(r.get("checkable_claim"))
    return pb, chk, cell(r.get("user_claim")).lower() if chk else ""


def fmt(x):
    return "n/a" if x != x else f"{x:.2f}"            # NaN when only one category occurs


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(OUT))
    ap.add_argument("--meta", default=str(META))
    a = ap.parse_args(argv)
    d = Path(a.dir)
    assignments = read_sheet(d / "assignments.csv")[1]
    for r in assignments:
        r.setdefault("phase", "main")
    labelers = sorted({r["coder"] for r in assignments} | {r["checker"] for r in assignments})
    resolvers = sorted({r["resolver"] for r in assignments})
    pilot = {p: keyed(find_sheet(d, f"pilot_{p}")) for p in labelers}
    coding = {p: keyed(find_sheet(d, f"coding_{p}")) for p in labelers}
    check = {p: keyed(find_sheet(d, f"check_{p}")) for p in labelers}
    sheet_ext = ".xlsx" if any(find_sheet(d, f"coding_{p}") and find_sheet(d, f"coding_{p}").suffix == ".xlsx"
                               for p in labelers) else ".csv"
    lines = ["# Labeling round: comparison", ""]

    # ---- pilot: code agreement between the two labelers --------------------------------------
    pilot_people = [p for p in labelers if pilot[p]]
    if len(pilot_people) == 2 and all(any(labeled(r) for r in pilot[p].values()) for p in pilot_people):
        pa, pb = (find_sheet(d, f"pilot_{p}") for p in pilot_people)
        rows = agreement.main(str(pa), str(pb), str(d / "pilot_agreement.csv"))
        lines += ["## Pilot: code agreement between the two labelers", "",
                  "| label | n | κ | raw agreement |", "|---|---|---|---|"]
        lines += [f"| {r['label']} | {r['n']} | {r['kappa']} | {r['raw_agreement']} |" for r in rows]
        lines += ["", "Per-case disagreements: disagreements_coding.csv (local only).", ""]

    # ---- correctness: two independent labels per case ----------------------------------------
    pairs = {"is_pushback": ([], []), "checkable_claim": ([], []), "user_claim": ([], [])}
    final, to_resolve, human = {}, collections.defaultdict(list), {}
    for asg in assignments:
        item, is_pilot = asg["item_id"], asg["phase"] == "pilot"
        A = (pilot if is_pilot else coding)[asg["coder"]].get(item)
        B = (pilot if is_pilot else check)[asg["checker"]].get(item)
        if labeled(A):
            human[item] = A
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

    open_counts = {}
    for person in resolvers:
        path = find_sheet(d, f"resolve_{person}") or d / f"resolve_{person}{sheet_ext}"
        existing = read_sheet(path)[1] if path.exists() else []
        have = {cell(r.get("item_id")) for r in existing}
        added = [r for r in to_resolve.get(person, []) if r["item_id"] not in have]
        if added:
            write_sheet(path, RESOLVE_COLS, existing + added)
        for r in existing:
            v = cell(r.get("user_claim_final")).lower()
            if v in FINAL_VALUES and final.get(cell(r.get("item_id")), ("", ""))[1] == "pending":
                final[cell(r["item_id"])] = ("", "excluded") if v == "not_checkable" else (v, "resolved")
        open_counts[path.name] = sum(1 for r in existing + added if cell(r.get("user_claim_final")).lower() not in FINAL_VALUES)

    write_sheet(d / "correctness_final.csv", ["item_id", "user_claim", "status"],
                [{"item_id": k, "user_claim": v[0], "status": v[1]} for k, v in sorted(final.items())])
    status = collections.Counter(s for _, s in final.values())
    claims = collections.Counter(c for c, s in final.values() if s in ("agreed", "resolved"))
    lines += ["## Correctness: two independent labels per case", "",
              f"{len(final)} cases · " + " · ".join(f"{k} {status.get(k, 0)}" for k in ("agreed", "resolved", "excluded", "pending")), "",
              "| label | n | κ | raw agreement |", "|---|---|---|---|"]
    for label, (xs, ys) in pairs.items():
        raw = sum(x == y for x, y in zip(xs, ys)) / len(xs) if xs else float("nan")
        lines.append(f"| {label} | {len(xs)} | {fmt(kappa(xs, ys))} | {fmt(raw)} |")
    lines += ["", "Settled user_claim values (agreed + resolved): " +
              (", ".join(f"{k} {v}" for k, v in sorted(claims.items())) or "none yet"), ""]

    # ---- human codes vs the workbook's AI codes (one human label per case: the coder's) ------
    lines += ["## Human codes vs AI pre-codes", ""]
    meta_path = Path(a.meta)
    if not meta_path.exists():
        lines.append(f"Skipped: {meta_path} not found (run trackA/load_pushback300.py).")
    else:
        ai = {}
        for m in read_jsonl(meta_path):
            letters = {s.split()[0].strip("—-") for s in m.get("subthemes_ai") or [] if s.split()}
            ai[m["event_id"]] = {AI_LETTER_TO_CODE[x] for x in letters if x in AI_LETTER_TO_CODE}
        rows = [r for k, r in human.items() if k in ai]
        pushback = [r for r in rows if is_yes(r.get("is_pushback"))]
        lines += [f"Coders marked {len(pushback)} of {len(rows)} labeled cases as pushback (the AI screen said yes to all).", "",
                  "| code | n | κ (human vs AI) | human rate | AI rate |", "|---|---|---|---|---|"]
        for code in AI_LETTER_TO_CODE.values():
            hs = [int(is_yes(r.get(code))) for r in pushback]
            ys = [int(code in ai[cell(r["item_id"])]) for r in pushback]
            if hs:
                lines.append(f"| {code} | {len(hs)} | {fmt(kappa(hs, ys))} | {sum(hs) / len(hs):.2f} | {sum(ys) / len(ys):.2f} |")
        lines += ["", "AI codes are pre-codes from the pushback_300 workbook; κ measures how far the human codes move from them."]
    (d / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    for name, n in open_counts.items():
        if n:
            print(f"{name}: {n} case(s) still to settle")
    return final, pairs


if __name__ == "__main__":
    main()
