#!/usr/bin/env python3
"""Draw the labeling sample and classify it with DeepSeek.

Inputs : pairs_expanded.jsonl (from build_pairs.py)
Outputs: label_sample.jsonl, judged.jsonl

Design:
  - 150 random cue-matched candidates + 150 random non-candidates, seed 13.
  - Each user turn is classified against the immediately preceding assistant turn
    with a strict 4-way rubric; the model returns JSON {label, reason}.
  - Results are written incrementally, so rerunning resumes rather than repeats.

Usage: python3 label_sample.py [--limit N]
"""
import argparse
import hashlib
import json
import os
import random
import re
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAIRS = HERE / "pairs_expanded.jsonl"
SAMPLE = HERE / "label_sample.jsonl"
JUDGED = HERE / "judged.jsonl"

SEED = 13
N_PER_STRATUM = 150
WORKERS = 8
MAX_ASSISTANT_CHARS = 12_000
MAX_USER_CHARS = 6_000
LABELS = {"pushback_disagreement", "neutral_question", "preference_change", "other"}
API = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-flash"

SYSTEM = (
    "You are a careful annotator in an HCI study of user pushback in chatbot "
    "conversations. Apply the rubric exactly. Return only a JSON object."
)

RUBRIC = """RUBRIC
You will read one ASSISTANT TURN followed by the USER TURN that comes immediately after it.
Classify ONLY the user turn by its relation to the assistant turn shown.

pushback_disagreement: The user disputes, corrects, or challenges the substantive content of
the assistant's preceding answer. This includes saying the answer is wrong, correcting a fact,
number, calculation, or recommendation, rejecting a claim, or insisting the assistant made an
error about the topic. The user does not need to use the word "wrong".

neutral_question: The user asks a follow-up question that merely seeks more detail,
clarification, or explanation, without asserting that the assistant was wrong.

preference_change: The user asks to change the format, length, style, tone, or presentation
(for example "make it shorter", "use bullet points", "answer in English"), not the substance
of the answer.

other: Anything else: a new topic, a fresh task instruction, a greeting, an unrelated request,
or a turn that cannot be judged from the context.

Decision rules:
- If the user both asks for more detail and asserts an error, choose pushback_disagreement.
- "Are you sure?" is pushback_disagreement only if it challenges the answer's correctness;
  if it merely asks for reassurance or elaboration, choose neutral_question.
- Format/length/style requests are preference_change even when phrased as a correction.
- Judge only the relation of the user turn to the assistant turn shown.

ASSISTANT TURN:
<<<
{assistant}
>>>

USER TURN:
<<<
{user}
>>>

Return exactly this JSON shape:
{{"label": "pushback_disagreement" | "neutral_question" | "preference_change" | "other", "reason": "short reason, at most 25 words"}}
"""


def clip(text: str, limit: int) -> tuple[str, bool]:
    if len(text) <= limit:
        return text, False
    return text[:limit] + "\n[... truncated ...]", True


def make_prompt(pair: dict) -> tuple[str, bool, bool, str, str]:
    a, at = clip(pair["assistant_text"], MAX_ASSISTANT_CHARS)
    u, ut = clip(pair["user_text"], MAX_USER_CHARS)
    return RUBRIC.format(assistant=a, user=u), at, ut, a, u


def call_model(prompt: str, timeout: int = 180) -> dict:
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY is not set")
    body = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    payload = json.dumps(body, ensure_ascii=False)

    def post(p: str) -> tuple[int, str]:
        cp = subprocess.run(
            [
                "curl", "-sS", "--max-time", str(timeout),
                "-X", "POST", API,
                "-H", "Content-Type: application/json",
                "-H", f"Authorization: Bearer {key}",
                "--data-binary", "@-",
                "-w", "\n%{http_code}",
            ],
            input=p, capture_output=True, text=True, timeout=timeout + 30,
        )
        raw, _, code = cp.stdout.rpartition("\n")
        return int(code.strip() or 0), raw

    code, raw = post(payload)
    if code == 400 and "response_format" in raw:
        body.pop("response_format", None)
        payload = json.dumps(body, ensure_ascii=False)
        code, raw = post(payload)
    if code != 200:
        raise RuntimeError(f"HTTP {code}: {raw[:300]}")
    data = json.loads(raw)
    choice = data["choices"][0]["message"]["content"]
    usage = data.get("usage") or {}
    return {
        "content": choice,
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
    }


def parse_label(content: str) -> tuple[str | None, str | None]:
    text = content.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            return None, None
        try:
            obj = json.loads(m.group(0))
        except json.JSONDecodeError:
            return None, None
    label = obj.get("label")
    reason = obj.get("reason")
    if label not in LABELS:
        return None, reason
    return label, reason


def pair_id(p: dict) -> str:
    raw = f"{p['row_idx']}:{p['turn_idx']}:{p['assistant_text'][:80]}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="classify only the first N sampled pairs")
    args = ap.parse_args()

    pairs = [json.loads(line) for line in PAIRS.open(encoding="utf-8")]
    cand = [p for p in pairs if p["cue_match"]]
    non = [p for p in pairs if not p["cue_match"]]
    rng = random.Random(SEED)
    cand_sample = rng.sample(cand, min(N_PER_STRATUM, len(cand)))
    non_sample = rng.sample(non, min(N_PER_STRATUM, len(non)))

    rows = []
    for p in cand_sample:
        rows.append({"stratum": "candidate", **p})
    for p in non_sample:
        rows.append({"stratum": "non_candidate", **p})
    for r in rows:
        r["pair_id"] = pair_id(r)
        r["sample_weight"] = (
            len(cand) / len(cand_sample) if r["stratum"] == "candidate"
            else len(non) / len(non_sample)
        )
        r["cue_match"] = r["stratum"] == "candidate"

    with SAMPLE.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"sample: {len(cand_sample)} candidates from {len(cand)}, "
          f"{len(non_sample)} non-candidates from {len(non)}, seed={SEED}")

    done = set()
    if JUDGED.exists():
        for line in JUDGED.open(encoding="utf-8"):
            try:
                done.add(json.loads(line)["pair_id"])
            except Exception:  # noqa: BLE001
                pass
    todo = [r for r in rows if r["pair_id"] not in done]
    if args.limit:
        todo = todo[: args.limit]
    print(f"judging {len(todo)} pairs ({len(done)} already done), workers={WORKERS}")

    lock = threading.Lock()
    calls = 0

    def work(r: dict) -> dict:
        prompt, at, ut, a, u = make_prompt(r)
        last_err = None
        for attempt in range(3):
            try:
                res = call_model(prompt)
                label, reason = parse_label(res["content"])
                if label is None and attempt < 1:
                    # one corrective retry for malformed output
                    res = call_model(prompt + "\nReturn only the JSON object, no prose.")
                    label, reason = parse_label(res["content"])
                return {
                    "pair_id": r["pair_id"],
                    "stratum": r["stratum"],
                    "sample_weight": r["sample_weight"],
                    "cue_match": r["cue_match"],
                    "conv_id": r["conv_id"],
                    "row_idx": r["row_idx"],
                    "turn_idx": r["turn_idx"],
                    "label": label,
                    "reason": reason,
                    "model": MODEL,
                    "prompt_tokens": res.get("prompt_tokens"),
                    "completion_tokens": res.get("completion_tokens"),
                    "parse_ok": label is not None,
                    "assistant_truncated": at,
                    "user_truncated": ut,
                    "assistant_text": a,
                    "user_text": u,
                    "raw_content": (res.get("content") or "")[:1200],
                }
            except Exception as e:  # noqa: BLE001
                last_err = e
                time.sleep(min(2 ** attempt, 8))
        return {
            "pair_id": r["pair_id"], "stratum": r["stratum"],
            "sample_weight": r["sample_weight"],
            "cue_match": r["cue_match"], "conv_id": r["conv_id"],
            "row_idx": r["row_idx"], "turn_idx": r["turn_idx"],
            "label": None, "reason": None, "model": MODEL,
            "prompt_tokens": None, "completion_tokens": None,
            "parse_ok": False, "error": str(last_err)[:300],
            "assistant_truncated": None, "user_truncated": None,
            "assistant_text": r["assistant_text"][:MAX_ASSISTANT_CHARS],
            "user_text": r["user_text"][:MAX_USER_CHARS],
            "raw_content": "",
        }

    with JUDGED.open("a", encoding="utf-8") as out, ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futures = {ex.submit(work, r): r for r in todo}
        for fut in as_completed(futures):
            rec = fut.result()
            with lock:
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                out.flush()
                calls += 1
                if calls % 25 == 0:
                    print(f"  judged {calls}/{len(todo)}", flush=True)

    # stable order for audit
    recs = [json.loads(line) for line in JUDGED.open(encoding="utf-8")]
    seen = {}
    for rec in recs:
        seen[rec["pair_id"]] = rec
    with JUDGED.open("w", encoding="utf-8") as f:
        for pid in sorted(seen):
            f.write(json.dumps(seen[pid], ensure_ascii=False) + "\n")
    print(f"judged.jsonl now has {len(seen)} unique records")


if __name__ == "__main__":
    main()
