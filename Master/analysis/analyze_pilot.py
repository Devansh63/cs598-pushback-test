"""Summarize single-turn runs: rates per model x tier x form x condition, contrasts, instruments.

  python3 analysis/analyze_pilot.py results/pilot_gemini_gemini-3.1-flash-lite [more run dirs...]

Writes <first run dir>/summary.md, numbers.json and disagreements.csv.
Round-1 rows only (multi-round runs are summarized by analyze_multiround.py).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analysis.common import by, instrument_agreement, load_runs, write_disagreements  # noqa: E402
from analysis.metrics import paired_contrast, pct, rates  # noqa: E402

FORM_ORDER = ["scripted", "factual_correction", "clarification_demand", "emotional_pushback", "real", "none"]
COND_ORDER = ["none", "instruct", "reframe", "verify_only", "verify_type", "no_pushback"]


def order(keys, ref):
    return sorted(keys, key=lambda k: (ref.index(k) if k in ref else 99, k))


def block_row(label, s):
    return (f"| {label} | {s['n_wrong']} / {s['n_right']} | **{pct(s['WCR'])}** "
            f"[{pct(s['caves_wilson'][0])}, {pct(s['caves_wilson'][1])}] | {pct(s['hedges'])} | "
            f"**{pct(s['WRR'])}** [{pct(s['resists_wilson'][0])}, {pct(s['resists_wilson'][1])}] | "
            f"{pct(s['unresolved'])} | {s['J']:+.2f} |")


HEADER = ("| group | n wrong / right | WCR = caves (Wilson) | hedges | WRR = resists (Wilson) | unresolved | J |\n"
          "|---|---|---|---|---|---|---|")


def main(run_dirs):
    rows, configs = load_runs(run_dirs)
    rows = [r for r in rows if r["round"] == 1]
    out_dir = Path(run_dirs[0])
    numbers = {"configs": configs}
    L = ["# Single-turn results", ""]
    for rid, c in configs.items():
        L.append(f"- `{rid}`: {c.get('provider')}/{c.get('model')} · temperature {c.get('temperature')} · "
                 f"judge {c.get('judge_provider')}/{c.get('judge_model')} · commit {c.get('commit')} · {c.get('started')}")
    L += ["", f"{len(rows)} judged replies. Definitions: PROGRESS.md §8 / analysis/metrics.py. "
          "Wilson 95% intervals; paired contrasts bootstrap whole questions.", ""]

    for (model,), rm in by(rows, "model").items():
        L += [f"## {model}", ""]
        base = [r for r in rm if r["condition"] == "none"]
        L += ["### By tier and form (condition = none)", "", HEADER]
        for (tier,), rt in by(base, "tier").items():
            for form in order({r["form"] for r in rt}, FORM_ORDER):
                s = rates([r for r in rt if r["form"] == form])
                numbers[f"{model}|{tier}|{form}|none"] = s
                L.append(block_row(f"{tier} · {form}", s))
            s = rates(rt)
            L.append(block_row(f"{tier} · all forms", s))
        L.append("")

        L += ["### By domain (condition = none)", "", HEADER]
        for (tier, dom), rd in by(base, "tier", "domain").items():
            L.append(block_row(f"{tier} · {dom}", rates(rd)))
        L.append("")

        conds = order({r["condition"] for r in rm}, COND_ORDER)
        if len(conds) > 1:
            L += ["### By condition (all forms except the no-pushback control)", "", HEADER]
            for cond in conds:
                s = rates([r for r in rm if r["condition"] == cond])
                numbers[f"{model}|all|all|{cond}"] = s
                L.append(block_row(cond, s))
            L += ["", "#### Pre-registered contrast: verify_type − verify_only", ""]
            a = [r for r in rm if r["condition"] == "verify_type"]
            b = [r for r in rm if r["condition"] == "verify_only"]
            for on in ("bad", "good"):
                c = paired_contrast(a, b, on=on)
                numbers[f"{model}|contrast|verify_type-verify_only|{on}"] = c
                L.append(f"- {on} outcome: {100 * c['diff']:+.1f} pp [{100 * c['lo']:+.0f}, {100 * c['hi']:+.0f}], n = {c['n_pairs']} pairs")
            L += ["", "#### Other contrasts (exploratory)", ""]
            for x, y in (("instruct", "none"), ("reframe", "none"), ("verify_only", "none"), ("verify_type", "none")):
                if x in conds and y in conds:
                    c = paired_contrast([r for r in rm if r["condition"] == x], [r for r in rm if r["condition"] == y], on="bad")
                    L.append(f"- {x} − {y} (bad outcome): {100 * c['diff']:+.1f} pp [{100 * c['lo']:+.0f}, {100 * c['hi']:+.0f}], n = {c['n_pairs']}")
            L.append("")

        if "scripted" in {r["form"] for r in base} and len({r["form"] for r in base}) > 1:
            L += ["### Scripted vs each other form (condition = none, paired over questions, bad outcome)", ""]
            scripted = [r for r in base if r["form"] == "scripted"]
            for form in order({r["form"] for r in base} - {"scripted", "none"}, FORM_ORDER):
                rf = [r for r in base if r["form"] == form]
                c = paired_contrast(rf, [dict(s, form=form) for s in scripted], on="bad")
                numbers[f"{model}|contrast|{form}-scripted|bad"] = c
                L.append(f"- {form} − scripted: {100 * c['diff']:+.1f} pp [{100 * c['lo']:+.0f}, {100 * c['hi']:+.0f}], n = {c['n_pairs']}")
            L.append("")

        L += ["### Response features (judge-coded)", "", "| tier | form | verbal concession, user wrong | verbal concession, user right | expresses uncertainty |", "|---|---|---|---|---|"]
        for (tier, form), rf in by(base, "tier", "form").items():
            w = [r for r in rf if r["direction"] == "user_wrong"]
            g = [r for r in rf if r["direction"] == "user_right"]
            vc = lambda rs: pct(sum(r["verbal_concession"] for r in rs) / len(rs)) if rs else "—"
            eu = pct(sum(r["expresses_uncertainty"] for r in rf) / len(rf)) if rf else "—"
            L.append(f"| {tier} | {form} | {vc(w)} | {vc(g)} | {eu} |")
        L.append("")

    ia = instrument_agreement(rows)
    n_dis = write_disagreements(rows, out_dir / "disagreements.csv")
    L += ["## Instrument agreement", "",
          f"- judge vs string markers: agreed on {ia['markers_state']['agree']} of {ia['markers_state']['n_decisive']} "
          f"decisive replies ({pct(ia['markers_state']['rate'])}) out of {len(rows)}",
          f"- judge vs LLM extractor: agreed on {ia['extractor_state']['agree']} of {ia['extractor_state']['n_decisive']} "
          f"decisive replies ({pct(ia['extractor_state']['rate'])})",
          f"- {n_dis} replies with any disagreement written to `disagreements.csv` for hand review", ""]
    numbers["instrument_agreement"] = ia
    (out_dir / "summary.md").write_text("\n".join(L) + "\n")
    (out_dir / "numbers.json").write_text(json.dumps(numbers, indent=1, default=str))
    print("\n".join(L))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
