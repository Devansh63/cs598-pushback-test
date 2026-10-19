"""Summarize the hard multi-round runs.

Per model x direction x form, the share of trials whose reply at round r ends on the correct
answer / hedges / ends on the wrong answer, plus "ever abandoned the correct answer" (a hedge or
wrong answer at any round). 95% CIs resample whole questions.

Usage: python3 -I phase2/analyze_multiround.py outputs/hard_<model> [outputs/hard_<model2> ...]
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

B = 5000
RNG = np.random.default_rng(598)
GOOD = {"user_wrong": "holds", "user_right": "accepts"}
BAD = {"user_wrong": "caves", "user_right": "resists"}


def boot(flags_by_q):
    """flags_by_q: Series indexed by qid of 0/1. CI of the mean, resampling questions."""
    x = flags_by_q.to_numpy(dtype=float)
    stats = [RNG.choice(x, len(x), replace=True).mean() for _ in range(B)]
    lo, hi = np.percentile(stats, [2.5, 97.5])
    return x.mean(), lo, hi


def load(run_dir):
    rows = [json.loads(l) for l in (Path(run_dir) / "trials.jsonl").read_text().splitlines() if l.strip()]
    flat = []
    for t in rows:
        for r in t["rounds"]:
            flat.append({"model": Path(run_dir).name.replace("hard_", ""), "qid": t["qid"],
                         "direction": t["direction"], "form": t["form"], "round": r["round"],
                         "outcome": r["outcome"], "final": r["judge"].get("final_answer"),
                         "concession": bool(r["judge"].get("verbal_concession")),
                         "marker": r["marker_check"]})
    return pd.DataFrame(flat)


def main(dirs):
    df = pd.concat([load(d) for d in dirs], ignore_index=True)
    lines = ["# Hard questions + 3 rounds of persistent pushback", "",
             f"{df.qid.nunique()} questions from real WildChat disputes · forms: scripted, real (original user wording) · "
             "rounds 2–3 escalate · judge: gemini-3.6-flash · 95% CIs resample questions", ""]
    table = []
    for model, dm in df.groupby("model", sort=False):
        lines += [f"## {model}", ""]
        for direction in ("user_wrong", "user_right"):
            dd = dm[dm.direction == direction]
            lines += [f"### {'User is wrong' if direction == 'user_wrong' else 'User is right'}", "",
                      f"| Form | Round | {GOOD[direction]} | hedges | {BAD[direction]} | concession language |",
                      "|---|---|---|---|---|---|"]
            for form in ("scripted", "real"):
                for rnd in (1, 2, 3):
                    s = dd[(dd.form == form) & (dd["round"] == rnd)]
                    if s.empty:
                        continue
                    g, h, b = (s.outcome == GOOD[direction]).mean(), (s.outcome == "hedge").mean(), (s.outcome == BAD[direction]).mean()
                    lines.append(f"| {form} | {rnd} | {g:.0%} | {h:.0%} | {b:.0%} | {s.concession.mean():.0%} |")
                    table.append({"model": model, "direction": direction, "form": form, "round": rnd,
                                  "n": len(s), "good": g, "hedge": h, "bad": b, "concession": s.concession.mean()})
            # ever abandoned the correct position, per trial
            per_trial = dd.groupby(["form", "qid"]).outcome.apply(lambda o: int((o != GOOD[direction]).any()))
            lines.append("")
            for form in ("scripted", "real"):
                if form in per_trial.index.get_level_values(0):
                    p, lo, hi = boot(per_trial.loc[form])
                    label = "left the correct answer (hedge or cave) at least once" if direction == "user_wrong" \
                        else "failed to settle on the correct answer at least once"
                    lines.append(f"- **{form}**: {label}: **{p:.0%}** [{lo:.0%}, {hi:.0%}] of {len(per_trial.loc[form])} questions")
                    table.append({"model": model, "direction": direction, "form": form, "round": "any",
                                  "n": len(per_trial.loc[form]), "bad": p, "bad_lo": lo, "bad_hi": hi})
            lines.append("")

    clear = df[df.marker != "ambiguous"]
    agree = (clear.final == clear.marker).mean()
    lines += ["## Judge check", "",
              f"String markers unambiguous for {len(clear)} of {len(df)} replies; judge agreed on {agree:.0%}.",
              f"Parse errors: {int((df.final == 'parse_error').sum())}.", ""]
    out = Path(dirs[0]).parent / "hard_summary.md"
    out.write_text("\n".join(lines))
    pd.DataFrame(table).to_csv(out.with_suffix(".csv"), index=False)
    clear[clear.final != clear.marker].to_csv(out.with_name("hard_judge_vs_markers.csv"), index=False)
    print("\n".join(lines))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
