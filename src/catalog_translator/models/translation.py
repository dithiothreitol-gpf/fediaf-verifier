"""Translation result models."""

from __future__ import annotations

from pydantic import Field

from fediaf_verifier.models.base import NullSafeBase

from .units import UnitCategory


class TranslatedUnit(NullSafeBase):
    """A translated unit returned by the AI."""

    unit_id: str = ""
    source_text: str = ""
    translated_text: str = ""
    category: UnitCategory = UnitCategory.OTHER
    note_for_designer: str = ""


class BatchResult(NullSafeBase):
    """Translation result for one batch (page)."""

    page_number: int = 0
    section_name: str = ""
    units: list[TranslatedUnit] = Field(default_factory=list)
    error: str = ""


class CatalogTranslationResult(NullSafeBase):
    """Full catalog translation pipeline result."""

    performed: bool = False
    source_filename: str = ""
    source_langs: str = "pl,en"
    target_lang: str = ""
    target_lang_name: str = ""
    batches: list[BatchResult] = Field(default_factory=list)
    total_units: int = 0
    translated_units: int = 0
    glossary_name: str = ""
    error: str = ""
