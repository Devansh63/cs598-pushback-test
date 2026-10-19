#!/usr/bin/env python3
"""Fetch a spread sample of WildChat conversations and save them to samples.jsonl.

Usage: python3 fetch_samples.py

Writes one JSON object per line: {"row_idx": int, "row": {...}}.
HTTP goes through `curl` via subprocess (macOS python CA store is unreliable).
"""
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "samples.jsonl"

BASE = (
    "https://datasets-server.huggingface.co/rows"
    "?dataset=allenai/WildChat-1M&config=default&split=train"
)
OFFSETS = list(range(0, 20000, 1000))  # 20 requests
PAGE = 100                              # server max
RETRIES = 6


def fetch(offset: int) -> list[dict]:
    url = f"{BASE}&offset={offset}&length={PAGE}"
    last_err = None
    for attempt in range(RETRIES):
        try:
            cp = subprocess.run(
                ["curl", "-sS", "--max-time", "120", "-w", "\n%{http_code}", url],
                capture_output=True, text=True, timeout=150,
            )
            body, _, code = cp.stdout.rpartition("\n")
            code = code.strip()
            if cp.returncode != 0:
                raise RuntimeError(f"curl rc={cp.returncode}: {cp.stderr.strip()[:200]}")
            if code != "200":
                raise RuntimeError(f"HTTP {code}: {body[:200]}")
            data = json.loads(body)
            rows = data.get("rows", [])
            if not rows:
                raise RuntimeError("empty rows array")
            print(f"offset {offset}: {len(rows)} rows", flush=True)
            return rows
        except Exception as e:  # noqa: BLE001 - retry any failure
            last_err = e
            wait = min(2 ** attempt, 30)
            print(f"offset {offset} attempt {attempt + 1} failed: {e}; sleeping {wait}s",
                  flush=True)
            time.sleep(wait)
    raise RuntimeError(f"offset {offset} failed after {RETRIES} attempts: {last_err}")


def main() -> None:
    if OUT.exists() and sum(1 for _ in OUT.open(encoding="utf-8")) >= 2000:
        print(f"{OUT} already has 2000+ conversations; skipping fetch")
        return

    collected: dict[int, dict] = {}
    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = {ex.submit(fetch, off): off for off in OFFSETS}
        for fut in as_completed(futures):
            for item in fut.result():
                collected[item["row_idx"]] = item

    ordered = [collected[k] for k in sorted(collected)]
    tmp = OUT.with_suffix(".jsonl.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for item in ordered:
            payload = {"row_idx": item["row_idx"], "row": item["row"]}
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    tmp.replace(OUT)

    print(f"wrote {len(ordered)} conversations to {OUT}")
    if len(ordered) < 2000:
        print(f"WARNING: expected 2000, got {len(ordered)}", file=sys.stderr)


if __name__ == "__main__":
    main()
