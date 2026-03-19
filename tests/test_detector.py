"""
Tests for the language detector.
Run with:  pytest tests/ -v
"""

import csv
import io
import pytest
from pathlib import Path

from src.detector import BigramTable, LanguageDetector


# ── helpers to build in-memory CSVs ──────────────────────────────────────────

def make_csv(rows: list[dict]) -> str:
    """Serialise a list of bigram dicts to CSV text."""
    fields = ["bigram", "valid_start", "valid_middle", "valid_end",
              "start_count", "middle_count", "end_count"]
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=fields)
    w.writeheader()
    for r in rows:
        w.writerow({**{"start_count": 1, "middle_count": 1, "end_count": 1}, **r})
    return out.getvalue()


def write_csv(tmp_path: Path, name: str, rows: list[dict]) -> Path:
    p = tmp_path / f"{name}_bigrams.csv"
    p.write_text(make_csv(rows))
    return p


# ── fixtures ──────────────────────────────────────────────────────────────────

DAGBANI_ROWS = [
    dict(bigram="di", valid_start="Y", valid_middle="Y", valid_end="Y"),
    dict(bigram="in", valid_start="N", valid_middle="Y", valid_end="Y"),
    dict(bigram="na", valid_start="Y", valid_middle="Y", valid_end="Y"),
    dict(bigram="an", valid_start="Y", valid_middle="Y", valid_end="Y"),
    dict(bigram="ni", valid_start="Y", valid_middle="Y", valid_end="Y"),
]

TWI_ROWS = [
    dict(bigram="me", valid_start="Y", valid_middle="Y", valid_end="Y"),
    dict(bigram="ew", valid_start="N", valid_middle="Y", valid_end="N"),
    dict(bigram="wo", valid_start="Y", valid_middle="Y", valid_end="Y"),
]

EWE_ROWS = [
    dict(bigram="ny", valid_start="Y", valid_middle="Y", valid_end="N"),
    dict(bigram="ye", valid_start="Y", valid_middle="Y", valid_end="Y"),
    dict(bigram="nu", valid_start="Y", valid_middle="Y", valid_end="Y"),
]


@pytest.fixture()
def data_dir(tmp_path):
    write_csv(tmp_path, "dagbani", DAGBANI_ROWS)
    write_csv(tmp_path, "twi",     TWI_ROWS)
    write_csv(tmp_path, "ewe",     EWE_ROWS)
    return tmp_path


@pytest.fixture()
def detector(data_dir):
    return LanguageDetector(data_dir=data_dir)


# ── BigramTable unit tests ────────────────────────────────────────────────────

class TestBigramTable:

    def test_load(self, tmp_path):
        write_csv(tmp_path, "dagbani", DAGBANI_ROWS)
        t = BigramTable(tmp_path / "dagbani_bigrams.csv")
        assert t.language == "dagbani"

    def test_valid_word(self, tmp_path):
        write_csv(tmp_path, "dagbani", DAGBANI_ROWS)
        t = BigramTable(tmp_path / "dagbani_bigrams.csv")
        # "dina": di(start) in(middle) na(end) — all valid
        assert t.word_matches("dina") is True

    def test_invalid_start(self, tmp_path):
        write_csv(tmp_path, "dagbani", DAGBANI_ROWS)
        t = BigramTable(tmp_path / "dagbani_bigrams.csv")
        # "in" has valid_start=N so a word starting with "in" should fail
        assert t.word_matches("inab") is False

    def test_unknown_bigram(self, tmp_path):
        write_csv(tmp_path, "dagbani", DAGBANI_ROWS)
        t = BigramTable(tmp_path / "dagbani_bigrams.csv")
        assert t.word_matches("xyz") is False

    def test_single_char(self, tmp_path):
        write_csv(tmp_path, "dagbani", DAGBANI_ROWS)
        t = BigramTable(tmp_path / "dagbani_bigrams.csv")
        assert t.word_matches("a") is True     # too short to check, skipped


# ── LanguageDetector unit tests ───────────────────────────────────────────────

class TestDetector:

    def test_loads_all_languages(self, detector):
        assert set(detector.tables.keys()) == {"dagbani", "twi", "ewe"}

    def test_missing_data_dir_raises(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        with pytest.raises(FileNotFoundError):
            LanguageDetector(data_dir=empty)

    def test_check_language_unknown_raises(self, detector):
        with pytest.raises(ValueError, match="hausa"):
            detector.check_language("some text", "hausa")

    def test_check_empty_text(self, detector):
        result = detector.check_language("", "dagbani")
        assert result["match"] is False
        assert result["sentences"] == 0

    def test_detect_empty_text(self, detector):
        result = detector.detect("")
        assert result["language"] == "unknown"

    def test_check_match_structure(self, detector):
        result = detector.check_language("dina nani", "dagbani")
        assert "match"     in result
        assert "score"     in result
        assert "sentences" in result
        assert "details"   in result

    def test_detect_structure(self, detector):
        result = detector.detect("dina nani")
        assert "language"  in result
        assert "scores"    in result
        assert "sentences" in result
        assert "details"   in result

    def test_thresholds_respected(self, data_dir):
        # set a very high text_threshold — nothing should match
        strict = LanguageDetector(data_dir=data_dir, text_threshold=1.01)
        result = strict.detect("dina nani dina nani")
        assert result["language"] == "unknown"

    def test_low_threshold_always_matches(self, data_dir):
        # set text_threshold to 0 — best language always wins
        loose = LanguageDetector(data_dir=data_dir, text_threshold=0.0)
        result = loose.detect("dina")
        assert result["language"] != "unknown"
