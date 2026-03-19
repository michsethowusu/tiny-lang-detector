#!/usr/bin/env python3
"""
scripts/batch_detect.py
────────────────────────
Run language detection over a folder of .txt files (or a CSV of texts)
and write results to a CSV report.

Works with any languages loaded from the data directory.

Usage
─────
  # Detect all .txt files in a folder
  python scripts/batch_detect.py --input-dir texts/ --output results.csv

  # Detect texts listed in a CSV (must have a 'text' column; optional 'id' column)
  python scripts/batch_detect.py --input-csv my_texts.csv --output results.csv

  # Check against a specific language only
  python scripts/batch_detect.py --input-dir texts/ --output results.csv --language dagbani

  # Custom data dir
  python scripts/batch_detect.py --input-dir texts/ --output results.csv --data-dir path/to/data
"""

import argparse
import csv
import sys
import textwrap
from pathlib import Path

# allow running from repo root without installing
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.detector import LanguageDetector


def iter_texts_from_dir(input_dir: Path):
    """Yield (id, text) pairs from .txt files in a directory."""
    files = sorted(input_dir.glob("*.txt"))
    if not files:
        raise FileNotFoundError(f"No .txt files found in '{input_dir}'")
    for f in files:
        yield f.stem, f.read_text(encoding="utf-8", errors="replace")


def iter_texts_from_csv(input_csv: Path):
    """Yield (id, text) pairs from a CSV file with a 'text' column."""
    with open(input_csv, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if "text" not in (reader.fieldnames or []):
            raise ValueError(f"CSV '{input_csv}' must have a 'text' column.")
        for i, row in enumerate(reader):
            id_ = row.get("id") or row.get("ID") or str(i + 1)
            yield id_, row["text"]


def run_batch(
    texts,
    detector: LanguageDetector,
    output_csv: Path,
    language: str | None = None,
) -> None:
    fieldnames = ["id", "text_preview", "language", "match", "score", "sentences"]
    # add per-language score columns when auto-detecting
    lang_cols = sorted(detector.tables.keys())
    if language is None:
        fieldnames += [f"score_{l}" for l in lang_cols]

    total = matched = 0

    with open(output_csv, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()

        for id_, text in texts:
            total += 1
            preview = textwrap.shorten(text.replace("\n", " "), width=60)

            if language:
                result = detector.check_language(text, language)
                row = {
                    "id":           id_,
                    "text_preview": preview,
                    "language":     language,
                    "match":        result["match"],
                    "score":        f"{result['score']:.3f}",
                    "sentences":    result["sentences"],
                }
                if result["match"]:
                    matched += 1
            else:
                result = detector.detect(text)
                row = {
                    "id":           id_,
                    "text_preview": preview,
                    "language":     result["language"],
                    "match":        result["language"] != "unknown",
                    "score":        "",
                    "sentences":    result["sentences"],
                }
                for l in lang_cols:
                    row[f"score_{l}"] = f"{result['scores'].get(l, 0):.3f}"
                if result["language"] != "unknown":
                    matched += 1

            writer.writerow(row)
            print(f"  [{total:>4}] {id_:<30} → {row['language']}")

    print(f"\n{'─'*50}")
    print(f"  Processed : {total}")
    print(f"  Matched   : {matched}")
    print(f"  Unknown   : {total - matched}")
    print(f"  Output    : {output_csv}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Batch language detection.")
    src_group = parser.add_mutually_exclusive_group(required=True)
    src_group.add_argument("--input-dir", type=Path, help="Folder of .txt files")
    src_group.add_argument("--input-csv", type=Path, help="CSV file with a 'text' column")

    parser.add_argument("--output",   "-o", type=Path, default=Path("results.csv"),
                        help="Output CSV path (default: results.csv)")
    parser.add_argument("--language", "-l", default=None,
                        help="Check against a specific language instead of auto-detect")
    parser.add_argument("--data-dir", default="data",
                        help="Directory with *_bigrams.csv files (default: data)")
    parser.add_argument("--text-threshold",     type=float, default=0.70)
    parser.add_argument("--sentence-threshold", type=float, default=0.80)
    args = parser.parse_args(argv)

    detector = LanguageDetector(
        data_dir=args.data_dir,
        text_threshold=args.text_threshold,
        sentence_threshold=args.sentence_threshold,
    )

    if args.input_dir:
        texts = list(iter_texts_from_dir(args.input_dir))
    else:
        texts = list(iter_texts_from_csv(args.input_csv))

    print(f"\nDetecting {len(texts)} text(s)…\n")
    run_batch(texts, detector, args.output, language=args.language)


if __name__ == "__main__":
    main()
