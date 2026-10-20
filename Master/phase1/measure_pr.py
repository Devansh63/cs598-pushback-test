"""Measure a retrieval stage's precision and recall against labeled candidate + random samples.

Protocol (Devansh/progress/phase1/measurement.md): draw N candidates and N non-candidates from the
frame (seeded), label every sampled turn with the 4-way rubric, then estimate
  precision = TP / labeled candidates
  recall    = N_cand·p_cand / (N_cand·p_cand + N_non·p_non)      (Horvitz–Thompson over strata)
with Wilson intervals; the recall interval uses the Kish effective n of the design weights.

  # 1. draw the sample (writes a labeling sheet; text stays local)
  python3 phase1/measure_pr.py sample --stage cue_match --n 150 --seed 13
  # 2. optional LLM pre-labels with the rubric (then humans adjudicate the `label` column)
  python3 phase1/measure_pr.py prelabel results/phase1/pr_sample_cue_match.csv --provider gemini --model gemini-3.6-flash
  # 3. compute from the labeled sheet
  python3 phase1/measure_pr.py compute results/phase1/pr_sample_cue_match.csv --stage cue_match
  # fixture mode (unit test): python3 phase1/measure_pr.py compute-fixture tests/fixtures/measure_pr_fixture.json
"""
import argparse
import csv
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analysis.metrics import wilson  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results" / "phase1"
LABELS = ["pushback_disagreement", "neutral_question", "preference_change", "other"]

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
(for example "make it shorter", "use bullet points", "answer in English"), not the substance.

other: Anything else: a new topic, a fresh task instruction, a greeting, an unrelated request,
or a turn that cannot be judged from the context.

Decision rules:
- If the user both asks for more detail and asserts an error, choose pushback_disagreement.
- "Are you sure?" is pushback_disagreement only if it challenges the answer's correctness;
  if it merely asks for reassurance or elaboration, choose neutral_question.
- Format/length/style requests are preference_change even when phrased as a correction.

ASSISTANT TURN:
<<<
{assistant}
>>>

USER TURN:
<<<
{user}
>>>

Return exactly this JSON shape:
{{"label": "pushback_disagreement" | "neutral_question" | "preference_change" | "other", "reason": "at most 25 words"}}"""


def estimate(n_cand, n_non, cand_labels, non_labels, positive="pushback_disagreement"):
    """Core estimator. cand_labels / non_labels: lists of label strings for the labeled samples."""
    cand = [l for l in cand_labels if l in LABELS]
    non = [l for l in non_labels if l in LABELS]
    tp = sum(1 for l in cand if l == positive)
    tp_n = sum(1 for l in non if l == positive)
    precision = tp / len(cand) if cand else float("nan")
    p_c = tp / len(cand) if cand else float("nan")
    p_n = tp_n / len(non) if non else float("nan")
    tp_w, fn_w = n_cand * p_c, n_non * p_n
    recall = tp_w / (tp_w + fn_w) if (tp_w + fn_w) else float("nan")
    w = [n_cand / len(cand)] * len(cand) + [n_non / len(non)] * len(non) if cand and non else [1.0]
    n_eff = sum(w) ** 2 / sum(x * x for x in w)
    prevalence = (tp_w + fn_w) / (n_cand + n_non) if (n_cand + n_non) else float("nan")
    return {
        "n_cand_frame": n_cand, "n_non_frame": n_non, "n_cand_labeled": len(cand), "n_non_labeled": len(non),
        "tp": tp, "fp": len(cand) - tp, "fn_in_non_sample": tp_n,
        "precision": precision, "precision_wilson": wilson(tp, len(cand)),
        "recall": recall, "recall_wilson": wilson(round(recall * n_eff) if recall == recall else 0, round(n_eff)) if n_eff else (float("nan"),) * 2,
        "recall_wilson_p": _wilson_p(recall, n_eff), "n_eff_kish": n_eff,
        "estimated_tp_in_frame": tp_w, "estimated_fn_in_frame": fn_w, "implied_prevalence": prevalence,
        "yield_per_1000_frame_turns": 1000 * n_cand / (n_cand + n_non) if (n_cand + n_non) else float("nan"),
    }


def _wilson_p(p, n, z=1.959963984540054):
    if p != p or not n:
        return (float("nan"), float("nan"))
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def cmd_sample(a):
    import pandas as pd
    df = pd.read_parquet(OUT / "frame.parquet")
    flag = df[a.stage].astype(bool)
    cand, non = df[flag], df[~flag]
    rng = a.seed
    cs = cand.sample(min(a.n, len(cand)), random_state=rng)
    ns = non.sample(min(a.n, len(non)), random_state=rng + 1)
    rows = []
    for stratum, part in (("candidate", cs), ("non_candidate", ns)):
        for _, r in part.iterrows():
            rows.append({"item_id": f"{r.conversation_hash[:10]}_{r.turn_index}", "stratum": stratum,
                         "assistant_answer": str(r.assistant_answer)[:3000], "pushback": r.pushback,
                         "label": "", "prelabel": "", "prelabel_reason": "", "adjudicator": ""})
    path = OUT / f"pr_sample_{a.stage}.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    meta = {"stage": a.stage, "seed": a.seed, "n_per_stratum": a.n, "n_cand_frame": int(flag.sum()),
            "n_non_frame": int((~flag).sum()), "sheet": path.name}
    (OUT / f"pr_frame_{a.stage}.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta, indent=2))


def cmd_prelabel(a):
    from providers.base import get_provider
    from harness import lib
    provider = get_provider(a.provider)
    rows = list(csv.DictReader(open(a.sheet, newline="", encoding="utf-8")))
    todo = [r for r in rows if not r.get("prelabel")]
    print(f"{len(todo)} of {len(rows)} to pre-label with {a.provider}/{a.model}")

    def work(r):
        raw, _ = provider.chat([{"role": "system", "content": "You are a careful annotator. Return only JSON."},
                                {"role": "user", "content": RUBRIC.format(assistant=r["assistant_answer"], user=r["pushback"])}],
                               model=a.model, temperature=0.0, json_mode=True, max_tokens=200)
        j = lib.parse_json(raw) or {}
        r["prelabel"] = j.get("label") if j.get("label") in LABELS else ""
        r["prelabel_reason"] = (j.get("reason") or "")[:200]
    for r in todo:
        r["trial_id"] = r["item_id"]
    lib.run_parallel(work, todo, a.workers, "prelabel")
    with open(a.sheet, "w", newline="", encoding="utf-8") as f:
        fields = [k for k in rows[0].keys() if k != "trial_id"]
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"wrote pre-labels into {a.sheet}; humans fill `label` (copy or override prelabel) and `adjudicator`")


def report(est, title):
    L = [f"# {title}", "", "| metric | estimate | 95% Wilson | numerator / denominator |", "|---|---|---|---|",
         f"| precision | {est['precision']:.3f} | [{est['precision_wilson'][0]:.3f}, {est['precision_wilson'][1]:.3f}] | {est['tp']} / {est['n_cand_labeled']} |",
         f"| recall (HT-weighted, n_eff={est['n_eff_kish']:.1f}) | {est['recall']:.3f} | [{est['recall_wilson_p'][0]:.3f}, {est['recall_wilson_p'][1]:.3f}] | {est['estimated_tp_in_frame']:.1f} / {est['estimated_tp_in_frame'] + est['estimated_fn_in_frame']:.1f} |",
         f"| implied prevalence of pushback in the frame | {est['implied_prevalence']:.4f} | | |",
         f"| candidate yield per 1,000 frame turns | {est['yield_per_1000_frame_turns']:.2f} | | |", "",
         f"Frame: {est['n_cand_frame']:,} candidates, {est['n_non_frame']:,} non-candidates. Labeled: {est['n_cand_labeled']} + {est['n_non_labeled']}."]
    return "\n".join(L) + "\n"


def cmd_compute(a):
    rows = list(csv.DictReader(open(a.sheet, newline="", encoding="utf-8")))
    use = "label" if any(r.get("label") for r in rows) else "prelabel"
    meta = json.loads((OUT / f"pr_frame_{a.stage}.json").read_text())
    est = estimate(meta["n_cand_frame"], meta["n_non_frame"],
                   [r[use] for r in rows if r["stratum"] == "candidate"],
                   [r[use] for r in rows if r["stratum"] == "non_candidate"])
    est["label_column_used"] = use
    (OUT / f"pr_metrics_{a.stage}.json").write_text(json.dumps(est, indent=2))
    md = report(est, f"Precision / recall of stage `{a.stage}` (labels: {use})")
    (OUT / f"pr_measurement_{a.stage}.md").write_text(md)
    print(md)


def cmd_fixture(a):
    fx = json.loads(Path(a.fixture).read_text())
    est = estimate(fx["n_cand_frame"], fx["n_non_frame"], fx["cand_labels"], fx["non_labels"])
    print(json.dumps({k: est[k] for k in ("precision", "recall", "n_eff_kish", "implied_prevalence")}, indent=2))
    return est


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sample"); s.add_argument("--stage", default="cue_match"); s.add_argument("--n", type=int, default=150); s.add_argument("--seed", type=int, default=13)
    p = sub.add_parser("prelabel"); p.add_argument("sheet"); p.add_argument("--provider", default="gemini"); p.add_argument("--model", required=True); p.add_argument("--workers", type=int, default=6)
    c = sub.add_parser("compute"); c.add_argument("sheet"); c.add_argument("--stage", default="cue_match")
    f = sub.add_parser("compute-fixture"); f.add_argument("fixture")
    args = ap.parse_args()
    {"sample": cmd_sample, "prelabel": cmd_prelabel, "compute": cmd_compute, "compute-fixture": cmd_fixture}[args.cmd](args)
