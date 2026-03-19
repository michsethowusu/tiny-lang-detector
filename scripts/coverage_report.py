#!/usr/bin/env python3
"""
scripts/coverage_report.py
───────────────────────────
Given a plain-text corpus file and a bigram CSV, print a detailed report
showing which bigrams in the corpus ARE and ARE NOT covered by the table,
and at which positions.

Useful for understanding how well your bigram table covers real text and
for spotting bigrams you might want to add or correct.

Usage
─────
  python scripts/coverage_report.py \
      --corpus corpus/dagbani_sample.txt \
      --bigrams data/dagbani_bigrams.csv

  # Show uncovered bigrams only
  python scripts/coverage_report.py \
      --corpus corpus/dagbani_sample.txt \
      --bigrams data/dagbani_bigrams.csv \
      --uncovered-only

  # Output as CSV
  python scripts/coverage_report.py \
      --corpus corpus/dagbani_sample.txt \
      --bigrams data/dagbani_bigrams.csv \
      --output-csv coverage.csv
"""

import argparse
import csv
import re
import unicodedata
from collections import defaultdict
from pathlib import Path


def normalise(word: str) -> str:
    word = word.lower()
    nfd = unicodedata.normalize("NFD", word)
    return "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")


def extract_bigrams(word: str) -> list[tuple[str, str]]:
    """Return [(bigram, position), …] where position ∈ {start, middle, end}."""
    w = normalise(word)
    if len(w) < 2:
        return []
    bgs = [w[i:i+2] for i in range(len(w) - 1)]
    n = len(bgs)
    result = []
    for i, bg in enumerate(bgs):
        if n == 1:
            result.append((bg, "start"))
            result.append((bg, "end"))
        elif i == 0:
            result.append((bg, "start"))
        elif i == n - 1:
            result.append((bg, "end"))
        else:
            result.append((bg, "middle"))
    return result


def load_bigram_table(csv_path: Path) -> dict[str, dict[str, bool]]:
    table = {}
    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            bg = row.get("bigram", "").strip().lower()
            if not bg or bg.startswith("#"):
                continue
            if not all(row.get(k) for k in ("valid_start", "valid_middle", "valid_end")):
                continue
            table[bg] = {
                "start":  row["valid_start"].strip().upper() == "Y",
                "middle": row["valid_middle"].strip().upper() == "Y",
                "end":    row["valid_end"].strip().upper() == "Y",
            }
    return table


def analyse_corpus(corpus_path: Path, table: dict) -> dict:
    text  = corpus_path.read_text(encoding="utf-8", errors="replace")
    words = [w for w in re.findall(r"[a-zA-ZÀ-ÿ]+", text) if len(w) >= 2]

    # corpus bigram frequencies: {bigram: {position: count}}
    corpus_bgs: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for word in words:
        for bg, pos in extract_bigrams(word):
            corpus_bgs[bg][pos] += 1

    covered   = {}   # bg present in table AND marked valid for that position
    uncovered = {}   # bg seen in corpus but NOT valid (or not in table) for position

    for bg, pos_counts in corpus_bgs.items():
        for pos, count in pos_counts.items():
            entry = table.get(bg)
            valid = entry is not None and entry.get(pos, False)
            key = (bg, pos)
            if valid:
                covered[key]   = count
            else:
                uncovered[key] = count

    total_occurrences  = sum(c for pc in corpus_bgs.values() for c in pc.values())
    covered_count      = sum(covered.values())
    uncovered_count    = sum(uncovered.values())

    return {
        "total_words":        len(words),
        "unique_bigrams":     len(corpus_bgs),
        "total_occurrences":  total_occurrences,
        "covered_count":      covered_count,
        "uncovered_count":    uncovered_count,
        "coverage_rate":      covered_count / total_occurrences if total_occurrences else 0,
        "covered":            covered,
        "uncovered":          uncovered,
    }


def print_report(result: dict, uncovered_only: bool = False, top_n: int = 30) -> None:
    print(f"\n{'═'*60}")
    print(f"  Corpus bigram coverage report")
    print(f"{'═'*60}")
    print(f"  Words analysed       : {result['total_words']:,}")
    print(f"  Unique bigrams seen  : {result['unique_bigrams']:,}")
    print(f"  Total occurrences    : {result['total_occurrences']:,}")
    print(f"  Covered occurrences  : {result['covered_count']:,}")
    print(f"  Uncovered occurr.    : {result['uncovered_count']:,}")
    print(f"  Coverage rate        : {result['coverage_rate']:.1%}")
    print()

    if not uncovered_only:
        print(f"  Top {top_n} covered bigrams (by frequency):")
        for (bg, pos), cnt in sorted(result["covered"].items(), key=lambda x: -x[1])[:top_n]:
            print(f"    {bg}  [{pos:<6}]  {cnt:>6}×")
        print()

    print(f"  Top {top_n} UNCOVERED bigrams (not valid for position, by frequency):")
    if not result["uncovered"]:
        print("    🎉 None — full coverage!")
    else:
        for (bg, pos), cnt in sorted(result["uncovered"].items(), key=lambda x: -x[1])[:top_n]:
            in_table = "in table (marked N)" if bg in {} else "NOT in table"
            print(f"    {bg}  [{pos:<6}]  {cnt:>6}×  ({in_table})")
    print()


def write_csv(result: dict, output_csv: Path) -> None:
    with open(output_csv, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["bigram", "position", "count", "covered"])
        for (bg, pos), cnt in sorted(result["covered"].items()):
            writer.writerow([bg, pos, cnt, True])
        for (bg, pos), cnt in sorted(result["uncovered"].items()):
            writer.writerow([bg, pos, cnt, False])
    print(f"  CSV written → {output_csv}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Bigram coverage report.")
    parser.add_argument("--corpus",  "-c", required=True, type=Path,
                        help="Plain-text corpus file")
    parser.add_argument("--bigrams", "-b", required=True, type=Path,
                        help="*_bigrams.csv file")
    parser.add_argument("--uncovered-only", action="store_true",
                        help="Print only uncovered bigrams")
    parser.add_argument("--top",     type=int, default=30,
                        help="How many bigrams to show per section (default: 30)")
    parser.add_argument("--output-csv", type=Path, default=None,
                        help="Write full results to this CSV path")
    args = parser.parse_args(argv)

    table  = load_bigram_table(args.bigrams)
    result = analyse_corpus(args.corpus, table)
    print_report(result, uncovered_only=args.uncovered_only, top_n=args.top)

    if args.output_csv:
        write_csv(result, args.output_csv)


if __name__ == "__main__":
    main()
