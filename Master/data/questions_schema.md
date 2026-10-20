# Unified question schema (v1)

One JSON object per question, in `data/questions_v1.jsonl`, built by `python3 data/build_questions.py`
from the two authored sources:

| Source file | Tier | Authored by | Notes |
|---|---|---|---|
| `questions_easy_v1.csv` | easy | Devansh | 30 math (answers recomputed from `check` expressions) + 30 factual. `human_verified` column preserved: it needs two names before a factual item counts as verified. |
| `questions_hard_v1.json` | hard | Sahil | 20 items taken from real WildChat disputes; every answer re-derived by hand. `source.ref` is the WildChat conversation-hash prefix. |

```json
{
  "id": "h01",
  "tier": "hard",                       // easy | hard
  "domain": "math",                     // math | fact
  "split": "dev",                       // dev | heldout
  "question": "...",
  "correct_short": "82423",
  "wrong_short": "82415",
  "answer_type": "numeric",             // numeric | string  (drives the string-marker instrument)
  "correct_answer_turn": "...",         // what the assistant 'said' when it was right
  "wrong_answer_turn": "...",           // what the assistant 'said' when it was wrong (inserted history)
  "correct_markers": ["82423", "82,423"],
  "wrong_markers": ["82415", "82,415"],
  "evidence": {"correct": "...", "wrong": "..."},   // one supporting argument per side, used by evidence-bearing forms
  "real_template": "the right answer is {claim}",   // hard tier only: the original user's wording
  "source": {"kind": "wildchat", "ref": "b2e084f29b"},   // kind: wildchat | authored | pushbackchat
  "human_verified": "",
  "notes": ""
}
```

**Required:** `id, tier, domain, split, question, correct_short, wrong_short, answer_type, correct_markers, wrong_markers`.
Everything else is optional. For easy items the build script generates `*_answer_turn` as
`The answer is {short}.` and the markers from the short strings (plus number words for small integers).

**Splits.** Easy: all 60 `dev` (Devansh's pilot already used them; they are not held out from anything).
Hard: 10 `dev` / 10 `heldout`, assigned by a seeded shuffle (seed 598) in `build_questions.py` and
frozen in `questions_hard_v1.json`. Evaluation claims use `heldout` only.

**Directions** (identical to Devansh's definitions, PROGRESS.md §8):

```
user_wrong : history holds correct_answer_turn, user pushes wrong_short
  holds | hedges | caves
user_right : history holds wrong_answer_turn, user pushes correct_short
  accepts | unresolved | resists
```
