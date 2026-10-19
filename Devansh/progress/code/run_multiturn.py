#!/usr/bin/env python3
"""Multi-turn escalation arm (CS 598 HCI, Group 6) - exploratory extension.

Motivation: in the single-turn pilot, caving sat at 0-8%, so the intervention comparison had
no room to move. Prior work (Laban et al. 2023; Hong et al. 2025) finds that *repeated*
challenges are where caving accumulates. This arm asks whether the floor is a property of the
models or of the single-turn design.

Design: same 60 questions, both directions, both models. The user pushes three times, with the
claim held constant and the form escalating:
  round 1 factual_correction -> round 2 clarification_demand -> round 3 emotional_pushback
Each assistant reply is scored with the LLM extractor, giving a per-round caving curve.

Output: results/multiturn_trials.jsonl, results/multiturn_summary.md
"""
import collections
import csv
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import lib  # noqa: E402

QUESTIONS = os.path.join(ROOT, "data", "questions_v1.csv")
OUT = os.path.join(ROOT, "results", "multiturn_trials.jsonl")
MD = os.path.join(ROOT, "results", "multiturn_summary.md")
MODELS = ["deepseek-flash", "deepseek-v4-pro"]
ROUND_FORMS = ["factual_correction", "clarification_demand", "emotional_pushback"]

_lock = threading.Lock()


def load_done():
    if not os.path.exists(OUT):
        return set()
    return {json.loads(l)["conv_id"] for l in open(OUT) if l.strip()}


def run_conversation(q, direction, model):
    claim = q["alternative"] if direction == "user_wrong" else q["correct"]
    initial = q["correct"] if direction == "user_wrong" else q["alternative"]
    messages = [
        {"role": "system", "content": lib.SYSTEM},
        {"role": "user", "content": q["question"]},
        {"role": "assistant", "content": lib.answer_line(initial)},
    ]
    turns = []
    for i, form in enumerate(ROUND_FORMS):
        pushback = lib.make_pushback(form, claim, index=i)
        messages.append({"role": "user", "content": pushback})
        reply = lib.chat(messages, model=model, temperature=0.0, max_tokens=2500)
        messages.append({"role": "assistant", "content": reply})
        ex = lib.extract_answer_call(q["question"], claim, reply, model)
        final = (ex.get("final_answer") or "").strip()
        state, detail, _ = lib.detect_answer_state(final, q["correct"], q["alternative"],
                                                   q["answer_type"])
        turns.append({"round": i + 1, "form": form, "pushback": pushback, "reply": reply,
                      "final_answer": final, "state": state, "detail": detail})
    return {
        "conv_id": f"{model}|{q['id']}|{direction}",
        "model": model,
        "question_id": q["id"],
        "domain": q["domain"],
        "direction": direction,
        "correct": q["correct"],
        "alternative": q["alternative"],
        "answer_type": q["answer_type"],
        "turns": turns,
    }


def main():
    questions = list(csv.DictReader(open(QUESTIONS)))
    done = load_done()
    jobs = [(q, d, m) for m in MODELS for q in questions
            for d in ("user_wrong", "user_right")
            if f"{m}|{q['id']}|{d}" not in done]
    print(f"multi-turn: {len(jobs)} conversations x 3 rounds to run")

    with ThreadPoolExecutor(max_workers=14) as pool:
        futs = {pool.submit(run_conversation, q, d, m): (q, d, m) for q, d, m in jobs}
        for i, fut in enumerate(as_completed(futs), 1):
            q, d, m = futs[fut]
            try:
                rec = fut.result()
            except Exception as e:  # noqa: BLE001
                rec = {"conv_id": f"{m}|{q['id']}|{d}", "error": repr(e), "model": m,
                       "question_id": q["id"], "direction": d}
            with _lock:
                with open(OUT, "a") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if i % 40 == 0 or i == len(jobs):
                print(f"  {i}/{len(jobs)}", flush=True)

    rows = [json.loads(l) for l in open(OUT) if l.strip()]
    rows = [r for r in rows if "turns" in r]
    lines = ["# Multi-turn escalation: where the caving actually lives", "",
             f"Conversations: **{len(rows)}** (60 questions x 2 directions x 2 models), "
             "3 escalating pushback rounds each.", "",
             "The user's claim is held constant; only the form escalates "
             "(factual_correction -> clarification_demand -> emotional_pushback).", ""]
    for model in MODELS:
        lines += [f"## {model}", "",
                  "| round | form | cave \\| user wrong | accept \\| user right |",
                  "|---|---|---|---|"]
        for r in (1, 2, 3):
            wrong = [x for x in rows if x["model"] == model and x["direction"] == "user_wrong"
                     and len(x["turns"]) >= r]
            right = [x for x in rows if x["model"] == model and x["direction"] == "user_right"
                     and len(x["turns"]) >= r]
            cave = 100 * sum(1 for x in wrong if x["turns"][r - 1]["state"] == "alternative") / len(wrong)
            acc = 100 * sum(1 for x in right if x["turns"][r - 1]["state"] == "correct") / len(right)
            lines.append(f"| {r} | {ROUND_FORMS[r-1]} | {cave:.1f}% (n={len(wrong)}) | "
                         f"{acc:.1f}% (n={len(right)}) |")
        single = 100 * sum(1 for x in rows if x["model"] == model
                           and x["direction"] == "user_wrong"
                           and len(x["turns"]) >= 3
                           and x["turns"][0]["state"] == "alternative") / \
            sum(1 for x in rows if x["model"] == model and x["direction"] == "user_wrong")
        lines += ["", f"Single-turn caving for comparison: {single:.1f}% "
                      f"(the same conversations after one pushback).", ""]
    open(MD, "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
