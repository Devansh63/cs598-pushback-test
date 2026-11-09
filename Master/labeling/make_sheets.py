"""Build blind labeling sheets for the 300-case corpus.

  python3 trackA/load_pushback300.py --contexts <pushback_300_contexts.md> --workbook <pushback_300_coded.xlsm>

  # two labelers: a shared pilot, then a split with a correctness cross-check
  python3 labeling/make_sheets.py --coders labeler_a labeler_b --resolver devansh [--pilot 50]

  # three or more: everyone codes a batch, checks the previous person's, resolves the one before
  python3 labeling/make_sheets.py --coders devansh sahil zhongyin mathew xuejun zoey

Two labelers (A, B), resolver R:
  pilot_<A>, pilot_<B>   the same --pilot cases, every column, labeled independently
  coding_<A>, coding_<B> half of the remaining cases each, every column
  check_<A>, check_<B>   the OTHER labeler's coding cases: gate codes + user_claim only, blind
  R settles correctness disagreements later on a resolve sheet (labeling/compare.py).
Three or more (c0..cn-1): coding_<ci> is a batch, check_<ci> is c(i-1)'s batch, resolver c(i+2).

Every case thus gets two independent correctness labels. Reads only conversation text
(results/trackA/data_local/contexts.jsonl): the workbook's AI codes never reach a sheet.

Writes to results/labeling/ (sheets are local only: verbatim text):
  <sheets>.xlsx         dropdowns, read-only text shaded, a quick-reference tab (--format csv for CSV)
  assignments.csv       item_id, phase, coder, checker, resolver (ids only: safe to commit)
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


def shuffled(item_ids, seed):
    ids = sorted(item_ids)
    random.Random(seed).shuffle(ids)
    return ids


def assign_rotation(item_ids, coders, seed):
    """Three or more people. Returns ({stem: [ids]}, assignment rows)."""
    ids, n = shuffled(item_ids, seed), len(coders)
    batches = {c: ids[i::n] for i, c in enumerate(coders)}
    sheets, rows = {}, []
    for i, c in enumerate(coders):
        sheets[f"coding_{c}"] = batches[c]
        sheets[f"check_{c}"] = batches[coders[(i - 1) % n]]
        rows += [{"item_id": k, "phase": "main", "coder": c, "checker": coders[(i + 1) % n],
                  "resolver": coders[(i + 2) % n]} for k in batches[c]]
    return sheets, rows


def assign_pair(item_ids, coders, resolver, pilot_n, seed):
    """Two labelers and a separate resolver. Returns ({stem: [ids]}, assignment rows)."""
    a, b = coders
    ids = shuffled(item_ids, seed)
    pilot, rest = ids[:pilot_n], ids[pilot_n:]
    batch = {a: rest[0::2], b: rest[1::2]}
    sheets = {f"pilot_{a}": pilot, f"pilot_{b}": pilot,
              f"coding_{a}": batch[a], f"coding_{b}": batch[b],
              f"check_{a}": batch[b], f"check_{b}": batch[a]}
    rows = [{"item_id": k, "phase": "pilot", "coder": a, "checker": b, "resolver": resolver} for k in pilot]
    rows += [{"item_id": k, "phase": "main", "coder": c, "checker": (b if c == a else a), "resolver": resolver}
             for c in (a, b) for k in batch[c]]
    return sheets, rows


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--coders", nargs="+", default=DEFAULT_CODERS)
    ap.add_argument("--resolver", help="required with two coders: who settles correctness disagreements")
    ap.add_argument("--pilot", type=int, default=50, help="two coders: cases both label (0 = none)")
    ap.add_argument("--seed", type=int, default=598)
    ap.add_argument("--format", choices=["xlsx", "csv"], default="xlsx")
    ap.add_argument("--contexts", default=str(CONTEXTS))
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--question-chars", type=int, default=1000)
    ap.add_argument("--answer-chars", type=int, default=2500)
    ap.add_argument("--earlier-chars", type=int, default=3000)
    ap.add_argument("--force", action="store_true", help="overwrite existing sheets")
    a = ap.parse_args(argv)
    coders = [c.strip().lower() for c in a.coders]
    if len(set(coders)) != len(coders) or len(coders) < 2:
        sys.exit("need at least two distinct coders")
    if len(coders) == 2:
        if not a.resolver or a.resolver.strip().lower() in coders:
            sys.exit("with two coders, --resolver must name a third person")
    if not Path(a.contexts).exists():
        sys.exit(f"{a.contexts} not found: run trackA/load_pushback300.py first")
    cases = {r["event_id"]: split_case(r, a.question_chars, a.answer_chars, a.earlier_chars)
             for r in read_jsonl(a.contexts)}
    if len(coders) == 2:
        sheets, rows = assign_pair(cases, coders, a.resolver.strip().lower(), a.pilot, a.seed)
    else:
        sheets, rows = assign_rotation(cases, coders, a.seed)

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    paths = {stem: out / f"{stem}.{a.format}" for stem in sheets}
    existing = [p for p in paths.values() if p.exists()]
    if existing and not a.force:
        sys.exit(f"refusing to overwrite {len(existing)} existing sheet(s), e.g. {existing[0]} (use --force)")
    for stem, ids in sheets.items():
        cols = check_cols() if stem.startswith("check_") else coding_cols()
        write_sheet(paths[stem], cols, [cases[k] for k in ids])
    write_sheet(out / "assignments.csv", ["item_id", "phase", "coder", "checker", "resolver"], rows)
    print(f"{len(cases)} cases -> {out}")
    for stem, ids in sheets.items():
        print(f"  {paths[stem].name}: {len(ids)} rows")
    return sheets, rows


if __name__ == "__main__":
    main()
