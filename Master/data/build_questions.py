"""Build data/questions_v1.jsonl (unified schema) from the two authored sources.

  python3 data/build_questions.py            # writes questions_v1.jsonl, verifies math answers
  python3 data/build_questions.py --check    # verify only, exit 1 on any mismatch

The hard-tier source (questions_hard_v1.json) is already in the unified schema with its split
frozen. If it is missing, it is regenerated once from ../Sahil/phase2/questions_hard.json with a
seeded 10/10 dev/heldout split (seed 598) and written back as the authored source.
"""
import argparse
import csv
import json
import math
import random
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EASY = HERE / "questions_easy_v1.csv"
HARD = HERE / "questions_hard_v1.json"
HARD_LEGACY = HERE.parent.parent / "Sahil" / "phase2" / "questions_hard.json"
OUT = HERE / "questions_v1.jsonl"
SPLIT_SEED = 598

NUMBER_WORDS = {0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven",
                8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve", 13: "thirteen",
                14: "fourteen", 15: "fifteen", 16: "sixteen", 17: "seventeen", 18: "eighteen",
                19: "nineteen", 20: "twenty"}


def markers_for(short, answer_type):
    m = [str(short)]
    if answer_type == "numeric":
        try:
            v = float(str(short).replace(",", ""))
            if v == int(v):
                if abs(v) >= 1000:
                    m.append(f"{int(v):,}")
                if int(v) in NUMBER_WORDS:
                    m.append(NUMBER_WORDS[int(v)])
        except ValueError:
            pass
    return sorted(set(m), key=len, reverse=True)


def from_easy_csv(path):
    out = []
    for r in csv.DictReader(open(path, encoding="utf-8")):
        out.append({
            "id": r["id"], "tier": "easy", "domain": r["domain"], "split": "dev",
            "question": r["question"], "correct_short": r["correct"], "wrong_short": r["alternative"],
            "answer_type": r["answer_type"],
            "correct_answer_turn": f"The answer is {r['correct']}.",
            "wrong_answer_turn": f"The answer is {r['alternative']}.",
            "correct_markers": markers_for(r["correct"], r["answer_type"]),
            "wrong_markers": markers_for(r["alternative"], r["answer_type"]),
            "evidence": {"correct": "", "wrong": ""},
            "source": {"kind": "authored", "ref": r.get("source", ""), "check": r.get("check", "")},
            "human_verified": r.get("human_verified", ""), "notes": r.get("notes", ""),
        })
    return out


def convert_legacy_hard(path):
    """One-time conversion of Sahil/phase2/questions_hard.json into the unified schema."""
    qs = json.loads(Path(path).read_text())
    ids = sorted(q["id"] for q in qs)
    rng = random.Random(SPLIT_SEED)
    rng.shuffle(ids)
    dev = set(ids[: len(ids) // 2])
    out = []
    for q in sorted(qs, key=lambda x: x["id"]):
        numeric = q["domain"] == "math" and any(c.isdigit() for c in q["correct_short"])
        out.append({
            "id": q["id"], "tier": "hard", "domain": q["domain"],
            "split": "dev" if q["id"] in dev else "heldout",
            "question": q["question"], "correct_short": q["correct_short"], "wrong_short": q["wrong_short"],
            "answer_type": "numeric" if numeric else "string",
            "correct_answer_turn": q["correct_answer_turn"], "wrong_answer_turn": q["wrong_answer_turn"],
            "correct_markers": q["correct_markers"], "wrong_markers": q["wrong_markers"],
            "evidence": {"correct": q["correct_evidence"], "wrong": q["wrong_evidence"]},
            "real_template": q["real_template"],
            "source": {"kind": "wildchat", "ref": q["source"], "source_user_was": q.get("source_user_was", "")},
            "human_verified": "Sahil Sashi (re-derived 2026-10-19)", "notes": "",
        })
    return out


def check_math(qs):
    bad = []
    for q in qs:
        expr = q.get("source", {}).get("check")
        if q["tier"] == "easy" and q["domain"] == "math" and expr:
            try:  # expressions are authored (e.g. "17*23", "math.gcd(48,180)"), evaluated with a tiny namespace
                val = eval(expr, {"__builtins__": {}},
                           {"math": math, "statistics": statistics, "sum": sum, "range": range,
                            "round": round, "abs": abs, "min": min, "max": max})
            except Exception as e:  # noqa: BLE001
                bad.append((q["id"], expr, repr(e)))
                continue
            target = float(q["correct_short"].replace(",", ""))
            if abs(float(val) - target) > max(0.005, 0.005 * abs(target)):  # answers may be rounded
                bad.append((q["id"], expr, val))
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    if not HARD.exists():
        hard = convert_legacy_hard(HARD_LEGACY)
        HARD.write_text(json.dumps(hard, indent=2, ensure_ascii=False) + "\n")
        print(f"wrote {HARD.name} from {HARD_LEGACY} with a {SPLIT_SEED}-seeded 10/10 split")
    hard = json.loads(HARD.read_text())
    easy = from_easy_csv(EASY)
    qs = easy + hard

    required = ["id", "tier", "domain", "split", "question", "correct_short", "wrong_short",
                "answer_type", "correct_markers", "wrong_markers"]
    problems = [(q.get("id"), k) for q in qs for k in required if not q.get(k)]
    ids = [q["id"] for q in qs]
    if len(ids) != len(set(ids)):
        problems.append(("duplicate ids", ""))
    problems += check_math(qs)
    if problems:
        print("PROBLEMS:", problems)
        sys.exit(1)
    if not args.check:
        with OUT.open("w", encoding="utf-8") as f:
            for q in qs:
                f.write(json.dumps(q, ensure_ascii=False) + "\n")
    n_split = {(q["tier"], q["split"]) for q in qs}
    counts = {f"{t}/{s}": sum(1 for q in qs if (q["tier"], q["split"]) == (t, s)) for t, s in sorted(n_split)}
    print(f"{len(qs)} questions OK; math checks passed; splits {counts}")


if __name__ == "__main__":
    main()
