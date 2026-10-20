"""Phase 1 stage 5: semantic score for EVERY follow-up turn in the frame, not just cue matches.

score = max cosine similarity to pushback prototypes − max similarity to instruction-edit prototypes.
A turn is a `semantic_candidate` when score > --margin. Scores are written back into
frame.parquet (local only) and a count summary into results/phase1/semantic_summary.json.

The semantic stage is a *retrieval* stage: its precision/recall must be measured with
measure_pr.py against labeled candidate and random samples, exactly like the lexical stage.

  python3 phase1/embeddings.py [--margin 0.0] [--batch 512] [--max-turns N]
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results" / "phase1"
MODEL = "sentence-transformers/all-MiniLM-L6-v2"

POS = ["That's wrong, the answer is 12, not 10.", "Are you sure? I'm pretty sure the capital is Sydney.",
       "My teacher said that 1 is a prime number.", "No, that's incorrect. 7 times 8 is 56.",
       "I don't think that's right, it happened in 1991.", "You made a mistake in your calculation, check it again.",
       "Actually the correct answer is B, not C.", "That's not true, water boils at 100 degrees Celsius.",
       "Wrong. The derivative of x^2 is 2x.", "Isn't it supposed to be 45? I got a different number.",
       "Hmm, 2+2 is 4 though.", "that doesn't match what the book says", "you said 3 earlier, now you say 5"]
NEG = ["That's not what I asked for, rewrite it.", "Make it shorter and more formal.", "Thanks, that's great!",
       "Can you write it again in a different style?", "No, I meant a list of ideas, not a paragraph.",
       "Try again with more detail and examples.", "Give me another option.", "Translate that into Spanish.",
       "continue", "now do the same for chapter 2", "what about in python?"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--margin", type=float, default=0.0)
    ap.add_argument("--batch", type=int, default=512)
    ap.add_argument("--max-turns", type=int, help="score only the first N frame turns (smoke test)")
    a = ap.parse_args()
    from sentence_transformers import SentenceTransformer
    df = pd.read_parquet(OUT / "frame.parquet")
    if a.max_turns:
        df = df.head(a.max_turns).copy()
    model = SentenceTransformer(MODEL)
    pos = model.encode(POS, normalize_embeddings=True)
    neg = model.encode(NEG, normalize_embeddings=True)
    texts = df["pushback"].str[:512].tolist()
    scores = np.empty(len(texts), dtype=np.float32)
    for s in range(0, len(texts), a.batch * 8):
        emb = model.encode(texts[s: s + a.batch * 8], batch_size=a.batch, normalize_embeddings=True,
                           show_progress_bar=False)
        scores[s: s + len(emb)] = (emb @ pos.T).max(1) - (emb @ neg.T).max(1)
        print(f"scored {min(s + len(emb), len(texts)):,}/{len(texts):,}", flush=True)
    df["semantic_score"] = scores
    df["semantic_candidate"] = df["semantic_score"] > a.margin
    df.to_parquet(OUT / "frame.parquet", index=False)
    summary = {
        "model": MODEL, "margin": a.margin, "n_scored": int(len(df)),
        "n_semantic_candidates": int(df["semantic_candidate"].sum()),
        "n_lexical_candidates": int(df["cue_match"].sum()),
        "n_both": int((df["semantic_candidate"] & df["cue_match"]).sum()),
        "n_semantic_only": int((df["semantic_candidate"] & ~df["cue_match"]).sum()),
        "score_quantiles": {q: float(np.quantile(scores, q)) for q in (0.5, 0.9, 0.99, 0.999)},
    }
    (OUT / "semantic_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
