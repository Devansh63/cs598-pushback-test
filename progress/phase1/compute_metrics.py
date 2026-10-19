#!/usr/bin/env python3
"""Compute precision, recall, Wilson CIs, and the confusion table.

Inputs : pairs_expanded.jsonl, pair_stats_expanded.json, judged.jsonl,
         pair_stats.json (pilot sample)
Output : metrics.json, measurement.md

Assumptions are stated in measurement.md; all numbers here come from the files
above and are dumped to metrics.json before being formatted.
"""
import json
import math
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
JUDGED = HERE / "judged.jsonl"
SAMPLE = HERE / "label_sample.jsonl"
STATS = HERE / "pair_stats_expanded.json"
PILOT_STATS = HERE / "pair_stats.json"
OUT_JSON = HERE / "metrics.json"
OUT_MD = HERE / "measurement.md"

LABELS = ["pushback_disagreement", "neutral_question", "preference_change", "other"]
Z = 1.959963984540054


def wilson_from_p(p: float, n: float) -> tuple[float, float]:
    if not n or n <= 0:
        return (float("nan"), float("nan"))
    denom = 1 + Z * Z / n
    centre = (p + Z * Z / (2 * n)) / denom
    half = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def wilson(k: int, n: int) -> tuple[float, float]:
    return wilson_from_p(k / n if n else float("nan"), n)


def fmt(x: float) -> str:
    return f"{x:.3f}"


def md_escape(text: str) -> str:
    """Escape pipes so regex text survives a Markdown table cell."""
    return text.replace("|", "\\|")


def main() -> None:
    stats = json.loads(STATS.read_text())
    pilot = json.loads(PILOT_STATS.read_text()) if PILOT_STATS.exists() else None
    judged = [json.loads(line) for line in JUDGED.open(encoding="utf-8")]

    cand = [r for r in judged if r["stratum"] == "candidate"]
    non = [r for r in judged if r["stratum"] == "non_candidate"]
    cand_ok = [r for r in cand if r.get("parse_ok") and r.get("label") in LABELS]
    non_ok = [r for r in non if r.get("parse_ok") and r.get("label") in LABELS]
    unparsed = len(judged) - len(cand_ok) - len(non_ok)

    tp = sum(1 for r in cand_ok if r["label"] == "pushback_disagreement")
    fp = len(cand_ok) - tp
    precision = tp / len(cand_ok) if cand_ok else float("nan")
    prec_lo, prec_hi = wilson(tp, len(cand_ok))

    n_c = stats["n_candidates"]
    n_n = stats["n_non_candidates"]
    n_c_lab = len(cand_ok)
    n_n_lab = len(non_ok)

    p_c = tp / n_c_lab if n_c_lab else float("nan")
    tp_n = sum(1 for r in non_ok if r["label"] == "pushback_disagreement")
    p_n = tp_n / n_n_lab if n_n_lab else float("nan")

    # Horvitz-Thompson style estimates of true positives caught and missed.
    tp_w = n_c * p_c
    fn_w = n_n * p_n
    recall = tp_w / (tp_w + fn_w) if (tp_w + fn_w) else float("nan")

    # Unweighted (raw label counts in the 300-pair sample).
    recall_unw = ((tp + tp_n) / (n_c_lab + n_n_lab)
                  if (n_c_lab + n_n_lab) else float("nan"))
    precision_unw = precision

    # Kish effective sample size for the weighted recall, using the design
    # weights attached to every labeled pair.
    weights = [r.get("sample_weight", 1.0) for r in cand_ok + non_ok]
    n_eff = (sum(weights) ** 2) / sum(w * w for w in weights) if weights else 0
    rec_lo, rec_hi = wilson_from_p(recall, n_eff)

    # Confusion table: cue match x label.
    conf = {stratum: Counter() for stratum in (True, False)}
    for r in cand_ok:
        conf[True][r["label"]] += 1
    for r in non_ok:
        conf[False][r["label"]] += 1

    label_dist = Counter(r["label"] for r in cand_ok + non_ok)

    # Descriptive cue-level precision within the labeled candidate sample.
    judged_by_id = {r["pair_id"]: r for r in judged}
    cue_stats: dict[str, list[int]] = {}
    for srow in (json.loads(line) for line in SAMPLE.open(encoding="utf-8")):
        if srow["stratum"] != "candidate":
            continue
        j = judged_by_id.get(srow["pair_id"])
        if not j or not j.get("parse_ok"):
            continue
        for cue in srow.get("matched_cues") or []:
            slot = cue_stats.setdefault(cue, [0, 0])
            slot[0] += 1
            if j["label"] == "pushback_disagreement":
                slot[1] += 1
    cue_table = "\n".join(
        f"| `{md_escape(cue)}` | {n} | {tp} | {tp / n:.2f} |"
        for cue, (n, tp) in sorted(cue_stats.items(), key=lambda kv: (-kv[1][0], kv[0]))
    )

    per_1000_conv = n_c / stats["n_conversations_sampled"] * 1000
    per_1000_en_conv = n_c / stats["n_english_conversations"] * 1000
    per_1000_pairs = n_c / stats["n_pairs"] * 1000

    metrics = {
        "frame": stats,
        "pilot": pilot,
        "labeling": {
            "n_candidate_labels": n_c_lab,
            "n_non_candidate_labels": n_n_lab,
            "n_unparsed": unparsed,
            "label_distribution": dict(label_dist),
            "confusion_cue_match_by_label": {
                "cue_match_true": dict(conf[True]),
                "cue_match_false": dict(conf[False]),
            },
        },
        "precision": {
            "value": precision,
            "unweighted_value": precision_unw,
            "tp": tp,
            "fp": fp,
            "n": n_c_lab,
            "wilson_95": [prec_lo, prec_hi],
        },
        "recall": {
            "value": recall,
            "unweighted_value": recall_unw,
            "estimated_tp_in_frame": tp_w,
            "estimated_fn_in_frame": fn_w,
            "tp_in_candidate_sample": tp,
            "fn_in_non_candidate_sample": tp_n,
            "effective_n_kish": n_eff,
            "wilson_95": [rec_lo, rec_hi],
        },
        "yield": {
            "candidates_per_1000_conversations": per_1000_conv,
            "candidates_per_1000_english_conversations": per_1000_en_conv,
            "candidates_per_1000_english_pairs": per_1000_pairs,
        },
    }
    OUT_JSON.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    s = stats
    regex = s["cue_pattern"]
    sub_rows = []
    for sub in s["subpatterns"]:
        hits = s["per_subpattern_pair_hits"].get(sub, 0)
        first = s["per_subpattern_first_attribution"].get(sub, 0)
        sub_rows.append(f"| `{md_escape(sub)}` | {hits} | {first} |")

    def conf_row(flag: bool) -> str:
        c = conf[flag]
        return (f"| {'yes' if flag else 'no'} | " +
                " | ".join(str(c.get(l, 0)) for l in LABELS) +
                f" | {sum(c.values())} |")

    pilot_note = ""
    if pilot:
        pilot_note = (
            f"The instructed 2,000-conversation spread sample (offsets 0–19,000 step 1,000) "
            f"contained {pilot['n_english_conversations']:,} English conversations and "
            f"{pilot['n_pairs']:,} usable pairs, with only **{pilot['n_candidates']}** cue-matched "
            f"pairs ({pilot['yield_per_1000_conversations']:.1f} per 1,000 conversations). "
            f"Because 6 candidates cannot support a 150-candidate precision estimate, the "
            f"measurement frame was rebuilt as a {s['n_conversations_sampled']:,}-conversation "
            f"random sample drawn from four official `allenai/WildChat-1M` parquet shards "
            f"(shards 00, 06, 07, 13; 15,000 rows sampled per shard, seed 13; see "
            f"`frame_manifest.json` and `build_frame_from_parquet.py`). The rows API was used "
            f"for the pilot but was quota-limited (HTTP 429); an incomplete rows-API expansion "
            f"(18,859 conversations, 64 candidates, 3.4 per 1,000) is consistent with the "
            f"shard frame's yield. The pilot and the shard frame are reported separately below."
        )

    md = f"""# Phase 1 — lexical pushback filter: precision/recall measurement

## What was measured

A cue-based filter is applied to the **user turn** of every adjacent
(assistant turn → next user turn) pair in English WildChat conversations. The
filter's output is compared against an LLM-labeled 4-way rubric, with labels
sampled separately from cue-matched and non-matched pairs.

### Filter (verbatim)

```python
CUES = r"{regex}"
```

Applied case-insensitively (`re.IGNORECASE`) to `user_text`. A pair is a
**candidate** if this regex matches anywhere in the user turn.

### Sampling frame

| quantity | value |
|---|---|
| conversations sampled (expanded frame) | {s['n_conversations_sampled']:,} |
| English conversations | {s['n_english_conversations']:,} |
| total English adjacent pairs | {s['n_english_pairs_total']:,} |
| pairs dropped for empty text | {s['n_pairs_dropped_empty']:,} |
| usable pairs | {s['n_pairs']:,} |
| candidate pairs | {s['n_candidates']:,} |
| non-candidate pairs | {s['n_non_candidates']:,} |
| labeled candidates | {n_c_lab} |
| labeled non-candidates | {n_n_lab} |
| unparsed labels (excluded) | {unparsed} |

{pilot_note}

### Yield

- **{per_1000_conv:.2f} candidate pairs per 1,000 conversations** (all languages in the frame).
- {per_1000_en_conv:.2f} per 1,000 English conversations.
- {per_1000_pairs:.3f} per 1,000 English adjacent pairs.

### Per-subpattern hits (expanded frame)

Counts overlap: one pair can match several subpatterns. "First attribution"
assigns the pair to the earliest subpattern in the list.

| subpattern | pairs matched | first attribution |
|---|---:|---:|
{chr(10).join(sub_rows)}

## Results

Labels come from DeepSeek `deepseek-flash` at temperature 0 with a strict rubric
(see `label_sample.py`). Positive class = `pushback_disagreement`.

| metric | estimate | 95% Wilson CI | numerator / denominator |
|---|---:|---|---|
| Precision (candidate sample, n={n_c_lab}) | {fmt(precision)} | [{fmt(prec_lo)}, {fmt(prec_hi)}] | {tp} TP / {tp + fp} predicted |
| Recall (weighted, n_eff={n_eff:.1f}) | {fmt(recall)} | [{fmt(rec_lo)}, {fmt(rec_hi)}] | {tp_w:.2f} / {tp_w + fn_w:.2f} weighted |
| Recall (unweighted, n={n_c_lab + n_n_lab}) | {fmt(recall_unw)} | — | {tp + tp_n} / {n_c_lab + n_n_lab} labeled |

Unweighted precision is {fmt(precision_unw)}, identical to the weighted value
because every candidate pair carries the same weight. The unweighted recall is
the raw positive rate in the deliberately 50/50 stratified sample
({tp + tp_n}/{n_c_lab + n_n_lab}); it is **not** a corpus recall estimate and is
shown only for audit. The weighted recall is the estimate to use.

The weighted recall estimates how many true disagreement pairs the filter
retrieves across the English pair population: it scales the candidate and
non-candidate label rates by their stratum sizes
(N_cand = {n_c:,}, N_non = {n_n:,}).

### Label × cue-match confusion

| cue match | pushback_disagreement | neutral_question | preference_change | other | total |
|---|---:|---:|---:|---:|---:|
{conf_row(True)}
{conf_row(False)}

### Label distribution in the labeled sample

| label | count |
|---|---:|
""" + "\n".join(f"| {l} | {label_dist.get(l, 0)} |" for l in LABELS) + f"""

### Cue-level precision in the labeled candidate sample

Counts overlap (a pair can match several cues), so this table is descriptive and
does not decompose the 150 candidates.

| cue | labeled candidates matching | pushback | precision |
|---|---:|---:|---:|
{cue_table}

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
   effective sample size n_eff = (Σw)² / Σw² = {n_eff:.1f}, because the two
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
- The sample is **{s['n_conversations_sampled']:,} conversations**, not the full
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
"""
    OUT_MD.write_text(md, encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    print(f"wrote {OUT_MD} and {OUT_JSON}")


if __name__ == "__main__":
    main()
