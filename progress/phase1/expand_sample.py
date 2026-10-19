#!/usr/bin/env python3
"""Expand the WildChat sample with random pages so the candidate pool is large
enough for a 150-candidate labeling sample.

Why this exists: the instructed 2,000-conversation spread sample produced only
6 cue-matched pairs, which cannot support a 150-candidate precision estimate.
This script draws a second, purely random sample of pages (seed 13) and stores
a slimmed row per conversation.  Only English conversations keep their
`conversation` array; for other languages only metadata is kept (they are
outside the measurement frame anyway).

Output: samples_expanded.jsonl, expand_manifest.json
Usage:  python3 expand_sample.py [N_PAGES]
"""
import json
import random
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "samples_expanded.jsonl"
MANIFEST = HERE / "expand_manifest.json"
BASE = (
    "https://datasets-server.huggingface.co/rows"
    "?dataset=allenai/WildChat-1M&config=default&split=train"
)
TOTAL_ROWS = 837_989
PAGE = 100
SEED = 13
RETRIES = 6
WORKERS = 4
DEFAULT_PAGES = 600


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
            return rows
        except Exception as e:  # noqa: BLE001
            last_err = e
            wait = min(2 ** attempt, 30)
            time.sleep(wait)
    raise RuntimeError(f"offset {offset} failed after {RETRIES} attempts: {last_err}")


def slim(item: dict) -> dict:
    row = item["row"]
    lang = row.get("language")
    rec = {
        "row_idx": item["row_idx"],
        "conversation_hash": row.get("conversation_hash"),
        "model": row.get("model"),
        "timestamp": row.get("timestamp"),
        "language": lang,
        "n_turns": len(row.get("conversation") or []),
    }
    if lang == "English":
        rec["conversation"] = row.get("conversation") or []
    return rec


def main() -> None:
    n_pages = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PAGES
    offsets = sorted(random.Random(SEED).sample(range(0, TOTAL_ROWS - PAGE + 1, PAGE), n_pages))

    lock = threading.Lock()
    seen_pages = set()
    seen_row = set()
    written = 0
    errors = []

    with OUT.open("w", encoding="utf-8") as out, ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futures = {ex.submit(fetch, off): off for off in offsets}
        done = 0
        for fut in as_completed(futures):
            off = futures[fut]
            done += 1
            try:
                rows = fut.result()
                recs = [slim(r) for r in rows]
            except Exception as e:  # noqa: BLE001
                errors.append({"offset": off, "error": str(e)})
                print(f"ERROR offset {off}: {e}", flush=True)
                continue
            with lock:
                seen_pages.add(off)
                for rec in recs:
                    if rec["row_idx"] in seen_row:
                        continue
                    seen_row.add(rec["row_idx"])
                    out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    written += 1
                    if written % 2000 == 0:
                        print(f"  ... {written} rows written ({done}/{n_pages} pages)", flush=True)
            if done % 50 == 0:
                print(f"{done}/{n_pages} pages, {written} rows", flush=True)

    manifest = {
        "seed": SEED,
        "requested_pages": n_pages,
        "successful_pages": len(seen_pages),
        "offsets": offsets,
        "n_rows_written": written,
        "errors": errors,
        "endpoint": BASE + "&offset=OFFSET&length=100",
        "note": "Only English rows retain the conversation field.",
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"wrote {written} rows from {len(seen_pages)} pages to {OUT}")
    if errors:
        print(f"{len(errors)} pages failed; see manifest", file=sys.stderr)


if __name__ == "__main__":
    main()
