#!/usr/bin/env python3
"""
scripts/validate_bigrams.py
────────────────────────────
Audit one or more *_bigrams.csv files and report on:
  - Missing expected bigrams (all aa–zz combinations)
  - Rows with invalid Y/N values
  - Bigrams that are listed as valid_start=N AND valid_middle=N AND valid_end=N
    (dead bigrams — they can never appear)
  - Count summary per language

Usage
─────
  python scripts/validate_bigrams.py data/dagbani_bigrams.csv
  python scripts/validate_bigrams.py data/*.csv
  python scripts/validate_bigrams.py data/dagbani_bigrams.csv --strict
"""

import argparse
import csv
import itertools
import string
import sys
from pathlib import Path


VALID_VALUES = {"Y", "N"}
POSITION_COLS = ("valid_start", "valid_middle", "valid_end")


def load_csv(path: Path) -> tuple[list[dict], list[str]]:
    """Return (rows, errors) — errors are human-readable problem strings."""
    errors = []
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            errors.append("File appears empty or has no header.")
            return rows, errors

        missing_cols = [c for c in (*POSITION_COLS, "bigram") if c not in reader.fieldnames]
        if missing_cols:
            errors.append(f"Missing required columns: {missing_cols}")
            return rows, errors

        for lineno, row in enumerate(reader, start=2):
            bigram = row.get("bigram", "").strip().lower()
            if not bigram or bigram.startswith("#"):
                continue
            for col in POSITION_COLS:
                val = row.get(col, "").strip().upper()
                if val not in VALID_VALUES:
                    errors.append(
                        f"Line {lineno}: bigram '{bigram}' has invalid {col}='{row[col]}'"
                    )
            rows.append(row)
    return rows, errors


def all_alphabetic_bigrams() -> set[str]:
    """All 676 lowercase aa–zz bigrams."""
    return {"".join(p) for p in itertools.product(string.ascii_lowercase, repeat=2)}


def audit(path: Path, strict: bool = False) -> dict:
    rows, load_errors = load_csv(path)
    result = {
        "path":          str(path),
        "language":      path.stem.split("_")[0],
        "total_rows":    len(rows),
        "load_errors":   load_errors,
        "invalid_rows":  [],
        "dead_bigrams":  [],
        "missing":       [],
        "ok":            False,
    }

    if load_errors:
        return result

    seen: set[str] = set()
    for row in rows:
        bg = row["bigram"].strip().lower()
        seen.add(bg)

        positions = {col: row[col].strip().upper() == "Y" for col in POSITION_COLS}

        if not any(positions.values()):
            result["dead_bigrams"].append(bg)

    if strict:
        result["missing"] = sorted(all_alphabetic_bigrams() - seen)

    result["ok"] = not result["load_errors"] and not result["invalid_rows"]
    return result


def print_report(audit_result: dict) -> None:
    lang = audit_result["language"].upper()
    path = audit_result["path"]
    ok   = "✅" if audit_result["ok"] else "❌"

    print(f"\n{ok}  [{lang}]  {path}")
    print(f"   Rows loaded   : {audit_result['total_rows']}")

    if audit_result["load_errors"]:
        print("   ⛔ Load errors:")
        for e in audit_result["load_errors"]:
            print(f"      • {e}")

    if audit_result["invalid_rows"]:
        print(f"   ⚠️  Invalid rows ({len(audit_result['invalid_rows'])}):")
        for e in audit_result["invalid_rows"][:10]:
            print(f"      • {e}")
        if len(audit_result["invalid_rows"]) > 10:
            print(f"      … and {len(audit_result['invalid_rows']) - 10} more")

    if audit_result["dead_bigrams"]:
        dbs = ", ".join(audit_result["dead_bigrams"][:20])
        extra = f" … +{len(audit_result['dead_bigrams'])-20} more" if len(audit_result["dead_bigrams"]) > 20 else ""
        print(f"   💀 Dead bigrams (all N) [{len(audit_result['dead_bigrams'])}]: {dbs}{extra}")

    if audit_result["missing"]:
        ms = ", ".join(audit_result["missing"][:20])
        extra = f" … +{len(audit_result['missing'])-20} more" if len(audit_result["missing"]) > 20 else ""
        print(f"   🔍 Missing bigrams [{len(audit_result['missing'])}]: {ms}{extra}")

    if audit_result["ok"] and not audit_result["dead_bigrams"] and not audit_result["missing"]:
        print("   Everything looks good.")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate bigram CSV files.")
    parser.add_argument("files", nargs="+", help="One or more *_bigrams.csv files")
    parser.add_argument(
        "--strict", action="store_true",
        help="Also report bigrams missing from the full aa–zz alphabet"
    )
    args = parser.parse_args(argv)

    all_ok = True
    for f in args.files:
        result = audit(Path(f), strict=args.strict)
        print_report(result)
        if not result["ok"]:
            all_ok = False

    print()
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
