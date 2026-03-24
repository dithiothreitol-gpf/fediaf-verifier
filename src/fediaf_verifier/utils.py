"""Shared utility functions."""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from typing import Any

from loguru import logger

from fediaf_verifier.providers import ProviderRateLimitError

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


def repair_truncated_json(text: str) -> str | None:
    """Attempt to repair JSON truncated by max_tokens limit.

    Closes unclosed strings, arrays, and objects so json.loads() can succeed.
    Returns repaired JSON string or None if repair is not possible.
    """
    import json as _json

    # First extract the JSON portion
    extracted = extract_json(text)

    # Try as-is first
    try:
        _json.loads(extracted)
        return extracted
    except _json.JSONDecodeError:
        pass

    # Work with the raw extracted text
    repaired = extracted.rstrip()

    # Remove trailing comma
    repaired = re.sub(r",\s*$", "", repaired)

    # Remove incomplete key-value pair at the end (e.g. `"key": "incompl`)
    # Pattern: trailing `"key": "...` without closing quote
    repaired = re.sub(r',?\s*"[^"]*":\s*"[^"]*$', "", repaired)
    # Pattern: trailing `"key": ` without value
    repaired = re.sub(r',?\s*"[^"]*":\s*$', "", repaired)
    # Pattern: trailing incomplete array element
    repaired = re.sub(r',?\s*"[^"]*$', "", repaired)

    # Remove trailing comma again after cleanup
    repaired = re.sub(r",\s*$", "", repaired)

    # Count unclosed brackets and braces
    open_braces = repaired.count("{") - repaired.count("}")
    open_brackets = repaired.count("[") - repaired.count("]")

    # Close them
    repaired += "]" * max(0, open_brackets)
    repaired += "}" * max(0, open_braces)

    try:
        _json.loads(repaired)
        logger.warning(
            "Repaired truncated JSON (closed {} braces, {} brackets)",
            max(0, open_braces),
            max(0, open_brackets),
        )
        return repaired
    except _json.JSONDecodeError:
        logger.error("Could not repair truncated JSON")
        return None


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


def fuzzy_lookup(
    value: str, mapping: dict[str, str], default: str | None = None,
) -> str:
    """Look up a value in a mapping, trying lowercase prefix/substring match."""
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
    # Substring match (handles "karma pełnoporcjowa mokra" → "wet")
    for key, mapped in mapping.items():
        if key in low:
            return mapped
    return default if default is not None else value


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
            product["species"] = fuzzy_lookup(
                product["species"], _SPECIES_MAP
            )
        if "lifestage" in product:
            product["lifestage"] = fuzzy_lookup(
                product["lifestage"], _LIFESTAGE_MAP
            )
        if "food_type" in product:
            product["food_type"] = fuzzy_lookup(
                product["food_type"], _FOOD_TYPE_MAP
            )

    # -- Extraction confidence --
    if "extraction_confidence" in data:
        data["extraction_confidence"] = fuzzy_lookup(
            data["extraction_confidence"], _CONFIDENCE_MAP
        )

    # -- Status --
    if "status" in data:
        data["status"] = fuzzy_lookup(data["status"], _STATUS_MAP)

    # -- Issues: normalize severity --
    issues = data.get("issues", [])
    if isinstance(issues, list):
        for issue in issues:
            if isinstance(issue, dict) and "severity" in issue:
                issue["severity"] = fuzzy_lookup(
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

    # -- Packaging check normalization --
    pkg = data.get("packaging_check", {})
    if isinstance(pkg, dict):
        _CLASSIFICATION_MAP = {
            "complete": "complete",
            "pełnoporcjowa": "complete",
            "pelnoporcjowa": "complete",
            "complementary": "complementary",
            "uzupełniająca": "complementary",
            "uzupelniajaca": "complementary",
            "treat": "treat",
            "przysmak": "treat",
            "not_stated": "not_stated",
        }
        if "product_classification" in pkg:
            pkg["product_classification"] = fuzzy_lookup(
                pkg["product_classification"], _CLASSIFICATION_MAP
            )
        # Normalize boolean fields
        bool_fields = [
            "feeding_guidelines_present", "storage_instructions_present",
            "claims_consistent_with_composition", "meat_percentage_claim_consistent",
            "net_weight_e_symbol", "country_of_origin_stated", "no_therapeutic_claims",
            "naming_percentage_rule_ok", "recycling_symbols_present", "barcode_visible",
            "qr_code_visible", "species_emblem_present", "date_marking_area_present",
            "translations_complete", "country_codes_for_languages",
            "compliance_statement_present",
            "gmo_declaration_required",
            "gmo_declaration_present",
            "free_contact_for_info",
            "is_raw_product",
            "raw_warning_present",
            "contains_insect_protein",
            "insect_allergen_warning",
            "irradiation_declared_if_applicable",
            "establishment_approval_number",
            "moisture_declaration_required",
            "moisture_declaration_present",
            "font_legibility_ok",
            "polish_language_complete",
        ]
        for field in bool_fields:
            if field in pkg:
                pkg[field] = _to_bool(pkg[field])

    return data


def api_call_with_retry[T](
    fn: Callable[[], T],
    max_retries: int = 3,
    base_delay: float = 15.0,
    spinner_callback: Callable[[str], None] | None = None,
) -> T:
    """Call fn() with exponential backoff on rate limit (429) errors.

    Args:
        fn: Zero-arg callable that makes the API call.
        max_retries: Maximum number of attempts.
        base_delay: Base delay in seconds (doubles each retry).
        spinner_callback: Optional function to update UI with wait message.

    Returns:
        Result of fn().

    Raises:
        ProviderRateLimitError: If all retries exhausted.
    """
    for attempt in range(max_retries):
        try:
            return fn()
        except ProviderRateLimitError:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2**attempt)  # 15s, 30s, 60s
            logger.warning(
                "Rate limit hit, retrying in {}s (attempt {}/{})",
                delay,
                attempt + 1,
                max_retries,
            )
            if spinner_callback:
                spinner_callback(
                    f"Rate limit — czekam {int(delay)}s przed ponowna proba..."
                )
            time.sleep(delay)
    raise RuntimeError("Unexpected: retry loop completed without return or raise")
