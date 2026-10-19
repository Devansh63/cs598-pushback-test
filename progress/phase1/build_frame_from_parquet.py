#!/usr/bin/env python3
"""Build a 60k-conversation random frame from official WildChat parquet shards.

The rows API is quota-limited (HTTP 429), so the measurement frame is drawn from
four official parquet shards of `allenai/WildChat-1M` (train split): shards 00,
06, 07 and 13, covering early, middle and late parts of the corpus.

For each shard, 15,000 rows are sampled uniformly at random (seed 13); the
sample retains the conversation only for English rows (the measurement frame).

Output: samples_frame.jsonl, frame_manifest.json
"""
import json
import random
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
SHARDS = ["shard00.parquet", "shard06.parquet", "shard07.parquet", "shard13.parquet"]
OUT = HERE / "samples_frame.jsonl"
MANIFEST = HERE / "frame_manifest.json"
SEED = 13
PER_SHARD = 15_000

COLUMNS = ["conversation_hash", "model", "timestamp", "conversation", "turn", "language"]


def main() -> None:
    sampled_total = 0
    english_total = 0
    lang_counts = Counter()
    shard_info = []

    with OUT.open("w", encoding="utf-8") as out:
        for si, name in enumerate(SHARDS):
            path = HERE / name
            if not path.exists():
                raise SystemExit(f"missing {path}; download it first")
            pf = pq.ParquetFile(path)
            n_rows = pf.metadata.num_rows
            table = pf.read(columns=COLUMNS)
            rng = random.Random(SEED + si)
            take = sorted(rng.sample(range(n_rows), min(PER_SHARD, n_rows)))
            sub = table.take(take)

            rows = sub.to_pylist()
            n_en = 0
            for local_idx, row in zip(take, rows):
                lang = row.get("language")
                lang_counts[lang or "UNKNOWN"] += 1
                rec = {
                    "row_idx": si * 1_000_000 + local_idx,
                    "shard": name,
                    "conversation_hash": row.get("conversation_hash"),
                    "model": row.get("model"),
                    "timestamp": row["timestamp"].isoformat() if row.get("timestamp") else None,
                    "language": lang,
                    "n_turns": len(row.get("conversation") or []),
                }
                if lang == "English":
                    n_en += 1
                    rec["conversation"] = [
                        {"role": t.get("role"), "content": t.get("content") or ""}
                        for t in (row.get("conversation") or [])
                    ]
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                sampled_total += 1
            english_total += n_en
            shard_info.append({
                "file": name, "n_rows_in_shard": n_rows,
                "n_sampled": len(take), "n_english": n_en,
            })
            print(f"{name}: {n_rows:,} rows, sampled {len(take):,}, English {n_en:,}",
                  flush=True)

    manifest = {
        "seed": SEED,
        "per_shard_sample": PER_SHARD,
        "n_sampled_total": sampled_total,
        "n_english_total": english_total,
        "language_counts": dict(lang_counts.most_common()),
        "shards": shard_info,
        "source": "https://huggingface.co/datasets/allenai/WildChat-1M (official parquet, train split)",
        "note": "row_idx is a synthetic id = shard_index*1,000,000 + parquet row index; "
                "only English rows retain the conversation field.",
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"wrote {sampled_total:,} rows ({english_total:,} English) to {OUT}")


if __name__ == "__main__":
    main()
