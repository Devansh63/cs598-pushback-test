"""Export coding sheets from the Phase 1 candidates.

  outputs/phase1/confirm_all.csv    every semantic-pass candidate, for manual confirmation
  outputs/phase1/pilot50_<coder>.csv  the 50-turn open-coding pilot (one copy per coder)

One turn per conversation in the pilot, stratified by domain hint. Text is scrubbed of
emails, URLs, phone numbers and @handles (WildChat already redacts most PII).

Usage: python3 -I phase1/make_coding_sheets.py --coders sahil devansh [--n 50] [--seed 598]
"""
import argparse
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs" / "phase1"
CTX = 700  # chars of question / answer shown to coders

SCRUB = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[EMAIL]"),
    (re.compile(r"https?://\S+|www\.\S+"), "[URL]"),
    (re.compile(r"\+\d{1,3}[\s.-]?\(?\d{2,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}\b"), "[PHONE]"),
    (re.compile(r"\(?\b\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}\b"), "[PHONE]"),
    (re.compile(r"(?<!\w)@\w{2,}"), "[HANDLE]"),
]

# Coding columns. Strategy and tone are multi-label (1 = present). See 'Codebook v1.md' in the vault Project folder.
CONFIRM_COLS = ["is_pushback", "checkable_claim", "notes"]
CODE_COLS = (["is_pushback", "checkable_claim"]
             + [f"s_{k}" for k in ["bare", "recheck", "alt_answer", "counter_evidence",
                                   "error_pointer", "authority", "inconsistency", "repetition",
                                   "self_doubt"]]
             + [f"t_{k}" for k in ["frustration", "hostility", "politeness"]]
             + ["user_claim", "notes"])


def scrub(text, limit=None):
    if text is None:
        return ""
    for rx, rep in SCRUB:
        text = rx.sub(rep, text)
    if limit and len(text) > limit:
        text = text[:limit] + " […]"
    return text


def sheet(df, cols):
    out = pd.DataFrame({
        "item_id": df["item_id"],
        "domain_hint": df["domain_hint"],
        "question": df["question"].map(lambda t: scrub(t, CTX)),
        "assistant_answer": df["assistant_answer"].map(lambda t: scrub(t, CTX)),
        "pushback": df["pushback"].map(scrub),
    })
    for c in cols:
        out[c] = ""
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--coders", nargs="+", default=["coder1", "coder2"])
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--seed", type=int, default=598)
    args = ap.parse_args()

    df = pd.read_parquet(OUT / "candidates.parquet")
    df = df[df["semantic_pass"]].copy()
    df["item_id"] = df["conversation_hash"].str[:10] + "_" + df["turn_index"].astype(str)
    df = df.sample(frac=1, random_state=args.seed)  # shuffle so sheets carry no ranking

    sheet(df, CONFIRM_COLS).to_csv(OUT / "confirm_all.csv", index=False)

    one_per_conv = df.drop_duplicates("conversation_hash")
    per = args.n // 2
    pilot = pd.concat([one_per_conv[one_per_conv.domain_hint == d].head(per) for d in ("math", "fact")])
    pilot = pilot.sample(frac=1, random_state=args.seed)
    pilot[["item_id", "conversation_hash", "turn_index", "model", "domain_hint"]].to_csv(
        OUT / "pilot50_key.csv", index=False)
    for c in args.coders:
        sheet(pilot, CODE_COLS).to_csv(OUT / f"pilot50_{c}.csv", index=False)
    print(f"confirm_all.csv: {len(df)} rows; pilot: {len(pilot)} rows x {len(args.coders)} coders")


if __name__ == "__main__":
    main()
