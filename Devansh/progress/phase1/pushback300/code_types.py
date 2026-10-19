#!/usr/bin/env python3
"""Second-coder pass over the 10-code pushback scheme (CS 598 HCI, Group 6).

The workbook's themes/subthemes were produced by an AI pipeline we cannot inspect and were never
human-coded. Before those codes can carry any claim, we need to know whether they are reproducible.
This script applies the same 10-code scheme with a fresh prompt and reports per-code agreement
(Cohen's kappa on binary presence), precision/recall against the workbook codes, and how often the
two coders produce the identical code set.

This is an *upper bound* on reliability: two AI coders sharing training data will agree more than
two humans would. It is a triage instrument, not a replacement for the two-human procedure.

Outputs:
  data_local/type_codes_ai.jsonl   local
  results/type_agreement.md        committed
"""
import argparse
import collections
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "code"))
import lib  # noqa: E402

DATA = os.path.join(HERE, "data_local")
RESULTS = os.path.join(HERE, "results")
MODEL = "deepseek-flash"
STRICT_B = False

SCHEME = {
    "B": ("Bare disagreement", "rejects or doubts the answer without a substantive reason, "
                               "alternative claim, or task correction"),
    "A": ("Alternative claim", "states or proposes a competing answer, value, or factual claim"),
    "I": ("Inconsistency challenge", "identifies an alleged conflict within the answer or with "
                                     "an earlier turn"),
    "L": ("Reasoning challenge", "challenges an assumption, inference, or logic using an "
                                 "articulated reason"),
    "E": ("Counter-evidence", "reports observations, tests, logs, or quoted material that "
                              "conflict with the answer"),
    "S": ("Appeal to authority or source", "explicitly invokes an external source, institution, "
                                           "or expert as support"),
    "R": ("Recheck request", "asks for confirmation, checking, reconsideration, or verification"),
    "T": ("Task or constraint correction", "says the assistant misunderstood the task, the user's "
                                           "meaning, or a required constraint"),
    "P": ("Repeated insistence", "signals persistence after an earlier attempt (still, again, "
                                 "already told you)"),
    "F": ("Frustration", "expresses irritation, impatience, or exasperation"),
}

B_RULE = """
Important: Bare disagreement (B) is MUTUALLY EXCLUSIVE with A, I, L, E, S and T. Use B only when
the turn rejects or doubts the answer with no substantive alternative, reason, evidence, source,
inconsistency claim, or task correction. B may co-occur with R, P or F.
"""

PROMPT = """Code the user's pushback against a chatbot answer using these labels. A turn may get several.

{codes}
{extra}

ASSISTANT ANSWER (truncated): {answer}

USER PUSHBACK: {turn}

Return JSON: {{"codes": ["B", "R", ...], "rationale": "<one sentence>"}}
Use only the codes above. Code what the user expresses; do not infer correctness."""

CODE_LINE = "\n".join(f"- {k} ({name}): {desc}" for k, (name, desc) in SCHEME.items())
_lock = threading.Lock()


def code_one(case):
    prompt = PROMPT.format(codes=CODE_LINE, extra=B_RULE if STRICT_B else "",
                           answer=(case["preceding_answer"] or "")[:1200],
                           turn=(case["target_text"] or "")[:900])
    raw = lib.chat([{"role": "user", "content": prompt}], model=MODEL, json_mode=True,
                   max_tokens=1500)
    return lib._parse_json(raw)


def kappa(pairs):
    n = len(pairs)
    if not n:
        return float("nan")
    po = sum(a == b for a, b in pairs) / n
    pe = (sum(a for a, _ in pairs) / n) * (sum(b for _, b in pairs) / n) + \
         (1 - sum(a for a, _ in pairs) / n) * (1 - sum(b for _, b in pairs) / n)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--rule-b", action="store_true",
                    help="add the workbook's mutual-exclusion rule for Bare disagreement")
    args = ap.parse_args()
    global STRICT_B
    STRICT_B = args.rule_b

    cases = [json.loads(l) for l in open(os.path.join(DATA, "contexts.jsonl"))]
    meta = {json.loads(l)["event_id"]: json.loads(l)
            for l in open(os.path.join(DATA, "meta.jsonl"))}
    out_path = os.path.join(DATA, "type_codes_ai" + ("_v2" if STRICT_B else "") + ".jsonl")
    done = set()
    if os.path.exists(out_path):
        done = {json.loads(l)["event_id"] for l in open(out_path) if l.strip()}
    todo = [c for c in cases if c["event_id"] not in done]
    print(f"coding {len(todo)} of {len(cases)} cases")

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(code_one, c): c for c in todo}
        for i, fut in enumerate(as_completed(futs), 1):
            c = futs[fut]
            try:
                a = fut.result()
                codes = [x for x in (a.get("codes") or []) if x in SCHEME]
                rec = {"event_id": c["event_id"], "codes": sorted(set(codes)),
                       "rationale": a.get("rationale")}
            except Exception as e:  # noqa: BLE001
                rec = {"event_id": c["event_id"], "error": repr(e)}
            with _lock:
                with open(out_path, "a") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if i % 50 == 0 or i == len(todo):
                print(f"  {i}/{len(todo)}", flush=True)

    ours = {json.loads(l)["event_id"]: json.loads(l).get("codes", [])
            for l in open(out_path) if l.strip()}

    def theirs(eid):
        out = []
        for s in meta[eid]["subthemes_ai"]:
            code = s.split()[0].strip("—-").strip()
            if code in SCHEME:
                out.append(code)
        return sorted(set(out))

    eids = [e for e in ours if e in meta and ours[e]]
    rows = []
    for code in SCHEME:
        a = [1 if code in ours[e] else 0 for e in eids]
        b = [1 if code in theirs(e) else 0 for e in eids]
        tp = sum(1 for x, y in zip(a, b) if x and y)
        precision = 100 * tp / sum(a) if sum(a) else float("nan")
        recall = 100 * tp / sum(b) if sum(b) else float("nan")
        rows.append((code, SCHEME[code][0], sum(b), sum(a), precision, recall, kappa(list(zip(a, b)))))

    exact = sum(1 for e in eids if sorted(set(ours[e])) == theirs(e))
    jacc = []
    for e in eids:
        A, B = set(ours[e]), set(theirs(e))
        jacc.append(len(A & B) / len(A | B) if (A | B) else 1.0)

    lines = ["# Type coding: is the workbook's 10-code scheme reproducible?", "",
             f"Two independent AI passes over **{len(eids)}** real pushback turns "
             f"(workbook preliminary codes vs. fresh prompt), model `{MODEL}`.", "",
             "| code | label | workbook n | our n | precision | recall | Cohen's κ |",
             "|---|---|---|---|---|---|---|"]
    for code, name, n_b, n_a, p, r, k in rows:
        lines.append(f"| {code} | {name} | {n_b} | {n_a} | {p:.0f}% | {r:.0f}% | {k:.2f} |")
    lines += ["", f"- identical code set: **{100*exact/len(eids):.1f}%** ({exact}/{len(eids)})",
              f"- mean Jaccard overlap: **{100*sum(jacc)/len(jacc):.1f}%**", "",
              "**Read this as an upper bound.** Two AI coders trained on overlapping data agree "
              "more than two humans would, so these kappas overstate human reliability. The codes "
              "that are *least* reproducible (low κ) are the ones the codebook must define more "
              "sharply before the two-human pass.", ""]
    # compare against the other variant if present
    other = os.path.join(DATA, "type_codes_ai.jsonl" if STRICT_B else "type_codes_ai_v2.jsonl")
    if os.path.exists(other):
        alt = {json.loads(l)["event_id"]: json.loads(l).get("codes", [])
               for l in open(other) if l.strip()}
        eids2 = [e for e in alt if e in meta and alt[e]]
        a = [1 if "B" in ours[e] else 0 for e in eids2]
        b = [1 if "B" in theirs(e) else 0 for e in eids2]
        alt_a = [1 if "B" in alt[e] else 0 for e in eids2]
        lines += ["", f"### Bare-disagreement check against the {'strict' if STRICT_B else 'original'} rule",
                  "",
                  f"- κ with the mutual-exclusion rule: **{kappa(list(zip(a, b))):.2f}** "
                  f"(this run, n={len(eids2)})",
                  f"- κ without it: **{kappa(list(zip(alt_a, b))):.2f}**",
                  f"- B labeled this run: {sum(a)}, in the other run: {sum(alt_a)}, "
                  f"in the workbook: {sum(b)}", ""]
    open(os.path.join(RESULTS, "type_agreement" + ("_v2" if STRICT_B else "") + ".md"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
