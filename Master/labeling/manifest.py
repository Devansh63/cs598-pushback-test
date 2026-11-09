"""A text-free record of the labeling sheets that were handed out, safe for the public repo.

  python3 labeling/manifest.py            # write results/labeling/sheets_manifest.csv
  python3 labeling/manifest.py --check    # verify returned sheets against it

The sheets hold verbatim user turns, so they stay out of git (results/.gitignore). The manifest
records, per sheet: who it went to, how many cases, a SHA-256 of its sorted case ids, and a SHA-256
of the file as sent. --check confirms a returned sheet holds exactly the cases that went out (its
file hash changes once labels are filled; the case-id hash must not). When the case ids differ,
it lists the missing and extra ids, using assignments.csv.
"""
import argparse
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from labeling.common import OUT, cell, find_sheet, read_sheet, write_sheet  # noqa: E402

NAME = "sheets_manifest.csv"
COLS = ["sheet", "labeler", "phase", "rows", "case_ids_sha256", "file_sha256", "bytes", "drive_location"]
PHASES = ("pilot", "coding", "check")
DRIVE_ROOT = "CS598-Group6 / Labeling"


def ids_of(path):
    return [cell(r.get("item_id")) for r in read_sheet(path)[1]]


def ids_hash(ids):
    return hashlib.sha256("\n".join(sorted(ids)).encode("utf-8")).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sheets(d):
    """(stem, phase, labeler, path) for every handed-out sheet in d, xlsx preferred."""
    stems = sorted({p.stem for p in Path(d).glob("*") if p.suffix in (".xlsx", ".csv") and p.stem.startswith(tuple(f"{x}_" for x in PHASES))})
    for stem in stems:
        phase, labeler = stem.split("_", 1)
        yield stem, phase, labeler, find_sheet(d, stem)


def expected_ids(assignments, phase, labeler):
    if phase == "pilot":
        return {r["item_id"] for r in assignments if r.get("phase") == "pilot" and labeler in (r["coder"], r["checker"])}
    who = "coder" if phase == "coding" else "checker"
    return {r["item_id"] for r in assignments if r.get("phase", "main") == "main" and r[who] == labeler}


def write(d, force=False):
    if (Path(d) / NAME).exists() and not force:
        sys.exit(f"{Path(d) / NAME} exists: it records the sheets as sent. Use --check, or --force for a new round.")
    rows = []
    for stem, phase, labeler, path in sheets(d):
        ids = ids_of(path)
        rows.append({"sheet": path.name, "labeler": labeler, "phase": phase, "rows": len(ids),
                     "case_ids_sha256": ids_hash(ids), "file_sha256": file_hash(path), "bytes": path.stat().st_size,
                     "drive_location": f"{DRIVE_ROOT} / {labeler.replace('_', ' ').title()}"})
    write_sheet(Path(d) / NAME, COLS, rows)
    for r in rows:
        print(f"{r['sheet']:<24} {r['rows']:>4} cases  ids {r['case_ids_sha256'][:12]}  -> {r['drive_location']}")
    return rows


def check(d):
    d = Path(d)
    manifest = read_sheet(d / NAME)[1]
    asg_path = d / "assignments.csv"
    assignments = read_sheet(asg_path)[1] if asg_path.exists() else []
    errors = 0
    for m in manifest:
        stem = Path(m["sheet"]).stem
        path = find_sheet(d, stem)
        if path is None:
            print(f"{m['sheet']:<24} not back yet")
            continue
        ids = ids_of(path)
        if ids_hash(ids) == m["case_ids_sha256"] and len(ids) == int(m["rows"]):
            state = "unchanged since sent" if file_hash(path) == m["file_sha256"] else "same cases, labels added"
            print(f"{path.name:<24} ok ({len(ids)} cases, {state})")
            continue
        errors += 1
        msg = f"{path.name:<24} ERROR: case ids differ from what was sent ({len(ids)} rows, sent {m['rows']})"
        if assignments:
            want, have = expected_ids(assignments, m["phase"], m["labeler"]), set(ids)
            dupes = len(ids) - len(have)
            msg += f"; missing {sorted(want - have)}; extra {sorted(have - want)}" + (f"; {dupes} duplicate row(s)" if dupes else "")
        print(msg)
    return errors


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(OUT))
    ap.add_argument("--check", action="store_true", help="verify returned sheets against the manifest")
    ap.add_argument("--force", action="store_true", help="rewrite the manifest (new round of sheets only)")
    a = ap.parse_args(argv)
    if a.check:
        n = check(a.dir)
        if n:
            sys.exit(1)
        return n
    return write(a.dir, a.force)


if __name__ == "__main__":
    main()
