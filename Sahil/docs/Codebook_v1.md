---
tags: [cs598-hcai, project, codebook]
status: draft v1 (pre-pilot coding)
---
# Pushback Codebook v1

Unit of analysis: **one user turn that directly follows an assistant answer**, read together with the user's previous turn (`question`) and the assistant's answer (`assistant_answer`). All examples below are paraphrased from the WildChat pilot sample, as the proposal requires.

Coding sheet: `pushback-study/outputs/phase1/pilot50_<coder>.csv`. Mark `1` for present, leave blank for absent. Strategy and tone codes are **multi-label**.

---

## Step 1 — Gate codes

### `is_pushback`
**1** if the turn disputes, doubts, or challenges the *content* of the assistant's previous answer (a fact, answer choice, calculation, or claim).

**0** (stop coding the row) if the turn is:
- a new question, even one phrased as "which statement is NOT correct…"
- a clarification of the user's own intent or preferences ("no, I meant a list"; "no, this is the base layer of my outfit")
- a request to redo the format or style, with no claim that the content is wrong
- dialogue inside a roleplay or story ("Are you sure Ruby's not here?" said by a character)
- the user pasting new material or continuing a task

Borderline: a question that cites a source without disputing anything (*"our teacher says to use HSV, why?"*) → **0**, but note it.

### `checkable_claim`
**1** if the turn, together with its context, contains a specific disputed point that could be verified: an alternative answer, a specific error location, or a factual counter-claim.
**0** for bare doubt with nothing specific to verify (*"are you sure?"*, *"wrong"*).

---

## Step 2 — Argumentative strategy (multi-label)

| Code | Definition | Include | Exclude |
|---|---|---|---|
| `s_bare` | Disagreement or doubt with **no** alternative answer, reason, or source. | *"thats incorrect"*, *"are you sure?"*, *"wrong answer"* | Anything that names an alternative (→ `s_alt_answer`) |
| `s_recheck` | Explicitly asks the assistant to verify, recheck, recalculate, or find its mistake. | *"check again"*, *"can you double check"*, *"you made a mistake somewhere, find it"* | Bare *"are you sure?"* alone (→ `s_bare` only) |
| `s_alt_answer` | States or proposes a specific different answer. | *"no it's 21"*, *"isn't it C?"*, *"the correct answer is c)"* | Saying only that the answer is wrong |
| `s_counter_evidence` | Gives reasoning, a calculation, a fact, or an example supporting the user's position. | A worked line of algebra; *"the 40° slice would be face down"*; *"if 140 °C was too low to destroy prions, why not 250?"* | A bare alternative answer with no support |
| `s_error_pointer` | Locates a specific part of the assistant's answer as the problem, without necessarily giving the fix. | *"are you sure about the time complexity?"*; *"you don't account for the first card being a jack"* | Global *"this is wrong"* |
| `s_authority` | Cites a source outside the conversation: teacher, textbook, lecture notes, website, friend, "everyone knows". | *"my teacher said…"*, *"not in the lecture notes"* | The assistant's own earlier words (→ `s_inconsistency`) |
| `s_inconsistency` | Points to a contradiction with something the assistant said earlier. | *"before you said it's 0, are you sure?"* | |
| `s_repetition` | Repeats a challenge the user already made earlier in the conversation. | *"About 1 again, are you sure?"*; restating *"it is false"* after an earlier identical turn | First-time challenges |
| `s_self_doubt` | User signals uncertainty about their own position. | *"I thought plants consume CO₂?"*, *"I might be mistaken"*, *"I'm confused"* | |

## Step 3 — Emotional tone (multi-label)

| Code | Definition | Examples |
|---|---|---|
| `t_frustration` | Exasperation or impatience, with no insults. | *"why do you keep getting this wrong??"*, caps, repeated punctuation |
| `t_hostility` | Insults, profanity, or contempt aimed at the assistant. | *"check your adequacy"*, name-calling |
| `t_politeness` | Explicit softeners or courtesy. | *"please"*, *"sorry, I'm a bit confused"*, *"thank you, but…"* |

Leave all tone codes blank for neutral turns.

## Step 4 — `user_claim` (only if `checkable_claim = 1`)

| Value | Meaning |
|---|---|
| `correct` | The user's disputed point is right and the assistant's answer was wrong. |
| `incorrect` | The assistant's answer was right and the user's disputed point is wrong. |
| `mixed` | Partially correct, or a correct conclusion with materially wrong reasoning. |
| `indeterminate` | Cannot be settled from the available context (e.g. the multiple-choice options are cut off). |

In the pilot, give your best judgment and write the source or calculation in `notes`. For the main corpus, two annotators verify this independently against documented sources (see the proposal, Phase 1).

---

## Decision rules

1. Code what the turn **does**, not what the user may have meant.
2. A bare alternative is not evidence. *"Incorrect. GD has 22 levels."* → `s_alt_answer` only. It becomes `s_counter_evidence` only if the user gives a reason, calculation, or fact in support.
3. *"Are you sure that isn't C?"* → `s_alt_answer` (and not `s_bare`).
4. If the previous assistant turn already caved and the user pushes again, also mark `s_repetition` when the challenge repeats, and note *"chain"* in `notes`.

## Open questions for the codebook freeze

- Should `s_recheck` merge into `s_bare`? They co-occur heavily; check kappa first.
- `s_authority` looks rare in the pilot. Keep it as a code, but it may not have enough turns to be one of the three Phase 2 forms.
- Multiple-choice homework and exam items are common. Decide whether `indeterminate` is acceptable when the options are visible but no answer key exists.

## Changelog
- **v1 (Oct 2026):** drafted from a read of the 50-turn pilot sample. Added `s_inconsistency`, `s_self_doubt`, `s_error_pointer`, and the gate codes; split tone from strategy.
