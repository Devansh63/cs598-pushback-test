"""Export coding sheets (codebook v2 columns) from the Phase 1 candidates.

  python3 phase1/make_coding_sheets.py --coders sahil devansh [--n 50] [--seed 598] [--stage cue_match]

Writes to results/phase1/ (all local-only, they contain verbatim turns):
  confirm_all.csv          every candidate, for manual confirmation (gate codes only)
  pilot<N>_<coder>.csv     the open-coding pilot, one copy per coder; one turn per conversation, half math / half fact
  pilot<N>_key.csv         ids only (committed-safe)
Column template: data/coding_sheet_template.csv
"""
import argparse
import csv
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results" / "phase1"
TEMPLATE = ROOT / "data" / "coding_sheet_template.csv"
CTX = 700

SCRUB = [(re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[EMAIL]"),
         (re.compile(r"https?://\S+|www\.\S+"), "[URL]"),
         (re.compile(r"\+\d{1,3}[\s.-]?\(?\d{2,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}\b"), "[PHONE]"),
         (re.compile(r"\(?\b\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}\b"), "[PHONE]"),
         (re.compile(r"(?<!\w)@\w{2,}"), "[HANDLE]")]


def scrub(text, limit=None):
    text = text or ""
    for rx, rep in SCRUB:
        text = rx.sub(rep, text)
    return text[:limit] + " […]" if limit and len(text) > limit else text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--coders", nargs="+", default=["coder1", "coder2"])
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--seed", type=int, default=598)
    a = ap.parse_args()
    cols = next(csv.reader(open(TEMPLATE, encoding="utf-8")))
    code_cols = [c for c in cols if c not in ("item_id", "domain_hint", "question", "assistant_answer", "pushback")]
    df = pd.read_parquet(OUT / "candidates.parquet")
    df["item_id"] = df["conversation_hash"].str[:10] + "_" + df["turn_index"].astype(str)
    df = df.sample(frac=1, random_state=a.seed)

    def sheet(d, keep):
        out = pd.DataFrame({"item_id": d["item_id"], "domain_hint": d["domain_hint"],
                            "question": d["question"].map(lambda t: scrub(t, CTX)),
                            "assistant_answer": d["assistant_answer"].map(lambda t: scrub(t, CTX)),
                            "pushback": d["pushback"].map(scrub)})
        for c in keep:
            out[c] = ""
        return out

    sheet(df, ["is_pushback", "checkable_claim", "notes"]).to_csv(OUT / "confirm_all.csv", index=False)
    one = df.drop_duplicates("conversation_hash")
    pilot = pd.concat([one[one.domain_hint == d].head(a.n // 2) for d in ("math", "fact")]).sample(frac=1, random_state=a.seed)
    pilot[["item_id", "conversation_hash", "turn_index", "model", "domain_hint"]].to_csv(OUT / f"pilot{a.n}_key.csv", index=False)
    for c in a.coders:
        sheet(pilot, code_cols).to_csv(OUT / f"pilot{a.n}_{c}.csv", index=False)
    print(f"confirm_all.csv: {len(df)} rows; pilot: {len(pilot)} rows x {len(a.coders)} coders; columns: {code_cols}")


if __name__ == "__main__":
    main()
