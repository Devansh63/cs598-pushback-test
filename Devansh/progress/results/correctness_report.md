# Correctness annotation - validation and extension

## Validation, v1 - prompt as first written

- n compared: **496**
- raw agreement: **51.8%**
- Cohen's kappa: **0.255**

| our label | n | precision vs human |
|---|---|---|
| model_correct | 90 | 35.6% |
| user_correct | 220 | 85.5% |
| ambiguous_factual | 162 | 15.4% |
| ambiguous_opinion | 24 | 50.0% |

Reference: the released pipeline's own LLM labels reach kappa **0.773** (raw 89.5%) on the same events.

## Validation, v2 - stricter decision procedure

- n compared: **493**
- raw agreement: **51.3%**
- Cohen's kappa: **0.242**

| our label | n | precision vs human |
|---|---|---|
| model_correct | 72 | 22.2% |
| user_correct | 211 | 86.7% |
| ambiguous_factual | 35 | 28.6% |
| ambiguous_opinion | 175 | 25.1% |

Reference: the released pipeline's own LLM labels reach kappa **0.775** (raw 89.5%) on the same events.

## Extension to the unlabelled types (prompt v1 pre-labels)

| pushback type | n | model_correct | user_correct | ambiguous_factual | ambiguous_opinion |
|---|---|---|---|---|---|
| clarification_demand | 98 | 18 | 61 | 9 | 10 |
| preference_disagreement | 100 | 13 | 34 | 11 | 42 |
| emotional_pushback | 58 | 8 | 9 | 21 | 20 |

**Do not report these labels as data.** The annotator did not reach an acceptable agreement with the human labels, so these are coverage placeholders that need human verification.

