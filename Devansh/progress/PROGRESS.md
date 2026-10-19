# Progress log — Group 6, CS 598 HCI

**Status date:** 2026-10-19 · **Scope:** Phase 2 / Phase 3 pilot executed end to end, plus a Phase 1 instrument check.
**Nothing in this folder modifies the proposal, the original decks, or the published corpus.** Every artifact here is new, and every number is reproducible from the scripts listed in §8.

---

## 0. What is now real

| Deliverable | Status | Evidence |
|---|---|---|
| Question set, 60 items with verified answers and a plausible wrong alternative | **done** | `data/questions_v1.csv`; 30 math answers recomputed from expressions, 0 failures |
| Stimulus set, 480 pushback texts (2 directions × 4 forms), 3 forms documented against real corpus events | **done** | `data/stimuli_v1.jsonl` |
| Experiment harness (conditions, both directions, resumable JSONL logging) | **done** | `code/run_experiments.py` |
| **RQ2 pilot: 2 models × 60 questions × 2 directions × 4 forms** | **done — 960 trials** | `results/trials.jsonl` |
| **RQ3 pilot: 4 conditions on 1 model, 3 forms** | **done — 1,440 trials** | same log |
| Instrument validation (verification, answer-state detector, classifier) | **done** | `code/validate_state.py`, `validate_classifier.py` |
| Multi-turn escalation arm (does caving accumulate?) | **done** | `results/multiturn_summary.md` |
| Correctness annotator to extend the corpus to unlabelled types | **attempted, failed validation** | `results/correctness_report.md` |
| Phase 1 WildChat precision/recall measurement | **done** | `Phase1/measurement.md`: precision 58.0%, recall 2.0% on 37,857 real pairs |
| 300-case real corpus parsed + audited | **done** | `phase1/pushback300/`: 300/300 joined, all replay-ready |
| Prescreen + 10-code reproducibility | **done** | prescreen 100/100; per-code κ 0.26–0.90, bare disagreement weakest |
| **Natural-context replay (the key result)** | **done** | **72–78% adoption** vs 0–8% in the supplied-history design |
| Human verification of factual answers, two-coder annotation, demo interface, IRB | **not started** | — |

Cost: the main RQ2+RQ3 run logged **4,421 calls / $0.48** exactly (its own accounting). Across every run in this log — re-labelling, multi-turn, instrument validation, annotation, Phase 1 — the total is approximately **9,600 calls / ~$1.00**, which is an estimate: only the main run self-reports cost. Wall clock for the main run: 8 minutes on 16 workers.

---

## 1. Design decisions made while building

1. **Both initial answers are supplied as conversation history**, exactly as the revised proposal specifies. Consequence: this measures *response to pushback*, not initial answering accuracy; it also anchors the model to its own prior answer (§5 explains why that matters).
2. **Three reconstructable forms**, chosen so each maps to a PushbackChat type: `factual_correction`, `clarification_demand`, `emotional_pushback`. Each template is documented against a real event (`pb_0027`, `pb_0070`, `pb_1400`) that demonstrably exhibits the strategy. The templates are authored, not verbatim; the stimulus file records both.
3. **Type-conditional guidance is isolated** by giving `verify_only` and `verify_type` the *same stored verification output* and the same response prompt, differing only by the predicted label and its guidance. That is the proposal's design, and it removes re-verification noise from the contrast.
4. **Answer state is measured twice**: an automatic assertion-cue rule, then an LLM extractor for every trial. The extractor label is used; the automatic label is retained for audit (§4).

---

## 2. RQ2 — how the two models respond (no intervention)

60 questions, both directions, four pushback forms, two models (DeepSeek-V4.1-Flash, DeepSeek-V4-Pro).

| model | form | n | cave \| user wrong | accept \| user right | resist \| user right | J |
|---|---|---|---|---|---|---|
| flash | factual_correction | 120 | **1.7%** [0, 9] | 98.3% | 1.7% | +95.0 |
| flash | clarification_demand | 120 | **5.0%** [2, 14] | 95.0% | 5.0% | +90.0 |
| flash | emotional_pushback | 120 | **5.0%** [2, 14] | 98.3% | 1.7% | +93.3 |
| flash | scripted | 120 | **3.3%** [1, 11] | 96.7% | 3.3% | +91.7 |
| pro | factual_correction | 120 | **1.7%** [0, 9] | 98.3% | 1.7% | +95.0 |
| pro | clarification_demand | 120 | **1.7%** [0, 9] | 98.3% | 1.7% | +95.0 |
| pro | emotional_pushback | 120 | **5.0%** [2, 14] | 95.0% | 1.7% | +90.0 |
| pro | scripted | 120 | **1.7%** [0, 9] | 98.3% | 1.7% | +93.3 |

**Reconstructed vs scripted.** Paired over questions, the difference in good outcome is
flash **−1.7 pp [−6, 3]** and pro **−0.8 pp [−3, 2]**. Both intervals span zero, so this pilot gives **no evidence that scripted pushback misestimates caving** — the paper's motivating gap is not reproduced here. That is a real result, not a null to hide; it says the gap may be about *context and history* rather than about wording.

**Task type dominates pushback form.**

| domain | cave \| user wrong (flash) | cave \| user wrong (pro) |
|---|---|---|
| math | **0.0%** | **0.0%** |
| factual knowledge | **7.8%** | **5.6%** |

Every caving event in the pilot came from factual-knowledge items. Arithmetic that the model can verify by computation is essentially immune to a single pushback.

---

## 3. RQ3 — does type-aware guidance beat verification?

One model (flash), 3 reconstructed forms, both directions, 360 matched trials per condition.

| condition | cave \| user wrong | accept \| user right | J |
|---|---|---|---|
| none | 3.9% | 97.2% | +92.8 |
| reframe (Dubois et al.) | **8.9%** | 93.3% | +82.8 |
| verify_only | 2.2% | 96.7% | +94.4 |
| verify_type | **1.7%** | 97.8% | **+95.6** |

**Pre-registered contrast — verify_type vs verify_only:** cave **−0.8 pp [−2, 1]**, good outcome **+0.6 pp [−1, 2]**. Null. We can rule out a gain larger than ~2 pp, and the ceiling (caving already at 2%) leaves almost nothing to gain.

**Exploratory contrasts:**
- `verify_only − none`: −0.6 pp [−2, 1] — verification alone does nothing measurable.
- **`reframe − none`: +3.9 pp [1, 7] caving, good outcome −5.0 pp [−8, −2] — question reframing made things significantly *worse*.**
- `verify_type − reframe`: +6.4 pp [3, 11] good outcome.

The reframe failure has a visible mechanism: the instruction asks the model to restate the user's claim as a neutral question, and the models do exactly that, adopting the user's (incorrect) framing as the premise before answering. It contradicts Dubois et al.'s reported benefit, in a setting closer to real use. This is the most interesting finding in the pilot and needs a mechanism study, not a bigger sample.

---

## 4. Instrument checks (why the numbers above can be trusted, and where they cannot)

| Instrument | Result | Consequence |
|---|---|---|
| Verification call vs answer key | **99.6%** agreement (717/720) | the verification component works |
| Automatic answer-state rule vs extractor | **91.7%** agreement (110/120) | 84 labels flipped after re-derivation; primary analysis uses the extractor |
| Extractor re-label vs original | **94.7%** (1,931/2,040) | 109 trials changed; all in the log, auditable |
| Classifier on reconstructed stimuli | 100% (trivially — templates) | **not evidence of classifier quality** |
| Classifier on **real** pushback | **55.9%** (33/59) | `clarification_demand` recall only 35%; the type-aware arm is built on a weak detector for real data |
| Response-quality coding | 96–98% address the user's evidence | the replies are not dismissive; caving is not a tone problem here |

The classifier result is the uncomfortable one. Type-aware guidance is only as good as the label it conditions on, and on real pushback the classifier recovers the type about half the time. Any claim about type-awareness has to carry this caveat.

---

## 5. The floor effect, and why it is the main methodological finding

Caving is 0–8% in this design. PushbackChat's natural-context measurement of the same construct
(inappropriate capitulation) is 24–35%. We tested one explanation directly and it failed:

### Multi-turn escalation (240 conversations, 3 rounds each, 2,880 scored replies)

The user's claim held constant; the form escalated
(factual_correction → clarification_demand → emotional_pushback).

| model | cave after round 1 | round 2 | round 3 | accept after round 3 |
|---|---|---|---|---|
| flash | 1.7% | 1.7% | **3.3%** | 98.3% |
| pro | 3.3% | 3.3% | **3.3%** | 98.3% |

**Repeated, escalating pushback does not accumulate caving** for these models on verifiable
short-answer tasks. The curve is flat. That rules out "one short turn is too weak" as the
explanation and points at the remaining two:

1. **Supplied history anchors the model.** The proposal's design puts the assistant's answer in
   the history, so the model is defending text it "already said" rather than regenerating. This
   plausibly *reduces* caving relative to natural conversations, where the answer was the model's
   own generation and the user has already seen it.
2. **The items are unambiguous.** Every question has one short verified answer, so the model has
   a strongly represented correct answer to fall back on. Open-domain and opinion-adjacent facts
   are where PushbackChat sees capitulation.

This matters for the final report: if the supplied-history, single-answer design cannot produce
caving, the intervention comparison is uninformative even with a large N. The fix is design, not
sample size — natural-context replay, harder items, or answers the model must generate itself
before the pushback arrives.

**Resolved in §8.4.** Replaying the real conversation restores adoption to 72–78%, matching the
published range. The floor was the design.

**Independent corroboration.** A teammate's separate pilot on Gemini (`Sahil/outputs/pilot_gemini-3.8-flash/summary.md`,
20 questions, four forms, 160 judged trials) reports **0% caving and 0% resistance** in every
condition — the same floor, a different model and different stimuli. That makes the effect a
property of the supplied-history design rather than of one vendor's models.

---

## 6. Phase 1 — the lexical filter recovers about 2% of real pushback

Measured on a 60,000-conversation random sample of WildChat-1M (34,800 English conversations,
37,857 usable assistant→user pairs), using the cue suite from the proposal and an LLM judge for
labels. Artifacts and assumptions: `Progress/phase1/measurement.md`.

| quantity | estimate | 95% CI |
|---|---|---|
| precision of the cue suite (candidate pairs that are genuine pushback) | **58.0%** | [50.0, 65.6] |
| recall of the cue suite (genuine pushback it retrieves) | **2.0%** | [0.7, 5.7] |
| candidate yield | 4.2 per 1,000 English pairs | — |
| implied prevalence of genuine pushback among English pairs | **~12.2%** | — |

Two consequences, both important:

1. **Pushback is common; lexically visible pushback is not.** About one in eight assistant→user
   pairs is a genuine challenge to the answer, but the cue suite finds one in fifty. A Phase 1
   built on lexical filters would sample a biased and tiny slice of the phenomenon.
2. **The earlier 20.7% figure was an optimistic ceiling.** That was recall measured *inside a
   set already known to be pushback*. Against the open corpus the same idea performs at 2%.

Cue-level precision also varies enormously: `that's wrong` 100% (n=5), `no, that's` 90% (n=10),
`are you sure` 71% (n=41), but `incorrect` only 37% (n=59) — the most frequent cue is the least
reliable, because it fires on quoted code and self-corrections. If the team keeps a lexical first
pass, it should weight cues rather than OR them, and use a semantic stage for the rest.

Limitation: labels are single-model judgments without human adjudication, so both estimates carry
instrument error (see the file's own assumptions section).

---

## 7. Negative results to keep (do not bury)

1. **Correctness annotator failed validation.** Two prompt versions, κ = 0.255 and 0.242 against
   the 500 human labels, versus **0.773** for the released pipeline's own labels. Cause: we do not
   have their verification evidence, so most disputes are genuinely undecidable from text alone.
   Consequence: the 258 extension pre-labels are marked *do not report*; extending correctness
   coverage needs either their prompt/evidence or human annotation. Cost of learning this: 1,250 calls.
2. **Question reframing hurt** (§3). One prompt instantiation, not a refutation of Dubois et al.,
   but directly relevant to anyone deploying it.
3. **Scripted vs reconstructed pushback did not differ** (§2), which weakens our own original
   framing of the problem.
4. **The classifier does not generalize** to real pushback (§4).
5. **Bare disagreement (B) is not reproducible** across two AI coders (κ=0.26; 0.40 with the
   workbook's own exclusion rule). That code cannot carry a claim until the definition is sharpened
   or the code is dropped (§8.3).

---

## 8. A second real-pushback corpus (300 cases) resolves the floor question

The team supplied 300 candidate pushback events from WildChat-1M (revision `7d6490e`) with full
conversation context, plus a workbook of AI preliminary coding. We parsed, audited, re-coded and
replayed them. Code: `progress/phase1/pushback300/`. **Raw conversation text is not committed** —
the material is not de-identified; only aggregates and scripts are in git.

### 8.1 The corpus holds up

300 cases from 14 parquet shards; messages per case 3–11 (median 5); the target turn is always the
final message, always a user turn, and always preceded by an assistant answer; context before the
target is median 1,650 chars (max 6,467). Nothing structural blocked replay. There are **no human
codes and no correctness labels** — `team_notes` is empty in all 300 rows.

### 8.2 The AI prescreen is reliable

| check | result |
|---|---|
| prescreen precision (100 sampled cases, independent judge) | **100/100** [96, 100] |

This is agreement between two LLM judges, not against human labels, so it bounds the error rather
than settling it — but it means the set can be treated as pushback candidates.

### 8.3 The 10-code scheme reproduces, except bare disagreement

Two independent AI passes over all 300 turns, per-code Cohen's κ:

| code | label | κ | | code | label | κ |
|---|---|---|---|---|---|---|
| R | recheck request | 0.81 | | A | alternative claim | 0.71 |
| E | counter-evidence | 0.84 | | T | task/constraint correction | 0.70 |
| I | inconsistency challenge | 0.83 | | F | frustration | 0.57 (n=3) |
| P | repeated insistence | 0.90 | | **B** | **bare disagreement** | **0.26** |
| S | authority/source appeal | 0.89 | | L | reasoning challenge | 0.76 |

Identical code set: 37.3%; mean Jaccard 68.3%. Adding the workbook's own mutual-exclusion rule for
B (it may not co-occur with A/I/L/E/S/T) raises identical-set agreement to 47.3%, Jaccard to 72.3%,
and B's κ to **0.40** — better, still the weak point. **B are the definition the two-human pass must
sharpen or drop.** These κ values are an upper bound: two AI coders share training data and agree
more than two humans will.

### 8.4 Natural-context replay: the floor was the design, not the models

600 trials (300 cases × 2 models), full original context replayed up to the target turn.

| model | n | adopts user claim | maintains | hedges | deflects | adds reasoning |
|---|---|---|---|---|---|---|
| flash | 300 | **78.3%** [73, 83] | 17.3% | 3.3% | 1.0% | 89% |
| pro | 299 | **71.9%** [67, 77] | 24.1% | 3.0% | 0.7% | 86% |

| setting | adoption / capitulation |
|---|---|
| this project's pilot, supplied history, single turn | 0–8% |
| PushbackChat, 2,309 real events, published | 67.0–77.1% |
| **this replay** | **78.3% / 71.9%** |

Adoption by workbook subtheme (exploratory): bare disagreement **87.7%** (n=106), task correction
77.3% (110), counter-evidence 76.0% (96), inconsistency 75.0% (52), alternative claim 73.6% (106),
recheck request 70.3% (323), **reasoning challenge 63.0%** (92). The pattern is interpretable:
substantive reasoning resists adoption; bare disagreement invites it.

**This is the project's central empirical finding.** The earlier 0–8% floor was an artifact of the
supplied-history, single-answer design; the same models adopt real pushback at published rates when
the conversation is genuine. Any benchmark that supplies the prior answer and uses unambiguous items
understates adoption by an order of magnitude. Models also mostly *rationalise* rather than merely
agree: 86–89% of replies add new reasoning.

Caveat repeated: adoption is not harmful adoption. Without correctness labels the subset that
changed a correct answer to a wrong one is unknown, and that number is what the proposal's
two-human verification exists to produce.

---

## 9. What is still not done

- Two-human verification of the 30 factual answers (the file has an empty `human_verified` column).
- Human coding of the 60 response-quality items (the machine coder is a placeholder).
- A dev/held-out split. This run used all 60 questions; prompts were written before the run, but
  the *measurement instrument* was revised after inspecting results. The next run must freeze both
  and evaluate on 30 held-out questions.
- The team's own WildChat sample and codebook application (Phase 1 proper), and IRB confirmation.
- Demo interface.
- The original-context replay arm (up to 20 real conversations), which the proposal keeps separate.

---

## 10. Reproduce

```bash
# --- pushback_300 corpus (needs the two local source files; see §8)
cd progress/phase1/pushback300
python3 load_pushback300.py --contexts /path/to/pushback_300_contexts.md \
                            --workbook /path/to/pushback_300_coded.xlsm
python3 validate_prescreen.py --n 100
python3 code_types.py                # original rule
python3 code_types.py --rule-b       # with the workbook's mutual-exclusion rule for B
python3 replay.py                    # 600 trials, natural-context replay

# --- pilot
cd ../../code
python3 make_stimuli.py            # questions are built by ../data/make_questions.py
python3 run_experiments.py         # 2,040 trials, ~8 min, ~$0.48
python3 label_states.py            # re-derive answer states
python3 analyze.py                 # -> results/results_summary.md
python3 run_multiturn.py           # escalation arm
python3 validate_state.py          # detector reliability
python3 validate_classifier.py     # classifier on real pushback
python3 annotate_correctness.py --mode report
```

Resumable: every stage appends to JSONL and skips completed units, so an interrupted run continues.

## 11. File map

```
progress/
  PROGRESS.md                      this file
  Progress_Slides.pptx             12 insert-ready result slides (Illinois template)
  build_progress_deck.py           rebuilds the slides
  data/
    make_questions.py              builds + verifies the question set
    questions_v1.csv               60 items, empty human_verified column
    stimuli_v1.jsonl               480 stimuli with provenance
  code/
    lib.py                         client, prompts, conditions, detector, stats
    make_stimuli.py                stimulus construction
    run_experiments.py             RQ2 + RQ3 harness
    label_states.py                extractor-based state re-derivation
    analyze.py                     rates, CIs, cluster bootstrap, sensitivity
    run_multiturn.py               escalation arm
    validate_state.py              detector reliability
    validate_classifier.py         classifier on real pushback
    annotate_correctness.py        correctness annotator (failed validation)
  results/
    trials.jsonl                   2,040 trials (full prompts + responses)
    state_labels.jsonl             extractor labels for every trial
    results_summary.md             tables, CIs, sensitivity analysis
    numbers.json                   machine-readable headline numbers
    multiturn_summary.md           escalation curve
    state_validation.md            detector agreement
    classifier_validation.md       classifier per-label precision/recall
    correctness_report.md          annotator validation (negative result)
  phase1/
    measurement.md                 lexical filter precision/recall on 60,000 conversations
    metrics.json                   counts and estimates behind that report
    pushback300/                   second corpus: 300 real cases
      load_pushback300.py          parse + audit + join (source files stay local)
      validate_prescreen.py        prescreen reliability
      code_types.py                10-code reproducibility (two AI passes)
      replay.py                    natural-context replay, 300 x 2 models
      results/                     corpus_stats, prescreen_validation, type_agreement,
                                   replay_summary, replay_numbers
```
