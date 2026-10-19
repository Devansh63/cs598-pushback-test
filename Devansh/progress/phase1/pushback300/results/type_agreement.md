# Type coding: is the workbook's 10-code scheme reproducible?

Two independent AI passes over **300** real pushback turns (workbook preliminary codes vs. fresh prompt), model `deepseek-flash`.

| code | label | workbook n | our n | precision | recall | Cohen's κ |
|---|---|---|---|---|---|---|
| B | Bare disagreement | 53 | 178 | 30% | 100% | 0.26 |
| A | Alternative claim | 53 | 74 | 66% | 92% | 0.71 |
| I | Inconsistency challenge | 26 | 33 | 76% | 96% | 0.83 |
| L | Reasoning challenge | 46 | 37 | 89% | 72% | 0.76 |
| E | Counter-evidence | 48 | 42 | 93% | 81% | 0.84 |
| S | Appeal to authority or source | 4 | 5 | 80% | 100% | 0.89 |
| R | Recheck request | 162 | 184 | 86% | 98% | 0.81 |
| T | Task or constraint correction | 55 | 44 | 84% | 67% | 0.70 |
| P | Repeated insistence | 21 | 21 | 90% | 90% | 0.90 |
| F | Frustration | 3 | 4 | 50% | 67% | 0.57 |

- identical code set: **37.3%** (112/300)
- mean Jaccard overlap: **68.3%**

**Read this as an upper bound.** Two AI coders trained on overlapping data agree more than two humans would, so these kappas overstate human reliability. The codes that are *least* reproducible (low κ) are the ones the codebook must define more sharply before the two-human pass.

