# How Real People Push Back

**Testing and improving how chatbots respond to user disagreement** — CS 598 HCI (Fall 2026), Group 6, University of Illinois Urbana-Champaign.

When a user disagrees with a chatbot's correct answer, the chatbot often gives in. This project measures that behaviour on pushback that real people actually wrote, and asks whether a response layer that adapts to the *type* of pushback does better than generic fixes.

**Status: pilot executed end to end.** A full Phase 2/Phase 3 pilot (2,040 trials, two models, both directions, four conditions) and a Phase 1 filter measurement (60,000 WildChat conversations) are complete. Results, including negative ones, are in [`progress/PROGRESS.md`](progress/PROGRESS.md).

---

## Headline findings from the pilot

| # | Finding | Number |
|---|---|---|
| 1 | Caving is at the floor on short verifiable answers | 0–8% caving; math **0.0%**, facts **5.6–7.8%** |
| 2 | Scripted pushback did **not** misestimate caving | reconstructed − scripted: −1.7 pp [−6, 3], −0.8 pp [−3, 2] |
| 3 | Question reframing **hurt** | +3.9 pp caving [1, 7], good outcome −5.0 pp [−8, −2] |
| 4 | Type-aware guidance ≈ verification alone | −0.8 pp [−2, 1], null |
| 5 | Repeated pushback does not accumulate caving | flat 1.7–3.3% across three escalating rounds |
| 6 | The proposed lexical filter fails on the open corpus | precision 58.0%, **recall 2.0%**, while ~12.2% of pairs are pushback |
| 7 | Two instruments failed validation | correctness annotator κ 0.255/0.242 (released pipeline: 0.773); type classifier 55.9% on real pushback |

Finding 5 is the important one for planning: the floor is a property of the design (the initial answer is supplied as history, and the items are unambiguous), not of the models. More trials will not fix it; the design has to change.

---

## Repository map

```
progress/                        pilot executed 2026-10-19
  PROGRESS.md                    full progress log: design, results, instruments, negative results, limits
  Progress_Slides.pptx           9 insert-ready result slides (Illinois template) + speaker notes
  build_progress_deck.py         rebuilds those slides
  code/
    lib.py                       API client, prompts, conditions, answer-state detector, statistics
    make_stimuli.py              builds the 480 pushback stimuli from real corpus exemplars
    run_experiments.py           RQ2 + RQ3 harness (resumable JSONL logging)
    label_states.py              re-derives the final answer for every trial
    analyze.py                   rates, Wilson intervals, cluster bootstrap, sensitivity analysis
    run_multiturn.py             multi-turn escalation arm
    validate_state.py            answer-state detector reliability
    validate_classifier.py       pushback classifier on real pushback
    annotate_correctness.py      correctness annotator (failed validation — see report)
  data/
    make_questions.py            builds and verifies the 60-item question set
    questions_v1.csv             30 math (answers recomputed) + 30 factual items
    stimuli_v1.jsonl             480 stimuli = 60 questions x 2 directions x 4 forms
  results/
    trials.jsonl                 2,040 trials: prompts, responses, conditions, labels
    results_summary.md           tables with confidence intervals
    multiturn_summary.md         escalation curve
    state_validation.md          detector agreement
    state_relabel_report.md      relabelling audit
    classifier_validation.md     per-label precision/recall on real pushback
    correctness_report.md        annotator validation (negative result)
    numbers.json                 machine-readable headline numbers
  phase1/
    measurement.md               filter precision/recall on 60,000 WildChat conversations
    metrics.json                 all counts and estimates behind that report
    *.py, run_all.sh             the measurement pipeline

midterm/                         material produced for the midterm presentation
  Group6_Midterm_Plan.md         revised scope, response to the six review points, annotation protocol, power analysis
  Group6_Midterm_Slides.pptx     19-slide midterm deck (Illinois template) + speaker notes
  prelim_analysis.py             re-analysis of the public PushbackChat release (reproducible)
  reanalysis.md / .json          results of that re-analysis
  build_deck.py                  rebuilds the midterm deck
```

---

## Reproducing

```bash
cd progress/code
export DEEPSEEK_API_KEY=...        # models are DeepSeek-V4.1-Flash and DeepSeek-V4-Pro
python3 ../data/make_questions.py  # builds + verifies the question set
python3 make_stimuli.py            # builds the 480 stimuli
python3 run_experiments.py         # 2,040 trials, ~8 min on 16 workers, $0.48
python3 label_states.py            # re-derive answer states
python3 analyze.py                 # -> results/results_summary.md
python3 run_multiturn.py           # escalation arm
python3 validate_state.py
python3 validate_classifier.py
python3 annotate_correctness.py --mode report
```

Every stage appends to a JSONL log and skips completed units, so an interrupted run resumes.

Phase 1 (no API key needed for sampling; the labeling step uses the same key):

```bash
cd progress/phase1
bash run_all.sh
```

The midterm re-analysis is standalone and downloads its own inputs:

```bash
cd midterm
python3 prelim_analysis.py         # -> reanalysis.md, reanalysis.json
```

---

## Data sources and licensing

- **WildChat-1M** (Zhao et al., 2024) — sampled for the Phase 1 measurement. ODC-BY. Only aggregate labels, metrics and derived statistics are committed here; raw conversation dumps are excluded and regenerable from the scripts.
- **PushbackChat v1** (anonymous release derived from WildChat) — 2,309 real pushback events, 500 human correctness labels, behaviour logs. Used as the Phase 1 substrate and for exemplar provenance. Not vendored; `midterm/prelim_analysis.py` downloads it.
- Model outputs in `progress/results/` were generated by us through the DeepSeek API.

No user identities are included, and no API keys are stored in this repository.

---

## What is deliberately not in this repository

- Raw WildChat conversation dumps (~440 MB; third-party text, regenerable).
- The cached public corpus downloads used by the midterm analysis (~36 MB; regenerable).
- The team's own presentation deck, which lives in the course drive.

---

## Notes on the state of the evidence

This is a **pilot**, not the final study. Known limits, all stated in `progress/PROGRESS.md`:

- One vendor's models (two DeepSeek variants), 60 questions, three reconstructed pushback forms.
- The 30 factual answers are curated but **not yet human-verified** (`human_verified` is empty in `questions_v1.csv`).
- No development/held-out split: the intervention prompts were frozen before the run, but the measurement instrument was revised after inspecting results.
- Answer states are assigned by an LLM extractor (validated against an automatic rule, not against human labels).
- Phase 1 labels are single-model judgments without human adjudication.

---

## People

| Member | Role |
|---|---|
| Devansh Agrawal | Coding lead; pilot implementation and analysis; scope revision |
| Zhongyin Wang | Data lead; corpus acquisition and licensing |
| Sahil Sashi | Coding lead; codebook and annotation protocol |
| Mathew Pan | Testing lead; question set, harness, scoring, model logs |
| Xuejun Zhang | Build lead; classifier, response layer, interface |
| Zoey Yao | Analysis and writing lead; statistics, positioning, report |
