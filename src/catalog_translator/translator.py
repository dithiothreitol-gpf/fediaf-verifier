"""Batch translation via AIProvider."""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
from typing import TYPE_CHECKING

from loguru import logger

from fediaf_verifier.utils import api_call_with_retry

from .glossary import build_glossary_prompt
from .models.glossary import GlossaryConfig
from .models.translation import BatchResult, TranslatedUnit
from .models.units import TranslationUnit
from .prompts import build_catalog_translation_prompt

if TYPE_CHECKING:
    from fediaf_verifier.providers import AIProvider


def _extract_json_array(raw: str) -> list[dict]:
    """Extract JSON array from AI response, stripping markdown fences if present."""
    text = raw.strip()
    # Remove markdown code fences
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()

    parsed = json.loads(text)
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict) and "translations" in parsed:
        return parsed["translations"]
    raise ValueError(f"Expected JSON array, got {type(parsed).__name__}")


def translate_batch(
    units: list[TranslationUnit],
    target_lang: str,
    target_lang_name: str,
    glossary: GlossaryConfig | None,
    provider: "AIProvider",
    max_tokens: int = 8192,
) -> BatchResult:
    """Translate a single batch (typically one page) of translation units.

    Args:
        units: Translation units to translate.
        target_lang: ISO language code (e.g., "de").
        target_lang_name: Full language name (e.g., "Deutsch").
        glossary: Optional glossary for terminology enforcement.
        provider: AI provider instance.
        max_tokens: Max tokens for AI response.

    Returns:
        BatchResult with translated units or error.
    """
    page_number = units[0].page_number if units else 0
    section_name = units[0].section_name if units else ""

    # Filter out do_not_translate units — pass them through directly
    to_translate = [u for u in units if not u.do_not_translate]
    passthrough = [u for u in units if u.do_not_translate]

    translated_units: list[TranslatedUnit] = []

    # Add passthrough units
    for u in passthrough:
        translated_units.append(
            TranslatedUnit(
                unit_id=u.unit_id,
                source_text=u.source_text,
                translated_text=u.source_text,
                category=u.category,
                note_for_designer="Bez zmian (nie do tłumaczenia)",
            )
        )

    if not to_translate:
        return BatchResult(
            page_number=page_number,
            section_name=section_name,
            units=translated_units,
        )

    glossary_section = build_glossary_prompt(glossary) if glossary else ""

    prompt = build_catalog_translation_prompt(
        units=to_translate,
        target_lang=target_lang,
        target_lang_name=target_lang_name,
        glossary_section=glossary_section,
        domain=glossary.domain if glossary else "general",
    )

    try:
        def _call() -> str:
            return provider.call(prompt=prompt, max_tokens=max_tokens)

        raw_response = api_call_with_retry(_call, max_retries=5, base_delay=5.0)
        items = _extract_json_array(raw_response)
    except Exception as exc:
        logger.error("Batch translation failed for page {}: {}", page_number, exc)
        return BatchResult(
            page_number=page_number,
            section_name=section_name,
            units=translated_units,
            error=str(exc),
        )

    # Build lookup from response
    response_map: dict[str, dict] = {}
    for item in items:
        uid = item.get("id", "")
        if uid:
            response_map[uid] = item

    # Match response to source units
    for u in to_translate:
        resp = response_map.get(u.unit_id, {})
        translated_units.append(
            TranslatedUnit(
                unit_id=u.unit_id,
                source_text=u.source_text,
                translated_text=resp.get("translated_text", ""),
                category=u.category,
                note_for_designer=resp.get("note", ""),
            )
        )

    # Sort by original order
    unit_order = {u.unit_id: i for i, u in enumerate(units)}
    translated_units.sort(key=lambda t: unit_order.get(t.unit_id, 999))

    return BatchResult(
        page_number=page_number,
        section_name=section_name,
        units=translated_units,
    )


def translate_catalog(
    pages: list[list[TranslationUnit]],
    target_lang: str,
    target_lang_name: str,
    glossary: GlossaryConfig | None,
    provider: "AIProvider",
    max_tokens: int = 8192,
    progress_callback: Callable[[int, int], None] | None = None,
) -> list[BatchResult]:
    """Translate all pages of a catalog.

    Args:
        pages: List of pages, each containing translation units.
        target_lang: ISO language code.
        target_lang_name: Full language name.
        glossary: Optional glossary.
        provider: AI provider instance.
        max_tokens: Max tokens per batch call.
        progress_callback: Called with (completed_count, total_count) after each batch.

    Returns:
        List of BatchResult, one per page.
    """
    total = len(pages)
    results: list[BatchResult] = []

    for i, page_units in enumerate(pages):
        logger.info("Translating batch {}/{} (page {})", i + 1, total, page_units[0].page_number)

        batch_result = translate_batch(
            units=page_units,
            target_lang=target_lang,
            target_lang_name=target_lang_name,
            glossary=glossary,
            provider=provider,
            max_tokens=max_tokens,
        )
        results.append(batch_result)

        if progress_callback:
            progress_callback(i + 1, total)

        # Throttle: short pause between batches to avoid RPM limits
        if i < total - 1:
            time.sleep(1)

    return results
