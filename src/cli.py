#!/usr/bin/env python3
"""
Tiny Language Detector — command-line interface.

Usage examples
──────────────
# Auto-detect language
tiny-detect detect "O di yɛra a saa"

# Check against a specific language
tiny-detect check dagbani "O di yɛra a saa"

# List all languages currently loaded
tiny-detect list

# Pipe text from a file
cat mytext.txt | tiny-detect detect -

# Verbose output (per-sentence scores)
tiny-detect detect --verbose "O di yɛra a saa"

# JSON output
tiny-detect --json detect "O di yɛra a saa"
"""

import argparse
import json
import sys
from pathlib import Path

from .detector import LanguageDetector


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tiny-detect",
        description=(
            "Lightweight bigram-based language detector.\n"
            "Any *_bigrams.csv file in --data-dir is loaded automatically."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--data-dir", default="data",
        help="Directory containing *_bigrams.csv files (default: ./data)"
    )
    parser.add_argument(
        "--word-threshold", type=float, default=0.80,
        help="Min bigram validity fraction per word (default: 0.80)"
    )
    parser.add_argument(
        "--sentence-threshold", type=float, default=0.80,
        help="Min word-match fraction per sentence (default: 0.80)"
    )
    parser.add_argument(
        "--text-threshold", type=float, default=0.70,
        help="Min sentence-pass fraction for positive ID (default: 0.70)"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Print per-sentence scores"
    )
    parser.add_argument(
        "--json", "-j", action="store_true",
        help="Output full result as JSON"
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # list sub-command
    sub.add_parser("list", help="List all languages loaded from the data directory")

    # detect sub-command
    detect_p = sub.add_parser("detect", help="Auto-detect the language of TEXT")
    detect_p.add_argument(
        "text", nargs="?", default="-",
        help="Text to analyse, or '-' to read from stdin (default)"
    )

    # check sub-command
    check_p = sub.add_parser(
        "check",
        help="Check TEXT against a specific LANGUAGE (use 'list' to see available)"
    )
    check_p.add_argument(
        "language",
        help="Language name — must match a *_bigrams.csv filename stem"
    )
    check_p.add_argument(
        "text", nargs="?", default="-",
        help="Text to analyse, or '-' to read from stdin (default)"
    )

    return parser


def read_text(raw: str) -> str:
    if raw == "-":
        return sys.stdin.read()
    p = Path(raw)
    if p.exists():
        return p.read_text(encoding="utf-8")
    return raw


def make_detector(args) -> LanguageDetector:
    return LanguageDetector(
        data_dir=args.data_dir,
        word_threshold=args.word_threshold,
        sentence_threshold=args.sentence_threshold,
        text_threshold=args.text_threshold,
    )


def cmd_list(detector: LanguageDetector, args) -> None:
    langs = sorted(detector.tables.keys())
    if args.json:
        print(json.dumps({"languages": langs}))
        return
    print(f"\n  Loaded languages ({len(langs)}):")
    for lang in langs:
        n = len(detector.tables[lang]._table)
        print(f"    • {lang:<20}  {n} bigrams")
    print()


def cmd_detect(detector: LanguageDetector, args) -> None:
    text   = read_text(args.text)
    result = detector.detect(text)

    if args.json:
        print(json.dumps(result, indent=2))
        return

    lang = result["language"]
    print(f"\n🔍 Detected language : {lang.upper() if lang != 'unknown' else 'UNKNOWN'}")
    print(f"   Sentences analysed: {result['sentences']}")
    print()
    for lang_name, score in sorted(result["scores"].items()):
        bar = "█" * int(score * 20)
        print(f"   {lang_name:<20} {score:5.1%}  {bar}")

    if args.verbose and result.get("details"):
        print("\n   Per-sentence word-match rates:")
        for lang_name, sents in result["details"].items():
            print(f"   [{lang_name}]")
            for i, s in enumerate(sents, 1):
                flag = "✓" if s >= args.sentence_threshold else "✗"
                print(f"     Sentence {i}: {s:.1%} {flag}")
    print()


def cmd_check(detector: LanguageDetector, args) -> None:
    text   = read_text(args.text)
    result = detector.check_language(text, args.language)

    if args.json:
        print(json.dumps(result, indent=2))
        return

    match  = result["match"]
    lang   = result["language"]
    score  = result["score"]
    symbol = "✅" if match else "❌"
    print(f"\n{symbol}  Text {'MATCHES' if match else 'does NOT match'} {lang.upper()}")
    print(f"   Sentence-pass rate : {score:.1%}  (threshold: {args.text_threshold:.0%})")
    print(f"   Sentences analysed : {result['sentences']}")

    if args.verbose:
        print("\n   Per-sentence word-match rates:")
        for i, s in enumerate(result["details"], 1):
            flag = "✓" if s >= args.sentence_threshold else "✗"
            print(f"     Sentence {i}: {s:.1%} {flag}")
    print()


def main(argv=None):
    parser = build_parser()
    args   = parser.parse_args(argv)

    try:
        detector = make_detector(args)
    except FileNotFoundError as e:
        print(f"\n⛔  {e}\n", file=sys.stderr)
        sys.exit(1)

    if args.command == "list":
        cmd_list(detector, args)
    elif args.command == "detect":
        cmd_detect(detector, args)
    elif args.command == "check":
        try:
            cmd_check(detector, args)
        except ValueError as e:
            langs = sorted(detector.tables.keys())
            print(f"\n⛔  {e}", file=sys.stderr)
            print(f"   Available: {', '.join(langs)}", file=sys.stderr)
            print("   Tip: run 'tiny-detect list' to see all loaded languages.\n",
                  file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
