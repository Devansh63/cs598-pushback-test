# pushback_300 — second real-pushback corpus

Work built on the team's `pushback_300` materials: **300 candidate pushback events drawn from
WildChat-1M** (revision `7d6490e`), with full conversation context and AI preliminary coding.

This folder does three things:

1. **Parses and audits the corpus** — structure, provenance, coding distribution.
2. **Tests whether the AI annotations are trustworthy** — prescreen precision and code reproducibility.
3. **Runs the natural-context replay** that the single-turn pilot could not: the model responds
   inside the original conversation, so we can see whether the 0–8% caving floor was a design artifact.

## Inputs (not in this repository)

The two source files contain **real user conversation text and are not de-identified**. They are
gitignored and must be supplied locally:

```
pushback300/source/pushback_300_contexts.md    full context for 300 cases (~930 KB)
pushback300/source/pushback_300_coded.xlsm     300 rows of metadata + AI preliminary codes
```

Copy them in, or pass paths explicitly:

```bash
python3 load_pushback300.py --contexts /path/to/pushback_300_contexts.md \
                            --workbook /path/to/pushback_300_coded.xlsm
```

Do **not** commit `source/` or `data_local/`. Only `results/` (aggregates) and the scripts belong
in git.

## What the corpus contains

| Property | Value |
|---|---|
| cases | 300, unique `event_id`s, 14 WildChat parquet shards |
| messages per case | min 3, median 5, max 11 |
| target turn | always the last message, always a user turn, always preceded by an assistant answer |
| target turn length | median 62 chars (p90 206, max 1,338) |
| challenged answer | median 548 chars (p90 1,667, max 4,262) |
| context before target | median 1,650 chars (p90 4,313, max 6,467) |
| human coding | **none** — `team_notes` empty in all 300 rows |
| correctness labels | **none** |

The workbook codes ten strategies in three themes: **B** bare disagreement, **A** alternative claim,
**I** inconsistency challenge (theme: challenging answer content); **L** reasoning challenge,
**E** counter-evidence, **S** authority/source appeal (theme: justifying disagreement);
**R** recheck request, **T** task/constraint correction, **P** repeated insistence,
**F** frustration (theme: shaping the repair interaction). All ten codes occur; `R` dominates at 162.

## Scripts

| Script | Purpose | Output |
|---|---|---|
| `load_pushback300.py` | parse markdown + workbook, validate structure, join on `event_id` | `results/corpus_stats.json`, `data_local/*.jsonl` |
| `validate_prescreen.py` | is the "AI is_pushback: yes" screen reliable? | `results/prescreen_validation.md` |
| `code_types.py` | second AI coder over the 10-code scheme → per-code κ | `results/type_agreement.md` |
| `replay.py` | natural-context replay, 300 cases × 2 models | `results/replay_summary.md` |

```bash
cd progress/phase1/pushback300
python3 load_pushback300.py --contexts ... --workbook ...
python3 validate_prescreen.py --n 100
python3 code_types.py
python3 replay.py
```

Requires `DEEPSEEK_API_KEY` and `openpyxl`. Every stage is resumable (JSONL keyed by case/model).

## Results

See `results/replay_summary.md`, `results/type_agreement.md`, `results/prescreen_validation.md`,
and the consolidated section in `../../PROGRESS.md`.

## Limits, stated once

- **Purposive sample.** Selected by an AI screener, not randomly, so counts describe this set and
  cannot be read as prevalence in WildChat.
- **No correctness labels.** "Adopts the user's position" is not "wrongly adopts". The harmful
  subset requires the two-human verification in the proposal.
- **AI annotations, twice.** The prescreen and both coding passes are model-generated. The κ values
  here are an *upper bound* on human reliability, since two AI coders share training data.
- **No no-pushback control** for these cases, so adoption cannot be cleanly attributed to the push.
