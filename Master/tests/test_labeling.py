"""Labeling round tools on a synthetic corpus: sheets are blind and balanced, Excel files round-trip,
checks catch codebook errors, and the comparison routes correctness disagreements to the resolver."""
import json

import pytest
from openpyxl import load_workbook

from labeling import check_sheets, compare, make_sheets, manifest
from labeling.common import check_cols, coding_cols, read_sheet, write_sheet

SIX = ["ann", "bob", "cat"]


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


def build(tmp_path, *extra, n=12):
    ctx, meta = fake_corpus(tmp_path, n)
    out = tmp_path / "labeling"
    make_sheets.main([*extra, "--contexts", str(ctx), "--out", str(out)])
    return out, meta


def test_rotation_sheets_are_blind_balanced_and_scrubbed(tmp_path):
    out, _ = build(tmp_path, "--coders", *SIX, "--format", "csv")
    asg = read_sheet(out / "assignments.csv")[1]
    assert len(asg) == 12 and len({r["item_id"] for r in asg}) == 12
    assert all(len({r["coder"], r["checker"], r["resolver"]}) == 3 for r in asg)
    for c in SIX:
        cols, rows = read_sheet(out / f"coding_{c}.csv")
        assert cols == coding_cols() and len(rows) == 4
        assert all(r[k] == "" for r in rows for k in ("is_pushback", "s_bare", "user_claim", "pbc_type"))
        assert all("[EMAIL]" in r["question"] and "earlier question" in r["earlier_turns"] for r in rows)
        assert all(" " in r["pushback"] for r in rows)          # text kept whole, not split
        ccols, crows = read_sheet(out / f"check_{c}.csv")
        assert ccols == check_cols()
        assert not ({r["item_id"] for r in rows} & {r["item_id"] for r in crows})   # never check yourself


def test_pair_design_pilot_then_split(tmp_path):
    out, _ = build(tmp_path, "--coders", "la", "lb", "--resolver", "dev", "--pilot", "4", n=14)
    ids = lambda stem: [r["item_id"] for r in read_sheet(out / f"{stem}.xlsx")[1]]
    assert ids("pilot_la") == ids("pilot_lb") and len(ids("pilot_la")) == 4
    assert len(ids("coding_la")) == len(ids("coding_lb")) == 5
    assert set(ids("check_la")) == set(ids("coding_lb")) and set(ids("check_lb")) == set(ids("coding_la"))
    every = set(ids("pilot_la")) | set(ids("coding_la")) | set(ids("coding_lb"))
    assert len(every) == 14
    asg = read_sheet(out / "assignments.csv")[1]
    assert {r["phase"] for r in asg} == {"pilot", "main"} and {r["resolver"] for r in asg} == {"dev"}
    wb = load_workbook(out / "coding_la.xlsx")
    assert wb.sheetnames == ["labels", "How to label"]
    assert len(wb["labels"].data_validations.dataValidation) >= 15      # a dropdown on every label column
    with pytest.raises(SystemExit):                                       # resolver must be a third person
        make_sheets.main(["--coders", "la", "lb", "--resolver", "la", "--contexts", str(tmp_path / "contexts.jsonl"),
                          "--out", str(tmp_path / "other")])


def test_refuses_to_overwrite(tmp_path):
    ctx, _ = fake_corpus(tmp_path)
    out = tmp_path / "labeling"
    make_sheets.main(["--coders", *SIX, "--contexts", str(ctx), "--out", str(out)])
    with pytest.raises(SystemExit):
        make_sheets.main(["--coders", *SIX, "--contexts", str(ctx), "--out", str(out)])


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


def test_excel_round_trip_numbers_come_back_as_text(tmp_path):
    p = tmp_path / "s.xlsx"
    write_sheet(p, coding_cols(), [dict(good_row("a"), s_alt_answer=1, is_pushback=1.0)])
    cols, rows = read_sheet(p)
    assert cols == coding_cols() and rows[0]["is_pushback"] == "1" and rows[0]["s_alt_answer"] == "1"
    assert check_sheets.check_rows(cols, rows) == ([], [])


def fill(out, stem, fn):
    path = next(p for p in (out / f"{stem}.xlsx", out / f"{stem}.csv") if p.exists())
    cols, rows = read_sheet(path)
    write_sheet(path, cols, [dict(r, **fn(r)) for r in rows])


def label(r):
    return {"is_pushback": "1", "checkable_claim": "1", "s_bare": "1", "s_recheck": "1",
            "user_claim": "incorrect", "pbc_type": "clarification_demand", "notes": "src"}


def test_compare_pair_design_routes_to_resolver(tmp_path):
    out, meta = build(tmp_path, "--coders", "la", "lb", "--resolver", "dev", "--pilot", "4", n=14)
    asg = read_sheet(out / "assignments.csv")[1]
    pilot_item = next(r["item_id"] for r in asg if r["phase"] == "pilot")
    main_item = next(r["item_id"] for r in asg if r["phase"] == "main" and r["coder"] == "la")
    for p in ("la", "lb"):
        fill(out, f"pilot_{p}", lambda r, p=p: dict(label(r), user_claim="correct" if (p == "lb" and r["item_id"] == pilot_item) else "incorrect"))
        fill(out, f"coding_{p}", label)
        fill(out, f"check_{p}", lambda r: dict(label(r), user_claim="mixed" if r["item_id"] == main_item else "incorrect"))
    final, _ = compare.main(["--dir", str(out), "--meta", str(meta)])
    assert final[pilot_item] == ("", "pending") and final[main_item] == ("", "pending")
    assert sum(1 for v in final.values() if v == ("incorrect", "agreed")) == 12
    rows = read_sheet(out / "resolve_dev.xlsx")[1]
    assert sorted(r["item_id"] for r in rows) == sorted([pilot_item, main_item])
    summary = (out / "summary.md").read_text()
    assert "## Pilot: code agreement" in summary and "| s_bare | 14 | n/a | 1.00 | 1.00 |" in summary
    # the resolver settles both; a re-run keeps their answers
    write_sheet(out / "resolve_dev.xlsx", compare.RESOLVE_COLS,
                [dict(r, user_claim_final="correct" if r["item_id"] == pilot_item else "not_checkable") for r in rows])
    final, _ = compare.main(["--dir", str(out), "--meta", str(meta)])
    assert final[pilot_item] == ("correct", "resolved") and final[main_item] == ("", "excluded")


def test_manifest_has_no_text_and_checks_returned_sheets(tmp_path, capsys):
    out, _ = build(tmp_path, "--coders", "la", "lb", "--resolver", "dev", "--pilot", "4", n=14)
    rows = manifest.main(["--dir", str(out)])
    assert sorted(r["sheet"] for r in rows) == sorted(f"{p}_{x}.xlsx" for p in ("pilot", "coding", "check") for x in ("la", "lb"))
    text = (out / manifest.NAME).read_text()
    assert "earlier question" not in text and "wrong really" not in text and "PB_" not in text   # no text, no ids
    assert manifest.main(["--dir", str(out), "--check"]) == 0
    fill(out, "coding_la", label)                                       # labels added: still the same cases
    assert manifest.main(["--dir", str(out), "--check"]) == 0
    assert "same cases, labels added" in capsys.readouterr().out
    cols, rs = read_sheet(out / "check_lb.xlsx")
    write_sheet(out / "check_lb.xlsx", cols, rs[1:])                     # a row deleted
    with pytest.raises(SystemExit):
        manifest.main(["--dir", str(out), "--check"])
    assert f"missing ['{rs[0]['item_id']}']" in capsys.readouterr().out
    with pytest.raises(SystemExit):                                      # never overwritten by accident
        manifest.main(["--dir", str(out)])


def test_coding_only_split_labels_each_case_once(tmp_path):
    four = ["la", "lb", "lc", "ld"]
    out, meta = build(tmp_path, "--coders", *four, "--no-check", n=12)
    assert sorted(p.name for p in out.glob("*.xlsx")) == sorted(f"coding_{c}.xlsx" for c in four)   # no pilot, no check
    batches = {c: [r["item_id"] for r in read_sheet(out / f"coding_{c}.xlsx")[1]] for c in four}
    assert all(len(v) == 3 for v in batches.values()) and len(set().union(*batches.values())) == 12
    asg = read_sheet(out / "assignments.csv")[1]
    assert all(r["checker"] == "" and r["resolver"] == "" for r in asg)
    first = batches["la"][0]
    for c in four:
        fill(out, f"coding_{c}", lambda r: {"is_pushback": "0"} if r["item_id"] == first else label(r))
    fill(out, "coding_lb", lambda r: {"user_claim": ""} if r["item_id"] == batches["lb"][0] else {})   # one left unfinished
    final, _ = compare.main(["--dir", str(out), "--meta", str(meta)])
    assert final[first] == ("", "excluded") and final[batches["lb"][0]] == ("", "pending")
    assert sum(1 for v in final.values() if v == ("incorrect", "single")) == 10
    assert not list(out.glob("resolve_*"))
    summary = (out / "summary.md").read_text()
    assert "one label per case" in summary and "| s_bare | 11 |" in summary            # human vs AI still reported
    rows = manifest.main(["--dir", str(out), "--drive-root", "Team / Split"])
    assert {r["drive_location"] for r in rows} == {f"Team / Split / {c.title()}" for c in four}
