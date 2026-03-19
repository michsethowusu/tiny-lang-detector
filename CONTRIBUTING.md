# Contributing to tiny-lang-detector

Thank you for wanting to contribute! This guide covers the main ways to help.

---

## Adding or improving a bigram table

The most impactful contribution is improving the bigram CSV files.

### File format

Each language needs a file at `data/<language>_bigrams.csv` with these columns:

| Column | Values | Meaning |
|---|---|---|
| `bigram` | two lowercase chars | the bigram, e.g. `an` |
| `valid_start` | `Y` or `N` | can this bigram open a word? |
| `valid_middle` | `Y` or `N` | can it appear mid-word? |
| `valid_end` | `Y` or `N` | can it close a word? |
| `start_count` | int ≥ 0 | corpus frequency at word start |
| `middle_count` | int ≥ 0 | corpus frequency mid-word |
| `end_count` | int ≥ 0 | corpus frequency at word end |

The `*_count` columns are informational — only the `valid_*` columns affect detection.

### How to build a bigram table from a corpus

```python
import csv, re, unicodedata
from collections import defaultdict
from pathlib import Path

def normalise(w):
    nfd = unicodedata.normalize("NFD", w.lower())
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")

def word_to_bigrams(word):
    w = normalise(word)
    return [w[i:i+2] for i in range(len(w)-1)]

corpus = Path("my_corpus.txt").read_text(encoding="utf-8")
words  = [w for w in re.findall(r"[a-zA-ZÀ-ÿ]+", corpus) if len(w) >= 2]

counts = defaultdict(lambda: {"start": 0, "middle": 0, "end": 0})
for word in words:
    bgs = word_to_bigrams(word)
    n = len(bgs)
    for i, bg in enumerate(bgs):
        if n == 1:
            counts[bg]["start"] += 1
            counts[bg]["end"]   += 1
        elif i == 0:       counts[bg]["start"]  += 1
        elif i == n-1:     counts[bg]["end"]    += 1
        else:              counts[bg]["middle"] += 1

# Write CSV — you then manually review and set Y/N based on the counts
with open("data/LANGUAGE_bigrams.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["bigram","valid_start","valid_middle","valid_end",
                "start_count","middle_count","end_count"])
    for bg, c in sorted(counts.items()):
        # Heuristic: mark as valid if count > 0, then manually review
        w.writerow([bg,
                    "Y" if c["start"]  > 0 else "N",
                    "Y" if c["middle"] > 0 else "N",
                    "Y" if c["end"]    > 0 else "N",
                    c["start"], c["middle"], c["end"]])
```

After generating the CSV, run the validator to check it:

```bash
python scripts/validate_bigrams.py data/LANGUAGE_bigrams.csv --strict
```

Then run the coverage report against your corpus to see how well it covers real text:

```bash
python scripts/coverage_report.py \
    --corpus my_corpus.txt \
    --bigrams data/LANGUAGE_bigrams.csv
```

---

## Adding example texts

Add representative text files to `examples/` following the naming pattern:
`examples/<language>_sample.txt`

---

## Running tests

```bash
pip install -e ".[dev]"
pytest -v
```

All tests must pass before submitting a PR.

---

## Submitting a PR

1. Fork the repo and create a branch: `git checkout -b add-hausa-bigrams`
2. Make your changes
3. Run `pytest -v` — all tests must pass
4. Run `python scripts/validate_bigrams.py data/*.csv` — no errors
5. Open a pull request with a clear description of what changed and why

---

## Reporting issues

Please include:
- The text that was misidentified
- Which language it should be
- Output of `lang-detect --json detect "your text here"`
