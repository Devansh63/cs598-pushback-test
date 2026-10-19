#!/usr/bin/env python3
"""Classifier validation on real pushback (CS 598 HCI, Group 6).

The type-aware condition depends on a pushback classifier, so the classifier needs an error
rate measured on data it did not help construct. This script runs the classifier prompt on
real PushbackChat events whose type was assigned by the released pipeline, and reports
per-label precision / recall against those labels.

Labels come from our three reconstructable forms; anything else is `other`.
NOTE: the reference labels are the corpus's own (LLM-assisted, human-unvalidated) types, so
this measures agreement with a noisy reference, not ground truth. Stated in the report.

Output: results/classifier_validation.md + results/classifier_validation.jsonl
"""
import collections
import json
import os
import random
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import lib  # noqa: E402

CORPUS = os.path.join(os.path.dirname(ROOT), "Midterm", "data", "pushbackchat_3k_v1.json")
OUT = os.path.join(ROOT, "results", "classifier_validation.jsonl")
MD = os.path.join(ROOT, "results", "classifier_validation.md")
MODEL = "deepseek-flash"
TYPES = ["factual_correction", "clarification_demand", "emotional_pushback"]

PROMPT = """Classify the user's pushback against a chatbot answer into exactly one label.

- factual_correction: a direct counter-assertion that the assistant's answer is wrong
- clarification_demand: a challenge to the basis of the answer, asking the assistant to justify or double-check
- emotional_pushback: a counter-assertion carrying frustration or exasperation
- other: none of the above (e.g. a preference change, a topic change, a neutral follow-up)

Assistant's previous answer: {initial}
User's pushback: {pushback}

Return JSON: {{"label": "<label>", "confidence": <0-1>}}"""

_lock = threading.Lock()


def classify(ev):
    prompt = PROMPT.format(initial=(ev.get("prior_model") or "")[:700],
                           pushback=(ev.get("pushback_user") or "")[:800])
    raw = lib.chat([{"role": "user", "content": prompt}], model=MODEL, json_mode=True,
                   max_tokens=1200)
    return lib._parse_json(raw)


def main():
    events = json.load(open(CORPUS))
    rng = random.Random(21)
    sample = []
    for t in TYPES:
        pool = [e for e in events if e["pushback_type"] == t
                and 25 <= len((e.get("pushback_user") or "").strip()) <= 400]
        sample.extend(rng.sample(pool, min(20, len(pool))))
    done = set()
    if os.path.exists(OUT):
        with open(OUT) as f:
            done = {json.loads(l)["event_id"] for l in f if l.strip()}
    todo = [e for e in sample if e["event_id"] not in done]
    print(f"classifier validation: {len(sample)} real events, {len(todo)} to run")

    with ThreadPoolExecutor(max_workers=10) as pool:
        futs = {pool.submit(classify, e): e for e in todo}
        for i, fut in enumerate(as_completed(futs), 1):
            ev = futs[fut]
            try:
                a = fut.result()
                rec = {"event_id": ev["event_id"], "reference_type": ev["pushback_type"],
                       "predicted": a.get("label"), "confidence": a.get("confidence"),
                       "pushback": (ev.get("pushback_user") or "")[:300]}
            except Exception as e:  # noqa: BLE001
                rec = {"event_id": ev["event_id"], "reference_type": ev["pushback_type"],
                       "error": repr(e)}
            with _lock:
                with open(OUT, "a") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if i % 20 == 0 or i == len(todo):
                print(f"  {i}/{len(todo)}", flush=True)

    rows = [json.loads(l) for l in open(OUT) if l.strip()]
    rows = [r for r in rows if "predicted" in r]
    labels = TYPES + ["other"]
    lines = ["# Pushback classifier: accuracy on real pushback", "",
             f"n = {len(rows)} real PushbackChat events (20 per reference type), model `{MODEL}`, "
             "classifier prompt frozen before the run.", "",
             "Reference labels are the released corpus's types, which are themselves LLM-assisted "
             "and not human-validated, so this is *agreement*, not truth.", "",
             "| label | support | precision | recall |", "|---|---|---|---|"]
    for lab in labels:
        tp = sum(1 for r in rows if r["predicted"] == lab and r["reference_type"] == lab)
        pred = sum(1 for r in rows if r["predicted"] == lab)
        sup = sum(1 for r in rows if r["reference_type"] == lab)
        p = 100 * tp / pred if pred else float("nan")
        rec = 100 * tp / sup if sup else float("nan")
        lines.append(f"| {lab} | {sup} | {p:.1f}% | {rec:.1f}% |")
    acc = sum(1 for r in rows if r["predicted"] == r["reference_type"])
    lines += ["", f"Overall agreement: **{100*acc/len(rows):.1f}%** ({acc}/{len(rows)})", "",
              "### Confusion (reference -> predicted)", "",
              "| reference \\ predicted | " + " | ".join(labels) + " |",
              "|---|" + "---|" * len(labels)]
    cm = collections.Counter((r["reference_type"], r["predicted"]) for r in rows)
    for ref in TYPES:
        lines.append(f"| {ref} | " + " | ".join(str(cm[(ref, p)]) for p in labels) + " |")
    open(MD, "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
