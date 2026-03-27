"""Glossary loading and management."""

from __future__ import annotations

import json
from pathlib import Path

from loguru import logger

from .models.glossary import GlossaryConfig

# Default glossaries directory (relative to project root)
_GLOSSARIES_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "glossaries"


def load_glossary(path: Path | None) -> GlossaryConfig | None:
    """Load a glossary from a JSON file.

    Expected JSON structure::

        {
          "meta": {"source_langs": ["pl","en"], "target_lang": "de", "domain": "pet_food"},
          "terms": {"source_term": "target_term", ...},
          "do_not_translate": ["brand_name", ...]
        }
    """
    if path is None or not path.exists():
        return None

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load glossary from {}: {}", path, exc)
        return None

    meta = raw.get("meta", {})
    return GlossaryConfig(
        source_langs=meta.get("source_langs", ["pl", "en"]),
        target_lang=meta.get("target_lang", "de"),
        domain=meta.get("domain", "general"),
        terms=raw.get("terms", {}),
        do_not_translate=raw.get("do_not_translate", []),
    )


def load_glossary_from_bytes(data: bytes) -> GlossaryConfig | None:
    """Load glossary from raw JSON bytes (e.g. Streamlit file uploader)."""
    try:
        raw = json.loads(data.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        logger.warning("Failed to parse glossary JSON: {}", exc)
        return None

    meta = raw.get("meta", {})
    return GlossaryConfig(
        source_langs=meta.get("source_langs", ["pl", "en"]),
        target_lang=meta.get("target_lang", "de"),
        domain=meta.get("domain", "general"),
        terms=raw.get("terms", {}),
        do_not_translate=raw.get("do_not_translate", []),
    )


def load_default_glossary(target_lang: str) -> GlossaryConfig | None:
    """Load the built-in glossary for a given target language."""
    path = _GLOSSARIES_DIR / f"pet_food_{target_lang}.json"
    if not path.exists():
        logger.info("No default glossary for target_lang={}", target_lang)
        return None
    return load_glossary(path)


def build_glossary_prompt(glossary: GlossaryConfig) -> str:
    """Format glossary as a prompt section for the AI."""
    if not glossary.terms and not glossary.do_not_translate:
        return ""

    parts: list[str] = []

    if glossary.terms:
        parts.append("SLOWNIK TERMINOW (OBOWIAZKOWY):")
        for src, tgt in glossary.terms.items():
            parts.append(f'  "{src}" → "{tgt}"')

    if glossary.do_not_translate:
        parts.append("\nNIE TLUMACZ (zachowaj oryginal):")
        for term in glossary.do_not_translate:
            parts.append(f"  - {term}")

    return "\n".join(parts)
