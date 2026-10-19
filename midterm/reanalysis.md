# PushbackChat v1 - independent re-analysis (Group 6, CS 598 HCI)

All numbers below are computed from the public PushbackChat v1 release (2,309 real English pushback events extracted from WildChat-4.8M) by `prelim_analysis.py`.

- events: **2309**
- events with human correctness labels: **500** (22%)
- behaviour rows (4 models): **9235**
- dataset sha256: `38974c084f7238cc6c9b1c7d498d9c15ff23d12d46922c3e89b90bf2800a2df7`

## 1. Behaviour distribution by model (all 2,309 real pushback events)

| model | capitulation | defense | hedge | deflection | missing |
|---|---|---|---|---|---|
| deepseek_v4_flash | 77.1% | 12.9% | 3.6% | 6.5% | 0 |
| llama_3_3_70b | 69.2% | 13.0% | 5.7% | 12.2% | 1 |
| nemotron_3_nano | 67.0% | 17.7% | 6.7% | 8.6% | 0 |
| qwen3_235b_a22b_2507 | 74.7% | 16.1% | 4.9% | 4.3% | 0 |

## 2. Capitulation rate by pushback type (all events)

| type | n | deepseek_v4_flash | llama_3_3_70b | nemotron_3_nano | qwen3_235b_a22b_2507 |
|---|---|---|---|---|---|
| factual_correction | 750 | 73.5% | 67.6% | 58.0% | 70.8% |
| clarification_demand | 750 | 75.2% | 62.4% | 65.2% | 71.6% |
| preference_disagreement | 750 | 84.8% | 79.6% | 80.4% | 83.5% |
| emotional_pushback | 59 | 49.2% | 40.7% | 35.6% | 52.5% |

## 3. Correctness-conditioned rates (human ground truth, n=500)

`user wrong` = human label `model_correct` (the prior answer was verified correct and the
pushback was wrong). `user right` = human label `user_correct`, i.e. the correction was valid.

| model | cave given user wrong (ICR) | accept given user right | resist/hedge given user right | gap |
|---|---|---|---|---|
| deepseek_v4_flash | 33.3% (66) [23.2, 45.3] | 82.9% | 13.8% | -49.6 pp |
| llama_3_3_70b | 30.3% (66) [20.6, 42.2] | 72.1% | 19.1% | -41.8 pp |
| nemotron_3_nano | 24.2% (66) [15.5, 35.8] | 65.0% | 30.3% | -40.8 pp |
| qwen3_235b_a22b_2507 | 34.8% (66) [24.5, 46.9] | 77.9% | 19.7% | -43.1 pp |

## 4. LLM vs. human ground-truth reliability (n=500)

raw agreement 89.6% | Cohen's kappa **0.776**

## 5. Would our proposed Phase 1 filter find real pushback?

- the keyword list written in our proposal matches **478/2309 = 20.7%** of turns that are *known* to be pushback
- recall measured inside an already-positive set: precision against the full 4.8M corpus is still unknown

| PushbackChat lexical cue | events it fires on | share |
|---|---|---|
| correction | 950 | 41.1% |
| disagreement | 503 | 21.8% |
| repetition | 328 | 14.2% |
| doubt | 288 | 12.5% |
| clarification | 232 | 10.0% |

Union of their cue suite: 2218/2309 = 96.1% of the released corpus.

## 6. Evidence for a multi-label codebook

- 406/2309 = 17.6% of pushback turns are flagged emotional *in addition to* their strategy type
| type | emotional | non-emotional |
|---|---|---|
| factual_correction | 110 | 640 |
| clarification_demand | 147 | 603 |
| preference_disagreement | 90 | 660 |
| emotional_pushback | 59 | 0 |

- 71/2309 = 3.1% match more than one lexical cue

## 7. Coverage limit that shapes our scope

| type | events | human correctness labels |
|---|---|---|
| factual_correction | 750 | 500 |
| clarification_demand | 750 | 0 |
| preference_disagreement | 750 | 0 |
| emotional_pushback | 59 | 0 |

Correctness ground truth covers **one** pushback type, and only 66 events satisfy
`user wrong + prior answer correct` with a human label. That ceiling is why the project
keeps a controlled question set as the primary source of statistical power.
