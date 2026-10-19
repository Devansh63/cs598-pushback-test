# Phase 1 — lexical pushback filter: precision/recall measurement

## What was measured

A cue-based filter is applied to the **user turn** of every adjacent
(assistant turn → next user turn) pair in English WildChat conversations. The
filter's output is compared against an LLM-labeled 4-way rubric, with labels
sampled separately from cue-matched and non-matched pairs.

### Filter (verbatim)

```python
CUES = r"\b(that'?s (wrong|incorrect|not right)|you'?re wrong|are you sure|no,? (that|it)'?s|i don'?t think (that|so)|actually,? (it|the)|incorrect|not correct|wrong answer|you made (a|an) (mistake|error)|recheck|re-?check|that is not what|it'?s actually)\b"
```

Applied case-insensitively (`re.IGNORECASE`) to `user_text`. A pair is a
**candidate** if this regex matches anywhere in the user turn.

### Sampling frame

| quantity | value |
|---|---|
| conversations sampled (expanded frame) | 60,000 |
| English conversations | 34,800 |
| total English adjacent pairs | 38,282 |
| pairs dropped for empty text | 425 |
| usable pairs | 37,857 |
| candidate pairs | 159 |
| non-candidate pairs | 37,698 |
| labeled candidates | 150 |
| labeled non-candidates | 150 |
| unparsed labels (excluded) | 0 |

The instructed 2,000-conversation spread sample (offsets 0–19,000 step 1,000) contained 948 English conversations and 1,620 usable pairs, with only **6** cue-matched pairs (3.0 per 1,000 conversations). Because 6 candidates cannot support a 150-candidate precision estimate, the measurement frame was rebuilt as a 60,000-conversation random sample drawn from four official `allenai/WildChat-1M` parquet shards (shards 00, 06, 07, 13; 15,000 rows sampled per shard, seed 13; see `frame_manifest.json` and `build_frame_from_parquet.py`). The rows API was used for the pilot but was quota-limited (HTTP 429); an incomplete rows-API expansion (18,859 conversations, 64 candidates, 3.4 per 1,000) is consistent with the shard frame's yield. The pilot and the shard frame are reported separately below.

### Yield

- **2.65 candidate pairs per 1,000 conversations** (all languages in the frame).
- 4.57 per 1,000 English conversations.
- 4.200 per 1,000 English adjacent pairs.

### Per-subpattern hits (expanded frame)

Counts overlap: one pair can match several subpatterns. "First attribution"
assigns the pair to the earliest subpattern in the list.

| subpattern | pairs matched | first attribution |
|---|---:|---:|
| `that'?s (wrong|incorrect|not right)` | 5 | 5 |
| `you'?re wrong` | 1 | 1 |
| `are you sure` | 44 | 44 |
| `no,? (that|it)'?s` | 11 | 10 |
| `i don'?t think (that|so)` | 6 | 5 |
| `actually,? (it|the)` | 6 | 6 |
| `incorrect` | 62 | 62 |
| `not correct` | 15 | 14 |
| `wrong answer` | 2 | 2 |
| `you made (a|an) (mistake|error)` | 2 | 2 |
| `recheck` | 2 | 2 |
| `re-?check` | 2 | 0 |
| `that is not what` | 0 | 0 |
| `it'?s actually` | 6 | 6 |

## Results

Labels come from DeepSeek `deepseek-flash` at temperature 0 with a strict rubric
(see `label_sample.py`). Positive class = `pushback_disagreement`.

| metric | estimate | 95% Wilson CI | numerator / denominator |
|---|---:|---|---|
| Precision (candidate sample, n=150) | 0.580 | [0.500, 0.656] | 87 TP / 150 predicted |
| Recall (weighted, n_eff=151.3) | 0.020 | [0.007, 0.057] | 92.22 / 4615.98 weighted |
| Recall (unweighted, n=300) | 0.350 | — | 105 / 300 labeled |

Unweighted precision is 0.580, identical to the weighted value
because every candidate pair carries the same weight. The unweighted recall is
the raw positive rate in the deliberately 50/50 stratified sample
(105/300); it is **not** a corpus recall estimate and is
shown only for audit. The weighted recall is the estimate to use.

The weighted recall estimates how many true disagreement pairs the filter
retrieves across the English pair population: it scales the candidate and
non-candidate label rates by their stratum sizes
(N_cand = 159, N_non = 37,698).

### Label × cue-match confusion

| cue match | pushback_disagreement | neutral_question | preference_change | other | total |
|---|---:|---:|---:|---:|---:|
| yes | 87 | 13 | 1 | 49 | 150 |
| no | 18 | 26 | 14 | 92 | 150 |

### Label distribution in the labeled sample

| label | count |
|---|---:|
| pushback_disagreement | 105 |
| neutral_question | 39 |
| preference_change | 15 |
| other | 141 |

### Cue-level precision in the labeled candidate sample

Counts overlap (a pair can match several cues), so this table is descriptive and
does not decompose the 150 candidates.

| cue | labeled candidates matching | pushback | precision |
|---|---:|---:|---:|
| `incorrect` | 59 | 22 | 0.37 |
| `are you sure` | 41 | 29 | 0.71 |
| `not correct` | 15 | 12 | 0.80 |
| `no,? (that|it)'?s` | 10 | 9 | 0.90 |
| `actually,? (it|the)` | 6 | 3 | 0.50 |
| `it'?s actually` | 6 | 3 | 0.50 |
| `that'?s (wrong|incorrect|not right)` | 5 | 5 | 1.00 |
| `i don'?t think (that|so)` | 4 | 1 | 0.25 |
| `re-?check` | 2 | 1 | 0.50 |
| `recheck` | 2 | 1 | 0.50 |
| `wrong answer` | 2 | 2 | 1.00 |
| `you made (a|an) (mistake|error)` | 2 | 1 | 0.50 |
| `you'?re wrong` | 1 | 1 | 1.00 |

## Assumptions

1. **LLM labels are ground truth.** Every label is a single `deepseek-flash`
   judgment at temperature 0; there is no human adjudication or inter-annotator
   agreement estimate. Systematic model error would bias both precision and
   recall.
2. **Stratified simple random sampling.** Within the candidate and
   non-candidate strata, pairs are treated as a simple random sample. The 300
   labeled pairs (150 + 150, seed 13) are weighted by the inverse of their
   stratum sampling fraction (`N_stratum / 150`).
3. **Independent pairs.** Wilson intervals assume independent observations.
   Pairs from the same conversation are correlated, so the true intervals are
   somewhat wider than reported; this is a conservative-in-the-wrong-direction
   approximation.
4. **Recall interval.** Wilson is computed on the weighted recall with the Kish
   effective sample size n_eff = (Σw)² / Σw² = 151.3, because the two
   strata are weighted differently. This is an approximation, not an exact
   design-based variance.
5. **Population.** The target is English conversations in the
   `allenai/WildChat-1M` **train** split (837,989 rows). The frame is 15,000
   rows sampled uniformly at random from each of four official parquet shards
   (00, 06, 07, 13), covering early, middle, and late corpus positions. The
   full 1M dataset (including other splits) and non-English conversations are
   outside the frame.
6. **Truncation.** Very long turns were truncated for the judge at 12,000
   assistant characters and 6,000 user characters; truncation flags are stored
   per record in `judged.jsonl`.

## Limitations

- Labels are **LLM-judged, not human-annotated**. The rubric reduces but does
  not eliminate ambiguity, especially for terse turns such as "are you sure?"
  and for turns that mix a correction with a new request.
- The sample is **60,000 conversations**, not the full
  837,989-row train split. Rows are random within four shards, but multiple
  pairs come from the same conversation, so observations are clustered and the
  Wilson intervals are somewhat optimistic.
- The cue suite is a **lexical proxy**. It cannot detect disagreement phrased
  without any cue ("Hmm, 2+2 is 4 though") and it fires on non-disagreement
  uses of the same words (for example "incorrect" inside quoted code or a
  jailbreak prompt). Both failure modes are visible in the confusion table.
- **Precision is conditional on a cue match** and does not depend on the
  candidate prevalence; recall does, and is therefore the more fragile number.
- **Language is labeled per conversation, not per turn.** Some user turns inside
  English conversations are written in another language; the English cue suite
  cannot match them, and such turns appear among the missed positives.
- The two duplicate `conversation_hash` values in the pilot sample were kept as
  separate corpus rows because they are distinct submissions with different
  timestamps; they do not affect the shard frame.
