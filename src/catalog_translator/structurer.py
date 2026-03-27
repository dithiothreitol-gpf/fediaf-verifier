"""Heuristic structuring of extracted text blocks into translation units."""

from __future__ import annotations

import re

from .models.extraction import CatalogExtraction, PageExtraction, TextBlock
from .models.units import TranslationUnit, UnitCategory

# Polish diacritics for language detection
_PL_CHARS = set("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ")

# Keywords for composition detection
_COMPOSITION_KEYWORDS_PL = {"skład", "składniki", "zawartość"}
_COMPOSITION_KEYWORDS_EN = {"composition", "ingredients", "contents"}

# Keywords for analytical constituents
_ANALYTICAL_KEYWORDS_PL = {"składniki analityczne", "analiza"}
_ANALYTICAL_KEYWORDS_EN = {"analytical constituents", "analysis", "typical analysis"}

# Feeding guide keywords
_FEEDING_KEYWORDS_PL = {"dawkowanie", "sposób podawania", "zalecana porcja"}
_FEEDING_KEYWORDS_EN = {"feeding guide", "feeding recommendation", "daily amount"}

# Section detection patterns (page-level sections)
_SECTION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"karma\s+mokra.*saszetk", re.I), "Karma mokra w saszetkach"),
    (re.compile(r"wet\s+(dog\s+)?food.*pouch", re.I), "Karma mokra w saszetkach"),
    (re.compile(r"karma\s+mokra.*puszk", re.I), "Karma mokra w puszkach"),
    (re.compile(r"wet\s+(dog\s+)?food.*can", re.I), "Karma mokra w puszkach"),
    (re.compile(r"przysmaki|gryzaki", re.I), "Naturalne przysmaki i gryzaki"),
    (re.compile(r"chews.*snacks|natural.*treats", re.I), "Naturalne przysmaki i gryzaki"),
    (re.compile(r"trener", re.I), "Trenerki"),
    (re.compile(r"training\s+treats", re.I), "Trenerki"),
    (re.compile(r"batonik|protein\s+bar", re.I), "Batoniki proteinowe"),
    (re.compile(r"chips", re.I), "Chipsy"),
    (re.compile(r"kie[łl]bas|sausage", re.I), "Kiełbaski"),
    (re.compile(r"karma\s+sucha|dry\s+food", re.I), "Karma sucha"),
    (re.compile(r"karma.*kot|cat\s+food", re.I), "Karma dla kota"),
    (re.compile(r"salamk", re.I), "Salamki"),
    (re.compile(r"superfood", re.I), "Superfood"),
]


def _detect_language(text: str) -> str:
    """Detect whether text is Polish or English based on diacritics and keywords."""
    has_pl_chars = any(c in _PL_CHARS for c in text)
    if has_pl_chars:
        return "pl"

    text_lower = text.lower()
    for kw in _COMPOSITION_KEYWORDS_PL | _ANALYTICAL_KEYWORDS_PL | _FEEDING_KEYWORDS_PL:
        if kw in text_lower:
            return "pl"
    for kw in _COMPOSITION_KEYWORDS_EN | _ANALYTICAL_KEYWORDS_EN | _FEEDING_KEYWORDS_EN:
        if kw in text_lower:
            return "en"

    return "en"  # default fallback


def _classify_block(block: TextBlock, page_height: float) -> UnitCategory:
    """Classify a text block into a content category based on heuristics."""
    text_lower = block.text.lower().strip()

    # Badge: short uppercase text
    if len(block.text) < 40 and block.text == block.text.upper() and block.font_size >= 10:
        # Check for badge-like patterns
        if any(
            kw in text_lower
            for kw in ("nowość", "new", "product from", "produkt z", "premium", "100%")
        ):
            return UnitCategory.BADGE

    # Heading: large bold text in upper portion of page
    if block.font_size >= 14 and block.is_bold:
        return UnitCategory.HEADING

    # Product name: bold, medium-large font
    if block.font_size >= 11 and block.is_bold and len(block.text) < 80:
        return UnitCategory.PRODUCT_NAME

    # Composition: keyword-triggered
    for kw in _COMPOSITION_KEYWORDS_PL | _COMPOSITION_KEYWORDS_EN:
        if text_lower.startswith(kw):
            return UnitCategory.COMPOSITION

    # Analytical constituents
    for kw in _ANALYTICAL_KEYWORDS_PL | _ANALYTICAL_KEYWORDS_EN:
        if kw in text_lower:
            return UnitCategory.ANALYTICAL

    # Feeding guide
    for kw in _FEEDING_KEYWORDS_PL | _FEEDING_KEYWORDS_EN:
        if kw in text_lower:
            return UnitCategory.FEEDING_GUIDE

    # Label-like: ends with colon (short text)
    if text_lower.endswith(":") and len(block.text) < 60:
        return UnitCategory.LABEL

    # Description: longer body text
    if len(block.text) > 100 and not block.is_bold:
        return UnitCategory.DESCRIPTION

    # Weight/quantity pattern — label
    if re.search(r"\d+\s*(g|kg|ml|l|szt|pcs)\b", text_lower, re.I):
        return UnitCategory.LABEL

    return UnitCategory.OTHER


def _detect_section(blocks: list[TextBlock]) -> str:
    """Try to detect a section name from the page's heading blocks."""
    for block in blocks:
        if block.font_size >= 14 or block.is_bold:
            text = block.text
            for pattern, section_name in _SECTION_PATTERNS:
                if pattern.search(text):
                    return section_name
    return ""


def structure_catalog(
    extraction: CatalogExtraction,
) -> list[list[TranslationUnit]]:
    """Convert extracted text blocks into categorized translation units.

    Args:
        extraction: Raw PDF extraction result.

    Returns:
        List of pages, each containing a list of TranslationUnit objects.
    """
    all_pages: list[list[TranslationUnit]] = []
    current_section = ""

    for page in extraction.pages:
        # Detect section from this page
        section = _detect_section(page.blocks)
        if section:
            current_section = section

        units: list[TranslationUnit] = []
        for i, block in enumerate(page.blocks):
            category = _classify_block(block, page.height)
            lang = _detect_language(block.text)

            unit = TranslationUnit(
                unit_id=f"p{page.page_number}_b{i}",
                source_text=block.text,
                category=category,
                page_number=page.page_number,
                section_name=current_section,
                detected_language=lang,
            )
            units.append(unit)

        if units:
            all_pages.append(units)

    return all_pages
