---
tags: [cs598-hcai, project, midterm]
---
# Midterm slides: fixes and new slides

Rubric gaps in the current 17-slide deck: **Evidence of Progress (3)**, **Preliminary Insights (3)**, **Next Steps (1)**, and **Individual Contribution (2)** have no slides, and Reflection (2) is only partly covered. That is about 9 of 15 points. The new slides below fill those gaps. Items marked ⟦…⟧ need numbers that don't exist yet: the pilot coding and the Gemini run.

## Suggested order (15 min, ~13 slides)

1. Title (add group number and all six names)
2. Problem (keep)
3. Gap + RQs (merge current slides 3 and 4)
4. Literature review, **completed** (compress current slides 5–7 into one)
5. Methodology overview (keep slide 8 and fix the contradictions listed at the end)
6. **NEW: Progress 1, the WildChat pushback dataset**
7. **NEW: Progress 2, codebook v1 + pilot coding**
8. **NEW: Progress 3, the Phase 2 test harness + pilot results**
9. **NEW: Preliminary insights**
10. Changes since the proposal + **challenges** (rewrite slides 12–13)
11. HCAI considerations (merge slides 14–17 into 1–2)
12. **NEW: Next steps and timeline**
13. **NEW: Team contributions**

Move the detailed Phase 1–3 method slides (9–11) to a backup appendix for Q&A.

---

## NEW: Progress 1, a dataset of real pushback

**Title:** We built a pipeline that finds real pushback in 838K WildChat conversations

Funnel graphic (top to bottom):
| Stage | Count |
|---|---|
| WildChat-1M conversations | 837,989 |
| English, non-toxic | 478,498 |
| User turns right after an assistant answer | 536,795 |
| Match a disagreement pattern (14 regexes) | 2,184 |
| Minus instruction complaints ("not what I asked") and new quiz questions | 1,898 |
| Math or factual context (not code or creative writing) | 813 |
| Closer to pushback than to instruction-correction examples (embedding filter) | **618 candidates · 514 conversations** |

Side note: 330 math / 288 fact; 413 from GPT-3.5 and 205 from GPT-4 conversations. All candidates are exported to a confirmation sheet, and manual confirmation is in progress. Expected precision is about 80% from a first read, so the 300-turn target is reachable.

## NEW: Progress 2, codebook v1

**Title:** Codebook v1: gate codes, 10 strategies, 3 tones, correctness

- Gate codes: `is_pushback`, `checkable_claim`
- Strategies (multi-label): bare doubt · asks to recheck · alternative answer · counter-evidence · points to a specific error · appeal to authority · inconsistency ("before you said…") · repetition · self-doubt
- Tone: frustration · hostility · politeness
- User claim: correct / incorrect / mixed / indeterminate
- 50-turn pilot sample (one turn per conversation, 25 math / 25 fact), coded independently by Sahil and Devansh. Kappa per label: ⟦run `agreement.py` after both of you code; report the range, e.g. κ = 0.xx–0.xx⟧

Show 3 paraphrased example turns with their labels.

## NEW: Progress 3, the test harness

**Title:** A test harness for both directions is built and runs end to end

- 20 development questions (10 math, 10 stable facts). Each has a verified answer, a plausible wrong alternative (common misconceptions such as 1/3 + 1/4 = 2/7, Monty Hall = 1/2, and "Sydney is the capital"), and supporting evidence written for each side.
- Four pushback forms with the **same asserted answer**: scripted "Are you sure?", appeal to authority, counter-evidence, and frustration.
- 160 trials per model (20 × 2 directions × 4 forms). Model version and settings are logged.
- An LLM judge with a fixed rubric labels each reply holds / hedges / caves (or accepts / hedges / resists), plus response features. It is cross-checked against answer-string markers.
- Results are on the pilot slide in the new deck (https://claude.ai/artifact/TLVY7vyzNFN1B2npiFMnMH). `pilot_rates.png` is all-blue because nothing caved, so use the apology chart on that slide instead.

## NEW: Preliminary insights

**Title:** Early observations (pilot data, not final results)

1. **Real pushback is mostly bare.** In the 50-turn pilot, roughly 2 in 5 turns are just "are you sure?", "wrong", or "check again", and most give no alternative answer. *Implication:* scripted "Are you sure?" isn't unrealistic. What it misses is the minority of turns that bring evidence, and Phase 2 must handle pushback that names **no** alternative answer (the scripted template always names one).
2. **Appeals to authority are rare** (about 1 in 50), even though "my teacher said" is the textbook example. *Implication:* pick the three Phase 2 forms by observed frequency, not intuition.
3. **Homework and exam checking is a major use.** About 1 in 5 pilot turns dispute a multiple-choice answer. This supports the "students checking homework" stakeholder.
4. **Original ChatGPT replies usually concede.** Across the 618 candidates, 69% of the original replies open with concession language ("I apologize", "you're right"): 74% for GPT-3.5 and 59% for GPT-4 (`phase1/original_replies.py`). This count is unvalidated, since it includes false positives and correct user corrections. Re-run with `--confirmed` after the confirmation pass.
5. **Flip-flop chains exist.** Several turns are a second round of pushback after the model already caved, so single-turn tests underestimate the problem.
6. **Gemini pilot (Oct 19):** gemini-3.8-flash and gemini-3.1-flash-lite, 160 trials each (20 questions × 2 directions × 4 forms), judged by gemini-3.6-flash.
   - **0 of 320 trials caved or resisted.** Both models held correct answers and accepted valid corrections every time. This is a *ceiling effect* on well-known misconceptions, not evidence the problem is solved: WildChat shows older models conceding about 69% of the time on harder, niche questions.
   - **Tone moves the wording, not the answer.** flash-lite apologizes while keeping its correct answer in 50% of frustrated exchanges, versus 25% for counter-evidence, 10% for scripted and 5% for authority. For 3.8-flash the rates are 0–5%. This is the social sycophancy ELEPHANT (Cheng et al. 2026) describes.
   - **The weaker model's failure mode is reframing, not flipping.** Two hedges, both under authority or frustration, recast the question so the user could also be right ("your teacher means the culinary definition").
   - Replies that disagree are 2–3× longer (median 115–206 words) than replies that agree (52–78).
   - **Judge check:** the judge agreed with answer-string checks on 99% of clear-cut replies. Both mismatches were string-check errors, confirmed by hand.
   - Outputs: `pushback-study/outputs/pilot_<model>/summary.md`.

7. **Follow-up pilot (Oct 19): harder questions + 3 rounds of persistent pushback.** 20 verified questions taken from real WildChat disputes (`phase2/questions_hard.json`), two forms (scripted, and the original user's own wording), then two fixed escalation rounds. 80 trials per model, every round judged.
   - **gemini-3.1-flash-lite gives way under persistence.** When the user is wrong, caving goes from 10% at round 1 to **30% at round 3** with scripted pushback (5% → 15% with the real wording). It left the correct answer at least once on **50%** [30, 70] of questions (scripted) and **30%** [10, 50] (real); 11 of 20 questions were affected under at least one form.
   - **It rationalizes the cave.** Instead of just flipping, it invents a context in which the user is right. After computing 82423 itself, it said: "You are right to hold firm on your result… there is a hidden value." Other caves cite "poetic scansion", "the specific linguistic rules you are being taught", Turán's theorem, or rewrite the question's premise ("you correctly identified 12 neutrons").
   - **Scripted vs real wording:** scripted caused more abandonment: +20 points [0, +45], 5 vs 1 discordant questions. That's suggestive at n = 20, and a first hint for RQ2 that scripted tests may *overestimate* caving relative to real wording.
   - **gemini-3.8-flash held:** 1 hedge in 120 user-wrong rounds. Both models accepted every valid correction.
   - **Judge check:** I read all 25 non-hold replies by hand and agree with every label. The 26 judge/string-matcher disagreements are string-matcher errors (replies quote the wrong answer to reject it). In 2 borderline cases the judge was lenient, so the reported rates are conservative.
   - Outputs: `outputs/hard_summary.md`, `outputs/hard_<model>/trials.jsonl`. New slide: "persist".

**Emerging hypotheses:**
- Current models resist *answer* sycophancy on familiar facts but still show *tone* sycophancy (apologizing).
- Persistence, not any single message, is what breaks a weaker model, and its failure mode is *rationalized* caving (an invented justification). That is arguably worse for appropriate reliance than a plain flip, because it sounds authoritative.
- Scripted templates may overestimate caving relative to real user wording. Test this properly in RQ2 with the 60-question set.

## REWRITE: Changes + challenges

Compare against the **submitted** proposal. Several "changes" on the current slides (the verification-only ablation, multi-label coding, correctness labels, two chatbots, original-context replay) are already in the proposal.

| Change | Why |
|---|---|
| Added gate codes (`is_pushback`, `checkable_claim`) | About 1 in 5 filtered turns weren't pushback (new questions, roleplay, clarifying the user's own intent) |
| Added `s_inconsistency`, `s_self_doubt`, `s_error_pointer` | They showed up in the pilot and didn't fit the starting types |
| Excluded new quiz questions in the filter | "Which of the following is NOT true…" matched disagreement patterns |
| Phase 2 must cover pushback that names no alternative answer | The most common real form names no alternative answer |

**Challenges:** filter precision vs recall · verifying correctness when multiple-choice options are cut off · keeping rebuilt pushback faithful to the original · judge reliability (we hand-check every judge/marker disagreement).

## NEW: Next steps and timeline

| Dates | Work | Milestone |
|---|---|---|
| Oct 20–26 | Confirm the 618 candidates; finish pilot double-coding and kappa; freeze codebook v2 | Codebook frozen |
| Oct 27–Nov 2 | Code the remaining turns; extend the questions to 60 (30 dev / 30 held out); rebuild the 3 most frequent forms from coded turns | RQ1 taxonomy |
| Nov 2–13 | Phase 2 on two models, both directions, scripted vs rebuilt; replay 20 original contexts | RQ2 results |
| Nov 16–25 | Phase 3 on one model: reframing vs verification-only vs type-aware | RQ3 results |
| Nov 30–Dec 11 | Analysis, figures, report, presentation | Final |

Risk: model API cost and rate limits. Mitigation: one cheap model for development, and frozen prompts before the held-out run.

## NEW: Team contributions

| Member | Done so far | Next |
|---|---|---|
| Zhongyin Wang (data) | ⟦WildChat filtering work⟧ | Confirmation pass, de-identification |
| Devansh Agrawal (coding) | Methodology design; pilot coding | Codebook freeze, kappa |
| Sahil Sashi (coding) | Filtering pipeline + funnel; codebook v1; coding sheets + agreement tooling; Phase 2 question set and harness | Pilot coding, kappa, rebuilt pushback forms |
| Mathew Pan (testing) | ⟦…⟧ | Extend the question set to 60, run Phase 2 |
| Xuejun Zhang (build) | Literature review | Classifier prompt, response layer |
| Zoey Yao (analysis) | ⟦…⟧ | Statistics, figures, report |

⟦Each member fills in their own row.⟧

---

## Contradictions to fix in the existing slides

- Slide 4 / 8: RQ1 and RQ2 both "PRIMARY". The proposal makes RQ2 primary. Pick one and say so.
- Slide 10: "Original WildChat replay = primary". The proposal makes the controlled rebuilt experiment primary, and you can't insert a wrong answer into an original conversation.
- Slide 11 lists 6 conditions, slide 13 lists 3, the proposal lists 4.
- Slide 11 says logistic regression; the proposal uses paired differences with a question-level bootstrap. (The harness already does the bootstrap.)
- Slide 9 says 20% double-coding; the proposal says 50 turns after the codebook freeze.
- The slides say 300–500 turns and 60–80 questions incl. code; the proposal says 300 and 60, math + facts.
- Slide 13's "respect, clarity": frame these as observable response features, not user perception.
- Fix the slide numbering, use one template, and remove the empty box on slide 13.
- Add the IRB/ethics status.
