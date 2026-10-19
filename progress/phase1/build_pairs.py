#!/usr/bin/env python3
"""Build adjacent (assistant, user) turn pairs from samples.jsonl.

Outputs:
  pairs.jsonl    one record per pair
  pair_stats.json  counts used by the writeup

Record keys: conv_id, row_idx, turn_idx, assistant_text, user_text, language,
cue_match, matched_cues.

Only English conversations are kept (the dataset stores a natural-language
`language` label per conversation). Pairs where either side is empty are dropped.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
SAMPLES = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "samples.jsonl"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "pairs.jsonl"
STATS = Path(sys.argv[3]) if len(sys.argv) > 3 else HERE / "pair_stats.json"

# Verbatim cue suite from the assignment.
CUE_PATTERN = (
    r"\b(that'?s (wrong|incorrect|not right)|you'?re wrong|are you sure|"
    r"no,? (that|it)'?s|i don'?t think (that|so)|actually,? (it|the)|"
    r"incorrect|not correct|wrong answer|you made (a|an) (mistake|error)|"
    r"recheck|re-?check|that is not what|it'?s actually)\b"
)
CUE_RE = re.compile(CUE_PATTERN, re.IGNORECASE)

SUBPATTERNS = [
    r"that'?s (wrong|incorrect|not right)",
    r"you'?re wrong",
    r"are you sure",
    r"no,? (that|it)'?s",
    r"i don'?t think (that|so)",
    r"actually,? (it|the)",
    r"incorrect",
    r"not correct",
    r"wrong answer",
    r"you made (a|an) (mistake|error)",
    r"recheck",
    r"re-?check",
    r"that is not what",
    r"it'?s actually",
]
SUB_RES = [(p, re.compile(r"\b(?:" + p + r")\b", re.IGNORECASE)) for p in SUBPATTERNS]


def main() -> None:
    convs = [json.loads(line) for line in SAMPLES.open(encoding="utf-8")]

    n_convs = len(convs)
    lang_counts = Counter((c.get("row") or c).get("language") or "UNKNOWN" for c in convs)
    n_english_convs = lang_counts.get("English", 0)

    pairs = []
    dropped_empty = 0
    total_english_pairs = 0

    for c in convs:
        row = c.get("row") or c
        if row.get("language") != "English":
            continue
        conv = row.get("conversation") or []
        conv_id = row.get("conversation_hash") or f"row-{c['row_idx']}"
        for i in range(len(conv) - 1):
            a, b = conv[i], conv[i + 1]
            if a.get("role") != "assistant" or b.get("role") != "user":
                continue
            total_english_pairs += 1
            atext = (a.get("content") or "").strip()
            utext = (b.get("content") or "").strip()
            if not atext or not utext:
                dropped_empty += 1
                continue
            matched = [p for p, rx in SUB_RES if rx.search(utext)]
            pairs.append({
                "conv_id": conv_id,
                "row_idx": c["row_idx"],
                "turn_idx": i,          # 0-based index of the assistant turn
                "assistant_text": atext,
                "user_text": utext,
                "language": row.get("language"),
                "cue_match": bool(CUE_RE.search(utext)),
                "matched_cues": matched,
            })

    with OUT.open("w", encoding="utf-8") as f:
        for p in pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    n_cand = sum(1 for p in pairs if p["cue_match"])
    sub_counts = Counter()
    for p in pairs:
        for m in p["matched_cues"]:
            sub_counts[m] += 1
    # first matching subpattern in the canonical order (for attribution)
    first_counts = Counter()
    for p in pairs:
        if p["matched_cues"]:
            first_counts[p["matched_cues"][0]] += 1

    stats = {
        "n_conversations_sampled": n_convs,
        "n_english_conversations": n_english_convs,
        "language_counts": dict(lang_counts.most_common()),
        "n_english_pairs_total": total_english_pairs,
        "n_pairs_dropped_empty": dropped_empty,
        "n_pairs": len(pairs),
        "n_candidates": n_cand,
        "n_non_candidates": len(pairs) - n_cand,
        "yield_per_1000_conversations": (
            n_cand / n_convs * 1000 if n_convs else 0.0
        ),
        "candidate_rate_per_pair": n_cand / len(pairs) if pairs else 0.0,
        "per_subpattern_pair_hits": dict(sub_counts),
        "per_subpattern_first_attribution": dict(first_counts),
        "cue_pattern": CUE_PATTERN,
        "subpatterns": SUBPATTERNS,
    }
    STATS.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
