# Labeling round (300-case corpus)

Human labels for the 300 real pushback cases: pushback codes (codebook v2) and whether the user
was right (`user_claim`). Labeler instructions are in the team's **Labeling Guide** (in the shared
Drive folder); the definitions come from [`../data/codebook_v2.md`](../data/codebook_v2.md).

## Current round: four labelers, coding only (generated 2026-11-09)

```bash
python3 labeling/make_sheets.py --coders labeler_a labeler_b labeler_c labeler_d --no-check
```

The 300 cases are split evenly at random (seed 598): `coding_labeler_a.xlsx` … `coding_labeler_d.xlsx`,
75 cases each, every column filled. There is no shared pilot and no check sheet, so each case gets
one label: the coder's `user_claim` is final (`status = single` in `correctness_final.csv`), and
`compare.py` reports human-vs-AI agreement only, not human-human agreement. `assignments.csv`
(committed, ids only) records each case's coder; checker and resolver are blank.

The sheets live only in the team Drive folder `CS598-Group6 / Labelling 4 people split`, one
subfolder per labeler, next to the labeling guide for this round: this repo is public and they hold
real user turns. `sheets_manifest.csv` is the repo's record of them.

Other designs the tools support:

- Two labelers with a shared pilot and a blind correctness cross-check (the plan before this round):
  `make_sheets.py --coders labeler_a labeler_b --resolver devansh --pilot 50`
- Three or more people with a cross-check: `make_sheets.py --coders a b c ...` gives each a coding
  batch and a check sheet for the previous person's batch, with the next-but-one person as resolver.

## Steps

Run from `Master/`. Steps 1, 2 and 4 need the `pushback_300` source files (in the shared Drive folder).

```bash
# 1. Parse the 300 cases (local only; AI codes stay in meta.jsonl and never reach a sheet)
python3 trackA/load_pushback300.py --contexts <pushback_300_contexts.md> --workbook <pushback_300_coded.xlsm>

# 2. Make the sheets (refuses to overwrite filled sheets; --format csv for CSV)
python3 labeling/make_sheets.py --coders labeler_a labeler_b labeler_c labeler_d --no-check

# 3. Record what goes out, then hand out the sheets privately (never through GitHub):
python3 labeling/manifest.py
#    When they come back, put them in results/labeling/ under the same names and check them:
python3 labeling/manifest.py --check                  # same cases as were sent out?
python3 labeling/check_sheets.py results/labeling/*.xlsx

# 4. Compare: final correctness labels and human vs AI codes (plus pilot/cross-check agreement
#    and a resolve sheet when the round has them)
python3 labeling/compare.py
#    With a cross-check, the resolver fills user_claim_final on resolve_<name>.xlsx; put it back and
#    re-run compare.py: settled answers are kept and correctness_final.csv gets the final labels.
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
| `results/labeling/sheets_manifest.csv` | per sheet: labeler, phase, rows, SHA-256 of its case ids and of the file as sent, Drive folder name (no text, no ids, no links) | yes |
| `results/labeling/correctness_final.csv` | item_id, user_claim, status | yes |
| `results/labeling/pilot_agreement.csv`, `summary.md` | agreement tables | yes |

Tests: `python3 -m pytest tests/test_labeling.py -q` (synthetic data, no API keys).
