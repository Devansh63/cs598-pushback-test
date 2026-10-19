# Phase 1 — dataset inspection notes

## Endpoint

`https://datasets-server.huggingface.co/rows?dataset=allenai/WildChat-1M&config=default&split=train&offset=OFFSET&length=100`

- Response keys: `features`, `rows`, `num_rows_total`, `num_rows_per_page`, `partial`.
- `num_rows_total` for `split=train`: **837,989**. `num_rows_per_page`: 100.
- Each element of `rows` has keys `row_idx`, `row`, `truncated_cells`.

## `row` fields (observed on offset 0)

| field | type | example / notes |
|---|---|---|
| `conversation_hash` | str | `c9ec5b440fbdd2a269333dd241f32f64` — 32-hex id |
| `model` | str | `gpt-4-0314` |
| `timestamp` | str | `2023-04-09T00:02:53Z` |
| `conversation` | list[dict] | `[{role, content}, ...]`; roles `user` / `assistant` |
| `turn` | int | `1` |
| `language` | str | `English` (natural-language name, not an ISO code) |
| `openai_moderation` | list[dict] | one entry per turn |
| `detoxify_moderation` | list[dict] | one entry per turn |
| `toxic` | bool | false |
| `redacted` | bool | false |
| `state` | str | `Texas` |
| `country` | str | `United States` |
| `hashed_ip` | str | hashed |
| `header` | dict | `accept-language`, `user-agent` |

## Sampling and pair construction

- 20 requests x length 100 at offsets 0, 1000, 2000, ..., 19000 = up to 2,000 conversations.
- `samples.jsonl` stores one line per conversation: `{"row_idx": N, "row": {...}}` (the `row` object
  verbatim plus `row_idx`).
- Pair = adjacent `(assistant turn, immediately following user turn)` inside `conversation`.
  Pairs that would include a non-adjacent turn or a system turn are not created.
- Language filter: `language == "English"` (the field exists for every row inspected). All non-English
  conversations are dropped and the count is reported in `measurement.md`.

## Cue suite (verbatim)

```
r"\b(that'?s (wrong|incorrect|not right)|you'?re wrong|are you sure|no,? (that|it)'?s|i don'?t think (that|so)|actually,? (it|the)|incorrect|not correct|wrong answer|you made (a|an) (mistake|error)|recheck|re-?check|that is not what|it'?s actually)\b"
```

Applied case-insensitively (`re.IGNORECASE`) to the **user** turn of each pair.

## Environment

- `python3` 3.14.3, curl 8.7.1. All HTTP via `subprocess` + `curl` (macOS CA store is broken for urllib).
- Model: DeepSeek `deepseek-flash`, `temperature=0`, JSON mode (`response_format={"type":"json_object"}`),
  falling back to plain text + JSON extraction if the parameter is rejected.

## Follow-up: expanded measurement frame

The 2,000-conversation pilot yielded only **6 candidate pairs** (3.0 per 1,000
conversations), too few for a 150-candidate precision estimate. The rows API was
retried with 600 random pages (seed 13), but the server began returning HTTP 429
and the run was stopped after 18,859 rows (64 candidates, 3.4 per 1,000).

The final frame therefore comes from the **official parquet files** of the same
dataset (train split), which are equivalent row-for-row:

- `data/train-00000-of-00014.parquet`, `...-00006-...`, `...-00007-...`,
  `...-00013-...` (early, middle, late corpus positions).
- 15,000 rows sampled uniformly at random from each shard (seed 13) =
  **60,000 conversations**, 34,800 English, 37,857 usable English pairs,
  **159 candidates**.
- Parquet schema differs from the rows API only in that each `conversation`
  element also carries per-turn metadata (`country`, `hashed_ip`, `header`,
  `language`, `redacted`, `state`, `timestamp`, `toxic`, `turn_identifier`).
  The analysis keeps only `role` and `content`.
- `row_idx` in `samples_frame.jsonl` is synthetic: `shard_index * 1_000_000 +
  parquet_row_index`. `frame_manifest.json` records all counts.

The pilot (`samples.jsonl`, `pairs.jsonl`, `pair_stats.json`) is retained as a
yield check and is not mixed into the precision/recall frame.

