"""Shared utility functions."""

from __future__ import annotations

import re
from typing import Any

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*\n(.*?)\n\s*```", re.DOTALL)


def extract_json(text: str) -> str:
    """Extract JSON from AI response, handling markdown code fences and preamble."""
    match = _JSON_FENCE_RE.search(text)
    if match:
        return match.group(1).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]

    return text


# -- Normalization maps for AI response cleanup ------------------------------------

_SPECIES_MAP: dict[str, str] = {
    "dog": "dog", "pies": "dog", "psy": "dog", "hund": "dog",
    "cat": "cat", "kot": "cat", "koty": "cat", "katze": "cat",
    "other": "other", "unknown": "unknown", "inny": "other",
}

_LIFESTAGE_MAP: dict[str, str] = {
    "puppy": "puppy", "szczenię": "puppy", "szczenie": "puppy",
    "szczeniak": "puppy", "welpe": "puppy", "junior": "puppy",
    "kitten": "kitten", "kocię": "kitten", "kocie": "kitten",
    "kätzchen": "kitten",
    "adult": "adult", "dorosły": "adult", "dorosly": "adult",
    "erwachsen": "adult",
    "senior": "senior", "starszy": "senior",
    "all_stages": "all_stages", "all stages": "all_stages",
    "all life stages": "all_stages", "wszystkie": "all_stages",
    "unknown": "unknown",
}

_FOOD_TYPE_MAP: dict[str, str] = {
    "dry": "dry", "sucha": "dry", "trocken": "dry",
    "wet": "wet", "mokra": "wet", "nass": "wet",
    "semi_moist": "semi_moist", "semi-moist": "semi_moist",
    "semi moist": "semi_moist", "półwilgotna": "semi_moist",
    "polwilgotna": "semi_moist",
    "treat": "treat", "przysmak": "treat", "smakołyk": "treat",
    "supplement": "supplement", "suplement": "supplement",
    "unknown": "unknown",
}

_SEVERITY_MAP: dict[str, str] = {
    "critical": "CRITICAL", "krytyczny": "CRITICAL", "krytyczne": "CRITICAL",
    "warning": "WARNING", "ostrzeżenie": "WARNING", "ostrzezenie": "WARNING",
    "major": "WARNING",
    "info": "INFO", "informacja": "INFO", "minor": "INFO",
    "low": "INFO",
}

_CONFIDENCE_MAP: dict[str, str] = {
    "high": "HIGH", "wysoka": "HIGH", "wysoki": "HIGH",
    "medium": "MEDIUM", "średnia": "MEDIUM", "srednia": "MEDIUM",
    "low": "LOW", "niska": "LOW", "niski": "LOW",
}

_STATUS_MAP: dict[str, str] = {
    "compliant": "COMPLIANT", "zgodny": "COMPLIANT", "zgodna": "COMPLIANT",
    "non_compliant": "NON_COMPLIANT", "niezgodny": "NON_COMPLIANT",
    "niezgodna": "NON_COMPLIANT",
    "requires_review": "REQUIRES_REVIEW",
    "do sprawdzenia": "REQUIRES_REVIEW",
    "do_sprawdzenia": "REQUIRES_REVIEW",
}


def _fuzzy_lookup(value: str, mapping: dict[str, str]) -> str:
    """Look up a value in a mapping, trying lowercase prefix match."""
    if not isinstance(value, str):
        return value
    low = value.lower().strip()
    # Exact match
    if low in mapping:
        return mapping[low]
    # Prefix match (handles "dorosły (Turkey/...)" → "adult")
    for key, mapped in mapping.items():
        if low.startswith(key):
            return mapped
    return value


def _to_bool(value: Any) -> bool:
    """Convert various AI responses to boolean."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        low = value.lower().strip()
        return low in ("true", "yes", "tak", "1", "present", "obecny", "obecne")
    return bool(value)


def normalize_ai_response(data: dict) -> dict:
    """Normalize AI JSON response to match Pydantic model expectations.

    Fixes common issues: Polish enum values, descriptive strings,
    wrong severity levels, non-boolean booleans, dict ingredients.
    """
    # -- Product normalization --
    product = data.get("product", {})
    if isinstance(product, dict):
        if "species" in product:
            product["species"] = _fuzzy_lookup(
                product["species"], _SPECIES_MAP
            )
        if "lifestage" in product:
            product["lifestage"] = _fuzzy_lookup(
                product["lifestage"], _LIFESTAGE_MAP
            )
        if "food_type" in product:
            product["food_type"] = _fuzzy_lookup(
                product["food_type"], _FOOD_TYPE_MAP
            )

    # -- Extraction confidence --
    if "extraction_confidence" in data:
        data["extraction_confidence"] = _fuzzy_lookup(
            data["extraction_confidence"], _CONFIDENCE_MAP
        )

    # -- Status --
    if "status" in data:
        data["status"] = _fuzzy_lookup(data["status"], _STATUS_MAP)

    # -- Issues: normalize severity --
    issues = data.get("issues", [])
    if isinstance(issues, list):
        for issue in issues:
            if isinstance(issue, dict) and "severity" in issue:
                issue["severity"] = _fuzzy_lookup(
                    issue["severity"], _SEVERITY_MAP
                )

    # -- Ingredients list: dict → flat list --
    ingredients = data.get("ingredients_list")
    if isinstance(ingredients, dict):
        flat: list[str] = []
        for val in ingredients.values():
            if isinstance(val, list):
                flat.extend(str(v) for v in val)
            else:
                flat.append(str(val))
        data["ingredients_list"] = flat

    # -- EU labelling check: string → bool --
    eu = data.get("eu_labelling_check", {})
    if isinstance(eu, dict):
        for key in list(eu.keys()):
            eu[key] = _to_bool(eu[key])

    return data
