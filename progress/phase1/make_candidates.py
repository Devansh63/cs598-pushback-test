#!/usr/bin/env python3
"""Write the auditable candidate corpus with light PII/secret redaction.

Inputs : pairs_expanded.jsonl, samples_expanded.jsonl
Output : candidates.jsonl (<= 300 records)

Each record keeps the assistant turn, the user turn, and (when available) the
preceding user turn as context. Emails, filesystem paths, and API-key-like
strings are replaced with <EMAIL>, <PATH>, <KEY>.
"""
import json
import random
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAIRS = HERE / "pairs_expanded.jsonl"
SAMPLES = HERE / "samples_frame.jsonl"
OUT = HERE / "candidates.jsonl"
CAP = 300
SEED = 13

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
PATH_RES = [
    re.compile(r"(?:/Users|/home|/var|/tmp|/etc|/opt|/mnt|/root|/private|/Volumes)/[^\s\"'<>)\]]*"),
    re.compile(r"[A-Za-z]:\\\\[^\s\"'<>)\]]*"),
    re.compile(r"~\/[^\s\"'<>)\]]*"),
]
KEY_RES = [
    re.compile(r"\bsk-[A-Za-z0-9_\-]{16,}\b"),
    re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}\b"),
    re.compile(r"(?i)\b(?:api[_-]?key|secret|access[_-]?token|auth[_-]?token)\b\s*[:=]\s*[^\s,;\"']{8,}"),
    re.compile(r"\b[A-Fa-f0-9]{40,}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
]


def redact(text: str) -> str:
    if not text:
        return text
    for rx in KEY_RES:
        text = rx.sub("<KEY>", text)
    for rx in PATH_RES:
        text = rx.sub("<PATH>", text)
    text = EMAIL_RE.sub("<EMAIL>", text)
    return text


def main() -> None:
    pairs = [json.loads(line) for line in PAIRS.open(encoding="utf-8")]
    cand = [p for p in pairs if p["cue_match"]]
    if len(cand) > CAP:
        cand = random.Random(SEED).sample(cand, CAP)
    cand.sort(key=lambda p: (p["row_idx"], p["turn_idx"]))

    convs = {}
    if SAMPLES.exists():
        for line in SAMPLES.open(encoding="utf-8"):
            r = json.loads(line)
            if r.get("conversation"):
                convs[r["row_idx"]] = r["conversation"]

    with OUT.open("w", encoding="utf-8") as f:
        for p in cand:
            context = []
            conv = convs.get(p["row_idx"])
            if conv and 0 < p["turn_idx"] <= len(conv):
                prev = conv[p["turn_idx"] - 1]
                context = [{
                    "role": prev.get("role"),
                    "content": redact((prev.get("content") or "")[:4000]),
                }]
            rec = {
                "conv_id": p["conv_id"],
                "row_idx": p["row_idx"],
                "turn_idx": p["turn_idx"],
                "language": p["language"],
                "matched_cues": p["matched_cues"],
                "context": context,
                "assistant_text": redact(p["assistant_text"]),
                "user_text": redact(p["user_text"]),
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"wrote {len(cand)} candidate records to {OUT}")


if __name__ == "__main__":
    main()
