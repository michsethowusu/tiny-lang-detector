# Tiny Language Detector 🔍

Detect **40 Ghanaian languages** from text using bigram pattern matching.  
No internet, no model, no setup — just Python 3.

## Supported languages

| | | | |
|---|---|---|---|
| Anufo | Anyin | Avatime | Bimoba |
| Bisa | Buli | Chumburung | Dagbani |
| Dangme | Delo | Ewe | Farefare |
| Gikyode | Gonja | Kasem | Konkomba |
| Konni | Kusaal | Lelemi | Mampruli |
| Nawuri | Nkonya | Ntcham | Nzema |
| Paasaal | Sekpele | Selee | Siwu |
| Southern Birifor | Southern Dagaare | Tampulma | Tumulung Sisaala |
| Tuwuli | Twi | Vagla | |

---

## Install

```bash
pip install .
```

That's it. No extra dependencies.

---

## Usage

### Check if a text matches a specific language

```bash
tiny-detect check dagbani "O di yɛra a saa"
```
```
✅  Text MATCHES DAGBANI
   Sentence-pass rate : 95.0%
   Sentences analysed : 1
```

```bash
tiny-detect check twi "O di yɛra a saa"
```
```
❌  Text does NOT match TWI
   Sentence-pass rate : 8.0%
   Sentences analysed : 1
```

### Auto-detect the language

```bash
tiny-detect detect "O di yɛra a saa"
```
```
🔍 Detected language : DAGBANI
   Sentences analysed : 1

   dagbani              95.0%  ███████████████████
   ewe                   8.0%  █
   twi                   6.0%  █
   ...
```

### See all supported languages

```bash
tiny-detect list
```

### Read from a file

```bash
cat mytext.txt | tiny-detect detect -
tiny-detect detect mytext.txt
```

### Get JSON output (useful for scripting)

```bash
tiny-detect --json detect "some text"
tiny-detect --json check dagbani "some text"
```

---

## Python API

```python
from src.detector import LanguageDetector

detector = LanguageDetector()

# Auto-detect
result = detector.detect("O di yɛra a saa")
print(result["language"])  # "dagbani"

# Check one language
result = detector.check_language("O di yɛra a saa", "dagbani")
print(result["match"])     # True
print(result["score"])     # 0.95
```

---

## How it works

Each language has a bigram table that defines which two-letter combinations are valid at the start, middle, and end of words. A text is matched to a language when enough of its words and sentences fit those patterns.

The detection thresholds (all adjustable):
- A **word** matches if ≥ 80% of its bigrams are valid
- A **sentence** passes if ≥ 80% of its words match  
- A **text** is identified as a language if ≥ 70% of its sentences pass

```bash
# Example: loosen the thresholds for noisy or mixed text
tiny-detect --text-threshold 0.60 --sentence-threshold 0.70 detect "some text"
```

---

## License

MIT
