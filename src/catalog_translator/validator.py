"""Post-translation validation checks."""

from __future__ import annotations

import re

from .models.glossary import GlossaryConfig
from .models.translation import BatchResult, TranslatedUnit
from .models.units import TranslationUnit
from .models.validation import ValidationIssue, ValidationReport, ValidationSeverity

# Target language diacritics for validation
_TARGET_DIACRITICS: dict[str, str] = {
    "de": "äöüßÄÖÜ",
    "fr": "éèêëàâçîïôùûüÿæœ",
    "es": "áéíóúñü¿¡",
    "it": "àèéìòù",
    "nl": "ëïöüé",
    "cs": "áčďéěíňóřšťúůýž",
    "sk": "áäčďéíĺľňóôŕšťúýž",
    "sv": "åäö",
    "da": "æøå",
    "pt": "áâãàçéêíóôõúü",
    "hu": "áéíóöőúüű",
    "ro": "ăâîșț",
}

_PL_DIACRITICS = set("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ")


def _check_number_preservation(
    source: TranslationUnit, translated: TranslatedUnit
) -> list[ValidationIssue]:
    """Verify all numbers from source appear in translation."""
    issues: list[ValidationIssue] = []

    orig_numbers = sorted(re.findall(r"\d+[.,]?\d*%?", source.source_text))
    trans_numbers = sorted(re.findall(r"\d+[.,]?\d*%?", translated.translated_text))

    if orig_numbers != trans_numbers:
        issues.append(
            ValidationIssue(
                unit_id=source.unit_id,
                page=source.page_number,
                check_type="number_preservation",
                severity=ValidationSeverity.ERROR,
                message=(
                    f"Niezgodnosc liczb: oryginal={orig_numbers} "
                    f"tlumaczenie={trans_numbers}"
                ),
                source_text=source.source_text,
                translated_text=translated.translated_text,
            )
        )

    return issues


def _check_diacritics(
    source: TranslationUnit,
    translated: TranslatedUnit,
    target_lang: str,
) -> list[ValidationIssue]:
    """Check for wrong diacritics in translation (e.g. Polish chars in DE output)."""
    issues: list[ValidationIssue] = []

    # Polish diacritics should not appear in target language translation
    if target_lang != "pl":
        pl_in_translation = [c for c in translated.translated_text if c in _PL_DIACRITICS]
        if pl_in_translation:
            issues.append(
                ValidationIssue(
                    unit_id=source.unit_id,
                    page=source.page_number,
                    check_type="diacritics",
                    severity=ValidationSeverity.WARNING,
                    message=f"Polskie znaki w tlumaczeniu {target_lang.upper()}: {''.join(set(pl_in_translation))}",
                    source_text=source.source_text,
                    translated_text=translated.translated_text,
                )
            )

    return issues


def _check_length_ratio(
    source: TranslationUnit, translated: TranslatedUnit
) -> list[ValidationIssue]:
    """Flag translations with suspicious length ratio."""
    issues: list[ValidationIssue] = []

    src_len = max(len(source.source_text), 1)
    tgt_len = len(translated.translated_text)
    ratio = tgt_len / src_len

    if ratio > 2.5 or ratio < 0.3:
        issues.append(
            ValidationIssue(
                unit_id=source.unit_id,
                page=source.page_number,
                check_type="length_ratio",
                severity=ValidationSeverity.WARNING,
                message=f"Podejrzana dlugosc tlumaczenia (ratio={ratio:.1f}x)",
                source_text=source.source_text,
                translated_text=translated.translated_text,
            )
        )

    return issues


def _check_terminology(
    source: TranslationUnit,
    translated: TranslatedUnit,
    glossary: GlossaryConfig,
) -> list[ValidationIssue]:
    """Verify glossary terms are used correctly."""
    issues: list[ValidationIssue] = []

    src_lower = source.source_text.lower()
    tgt_lower = translated.translated_text.lower()

    for term, expected in glossary.terms.items():
        if term.lower() in src_lower and expected.lower() not in tgt_lower:
            issues.append(
                ValidationIssue(
                    unit_id=source.unit_id,
                    page=source.page_number,
                    check_type="terminology",
                    severity=ValidationSeverity.WARNING,
                    message=f"Niespojny termin: oczekiwano '{expected}' dla '{term}'",
                    source_text=source.source_text,
                    translated_text=translated.translated_text,
                )
            )

    # Check do_not_translate terms are preserved
    for name in glossary.do_not_translate:
        if name.lower() in src_lower and name.lower() not in tgt_lower:
            issues.append(
                ValidationIssue(
                    unit_id=source.unit_id,
                    page=source.page_number,
                    check_type="do_not_translate",
                    severity=ValidationSeverity.WARNING,
                    message=f"Brak nazwy wlasnej '{name}' w tlumaczeniu",
                    source_text=source.source_text,
                    translated_text=translated.translated_text,
                )
            )

    return issues


def _check_trailing_punctuation(
    source: TranslationUnit, translated: TranslatedUnit
) -> list[ValidationIssue]:
    """Check that trailing punctuation matches."""
    issues: list[ValidationIssue] = []
    src = source.source_text.strip()
    tgt = translated.translated_text.strip()

    if src and tgt and src[-1] in ".!?:" and tgt[-1] != src[-1]:
        issues.append(
            ValidationIssue(
                unit_id=source.unit_id,
                page=source.page_number,
                check_type="punctuation",
                severity=ValidationSeverity.INFO,
                message=f"Inna interpunkcja koncowa: '{src[-1]}' vs '{tgt[-1]}'",
                source_text=source.source_text,
                translated_text=translated.translated_text,
            )
        )

    return issues


def validate_catalog(
    pages: list[list[TranslationUnit]],
    batches: list[BatchResult],
    glossary: GlossaryConfig | None,
    target_lang: str,
) -> ValidationReport:
    """Run all validation checks on translated catalog.

    Args:
        pages: Original structured pages.
        batches: Translation results per batch.
        glossary: Optional glossary for terminology checks.
        target_lang: Target language ISO code.

    Returns:
        ValidationReport with all issues found.
    """
    all_issues: list[ValidationIssue] = []
    total_checked = 0

    # Build lookup: unit_id → source unit
    source_map: dict[str, TranslationUnit] = {}
    for page_units in pages:
        for u in page_units:
            source_map[u.unit_id] = u

    for batch in batches:
        if batch.error:
            continue
        for tu in batch.units:
            source = source_map.get(tu.unit_id)
            if not source or not tu.translated_text:
                continue

            total_checked += 1

            # Empty translation
            if not tu.translated_text.strip():
                all_issues.append(
                    ValidationIssue(
                        unit_id=tu.unit_id,
                        page=source.page_number,
                        check_type="empty",
                        severity=ValidationSeverity.ERROR,
                        message="Brak tlumaczenia",
                        source_text=source.source_text,
                        translated_text="",
                    )
                )
                continue

            all_issues.extend(_check_number_preservation(source, tu))
            all_issues.extend(_check_diacritics(source, tu, target_lang))
            all_issues.extend(_check_length_ratio(source, tu))
            all_issues.extend(_check_trailing_punctuation(source, tu))

            if glossary:
                all_issues.extend(_check_terminology(source, tu, glossary))

    errors = sum(1 for i in all_issues if i.severity == ValidationSeverity.ERROR)
    warnings = sum(1 for i in all_issues if i.severity == ValidationSeverity.WARNING)

    return ValidationReport(
        issues=all_issues,
        total_checked=total_checked,
        errors_count=errors,
        warnings_count=warnings,
    )
