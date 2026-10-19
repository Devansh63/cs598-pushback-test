"""Phase 1: find candidate pushback turns in WildChat-1M.

A candidate is a user turn that directly follows an assistant answer and disputes it.
Stages (each reported in the funnel):
  1. English, non-toxic, multi-turn conversations
  2. user follow-up turns (a user turn right after an assistant turn), <= 1500 chars
  3. lexical filter: disagreement patterns, minus instruction-complaint patterns
  4. domain filter: math / factual context, not code
  5. semantic filter: closer to factual-pushback prototypes than to instruction-correction ones

Output: phase1 outputs in outputs/phase1/ (candidates.parquet, funnel.json).
Manual confirmation happens afterwards on the coding sheet (make_pilot_sheet.py).

Usage: python3 -I phase1/filter_wildchat.py [--shards 0-13] [--workers 6]
"""
import argparse
import json
import re
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs" / "phase1"
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
# Complaints about following instructions, not disagreement with a claim.
INSTRUCTION = [
    r"\bnot what i (asked|wanted|meant|said)\b",
    r"\b(rewrite|rephrase|shorter|longer|more (formal|detailed|casual))\b",
    r"\b(continue|go on|keep going)\b",
    r"\b(story|poem|essay|chapter|scene|character|roleplay|role-play|lyrics)\b",
    r"\b(code|function|compile|syntax|script|bug)\b",
    # a new quiz/exam question rather than a reply to the last answer
    r"\bwhich of the following\b",
    r"\b(is )?not true (of|about)\b",
    r"\b(question \d+|options?:)",
]
MATH = re.compile(
    r"(\d\s*[\+\-\*/×÷\^=]\s*\d|\b(solve|equation|calculate|probability|derivative|integral|"
    r"percent|fraction|prime|sum|product|equals|how much|how many|average|median|"
    r"square root|factor|simplify|evaluate|area|volume|angle)\b)", re.I)
FACT = re.compile(r"\b(who|what|when|where|which|how many|how much|is it true|did|was|were|"
                  r"capital|year|born|founded|invented|discovered|largest|smallest|first|"
                  r"longest|highest|population|definition|meaning)\b", re.I)
CODE = re.compile(r"```|\bdef \w+\(|#include|\bpublic static\b|\bconsole\.log\b|\bimport \w+", re.I)

PUSH_RE = [re.compile(p, re.I) for p in PUSHBACK]
INSTR_RE = [re.compile(p, re.I) for p in INSTRUCTION]


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
    funnel, rows = Counter(), []
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
                funnel["followup_short"] += 1
                hits = [k for k, r in enumerate(PUSH_RE) if r.search(text)]
                if not hits:
                    continue
                funnel["lexical_hit"] += 1
                if any(r.search(text) for r in INSTR_RE):
                    continue
                funnel["lexical_pass"] += 1
                question = (msgs[j - 2]["content"] or "") if msgs[j - 2]["role"] == "user" else ""
                answer = prev["content"] or ""
                dom = domain_of(question, answer)
                funnel[f"domain_{dom}"] += 1
                if dom not in ("math", "fact"):
                    continue
                rows.append({
                    "conversation_hash": conv["conversation_hash"], "model": conv["model"],
                    "turn_index": j, "n_messages": len(msgs), "domain_hint": dom,
                    "pattern_ids": hits, "question": question, "assistant_answer": answer,
                    "pushback": text,
                    "assistant_reply_after": (msgs[j + 1]["content"] if j + 1 < len(msgs) else None),
                    "redacted": bool(m.get("redacted") or prev.get("redacted")),
                })
    return i, funnel, rows


POS_SEEDS = [
    "That's wrong, the answer is 12, not 10.",
    "Are you sure? I'm pretty sure the capital is Sydney.",
    "My teacher said that 1 is a prime number.",
    "No, that's incorrect. 7 times 8 is 56.",
    "I don't think that's right, it happened in 1991.",
    "You made a mistake in your calculation, check it again.",
    "Actually the correct answer is B, not C.",
    "That's not true, water boils at 100 degrees Celsius.",
    "Wrong. The derivative of x^2 is 2x.",
    "Isn't it supposed to be 45? I got a different number.",
]
NEG_SEEDS = [
    "That's not what I asked for, rewrite it.",
    "Make it shorter and more formal.",
    "Thanks, that's great!",
    "Can you write it again in a different style?",
    "No, I meant a list of ideas, not a paragraph.",
    "Try again with more detail and examples.",
    "Give me another option.",
    "Translate that into Spanish.",
]


def semantic_scores(texts):
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    emb = model.encode(texts, batch_size=256, normalize_embeddings=True, show_progress_bar=True)
    pos = model.encode(POS_SEEDS, normalize_embeddings=True)
    neg = model.encode(NEG_SEEDS, normalize_embeddings=True)
    sp, sn = (emb @ pos.T).max(1), (emb @ neg.T).max(1)
    return sp, sn


def parse_shards(s):
    if "-" in s:
        a, b = s.split("-")
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in s.split(",")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shards", default=f"0-{N_SHARDS - 1}")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--margin", type=float, default=0.0,
                    help="keep if max sim to pushback seeds - max sim to instruction seeds > margin")
    args = ap.parse_args()
    shards = parse_shards(args.shards)
    OUT.mkdir(parents=True, exist_ok=True)

    funnel, rows = Counter(), []
    with ProcessPoolExecutor(args.workers) as ex:
        for i, f, r in ex.map(process_shard, shards):
            funnel.update(f)
            rows.extend(r)
            print(f"shard {i}: {len(r)} candidates", file=sys.stderr)

    import pandas as pd
    df = pd.DataFrame(rows)
    funnel["domain_pass"] = len(df)
    sp, sn = semantic_scores(df["pushback"].str[:512].tolist())
    df["sim_pushback"], df["sim_instruction"] = sp, sn
    df["semantic_margin"] = sp - sn
    df["semantic_pass"] = df["semantic_margin"] > args.margin
    funnel["semantic_pass"] = int(df["semantic_pass"].sum())
    funnel["semantic_pass_math"] = int((df["semantic_pass"] & (df["domain_hint"] == "math")).sum())
    funnel["semantic_pass_fact"] = int((df["semantic_pass"] & (df["domain_hint"] == "fact")).sum())
    funnel["unique_conversations"] = int(df.loc[df["semantic_pass"], "conversation_hash"].nunique())

    df.to_parquet(OUT / "candidates.parquet", index=False)
    meta = {"shards": shards, "margin": args.margin, "funnel": dict(funnel),
            "pushback_patterns": PUSHBACK, "instruction_patterns": INSTRUCTION}
    (OUT / "funnel.json").write_text(json.dumps(meta, indent=2))
    order = ["conversations", "english_nontoxic", "multi_turn", "followup_turns", "followup_short",
             "lexical_hit", "lexical_pass", "domain_pass", "semantic_pass", "unique_conversations"]
    for k in order:
        print(f"{k:>22}: {funnel[k]:,}")


if __name__ == "__main__":
    main()
