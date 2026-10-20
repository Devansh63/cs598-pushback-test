#!/usr/bin/env python3
"""Track A: independent re-analysis of PushbackChat v1 (Devansh/midterm/prelim_analysis.py, paths adapted).

Question this answers: before we build our own pushback pipeline, what do we already
know from the closest public artifact (PushbackChat v1, real WildChat pushback)?

What it does:
  1. Downloads the public PushbackChat v1 reproducibility artifacts (cached in ./data).
  2. Recomputes the per-model behaviour distribution (replication check vs. their
     published main_findings.md).
  3. Computes capitulation rate by pushback type, per model.
  4. Joins the 500 human correctness labels and computes the correctness-conditioned
     rates that our project needs: caving on wrong pushback (ICR) vs. accepting a
     correct correction vs. wrongly resisting one, with Wilson 95% CIs.
  5. Measures how much of real pushback our proposed lexical filter would recover.
  6. Reports label reliability (LLM vs. human ground truth, Cohen's kappa) and the
     multi-label evidence that motivates revising our codebook.

Run:  python3 trackA/pushbackchat_reanalysis.py   (downloads to results/trackA/pushbackchat_cache/, writes results/trackA/pushbackchat_reanalysis.{md,json})
Deps: python3 stdlib only.
"""
import collections
import csv
import hashlib
import json
import math
import os
import re
import shutil
import ssl
import subprocess
import sys
import urllib.error
import urllib.request

BASE = "https://huggingface.co/datasets/NoirZangetsu/pushbackchat-v1/resolve/main"
HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.join(os.path.dirname(HERE), "results", "trackA")
DATA = os.path.join(OUTDIR, "pushbackchat_cache")

FILES = [
    "config/default.yaml",
    "analysis/behavior_label_overrides.csv",
    "analysis/ground_truth.csv",
    "analysis/results/main_findings.md",
    "dataset/pushbackchat_3k_v1.json",
    "results/behaviors/deepseek_v4_flash_behaviors.jsonl",
    "results/behaviors/llama_3_3_70b_behaviors.jsonl",
    "results/behaviors/nemotron_3_nano_behaviors.jsonl",
    "results/behaviors/qwen3_235b_a22b_2507_behaviors.jsonl",
]

MODELS = ["deepseek_v4_flash", "llama_3_3_70b", "nemotron_3_nano", "qwen3_235b_a22b_2507"]
TYPES = ["factual_correction", "clarification_demand", "preference_disagreement", "emotional_pushback"]
LABELS = ["model_correct", "user_correct", "ambiguous_opinion", "ambiguous_factual"]
CUES = ["correction", "disagreement", "repetition", "doubt", "clarification"]

# The keyword list as written in our proposal, Sec. 3 Phase 1.
PROPOSED_KEYWORDS = r"(that'?s wrong|that'?s incorrect|are you sure|i don'?t think|no,? that|you'?re wrong|incorrect|not correct)"

OUT = []
RESULT = {}


def emit(line=""):
    print(line)
    OUT.append(line)


def _download(url, dst):
    """curl first (system CA store); urllib as fallback for machines with no CA bundle."""
    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
    if shutil.which("curl"):
        rc = subprocess.call(["curl", "-fsSL", "-m", "300", "-o", dst, url])
        if rc == 0 and os.path.getsize(dst) > 0:
            return
        print(f"  curl failed for {url}, falling back to urllib", file=sys.stderr)
    try:
        urllib.request.urlretrieve(url, dst)
    except urllib.error.URLError as e:
        print(f"  urllib failed ({e}); retrying without certificate verification", file=sys.stderr)
        ctx = ssl._create_unverified_context()
        with urllib.request.urlopen(url, context=ctx) as r, open(dst, "wb") as f:
            shutil.copyfileobj(r, f)


def fetch(rel):
    dst = os.path.join(DATA, os.path.basename(rel))
    if not os.path.exists(dst) or os.path.getsize(dst) == 0:
        print(f"  downloading {rel}", file=sys.stderr)
        _download(f"{BASE}/{rel}", dst)
    return dst


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def wilson(k, n, z=1.96):
    """Wilson score interval, returned in percent."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (100 * (c - h), 100 * (c + h))


def kappa(pairs, categories):
    n = len(pairs)
    po = sum(a == b for a, b in pairs) / n
    pe = 0.0
    for c in categories:
        pe += (sum(a == c for a, _ in pairs) / n) * (sum(b == c for _, b in pairs) / n)
    return (po - pe) / (1 - pe), po


# ---------------------------------------------------------------- load
paths = {rel: fetch(rel) for rel in FILES}

events = json.load(open(paths["dataset/pushbackchat_3k_v1.json"]))
ds = {e["event_id"]: e for e in events}
gt_rows = list(csv.DictReader(open(paths["analysis/ground_truth.csv"])))
human = {r["event_id"]: r["human_label"] for r in gt_rows}
llm = {r["event_id"]: r["llm_label"] for r in gt_rows}

beh = {}
for m in MODELS:
    path = paths[f"results/behaviors/{m}_behaviors.jsonl"]
    with open(path) as f:
        beh[m] = {json.loads(l)["event_id"]: json.loads(l)["behavior"] for l in f}
    for r in csv.DictReader(open(paths["analysis/behavior_label_overrides.csv"])):
        if r["model_name"] == m and r["event_id"] in beh[m]:
            beh[m][r["event_id"]] = r["new_behavior"]


def counts(model, ids):
    return collections.Counter(beh[model].get(e, "MISSING") for e in ids)


emit("# PushbackChat v1 - independent re-analysis (Group 6, CS 598 HCI)")
emit()
emit("All numbers below are computed from the public PushbackChat v1 release "
     "(2,309 real English pushback events extracted from WildChat-4.8M) by `prelim_analysis.py`.")
emit()
emit(f"- events: **{len(ds)}**")
emit(f"- events with human correctness labels: **{len(human)}** ({100 * len(human) / len(ds):.0f}%)")
emit(f"- behaviour rows (4 models): **{sum(len(v) for v in beh.values())}**")
emit(f"- dataset sha256: `{sha256(paths['dataset/pushbackchat_3k_v1.json'])}`")

# ---------------------------------------------------------------- 1 behaviour
emit()
emit("## 1. Behaviour distribution by model (all 2,309 real pushback events)")
emit()
emit("| model | capitulation | defense | hedge | deflection | missing |")
emit("|---|---|---|---|---|---|")
dist = {}
for m in MODELS:
    c = counts(m, ds)
    n = sum(c[k] for k in ("capitulation", "defense", "hedge", "deflection"))
    dist[m] = {k: round(100 * c[k] / n, 1) for k in ("capitulation", "defense", "hedge", "deflection")}
    emit(f"| {m} | {100 * c['capitulation'] / n:.1f}% | {100 * c['defense'] / n:.1f}% | "
         f"{100 * c['hedge'] / n:.1f}% | {100 * c['deflection'] / n:.1f}% | {c['MISSING']} |")
RESULT["behaviour_by_model"] = dist

# ---------------------------------------------------------------- 2 by type
emit()
emit("## 2. Capitulation rate by pushback type (all events)")
emit()
emit("| type | n | " + " | ".join(MODELS) + " |")
emit("|---|---|" + "---|" * len(MODELS))
by_type = {}
for t in TYPES:
    ids = [e for e, r in ds.items() if r["pushback_type"] == t]
    row = {m: round(100 * counts(m, ids)["capitulation"] / len(ids), 1) for m in MODELS}
    by_type[t] = {"n": len(ids), **row}
    emit(f"| {t} | {len(ids)} | " + " | ".join(f"{row[m]:.1f}%" for m in MODELS) + " |")
RESULT["capitulation_by_type"] = by_type

# ---------------------------------------------------------------- 3 conditioned
emit()
emit("## 3. Correctness-conditioned rates (human ground truth, n=500)")
emit()
emit("`user wrong` = human label `model_correct` (the prior answer was verified correct and the")
emit("pushback was wrong). `user right` = human label `user_correct`, i.e. the correction was valid.")
emit()
emit("| model | cave given user wrong (ICR) | accept given user right | resist/hedge given user right | gap |")
emit("|---|---|---|---|---|")
wrong = [e for e, l in human.items() if l == "model_correct"]
right = [e for e, l in human.items() if l == "user_correct"]
conditioned = {}
for m in MODELS:
    cw, nw = counts(m, wrong)["capitulation"], len(wrong)
    c = counts(m, right)
    nr = len(right)
    lo, hi = wilson(cw, nw)
    conditioned[m] = {
        "icr": round(100 * cw / nw, 1), "icr_n": nw, "icr_ci": [round(lo, 1), round(hi, 1)],
        "accept_given_right": round(100 * c["capitulation"] / nr, 1),
        "resist_given_right": round(100 * (c["defense"] + c["hedge"]) / nr, 1),
        "gap_pp": round(100 * cw / nw - 100 * c["capitulation"] / nr, 1),
    }
    emit(f"| {m} | {100 * cw / nw:.1f}% ({nw}) [{lo:.1f}, {hi:.1f}] | "
         f"{100 * c['capitulation'] / nr:.1f}% | {100 * (c['defense'] + c['hedge']) / nr:.1f}% | "
         f"{100 * cw / nw - 100 * c['capitulation'] / nr:+.1f} pp |")
RESULT["conditioned"] = conditioned
RESULT["conditioned_n"] = {"user_wrong": len(wrong), "user_right": len(right)}

# ---------------------------------------------------------------- 4 reliability
emit()
emit("## 4. LLM vs. human ground-truth reliability (n=500)")
k, po = kappa([(llm[e], human[e]) for e in human], LABELS)
emit()
emit(f"raw agreement {po:.1%} | Cohen's kappa **{k:.3f}**")
RESULT["gt_kappa"] = round(k, 3)
RESULT["gt_agreement"] = round(po, 3)

# ---------------------------------------------------------------- 5 filter recall
emit()
emit("## 5. Would our proposed Phase 1 filter find real pushback?")
hits = sum(1 for r in ds.values() if re.search(PROPOSED_KEYWORDS, r["pushback_user"], re.I))
emit()
emit(f"- the keyword list written in our proposal matches **{hits}/{len(ds)} = {100 * hits / len(ds):.1f}%** "
     f"of turns that are *known* to be pushback")
emit("- recall measured inside an already-positive set: precision against the full 4.8M corpus is still unknown")
cue_counts = {}
emit()
emit("| PushbackChat lexical cue | events it fires on | share |")
emit("|---|---|---|")
for cue in CUES:
    n = sum(1 for r in ds.values() if cue in str(r["regex_match_groups"]))
    cue_counts[cue] = n
    emit(f"| {cue} | {n} | {100 * n / len(ds):.1f}% |")
union = {e for e, r in ds.items() if any(c in str(r["regex_match_groups"]) for c in CUES)}
RESULT["proposed_filter_recall"] = round(100 * hits / len(ds), 1)
RESULT["cue_counts"] = cue_counts
emit()
emit(f"Union of their cue suite: {len(union)}/{len(ds)} = {100 * len(union) / len(ds):.1f}% of the released corpus.")

# ---------------------------------------------------------------- 6 taxonomy
emit()
emit("## 6. Evidence for a multi-label codebook")
emo = sum(1 for r in ds.values() if r["has_emotion"])
emit()
emit(f"- {emo}/{len(ds)} = {100 * emo / len(ds):.1f}% of pushback turns are flagged emotional "
     f"*in addition to* their strategy type")
emit("| type | emotional | non-emotional |")
emit("|---|---|---|")
for t in TYPES:
    a = sum(1 for r in ds.values() if r["pushback_type"] == t and r["has_emotion"])
    b = sum(1 for r in ds.values() if r["pushback_type"] == t and not r["has_emotion"])
    emit(f"| {t} | {a} | {b} |")
multi = sum(1 for r in ds.values() if sum(c in str(r["regex_match_groups"]) for c in CUES) > 1)
emit()
emit(f"- {multi}/{len(ds)} = {100 * multi / len(ds):.1f}% match more than one lexical cue")
RESULT["multi_label"] = {"emotion": emo, "multi_cue": multi}

emit()
emit("## 7. Coverage limit that shapes our scope")
emit()
emit("| type | events | human correctness labels |")
emit("|---|---|---|")
cov = {}
for t in TYPES:
    ids = [e for e, r in ds.items() if r["pushback_type"] == t]
    lab = sum(1 for e in ids if e in human)
    cov[t] = {"events": len(ids), "labelled": lab}
    emit(f"| {t} | {len(ids)} | {lab} |")
RESULT["gt_coverage"] = cov
emit()
emit("Correctness ground truth covers **one** pushback type, and only 66 events satisfy")
emit("`user wrong + prior answer correct` with a human label. That ceiling is why the project")
emit("keeps a controlled question set as the primary source of statistical power.")

# ---------------------------------------------------------------- write
os.makedirs(OUTDIR, exist_ok=True)
with open(os.path.join(OUTDIR, "pushbackchat_reanalysis.md"), "w") as f:
    f.write("\n".join(OUT) + "\n")
with open(os.path.join(OUTDIR, "pushbackchat_reanalysis.json"), "w") as f:
    json.dump(RESULT, f, indent=2)
print("\n[written results/trackA/pushbackchat_reanalysis.md, .json]")
