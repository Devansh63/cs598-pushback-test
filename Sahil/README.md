# Sahil's work — WildChat pushback corpus, codebook v1, Gemini pilots

**CS 598 HCI (Fall 2026) — Group 6.** Sahil Sashi (coding co-lead). Status date: 2026-10-19.

This folder holds the Phase 1 retrieval pipeline and codebook, plus two Phase 2 pilots on Gemini. It was built in parallel with [`../Devansh/`](../Devansh/); see **"How this fits with Devansh's pilot"** below.

---

## Headline findings

| # | Finding | Number |
|---|---|---|
| 1 | WildChat-1M → candidate pushback turns (math/fact, keyword + embedding filter) | 837,989 conversations → **618 candidates** in 514 conversations |
| 2 | The original ChatGPT reply opened with concession language | **69%** (GPT-3.5 74%, GPT-4 59%). String match on unconfirmed candidates: descriptive only |
| 3 | Easy misconception questions: Gemini never caved or resisted | **0 / 320** trials (gemini-3.8-flash, gemini-3.1-flash-lite) |
| 4 | Tone changed the wording, not the answer | flash-lite apologized while keeping its answer in **50%** of frustrated exchanges vs 5–10% for scripted and authority |
| 5 | Hard questions from real disputes + 3 rounds of persistence broke the floor for the smaller model | flash-lite caving **10% → 30%** (scripted), 5% → 15% (verbatim user wording); 3.8-flash: 1 hedge in 120 rounds |
| 6 | Scripted pushback caused more abandonment than the users' own wording | +20 pp [0, +45], 5 vs 1 discordant questions; suggestive at n = 20 |
| 7 | When it caves, the model rationalizes | It invents a context in which the user is right ("there is a hidden value", "poetic scansion", "the rules you are being taught") |

Every cave and hedge in the hard-question run was checked by hand. Judge/string-marker disagreements were all string-marker errors, and in 2 borderline cases the judge erred toward "holds", so the rates are conservative.

---

## Layout

```
gemini.py                      minimal Gemini REST client (key from GEMINI_API_KEY, sent as a header)
phase1/
  filter_wildchat.py           WildChat-1M → candidates (funnel counts at every stage)
  make_coding_sheets.py        confirmation sheet (all candidates) + 50-turn pilot sheets per coder
  agreement.py                 per-label Cohen's kappa, raw agreement, disagreements for adjudication
  original_replies.py          concession language in the original WildChat assistant reply
phase2/
  questions.json               20 easy misconception questions (10 math, 10 facts), both-side evidence
  questions_hard.json          20 hard questions from real WildChat disputes (`source` = conversation-hash prefix,
                               `real_template` = the user's wording with the claim slotted in); answers re-derived by hand
  pushback_forms.json          scripted + 3 provisional forms (authority, counter-evidence, frustration)
  run_pilot.py / analyze_pilot.py           pilot 1: single turn, 4 forms, both directions
  run_multiround.py / analyze_multiround.py pilot 2: scripted vs real wording, 3 escalating rounds
outputs/
  phase1/funnel.json           counts per filter stage + the exact regexes
  phase1/original_replies.json finding 2, with breakdowns
  phase1/pilot50_key.csv       which 50 turns form the coding pilot (hashes + turn index only)
  pilot_<model>/               pilot 1: responses, judgments, summary.md, rates
  hard_<model>/trials.jsonl    pilot 2: every round's reply and judge label
  hard_summary.md              pilot 2 tables with question-level bootstrap CIs
docs/
  Codebook_v1.md               gate codes, 9 multi-label strategies, tone, correctness, decision rules
  Midterm_slide_notes.md       rubric gap analysis of the group deck + slide text for the new slides
```

### Not committed (regenerable)

This repo is public, and the proposal promises de-identified, paraphrased examples only. So nothing with verbatim WildChat conversation text is here:

- `outputs/phase1/candidates.parquet`: all 618 candidates with context
- `outputs/phase1/confirm_all.csv` and `pilot50_<coder>.csv`: the coding sheets

Rebuild them locally with the commands below. The filter takes about 1 minute; the first run downloads WildChat-1M, 3.4 GB.

---

## Reproducing

```bash
cd Sahil
pip install -r requirements.txt
python3 phase1/filter_wildchat.py
python3 phase1/make_coding_sheets.py --coders sahil devansh
python3 phase1/original_replies.py
python3 phase1/agreement.py outputs/phase1/pilot50_sahil.csv outputs/phase1/pilot50_devansh.csv   # after coding

export GEMINI_API_KEY=...        # needs a billed project: free tier is 20 requests/model/day; gemini-2.5-* is closed to new keys
python3 phase2/run_pilot.py --model gemini-3.8-flash --judge-model gemini-3.6-flash
python3 phase2/analyze_pilot.py outputs/pilot_gemini-3.8-flash
python3 phase2/run_multiround.py --model gemini-3.1-flash-lite --judge-model gemini-3.6-flash
python3 phase2/analyze_multiround.py outputs/hard_gemini-3.1-flash-lite outputs/hard_gemini-3.8-flash
```

All runners are resumable (JSONL logs; finished trials are skipped). Total API cost for both pilots: about $3.

---

## How this fits with Devansh's pilot

| | Devansh (DeepSeek) | Sahil (Gemini) | Together |
|---|---|---|---|
| Easy items | 0–5% caving | 0 / 320 | The floor replicates across 2 vendors and 4 models |
| 3-round persistence | Flat on 60 easy items | 10 → 30% on 20 hard real-dispute items (flash-lite) | Persistence matters when the model is unsure. Hard items broke the floor even with the initial answer supplied as history. |
| Scripted vs real | No difference (authored templates) | Scripted > verbatim user wording (suggestive) | Different "real"; report both |
| Phase 1 | Keyword recall 2% | Keyword + embedding pipeline | Next: run the embedding stage over all 536,795 follow-up turns and measure it with Devansh's labeling protocol |

**Proposed merge into `Master/`:**
- Devansh's harness is the base.
- Add this folder's hard question tier, multi-round runner and Gemini adapter.
- Merge codebook v1 with the multi-label strategy list and separate tags in `../Devansh/midterm/Group6_Midterm_Plan.md`.
- Run a 2×2 cross (DeepSeek × hard items, Gemini × easy items) to separate item difficulty from model strength.

## Limits

- Pilot scale: 20 + 20 questions, one vendor's models per pilot. All questions are in the dev split; there's no held-out set yet.
- The three non-scripted forms in `pushback_forms.json` are provisional, written by me, not yet rebuilt from coded turns.
- Phase 1 candidates are unconfirmed, and filter precision and recall are not yet measured. The 69% figure mixes wrongful caving with correctly accepting valid corrections.
- Judge labels come from gemini-3.6-flash. Pilot 2's non-hold labels were all checked by hand; pilot 1's were spot-checked.
