#!/usr/bin/env bash
# End-to-end reproduction for the Phase 1 filter measurement.
# Everything runs inside this directory; no files outside it are touched.
set -euo pipefail
cd "$(dirname "$0")"

# 1. Pilot sample from the rows API: 2,000 conversations, spread offsets.
#    (Requires network. The server may rate-limit; the script retries.)
python3 fetch_samples.py
python3 build_pairs.py

# 2. Measurement frame: four official parquet shards, 15,000 random rows each.
#    Download once (approximately 900 MB):
#      for s in 00 06 07 13; do
#        curl -L -o shard$s.parquet \
#          "https://huggingface.co/datasets/allenai/WildChat-1M/resolve/main/data/train-000$s-of-00014.parquet"
#      done
python3 build_frame_from_parquet.py
python3 build_pairs.py samples_frame.jsonl pairs_expanded.jsonl pair_stats_expanded.json

# 3. Label 150 candidates + 150 non-candidates (seed 13) with DeepSeek.
#    Requires DEEPSEEK_API_KEY. Resumes if judged.jsonl already exists.
python3 label_sample.py

# 4. Metrics, CIs, measurement.md, and the redacted candidate corpus.
python3 compute_metrics.py
python3 make_candidates.py
