#!/usr/bin/env python3
"""Build the Phase 2 stimulus set (CS 598 HCI, Group 6).

For every question, both directions and every form, produce the pushback text.

  direction user_wrong : history has the CORRECT answer, user pushes the ALTERNATIVE
  direction user_right : history has the ALTERNATIVE answer, user pushes the CORRECT answer

Forms: three reconstructed from real PushbackChat types (factual_correction,
clarification_demand, emotional_pushback) plus the scripted baseline from the revised
proposal. Each reconstructed stimulus records the real event it was authored from, so the
provenance claim ("reconstructed from real pushback") is auditable.

Output: stimuli_v1.jsonl
"""
import csv
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from lib import FORMS, make_pushback  # noqa: E402

QUESTIONS = os.path.join(ROOT, "data", "questions_v1.csv")
CORPUS = os.path.join(os.path.dirname(ROOT), "Midterm", "data", "pushbackchat_3k_v1.json")
OUT = os.path.join(ROOT, "data", "stimuli_v1.jsonl")

PII = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "<EMAIL>"),
    (re.compile(r"(?:[A-Za-z]:\\|/)(?:[\w.-]+[/\\]){2,}[\w.-]+"), "<PATH>"),
    (re.compile(r"\b(sk|pk|ghp|xox[bp])[-_][A-Za-z0-9_-]{12,}"), "<KEY>"),
]


def scrub(text):
    for pat, repl in PII:
        text = pat.sub(repl, text)
    return text


# Exemplars chosen by reading candidates (not by regex): each one demonstrably exhibits the
# form it documents. The templates in lib.py were authored from these; they are not verbatim
# derivations, so the quoted text is documentation of the source strategy, not a citation.
CURATED_EXEMPLARS = {
    "factual_correction": "pb_0027",    # "No, incorrect, you have used the number 3 twice."
    "clarification_demand": "pb_0070",  # "I think you misinterpreted the question again..."
    "emotional_pushback": "pb_1400",    # "I find it extremely disappointing and frustrating..."
}


def pick_exemplars():
    events = {e["event_id"]: e for e in json.load(open(CORPUS))}
    out = {}
    for form, eid in CURATED_EXEMPLARS.items():
        ev = events.get(eid)
        if ev is None:
            raise SystemExit(f"curated exemplar {eid} not found in corpus")
        text = scrub((ev.get("pushback_user") or "").strip())
        out[form] = {"event_id": eid, "text": text}
    return out


def main():
    rows = list(csv.DictReader(open(QUESTIONS)))
    exemplars = pick_exemplars()
    missing = [t for t in FORMS if t not in exemplars]
    if missing:
        raise SystemExit(f"no exemplar for forms {missing}")

    out = []
    for r in rows:
        for direction in ("user_wrong", "user_right"):
            claim = r["alternative"] if direction == "user_wrong" else r["correct"]
            initial = r["correct"] if direction == "user_wrong" else r["alternative"]
            for i, form in enumerate(list(FORMS.keys()) + ["scripted"]):
                text = make_pushback(form, claim, index=i)
                out.append({
                    "stim_id": f"{r['id']}-{direction}-{form}",
                    "question_id": r["id"],
                    "domain": r["domain"],
                    "question": r["question"],
                    "direction": direction,
                    "form": form,
                    "intended_type": form if form != "scripted" else "scripted",
                    "initial_answer": initial,
                    "claim": claim,
                    "pushback": text,
                    "source_event": exemplars.get(form, {}).get("event_id") if form != "scripted" else "template",
                    "source_text": exemplars.get(form, {}).get("text") if form != "scripted" else None,
                })

    with open(OUT, "w") as f:
        for rec in out:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    n_q = len(rows)
    print(f"wrote {OUT}: {len(out)} stimuli = {n_q} questions x 2 directions x 4 forms")
    print("provenance (real PushbackChat event each form's wording was authored from):")
    for t, ex in exemplars.items():
        print(f"  {t:22s} {ex['event_id']}  \"{ex['text'][:90]}\"")
    print("\nexample stimulus:")
    print(json.dumps(out[1], indent=1, ensure_ascii=False)[:700])


if __name__ == "__main__":
    main()
