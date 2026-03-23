"""EU Feed Additives Register validator.

Parses the EU Feed Additives Register (Excel download from the Food & Feed
Information Portal) and provides lookup/validation functions for additive
names, E-numbers, functional groups, and species restrictions.

Data source: https://ec.europa.eu/food/food-feed-portal/screen/feed-additives/search
Download the register as Excel and place it in data/eu_feed_additives.xlsx.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any

from loguru import logger

# Default path for the additives data file (JSON, pre-parsed from Excel)
_DEFAULT_DATA_PATH = Path(__file__).resolve().parent.parent.parent / "data"
_ADDITIVES_JSON = _DEFAULT_DATA_PATH / "eu_feed_additives.json"
_ADDITIVES_XLSX = _DEFAULT_DATA_PATH / "eu_feed_additives.xlsx"

# In-memory cache
_additives_db: list[dict[str, Any]] | None = None


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def _load_from_json(path: Path) -> list[dict[str, Any]]:
    """Load pre-parsed additives from JSON cache."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_from_excel(path: Path) -> list[dict[str, Any]]:
    """Parse EU Feed Additives Register Excel file.

    Expected columns (may vary by download version):
    - Identification number (E-number / additive ID)
    - Additive name
    - Functional group
    - Category
    - Species / animal category
    - Maximum content (mg/kg)
    - Minimum content (mg/kg)
    - Authorisation regulation

    Returns list of dicts with normalized keys.
    """
    try:
        import openpyxl
    except ImportError:
        raise ImportError(
            "openpyxl jest wymagany do parsowania EU Feed Additives Excel. "
            "Zainstaluj: pip install openpyxl"
        )

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    if ws is None:
        raise ValueError(f"Pusty plik Excel: {path}")

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []

    # First row = headers
    raw_headers = [str(h or "").strip().lower() for h in rows[0]]

    # Map known header patterns to normalized keys (use word boundaries)
    import re as _re

    _HEADER_PATTERNS: list[tuple[str, str]] = [
        (r"\b(identif|number|numer|e.?num)", "id_number"),
        (r"\b(additive\b.*name|nazwa\b.*addyt|^name$)", "name"),
        (r"\b(functional|funkcj)", "functional_group"),
        (r"\b(categor|kategor)", "category"),
        (r"\b(species|gatun|animal)", "species"),
        (r"\bmax.*content|\bmaximum", "max_content"),
        (r"\bmin.*content|\bminimum", "min_content"),
        (r"\b(regulat|rozporz|authori)", "regulation"),
    ]
    header_map: dict[int, str] = {}
    for i, h in enumerate(raw_headers):
        for pattern, key in _HEADER_PATTERNS:
            if _re.search(pattern, h):
                header_map[i] = key
                break

    additives: list[dict[str, Any]] = []
    for row in rows[1:]:
        entry: dict[str, Any] = {}
        for i, val in enumerate(row):
            key = header_map.get(i)
            if key:
                entry[key] = str(val).strip() if val is not None else ""
        if entry.get("name") or entry.get("id_number"):
            additives.append(entry)

    wb.close()
    return additives


def load_additives_db(
    json_path: Path | None = None,
    excel_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Load additives database, with caching.

    Tries JSON cache first, then Excel. Generates JSON cache from Excel
    if needed.
    """
    global _additives_db
    if _additives_db is not None:
        return _additives_db

    jp = json_path or _ADDITIVES_JSON
    xp = excel_path or _ADDITIVES_XLSX

    # Try JSON first (fast)
    if jp.is_file():
        try:
            _additives_db = _load_from_json(jp)
            logger.info("Zaladowano {} additywow z JSON cache", len(_additives_db))
            return _additives_db
        except Exception as e:
            logger.warning("Blad odczytu JSON cache: {}", e)

    # Try Excel
    if xp.is_file():
        try:
            _additives_db = _load_from_excel(xp)
            logger.info("Sparsowano {} additywow z Excel", len(_additives_db))
            # Save JSON cache
            try:
                with open(jp, "w", encoding="utf-8") as f:
                    json.dump(_additives_db, f, ensure_ascii=False, indent=2)
                logger.info("Zapisano JSON cache: {}", jp)
            except Exception as e:
                logger.warning("Nie mozna zapisac JSON cache: {}", e)
            return _additives_db
        except Exception as e:
            logger.error("Blad parsowania Excel: {}", e)

    logger.warning(
        "Brak pliku EU Feed Additives Register. "
        "Pobierz z: https://ec.europa.eu/food/food-feed-portal/screen/feed-additives/search "
        "i zapisz jako data/eu_feed_additives.xlsx"
    )
    _additives_db = []
    return _additives_db


# ---------------------------------------------------------------------------
# Validation functions
# ---------------------------------------------------------------------------


def validate_additive(
    name_or_id: str,
    species: str = "",
) -> dict[str, Any]:
    """Validate an additive name or E-number against the EU register.

    Args:
        name_or_id: Additive name (e.g., "witamina E") or ID (e.g., "3a700").
        species: Target species ("dog", "cat", etc.) for restriction check.

    Returns:
        Dict with keys: found (bool), matches (list of matching entries),
        warnings (list of str).
    """
    db = load_additives_db()
    if not db:
        return {
            "found": False,
            "matches": [],
            "warnings": ["Baza EU Feed Additives niedostepna"],
        }

    query = name_or_id.strip().lower()
    matches: list[dict[str, Any]] = []
    warnings: list[str] = []

    for entry in db:
        entry_name = entry.get("name", "").lower()
        entry_id = entry.get("id_number", "").lower()

        # Match by ID number or name substring
        if query == entry_id or query in entry_name or entry_name in query:
            matches.append(entry)

    if not matches:
        # Try fuzzy: check if any word of the query matches
        query_words = set(query.split())
        for entry in db:
            entry_words = set(entry.get("name", "").lower().split())
            if query_words & entry_words and len(query_words & entry_words) >= 2:
                matches.append(entry)

    # Check species restrictions
    if matches and species:
        species_lower = species.lower()
        for m in matches:
            entry_species = m.get("species", "").lower()
            if entry_species and species_lower not in entry_species and "all" not in entry_species:
                warnings.append(
                    f"Addityw '{m.get('name', '')}' moze nie byc dozwolony dla "
                    f"gatunku '{species}' (dozwolone: {entry_species})"
                )

    return {
        "found": len(matches) > 0,
        "matches": matches[:5],  # limit to top 5
        "warnings": warnings,
    }


def validate_additives_list(
    additives_text: str,
    species: str = "",
) -> list[dict[str, Any]]:
    """Validate a comma/semicolon-separated list of additives.

    Args:
        additives_text: Full additives declaration from label.
        species: Target species.

    Returns:
        List of validation results, one per detected additive.
    """
    # Split by common delimiters
    parts = re.split(r"[,;]\s*", additives_text)
    results = []
    for part in parts:
        part = part.strip()
        if not part or len(part) < 3:
            continue
        # Try to extract E-number or additive name
        # Pattern: "witamina E (3a700) 250 mg/kg" → name="witamina E", id="3a700"
        id_match = re.search(r"\b(\d[a-z]?\d{2,4})\b", part, re.IGNORECASE)
        name = re.sub(r"\d+\s*(mg|iu|µg|mcg)/kg.*", "", part, flags=re.IGNORECASE).strip()

        if id_match:
            result = validate_additive(id_match.group(1), species)
            result["query"] = part
            result["extracted_id"] = id_match.group(1)
            results.append(result)
        elif name:
            result = validate_additive(name, species)
            result["query"] = part
            results.append(result)

    return results
