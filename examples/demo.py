#!/usr/bin/env python3
"""
examples/demo.py
─────────────────
Quick demonstration of the Python API.
Run from the repo root:  python examples/demo.py

Works with however many languages are loaded — no hardcoded names.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.detector import LanguageDetector

# ── setup ──────────────────────────────────────────────────────────────────────
detector = LanguageDetector(data_dir="data")
loaded = sorted(detector.tables.keys())
print(f"Loaded languages: {loaded}\n")
print("=" * 60)


# ── 1. Auto-detect all example files ──────────────────────────────────────────
print("\n[1] Auto-detect from example files\n")

for txt_file in sorted(Path("examples").glob("*_sample.txt")):
    text   = txt_file.read_text(encoding="utf-8")
    result = detector.detect(text)
    lang   = result["language"].upper() if result["language"] != "unknown" else "UNKNOWN"
    scores = "  ".join(f"{l}: {s:.0%}" for l, s in sorted(result["scores"].items()))
    print(f"  {txt_file.name:<28} → {lang:<12}  [{scores}]")


# ── 2. Single-language check for every loaded language ────────────────────────
print("\n\n[2] Each example file checked against its own language\n")

for txt_file in sorted(Path("examples").glob("*_sample.txt")):
    lang = txt_file.stem.replace("_sample", "")
    if lang not in detector.tables:
        continue
    text   = txt_file.read_text(encoding="utf-8")
    result = detector.check_language(text, lang)
    symbol = "✅" if result["match"] else "❌"
    print(f"  {symbol} [{lang:<12}] score={result['score']:.0%}  sentences={result['sentences']}")


# ── 3. Cross-check: each file against every OTHER language ────────────────────
print("\n\n[3] Cross-check (should all be ❌)\n")

for txt_file in sorted(Path("examples").glob("*_sample.txt")):
    own_lang = txt_file.stem.replace("_sample", "")
    if own_lang not in detector.tables:
        continue
    text = txt_file.read_text(encoding="utf-8")
    for lang in loaded:
        if lang == own_lang:
            continue
        result = detector.check_language(text, lang)
        symbol = "✅" if result["match"] else "❌"
        print(f"  {symbol} [{own_lang} text vs {lang:<12}] score={result['score']:.0%}")


# ── 4. Custom thresholds ───────────────────────────────────────────────────────
print("\n\n[4] Custom thresholds demo\n")

if loaded:
    first_lang = loaded[0]
    txt_file   = Path(f"examples/{first_lang}_sample.txt")
    if txt_file.exists():
        sample  = txt_file.read_text(encoding="utf-8")
        strict  = LanguageDetector(data_dir="data", text_threshold=0.90, sentence_threshold=0.90)
        relaxed = LanguageDetector(data_dir="data", text_threshold=0.50, sentence_threshold=0.50)
        rs = strict.check_language(sample, first_lang)
        rr = relaxed.check_language(sample, first_lang)
        print(f"  Language: {first_lang}")
        print(f"  Strict  (90%/90%) → {'MATCH' if rs['match'] else 'NO MATCH'} ({rs['score']:.0%})")
        print(f"  Relaxed (50%/50%) → {'MATCH' if rr['match'] else 'NO MATCH'} ({rr['score']:.0%})")

print("\n" + "=" * 60 + "\n")
