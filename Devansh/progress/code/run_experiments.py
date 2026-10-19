#!/usr/bin/env python3
"""Run the Phase 2 / Phase 3 pilot (CS 598 HCI, Group 6).

Design mirrors the revised proposal:
  RQ2  two models x 60 questions x 2 directions x 4 pushback forms (3 reconstructed + scripted)
       -> caving rate (wrong pushback) and resistance (correct pushback)
  RQ3  one model x 3 reconstructed forms x 2 directions x 4 conditions
       none | reframe | verify_only | verify_type
       The two verification conditions consume the SAME stored verification result and differ
       only in whether the predicted pushback label + type guidance are added, so the contrast
       isolates type-aware guidance from re-verification.

Every trial is appended to a JSONL log as it completes, so the run is resumable and auditable.

Usage
  python3 run_experiments.py --limit 8                      # smoke test
  python3 run_experiments.py                                # full pilot
  python3 run_experiments.py --phases rq2 --models deepseek-flash
"""
import argparse
import hashlib
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import lib  # noqa: E402

QUESTIONS = os.path.join(ROOT, "data", "questions_v1.csv")
STIMULI = os.path.join(ROOT, "data", "stimuli_v1.jsonl")
RESULTS = os.path.join(ROOT, "results")
TRIALS = os.path.join(RESULTS, "trials.jsonl")

_write_lock = threading.Lock()
_cache_lock = threading.Lock()
_verify_cache = {}
_class_cache = {}


def load_jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def append(rec):
    with _write_lock:
        with open(TRIALS, "a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()


def trial_id(model, stim_id, condition):
    return f"{model}|{stim_id}|{condition}"


def get_verification(stim, model):
    key = (stim["stim_id"], model)
    with _cache_lock:
        if key in _verify_cache:
            return _verify_cache[key]
    v = lib.verify_call(stim["question"], stim["initial_answer"], stim["claim"], model)
    with _cache_lock:
        _verify_cache[key] = v
    return v


def get_type(stim, model):
    key = (stim["stim_id"], model)
    with _cache_lock:
        if key in _class_cache:
            return _class_cache[key]
    c = lib.classify_call(stim["initial_answer"], stim["pushback"], model)
    with _cache_lock:
        _class_cache[key] = c
    return c


def should_code_quality(stim_id, condition, rate):
    h = int(hashlib.sha256(f"{stim_id}|{condition}".encode()).hexdigest()[:8], 16)
    return (h % 1000) < int(rate * 1000)


def run_one(trial):
    stim = trial["stim"]
    model = trial["model"]
    condition = trial["condition"]
    extra = None
    verification = None
    predicted = None

    if condition in ("verify_only", "verify_type"):
        verification = get_verification(stim, model)
        if condition == "verify_type":
            c = get_type(stim, model)
            predicted = c.get("label")
            if predicted not in lib.FORM_DEFINITIONS:
                predicted = stim["intended_type"]  # classifier output unusable -> fall back
        extra = lib.system_extra(condition, verification=verification, pushback_type=predicted)
    else:
        extra = lib.system_extra(condition)

    messages = lib.trial_messages(stim["question"], stim["initial_answer"],
                                  stim["pushback"], system_extra=extra)
    response = lib.chat(messages, model=model, temperature=0.0, max_tokens=2500)
    state, detail, ambiguous = lib.detect_answer_state(
        response, stim["correct"], stim["alternative"], stim["answer_type"])
    method = "auto"
    if ambiguous or state == "neither":
        ex = lib.extract_answer_call(stim["question"], stim["claim"], response, model)
        final = (ex.get("final_answer") or "").strip()
        if final:
            state2, _, _ = lib.detect_answer_state(final, stim["correct"], stim["alternative"],
                                                   stim["answer_type"])
            if state2 != "neither":
                state, method = state2, "llm_extract"

    quality = None
    if trial.get("code_quality"):
        quality = lib.quality_call(stim["pushback"], response, model)

    return {
        "trial_id": trial_id(model, stim["stim_id"], condition),
        "phase": trial["phase"],
        "model": model,
        "condition": condition,
        "stim_id": stim["stim_id"],
        "question_id": stim["question_id"],
        "domain": stim["domain"],
        "direction": stim["direction"],
        "form": stim["form"],
        "intended_type": stim["intended_type"],
        "initial_answer": stim["initial_answer"],
        "claim": stim["claim"],
        "correct": stim["correct"],
        "alternative": stim["alternative"],
        "answer_type": stim["answer_type"],
        "pushback": stim["pushback"],
        "response": response,
        "answer_state": state,
        "state_detail": detail,
        "state_method": method,
        "verification": verification,
        "predicted_type": predicted,
        "quality": quality,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }


def build_trials(models, phases, quality_rate):
    stimuli = load_jsonl(STIMULI)
    questions = {q["id"]: q for q in load_csv(QUESTIONS)}
    trials = []
    for model in models:
        if "rq2" in phases:
            for s in stimuli:
                trials.append({"phase": "rq2", "model": model, "condition": "none", "stim": s,
                               "code_quality": should_code_quality(s["stim_id"], "none", quality_rate)})
        if "rq3" in phases and model == "deepseek-flash":
            for s in stimuli:
                if s["form"] == "scripted":
                    continue
                for cond in ("reframe", "verify_only", "verify_type"):
                    trials.append({"phase": "rq3", "model": model, "condition": cond, "stim": s,
                                   "code_quality": should_code_quality(s["stim_id"], cond, quality_rate)})
    # attach answer keys / types from the question table
    for t in trials:
        q = questions[t["stim"]["question_id"]]
        t["stim"] = dict(t["stim"])
        t["stim"]["correct"] = q["correct"]
        t["stim"]["alternative"] = q["alternative"]
        t["stim"]["answer_type"] = q["answer_type"]
    return trials


def load_csv(path):
    import csv
    with open(path) as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="deepseek-flash,deepseek-v4-pro")
    ap.add_argument("--phases", default="rq2,rq3")
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--limit", type=int, default=0, help="run only the first N trials (smoke test)")
    ap.add_argument("--quality-rate", type=float, default=0.12,
                    help="fraction of trials to code for response quality")
    ap.add_argument("--dry-run", action="store_true", help="list the plan, make no API calls")
    args = ap.parse_args()

    os.makedirs(RESULTS, exist_ok=True)
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    phases = [p.strip() for p in args.phases.split(",") if p.strip()]

    trials = build_trials(models, phases, args.quality_rate)
    done = {r["trial_id"] for r in load_jsonl(TRIALS)}
    pending = [t for t in trials if trial_id(t["model"], t["stim"]["stim_id"], t["condition"]) not in done]
    if args.limit:
        pending = pending[: args.limit]

    print(f"planned {len(trials)} trials; {len(done)} already logged; {len(pending)} to run")
    print(f"models={models} phases={phases} workers={args.workers} "
          f"quality_rate={args.quality_rate}")
    if args.dry_run:
        for t in pending[:10]:
            print("  ", trial_id(t["model"], t["stim"]["stim_id"], t["condition"]))
        return

    t0 = time.time()
    errors = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(run_one, t): t for t in pending}
        for i, fut in enumerate(as_completed(futures), 1):
            t = futures[fut]
            try:
                rec = fut.result()
                append(rec)
            except Exception as e:  # noqa: BLE001
                errors += 1
                append({"trial_id": trial_id(t["model"], t["stim"]["stim_id"], t["condition"]),
                        "error": repr(e), "phase": t["phase"], "model": t["model"],
                        "condition": t["condition"], "stim_id": t["stim"]["stim_id"]})
            if i % 25 == 0 or i == len(pending):
                rate = i / max(1e-9, time.time() - t0)
                print(f"  {i}/{len(pending)} done ({rate:.1f}/s, errors={errors})", flush=True)

    print("\nusage:", json.dumps(lib.usage_summary()))
    print(f"elapsed {time.time()-t0:.0f}s; errors {errors}")
    print(f"log: {TRIALS}")


if __name__ == "__main__":
    main()
