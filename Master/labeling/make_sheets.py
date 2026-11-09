"""Build blind labeling sheets for the 300-case corpus: one coding sheet and one check sheet per person.

  python3 trackA/load_pushback300.py --contexts <pushback_300_contexts.md> --workbook <pushback_300_coded.xlsm>
  python3 labeling/make_sheets.py [--coders devansh sahil zhongyin mathew xuejun zoey] [--seed 598]

Every case is labeled by one CODER (codebook v2, all columns) and checked for correctness by a
second person, the CHECKER (gate codes + user_claim only), who never sees the coder's labels. A
third person, the RESOLVER, settles correctness disagreements later (labeling/compare.py). With
coders c0..c(n-1), the checker of c_i's batch is c_(i+1) and the resolver is c_(i+2).

Reads only conversation text (results/trackA/data_local/contexts.jsonl). The AI codes in the
workbook never reach a sheet.

Writes to results/labeling/:
  coding_<name>.csv   that person's batch, every codebook column       (local only: verbatim text)
  check_<name>.csv    the previous person's batch, correctness columns  (local only: verbatim text)
  assignments.csv     item_id, coder, checker, resolver                 (ids only: safe to commit)
Refuses to overwrite existing sheets (they may already be filled) unless --force.
"""
import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from labeling.common import (CONTEXTS, DEFAULT_CODERS, OUT, check_cols, coding_cols,  # noqa: E402
                             read_jsonl, write_sheet)
from phase1.make_coding_sheets import scrub  # noqa: E402  (one de-identification rule for all sheets)


def tail(text, limit):
    """Keep the END of the text: the turns nearest the pushback matter most."""
    return text if len(text) <= limit else "[…] " + text[-limit:]


def split_case(rec, q_limit, a_limit, earlier_limit):
    msgs = sorted(rec["messages"], key=lambda m: m["index"])
    t = next((i for i, m in enumerate(msgs) if m["index"] == rec["target_index"]), len(msgs) - 1)
    a = max((i for i in range(t) if msgs[i]["role"] == "assistant"), default=None)
    q = max((i for i in range(a) if msgs[i]["role"] == "user"), default=None) if a is not None else None
    cut = q if q is not None else (a if a is not None else t)
    earlier = "\n\n".join(f"[{m['role']}] {m['content']}" for m in msgs[:cut])
    return {"item_id": rec["event_id"],
            "domain_hint": "",
            "earlier_turns": tail(scrub(earlier), earlier_limit) if earlier else "",
            "question": scrub(msgs[q]["content"], q_limit) if q is not None else "",
            "assistant_answer": scrub(msgs[a]["content"], a_limit) if a is not None else "",
            "pushback": scrub(msgs[t]["content"])}


def assign(item_ids, coders, seed):
    ids = sorted(item_ids)
    random.Random(seed).shuffle(ids)
    n = len(coders)
    batches = {c: ids[i::n] for i, c in enumerate(coders)}
    rows = []
    for i, c in enumerate(coders):
        for item in batches[c]:
            rows.append({"item_id": item, "coder": c, "checker": coders[(i + 1) % n], "resolver": coders[(i + 2) % n]})
    return batches, rows


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--coders", nargs="+", default=DEFAULT_CODERS)
    ap.add_argument("--seed", type=int, default=598)
    ap.add_argument("--contexts", default=str(CONTEXTS))
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--question-chars", type=int, default=1000)
    ap.add_argument("--answer-chars", type=int, default=2500)
    ap.add_argument("--earlier-chars", type=int, default=1500)
    ap.add_argument("--force", action="store_true", help="overwrite existing sheets")
    a = ap.parse_args(argv)
    coders = [c.strip().lower() for c in a.coders]
    if len(set(coders)) < 3 or len(set(coders)) != len(coders):
        sys.exit("need at least three distinct coders (coder, checker and resolver must differ)")
    if not Path(a.contexts).exists():
        sys.exit(f"{a.contexts} not found: run trackA/load_pushback300.py first")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    existing = [p for c in coders for p in (out / f"coding_{c}.csv", out / f"check_{c}.csv") if p.exists()]
    if existing and not a.force:
        sys.exit(f"refusing to overwrite {len(existing)} existing sheet(s), e.g. {existing[0]} (use --force)")

    cases = {r["event_id"]: split_case(r, a.question_chars, a.answer_chars, a.earlier_chars)
             for r in read_jsonl(a.contexts)}
    batches, rows = assign(cases, coders, a.seed)
    for i, c in enumerate(coders):
        write_sheet(out / f"coding_{c}.csv", coding_cols(), [cases[k] for k in batches[c]])
        prev = coders[(i - 1) % len(coders)]
        write_sheet(out / f"check_{c}.csv", check_cols(), [cases[k] for k in batches[prev]])
    write_sheet(out / "assignments.csv", ["item_id", "coder", "checker", "resolver"], rows)
    sizes = ", ".join(f"{c} {len(batches[c])}" for c in coders)
    print(f"{len(cases)} cases -> {out}: coding sheets ({sizes}); each person also checks the previous "
          f"person's batch; assignments.csv written")
    return batches, rows


if __name__ == "__main__":
    main()
