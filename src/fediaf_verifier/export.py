"""Report export — JSON and TXT formatters."""


from fediaf_verifier.models import (
    DesignAnalysisResult,
    EnrichedReport,
    LabelStructureCheckResult,
    LinguisticCheckResult,
    TranslationResult,
)


def to_json(report: EnrichedReport) -> str:
    """Serialize report to pretty-printed JSON."""
    return report.model_dump_json(indent=2, exclude_none=True)


def to_text(report: EnrichedReport, filename: str, market: str | None) -> str:
    """Format report as human-readable text."""
    lines = [
        "=" * 60,
        "RAPORT WERYFIKACJI FEDIAF",
        "=" * 60,
        f"Plik:            {filename}",
        f"Rynek:           {market or 'nie okreslono'}",
        f"Status:          {report.status.value}",
        f"Wynik zgodnosci: {report.compliance_score}/100",
        f"Pewnosc odczytu: {report.extraction_confidence.value}",
        f"Wymaga przegladu: {'TAK' if report.requires_human_review else 'NIE'}",
        "",
    ]

    # Product info
    p = report.product
    lines.extend([
        "PRODUKT:",
        f"  Gatunek:    {p.species.value}",
        f"  Etap zycia: {p.lifestage.value}",
        f"  Typ karmy:  {p.food_type.value}",
    ])
    if p.name:
        lines.append(f"  Nazwa:      {p.name}")
    if p.brand:
        lines.append(f"  Marka:      {p.brand}")
    lines.append("")

    # Reliability flags
    if report.reliability_flags:
        lines.append("OSTRZEZENIA O RZETELNOSCI:")
        for flag in report.reliability_flags:
            lines.append(f"  ! {flag}")
        lines.append("")

    # Hard rule flags
    if report.hard_rule_flags:
        lines.append("PROBLEMY WYKRYTE PRZEZ REGULY DETERMINISTYCZNE:")
        for flag in report.hard_rule_flags:
            lines.append(
                f"  [REGULA][{flag.severity.value}] {flag.description}"
            )
        lines.append("")

    # Cross-check
    cross = report.cross_check_result
    if cross.passed is not None:
        lines.append("WERYFIKACJA KRZYZOWA:")
        if cross.passed:
            lines.append("  Oba odczyty zgodne — wartosci potwierdzone.")
        else:
            lines.append(
                f"  Znaleziono {len(cross.discrepancies)} rozbieznosci:"
            )
            for d in cross.discrepancies:
                lines.append(
                    f"    {d.nutrient}: glowny {d.main_value}%, "
                    f"krzyzowy {d.cross_value}% (roznica {d.difference}%)"
                )
        if cross.reading_notes:
            lines.append(f"  Uwagi: {cross.reading_notes}")
        lines.append("")

    # Linguistic check
    ling = report.linguistic_check_result
    if ling.performed and ling.report:
        lr = ling.report
        ISSUE_TYPE_LABELS = {
            "spelling": "ORTOGRAFIA",
            "grammar": "GRAMATYKA",
            "punctuation": "INTERPUNKCJA",
            "diacritics": "DIAKRYTYKI",
            "terminology": "TERMINOLOGIA",
        }
        lines.extend([
            "WERYFIKACJA JEZYKOWA:",
            f"  Jezyk: {lr.detected_language_name} ({lr.detected_language})",
            f"  Jakosc: {lr.overall_quality}",
            f"  {lr.summary}",
        ])
        if lr.issues:
            lines.append(f"  Znalezione problemy ({len(lr.issues)}):")
            for li in lr.issues:
                type_label = ISSUE_TYPE_LABELS.get(li.issue_type, li.issue_type)
                lines.append(
                    f'    [{type_label}] "{li.original}" -> '
                    f'"{li.suggestion}" ({li.explanation})'
                )
        else:
            lines.append("  Brak bledow jezykowych.")
        lines.append("")

    # Issues
    lines.append(f"PROBLEMY REGULACYJNE ({len(report.issues)}):")
    if not report.issues:
        lines.append("  Brak problemow regulacyjnych.")
    else:
        for issue in report.issues:
            src = " [REGULA]" if issue.source == "HARD_RULE" else ""
            lines.append(
                f"  [{issue.severity.value}{src}] {issue.description}"
            )
            if issue.fediaf_reference:
                lines.append(f"    Odniesienie: {issue.fediaf_reference}")
            if issue.found_value is not None:
                lines.append(
                    f"    Znaleziono: {issue.found_value} | "
                    f"Wymagane: {issue.required_value or '—'}"
                )
    lines.append("")

    # EU labelling
    eu = report.eu_labelling_check
    lines.append("WYMAGANIA ETYKIETOWANIA EU (Rozp. 767/2009):")
    eu_items = {
        "Lista skladnikow": eu.ingredients_listed,
        "Skladniki analityczne": eu.analytical_constituents_present,
        "Dane producenta": eu.manufacturer_info,
        "Masa netto": eu.net_weight_declared,
        "Gatunek zwierzecia": eu.species_clearly_stated,
        "Nr partii / data": eu.batch_or_date_present,
    }
    for label, val in eu_items.items():
        icon = "OK" if val else "BRAK"
        lines.append(f"  [{icon}] {label}")
    lines.append("")

    # Packaging check
    pkg = report.packaging_check
    CLASSIFICATION_LABELS = {
        "complete": "Karma pelnoporcjowa",
        "complementary": "Karma uzupelniajaca",
        "treat": "Przysmak",
        "not_stated": "Nie okreslono",
    }
    lines.append("KONTROLA OPAKOWANIA:")
    lines.append(
        f"  Klasyfikacja: "
        f"{CLASSIFICATION_LABELS.get(pkg.product_classification, pkg.product_classification)}"
    )
    pkg_items = {
        "Instrukcja dawkowania": pkg.feeding_guidelines_present,
        "Przechowywanie": pkg.storage_instructions_present,
        "Symbol e przy masie": pkg.net_weight_e_symbol,
        "Kraj pochodzenia": pkg.country_of_origin_stated,
        "Brak claimow leczniczych": pkg.no_therapeutic_claims,
        "Regula % w nazwie OK": pkg.naming_percentage_rule_ok,
        "Oznaczenia recyklingu": pkg.recycling_symbols_present,
        "Kod EAN widoczny": pkg.barcode_visible,
        "Kod QR widoczny": pkg.qr_code_visible,
        "Emblemat gatunku": pkg.species_emblem_present,
        "Miejsce na date/partie": pkg.date_marking_area_present,
        "Tlumaczenia kompletne": pkg.translations_complete,
        "Kody krajow": pkg.country_codes_for_languages,
        "Oswiadczenie FEDIAF": pkg.compliance_statement_present,
        "Kontakt do info (Art.19)": pkg.free_contact_for_info,
        "Nr zatwierdzenia zakladu": pkg.establishment_approval_number,
        "Deklaracja GMO": pkg.gmo_declaration_present,
        "Czytelnosc fontu": pkg.font_legibility_ok,
        "Polski kompletny": pkg.polish_language_complete,
    }
    if pkg.is_raw_product:
        pkg_items["Ostrzezenia raw/BARF"] = pkg.raw_warning_present
    if pkg.contains_insect_protein:
        pkg_items["Alergia krzyzowa (owady)"] = pkg.insect_allergen_warning
    if pkg.moisture_declaration_required:
        pkg_items["Wilgotnosc >14% zadeklarowana"] = pkg.moisture_declaration_present
    for label, val in pkg_items.items():
        icon = "OK" if val else "BRAK"
        lines.append(f"  [{icon}] {label}")
    if not pkg.claims_consistent_with_composition or pkg.claims_inconsistencies:
        lines.append("  SPOJNOSC CLAIMOW:")
        for inc in pkg.claims_inconsistencies:
            lines.append(f"    ! {inc}")
    if pkg.naming_percentage_notes:
        lines.append(f"  Regula % uwagi: {pkg.naming_percentage_notes}")
    if pkg.packaging_notes:
        for note in pkg.packaging_notes:
            lines.append(f"  Uwaga: {note}")
    lines.append("")

    # Recommendations
    if report.recommendations:
        lines.append("REKOMENDACJE:")
        for rec in report.recommendations:
            lines.append(f"  -> {rec}")
        lines.append("")

    # Market trends
    if report.market_trends and market:
        trends = report.market_trends
        lines.extend([
            f"TRENDY RYNKOWE — {market}:",
            f"  Pozycjonowanie: {trends.positioning.value}",
            f"  {trends.summary}",
        ])
        if trends.trend_notes:
            for note in trends.trend_notes:
                lines.append(f"  - {note}")
        lines.append("")

    # Disclaimer
    lines.extend([
        "=" * 60,
        "ZASTRZEZENIE: Raport wygenerowany automatycznie przez system AI.",
        "Wyniki < 85 pkt lub REQUIRES_REVIEW wymagaja weryfikacji eksperta",
        "ds. zywienia zwierzat przed podjeciem decyzji regulacyjnej.",
        "=" * 60,
    ])

    return "\n".join(lines)


def linguistic_to_text(result: LinguisticCheckResult, filename: str) -> str:
    """Format standalone linguistic check as human-readable text."""
    lines = [
        "=" * 60,
        "WERYFIKACJA JEZYKOWA — BULT Quality Check",
        "=" * 60,
        f"Plik: {filename}",
        "",
    ]

    if not result.performed or not result.report:
        lines.append(
            f"Weryfikacja nie powiodla sie: {result.error or 'nieznany blad'}"
        )
        return "\n".join(lines)

    lr = result.report
    ISSUE_TYPE_LABELS = {
        "spelling": "ORTOGRAFIA",
        "grammar": "GRAMATYKA",
        "punctuation": "INTERPUNKCJA",
        "diacritics": "DIAKRYTYKI",
        "terminology": "TERMINOLOGIA",
    }

    lines.extend([
        f"Jezyk:   {lr.detected_language_name} ({lr.detected_language})",
        f"Jakosc:  {lr.overall_quality}",
        f"Uwagi:   {lr.summary}",
        "",
    ])

    if lr.issues:
        lines.append(f"ZNALEZIONE PROBLEMY ({len(lr.issues)}):")
        for li in lr.issues:
            type_label = ISSUE_TYPE_LABELS.get(li.issue_type, li.issue_type)
            lines.append(
                f'  [{type_label}] "{li.original}" -> '
                f'"{li.suggestion}" ({li.explanation})'
            )
    else:
        lines.append("Brak bledow jezykowych.")

    lines.extend([
        "",
        "=" * 60,
        "Raport wygenerowany automatycznie. BULT Quality Check.",
        "=" * 60,
    ])

    return "\n".join(lines)


def structure_to_text(
    result: LabelStructureCheckResult, filename: str,
) -> str:
    """Format label structure & font check as human-readable text."""
    lines = [
        "=" * 60,
        "KONTROLA STRUKTURY ETYKIETY I CZCIONKI",
        "BULT Quality Check",
        "=" * 60,
        f"Plik: {filename}",
        "",
    ]

    if not result.performed or not result.report:
        lines.append(
            f"Kontrola nie powiodla sie: {result.error or 'nieznany blad'}"
        )
        return "\n".join(lines)

    r = result.report

    STATUS_LABELS = {
        "ok": "OK — brak problemow",
        "warnings": "OSTRZEZENIA — wykryto potencjalne problemy",
        "errors": "BLEDY — wymagana korekta",
    }
    lines.extend([
        f"Status: {STATUS_LABELS.get(r.overall_status, r.overall_status)}",
        f"Sekcji jezykowych: {r.section_count}",
        f"Problemow z czcionka: {r.font_issues_count}",
        f"Podsumowanie: {r.summary}",
        "",
    ])

    # Language sections
    if r.language_sections:
        lines.append("SEKCJE JEZYKOWE:")
        lines.append("-" * 40)
        for sec in r.language_sections:
            marker_info = (
                f"{sec.marker_type}: \"{sec.marker_text}\""
                if sec.marker_present
                else "BRAK MARKERA"
            )
            lines.append(
                f"  [{sec.language_code.upper()}] {sec.language_name} "
                f"— marker: {marker_info}"
            )
            lines.append(
                f"    Tresc: {'obecna' if sec.content_present else 'BRAK'} | "
                f"Kompletna: {'tak' if sec.content_complete else 'NIE'}"
            )
            if sec.section_elements:
                lines.append(
                    f"    Elementy: {', '.join(sec.section_elements)}"
                )
            if sec.missing_elements:
                lines.append(
                    f"    BRAKUJE: {', '.join(sec.missing_elements)}"
                )
            if sec.notes:
                lines.append(f"    Uwagi: {sec.notes}")
        lines.append("")

    # Diacritics check
    if r.diacritics_check:
        lines.append("KOMPLETNOSC DIAKRYTYKOW (per jezyk):")
        for lang, ok in r.diacritics_check.items():
            icon = "OK" if ok else "PROBLEM"
            lines.append(f"  [{icon}] {lang.upper()}")
        lines.append("")

    # Structure issues
    if r.structure_issues:
        lines.append(f"PROBLEMY STRUKTURALNE ({len(r.structure_issues)}):")
        lines.append("-" * 40)
        SEV_MAP = {
            "critical": "KRYTYCZNY",
            "warning": "OSTRZEZENIE",
            "info": "INFO",
        }
        for si in r.structure_issues:
            sev = SEV_MAP.get(si.severity, si.severity.upper())
            langs = ", ".join(si.affected_languages) if si.affected_languages else "—"
            lines.append(f"  [{sev}] {si.description}")
            lines.append(f"    Typ: {si.issue_type} | Jezyki: {langs}")
            if si.location:
                lines.append(f"    Lokalizacja: {si.location}")
        lines.append("")

    # Glyph/font issues
    if r.glyph_issues:
        lines.append(f"PROBLEMY Z CZCIONKA/GLIFAMI ({len(r.glyph_issues)}):")
        lines.append("-" * 40)
        for gi in r.glyph_issues:
            lines.append(
                f"  [{gi.language_code.upper()}] {gi.issue_type}: "
                f"\"{gi.affected_text}\" -> \"{gi.expected_text}\""
            )
            if gi.missing_characters:
                lines.append(
                    f"    Brakujace znaki: {' '.join(gi.missing_characters)}"
                )
            if gi.location:
                lines.append(f"    Lokalizacja: {gi.location}")
            if gi.explanation:
                lines.append(f"    Wyjasnienie: {gi.explanation}")
        lines.append("")

    if not r.structure_issues and not r.glyph_issues:
        lines.append("Nie wykryto problemow strukturalnych ani z czcionka.")
        lines.append("")

    lines.extend([
        "=" * 60,
        "Raport wygenerowany automatycznie. BULT Quality Check.",
        "=" * 60,
    ])

    return "\n".join(lines)


def translation_to_text(
    result: TranslationResult, source_label: str,
) -> str:
    """Format translation as human-readable text."""
    lines = [
        "=" * 60,
        "TLUMACZENIE ETYKIETY — BULT Quality Check",
        "=" * 60,
        f"Zrodlo: {source_label}",
        "",
    ]

    if not result.performed or not result.report:
        lines.append(
            f"Tlumaczenie nie powiodlo sie: {result.error or 'nieznany blad'}"
        )
        return "\n".join(lines)

    r = result.report
    lines.extend([
        f"Jezyk zrodlowy: {r.source_language_name} ({r.source_language})",
        f"Jezyk docelowy: {r.target_language_name} ({r.target_language})",
        f"Sekcji: {len(r.sections)}",
        "",
    ])

    for sec in r.sections:
        lines.append("-" * 60)
        lines.append(f"SEKCJA: {sec.section_name}")
        lines.append("-" * 60)
        lines.append("ORYGINAL:")
        for ln in sec.original_text.splitlines():
            lines.append(f"  {ln}")
        lines.append("")
        lines.append("TLUMACZENIE:")
        for ln in sec.translated_text.splitlines():
            lines.append(f"  {ln}")
        if sec.notes:
            lines.append(f"\nUWAGI: {sec.notes}")
        lines.append("")

    if r.overall_notes:
        lines.append(f"UWAGI OGOLNE: {r.overall_notes}")
        lines.append("")

    if r.summary:
        lines.append(f"PODSUMOWANIE: {r.summary}")
        lines.append("")

    lines.extend([
        "=" * 60,
        "Raport wygenerowany automatycznie. BULT Quality Check.",
        "=" * 60,
    ])

    return "\n".join(lines)


def design_to_text(
    result: DesignAnalysisResult, filename: str,
) -> str:
    """Format design analysis as human-readable text for R&D."""
    lines = [
        "=" * 60,
        "ANALIZA PROJEKTU GRAFICZNEGO ETYKIETY",
        "BULT Quality Check — raport dla R&D",
        "=" * 60,
        f"Plik: {filename}",
        "",
    ]

    if not result.performed or not result.report:
        lines.append(
            f"Analiza nie powiodla sie: {result.error or 'nieznany blad'}"
        )
        return "\n".join(lines)

    r = result.report
    lines.extend([
        f"OCENA OGOLNA: {r.overall_score}/100",
        f"{r.overall_assessment}",
        "",
    ])

    # Category scores
    if r.category_scores:
        lines.append("OCENY PER KATEGORIA:")
        lines.append("-" * 40)
        for cat in r.category_scores:
            lines.append(
                f"  [{cat.score:3d}/100] {cat.category_name.upper()}"
            )
            if cat.findings:
                lines.append("    Obserwacje:")
                for f in cat.findings:
                    lines.append(f"      - {f}")
            if cat.recommendations:
                lines.append("    Rekomendacje:")
                for rec in cat.recommendations:
                    lines.append(f"      -> {rec}")
            lines.append("")

    # Strengths
    if r.strengths:
        lines.append("MOCNE STRONY:")
        for s in r.strengths:
            lines.append(f"  + {s}")
        lines.append("")

    # Issues sorted by severity
    if r.issues:
        SEV_ORDER = {"critical": 0, "major": 1, "minor": 2, "suggestion": 3}
        SEV_LABELS = {
            "critical": "KRYTYCZNY",
            "major": "ISTOTNY",
            "minor": "DROBNY",
            "suggestion": "SUGESTIA",
        }
        sorted_issues = sorted(
            r.issues, key=lambda i: SEV_ORDER.get(i.severity, 9)
        )
        lines.append(f"PROBLEMY ({len(r.issues)}):")
        lines.append("-" * 40)
        for issue in sorted_issues:
            sev = SEV_LABELS.get(issue.severity, issue.severity.upper())
            lines.append(f"  [{sev}] {issue.description}")
            if issue.recommendation:
                lines.append(f"    -> {issue.recommendation}")
            if issue.location:
                lines.append(f"    Lokalizacja: {issue.location}")
        lines.append("")

    # Competitive benchmarks
    if r.competitive_benchmarks:
        lines.append("BENCHMARK KONKURENCYJNY:")
        lines.append("-" * 40)
        for bm in r.competitive_benchmarks:
            lines.append(f"  {bm.aspect}:")
            lines.append(f"    Obecny poziom:    {bm.current_level}")
            lines.append(f"    Standard branzy:  {bm.industry_standard}")
            lines.append(f"    -> {bm.suggestion}")
        lines.append("")

    # Trends
    if r.trend_alignment:
        lines.append("TRENDY BRANZOWE:")
        for t in r.trend_alignment:
            lines.append(f"  - {t}")
        lines.append("")

    # Executive summary
    if r.actionable_summary:
        lines.append("PODSUMOWANIE DLA R&D:")
        lines.append("-" * 40)
        lines.append(f"  {r.actionable_summary}")
        lines.append("")

    lines.extend([
        "=" * 60,
        "Raport wygenerowany automatycznie. BULT Quality Check.",
        "=" * 60,
    ])

    return "\n".join(lines)
