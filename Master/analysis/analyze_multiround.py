"""Summarize multi-round runs: outcome by round, and 'ever left the correct answer' per trial.

  python3 analysis/analyze_multiround.py results/multiround_gemini_gemini-3.1-flash-lite [more...]

Writes <first run dir>/summary.md, numbers.json and disagreements.csv.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analysis.common import by, instrument_agreement, load_runs, write_disagreements  # noqa: E402
from analysis.metrics import BAD, GOOD, cluster_bootstrap_ci, paired_diff_ci, pct, rates  # noqa: E402


def ever_left(rows):
    """Per (qid, direction, form): 1 if any round's outcome is not the good one."""
    out = {}
    for r in rows:
        k = (r["qid"], r["direction"], r["form"])
        out[k] = max(out.get(k, 0), int(r["outcome"] != GOOD[r["direction"]]))
    return out


def main(run_dirs):
    rows, configs = load_runs(run_dirs)
    out_dir = Path(run_dirs[0])
    numbers = {"configs": configs}
    L = ["# Multi-round results", ""]
    for rid, c in configs.items():
        L.append(f"- `{rid}`: {c.get('provider')}/{c.get('model')} · temperature {c.get('temperature')} · "
                 f"judge {c.get('judge_provider')}/{c.get('judge_model')} · rounds {c.get('rounds')} · commit {c.get('commit')}")
    L += ["", f"{len(rows)} judged replies. Round 1 is the pushback form; rounds 2–3 are the fixed escalation "
          "templates. CIs: Wilson per round; question-level bootstrap for 'ever left'.", ""]

    for (model, tier), rm in by(rows, "model", "tier").items():
        L += [f"## {model} · {tier} tier", ""]
        for direction in ("user_wrong", "user_right"):
            rd = [r for r in rm if r["direction"] == direction]
            if not rd:
                continue
            good, bad = GOOD[direction], BAD[direction]
            L += [f"### {'User is wrong' if direction == 'user_wrong' else 'User is right'}", "",
                  f"| form | round | n | {good} | hedge/unresolved | {bad} (Wilson) | verbal concession |",
                  "|---|---|---|---|---|---|---|"]
            for (form,), rf in by(rd, "form").items():
                for (rnd,), rr in by(rf, "round").items():
                    s = rates(rr)
                    b = s["WCR"] if direction == "user_wrong" else s["WRR"]
                    ci = s["caves_wilson"] if direction == "user_wrong" else s["resists_wilson"]
                    neither = s["hedges"] if direction == "user_wrong" else s["unresolved"]
                    g = s["holds"] if direction == "user_wrong" else s["accepts"]
                    vc = sum(r["verbal_concession"] for r in rr) / len(rr)
                    numbers[f"{model}|{tier}|{direction}|{form}|r{rnd}"] = {"n": len(rr), "good": g, "neither": neither, "bad": b, "bad_wilson": ci, "verbal_concession": vc}
                    L.append(f"| {form} | {rnd} | {len(rr)} | {pct(g)} | {pct(neither)} | **{pct(b)}** [{pct(ci[0])}, {pct(ci[1])}] | {pct(vc)} |")
            L.append("")
            el = ever_left(rd)
            for form in sorted({k[2] for k in el}):
                vals = {q: [v] for (q, d, f), v in el.items() if f == form}
                p = sum(v[0] for v in vals.values()) / len(vals)
                lo, hi = cluster_bootstrap_ci(vals)
                numbers[f"{model}|{tier}|{direction}|{form}|ever_left"] = {"rate": p, "lo": lo, "hi": hi, "n": len(vals)}
                L.append(f"- **{form}**: left the {good} outcome at least once in {len(vals)} questions: **{pct(p)}** [{pct(lo)}, {pct(hi)}]")
            forms = sorted({k[2] for k in el})
            if "scripted" in forms and len(forms) > 1:
                for form in forms:
                    if form == "scripted":
                        continue
                    pairs = [(q, el[(q, direction, form)], el[(q, direction, "scripted")])
                             for (q, d, f) in el if f == form and (q, direction, "scripted") in el]
                    point, (lo, hi) = paired_diff_ci(pairs)
                    numbers[f"{model}|{tier}|{direction}|{form}-scripted|ever_left_diff"] = {"diff": point, "lo": lo, "hi": hi, "n": len(pairs)}
                    L.append(f"- {form} − scripted (ever left, paired): {100 * point:+.0f} pp [{100 * lo:+.0f}, {100 * hi:+.0f}], n = {len(pairs)}")
            L.append("")

    ia = instrument_agreement(rows)
    n_dis = write_disagreements(rows, out_dir / "disagreements.csv")
    L += ["## Instrument agreement", "",
          f"- judge vs string markers: {ia['markers_state']['agree']} / {ia['markers_state']['n_decisive']} decisive ({pct(ia['markers_state']['rate'])})",
          f"- judge vs LLM extractor: {ia['extractor_state']['agree']} / {ia['extractor_state']['n_decisive']} decisive ({pct(ia['extractor_state']['rate'])})",
          f"- {n_dis} replies with any disagreement in `disagreements.csv`", ""]
    numbers["instrument_agreement"] = ia
    (out_dir / "summary.md").write_text("\n".join(L) + "\n")
    (out_dir / "numbers.json").write_text(json.dumps(numbers, indent=1, default=str))
    print("\n".join(L))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
