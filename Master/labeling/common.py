"""Shared definitions for the human labeling round on the 300-case corpus (codebook v2)."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "data" / "coding_sheet_template.csv"
CONTEXTS = ROOT / "results" / "trackA" / "data_local" / "contexts.jsonl"
META = ROOT / "results" / "trackA" / "data_local" / "meta.jsonl"
OUT = ROOT / "results" / "labeling"

DEFAULT_CODERS = ["devansh", "sahil", "zhongyin", "mathew", "xuejun", "zoey"]

# Columns the labeler reads but never edits. `earlier_turns` is added for this corpus so that
# x_persistence (a second or later challenge) can be judged from the thread.
READ_COLS = ["item_id", "domain_hint", "earlier_turns", "question", "assistant_answer", "pushback"]
# The second-opinion sheet asks only for the correctness columns.
CHECK_LABEL_COLS = ["is_pushback", "checkable_claim", "user_claim", "notes"]

USER_CLAIM_VALUES = {"correct", "incorrect", "mixed", "indeterminate"}
PBC_TYPES = {"factual_correction", "clarification_demand", "preference_disagreement", "emotional_pushback"}
# s_bare = 1 only if all of these are blank (codebook v2, section 2).
BARE_EXCLUDES = ["s_alt_answer", "s_counter_evidence", "s_error_pointer", "s_authority",
                 "s_inconsistency", "s_task_correction"]
# pushback_300 workbook letters -> codebook v2 columns (codebook v2, sections 2-4).
AI_LETTER_TO_CODE = {"B": "s_bare", "R": "s_recheck", "A": "s_alt_answer", "E": "s_counter_evidence",
                     "L": "s_error_pointer", "S": "s_authority", "I": "s_inconsistency",
                     "T": "s_task_correction", "P": "x_persistence", "F": "t_frustration"}

YES = {"1", "y", "yes", "true", "x"}


def template_cols():
    with open(TEMPLATE, encoding="utf-8") as f:
        return next(csv.reader(f))


def coding_cols():
    """Template columns with `earlier_turns` inserted before `question`."""
    cols = template_cols()
    i = cols.index("question")
    return cols[:i] + ["earlier_turns"] + cols[i:]


def label_cols():
    return [c for c in template_cols() if c not in ("item_id", "domain_hint", "question", "assistant_answer", "pushback")]


def check_cols():
    return READ_COLS + CHECK_LABEL_COLS


def is_yes(v):
    return str(v or "").strip().lower() in YES


def cell(v):
    return str(v or "").strip()


def read_sheet(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames or [], list(reader)


def write_sheet(path, cols, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def read_jsonl(path):
    """Split on "\\n" only: real chat text contains U+2028/U+2029 (see Master/README.md)."""
    import json
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").split("\n") if l.strip()]
