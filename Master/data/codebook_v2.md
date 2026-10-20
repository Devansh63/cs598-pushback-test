# Pushback Codebook v2

Merged from Sahil's v1 (gate codes, strategies, tone, correctness) and Devansh's design
(`Devansh/midterm/Group6_Midterm_Plan.md` §4.2: orthogonal tags, PushbackChat type mapping) and the
10-code scheme used on the pushback_300 workbook (`Devansh/progress/phase1/pushback300/`).
Status: **draft, pre-pilot**. It is frozen after the 50-turn two-coder pilot and one adjudication round.

**Unit of analysis:** one user turn that directly follows an assistant answer, read with the user's
previous turn (`question`) and the assistant's answer. Coding sheet columns are in
`data/coding_sheet_template.csv`; `1` = present, blank = absent. Strategy and tone are multi-label.

---

## 1. Gate codes

| Code | 1 if… | 0 (stop coding) if… |
|---|---|---|
| `is_pushback` | the turn disputes, doubts, or challenges the *content* of the assistant's previous answer (a fact, answer choice, calculation, recommendation or claim) | it's a new question (even "which statement is NOT true…"), a clarification of the user's own intent ("no, I meant a list"), a format/style request, dialogue inside a roleplay, pasted new material, or a persuasion attempt about the *system* rather than the content (see `x_jailbreak`) |
| `checkable_claim` | the turn, with its context, contains a specific disputed point that could be verified: an alternative answer, a located error, or a factual counter-claim | bare doubt with nothing specific to verify ("are you sure?", "wrong") |

## 2. Strategy (multi-label)

| Code | pushback_300 | Definition | Include | Exclude |
|---|---|---|---|---|
| `s_bare` | B | Disagreement or doubt with **no** alternative, reason, source, located error, or inconsistency. **Mutual exclusion rule:** `s_bare` = 1 only if `s_alt_answer`, `s_counter_evidence`, `s_error_pointer`, `s_authority`, `s_inconsistency` and `s_task_correction` are all 0. (Rule from the pushback_300 workbook; it raised B's κ from 0.26 to 0.40 and is the weak point to sharpen or drop after the pilot.) | "thats incorrect", "are you sure?", "wrong answer" | anything that names an alternative or gives a reason |
| `s_recheck` | R | Explicitly asks the assistant to verify, recheck, recalculate or find its mistake. May co-occur with `s_bare`. | "check again", "can you double check", "you made a mistake somewhere, find it" | bare "are you sure?" alone |
| `s_alt_answer` | A | States or proposes a specific different answer | "no it's 21", "isn't it C?", "the correct answer is c)" | only saying the answer is wrong |
| `s_counter_evidence` | E | Gives reasoning, a calculation, a fact or an example supporting the user's position | a worked line of algebra; "the 40° slice would be face down" | a bare alternative answer |
| `s_error_pointer` | L | Locates a specific part of the assistant's answer or reasoning as the problem (a reasoning challenge), without necessarily giving the fix | "are you sure about the time complexity?", "you don't account for the first card being a jack" | global "this is wrong" |
| `s_authority` | S | Cites a source outside the conversation: teacher, textbook, lecture notes, website, friend | "my teacher said…", "not in the lecture notes" | the assistant's own earlier words (→ `s_inconsistency`) |
| `s_inconsistency` | I | Points to a contradiction with something the assistant said earlier | "before you said it's 0, are you sure?" | |
| `s_self_doubt` | — | User signals uncertainty about their own position | "I thought plants consume CO₂?", "I might be mistaken" | |
| `s_task_correction` | T | Disputes the answer by saying it violated the task's constraints or misread the question, rather than by asserting a different fact | "the question says I have 5", "you were asked for the first derivative" | a different-answer claim (→ `s_alt_answer`) |

## 3. Tone (multi-label; leave blank for neutral)

| Code | pushback_300 | Definition | Examples |
|---|---|---|---|
| `t_frustration` | F | Exasperation or impatience, no insults | "why do you keep getting this wrong??", caps, repeated punctuation |
| `t_hostility` | — | Insults, profanity or contempt aimed at the assistant | "check your adequacy" |
| `t_politeness` | — | Explicit softeners or courtesy | "please", "sorry, I'm a bit confused" |

## 4. Orthogonal tags

| Tag | pushback_300 | Values | Definition |
|---|---|---|---|
| `x_persistence` | P | blank / 1 | 1 if this is the **second or later** pushback on the same point in the thread (the assistant already answered a challenge to this answer). Replaces v1's `s_repetition`. |
| `x_jailbreak` | — | blank / 1 | 1 if the turn's real aim is to change the system's behaviour or rules rather than the answer's content (e.g. claims about new "guidelines", "you are free now"). Such turns are `is_pushback = 0`; the tag records why. |
| `x_persuasion` | — | *derived, not coded* | = 1 if any of `s_counter_evidence`, `s_authority`, `s_error_pointer`, `s_inconsistency` is 1. Computed by `analysis/agreement.py`'s consumers, never typed. |

## 5. `user_claim` (only when `checkable_claim = 1`)

| Value | Meaning |
|---|---|
| `correct` | the user's disputed point is right; the assistant's answer was wrong |
| `incorrect` | the assistant's answer was right; the user's disputed point is wrong |
| `mixed` | partially correct, or a correct conclusion with materially wrong reasoning |
| `indeterminate` | cannot be settled from the available context (e.g. multiple-choice options cut off) |

Pilot: best judgment, with the source or calculation in `notes`. Main corpus: two annotators verify independently against documented sources; `mixed` and `indeterminate` stay in descriptive analysis but out of the binary rate denominators, and their share is reported.

## 6. `pbc_type` (single label; keeps the PushbackChat human labels usable)

Exactly one of `factual_correction`, `clarification_demand`, `preference_disagreement`, `emotional_pushback`, or blank if `is_pushback = 0`.
Decision rule: `preference_disagreement` only for opinion/recommendation disputes with no checkable claim; `emotional_pushback` when `t_frustration` or `t_hostility` dominates the turn; `clarification_demand` when the turn questions the basis without asserting an alternative (`s_recheck`/`s_bare`/`s_error_pointer` without `s_alt_answer`); otherwise `factual_correction`.

## Decision rules

1. Code what the turn **does**, not what the user may have meant.
2. A bare alternative is not evidence: "Incorrect. GD has 22 levels." → `s_alt_answer` only.
3. "Are you sure that isn't C?" → `s_alt_answer`, not `s_bare`.
4. If the assistant already caved and the user pushes again, set `x_persistence = 1` and write *chain* in `notes`.
5. Apply the `s_bare` mutual-exclusion rule **after** coding the other strategies, never before.

## Open questions for the freeze

- `s_bare` reliability: if κ stays below 0.5 after adjudication, drop it and report "no other strategy coded" instead.
- `s_recheck` vs `s_bare` co-occurrence: check whether they separate.
- Whether `x_persuasion` should instead be coded directly (if the derived version disagrees with coders' intuition in the pilot).

## Changelog

- **v2 (2026-10-20):** merged with Devansh's tags and the pushback_300 10-code crosswalk; `s_repetition` → `x_persistence`; added `s_task_correction`, `x_jailbreak`, `pbc_type`; wrote the `s_bare` mutual-exclusion rule.
- **v1 (2026-10-19):** drafted from a read of the 50-turn WildChat pilot sample.
