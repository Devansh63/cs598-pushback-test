# Labeling round (300-case corpus)

Human labels for the 300 real pushback cases: pushback codes (codebook v2) and whether the user
was right (`user_claim`). Labeler instructions are in the team's **Labeling Guide** (in the shared
Drive folder); the definitions come from [`../data/codebook_v2.md`](../data/codebook_v2.md).

## Current round: two labelers (generated 2026-11-09)

```bash
python3 labeling/make_sheets.py --coders labeler_a labeler_b --resolver devansh --pilot 50
```

| Phase | Labeler A | Labeler B | Correctness labels per case |
|---|---|---|---|
| Pilot | `pilot_labeler_a.xlsx`: 50 cases, every column | `pilot_labeler_b.xlsx`: the same 50 | A and B |
| Main | `coding_labeler_a.xlsx`: 125 cases, every column; `check_labeler_a.xlsx`: B's 125, correctness only | `coding_labeler_b.xlsx`; `check_labeler_b.xlsx`: A's 125 | coder and checker |
| Disagreements | | | Devansh settles on `resolve_devansh.xlsx` |

The pilot comes first: compare the two pilot sheets, settle disagreements, freeze the codebook,
then the main round starts. `assignments.csv` (committed, ids only) records every case's phase,
coder, checker and resolver. The same seed always gives the same split.

Three or more people instead: `make_sheets.py --coders a b c ...` gives each a coding batch and a
check sheet for the previous person's batch, with the next-but-one person as resolver.

## Steps

Run from `Master/`. Steps 1, 2 and 4 need the `pushback_300` source files (in the shared Drive folder).

```bash
# 1. Parse the 300 cases (local only; AI codes stay in meta.jsonl and never reach a sheet)
python3 trackA/load_pushback300.py --contexts <pushback_300_contexts.md> --workbook <pushback_300_coded.xlsm>

# 2. Make the sheets (refuses to overwrite filled sheets; --format csv for CSV)
python3 labeling/make_sheets.py --coders labeler_a labeler_b --resolver devansh --pilot 50

# 3. Hand out the sheets privately (never through GitHub). When they come back, put them in
#    results/labeling/ under the same names and check them:
python3 labeling/check_sheets.py results/labeling/*.xlsx

# 4. Compare: pilot code agreement, correctness agreement, the resolve sheet, human vs AI codes
python3 labeling/compare.py
#    The resolver fills user_claim_final on resolve_<name>.xlsx; put it back and re-run compare.py:
#    settled answers are kept and correctness_final.csv gets the final labels.
```

## The sheets

Excel files with two tabs: `labels` (one row per case) and `How to label` (a quick reference).
Grey columns are read-only text; every label column has a dropdown, so only valid values can be
entered. They open in Excel or directly in Google Drive. Text shown: the conversation before the
question (`earlier_turns`, its last 3,000 characters, for judging `x_persistence`), the question
(up to 1,000), the answer (up to 2,500) and the pushback in full. Emails, URLs, phone numbers and
handles are replaced with placeholders by the same rule as the pilot sheets
(`phase1/make_coding_sheets.py`). `domain_hint` is blank for this corpus.

## Files

| File | Contents | In git? |
|---|---|---|
| `results/labeling/pilot_*`, `coding_*`, `check_*`, `resolve_*`, `disagreements_*` | verbatim conversation text | no (`results/.gitignore`) |
| `results/labeling/assignments.csv` | item_id, phase, coder, checker, resolver | yes |
| `results/labeling/correctness_final.csv` | item_id, user_claim, status | yes |
| `results/labeling/pilot_agreement.csv`, `summary.md` | agreement tables | yes |

Tests: `python3 -m pytest tests/test_labeling.py -q` (synthetic data, no API keys).
