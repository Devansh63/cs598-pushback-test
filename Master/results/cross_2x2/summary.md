# 2×2 cross: model × item difficulty (scripted form, 3 rounds)

- `cross_gemini_gemini-3.1-flash-lite`: gemini/gemini-3.1-flash-lite · temperature 0.0 · judge gemini/gemini-3.6-flash · commit e131cf0 · 2026-10-20T00:25:22+00:00

Pre-registered in `PREREGISTRATION.md` before any trial. Primary cells: easy (60 items) and hard **held-out** (10 items).

## Primary: caving by round (user is wrong)

| model | tier | n items | caves r1 | caves r2 | **caves r3** (Wilson) | ever left correct (boot) | accepts r3 (user right) | J r3 |
|---|---|---|---|---|---|---|---|---|
| gemini-3.1-flash-lite | easy | 60 | 0% | 0% | **0%** [0%, 6%] | 5% [0%, 12%] | 100% | +0.95 |
| gemini-3.1-flash-lite | hard-dev (exploratory) | 10 | 0% | 0% | **10%** [2%, 40%] | 20% [0%, 50%] | 100% | +0.90 |
| gemini-3.1-flash-lite | hard-heldout | 10 | 0% | 0% | **20%** [6%, 51%] | 20% [0%, 50%] | 100% | +0.80 |

## Contrasts (hard-heldout − easy, within model; round-3 caving, user wrong)

- **gemini-3.1-flash-lite**: hard 20% [0%, 50%] vs easy 0% [0%, 0%] → difference +20 pp

## Reading the result against the pre-registered hypotheses

- H-difficulty: hard − easy > 0 for **both** models.
- H-model: hard − easy > 0 for the weak model only.
- Interaction: both, with the weak model moving more.
- Null: neither moves.

Fill in the verdict by hand from the tables above; do not automate the interpretation.

## Instrument agreement

- judge vs markers: 240 / 247 decisive (97%)
- judge vs extractor: 444 / 445 decisive (100%)
- 7 disagreements → `disagreements.csv`

