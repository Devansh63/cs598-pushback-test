"""Phase 1 stage 1–4: find candidate pushback turns in WildChat-1M and keep the full frame of
follow-up turns so recall can be measured against a random negative sample.

Stages (every count goes into the funnel):
  1. English, non-toxic, multi-turn conversations
  2. user follow-up turns (a user turn right after an assistant turn), <= 1500 chars   = THE FRAME
  3. lexical cue match, minus instruction-complaint / quiz-prompt patterns
  4. domain hint (math / fact / code / other)

Outputs (results/phase1/, text files are gitignored):
  frame.parquet        every follow-up turn: ids, cue_match, domain_hint, lengths, text  (local only)
  candidates.parquet   cue-matched math/fact turns with context                          (local only)
  funnel.json          counts per stage + the exact patterns                             (committed)

  python3 phase1/filter_wildchat.py [--shards 0-13] [--workers 6]
"""
import argparse
import json
import re
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results" / "phase1"
REPO = "allenai/WildChat-1M"
N_SHARDS = 14
MAX_PUSHBACK_CHARS = 1500

PUSHBACK = [
    r"\b(that'?s|this is|it'?s|you'?re|you are|your answer is|the answer is)\s+(not\s+)?(wrong|incorrect|false|mistaken|a mistake)\b",
    r"\bthat'?s not (true|right|correct|accurate)\b",
    r"\b(is|was) (not|n't) (true|right|correct|accurate)\b",
    r"\bare you sure\b",
    r"\bi (don'?t|do not) think (that'?s|this is|so|you'?re|it'?s|that is)\b",
    r"\byou made (a|an) (mistake|error)\b",
    r"\b(wrong|incorrect) (answer|calculation|result)\b",
    r"\bthe (correct|right|actual|real) answer (is|should be)\b",
    r"\b(my|our|the) (teacher|professor|prof|textbook|book|instructor|tutor|lecturer)\b.{0,40}\b(said|says|told|states|shows)\b",
    r"\b(check|recheck|re-check|double.?check|recalculate) (it |that |this |your )?(again|answer|work|math|calculation)\b",
    r"^\s*(no|nope)\b[\s,.!]+(it|that|this|you|the|its|it'?s|wrong|incorrect|not)\b",
    r"^\s*(wrong|incorrect)\b",
    r"\bactually,? (it|the answer|that|this) (is|was|should)\b",
    r"\bi (believe|think) (it|the answer|that) (is|should be|was)\b",
    r"\b(isn'?t|wasn'?t|doesn'?t) (it|that) (be|equal)\b",
]
EXCLUDE = [
    r"\bnot what i (asked|wanted|meant|said)\b",
    r"\b(rewrite|rephrase|shorter|longer|more (formal|detailed|casual))\b",
    r"\b(continue|go on|keep going)\b",
    r"\b(story|poem|essay|chapter|scene|character|roleplay|role-play|lyrics)\b",
    r"\b(code|function|compile|syntax|script|bug)\b",
    r"\bwhich of the following\b",
    r"\b(is )?not true (of|about)\b",
    r"\b(question \d+|options?:)",
]
MATH = re.compile(r"(\d\s*[\+\-\*/×÷\^=]\s*\d|\b(solve|equation|calculate|probability|derivative|integral|"
                  r"percent|fraction|prime|sum|product|equals|how much|how many|average|median|"
                  r"square root|factor|simplify|evaluate|area|volume|angle)\b)", re.I)
FACT = re.compile(r"\b(who|what|when|where|which|how many|how much|is it true|did|was|were|capital|year|born|"
                  r"founded|invented|discovered|largest|smallest|first|longest|highest|population|definition|meaning)\b", re.I)
CODE = re.compile(r"```|\bdef \w+\(|#include|\bpublic static\b|\bconsole\.log\b|\bimport \w+", re.I)
PUSH_RE = [re.compile(p, re.I) for p in PUSHBACK]
EXCL_RE = [re.compile(p, re.I) for p in EXCLUDE]


def shard_path(i):
    from huggingface_hub import hf_hub_download
    return hf_hub_download(REPO, f"data/train-{i:05d}-of-{N_SHARDS:05d}.parquet", repo_type="dataset")


def domain_of(question, answer):
    ctx = f"{question}\n{answer}"
    if CODE.search(ctx):
        return "code"
    if MATH.search(question) or len(MATH.findall(answer)) >= 2:
        return "math"
    if FACT.search(question[:500]) and len(answer) < 2500:
        return "fact"
    return "other"


def process_shard(i):
    pf = pq.ParquetFile(shard_path(i))
    funnel, frame, cands = Counter(), [], []
    cols = ["conversation_hash", "model", "language", "turn", "toxic", "conversation"]
    for rg in range(pf.num_row_groups):
        for conv in pf.read_row_group(rg, columns=cols).to_pylist():
            funnel["conversations"] += 1
            if conv["language"] != "English" or conv["toxic"]:
                continue
            funnel["english_nontoxic"] += 1
            if conv["turn"] < 2:
                continue
            funnel["multi_turn"] += 1
            msgs = conv["conversation"]
            for j in range(2, len(msgs)):
                m, prev = msgs[j], msgs[j - 1]
                if m["role"] != "user" or prev["role"] != "assistant":
                    continue
                text = m["content"] or ""
                funnel["followup_turns"] += 1
                if len(text) > MAX_PUSHBACK_CHARS or m.get("toxic"):
                    continue
                funnel["frame_turns"] += 1
                hits = [k for k, r in enumerate(PUSH_RE) if r.search(text)]
                excluded = bool(hits) and any(r.search(text) for r in EXCL_RE)
                question = (msgs[j - 2]["content"] or "") if msgs[j - 2]["role"] == "user" else ""
                answer = prev["content"] or ""
                dom = domain_of(question, answer)
                cue = bool(hits) and not excluded
                frame.append({"conversation_hash": conv["conversation_hash"], "turn_index": j, "shard": i,
                              "cue_hit": bool(hits), "cue_match": cue, "domain_hint": dom,
                              "pushback_len": len(text), "pushback": text, "assistant_answer": answer[:4000],
                              "question": question[:2000]})
                if hits:
                    funnel["lexical_hit"] += 1
                if cue:
                    funnel["lexical_pass"] += 1
                    funnel[f"domain_{dom}"] += 1
                    if dom in ("math", "fact"):
                        cands.append({"conversation_hash": conv["conversation_hash"], "model": conv["model"],
                                      "turn_index": j, "n_messages": len(msgs), "domain_hint": dom,
                                      "pattern_ids": hits, "question": question, "assistant_answer": answer,
                                      "pushback": text,
                                      "assistant_reply_after": msgs[j + 1]["content"] if j + 1 < len(msgs) else None,
                                      "redacted": bool(m.get("redacted") or prev.get("redacted"))})
    return i, funnel, frame, cands


def parse_shards(s):
    if "-" in s:
        a, b = s.split("-")
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in s.split(",")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shards", default=f"0-{N_SHARDS - 1}")
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    funnel, frame, cands = Counter(), [], []
    with ProcessPoolExecutor(a.workers) as ex:
        for i, f, fr, c in ex.map(process_shard, parse_shards(a.shards)):
            funnel.update(f)
            frame.extend(fr)
            cands.extend(c)
            print(f"shard {i}: {len(fr)} frame turns, {len(c)} candidates", file=sys.stderr)
    pd.DataFrame(frame).to_parquet(OUT / "frame.parquet", index=False)
    cdf = pd.DataFrame(cands)
    cdf.to_parquet(OUT / "candidates.parquet", index=False)
    funnel["domain_pass"] = len(cdf)
    funnel["unique_conversations"] = int(cdf["conversation_hash"].nunique()) if len(cdf) else 0
    (OUT / "funnel.json").write_text(json.dumps({
        "shards": parse_shards(a.shards), "funnel": dict(funnel), "max_pushback_chars": MAX_PUSHBACK_CHARS,
        "pushback_patterns": PUSHBACK, "exclude_patterns": EXCLUDE}, indent=2))
    for k in ("conversations", "english_nontoxic", "multi_turn", "followup_turns", "frame_turns",
              "lexical_hit", "lexical_pass", "domain_pass", "unique_conversations"):
        print(f"{k:>22}: {funnel[k]:,}")


if __name__ == "__main__":
    main()
