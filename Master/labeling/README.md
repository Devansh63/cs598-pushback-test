# Labeling round (300-case corpus)

Human labels for the 300 real pushback cases: pushback codes (codebook v2) and whether the user
was right (`user_claim`). Labeler instructions are in the team's **Labeling Guide** doc; the
definitions come from [`../data/codebook_v2.md`](../data/codebook_v2.md).

Who does what, per case:

| Role | Labels | Sheet |
|---|---|---|
| Coder | every codebook column | `coding_<name>.csv` (50 cases) |
| Checker | gate codes + `user_claim` only, without seeing the coder's labels | `check_<name>.csv` (the previous person's 50 cases) |
| Resolver | the final `user_claim` where coder and checker disagree | `resolve_<name>.csv` (made by `compare.py`) |

With the default order `devansh sahil zhongyin mathew xuejun zoey`, each person's batch is checked
by the next person and resolved by the one after that (the list wraps around).

## Steps

Run from `Master/`. Steps 1–2 and 4 need the local `pushback_300` source files, so they run on the
machine that has them.

```bash
# 1. Parse the 300 cases (local only; AI codes stay in meta.jsonl and never reach a sheet)
python3 trackA/load_pushback300.py --contexts <pushback_300_contexts.md> --workbook <pushback_300_coded.xlsm>

# 2. Make the sheets: results/labeling/coding_<name>.csv, check_<name>.csv, assignments.csv
python3 labeling/make_sheets.py            # --coders to change people or order; refuses to overwrite

# 3. Send each person their two sheets privately (never through GitHub). When they come back,
#    put them in results/labeling/ under the same names and check them:
python3 labeling/check_sheets.py results/labeling/coding_*.csv results/labeling/check_*.csv

# 4. Compare: correctness agreement, resolve_<name>.csv for each resolver, human vs AI codes
python3 labeling/compare.py
#    Send each resolve_<name>.csv to its person; they fill user_claim_final. Put it back and re-run
#    compare.py: resolved answers are kept, and correctness_final.csv gets the settled labels.
```

Labelers can run `check_sheets.py` on their own sheet before sending it back; it needs only Python.

## Files

| File | Contents | In git? |
|---|---|---|
| `results/labeling/coding_*.csv`, `check_*.csv`, `resolve_*.csv` | verbatim conversation text | no (`results/.gitignore`) |
| `results/labeling/assignments.csv` | item_id, coder, checker, resolver | yes |
| `results/labeling/correctness_final.csv` | item_id, user_claim, status | yes |
| `results/labeling/summary.md` | agreement tables | yes |

Sheets show the question (up to 1,000 characters), the answer (up to 2,500), the pushback in full,
and `earlier_turns`: the conversation before the question, keeping its last 1,500 characters, so
`x_persistence` can be judged. Emails, URLs, phone numbers and handles are replaced with
placeholders by the same rule as the pilot sheets (`phase1/make_coding_sheets.py`). `domain_hint`
is blank for this corpus.

The 50-turn two-coder **pilot** (Phase 1 candidates) uses `phase1/make_coding_sheets.py` and
`analysis/agreement.py`; run it first and freeze the codebook before this round starts.

Tests: `python3 -m pytest tests/test_labeling.py -q` (synthetic data, no API keys).
