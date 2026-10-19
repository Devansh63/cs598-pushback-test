# Type coding: is the workbook's 10-code scheme reproducible?

Two independent AI passes over **300** real pushback turns (workbook preliminary codes vs. fresh prompt), model `deepseek-flash`.

| code | label | workbook n | our n | precision | recall | Cohen's κ |
|---|---|---|---|---|---|---|
| B | Bare disagreement | 53 | 132 | 39% | 96% | 0.40 |
| A | Alternative claim | 53 | 71 | 69% | 92% | 0.74 |
| I | Inconsistency challenge | 26 | 33 | 79% | 100% | 0.87 |
| L | Reasoning challenge | 46 | 32 | 91% | 63% | 0.71 |
| E | Counter-evidence | 48 | 41 | 85% | 73% | 0.75 |
| S | Appeal to authority or source | 4 | 5 | 80% | 100% | 0.89 |
| R | Recheck request | 162 | 181 | 88% | 99% | 0.84 |
| T | Task or constraint correction | 55 | 43 | 86% | 67% | 0.71 |
| P | Repeated insistence | 21 | 20 | 90% | 86% | 0.87 |
| F | Frustration | 3 | 7 | 29% | 67% | 0.39 |

- identical code set: **47.3%** (142/300)
- mean Jaccard overlap: **72.3%**

**Read this as an upper bound.** Two AI coders trained on overlapping data agree more than two humans would, so these kappas overstate human reliability. The codes that are *least* reproducible (low κ) are the ones the codebook must define more sharply before the two-human pass.


### Bare-disagreement check against the strict rule

- κ with the mutual-exclusion rule: **0.40** (this run, n=300)
- κ without it: **0.26**
- B labeled this run: 132, in the other run: 178, in the workbook: 53

