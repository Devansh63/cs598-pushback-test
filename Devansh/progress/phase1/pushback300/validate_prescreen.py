#!/usr/bin/env python3
"""Validate the AI prescreen in `pushback_300` (CS 598 HCI, Group 6).

All 300 cases carry "AI is_pushback: yes", produced by a different pipeline we cannot inspect.
Before treating the set as pushback, measure how often that screen is right.

Samples N cases, asks an independent judge with a strict 4-label rubric, and reports precision
with a Wilson interval. False positives are listed by event_id (no text in the committed file).

Outputs:
  data_local/prescreen_judged.jsonl   local, contains conversation text
  results/prescreen_validation.md     committed aggregates
"""
import argparse
import json
import os
import random
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "code"))
import lib  # noqa: E402

DATA = os.path.join(HERE, "data_local")
RESULTS = os.path.join(HERE, "results")
MODEL = "deepseek-flash"

PROMPT = """A user turn follows a chatbot answer. Decide whether the user turn pushes back on that answer.

Four labels:
- pushback_disagreement: the user disputes, corrects, or challenges the substantive content of the answer
- neutral_question: a follow-up asking for more detail, with no challenge
- preference_change: a request to change format, length, style, or topic
- other: acknowledgement, thanks, a new question, roleplay, or anything else

ASSISTANT ANSWER (truncated): {answer}

USER TURN: {turn}

Return JSON: {{"label": "<label>", "reason": "<short>"}}"""

_lock = threading.Lock()


def judge(case):
    prompt = PROMPT.format(answer=(case["preceding_answer"] or "")[:1500],
                           turn=(case["target_text"] or "")[:900])
    raw = lib.chat([{"role": "user", "content": prompt}], model=MODEL, json_mode=True,
                   max_tokens=1200)
    return lib._parse_json(raw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--seed", type=int, default=29)
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args()

    cases = [json.loads(l) for l in open(os.path.join(DATA, "contexts.jsonl"))]
    sample = random.Random(args.seed).sample(cases, args.n)
    print(f"judging {len(sample)} of {len(cases)} cases")

    out_path = os.path.join(DATA, "prescreen_judged.jsonl")
    done = set()
    if os.path.exists(out_path):
        done = {json.loads(l)["event_id"] for l in open(out_path) if l.strip()}
    todo = [c for c in sample if c["event_id"] not in done]

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(judge, c): c for c in todo}
        for i, fut in enumerate(as_completed(futs), 1):
            c = futs[fut]
            try:
                a = fut.result()
                rec = {"event_id": c["event_id"], "label": a.get("label"),
                       "reason": a.get("reason"), "target_text": c["target_text"]}
            except Exception as e:  # noqa: BLE001
                rec = {"event_id": c["event_id"], "error": repr(e)}
            with _lock:
                with open(out_path, "a") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if i % 25 == 0 or i == len(todo):
                print(f"  {i}/{len(todo)}", flush=True)

    rows = [json.loads(l) for l in open(out_path) if l.strip()]
    rows = [r for r in rows if r.get("label")]
    tp = [r for r in rows if r["label"] == "pushback_disagreement"]
    lo, hi = lib.wilson(len(tp), len(rows))
    import collections
    dist = collections.Counter(r["label"] for r in rows)
    fps = [r["event_id"] for r in rows if r["label"] != "pushback_disagreement"]

    lines = ["# Is the `pushback_300` prescreen reliable?", "",
             f"Sample: **{len(rows)}** of 300 cases, independent judge (`{MODEL}`, temperature 0), "
             "rubric shown in `validate_prescreen.py`.", "",
             f"- prescreen precision (case really is pushback): **{100*len(tp)/len(rows):.1f}%** "
             f"[{lo:.0f}, {hi:.0f}]", "",
             "| judge label | n | share |", "|---|---|---|"]
    for lab, n in dist.most_common():
        lines.append(f"| {lab} | {n} | {100*n/len(rows):.1f}% |")
    lines += ["", f"Event ids of non-confirmed cases ({len(fps)}): " + ", ".join(f"`{e}`" for e in fps[:25])
              + ("" if len(fps) <= 25 else f" … (+{len(fps)-25})"), "",
              "**Caveat.** This is agreement between two LLM judges, not against human labels. "
              "It bounds how much the prescreen could be wrong; it does not settle it. Human "
              "adjudication of the flagged cases is still required before any rate is reported.", ""]
    open(os.path.join(RESULTS, "prescreen_validation.md"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
