"""Glossary configuration model."""

from __future__ import annotations

from pydantic import Field

from fediaf_verifier.models.base import NullSafeBase


class GlossaryConfig(NullSafeBase):
    """Terminology glossary for translation consistency."""

    source_langs: list[str] = Field(default_factory=lambda: ["pl", "en"])
    target_lang: str = "de"
    domain: str = "pet_food"
    terms: dict[str, str] = Field(default_factory=dict)
    do_not_translate: list[str] = Field(default_factory=list)
