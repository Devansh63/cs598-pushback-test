#!/usr/bin/env python3
"""Re-derive the final answer for every trial with the LLM extractor (CS 598 HCI, Group 6).

Why: the automatic detector and the extractor disagreed on 8.3% of a validation sample, and
the disagreements were mostly number-word answers ("six sides") and multi-term arithmetic
("5! - 4! = 120 - 24 = 96"). Reading them showed the extractor was right and the detector
was wrong, so the primary state is re-derived here for every trial. The automatic label is
kept for comparison.

Output: results/state_labels.jsonl (resumable) and results/state_relabel_report.md
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

TRIALS = os.path.join(ROOT, "results", "trials.jsonl")
OUT = os.path.join(ROOT, "results", "state_labels.jsonl")
REPORT = os.path.join(ROOT, "results", "state_relabel_report.md")

_lock = threading.Lock()


def load_labels():
    if not os.path.exists(OUT):
        return {}
    out = {}
    with open(OUT) as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                out[r["trial_id"]] = r
    return out


def main():
    rows = {}
    with open(TRIALS) as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            if "error" in r or not r.get("response"):
                continue
            rows[r["trial_id"]] = r
    qmap = {q["id"]: q["question"] for q in
            csv.DictReader(open(os.path.join(ROOT, "data", "questions_v1.csv")))}
    done = load_labels()
    todo = [r for tid, r in rows.items() if tid not in done]
    print(f"{len(rows)} trials, {len(todo)} to re-label")

    def work(r):
        ex = lib.extract_answer_call(qmap[r["question_id"]], r["claim"], r["response"], r["model"])
        final = (ex.get("final_answer") or "").strip()
        state, detail, ambiguous = lib.detect_answer_state(
            final, r["correct"], r["alternative"], r["answer_type"])
        return {"trial_id": r["trial_id"], "final_answer": final, "derived_state": state,
                "detail": detail, "ambiguous": ambiguous, "raw": ex.get("_raw")}

    with ThreadPoolExecutor(max_workers=12) as pool:
        futs = {pool.submit(work, r): r for r in todo}
        for i, fut in enumerate(as_completed(futs), 1):
            r = futs[fut]
            try:
                rec = fut.result()
            except Exception as e:  # noqa: BLE001
                rec = {"trial_id": r["trial_id"], "error": repr(e)}
            with _lock:
                with open(OUT, "a") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if i % 100 == 0 or i == len(todo):
                print(f"  {i}/{len(todo)}", flush=True)

    # report agreement between instruments
    labels = load_labels()
    pairs = []
    for tid, r in rows.items():
        lab = labels.get(tid)
        if not lab or "derived_state" not in lab:
            continue
        pairs.append((r["answer_state"], lab["derived_state"], r))
    agree = sum(1 for a, b, _ in pairs if a == b)
    lo, hi = lib.wilson(agree, len(pairs))
    by_prev = collections.Counter((a, b) for a, b, _ in pairs)
    lines = ["# Re-derived answer states", "",
             f"Trials re-labelled with the extractor: {len(pairs)}",
             f"Agreement with the original label: **{agree}/{len(pairs)} = "
             f"{100*agree/len(pairs):.1f}%** [{lo:.0f}, {hi:.0f}]", "",
             "| original | re-derived | n |", "|---|---|---|"]
    for (a, b), n in by_prev.most_common():
        if a != b:
            lines.append(f"| {a} | {b} | {n} |")
    lines += ["", "The re-derived state is used in the analysis; the original label is retained "
                  "in the trial log for audit.", ""]
    open(REPORT, "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
