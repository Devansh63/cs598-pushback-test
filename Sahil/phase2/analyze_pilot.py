"""Summarize a Phase 2 pilot run.

Rates per direction x pushback form, with 95% CIs from a question-level bootstrap
(resample whole questions, keeping all their trials), plus paired differences vs the
scripted baseline. Also checks the judge against the string-marker heuristic.

Usage: python3 -I phase2/analyze_pilot.py outputs/pilot_<model>
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
FORM_ORDER = ["scripted", "authority", "counter_evidence", "frustration"]


def boot_rate(df, outcome):
    """Pooled rate over trials; CI resamples whole questions."""
    qids = df["qid"].unique()
    by_q = {q: g["outcome"].eq(outcome).to_numpy() for q, g in df.groupby("qid")}
    point = df["outcome"].eq(outcome).mean()
    stats = []
    for _ in range(B):
        samp = RNG.choice(qids, len(qids), replace=True)
        x = np.concatenate([by_q[q] for q in samp])
        stats.append(x.mean())
    lo, hi = np.percentile(stats, [2.5, 97.5])
    return point, lo, hi


def boot_paired_diff(df, form, base, outcome):
    """Difference in rate (form - base), resampling questions so pairs stay together."""
    a = df[df.form == form].groupby("qid")["outcome"].apply(lambda s: s.eq(outcome).mean())
    b = df[df.form == base].groupby("qid")["outcome"].apply(lambda s: s.eq(outcome).mean())
    d = (a - b).dropna().to_numpy()
    stats = [RNG.choice(d, len(d), replace=True).mean() for _ in range(B)]
    lo, hi = np.percentile(stats, [2.5, 97.5])
    return d.mean(), lo, hi


def main(run_dir):
    run_dir = Path(run_dir)
    rows = [json.loads(l) for l in (run_dir / "judgments.jsonl").read_text().splitlines() if l.strip()]
    df = pd.json_normalize(rows)
    cfg = json.loads((run_dir / "run_config.json").read_text())
    forms = [f for f in FORM_ORDER if f in set(df.form)] + sorted(set(df.form) - set(FORM_ORDER))

    lines = [f"# Phase 2 pilot: {cfg['model']}", "",
             f"Judge: {cfg['judge_model']} · temperature: {cfg['temperature'] or 'API default'} · "
             f"{df.qid.nunique()} questions · {len(df)} judged trials · 95% CIs from question-level bootstrap",
             ""]

    table = []
    for direction in ("user_wrong", "user_right"):
        sub = df[df.direction == direction]
        lines += [f"## {'User is wrong (resistance)' if direction == 'user_wrong' else 'User is right (openness)'}", "",
                  f"| Form | n | {GOOD[direction]} | hedges | {BAD[direction]} | {BAD[direction]} vs scripted (paired) |",
                  "|---|---|---|---|---|---|"]
        for f in forms:
            s = sub[sub.form == f]
            if s.empty:
                continue
            g = s.outcome.eq(GOOD[direction]).mean()
            h = s.outcome.eq("hedge").mean()
            p, lo, hi = boot_rate(s, BAD[direction])
            if f != "scripted" and "scripted" in forms:
                d, dlo, dhi = boot_paired_diff(sub, f, "scripted", BAD[direction])
                diff = f"{d:+.0%} [{dlo:+.0%}, {dhi:+.0%}]"
            else:
                diff = "—"
            lines.append(f"| {f} | {len(s)} | {g:.0%} | {h:.0%} | **{p:.0%}** [{lo:.0%}, {hi:.0%}] | {diff} |")
            table.append({"direction": direction, "form": f, "n": len(s), "good": g, "hedge": h,
                          "bad": p, "bad_lo": lo, "bad_hi": hi,
                          "other": 1 - g - h - p})
        lines.append("")

    # Response features
    j = df.filter(like="judge.").rename(columns=lambda c: c.replace("judge.", ""))
    feat = pd.concat([df[["direction", "form"]], j], axis=1)
    lines += ["## Response features (judge-coded, share of trials)", "",
              "| Direction | Form | verbal concession | explains decision | addresses user's argument | expresses uncertainty |",
              "|---|---|---|---|---|---|"]
    for (dirn, f), g in feat.groupby(["direction", "form"]):
        aua = g["addresses_user_argument"].dropna()
        lines.append(f"| {dirn} | {f} | {g['verbal_concession'].mean():.0%} | {g['explains_decision'].mean():.0%} | "
                     f"{(format(aua.astype(bool).mean(), '.0%') if len(aua) else '—')} | "
                     f"{g['expresses_uncertainty'].mean():.0%} |")
    # Concession language without changing answer: "says you're right, keeps answer"
    holds = feat[(df.outcome == "holds") & feat["verbal_concession"].astype(bool)]
    lines += ["", f"Replies that **hold the correct answer but still use concession language**: "
              f"{len(holds)} of {int((df.outcome == 'holds').sum())} holds.", ""]

    # Judge vs marker heuristic
    clear = df[df.marker_check != "ambiguous"]
    fa = df.loc[clear.index, "judge.final_answer"]
    agree = (fa == clear.marker_check).mean() if len(clear) else float("nan")
    lines += ["## Judge check", "",
              f"String markers were unambiguous for {len(clear)} of {len(df)} replies; the judge agreed on "
              f"{agree:.0%} of those. Disagreements are listed in `judge_vs_markers.csv` for hand review.",
              f"Judge parse errors: {int((df['judge.final_answer'] == 'parse_error').sum())}.", ""]
    clear[fa != clear.marker_check].to_csv(run_dir / "judge_vs_markers.csv", index=False)

    (run_dir / "summary.md").write_text("\n".join(lines))
    pd.DataFrame(table).to_csv(run_dir / "rates.csv", index=False)
    plot(pd.DataFrame(table), cfg["model"], run_dir / "pilot_rates.png")
    print("\n".join(lines))


def plot(t, model, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # Polarity encoding: good outcome (blue) / neutral hedge (gray) / bad outcome (orange).
    colors = {"good": "#2a78d6", "hedge": "#b4b2a9", "bad": "#eb6834", "other": "#e4e2dc"}
    ink, muted = "#0b0b0b", "#52514e"
    plt.rcParams.update({"font.family": "Helvetica", "font.size": 11})
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.6), sharey=True)
    titles = {"user_wrong": ("User is wrong", "holds", "caves"),
              "user_right": ("User is right", "accepts", "resists")}
    for ax, direction in zip(axes, ("user_wrong", "user_right")):
        s = t[t.direction == direction].set_index("form").reindex(FORM_ORDER).dropna(subset=["n"])
        y = np.arange(len(s))[::-1]
        left = np.zeros(len(s))
        for key in ("good", "hedge", "bad", "other"):
            w = s[key].to_numpy()
            ax.barh(y, w, left=left, color=colors[key], height=0.62, edgecolor="white", linewidth=2)
            for yi, l, wi in zip(y, left, w):
                if wi >= 0.08 and key in ("good", "bad"):
                    ax.text(l + wi / 2, yi, f"{wi:.0%}", ha="center", va="center", color="white",
                            fontsize=10, fontweight="bold")
            left += w
        title, good, bad = titles[direction]
        ax.set_title(f"{title}: {good} / hedges / {bad}", loc="left", color=ink, fontsize=12)
        ax.set_yticks(y, [f.replace("_", " ") for f in s.index], color=ink)
        ax.set_xlim(0, 1)
        ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
        ax.tick_params(colors=muted, length=0)
        for sp in ax.spines.values():
            sp.set_visible(False)
        ax.grid(axis="x", color="#e4e2dc", linewidth=0.8)
        ax.set_axisbelow(True)
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(color=colors["good"], label="keeps / reaches correct answer"),
                        Patch(color=colors["hedge"], label="hedges"),
                        Patch(color=colors["bad"], label="ends on wrong answer")],
               loc="lower center", ncol=3, frameon=False, fontsize=10, labelcolor=muted)
    fig.suptitle(f"Pilot: how {model} responds to pushback (n = {int(t.n.iloc[0])} per bar)",
                 x=0.01, ha="left", color=ink, fontsize=13)
    fig.tight_layout(rect=(0, 0.08, 1, 0.95))
    fig.savefig(path, dpi=200, facecolor="white")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
