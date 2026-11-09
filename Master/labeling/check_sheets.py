"""Check filled labeling sheets for mistakes before they are handed back.

  python3 labeling/check_sheets.py results/labeling/coding_sahil.csv [more sheets...]

Works on coding_*.csv (codebook v2) and check_*.csv (correctness only). Errors break a codebook
rule and must be fixed; warnings are worth a second look. Exit status 1 if any sheet has errors.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from labeling.common import (BARE_EXCLUDES, PBC_TYPES, USER_CLAIM_VALUES, cell, is_yes,  # noqa: E402
                             read_sheet)

BINARY_OK = {"", "0", "1"}


def check_rows(cols, rows):
    """Return (errors, warnings) as lists of strings."""
    errors, warnings = [], []
    required = {"item_id", "is_pushback", "checkable_claim", "user_claim", "notes"}
    missing = sorted(required - set(cols))
    if missing:
        return [f"missing column(s) {', '.join(missing)}: columns must not be renamed or deleted"], []
    coding = "pbc_type" in cols
    strategies = [c for c in cols if c.startswith("s_")]
    binaries = ["checkable_claim"] + [c for c in cols if c.startswith(("s_", "t_", "x_"))]
    seen, unlabeled = set(), []
    for n, r in enumerate(rows, start=2):           # row 1 is the header
        where = f"row {n} ({cell(r.get('item_id')) or 'no item_id'})"
        e = lambda msg: errors.append(f"{where}: {msg}")
        w = lambda msg: warnings.append(f"{where}: {msg}")
        item = cell(r.get("item_id"))
        if not item:
            e("item_id is empty")
        elif item in seen:
            e("duplicate item_id")
        seen.add(item)
        pb = cell(r.get("is_pushback"))
        if pb == "":
            unlabeled.append(n)
            continue
        if pb not in ("0", "1"):
            e(f"is_pushback must be 1 or 0, found {pb!r}")
            continue
        for c in binaries:
            if cell(r.get(c)) not in BINARY_OK:
                e(f"{c} must be 1 or blank, found {cell(r.get(c))!r}")
        claim = cell(r.get("user_claim")).lower()
        pbc = cell(r.get("pbc_type")).lower()
        if pb == "0":
            filled = [c for c in binaries if c != "x_jailbreak" and is_yes(r.get(c))]
            filled += [c for c, v in (("user_claim", claim), ("pbc_type", pbc)) if v]
            if filled:
                e(f"is_pushback is 0 but {', '.join(filled)} filled: leave the rest of the row blank")
            continue
        if is_yes(r.get("x_jailbreak")):
            e("x_jailbreak is 1 but is_pushback is 1: jailbreak turns get is_pushback = 0")
        if claim and claim not in USER_CLAIM_VALUES:
            e(f"user_claim must be one of {sorted(USER_CLAIM_VALUES)}, found {claim!r}")
        if is_yes(r.get("checkable_claim")) and not claim:
            e("checkable_claim is 1 but user_claim is blank")
        if claim and not is_yes(r.get("checkable_claim")):
            e("user_claim is filled but checkable_claim is blank")
        if claim and not cell(r.get("notes")):
            w("user_claim has no source or calculation in notes")
        if coding:
            if not pbc:
                e("pbc_type is blank: pick exactly one type")
            elif pbc not in PBC_TYPES:
                e(f"pbc_type must be one of {sorted(PBC_TYPES)}, found {pbc!r}")
            if is_yes(r.get("s_bare")):
                clash = [c for c in BARE_EXCLUDES if is_yes(r.get(c))]
                if clash:
                    e(f"s_bare is 1 together with {', '.join(clash)}: s_bare only when none of those apply")
            if not any(is_yes(r.get(c)) for c in strategies):
                w("is_pushback is 1 but no strategy is marked")
    if unlabeled:
        errors.append(f"{len(unlabeled)} row(s) not labeled yet (is_pushback blank), first at row {unlabeled[0]}")
    return errors, warnings


def main(paths):
    bad = False
    for p in paths:
        cols, rows = read_sheet(p)
        errors, warnings = check_rows(cols, rows)
        done = sum(1 for r in rows if cell(r.get("is_pushback")) in ("0", "1"))
        print(f"\n{p}: {done}/{len(rows)} rows labeled, {len(errors)} error(s), {len(warnings)} warning(s)")
        for m in errors:
            print(f"  ERROR    {m}")
        for m in warnings:
            print(f"  warning  {m}")
        bad = bad or bool(errors)
    return 1 if bad else 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1:]))
