#!/usr/bin/env python3
"""Validate the automatic answer-state detector (CS 598 HCI, Group 6).

The primary metrics depend on knowing which answer a reply commits to. The harness assigns
this automatically (assertion-cue scoring) and escalates ambiguous cases to an LLM extractor.
This script measures the reliability of the automatic rule: on a random sample of trials the
rule handled *without* escalation, ask the extractor independently and compare.

Agreement here is between two instruments, not against human labels; it bounds, but does not
eliminate, measurement error. A human spot-check of disagreements is the next step (and is
recorded as such in the progress log).

Output: results/state_validation.md
"""
import collections
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import lib  # noqa: E402

TRIALS = os.path.join(ROOT, "results", "trials.jsonl")
MD = os.path.join(ROOT, "results", "state_validation.md")
N = 120


def main():
    rows = [json.loads(l) for l in open(TRIALS) if l.strip()]
    import csv
    qmap = {q["id"]: q["question"] for q in
            csv.DictReader(open(os.path.join(ROOT, "data", "questions_v1.csv")))}
    auto = [r for r in rows if r.get("state_method") == "auto" and r.get("response")]
    sample = random.Random(11).sample(auto, min(N, len(auto)))
    agree = 0
    checked = 0
    disagreements = []
    for r in sample:
        ex = lib.extract_answer_call(qmap[r["question_id"]], r["claim"], r["response"], r["model"])
        final = (ex.get("final_answer") or "").strip()
        if not final:
            continue
        state, _, _ = lib.detect_answer_state(final, r["correct"], r["alternative"],
                                              r["answer_type"])
        checked += 1
        if state == r["answer_state"]:
            agree += 1
        else:
            disagreements.append({"trial_id": r["trial_id"], "auto": r["answer_state"],
                                  "extracted": state, "final": final[:160],
                                  "response": r["response"][:400]})
    lo, hi = lib.wilson(agree, checked)
    lines = ["# Automatic answer-state detector: reliability check", "",
             f"Sampled {checked} trials that the automatic rule handled without escalation "
             f"(of {len(auto)} such trials).", "",
             f"- agreement with the independent LLM extractor: **{agree}/{checked} = "
             f"{100*agree/checked:.1f}%** [{lo:.0f}, {hi:.0f}]", "",
             "Disagreements are listed below for human adjudication; until they are adjudicated, "
             "the primary rates carry this measurement error.", ""]
    if disagreements:
        lines += ["| trial | auto | extracted | extractor's final answer |", "|---|---|---|---|"]
        for d in disagreements[:20]:
            lines.append(f"| {d['trial_id']} | {d['auto']} | {d['extracted']} | "
                         f"{d['final'].replace('|', '/')[:80]} |")
    else:
        lines.append("No disagreements in the sample.")
    open(MD, "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))
    with open(os.path.join(ROOT, "results", "state_validation.jsonl"), "w") as f:
        for d in disagreements:
            f.write(json.dumps(d) + "\n")


if __name__ == "__main__":
    main()
