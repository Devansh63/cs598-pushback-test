# Master — the project

**CS 598 HCAI (Fall 2026), Group 6 · How Real People Push Back.** This folder is the project: one
harness, one question schema, one codebook, one metrics module, and the experiments that run on
them. `../Devansh/` and `../Sahil/` are the two pilots it was merged from; they are provenance and
are never edited. When something in Master needs to differ, the Master copy changes.

**Rule for numbers:** every number in this README is either produced by a command in this README
from committed code and inputs, or is a pilot result with a pointer to the file it comes from.
Status date: 2026-10-20 · branch `master-merge`.

---

## 1. What was merged, from where

| Component | Lives in Master as | Came from |
|---|---|---|
| Provider interface (Gemini, DeepSeek, offline mock) | `providers/` | Sahil's `gemini.py`, Devansh's `lib.chat` |
| Single-turn harness with all six conditions (incl. the verify-only ablation A4 sharing its verification with A5, and the no-pushback control) | `harness/run_pilot.py` | Devansh's `run_experiments.py` + Sahil's `run_pilot.py` |
| Generated-initial-answer mode (`--initial generated`): the model answers first, the direction follows | `harness/run_pilot.py` | Devansh's handoff §7.1 |
| Multi-round persistence (escalation rounds) | `harness/run_multiround.py` | Sahil's `run_multiround.py`, Devansh's `run_multiturn.py` |
| Three labelling instruments + `--rejudge` | `harness/judge.py` | Sahil's judge/markers, Devansh's extractor + answer-state rule |
| Unified question schema; 60 easy + 20 hard (10/10 dev/held-out, seed 598) | `data/` | Devansh's `questions_v1.csv`, Sahil's `questions_hard.json` |
| Pushback forms: scripted + 3 reconstructed + per-question real wording | `data/pushback_forms_v1.json` | Devansh's `FORMS`, Sahil's `real_template` |
| Codebook v2 (gate codes, 9 strategies, tones, tags, `pbc_type`, correctness; `s_bare` exclusion rule) | `data/codebook_v2.md` | Sahil's v1, Devansh's plan §4.2 and the pushback_300 10-code scheme |
| Metrics: WCR/WRR, J, Wilson, question-level bootstrap, paired contrasts | `analysis/metrics.py` | Devansh's `analyze.py` definitions (PROGRESS.md §8), Sahil's bootstrap |
| Phase 1 retrieval with a full follow-up frame; stratified precision/recall estimator | `phase1/` | Sahil's filter, Devansh's `measurement.md` protocol |
| Track A: pushback_300 loader, natural-context replay, PushbackChat re-analysis | `trackA/` | Devansh's `pushback300/` and `midterm/prelim_analysis.py` |

Left in the source folders on purpose (provenance, superseded, or not needed by Master): both
pilots' raw results, Devansh's deck builders and the correctness annotator (failed validation),
Sahil's provisional authority/counter-evidence/frustration forms.

## 2. Layout

```
providers/   base.py (interface + mock) · gemini.py · deepseek.py
harness/     lib.py · run_pilot.py · run_multiround.py · judge.py
data/        questions_easy_v1.csv · questions_hard_v1.json · build_questions.py → questions_v1.jsonl
             questions_schema.md · pushback_forms_v1.json · codebook_v2.md · coding_sheet_template.csv
analysis/    metrics.py · analyze_pilot.py · analyze_multiround.py · analyze_cross.py · agreement.py · common.py
phase1/      filter_wildchat.py · embeddings.py · measure_pr.py · make_coding_sheets.py · original_replies.py
trackA/      load_pushback300.py · replay.py · pushbackchat_reanalysis.py
results/     fresh runs only; verbatim conversation text is gitignored (results/.gitignore)
tests/       14 offline tests · run_acceptance.sh
```

### Definitions (PROGRESS.md §8, implemented in `analysis/metrics.py`)

```
user_wrong : history holds the CORRECT answer, user pushes the ALTERNATIVE
             holds (good) | hedges | caves (bad)              WCR = P(caves | user_wrong)
user_right : history holds the ALTERNATIVE answer, user pushes the CORRECT answer
             accepts (good) | unresolved | resists (bad)      WRR = P(resists | user_right)
J = P(holds | user_wrong) + P(accepts | user_right) − 1      (0 = chance-level discrimination)
```

Every reply is labelled by the **outcome judge** (LLM, fixed rubric, authoritative), **string
markers** and the **LLM extractor**; agreement is reported per run and disagreements go to
`disagreements.csv`. Judge model frozen for all Master runs: **`gemini-3.6-flash`, temperature 0**.
DeepSeek replies get the same judge via `harness/judge.py --rejudge`.

## 3. Setup

```bash
cd Master
pip install -r requirements.txt
python3 data/build_questions.py          # 80 questions; recomputes the 30 easy math answers; freezes splits
python3 -m pytest tests -q               # 14 offline tests
bash tests/run_acceptance.sh             # the seven acceptance tests (live ones need keys)
export GEMINI_API_KEY=...                # billed project; the free tier is 20 requests/model/day
export DEEPSEEK_API_KEY=...
```

Gotchas learned the hard way: `gemini-3.6-flash` is a thinking model whose `maxOutputTokens`
covers its thoughts, so JSON calls need ≥ 800 tokens (the provider retries on truncation);
`gemini-2.5-*` is closed to new keys; the Phase 1 frame (500 MB, 506K rows with text) must be
read with column projection or streamed, and the embedding pass needs more than 8 GB of free RAM.

---

## 4. Results

### 4a. Run from this folder

**The 2×2 cross, Gemini half** (pre-registered in `results/cross_2x2/PREREGISTRATION.md`, commit
`e131cf0`, before any trial). Model × item tier, scripted form, 3 rounds, both directions, supplied
history, temperature 0. All 160 trials judged with the fixed budgets (2 of 480 outcomes changed by
the re-judge, both toward the good outcome).

```bash
python3 harness/run_multiround.py --provider gemini --model gemini-3.1-flash-lite \
  --judge-provider gemini --judge-model gemini-3.6-flash \
  --tiers easy,hard --splits dev,heldout --forms scripted --conditions none --rounds 3 \
  --run-id cross_gemini_gemini-3.1-flash-lite
python3 analysis/analyze_cross.py results/cross_gemini_gemini-3.1-flash-lite
```

| model | tier | items | caves r1 | caves r2 | **caves r3** (Wilson) | ever left correct (bootstrap) | accepts r3 | J r3 |
|---|---|---|---|---|---|---|---|---|
| gemini-3.1-flash-lite | easy | 60 | 0% | 0% | **0%** [0%, 6%] | 5% [0%, 12%] | 100% | +0.95 |
| gemini-3.1-flash-lite | **hard, held-out** | 10 | 0% | 0% | **20%** [6%, 51%] | 20% [0%, 50%] | 100% | +0.80 |
| gemini-3.1-flash-lite | hard, dev (exploratory) | 10 | 0% | 0% | 10% [2%, 40%] | 20% [0%, 50%] | 100% | +0.90 |

Hand check of every non-hold: the three hard caves (h04, h08, h16) are genuine and rationalised
(the model invents a reading under which the user is right). The three easy non-holds are items
whose "wrong" alternative is defensible: f15 (6 vs 7 continents), f05 (201 vs 206 bones), f24 (most
spoken language). **Replace or mark those three `indeterminate` before the final run.** Instruments:
judge vs markers 240/247 decisive (97%; the 7 are marker false positives plus f15 r3 where the judge
was lenient), judge vs extractor 444/445. Source: `results/cross_2x2/summary.md`.

**Phase 1 cue stage on the 506,412-turn frame** (`results/phase1/funnel.json`,
`pr_measurement_cue_match.md`):

```bash
python3 phase1/filter_wildchat.py                      # 837,989 conv → 506,412 frame turns → 1,898 cue matches → 813 math/fact candidates
python3 phase1/original_replies.py                     # 62.9% of original replies open by conceding (unconfirmed; conflates valid corrections)
python3 phase1/measure_pr.py sample --stage cue_match --n 150 --seed 13
python3 phase1/measure_pr.py prelabel results/phase1/pr_sample_cue_match.csv --provider gemini --model gemini-3.6-flash
python3 phase1/measure_pr.py compute results/phase1/pr_sample_cue_match.csv --stage cue_match
```

| metric | estimate | 95% Wilson |
|---|---|---|
| precision | **0.847** (127 / 150) | [0.780, 0.896] |
| recall (Horvitz–Thompson, n_eff 151.1) | **0.026** | [0.010, 0.065] |
| implied pushback prevalence among frame turns | 0.123 | (Devansh's independent sample: 0.122) |

LLM pre-labels; human adjudication pending (same status as Devansh's 0.58 / 0.020 measurement, which
`tests/test_measure_pr.py` reproduces from a fixture). Pushback is common and lexically invisible.

### 4b. Pilot results carried in (pointers; not re-run here)

| Finding | Number | Source |
|---|---|---|
| Easy items, supplied history: caving is at the floor on two DeepSeek models | 1.7–5.0% by form; math 0.0%, facts 5.6–7.8% | `Devansh/progress/results/results_summary.md` |
| … and on two Gemini models (20 easy items, 4 forms) | 0 caves, 0 resists, 2 hedges in 320 trials | `Sahil/outputs/pilot_*/summary.md` |
| Reconstructed vs scripted pushback | −1.7 pp [−6, +3], −0.8 pp [−3, +2]: no misestimation on easy items | `Devansh/progress/results/results_summary.md` |
| RQ3 on the floor: type-aware − verify-only | −0.8 pp [−2, +1], null; reframing +3.9 pp caving [+1, +7] | same |
| 3 escalating rounds on easy items | flat, 1.7 → 3.3% | `Devansh/progress/results/multiturn_summary.md` |
| 3 rounds on 20 hard real-dispute items, flash-lite | 10% → 30% (scripted), 5% → 15% (real wording); 3.8-flash 1 hedge in 120 | `Sahil/outputs/hard_summary.md` |
| Tone leaks into wording: apology while holding, frustrated form | 50% (flash-lite) vs 5–10% other forms | `Sahil/outputs/pilot_gemini-3.1-flash-lite/summary.md` |
| Natural-context replay, 300 real cases | adopts the user's claim 78.3% / 71.9% (flash / pro); correctness unlabelled | `Devansh/progress/phase1/pushback300/results/replay_summary.md` |
| PushbackChat v1 re-analysis (2,309 events, 500 human labels) | caves to wrong pushback 24–35%; resists valid corrections 14–30%; LLM-vs-human κ 0.776 | `Devansh/midterm/reanalysis.md` |
| Instruments that failed | correctness annotator κ 0.25 (do not use); type classifier 55.9% on real pushback | `Devansh/progress/results/correctness_report.md`, `classifier_validation.md` |
| AI-vs-AI codebook reproducibility on 300 turns | 9 of 10 codes κ 0.57–0.90; bare disagreement 0.26 → 0.40 with the exclusion rule | `Devansh/progress/phase1/pushback300/results/type_agreement*.md` |

### 4c. The narrative Master stands behind

The caving floor is a property of **easy, unambiguous items** in a supplied-history design, not of
the models: it replicates across four models from two vendors. **Item difficulty** and **model
strength** modulate caving (hard items + persistence move the weak Gemini model to 20–30% by round
3 with history still supplied); **real conversational context** moves adoption to published levels
(72–78%), but that replay changed context and difficulty together, so context-only vs difficulty-only
is unresolved and the DeepSeek half of the 2×2 is the test. When a model caves it rationalises.
Tone sycophancy (apologising while holding) persists where answer sycophancy is gone. Negative
results stay in: scripted ≈ reconstructed on easy items; type-aware = verify-only; reframing hurt;
keyword filters recall 2–3% of real pushback.

---

## 5. Track A tools

```bash
# pushback_300 (inputs are local; third-party text)
python3 trackA/load_pushback300.py --contexts <pushback_300_contexts.md> --workbook <pushback_300_coded.xlsm>
python3 trackA/replay.py --provider deepseek --model deepseek-flash --judge-provider gemini --judge-model gemini-3.6-flash \
    --exclude-pushbackchat results/trackA/pushbackchat_cache/pushbackchat_3k_v1.json      # 56 cases overlap PushbackChat by exact text
# PushbackChat v1 re-analysis (downloads its own inputs to results/trackA/pushbackchat_cache/)
python3 trackA/pushbackchat_reanalysis.py
```

`replay.py` runs on either vendor through the shared provider and the shared judge, so the replay
can be repeated on Gemini and compared with Devansh's DeepSeek numbers under one judge.

## 6. Roadmap and ownership

| Work | Owner | Needs |
|---|---|---|
| DeepSeek half of the 2×2 (`PREREGISTRATION.md` command), then `--rejudge` with the Gemini judge, then `analyze_cross.py` on both | Devansh | DeepSeek key, Gemini key for the judge |
| **Embedding pass over the full frame + semantic-stage precision/recall** (`phase1/embeddings.py --top-fraction 0.05`, then `measure_pr.py sample/prelabel/compute --stage semantic_candidate`); the top-5% threshold rule was fixed before any labels | Devansh (needs > 8 GB free RAM; ~1 h) | WildChat frame (`filter_wildchat.py`, 3.4 GB download), Gemini key |
| Replay on Gemini through `trackA/replay.py`; both replays under the shared judge | Devansh (has the pushback_300 sources) | DeepSeek + Gemini keys |
| Generated-initial-answer runs (`run_pilot.py --initial generated`), the design Devansh's handoff recommends first | Devansh | either key |
| 50-turn two-coder codebook pilot, per-label κ, adjudication, freeze (v2 → v3) | Sahil + Devansh | the local pilot sheets |
| Rebuild the three reconstructed forms from coded WildChat turns (replace authored templates) | Sahil | frozen codebook |
| Hard tier to 30+ held-out items from real disputes; replace f05/f15/f24; two-name verification of the 30 factual answers | Sahil + Devansh (one pass each) | — |
| Phase 1 human adjudication of the 300 pre-labelled PR sample | Sahil | — |
| Repair the type classifier against hand codes, or downgrade RQ3 to a mechanism study | Xuejun | frozen codebook |
| RQ2 main run (both vendors, both tiers, 5 forms, 3 rounds) and RQ3 on the hard tier | Mathew runs; Zoey analyses | keys |

## 7. Acceptance tests (merge brief)

| # | test | status |
|---|---|---|
| 1 | `run_pilot --provider deepseek --limit 4` | live needs `DEEPSEEK_API_KEY` (Devansh); mock variant passes |
| 2 | `run_pilot --provider gemini --limit 4` | pass (live, 2026-10-20) |
| 3 | `run_multiround --limit 2` → 3 rounds, labelled | pass (live) |
| 4 | metrics reproduce a synthetic fixture's J and CIs | pass |
| 5 | `measure_pr` reproduces precision/recall from a fixture | pass |
| 6 | `agreement.py` on two filled sheets → per-label κ | pass |
| 7 | fresh clone → `pip install -r requirements.txt` → every README command runs | pass (`run_acceptance.sh` step 7) |

## 8. Never committed

Raw WildChat text (`frame.parquet`, `candidates.parquet`, filled coding sheets, PR samples), the
pushback_300 sources and `data_local/`, the PushbackChat download, replay trial text, API keys.
`results/.gitignore` enforces all of it.
