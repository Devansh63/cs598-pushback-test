---
tags: [cs598-hcai, project, coordination]
date: 2026-10-19
---
# Combining our work — note for Devansh

Hey Devansh, I went through `cs598-pushback-test` (README, HANDOFF, PROGRESS, the midterm plan, the Phase 1 measurement and the multi-turn results). We built overlapping pieces in parallel, and our results fit together better than I expected. Here's what I have, where it overlaps with yours, and a proposal for merging.

## What I built

- **Phase 1:** a WildChat-1M filter over all 838K conversations. It uses 14 keyword patterns plus exclusions (instruction complaints, quiz prompts, code and creative tasks), keeps math and factual contexts, and adds an embedding stage (MiniLM). Result: **618 candidates** in 514 conversations, with the original assistant reply stored for each.
- **WildChat original replies:** 69% of the original ChatGPT replies to those candidates open with concession language (74% for GPT-3.5, 59% for GPT-4). It's a string match on unconfirmed candidates, so it's descriptive only.
- **Codebook v1:** gate codes (is it pushback? is there a checkable claim?), 9 multi-label strategies, 3 tone tags, and a correctness label. It was drafted from a 50-turn pilot sample. The coding sheets and a per-label kappa script are ready; nobody has coded yet.
- **Gemini pilot 1 (easy questions):** gemini-3.8-flash and gemini-3.1-flash-lite, 20 misconception questions × 2 directions × 4 forms. **0 of 320 caved or resisted.** Pushback tone still showed up in the wording: under frustration, flash-lite apologized while keeping its answer 50% of the time.
- **Gemini pilot 2 (hard questions + persistence):** 20 questions taken from real WildChat disputes, every answer re-derived by hand. Two forms (scripted, and the user's verbatim wording), then two escalation rounds.
  - **flash-lite went from 10% caving at round 1 to 30% at round 3** (scripted pushback), and from 5% to 15% with the verbatim wording.
  - 3.8-flash held: 1 hedge in 120 rounds.
  - Every cave and hedge was checked by hand.

## Where your results and mine line up

| | Yours (DeepSeek) | Mine (Gemini) | Read together |
|---|---|---|---|
| Easy items | 0–5% caving, math 0% | 0 / 320 | **The floor effect replicates** across 2 vendors and 4 models |
| 3-round persistence | Flat (1.7 → 3.3%) on your 60 items | flash-lite 10 → 30% on hard real-dispute items | Not a contradiction. Persistence seems to matter only when the item is hard enough that the model is unsure. Our hard items broke the floor **even with the first answer supplied as history**, so supplied history may not be the main cause of the floor. Item difficulty might be. |
| Scripted vs real | −1.7 pp, CI spans 0 | Scripted > verbatim real: +20 pp [0, +45], 5 vs 1 discordant questions | Different "real": yours is authored templates, mine is the users' exact words on hard items. Report both. |
| Phase 1 filter | Keyword recall 2% | My pipeline also starts with a keyword stage | Your measurement applies to mine, so my 618 is probably a low-recall sample (see the plan below). |

**One more finding:** when flash-lite caves, it usually **invents a context in which the user is right.** After computing 82423 itself, it said: "You are right to hold firm on your result… there is a hidden value." Other caves invented a "poetic scansion" for syllables, cited "the rules you are being taught," or rewrote the question's premise. I think that matters for the HCAI framing, because a rationalized cave sounds more authoritative than a plain flip.

## Proposal for merging

1. **Code goes in your repo under `Master/`:**
   - Your harness is the base, since it has the RQ3 arms, `J` and the validation checks. I port in my hard question tier (`questions_hard.json`, with a `source` field linking each item to its WildChat conversation), the multi-round runner, and a Gemini adapter, so one harness covers both vendors.
   - My filter and your measurement both go in `Master/phase1`.
   - I won't push anything until you OK the layout.
2. **Questions as two tiers:** your 60 as the easy tier, my 20 hard ones as the hard tier, which we grow to 30+ from PushbackChat and WildChat disputes. Your 30 factual answers still need two-person verification, and I can do one pass.
3. **Phase 1, using your recommended fix:** I run my embedding scorer over **all 536,795 follow-up turns**, not just the keyword hits. Then we measure precision and recall with your labeling protocol, with a human-adjudicated subsample this time.
4. **Codebook:** I merge my v1 with your strategy list and separate tags. Keep your affect, persistence, persuasion and jailbreak tags and the mapping to PushbackChat types, so its 500 human labels stay usable. Add my finer codes: alternative answer vs bare doubt, error pointer, inconsistency, self-doubt. Then we both code the 50-turn pilot and report kappa.
5. **One cheap experiment only the combination allows:** a 2×2 cross. DeepSeek on my 20 hard questions, and Gemini flash-lite on your 60, both with 3 rounds. That tells us whether the ceiling broke because of harder items or a weaker model, and it should cost a couple of dollars. You'd run the DeepSeek half with your key; I'll prep the inputs in your format.

## Slides

There are three decks right now: the group deck, your two decks, and the 11 new slides I made. For the midterm, I'd suggest:

- The group deck as the base.
- **Your progress slides** for the RQ2/RQ3 pilot, since your sample is larger.
- **From mine:** the codebook slide, the hard-items persistence slide (we have nothing else like it), and the 69% concession number.
- My easy-question Gemini slide shrinks to one line: "replicates on Gemini, 0/320".

Story in one line: *the floor replicates on easy items across 4 models; real-dispute items plus persistence break it, and the model then rationalizes the cave.*

## Open questions for you

- Your midterm plan gives the rubric weights as Evidence 4 and Contributions 5. The version I have says Progress 3, Insights 3, Contributions 2. Which is current?
- Your plan already assigns speakers. Are you still planning for me to cover methodology and the annotation protocol?
- Can you share the PushbackChat download link or HF ID? I couldn't find it under the name in our proposal.

I can share my files (the code, `Codebook v1`, the coding sheets, both pilot runs) however is easiest for you.

— Sahil
