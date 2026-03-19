"""
Tiny Language Detector — bigram-based language identification.

Works with any language that has a *_bigrams.csv file in the data directory.
Drop in a new CSV and it is automatically picked up — no code changes needed.

Detection logic:
  - A word "matches" a language if all its consecutive bigrams are valid
    (valid_start for the opening bigram, valid_middle for interior bigrams,
     valid_end for the closing bigram).
  - A sentence "passes" if ≥ 80% of its words match the language.
  - A text is classified as the language if ≥ 70% of its sentences pass.
    If no language clears the threshold, the text is "unknown".
"""

import csv
import re
import unicodedata
from pathlib import Path
from typing import Optional


# ── thresholds ────────────────────────────────────────────────────────────────
WORD_MATCH_THRESHOLD   = 0.80   # fraction of bigrams in a word that must be valid
SENTENCE_PASS_THRESHOLD = 0.80  # fraction of words in a sentence that must match
TEXT_MATCH_THRESHOLD   = 0.70   # fraction of sentences that must pass


class BigramTable:
    """Holds the bigram validity rules for one language."""

    def __init__(self, csv_path: str | Path):
        self.language = Path(csv_path).stem.split("_")[0]   # e.g. "dagbani"
        self._table: dict[str, dict[str, bool]] = {}         # bigram → {start, middle, end}
        self._load(csv_path)

    def _load(self, csv_path: str | Path) -> None:
        with open(csv_path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                bigram = row.get("bigram", "").lower().strip()
                # skip blank rows and comment rows (lines starting with #)
                if not bigram or bigram.startswith("#"):
                    continue
                if not all(row.get(k) for k in ("valid_start", "valid_middle", "valid_end")):
                    continue
                self._table[bigram] = {
                    "start":  row["valid_start"].strip().upper() == "Y",
                    "middle": row["valid_middle"].strip().upper() == "Y",
                    "end":    row["valid_end"].strip().upper() == "Y",
                }

    # ── public helpers ────────────────────────────────────────────────────────

    def word_matches(self, word: str) -> bool:
        """
        Return True if every bigram in *word* is valid for its position.

        Position rules
        ──────────────
        len == 2  → the single bigram is checked as both start AND end.
        len >= 3  → first bigram = start, last bigram = end, rest = middle.
        len <= 1  → single-char tokens are skipped (return True).
        """
        word = self._normalise(word)
        if len(word) <= 1:
            return True                       # nothing to check

        bigrams = [word[i:i+2] for i in range(len(word) - 1)]
        n = len(bigrams)

        for idx, bg in enumerate(bigrams):
            if bg not in self._table:
                return False                  # unknown bigram → no match

            row = self._table[bg]

            if n == 1:                        # 2-char word
                if not (row["start"] and row["end"]):
                    return False
            elif idx == 0:
                if not row["start"]:
                    return False
            elif idx == n - 1:
                if not row["end"]:
                    return False
            else:
                if not row["middle"]:
                    return False

        return True

    # ── internal ──────────────────────────────────────────────────────────────

    @staticmethod
    def _normalise(word: str) -> str:
        """Lower-case and strip diacritics so the bigram table can stay ASCII."""
        word = word.lower()
        # decompose → strip combining marks → recompose
        nfd = unicodedata.normalize("NFD", word)
        return "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")


class LanguageDetector:
    """
    Detect the language of a text using bigram pattern matching.

    Automatically loads every *_bigrams.csv file found in data_dir.
    Add a new language at any time by dropping a new CSV into that folder —
    no code changes required.

    Parameters
    ----------
    data_dir : str | Path
        Directory containing *_bigrams.csv files (one per language).
    word_threshold : float
        Minimum fraction of a word's bigrams that must be valid for the word
        to be considered a match  (default 0.80).
    sentence_threshold : float
        Minimum fraction of words in a sentence that must match for the
        sentence to "pass"  (default 0.80).
    text_threshold : float
        Minimum fraction of sentences that must pass for the text to be
        classified as that language  (default 0.70).
    """

    def __init__(
        self,
        data_dir: str | Path = "data",
        word_threshold: float     = WORD_MATCH_THRESHOLD,
        sentence_threshold: float = SENTENCE_PASS_THRESHOLD,
        text_threshold: float     = TEXT_MATCH_THRESHOLD,
    ):
        self.word_threshold     = word_threshold
        self.sentence_threshold = sentence_threshold
        self.text_threshold     = text_threshold

        self.tables: dict[str, BigramTable] = {}
        self._load_tables(Path(data_dir))

    def _load_tables(self, data_dir: Path) -> None:
        for csv_file in sorted(data_dir.glob("*_bigrams.csv")):
            table = BigramTable(csv_file)
            self.tables[table.language] = table
        if not self.tables:
            raise FileNotFoundError(
                f"No *_bigrams.csv files found in '{data_dir}'. "
                "Create one per language, e.g. data/dagbani_bigrams.csv"
            )

    # ── public API ────────────────────────────────────────────────────────────

    def detect(self, text: str) -> dict:
        """
        Classify *text* and return a detailed result dict.

        Returns
        -------
        {
          "language"  : str,          # detected language or "unknown"
          "scores"    : {lang: float},# sentence-pass rate per language
          "sentences" : int,          # number of sentences analysed
          "details"   : {lang: [...]} # per-sentence word-match rates
        }
        """
        sentences = self._split_sentences(text)
        if not sentences:
            return {"language": "unknown", "scores": {}, "sentences": 0, "details": {}}

        scores:  dict[str, float] = {}
        details: dict[str, list]  = {}

        for lang, table in self.tables.items():
            per_sentence = [self._sentence_score(s, table) for s in sentences]
            passing = sum(1 for s in per_sentence if s >= self.sentence_threshold)
            scores[lang]  = passing / len(sentences)
            details[lang] = per_sentence

        # pick best language that clears the text threshold
        candidates = {l: s for l, s in scores.items() if s >= self.text_threshold}
        if candidates:
            detected = max(candidates, key=candidates.__getitem__)
        else:
            detected = "unknown"

        return {
            "language":  detected,
            "scores":    scores,
            "sentences": len(sentences),
            "details":   details,
        }

    def check_language(self, text: str, language: str) -> dict:
        """
        Check whether *text* matches a specific *language* (case-insensitive).

        Returns
        -------
        {
          "match"     : bool,
          "language"  : str,
          "score"     : float,   # sentence-pass rate (0–1)
          "sentences" : int,
          "details"   : [float]  # per-sentence word-match rates
        }
        """
        language = language.lower()
        if language not in self.tables:
            raise ValueError(
                f"Unknown language '{language}'. "
                f"Available: {list(self.tables)}"
            )
        table     = self.tables[language]
        sentences = self._split_sentences(text)
        if not sentences:
            return {"match": False, "language": language, "score": 0.0,
                    "sentences": 0, "details": []}

        per_sentence = [self._sentence_score(s, table) for s in sentences]
        passing      = sum(1 for s in per_sentence if s >= self.sentence_threshold)
        score        = passing / len(sentences)

        return {
            "match":     score >= self.text_threshold,
            "language":  language,
            "score":     score,
            "sentences": len(sentences),
            "details":   per_sentence,
        }

    # ── internal helpers ──────────────────────────────────────────────────────

    def _sentence_score(self, sentence: str, table: BigramTable) -> float:
        """Return fraction of words in *sentence* that match *table*."""
        words = self._tokenise(sentence)
        if not words:
            return 0.0
        matches = sum(1 for w in words if table.word_matches(w))
        return matches / len(words)

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        """Split text into sentences on . ! ? and newlines."""
        parts = re.split(r"[.!?\n]+", text)
        return [p.strip() for p in parts if p.strip()]

    @staticmethod
    def _tokenise(sentence: str) -> list[str]:
        """Return alphabetic tokens only (length ≥ 2)."""
        return [w for w in re.findall(r"[a-zA-ZÀ-ÿ]+", sentence) if len(w) >= 2]
