"""Deterministic spell-checking and diacritics validation.

Uses spylls (pure-Python Hunspell) for spell-checking and
Unicode-aware rules for diacritics verification.
Zero AI — all checks are deterministic.
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from pathlib import Path

from loguru import logger

# ---------------------------------------------------------------------------
# Unicode normalization
# ---------------------------------------------------------------------------


def normalize_nfc(text: str) -> str:
    """Normalize text to NFC (canonical composed form).

    Critical for diacritics comparison: é (U+00E9) vs e+´ (U+0065+U+0301)
    look identical but fail string comparison without normalization.
    """
    return unicodedata.normalize("NFC", text)


# ---------------------------------------------------------------------------
# Language → dictionary mapping
# ---------------------------------------------------------------------------

# ISO 639-1 → Hunspell dictionary file stem
_LANG_TO_DICT = {
    "pl": "pl_PL",
    "de": "de_DE",
    "fr": "fr_FR",
    "en": "en_US",
    "it": "it_IT",
    "es": "es_ES",
    "cs": "cs_CZ",
    "hu": "hu_HU",
    "ro": "ro_RO",
}

_DICT_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "dictionaries"

# Pet food industry terms not in standard dictionaries.
# Added to every language as supplementary known-good words.
_PET_FOOD_TERMS = {
    # Polish
    "pełnoporcjowa", "pełnoporcjowe", "pełnoporcjowy",
    "uzupełniająca", "uzupełniające", "uzupełniający",
    "monobialko", "monobiałko", "monobiałkowa",
    "bezzbożowa", "bezzbożowe", "bezzbożowy",
    "hipoalergiczna", "hipoalergiczne", "hipoalergiczny",
    "prebiotyk", "prebiotyki", "probiotyk", "probiotyki",
    "glukozamina", "chondroityna", "tauryna",
    "kwasy omega", "omega-3", "omega-6",
    # German
    "Alleinfuttermittel", "Ergänzungsfuttermittel",
    "Rohprotein", "Rohfett", "Rohfaser", "Rohasche",
    "Heimtiernahrung", "Feuchtigkeit",
    # French
    "protéine", "protéines", "cendres",
    # English
    "kibble", "croquette", "glucosamine", "chondroitin",
    "taurine", "prebiotic", "prebiotics", "probiotic",
    "hypoallergenic", "grain-free",
    # Shared / international
    "FEDIAF", "AAFCO", "FOS", "MOS", "DHA", "EPA",
    "L-karnityna", "L-carnitine", "L-carnitin",
}


# ---------------------------------------------------------------------------
# Diacritics allowlists per language
# ---------------------------------------------------------------------------

EXPECTED_DIACRITICS: dict[str, set[str]] = {
    "pl": set("ąęśćźżłńóĄĘŚĆŹŻŁŃÓ"),
    "de": set("äöüßÄÖÜ"),
    "fr": set("àâæçéèêëîïôœùûüÿÀÂÆÇÉÈÊËÎÏÔŒÙÛÜŸ"),
    "cs": set("řšžčůúýáéíěňťďŘŠŽČŮÚÝÁÉÍĚŇŤĎ"),
    "hu": set("áéíóöőúüűÁÉÍÓÖŐÚÜŰ"),
    "ro": set("ăâîșțĂÂÎȘȚ"),
    "it": set("àèéìòùÀÈÉÌÒÙ"),
    "es": set("áéíñóúüÁÉÍÑÓÚÜ¿¡"),
}


# ---------------------------------------------------------------------------
# Dictionary loading (lazy, cached)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=16)
def _load_dictionary(lang_code: str):
    """Load Hunspell dictionary for the given language.

    Returns None if dictionary not available (won't crash the app).
    """
    dict_stem = _LANG_TO_DICT.get(lang_code)
    if not dict_stem:
        logger.debug("No dictionary mapping for language: {}", lang_code)
        return None

    dic_path = _DICT_DIR / f"{dict_stem}.dic"
    aff_path = _DICT_DIR / f"{dict_stem}.aff"

    if not dic_path.exists() or not aff_path.exists():
        logger.warning(
            "Dictionary files not found for {}: {} / {}",
            lang_code, dic_path, aff_path,
        )
        return None

    try:
        from spylls.hunspell import Dictionary
        d = Dictionary.from_files(str(_DICT_DIR / dict_stem))
        logger.info("Loaded dictionary: {} ({} → {})", lang_code, dict_stem, dic_path)
        return d
    except Exception as e:
        logger.warning("Failed to load dictionary for {}: {}", lang_code, e)
        return None


# ---------------------------------------------------------------------------
# Word extraction
# ---------------------------------------------------------------------------

# Split text into words, keeping diacritics and hyphens
_WORD_RE = re.compile(r"[\w\u0080-\u024F][\w\u0080-\u024F'-]*", re.UNICODE)

# Skip: numbers, units, codes, brand-like tokens, short words
_SKIP_RE = re.compile(
    r"^("
    r"\d+[.,]?\d*%?"          # numbers: 26.5%, 100
    r"|[A-Z]{2,5}\d*"         # codes: EAN, DE, PL01
    r"|https?://\S+"          # URLs
    r"|[a-zA-Z]{1,2}"         # 1-2 letter words (prepositions etc.)
    r"|E\d{3,4}"              # E-additives: E300, E1000
    r")$"
)


def _extract_words(text: str) -> list[str]:
    """Extract checkable words from text."""
    text = normalize_nfc(text)
    words = _WORD_RE.findall(text)
    return [w for w in words if not _SKIP_RE.match(w)]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class SpellCheckResult:
    """Result of deterministic spell-checking a single word."""

    __slots__ = ("word", "correct", "suggestions", "source")

    def __init__(
        self,
        word: str,
        correct: bool,
        suggestions: list[str] | None = None,
        source: str = "hunspell",
    ):
        self.word = word
        self.correct = correct
        self.suggestions = suggestions or []
        self.source = source

    def __repr__(self) -> str:
        return (
            f"SpellCheckResult({self.word!r}, correct={self.correct}, "
            f"suggestions={self.suggestions!r})"
        )


def check_spelling(
    text: str,
    language: str,
    max_issues: int = 30,
) -> list[SpellCheckResult]:
    """Check spelling of text using Hunspell dictionary.

    Args:
        text: Text to check.
        language: ISO 639-1 language code (e.g. "pl", "de").
        max_issues: Maximum number of issues to return.

    Returns:
        List of SpellCheckResult for misspelled words only.
    """
    dictionary = _load_dictionary(language)
    if dictionary is None:
        return []

    words = _extract_words(text)
    results: list[SpellCheckResult] = []
    seen: set[str] = set()

    for word in words:
        if word in seen:
            continue
        seen.add(word)

        # Skip pet food industry terms
        if word in _PET_FOOD_TERMS or word.lower() in _PET_FOOD_TERMS:
            continue

        # Hunspell lookup
        if not dictionary.lookup(word):
            # Try lowercase variant (Hunspell is case-sensitive for some langs)
            if word[0].isupper() and dictionary.lookup(word.lower()):
                continue
            # Try title case
            if word.islower() and dictionary.lookup(word.title()):
                continue

            suggestions = []
            try:
                suggestions = list(dictionary.suggest(word))[:5]
            except Exception:
                pass

            results.append(SpellCheckResult(
                word=word,
                correct=False,
                suggestions=suggestions,
                source="hunspell",
            ))

            if len(results) >= max_issues:
                break

    return results


def check_diacritics_presence(
    text: str,
    language: str,
) -> dict[str, bool]:
    """Check if text contains expected diacritics for the given language.

    Returns dict with:
      - "has_diacritics": whether any expected diacritics are present
      - "missing_expected": True if text has words that SHOULD have
        diacritics but don't (heuristic)
    """
    expected = EXPECTED_DIACRITICS.get(language)
    if not expected:
        return {"has_diacritics": True, "missing_expected": False}

    text_nfc = normalize_nfc(text)
    found = expected & set(text_nfc)

    return {
        "has_diacritics": len(found) > 0,
        "missing_expected": len(found) == 0 and len(text_nfc) > 50,
    }


def validate_ai_linguistic_issues(
    ai_issues: list[dict],
    text: str,
    language: str,
) -> list[dict]:
    """Cross-validate AI-reported linguistic issues against Hunspell.

    For each AI issue of type "spelling" or "diacritics":
    - If Hunspell ALSO flags the word → HIGH confidence (AI confirmed)
    - If Hunspell says the word is CORRECT → LOW confidence (possible hallucination)
    - If no dictionary available → MEDIUM confidence (can't verify)

    Adds 'confidence' and 'verified_by' keys to each issue dict.

    Args:
        ai_issues: List of AI-generated LinguisticIssue dicts.
        text: Full text that was checked (for context).
        language: ISO 639-1 code.

    Returns:
        Same list with added confidence/verified_by fields.
    """
    dictionary = _load_dictionary(language)

    for issue in ai_issues:
        issue_type = issue.get("issue_type", "")
        original = normalize_nfc(issue.get("original", ""))

        if issue_type in ("spelling", "diacritics") and dictionary is not None:
            # Extract the flagged word(s) from original
            words = _extract_words(original)
            if not words:
                issue["confidence"] = "medium"
                issue["verified_by"] = "ai_only"
                continue

            # Check if ANY of the words are actually misspelled per Hunspell
            hunspell_agrees = False
            for w in words:
                if w in _PET_FOOD_TERMS or w.lower() in _PET_FOOD_TERMS:
                    continue
                if not dictionary.lookup(w):
                    hunspell_agrees = True
                    break

            if hunspell_agrees:
                issue["confidence"] = "high"
                issue["verified_by"] = "ai+hunspell"
            else:
                issue["confidence"] = "low"
                issue["verified_by"] = "ai_only (hunspell disagrees)"

        elif issue_type == "grammar":
            # Grammar: can't verify deterministically without LanguageTool
            issue["confidence"] = "medium"
            issue["verified_by"] = "ai_only"

        elif issue_type in ("punctuation", "terminology"):
            issue["confidence"] = "medium"
            issue["verified_by"] = "ai_only"

        else:
            if dictionary is None:
                issue["confidence"] = "medium"
                issue["verified_by"] = "ai_only (no dictionary)"
            else:
                issue["confidence"] = "medium"
                issue["verified_by"] = "ai_only"

    return ai_issues
