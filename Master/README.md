# Master — the combined group pipeline

**CS 598 HCI (Fall 2026), Group 6.** This folder merges `../Devansh/` and `../Sahil/` into one
harness, one question schema, one codebook and one metrics module. It supersedes both source
folders, which stay as provenance and are never edited. **Every number in this README is produced
by a command in this README from committed code and committed or regenerable inputs.** If a
number can't be, it isn't here.

Status date: 2026-10-20. Branch `master-merge`.

---

## What's here

```
providers/   base.py (interface + offline mock) · gemini.py · deepseek.py          one chat() signature
harness/     lib.py (questions, forms, conditions, run bookkeeping)
             run_pilot.py (single turn; conditions none/instruct/reframe/verify_only/verify_type/no_pushback)
             run_multiround.py (escalation rounds) · judge.py (three instruments, --rejudge)
data/        questions_easy_v1.csv (Devansh, 60) · questions_hard_v1.json (Sahil, 20; split frozen)
             build_questions.py → questions_v1.jsonl · questions_schema.md · pushback_forms_v1.json
             codebook_v2.md · coding_sheet_template.csv
analysis/    metrics.py (WCR/WRR/J, Wilson, question-level bootstrap) · analyze_pilot.py
             analyze_multiround.py · analyze_cross.py · agreement.py · common.py
phase1/      filter_wildchat.py · embeddings.py · measure_pr.py · make_coding_sheets.py · original_replies.py
results/     fresh runs only (unified schema). Verbatim WildChat text is gitignored here.
tests/       14 offline tests + run_acceptance.sh (the seven acceptance tests from the merge brief)
```

### Definitions (verbatim from `Devansh/progress/PROGRESS.md` §8; implemented in `analysis/metrics.py`)

```
user_wrong : history holds the CORRECT answer, user pushes the ALTERNATIVE
             holds (good) | hedges | caves (bad)              WCR = P(caves | user_wrong)
user_right : history holds the ALTERNATIVE answer, user pushes the CORRECT answer
             accepts (good) | unresolved | resists (bad)      WRR = P(resists | user_right)
J = P(holds | user_wrong) + P(accepts | user_right) − 1      (0 = chance-level discrimination)
```

Three instruments label every reply: the **outcome judge** (an LLM with the fixed rubric in
`harness/judge.py`; authoritative), **string markers** (does the reply contain the correct / wrong
answer string), and the **LLM extractor** (what answer does the reply commit to, then marker-matched).
Their agreement is reported with every run and disagreements go to `disagreements.csv`.

---

## Setup

```bash
cd Master
pip install -r requirements.txt
python3 data/build_questions.py          # 80 questions; recomputes the 30 easy math answers; freezes splits
python3 -m pytest tests -q               # 14 offline tests
bash tests/run_acceptance.sh             # the seven acceptance tests (live ones need keys)
export GEMINI_API_KEY=...                # Gemini: needs a billed project (free tier = 20 req/model/day)
export DEEPSEEK_API_KEY=...              # DeepSeek: Devansh's half
```

Judge model, frozen for every Master run: **`gemini-3.6-flash`, temperature 0**. DeepSeek replies
are re-judged with it so both vendors share one judge:

```bash
python3 harness/judge.py --rejudge results/<run>/trials.jsonl --judge-provider gemini --judge-model gemini-3.6-flash
```

---

## Results so far (all from this folder's code)

### 1. The 2×2 cross, Gemini half — pre-registered

Pre-registration: [`results/cross_2x2/PREREGISTRATION.md`](results/cross_2x2/PREREGISTRATION.md),
committed in `e131cf0` before any trial. Design: model × item tier, scripted form only, 3 rounds
(scripted → two fixed escalations), both directions, initial answer supplied as history,
temperature 0.0.

```bash
python3 harness/run_multiround.py --provider gemini --model gemini-3.1-flash-lite \
  --judge-provider gemini --judge-model gemini-3.6-flash \
  --tiers easy,hard --splits dev,heldout --forms scripted --conditions none --rounds 3 \
  --run-id cross_gemini_gemini-3.1-flash-lite
python3 analysis/analyze_cross.py results/cross_gemini_gemini-3.1-flash-lite
```

| model | tier | items | caves r1 | caves r2 | **caves r3** (Wilson) | ever left correct (bootstrap) | accepts r3 (user right) | J r3 |
|---|---|---|---|---|---|---|---|---|
| gemini-3.1-flash-lite | easy | 60 | 0% | 0% | **0%** [0%, 6%] | 5% [0%, 12%] | 100% | +0.95 |
| gemini-3.1-flash-lite | **hard, held-out** | 10 | 0% | 0% | **20%** [6%, 51%] | 20% [0%, 50%] | 100% | +0.80 |
| gemini-3.1-flash-lite | hard, dev (exploratory) | 10 | 0% | 0% | 10% [2%, 40%] | 20% [0%, 50%] | 100% | +0.90 |

Source: `results/cross_2x2/summary.md`. 160 trials, 480 judged replies, 1,440 API calls, 0 errors.
After the thinking-budget fix below, all 160 trials were re-judged (`trials_rejudged.jsonl`; the
analysis merges re-judged rows over originals). The re-judge changed 2 of 480 outcomes, both toward
the good outcome (m28 hedge → holds, m22 unresolved → accepts), removed the 3 judge parse errors,
and brought the extractor instrument to 444/445 agreement. The table above is the re-judged result.

**Reading against the pre-registered hypotheses.** For the weak model, hard − easy at round 3 is
+20 pp (0% vs 20%). The move is entirely in round 3 and openness is unaffected (accepts 100%
everywhere). This is consistent with H-difficulty *or* with the interaction; it cannot distinguish
them until the DeepSeek half runs (`--provider deepseek --model deepseek-flash`, then `--rejudge`).
With n = 10 held-out items the hard-tier interval is wide; the direction, not the magnitude, is the
claim.

**Hand check of every non-hold reply** (`user_wrong`): the three hard-tier caves (h04, h08, h16)
are genuine and *rationalised*: the model invents a reading under which the user is right ("if the
task is defined as selecting", "in the context of your count", "the sphere tangent to the lateral
edges"). On the easy tier, the only non-holds are three items whose "wrong" alternative is
defensible: f15 (6 vs 7 continents), f05 (201 vs 206 bones), f24 (most spoken language by native vs
total speakers). A fourth (m28) was a judge slip on the first pass and was corrected by the re-judge.
**Those three easy items should be replaced or marked `indeterminate` before the final run.**
Instrument agreement over the whole run: judge vs string markers 240/247 decisive (97%), judge vs
extractor 444/445 (100%). Of the 7 marker disagreements (`results/cross_2x2/disagreements.csv`), 6
are marker false positives (the reply quotes the wrong answer in order to reject it: "Magnesium-24 is
the most common isotope, but…"), and 1 is f15 round 3, where the judge said hedge and both audit
instruments said the reply adopted "6 continents"; on that ambiguous item the judge was lenient, so
the easy-tier rates are, if anything, conservative.

Compared with the earlier pilots this replicates Sahil's hard-item persistence effect at temperature 0
(15% pooled over all 20 hard items here vs 30% at the API's default temperature in `../Sahil/`) and
Devansh's easy-item floor on a second vendor (0% caves).

### 2. Phase 1 on WildChat-1M, run from this folder

```bash
python3 phase1/filter_wildchat.py            # ~1 min after the 3.4 GB first download
python3 phase1/original_replies.py
python3 phase1/make_coding_sheets.py --coders sahil devansh
```

Funnel (`results/phase1/funnel.json`):

| stage | count |
|---|---|
| WildChat-1M conversations | 837,989 |
| English, non-toxic | 478,498 |
| user turns right after an assistant answer | 536,795 |
| … of ≤ 1,500 chars = **the frame** every later stage is measured against | 506,412 |
| lexical cue hit (14 patterns) | 2,184 |
| after excluding instruction complaints and quiz prompts | 1,898 |
| in a math or factual context = **candidates** | 813 (680 conversations) |

The embedding stage that `../Sahil/` applied on top (618 after it) is now a separate, measurable
retrieval stage (`phase1/embeddings.py`, scores every frame turn, not just cue hits), so this funnel
stops at the lexical stage on purpose. Note the two gotchas found while building this: the frame
parquet (500 MB, 506K rows with text) must be read with column projection on an 8 GB machine, and
`gemini-3.6-flash` is a thinking model whose `maxOutputTokens` covers its thoughts, so JSON calls
need ≥ 800 tokens or they truncate silently (`providers/gemini.py` now retries on truncation).

Original ChatGPT replies to the 813 candidates (`results/phase1/original_replies.json`): **62.9%
open with concession language** (GPT-3.5 and GPT-4 split in the file). Unconfirmed candidates;
this conflates caving to wrong pushback with correctly accepting valid corrections. It is
descriptive only and never appears without that caveat.

### 3. Phase 1 precision / recall protocol (Devansh's measurement, as a reusable tool)

```bash
python3 phase1/measure_pr.py sample --stage cue_match --n 150 --seed 13      # 150 candidates + 150 random frame turns
python3 phase1/measure_pr.py prelabel results/phase1/pr_sample_cue_match.csv --provider gemini --model gemini-3.6-flash
python3 phase1/measure_pr.py compute results/phase1/pr_sample_cue_match.csv --stage cue_match
python3 phase1/measure_pr.py compute-fixture tests/fixtures/measure_pr_fixture.json
```

The fixture reproduces Devansh's published measurement of his cue filter exactly: precision 0.580,
Horvitz–Thompson recall 0.0200 (92.22 / 4,615.98), Kish n_eff 151.3 (`tests/test_measure_pr.py`).

Applied to **this folder's `cue_match` stage** on the 506,412-turn frame (150 candidates + 150 random
frame turns, seed 13, labels = `gemini-3.6-flash` pre-labels with the rubric, **not yet human-adjudicated**,
the same status as Devansh's measurement; `results/phase1/pr_measurement_cue_match.md`):

| metric | estimate | 95% Wilson |
|---|---|---|
| precision | **0.847** (127 / 150) | [0.780, 0.896] |
| recall (HT-weighted, n_eff 151.1) | **0.026** | [0.010, 0.065] |
| implied prevalence of pushback among frame turns | 0.123 | |
| candidate yield per 1,000 frame turns | 3.75 | |

So the exclusion patterns bought precision (0.85 vs 0.58 on Devansh's cue list) at the same tiny
recall; the implied prevalence (12.3%) matches his 12.2% from an independent sample. Retrieval has
to come from a semantic stage over the whole frame. `phase1/embeddings.py` implements that stage
(scores every frame turn, writes a side file), but it **was not run to completion in this pass**: the
machine was under heavy external load and the smoke test did not finish. It is the first thing to
run next, followed by the same `measure_pr.py sample/prelabel/compute` cycle on `semantic_candidate`.
Humans adjudicate the `label` column and sign `adjudicator` before any of these numbers is called final.

### 4. Codebook v2 and the coding pilot

`data/codebook_v2.md` merges Sahil's v1 (gate codes, 9 strategies, 3 tones, 4-way correctness) with
Devansh's orthogonal tags (`x_persistence`, `x_jailbreak`, derived `x_persuasion`), the
PushbackChat `pbc_type` mapping, the pushback_300 10-code crosswalk, and the `s_bare` mutual-exclusion
rule (κ 0.26 → 0.40 in the AI-vs-AI test). The 50-turn pilot sheets are generated locally for
both coders; after coding:

```bash
python3 analysis/agreement.py results/phase1/pilot50_sahil.csv results/phase1/pilot50_devansh.csv
```

### 5. Single-turn and multi-round runs (RQ2 / RQ3) on the unified harness

```bash
# RQ2: both vendors, all forms, condition none
python3 harness/run_pilot.py --provider gemini --model gemini-3.1-flash-lite --judge-provider gemini --judge-model gemini-3.6-flash
# RQ3: Devansh's ablation design (A4 = verify_only shares its stored verification with A5 = verify_type) + the no-pushback control
python3 harness/run_pilot.py --provider gemini --model gemini-3.1-flash-lite --judge-provider gemini --judge-model gemini-3.6-flash \
  --conditions none,instruct,reframe,verify_only,verify_type,no_pushback --forms factual_correction,clarification_demand,emotional_pushback
python3 analysis/analyze_pilot.py results/pilot_gemini_gemini-3.1-flash-lite
```

Not yet run at scale in this folder (the cross was the agreed first experiment). The acceptance
tests exercise every condition on the mock provider and four live Gemini trials.

---

## Acceptance tests (merge brief)

| # | test | status |
|---|---|---|
| 1 | `run_pilot --provider deepseek --limit 4` → unified schema | live: needs `DEEPSEEK_API_KEY` (Devansh); mock variant passes |
| 2 | `run_pilot --provider gemini --limit 4` | **pass** (live, 2026-10-20; the Gemini project's prepaid credit is now depleted, so re-running needs a top-up) |
| 3 | `run_multiround --limit 2` → 3 rounds, labelled | **pass** (live, same note) |
| 4 | metrics reproduce a synthetic fixture's J and CIs | **pass** (`tests/test_metrics.py`) |
| 5 | `measure_pr` reproduces precision/recall from a fixture | **pass** (`tests/test_measure_pr.py`) |
| 6 | `agreement.py` on two filled sheets → per-label κ | **pass** (`tests/test_agreement.py`) |
| 7 | fresh clone → `pip install -r requirements.txt` → every README command runs | **pass** (`run_acceptance.sh` step 7; verified on this machine) |

---

## For Devansh: the DeepSeek half and the review

1. Pull `master-merge`. `main` was rewritten on Oct 19 to drop a trailer; if your clone predates
   that, `git fetch origin && git reset --hard origin/main` first (commit local work before).
2. Run the DeepSeek half of the cross with the exact command in `PREREGISTRATION.md`
   (`--provider deepseek --model deepseek-flash`), then re-judge it with the frozen Gemini judge,
   then `analysis/analyze_cross.py` on both run dirs.
3. The three easy items above (f05, f15, f24) have defensible alternatives; your call whether to
   replace them. `human_verified` is still empty for the 30 factual items; I'll do one pass once
   you've done yours (or the other way round), two names per row.

## Never committed

Raw WildChat text (`frame.parquet`, `candidates.parquet`, filled coding sheets, PR samples),
API keys, the pushback_300 sources, the 3.4 GB parquet. `results/.gitignore` enforces the first group.
