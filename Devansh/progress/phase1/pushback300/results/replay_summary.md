# Natural-context replay: 300 real pushback cases

Trials analysed: **599** (2 models x 300 cases). Behaviours labelled by `deepseek-flash` from the reply plus the prior answer and the pushback.

## Overall

| model | n | adopts user claim | maintains | hedges | deflects | unclear | adds reasoning |
|---|---|---|---|---|---|---|---|
| deepseek-flash | 300 | **78.3%** [73, 83] | 17.3% | 3.3% | 1.0% | 0.0% | 89% |
| deepseek-v4-pro | 299 | **71.9%** [67, 77] | 24.1% | 3.0% | 0.7% | 0.3% | 86% |

## Comparison with the two reference points

| setting | adoption / capitulation |
|---|---|
| our pilot, supplied history, single turn | 0–8% caving |
| PushbackChat, 2,309 real events, published | 67.0–77.1% capitulation |
| this replay, deepseek-flash | 78.3% |
| this replay, deepseek-v4-pro | 71.9% |

## Exploratory: adoption by workbook subtheme

| code | n | adopts user claim | maintains |
|---|---|---|---|
| A | 106 | 73.6% | 21.7% |
| B | 106 | 87.7% | 8.5% |
| E | 96 | 76.0% | 22.9% |
| I | 52 | 75.0% | 25.0% |
| L | 92 | 63.0% | 35.9% |
| P | 42 | 76.2% | 16.7% |
| R | 323 | 70.3% | 24.5% |
| T | 110 | 77.3% | 19.1% |

## What this does and does not show

- It shows how often two models *change position* when a real user pushes back inside the original conversation. That is the behaviour PushbackChat measures, and the comparison above is the useful one.
- It does **not** show that adoption was harmful. Correctness of the challenged answer is unlabelled; 'adopted' is not 'wrongly adopted'. The harmful subset needs the two-human verification described in the proposal.
- The target model did not generate the challenged answer, exactly as in PushbackChat's design, so both share that validity caveat.
- No no-pushback control exists for these cases, so we cannot separate 'the reply would have changed anyway' from 'the pushback caused it'.

