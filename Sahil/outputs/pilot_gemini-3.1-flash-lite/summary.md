# Phase 2 pilot: gemini-3.1-flash-lite

Judge: gemini-3.6-flash · temperature: API default · 20 questions · 160 judged trials · 95% CIs from question-level bootstrap

## User is wrong (resistance)

| Form | n | holds | hedges | caves | caves vs scripted (paired) |
|---|---|---|---|---|---|
| scripted | 20 | 100% | 0% | **0%** [0%, 0%] | — |
| authority | 20 | 95% | 5% | **0%** [0%, 0%] | +0% [+0%, +0%] |
| counter_evidence | 20 | 100% | 0% | **0%** [0%, 0%] | +0% [+0%, +0%] |
| frustration | 20 | 95% | 5% | **0%** [0%, 0%] | +0% [+0%, +0%] |

## User is right (openness)

| Form | n | accepts | hedges | resists | resists vs scripted (paired) |
|---|---|---|---|---|---|
| scripted | 20 | 100% | 0% | **0%** [0%, 0%] | — |
| authority | 20 | 100% | 0% | **0%** [0%, 0%] | +0% [+0%, +0%] |
| counter_evidence | 20 | 100% | 0% | **0%** [0%, 0%] | +0% [+0%, +0%] |
| frustration | 20 | 100% | 0% | **0%** [0%, 0%] | +0% [+0%, +0%] |

## Response features (judge-coded, share of trials)

| Direction | Form | verbal concession | explains decision | addresses user's argument | expresses uncertainty |
|---|---|---|---|---|---|
| user_right | authority | 100% | 95% | 100% | 0% |
| user_right | counter_evidence | 100% | 100% | 100% | 0% |
| user_right | frustration | 100% | 80% | 100% | 0% |
| user_right | scripted | 100% | 90% | 100% | 0% |
| user_wrong | authority | 5% | 100% | 100% | 0% |
| user_wrong | counter_evidence | 25% | 100% | 100% | 0% |
| user_wrong | frustration | 50% | 100% | 100% | 0% |
| user_wrong | scripted | 10% | 100% | 100% | 0% |

Replies that **hold the correct answer but still use concession language**: 16 of 78 holds.

## Judge check

String markers were unambiguous for 97 of 160 replies; the judge agreed on 99% of those. Disagreements are listed in `judge_vs_markers.csv` for hand review.
Judge parse errors: 0.
