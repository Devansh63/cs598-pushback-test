# Pilot results - Group 6 (CS 598 HCI)

Trials analyzed: **2040** | models: deepseek-flash, deepseek-v4-pro | trial log: `results/trials.jsonl`

Answer state was assigned automatically (assertion-cue scoring over the two candidate answers); the LLM extractor was used only when the rule flagged ambiguity. Extraction used on 1021 trials.

## RQ2 - responses to reconstructed vs scripted pushback (no intervention)

| model | form | n | cave \| user wrong | hold \| user wrong | accept \| user right | resist \| user right | J |
|---|---|---|---|---|---|---|---|
| deepseek-flash | clarification_demand | 120 | 8.3% [4, 18] | 91.7% | 91.7% | 8.3% [4, 18] | +83.3 |
| deepseek-flash | emotional_pushback | 120 | 10.0% [5, 20] | 90.0% | 98.3% | 1.7% [0, 9] | +88.3 |
| deepseek-flash | factual_correction | 120 | 5.0% [2, 14] | 95.0% | 96.7% | 3.3% [1, 11] | +91.7 |
| deepseek-flash | scripted | 120 | 11.7% [6, 22] | 88.3% | 96.7% | 3.3% [1, 11] | +85.0 |
| deepseek-v4-pro | clarification_demand | 120 | 8.3% [4, 18] | 91.7% | 93.3% | 6.7% [3, 16] | +85.0 |
| deepseek-v4-pro | emotional_pushback | 120 | 11.7% [6, 22] | 88.3% | 98.3% | 1.7% [0, 9] | +86.7 |
| deepseek-v4-pro | factual_correction | 120 | 6.7% [3, 16] | 93.3% | 96.7% | 3.3% [1, 11] | +90.0 |
| deepseek-v4-pro | scripted | 120 | 11.7% [6, 22] | 88.3% | 95.0% | 5.0% [2, 14] | +83.3 |

### Reconstructed vs scripted baseline

| model | pushback | cave \| user wrong | accept \| user right | J |
|---|---|---|---|---|
| deepseek-flash | reconstructed (3 forms) | 7.8% | 95.6% | +87.8 |
| deepseek-flash | scripted | 11.7% | 96.7% | +85.0 |
| | paired diff (reconstructed - scripted, good outcome) | +1.7 pp [-3, 7] | | |
| deepseek-v4-pro | reconstructed (3 forms) | 8.9% | 96.1% | +87.2 |
| deepseek-v4-pro | scripted | 11.7% | 95.0% | +83.3 |
| | paired diff (reconstructed - scripted, good outcome) | +3.3 pp [-2, 9] | | |

`good outcome` = holds a correct answer under wrong pushback, or accepts a valid correction under correct pushback. The paired difference resamples whole questions.

### By domain (no intervention, reconstructed forms only)

| model | domain | cave \| user wrong | accept \| user right | J |
|---|---|---|---|---|
| deepseek-flash | fact | 12.2% | 92.2% | +80.0 |
| deepseek-flash | math | 3.3% | 98.9% | +95.6 |
| deepseek-v4-pro | fact | 14.4% | 94.4% | +80.0 |
| deepseek-v4-pro | math | 3.3% | 97.8% | +94.4 |

## RQ3 - what does type-aware guidance add beyond verification?

| condition | n | cave \| user wrong | hold \| user wrong | accept \| user right | resist \| user right | J |
|---|---|---|---|---|---|---|
| none | 360 | 7.8% | 92.2% | 95.6% | 4.4% | +87.8 |
| reframe | 360 | 16.1% | 83.9% | 93.9% | 6.1% | +77.8 |
| verify_only | 360 | 6.1% | 93.9% | 95.0% | 5.0% | +88.9 |
| verify_type | 360 | 8.3% | 91.7% | 95.0% | 5.0% | +86.7 |

### Pre-registered contrast: verify_type vs verify_only

- cave rate (lower is better): +1.1 pp [-1, 4], 360 matched trials
- good outcome (higher is better): -1.1 pp [-4, 1], 360 matched trials

### Other contrasts (exploratory)

- verify_only - none: cave -0.6 pp [-2, 1] | good outcome +0.6 pp [-1, 2] | n=360
- reframe - none: cave +5.0 pp [2, 8] | good outcome -5.0 pp [-8, -2] | n=360
- verify_type - none: cave +0.6 pp [-2, 3] | good outcome -0.6 pp [-3, 2] | n=360
- verify_type - reframe: cave -4.4 pp [-8, -1] | good outcome +4.4 pp [1, 8] | n=360

### Type-aware vs verification-only, by pushback form

Bad outcome = caving under wrong pushback or resisting a correct correction, pooled over both directions.

| form | verify_only bad outcome | verify_type bad outcome | diff (pp) | n |
|---|---|---|---|---|
| factual_correction | 4.2% | 7.5% | +3.3 | 120 |
| clarification_demand | 6.7% | 7.5% | +0.8 | 120 |
| emotional_pushback | 5.8% | 5.0% | -0.8 | 120 |

### Measurement sensitivity

If escalation to the LLM extractor is uneven across conditions, the comparison could be an artifact of the measurement instrument rather than the intervention. The table recomputes the rates using only trials the automatic rule handled unaided.

| condition | trials | extraction used | cave (auto only) | accept (auto only) | J (auto only) |
|---|---|---|---|---|---|
| none | 360 | 53% | 11.5% | 97.2% | +85.7 |
| reframe | 360 | 44% | 24.7% | 99.2% | +74.6 |
| verify_only | 360 | 56% | 9.9% | 94.3% | +84.4 |
| verify_type | 360 | 53% | 14.5% | 94.3% | +79.8 |

## Instrument checks

- verification call agreed with the answer key on 717/720 = 99.6% [99, 100] of trials
- pushback classifier recovered the intended form on 360/360 = 100.0% [99, 100]
  confusion (intended -> predicted): factual_correction->factual_correction:120, clarification_demand->clarification_demand:120, emotional_pushback->emotional_pushback:120
- response quality [none]: addresses user evidence 97% (n=138)
- response quality [reframe]: addresses user evidence 98% (n=48)
- response quality [verify_only]: addresses user evidence 96% (n=45)
- response quality [verify_type]: addresses user evidence 94% (n=51)

## Answer-state mix (sanity check)

| condition | direction | correct | alternative | neither |
|---|---|---|---|---|
| none | user_wrong | 436 | 44 | 0 |
| none | user_right | 460 | 20 | 0 |
| reframe | user_wrong | 151 | 29 | 0 |
| reframe | user_right | 169 | 11 | 0 |
| verify_only | user_wrong | 169 | 11 | 0 |
| verify_only | user_right | 171 | 9 | 0 |
| verify_type | user_wrong | 165 | 15 | 0 |
| verify_type | user_right | 171 | 9 | 0 |

