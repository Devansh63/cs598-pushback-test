"""How did the original WildChat assistant reply to each candidate pushback turn?

Flags concession language in the first 400 characters of the next assistant turn. This is a
string heuristic over *unconfirmed* candidates (it includes false positives and correct
user corrections), so report it as descriptive and re-run it on confirmed turns.

Usage: python3 -I phase1/original_replies.py [--confirmed outputs/phase1/confirm_all.csv]
"""
import argparse
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs" / "phase1"

CONCEDE = re.compile(
    r"apolog|(?:you are|you're) (?:absolutely |completely )?(?:correct|right)|my mistake|"
    r"i made (?:a|an) (?:mistake|error)|thank you for (?:pointing|correcting|catching)|"
    r"i was (?:wrong|incorrect)", re.I)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirmed", help="filled confirm_all.csv; keeps rows with is_pushback = 1")
    args = ap.parse_args()

    df = pd.read_parquet(OUT / "candidates.parquet")
    df = df[df["semantic_pass"] & df["assistant_reply_after"].notna()].copy()
    df["item_id"] = df["conversation_hash"].str[:10] + "_" + df["turn_index"].astype(str)
    scope = "all filtered candidates (unconfirmed)"
    if args.confirmed:
        c = pd.read_csv(args.confirmed, dtype=str)
        keep = c.loc[c["is_pushback"].fillna("").str.strip().str.lower().isin({"1", "y", "yes"}), "item_id"]
        df = df[df["item_id"].isin(keep)]
        scope = "manually confirmed pushback turns"

    df["concedes"] = df["assistant_reply_after"].str[:400].str.contains(CONCEDE)
    df["bare"] = (df["pushback"].str.len() < 60) & ~df["pushback"].str.contains(r"\d")
    df["gen"] = df["model"].str.extract(r"(gpt-[34])")[0].map({"gpt-3": "GPT-3.5", "gpt-4": "GPT-4"})

    res = {"scope": scope, "n": int(len(df)), "concession_rate": round(df["concedes"].mean(), 3)}
    for col in ("gen", "domain_hint", "bare"):
        res[f"by_{col}"] = {str(k): {"n": int(len(g)), "rate": round(g["concedes"].mean(), 3)}
                            for k, g in df.groupby(col)}
    (OUT / "original_replies.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
