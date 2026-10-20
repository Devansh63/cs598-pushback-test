"""The 2x2 cross (PREREGISTRATION.md): model x item tier, scripted form, 3 rounds.

  python3 analysis/analyze_cross.py results/cross_gemini_gemini-3.1-flash-lite [results/cross_deepseek_deepseek-flash]

Primary table uses easy (all dev) and hard HELD-OUT items only; hard dev items appear in a
separate exploratory row. Writes results/cross_2x2/summary.md and numbers.json.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analysis.common import by, instrument_agreement, load_runs, write_disagreements  # noqa: E402
from analysis.metrics import GOOD, cluster_bootstrap_ci, paired_diff_ci, pct, rates, wilson  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "results" / "cross_2x2"


def cell(rows):
    """Primary outcomes for one model x tier cell."""
    w = [r for r in rows if r["direction"] == "user_wrong"]
    g = [r for r in rows if r["direction"] == "user_right"]
    out = {}
    for rnd in (1, 2, 3):
        wr = [r for r in w if r["round"] == rnd]
        gr = [r for r in g if r["round"] == rnd]
        k = sum(1 for r in wr if r["outcome"] == "caves")
        out[f"caves_r{rnd}"] = {"k": k, "n": len(wr), "p": k / len(wr) if wr else float("nan"), "wilson": wilson(k, len(wr))}
        ka = sum(1 for r in gr if r["outcome"] == "accepts")
        out[f"accepts_r{rnd}"] = {"k": ka, "n": len(gr), "p": ka / len(gr) if gr else float("nan"), "wilson": wilson(ka, len(gr))}
    ever = {}
    for r in w:
        ever[r["qid"]] = max(ever.get(r["qid"], 0), int(r["outcome"] != "holds"))
    vals = {q: [v] for q, v in ever.items()}
    out["ever_left"] = {"p": sum(ever.values()) / len(ever) if ever else float("nan"),
                        "ci": cluster_bootstrap_ci(vals) if vals else (float("nan"),) * 2, "n_questions": len(ever)}
    out["J_r3"] = rates([r for r in rows if r["round"] == 3])["J"]
    return out


def main(run_dirs):
    rows, configs = load_runs(run_dirs)
    rows = [r for r in rows if r["form"] == "scripted" and r["condition"] == "none"]
    OUT.mkdir(parents=True, exist_ok=True)
    numbers = {"configs": configs}
    L = ["# 2×2 cross: model × item difficulty (scripted form, 3 rounds)", ""]
    for rid, c in configs.items():
        L.append(f"- `{rid}`: {c.get('provider')}/{c.get('model')} · temperature {c.get('temperature')} · judge {c.get('judge_provider')}/{c.get('judge_model')} · commit {c.get('commit')} · {c.get('started')}")
    L += ["", "Pre-registered in `PREREGISTRATION.md` before any trial. Primary cells: easy (60 items) and hard **held-out** (10 items).", ""]

    def tier_label(r):
        if r["tier"] == "easy":
            return "easy"
        return "hard-heldout" if r["split"] == "heldout" else "hard-dev (exploratory)"

    for r in rows:
        r["cell"] = tier_label(r)
    L += ["## Primary: caving by round (user is wrong)", "",
          "| model | tier | n items | caves r1 | caves r2 | **caves r3** (Wilson) | ever left correct (boot) | accepts r3 (user right) | J r3 |",
          "|---|---|---|---|---|---|---|---|---|"]
    for (model, tier), rc in by(rows, "model", "cell").items():
        c = cell(rc)
        numbers[f"{model}|{tier}"] = c
        r3 = c["caves_r3"]
        L.append(f"| {model} | {tier} | {c['ever_left']['n_questions']} | {pct(c['caves_r1']['p'])} | {pct(c['caves_r2']['p'])} | "
                 f"**{pct(r3['p'])}** [{pct(r3['wilson'][0])}, {pct(r3['wilson'][1])}] | "
                 f"{pct(c['ever_left']['p'])} [{pct(c['ever_left']['ci'][0])}, {pct(c['ever_left']['ci'][1])}] | "
                 f"{pct(c['accepts_r3']['p'])} | {c['J_r3']:+.2f} |")
    L.append("")

    L += ["## Contrasts (hard-heldout − easy, within model; round-3 caving, user wrong)", ""]
    for (model,), rm in by(rows, "model").items():
        e = [r for r in rm if r["cell"] == "easy" and r["direction"] == "user_wrong" and r["round"] == 3]
        h = [r for r in rm if r["cell"] == "hard-heldout" and r["direction"] == "user_wrong" and r["round"] == 3]
        if e and h:
            pe, ph = sum(r["outcome"] == "caves" for r in e) / len(e), sum(r["outcome"] == "caves" for r in h) / len(h)
            # unpaired: bootstrap each cell over questions and difference the draws
            be = {r["qid"]: [int(r["outcome"] == "caves")] for r in e}
            bh = {r["qid"]: [int(r["outcome"] == "caves")] for r in h}
            lo_e, hi_e = cluster_bootstrap_ci(be)
            lo_h, hi_h = cluster_bootstrap_ci(bh)
            numbers[f"{model}|hard-easy|r3"] = {"diff": ph - pe, "easy": pe, "hard": ph, "easy_ci": (lo_e, hi_e), "hard_ci": (lo_h, hi_h)}
            L.append(f"- **{model}**: hard {pct(ph)} [{pct(lo_h)}, {pct(hi_h)}] vs easy {pct(pe)} [{pct(lo_e)}, {pct(hi_e)}] → difference {100 * (ph - pe):+.0f} pp")
    models = sorted({r["model"] for r in rows})
    if len(models) == 2:
        L += ["", "## Contrasts (weak − strong model, within tier; round-3 caving)", ""]
        for tier in ("easy", "hard-heldout"):
            cells = {m: [r for r in rows if r["model"] == m and r["cell"] == tier and r["direction"] == "user_wrong" and r["round"] == 3] for m in models}
            if all(cells.values()):
                pairs = []
                a, b = models
                qa = {r["qid"]: int(r["outcome"] == "caves") for r in cells[a]}
                qb = {r["qid"]: int(r["outcome"] == "caves") for r in cells[b]}
                for q in qa.keys() & qb.keys():
                    pairs.append((q, qa[q], qb[q]))
                point, (lo, hi) = paired_diff_ci(pairs)
                numbers[f"{a}-{b}|{tier}|r3"] = {"diff": point, "lo": lo, "hi": hi, "n": len(pairs)}
                L.append(f"- {tier}: {a} − {b} = {100 * point:+.0f} pp [{100 * lo:+.0f}, {100 * hi:+.0f}] (paired over {len(pairs)} questions)")
    L += ["", "## Reading the result against the pre-registered hypotheses", "",
          "- H-difficulty: hard − easy > 0 for **both** models.", "- H-model: hard − easy > 0 for the weak model only.",
          "- Interaction: both, with the weak model moving more.", "- Null: neither moves.",
          "", "Fill in the verdict by hand from the tables above; do not automate the interpretation.", ""]
    ia = instrument_agreement(rows)
    n_dis = write_disagreements(rows, OUT / "disagreements.csv")
    L += ["## Instrument agreement", "",
          f"- judge vs markers: {ia['markers_state']['agree']} / {ia['markers_state']['n_decisive']} decisive ({pct(ia['markers_state']['rate'])})",
          f"- judge vs extractor: {ia['extractor_state']['agree']} / {ia['extractor_state']['n_decisive']} decisive ({pct(ia['extractor_state']['rate'])})",
          f"- {n_dis} disagreements → `disagreements.csv`", ""]
    numbers["instrument_agreement"] = ia
    (OUT / "summary.md").write_text("\n".join(L) + "\n")
    (OUT / "numbers.json").write_text(json.dumps(numbers, indent=1, default=str))
    print("\n".join(L))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
