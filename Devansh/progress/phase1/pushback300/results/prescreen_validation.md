# Is the `pushback_300` prescreen reliable?

Sample: **100** of 300 cases, independent judge (`deepseek-flash`, temperature 0), rubric shown in `validate_prescreen.py`.

- prescreen precision (case really is pushback): **100.0%** [96, 100]

| judge label | n | share |
|---|---|---|
| pushback_disagreement | 100 | 100.0% |

Event ids of non-confirmed cases (0): 

**Caveat.** This is agreement between two LLM judges, not against human labels. It bounds how much the prescreen could be wrong; it does not settle it. Human adjudication of the flagged cases is still required before any rate is reported.

