"""Phase 1 stage 5: semantic score for EVERY follow-up turn in the frame, not just cue matches.

score = max cosine similarity to pushback prototypes − max similarity to instruction-edit prototypes.
A turn is a `semantic_candidate` when score > --margin. Scores are written to
results/phase1/frame_scores.parquet (ids + scores, local only) and a count summary into
results/phase1/semantic_summary.json.

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
    ap.add_argument("--rethreshold", action="store_true",
                    help="re-flag semantic_candidate from the saved scores with a new --margin or --top-fraction; no encoding")
    ap.add_argument("--top-fraction", type=float,
                    help="instead of --margin, flag the top F of frame turns by score (margin set to that quantile)")
    a = ap.parse_args()
    if a.rethreshold:
        df = pd.read_parquet(OUT / "frame_scores.parquet")
        if a.top_fraction:
            a.margin = float(np.quantile(df["semantic_score"], 1 - a.top_fraction))
        df["semantic_candidate"] = df["semantic_score"] > a.margin
        df.to_parquet(OUT / "frame_scores.parquet", index=False)
        write_summary(df, a.margin, df["semantic_score"].to_numpy())
        return
    import pyarrow.parquet as pq
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(MODEL)
    pos = model.encode(POS, normalize_embeddings=True)
    neg = model.encode(NEG, normalize_embeddings=True)
    # Stream the frame in row batches: the full text column does not fit in 8 GB of RAM.
    pf = pq.ParquetFile(OUT / "frame.parquet")
    total = pf.metadata.num_rows if not a.max_turns else min(a.max_turns, pf.metadata.num_rows)
    parts, done = [], 0
    for rb in pf.iter_batches(batch_size=a.batch * 32, columns=["conversation_hash", "turn_index", "cue_match", "pushback"]):
        chunk = rb.to_pandas()
        if a.max_turns:
            chunk = chunk.head(max(0, a.max_turns - done))
            if chunk.empty:
                break
        texts = [t[:512] for t in chunk["pushback"].tolist()]
        emb = model.encode(texts, batch_size=a.batch, normalize_embeddings=True, show_progress_bar=False)
        chunk["semantic_score"] = ((emb @ pos.T).max(1) - (emb @ neg.T).max(1)).astype(np.float32)
        parts.append(chunk.drop(columns=["pushback"]))
        done += len(chunk)
        print(f"scored {done:,}/{total:,}", flush=True)
        if a.max_turns and done >= a.max_turns:
            break
    df = pd.concat(parts, ignore_index=True)
    scores = df["semantic_score"].to_numpy()
    if a.top_fraction:
        a.margin = float(np.quantile(scores, 1 - a.top_fraction))
    df["semantic_candidate"] = df["semantic_score"] > a.margin
    # scores live in a side file keyed by (conversation_hash, turn_index); the frame is never rewritten
    df.to_parquet(OUT / "frame_scores.parquet", index=False)
    write_summary(df, a.margin, scores)


def write_summary(df, margin, scores):
    summary = {
        "model": MODEL, "margin": margin, "n_scored": int(len(df)),
        "n_semantic_candidates": int(df["semantic_candidate"].sum()),
        "n_lexical_candidates": int(df["cue_match"].sum()),
        "n_both": int((df["semantic_candidate"] & df["cue_match"]).sum()),
        "n_semantic_only": int((df["semantic_candidate"] & ~df["cue_match"]).sum()),
        "score_quantiles": {q: float(np.quantile(scores, q)) for q in (0.5, 0.9, 0.95, 0.99, 0.999)},
    }
    (OUT / "semantic_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
