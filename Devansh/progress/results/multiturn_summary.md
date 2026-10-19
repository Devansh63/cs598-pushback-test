# Multi-turn escalation: where the caving actually lives

Conversations: **240** (60 questions x 2 directions x 2 models), 3 escalating pushback rounds each.

The user's claim is held constant; only the form escalates (factual_correction -> clarification_demand -> emotional_pushback).

## deepseek-flash

| round | form | cave \| user wrong | accept \| user right |
|---|---|---|---|
| 1 | factual_correction | 1.7% (n=60) | 98.3% (n=60) |
| 2 | clarification_demand | 1.7% (n=60) | 98.3% (n=60) |
| 3 | emotional_pushback | 3.3% (n=60) | 98.3% (n=60) |

Single-turn caving for comparison: 1.7% (the same conversations after one pushback).

## deepseek-v4-pro

| round | form | cave \| user wrong | accept \| user right |
|---|---|---|---|
| 1 | factual_correction | 3.3% (n=60) | 96.7% (n=60) |
| 2 | clarification_demand | 3.3% (n=60) | 98.3% (n=60) |
| 3 | emotional_pushback | 3.3% (n=60) | 98.3% (n=60) |

Single-turn caving for comparison: 3.3% (the same conversations after one pushback).

