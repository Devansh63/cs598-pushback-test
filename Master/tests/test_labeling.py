"""Labeling round tools on a synthetic corpus: sheets are blind, checks catch codebook errors,
and the comparison routes correctness disagreements to the right resolver."""
import json

import pytest

from labeling import check_sheets, compare, make_sheets
from labeling.common import coding_cols, check_cols, read_sheet, write_sheet

CODERS = ["ann", "bob", "cat"]


def fake_corpus(tmp_path, n=12):
    ctx, meta = tmp_path / "contexts.jsonl", tmp_path / "meta.jsonl"
    with open(ctx, "w", encoding="utf-8") as f, open(meta, "w", encoding="utf-8") as g:
        for k in range(n):
            eid = f"PB_{k:04x}"
            msgs = [{"index": 1, "role": "user", "flag": "", "content": f"earlier question {k}"},
                    {"index": 2, "role": "assistant", "flag": "", "content": "earlier answer"},
                    {"index": 3, "role": "user", "flag": "", "content": f"Is {k} prime? mail me at a.b@example.com"},
                    {"index": 4, "role": "assistant", "flag": "PRECEDING ASSISTANT ANSWER", "content": f"answer {k}"},
                    {"index": 5, "role": "user", "flag": "TARGET USER TURN", "content": f"wrong really {k}"}]
            f.write(json.dumps({"event_id": eid, "messages": msgs, "target_index": 5}) + "\n")
            g.write(json.dumps({"event_id": eid, "subthemes_ai": ["B — Bare disagreement", "R — Recheck"]}) + "\n")
    return ctx, meta


def build(tmp_path):
    ctx, meta = fake_corpus(tmp_path)
    out = tmp_path / "labeling"
    make_sheets.main(["--coders", *CODERS, "--contexts", str(ctx), "--out", str(out)])
    return out, meta


def test_sheets_are_blind_balanced_and_scrubbed(tmp_path):
    out, _ = build(tmp_path)
    asg = read_sheet(out / "assignments.csv")[1]
    assert len(asg) == 12 and len({r["item_id"] for r in asg}) == 12
    assert all(len({r["coder"], r["checker"], r["resolver"]}) == 3 for r in asg)
    for c in CODERS:
        cols, rows = read_sheet(out / f"coding_{c}.csv")
        assert cols == coding_cols() and len(rows) == 4
        assert all(r[k] == "" for r in rows for k in ("is_pushback", "s_bare", "user_claim", "pbc_type"))
        assert not any("subtheme" in k or "ai" in k.split("_") for k in cols)
        assert all("[EMAIL]" in r["question"] and "earlier question" in r["earlier_turns"] for r in rows)
        assert all(" " in r["pushback"] for r in rows)          # text kept whole, not split
        ccols, crows = read_sheet(out / f"check_{c}.csv")
        assert ccols == check_cols()
        mine = {r["item_id"] for r in rows}
        checked = {r["item_id"] for r in crows}
        assert not (mine & checked)                                     # nobody checks their own batch


def test_refuses_to_overwrite(tmp_path):
    ctx, _ = fake_corpus(tmp_path)
    out = tmp_path / "labeling"
    make_sheets.main(["--coders", *CODERS, "--contexts", str(ctx), "--out", str(out)])
    with pytest.raises(SystemExit):
        make_sheets.main(["--coders", *CODERS, "--contexts", str(ctx), "--out", str(out)])


def good_row(item):
    return {"item_id": item, "is_pushback": "1", "checkable_claim": "1", "s_alt_answer": "1",
            "user_claim": "incorrect", "pbc_type": "factual_correction", "notes": "7 x 13 = 91"}


def test_check_catches_codebook_errors(tmp_path):
    cols = coding_cols()
    ok = [good_row("a"), {"item_id": "b", "is_pushback": "0"}, {"item_id": "c", "is_pushback": "0", "x_jailbreak": "1"}]
    errors, warnings = check_sheets.check_rows(cols, ok)
    assert errors == [] and warnings == []
    bad = [dict(good_row("d"), s_bare="1"),                       # s_bare with an alternative
           dict(good_row("e"), user_claim=""),                    # checkable but no claim
           dict(good_row("f"), pbc_type="factual"),               # invalid type
           {"item_id": "g", "is_pushback": "0", "s_bare": "1"},   # labels after a 0
           dict(good_row("h"), user_claim="wrong"),               # invalid claim value
           {"item_id": "i", "is_pushback": ""}]                   # not labeled yet
    errors, _ = check_sheets.check_rows(cols, bad)
    text = "\n".join(errors)
    for item in "defgh":
        assert f"({item})" in text
    assert "1 row(s) not labeled yet" in text
    assert check_sheets.check_rows(["item_id", "pushback"], [])[0]  # renamed/deleted columns


def fill(out, person, kind, fn):
    path = out / f"{kind}_{person}.csv"
    cols, rows = read_sheet(path)
    write_sheet(path, cols, [dict(r, **fn(r)) for r in rows])


def test_compare_routes_disagreements(tmp_path):
    out, meta = build(tmp_path)
    asg = {r["item_id"]: r for r in read_sheet(out / "assignments.csv")[1]}
    first = sorted(asg)[0]
    label = lambda r: {"is_pushback": "1", "checkable_claim": "1", "s_bare": "1", "s_recheck": "1",
                       "user_claim": "incorrect", "pbc_type": "clarification_demand", "notes": "src"}
    flip = lambda r: dict(label(r), user_claim="correct" if r["item_id"] == first else "incorrect")
    for c in CODERS:
        fill(out, c, "coding", label)
        fill(out, c, "check", flip)
    final, pairs = compare.main(["--dir", str(out), "--meta", str(meta)])
    assert final[first] == ("", "pending")
    assert sum(1 for v in final.values() if v == ("incorrect", "agreed")) == 11
    resolver = asg[first]["resolver"]
    rows = read_sheet(out / f"resolve_{resolver}.csv")[1]
    assert [r["item_id"] for r in rows] == [first]
    # the resolver settles it; a re-run keeps their answer and marks it resolved
    write_sheet(out / f"resolve_{resolver}.csv", compare.RESOLVE_COLS, [dict(rows[0], user_claim_final="correct")])
    final, _ = compare.main(["--dir", str(out), "--meta", str(meta)])
    assert final[first] == ("correct", "resolved")
    summary = (out / "summary.md").read_text()
    assert "| s_bare | 12 | n/a | 1.00 | 1.00 |" in summary    # human = AI on every case: one category only
