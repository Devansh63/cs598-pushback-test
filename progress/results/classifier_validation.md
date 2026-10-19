# Pushback classifier: accuracy on real pushback

n = 59 real PushbackChat events (20 per reference type), model `deepseek-flash`, classifier prompt frozen before the run.

Reference labels are the released corpus's types, which are themselves LLM-assisted and not human-validated, so this is *agreement*, not truth.

| label | support | precision | recall |
|---|---|---|---|
| factual_correction | 20 | 82.4% | 70.0% |
| clarification_demand | 20 | 50.0% | 35.0% |
| emotional_pushback | 19 | 92.3% | 63.2% |
| other | 0 | 0.0% | nan% |

Overall agreement: **55.9%** (33/59)

### Confusion (reference -> predicted)

| reference \ predicted | factual_correction | clarification_demand | emotional_pushback | other |
|---|---|---|---|---|
| factual_correction | 14 | 6 | 0 | 0 |
| clarification_demand | 2 | 7 | 1 | 10 |
| emotional_pushback | 1 | 1 | 12 | 5 |
