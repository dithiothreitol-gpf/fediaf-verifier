"""Report export — JSON and TXT formatters."""


from fediaf_verifier.models import (
    ArtworkInspectionResult,
    ClaimsCheckResult,
    DesignAnalysisResult,
    EANCheckResult,
    EnrichedReport,
    LabelDiffResult,
    LabelStructureCheckResult,
    LabelTextResult,
    LinguisticCheckResult,
    MarketCheckResult,
    PresentationCheckResult,
    ProductDescriptionResult,
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
        "WERYFIKACJA JEZYKOWA — BULT Quality Assurance",
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
        "Raport wygenerowany automatycznie. BULT Quality Assurance.",
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
        "BULT Quality Assurance",
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
        "Raport wygenerowany automatycznie. BULT Quality Assurance.",
        "=" * 60,
    ])

    return "\n".join(lines)


def translation_to_text(
    result: TranslationResult, source_label: str,
) -> str:
    """Format translation as human-readable text."""
    lines = [
        "=" * 60,
        "TLUMACZENIE ETYKIETY — BULT Quality Assurance",
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
        "Raport wygenerowany automatycznie. BULT Quality Assurance.",
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
        "BULT Quality Assurance — raport dla R&D",
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

    # Competitive benchmarks (AI qualitative)
    if r.competitive_benchmarks:
        lines.append("BENCHMARK KONKURENCYJNY:")
        lines.append("-" * 40)
        for bm in r.competitive_benchmarks:
            lines.append(f"  {bm.aspect}:")
            lines.append(f"    Obecny poziom:    {bm.current_level}")
            lines.append(f"    Standard branzy:  {bm.industry_standard}")
            lines.append(f"    -> {bm.suggestion}")
        lines.append("")

    # Quantitative benchmarks
    if r.benchmark_comparisons:
        seg = r.benchmark_comparisons[0].segment if r.benchmark_comparisons else "?"
        lines.append(f"BENCHMARK ILOSCIOWY (segment: {seg}):")
        lines.append("-" * 40)
        for bc in r.benchmark_comparisons:
            lines.append(
                f"  {bc.category_name}: {bc.score}/100 "
                f"(percentyl: {bc.percentile}, "
                f"p25={bc.benchmark_low} med={bc.benchmark_median} "
                f"p75={bc.benchmark_high}) — {bc.verdict}"
            )
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
        "Raport wygenerowany automatycznie. BULT Quality Assurance.",
        "=" * 60,
    ])

    return "\n".join(lines)


def ean_to_text(result: EANCheckResult, filename: str) -> str:
    """Format EAN/barcode check as human-readable text."""
    lines = [
        "=" * 60,
        "WALIDACJA KODOW KRESKOWYCH I QR",
        "BULT Quality Assurance",
        "=" * 60,
        f"Plik: {filename}",
        "",
    ]

    if not result.performed or not result.report:
        lines.append(
            f"Walidacja nie powiodla sie: {result.error or 'nieznany blad'}"
        )
        return "\n".join(lines)

    r = result.report
    lines.extend([
        f"Kodow kreskowych: {r.barcodes_found}",
        f"Wszystkie poprawne: {'TAK' if r.all_valid else 'NIE'}",
        "",
    ])

    if r.ean_results:
        lines.append("KODY KRESKOWE:")
        lines.append("-" * 40)
        for ean in r.ean_results:
            valid = "OK" if ean.check_digit_valid else "BLEDNY"
            lines.append(
                f"  [{valid}] {ean.barcode_type}: {ean.barcode_number}"
            )
            if ean.country_name:
                lines.append(
                    f"    Kraj: {ean.country_name} (prefiks {ean.country_prefix})"
                )
            if not ean.check_digit_valid and ean.expected_check_digit:
                lines.append(
                    f"    Oczekiwana cyfra kontrolna: {ean.expected_check_digit}"
                )
            if ean.notes:
                lines.append(f"    Uwagi: {ean.notes}")
        lines.append("")

    if r.qr_codes:
        lines.append("KODY QR:")
        lines.append("-" * 40)
        for qr in r.qr_codes:
            status = "czytelny" if qr.readable else "nieczytelny"
            lines.append(f"  [{status}] {qr.content or '(brak tresci)'}")
            if qr.notes:
                lines.append(f"    Uwagi: {qr.notes}")
        lines.append("")

    if r.summary:
        lines.append(f"Podsumowanie: {r.summary}")
        lines.append("")

    lines.extend([
        "=" * 60,
        "Raport wygenerowany automatycznie. BULT Quality Assurance.",
        "=" * 60,
    ])

    return "\n".join(lines)


def claims_to_text(result: ClaimsCheckResult, filename: str) -> str:
    """Format claims vs composition check as human-readable text."""
    lines = [
        "=" * 60,
        "WALIDACJA CLAIMOW VS SKLAD",
        "BULT Quality Assurance",
        "=" * 60,
        f"Plik: {filename}",
        "",
    ]

    if not result.performed or not result.report:
        lines.append(
            f"Walidacja nie powiodla sie: {result.error or 'nieznany blad'}"
        )
        return "\n".join(lines)

    r = result.report

    CONSISTENCY_LABELS = {
        "consistent": "SPOJNE — brak problemow",
        "inconsistencies_found": "NIESPOJNOSCI — wykryto problemy",
        "critical_issues": "KRYTYCZNE — wymagana natychmiastowa korekta",
    }
    lines.extend([
        f"Status: {CONSISTENCY_LABELS.get(r.overall_consistency, r.overall_consistency)}",
        f"Wynik: {r.score}/100",
        f"Podsumowanie: {r.summary}",
        "",
    ])

    # Claims found
    if r.claims_found:
        lines.append(f"ZNALEZIONE CLAIMY ({len(r.claims_found)}):")
        for claim in r.claims_found:
            lines.append(f"  - {claim}")
        lines.append("")

    # Ingredients with percentages
    if r.ingredients_with_percentages:
        lines.append("SKLADNIKI Z PROCENTAMI:")
        for ing in r.ingredients_with_percentages:
            lines.append(f"  - {ing}")
        lines.append("")

    # Claim validations
    if r.claim_validations:
        SEV_MAP = {
            "critical": "KRYTYCZNY",
            "warning": "OSTRZEZENIE",
            "info": "INFO",
        }
        lines.append(f"WERYFIKACJA CLAIMOW ({len(r.claim_validations)}):")
        lines.append("-" * 40)
        for cv in r.claim_validations:
            sev = SEV_MAP.get(cv.severity, cv.severity.upper())
            status = "OK" if cv.is_consistent else "NIESPOJNY"
            lines.append(
                f"  [{status}][{sev}] {cv.claim_text} ({cv.claim_category})"
            )
            if not cv.is_consistent and cv.inconsistency_description:
                lines.append(f"    Problem: {cv.inconsistency_description}")
            if cv.relevant_ingredients:
                lines.append(
                    f"    Skladniki: {', '.join(cv.relevant_ingredients)}"
                )
            if cv.recommendation:
                lines.append(f"    -> {cv.recommendation}")
        lines.append("")

    # Naming rule check
    if r.naming_rule_check:
        nr = r.naming_rule_check
        status = "OK" if nr.compliant else "NIEZGODNY"
        lines.append("REGULA % W NAZWIE (EU 767/2009):")
        lines.append("-" * 40)
        lines.append(f"  [{status}] Nazwa: {nr.product_name}")
        lines.append(
            f"    Slowo kluczowe: \"{nr.trigger_word}\" "
            f"-> min {nr.required_minimum_percent}% {nr.ingredient_name}"
        )
        if nr.actual_percent is not None:
            lines.append(f"    Faktyczny %: {nr.actual_percent}%")
        if nr.notes:
            lines.append(f"    Uwagi: {nr.notes}")
        lines.append("")

    # Grain-free check
    if r.grain_free_check_passed is not None:
        status = "OK" if r.grain_free_check_passed else "NIESPOJNY"
        lines.append(f"CLAIM \"BEZ ZBOZ\": [{status}]")
        if r.grain_ingredients_found:
            lines.append(
                f"  Znalezione zboze: {', '.join(r.grain_ingredients_found)}"
            )
        lines.append("")

    # Therapeutic claims
    if r.therapeutic_claims_found:
        lines.append(
            f"CLAIMY TERAPEUTYCZNE (ZABRONIONE) ({len(r.therapeutic_claims_found)}):"
        )
        for tc in r.therapeutic_claims_found:
            lines.append(f"  ! {tc}")
        lines.append("")

    lines.extend([
        "=" * 60,
        "Raport wygenerowany automatycznie. BULT Quality Assurance.",
        "=" * 60,
    ])

    return "\n".join(lines)


def presentation_to_text(
    result: PresentationCheckResult, filename: str,
) -> str:
    """Format commercial presentation compliance check as human-readable text."""
    lines = [
        "=" * 60,
        "WALIDACJA PREZENTACJI HANDLOWEJ",
        "BULT Quality Assurance",
        "=" * 60,
        f"Plik: {filename}",
        "",
    ]

    if not result.performed or not result.report:
        lines.append(
            f"Walidacja nie powiodla sie: {result.error or 'nieznany blad'}"
        )
        return "\n".join(lines)

    r = result.report

    COMPLIANCE_LABELS = {
        "compliant": "ZGODNE — brak problemow",
        "issues_found": "PROBLEMY — wykryto niezgodnosci",
        "critical_issues": "KRYTYCZNE — wymagana natychmiastowa korekta",
    }
    lines.extend([
        f"Status: {COMPLIANCE_LABELS.get(r.overall_compliance, r.overall_compliance)}",
        f"Wynik: {r.score}/100",
        f"Podsumowanie: {r.summary}",
        "",
    ])

    SEV_MAP = {
        "critical": "KRYTYCZNY",
        "warning": "OSTRZEZENIE",
        "info": "INFO",
    }

    # -- Product context -------------------------------------------------------
    lines.append("KONTEKST PRODUKTU:")
    lines.append("-" * 40)
    if r.product_name:
        lines.append(f"  Nazwa produktu: {r.product_name}")
    if r.brand_name:
        lines.append(f"  Marka: {r.brand_name}")
    if r.product_classification:
        lines.append(f"  Klasyfikacja: {r.product_classification}")
    if r.food_type:
        lines.append(f"  Typ karmy: {r.food_type}")
    if r.species:
        lines.append(f"  Gatunek: {r.species}")
    if r.lifestage:
        lines.append(f"  Etap zycia: {r.lifestage}")
    lines.append("")

    if r.ingredients_with_percentages:
        lines.append("SKLADNIKI Z PROCENTAMI:")
        for ing in r.ingredients_with_percentages:
            lines.append(f"  - {ing}")
        lines.append("")

    if r.additives_list:
        lines.append("DODATKI:")
        for add in r.additives_list:
            lines.append(f"  - {add}")
        lines.append("")

    # -- Section 1: Recipes ----------------------------------------------------
    lines.append(f"--- SEKCJA 1: RECEPTURY ({r.recipe_section_score}/100) ---")
    if r.recipe_claims_found:
        lines.append(f"Znalezione claimy recepturowe ({len(r.recipe_claims_found)}):")
        for claim in r.recipe_claims_found:
            lines.append(f"  - {claim}")
        lines.append("")

    if r.recipe_claim_checks:
        lines.append(f"WERYFIKACJA ({len(r.recipe_claim_checks)}):")
        lines.append("-" * 40)
        for rc in r.recipe_claim_checks:
            sev = SEV_MAP.get(rc.severity, rc.severity.upper())
            status = "OK" if rc.compliant else "NIEZGODNY"
            lines.append(f"  [{status}][{sev}] {rc.claim_text} ({rc.claim_type})")
            if rc.regulation_reference:
                lines.append(f"    Podstawa: {rc.regulation_reference}")
            if rc.finding:
                lines.append(f"    Ustalenie: {rc.finding}")
            if not rc.compliant and rc.issue_description:
                lines.append(f"    Problem: {rc.issue_description}")
            if rc.recommendation:
                lines.append(f"    -> {rc.recommendation}")
        lines.append("")
    elif not r.recipe_claims_found:
        lines.append("  Brak claimow recepturowych na etykiecie.")
        lines.append("")

    # -- Section 2: Names ------------------------------------------------------
    lines.append(f"--- SEKCJA 2: NAZWY ({r.naming_section_score}/100) ---")
    if r.naming_convention_checks:
        lines.append(
            f"REGULY PROCENTOWE ({len(r.naming_convention_checks)}):"
        )
        lines.append("-" * 40)
        for nc in r.naming_convention_checks:
            status = "OK" if nc.compliant else "NIEZGODNY"
            lines.append(
                f"  [{status}] {nc.product_name} — "
                f"\"{nc.trigger_expression}\" -> {nc.applicable_rule}"
            )
            lines.append(
                f"    Wymagane: min {nc.required_minimum_percent}% "
                f"{nc.highlighted_ingredient}"
            )
            if nc.actual_percent is not None:
                lines.append(f"    Znalezione: {nc.actual_percent}%")
            if nc.notes:
                lines.append(f"    Uwagi: {nc.notes}")
        lines.append("")

    if r.name_consistency_checks:
        lines.append(
            f"SPOJNOSC NAZWY ({len(r.name_consistency_checks)}):"
        )
        lines.append("-" * 40)
        for ncc in r.name_consistency_checks:
            sev = SEV_MAP.get(ncc.severity, ncc.severity.upper())
            status = "OK" if ncc.compliant else "NIEZGODNY"
            lines.append(
                f"  [{status}][{sev}] {ncc.check_type}: {ncc.description}"
            )
            if ncc.finding:
                lines.append(f"    Ustalenie: {ncc.finding}")
            if not ncc.compliant and ncc.issue_description:
                lines.append(f"    Problem: {ncc.issue_description}")
            if ncc.recommendation:
                lines.append(f"    -> {ncc.recommendation}")
        lines.append("")

    # -- Section 3: Brand -----------------------------------------------------
    lines.append(f"--- SEKCJA 3: MARKA ({r.brand_section_score}/100) ---")
    if r.brand_compliance_checks:
        lines.append(
            f"ZGODNOSC MARKI ({len(r.brand_compliance_checks)}):"
        )
        lines.append("-" * 40)
        for bc in r.brand_compliance_checks:
            sev = SEV_MAP.get(bc.severity, bc.severity.upper())
            status = "OK" if bc.compliant else "NIEZGODNY"
            lines.append(
                f"  [{status}][{sev}] \"{bc.flagged_element}\" ({bc.check_type})"
            )
            if bc.regulation_reference:
                lines.append(f"    Podstawa: {bc.regulation_reference}")
            if not bc.compliant and bc.issue_description:
                lines.append(f"    Problem: {bc.issue_description}")
            if bc.recommendation:
                lines.append(f"    -> {bc.recommendation}")
        lines.append("")
    else:
        lines.append("  Brak elementow do weryfikacji w marce.")
        lines.append("")

    # -- Section 4: Trademarks ------------------------------------------------
    lines.append(
        f"--- SEKCJA 4: ZASTRZEZENIA ({r.trademark_section_score}/100) ---"
    )
    if r.trademark_checks:
        RISK_MAP = {
            "high": "WYSOKIE",
            "medium": "SREDNIE",
            "low": "NISKIE",
            "none": "BRAK",
        }
        lines.append(f"ANALIZA IP/TRADEMARK ({len(r.trademark_checks)}):")
        lines.append("-" * 40)
        for tc in r.trademark_checks:
            risk = RISK_MAP.get(tc.risk_level, tc.risk_level.upper())
            lines.append(
                f"  [Ryzyko: {risk}] \"{tc.element_text}\" ({tc.element_type})"
            )
            if tc.potential_owner:
                lines.append(f"    Potencjalny wlasciciel: {tc.potential_owner}")
            if tc.trademark_symbol_found and tc.trademark_symbol_found != "none":
                sym = "(R)" if tc.trademark_symbol_found == "registered" else "TM"
                lines.append(f"    Symbol na etykiecie: {sym}")
            if tc.issue_description:
                lines.append(f"    Opis: {tc.issue_description}")
            if tc.recommendation:
                lines.append(f"    -> {tc.recommendation}")
        lines.append("")
    else:
        lines.append("  Brak potencjalnych naruszen znakow towarowych.")
        lines.append("")

    lines.extend([
        "=" * 60,
        "Raport wygenerowany automatycznie. BULT Quality Assurance.",
        "=" * 60,
    ])

    return "\n".join(lines)


def label_text_to_text(result: LabelTextResult, product_name: str = "") -> str:
    """Format generated label text as human-readable output."""
    lines = [
        "=" * 60,
        "WYGENEROWANY TEKST ETYKIETY",
        "BULT Quality Assurance",
        "=" * 60,
    ]
    if product_name:
        lines.append(f"Produkt: {product_name}")
    lines.append("")

    if not result.performed or not result.report:
        lines.append(
            f"Generowanie nie powiodlo sie: {result.error or 'nieznany blad'}"
        )
        return "\n".join(lines)

    r = result.report
    lines.extend([
        f"Jezyk: {r.language_name} ({r.language})",
        f"Gatunek: {r.species}",
        f"Etap zycia: {r.lifestage}",
        f"Typ karmy: {r.food_type}",
        "",
    ])

    # Sections
    if r.sections:
        for sec in r.sections:
            lines.append("-" * 60)
            lines.append(f"SEKCJA: {sec.section_title}")
            if sec.regulatory_reference:
                lines.append(f"  Regulacja: {sec.regulatory_reference}")
            lines.append("-" * 60)
            for ln in sec.content.splitlines():
                lines.append(f"  {ln}")
            if sec.notes:
                lines.append(f"  Uwagi: {sec.notes}")
            lines.append("")

    # Feeding table
    if r.feeding_table:
        lines.append("TABELA DAWKOWANIA:")
        lines.append("-" * 40)
        lines.append(f"  {'Masa ciala':<20} {'Dawka dzienna':<20}")
        lines.append(f"  {'-' * 18:<20} {'-' * 18:<20}")
        for row in r.feeding_table:
            lines.append(f"  {row.weight_range:<20} {row.daily_amount:<20}")
        lines.append("")

    # Warnings
    if r.warnings:
        lines.append(f"OSTRZEZENIA ({len(r.warnings)}):")
        for w in r.warnings:
            lines.append(f"  ! {w}")
        lines.append("")

    # Complete text
    if r.complete_text:
        lines.append("=" * 60)
        lines.append("PELNY TEKST ETYKIETY:")
        lines.append("=" * 60)
        for ln in r.complete_text.splitlines():
            lines.append(ln)
        lines.append("")

    # Summary
    if r.summary:
        lines.append(f"Podsumowanie: {r.summary}")
        lines.append("")

    lines.extend([
        "=" * 60,
        "Tekst wygenerowany automatycznie. BULT Quality Assurance.",
        "=" * 60,
    ])

    return "\n".join(lines)


def product_description_to_text(
    result: ProductDescriptionResult, product_name: str = "",
) -> str:
    """Format generated product description as human-readable text."""
    lines = [
        "=" * 60,
        "WYGENEROWANY OPIS PRODUKTU",
        "BULT Quality Assurance",
        "=" * 60,
    ]
    if product_name:
        lines.append(f"Produkt: {product_name}")
    lines.append("")

    if not result.performed or not result.report:
        lines.append(
            f"Generowanie nie powiodlo sie: {result.error or 'nieznany blad'}"
        )
        return "\n".join(lines)

    r = result.report

    TONE_LABELS = {
        "premium": "Premium / Luksusowy",
        "scientific": "Naukowy / Weterynaryjny",
        "natural": "Naturalny / Wholesome",
        "standard": "Standardowy / Neutralny",
    }
    lines.extend([
        f"Jezyk: {r.language_name} ({r.language})",
        f"Gatunek: {r.species}",
        f"Etap zycia: {r.lifestage}",
        f"Typ karmy: {r.food_type}",
        f"Styl: {TONE_LABELS.get(r.tone, r.tone)}",
        "",
    ])

    # Headline
    if r.headline:
        lines.append("HEADLINE:")
        lines.append(f"  {r.headline}")
        lines.append("")

    # Short description
    if r.short_description:
        lines.append("KROTKI OPIS (do kart produktowych):")
        lines.append("-" * 40)
        for ln in r.short_description.splitlines():
            lines.append(f"  {ln}")
        lines.append("")

    # Bullet points
    if r.bullet_points:
        lines.append(f"KLUCZOWE PUNKTY SPRZEDAZOWE ({len(r.bullet_points)}):")
        lines.append("-" * 40)
        for bp in r.bullet_points:
            lines.append(f"  - {bp}")
        lines.append("")

    # Sections
    if r.sections:
        for sec in r.sections:
            lines.append("-" * 60)
            lines.append(f"SEKCJA: {sec.section_title}")
            lines.append("-" * 60)
            for ln in sec.content.splitlines():
                lines.append(f"  {ln}")
            lines.append("")

    # SEO metadata
    if r.seo:
        lines.append("SEO METADATA:")
        lines.append("-" * 40)
        if r.seo.meta_title:
            lines.append(f"  Meta title: {r.seo.meta_title}")
        if r.seo.meta_description:
            lines.append(f"  Meta description: {r.seo.meta_description}")
        if r.seo.focus_keyword:
            lines.append(f"  Focus keyword: {r.seo.focus_keyword}")
        if r.seo.keywords:
            lines.append(f"  Keywords: {', '.join(r.seo.keywords)}")
        lines.append("")

    # Claims used
    if r.claims_used:
        lines.append(f"UZYTE CLAIMY ({len(r.claims_used)}):")
        for c in r.claims_used:
            lines.append(f"  + {c}")
        lines.append("")

    # Claims warnings
    if r.claims_warnings:
        WARNING_TYPE_MAP = {
            "forbidden_therapeutic": "ZAKAZANY CLAIM TERAPEUTYCZNY",
            "unsubstantiated": "BRAK UZASADNIENIA",
            "naming_rule_violation": "NARUSZENIE REGULY NAZEWNICTWA",
            "needs_evidence": "WYMAGA DOWODU",
        }
        lines.append(f"OSTRZEZENIA CLAIMOW ({len(r.claims_warnings)}):")
        lines.append("-" * 40)
        for cw in r.claims_warnings:
            wt = WARNING_TYPE_MAP.get(cw.warning_type, cw.warning_type.upper())
            lines.append(f"  ! [{wt}] {cw.claim_text}")
            if cw.explanation:
                lines.append(f"    Wyjasnienie: {cw.explanation}")
            if cw.recommendation:
                lines.append(f"    -> {cw.recommendation}")
        lines.append("")

    # Complete text
    if r.complete_text:
        lines.append("=" * 60)
        lines.append("PELNY OPIS PRODUKTU:")
        lines.append("=" * 60)
        for ln in r.complete_text.splitlines():
            lines.append(ln)
        lines.append("")

    # Summary
    if r.summary:
        lines.append(f"Podsumowanie: {r.summary}")
        lines.append("")

    lines.extend([
        "=" * 60,
        "Opis wygenerowany automatycznie. BULT Quality Assurance.",
        "=" * 60,
    ])

    return "\n".join(lines)


def market_check_to_text(
    result: MarketCheckResult, filename: str,
) -> str:
    """Format per-market compliance check as human-readable text."""
    lines = [
        "=" * 60,
        "WALIDACJA ZGODNOSCI RYNKOWEJ",
        "BULT Quality Assurance",
        "=" * 60,
        f"Plik: {filename}",
        "",
    ]

    if not result.performed or not result.report:
        lines.append(
            f"Walidacja nie powiodla sie: {result.error or 'nieznany blad'}"
        )
        return "\n".join(lines)

    r = result.report

    COMPLIANCE_LABELS = {
        "compliant": "ZGODNE — brak problemow",
        "issues_found": "PROBLEMY — wykryto niezgodnosci",
        "non_compliant": "NIEZGODNE — wymagana korekta",
    }
    lines.extend([
        f"Rynek docelowy: {r.target_market} ({r.target_market_code})",
        f"Status: {COMPLIANCE_LABELS.get(r.overall_compliance, r.overall_compliance)}",
        f"Wynik: {r.score}/100",
        f"Bazowa zgodnosc EU 767/2009: {'TAK' if r.base_eu_compliant else 'NIE'}",
        f"Wymagania jezykowe: {'SPELNIONE' if r.language_requirements_met else 'NIESPELNIONE'}",
        "",
    ])

    if r.language_notes:
        lines.append(f"Uwagi jezykowe: {r.language_notes}")
        lines.append("")

    # Market-specific requirements
    if r.market_specific_requirements:
        SEV_MAP = {
            "critical": "KRYTYCZNY",
            "warning": "OSTRZEZENIE",
            "info": "INFO",
        }
        CATEGORY_MAP = {
            "language": "JEZYK",
            "labeling": "ETYKIETOWANIE",
            "claims": "CLAIMY",
            "legal": "PRAWNE",
            "packaging": "OPAKOWANIE",
        }
        lines.append(
            f"WYMAGANIA SPECYFICZNE DLA RYNKU "
            f"({len(r.market_specific_requirements)}):"
        )
        lines.append("-" * 40)
        for req in r.market_specific_requirements:
            sev = SEV_MAP.get(req.severity, req.severity.upper())
            cat = CATEGORY_MAP.get(req.category, req.category.upper())
            status = "OK" if req.compliant else "NIEZGODNE"
            lines.append(
                f"  [{status}][{sev}] [{cat}] {req.description}"
            )
            if req.requirement_id:
                lines.append(f"    ID: {req.requirement_id}")
            if req.regulation_reference:
                lines.append(f"    Regulacja: {req.regulation_reference}")
            if req.finding:
                lines.append(f"    Znaleziono: {req.finding}")
            if not req.compliant and req.recommendation:
                lines.append(f"    -> {req.recommendation}")
        lines.append("")

    # Additional certifications
    if r.additional_certifications_recommended:
        lines.append("REKOMENDOWANE CERTYFIKATY:")
        for cert in r.additional_certifications_recommended:
            lines.append(f"  -> {cert}")
        lines.append("")

    # Summary
    if r.summary:
        lines.append(f"Podsumowanie: {r.summary}")
        lines.append("")

    lines.extend([
        "=" * 60,
        "Raport wygenerowany automatycznie. BULT Quality Assurance.",
        "=" * 60,
    ])

    return "\n".join(lines)


def diff_to_text(
    result: LabelDiffResult, old_filename: str, new_filename: str,
) -> str:
    """Format label diff as human-readable text."""
    lines = [
        "=" * 60,
        "POROWNANIE WERSJI ETYKIETY",
        "BULT Quality Assurance",
        "=" * 60,
        f"Stara wersja: {old_filename}",
        f"Nowa wersja:  {new_filename}",
        "",
    ]

    if not result.performed or not result.report:
        lines.append(
            f"Porownanie nie powiodlo sie: {result.error or 'nieznany blad'}"
        )
        return "\n".join(lines)

    r = result.report
    RISK_LABELS = {
        "low": "NISKI -- zmiany kosmetyczne",
        "medium": "SREDNI -- istotne zmiany, sprawdz",
        "high": "WYSOKI -- wymagana weryfikacja regulacyjna",
    }
    lines.extend([
        f"Poziom ryzyka: {RISK_LABELS.get(r.risk_level, r.risk_level)}",
        f"Liczba zmian: {r.change_count}",
        f"Ocena: {r.overall_assessment}",
        "",
    ])

    if r.text_changes:
        SEV_MAP = {"critical": "KRYTYCZNY", "warning": "OSTRZEZENIE", "info": "INFO"}
        lines.append(f"ZMIANY TRESCI ({len(r.text_changes)}):")
        lines.append("-" * 40)
        for ch in r.text_changes:
            sev = SEV_MAP.get(ch.severity, ch.severity.upper())
            lines.append(f"  [{sev}] [{ch.change_type}] {ch.section}")
            if ch.old_text:
                lines.append(f'    Bylo: "{ch.old_text}"')
            if ch.new_text:
                lines.append(f'    Jest: "{ch.new_text}"')
            if ch.regulatory_impact:
                lines.append(f"    Wplyw: {ch.regulatory_impact}")
        lines.append("")

    if r.layout_changes:
        lines.append(f"ZMIANY UKLADU ({len(r.layout_changes)}):")
        for lc in r.layout_changes:
            lines.append(f"  [{lc.severity.upper()}] {lc.description}")
        lines.append("")

    if r.new_issues_introduced:
        lines.append(f"NOWE PROBLEMY ({len(r.new_issues_introduced)}):")
        for ni in r.new_issues_introduced:
            lines.append(f"  ! [{ni.severity.upper()}] {ni.description}")
            if ni.introduced_by_change:
                lines.append(f"    Przyczyna: {ni.introduced_by_change}")
        lines.append("")

    if r.issues_resolved:
        lines.append(f"NAPRAWIONE PROBLEMY ({len(r.issues_resolved)}):")
        for ir_item in r.issues_resolved:
            lines.append(f"  + {ir_item}")
        lines.append("")

    if r.summary:
        lines.append(f"PODSUMOWANIE: {r.summary}")
        lines.append("")

    lines.extend([
        "=" * 60,
        "Raport wygenerowany automatycznie. BULT Quality Assurance.",
        "=" * 60,
    ])

    return "\n".join(lines)


def artwork_inspection_to_text(
    result: ArtworkInspectionResult, filename_a: str, filename_b: str = "",
) -> str:
    """Format artwork inspection report as human-readable text."""
    lines = [
        "=" * 60,
        "INSPEKCJA ARTWORK — RAPORT QA",
        "BULT Quality Assurance",
        "=" * 60,
        f"Plik A (master): {filename_a}",
    ]
    if filename_b:
        lines.append(f"Plik B (proof):  {filename_b}")
    lines.append("")

    if not result.performed or not result.report:
        lines.append(
            f"Inspekcja nie powiodla sie: {result.error or 'nieznany blad'}"
        )
        return "\n".join(lines)

    r = result.report
    VERDICT_MAP = {
        "pass": "POZYTYWNA",
        "review": "WYMAGA PRZEGLADU",
        "fail": "NEGATYWNA",
    }
    lines.extend([
        f"Ocena ogolna: {r.overall_score}/100",
        f"Werdykt: {VERDICT_MAP.get(r.overall_verdict, r.overall_verdict.upper())}",
        "",
    ])

    # -- Print readiness --
    if r.print_readiness:
        pr = r.print_readiness
        lines.extend([
            "-" * 40,
            "GOTOWOSC DO DRUKU",
            "-" * 40,
            f"  Format: {pr.file_format}",
            f"  DPI: {pr.dpi:.0f} ({'OK' if pr.dpi_sufficient else 'ZA NISKIE'})",
            f"  Przestrzen barw: {pr.color_space} "
            f"({'OK' if pr.color_space_print_ready else 'WYMAGA KONWERSJI'})",
            f"  Przezroczystosc: {'TAK' if pr.has_transparency else 'brak'}",
        ])
        if pr.fonts_embedded is not None:
            lines.append(
                f"  Fonty osadzone: {'TAK' if pr.fonts_embedded else 'NIE — krytyczne!'}"
            )
        if pr.has_bleed:
            lines.append("  Spad (bleed): wykryty")
        else:
            lines.append("  Spad (bleed): nie wykryty — dodaj min 3mm")
        if pr.page_size_mm:
            lines.append(
                f"  Rozmiar: {pr.page_size_mm[0]:.1f} x {pr.page_size_mm[1]:.1f} mm"
            )
        lines.append(
            f"  Score: {pr.score}/100 — {'GOTOWY' if pr.print_ready else 'NIE GOTOWY'}"
        )
        if pr.issues:
            lines.append("")
            SEV_PR = {"critical": "KRYTYCZNY", "warning": "OSTRZEZENIE", "info": "INFO"}
            for iss in pr.issues:
                sev = SEV_PR.get(iss.severity, iss.severity.upper())
                lines.append(f"  [{sev}] {iss.description}")
                if iss.recommendation:
                    lines.append(f"    -> {iss.recommendation}")
        lines.append("")

    # -- Color analysis --
    if r.color_analysis:
        ca = r.color_analysis
        lines.extend([
            "-" * 40,
            "ANALIZA KOLOROW",
            "-" * 40,
            f"  Przestrzen: {ca.color_space_detected}"
            f"{' (CMYK)' if ca.is_cmyk else ''}",
            "  Dominujace kolory:",
        ])
        for c in ca.dominant_colors:
            lines.append(f"    {c.hex} ({c.name}) — {c.percentage:.1f}%")

        if ca.comparisons:
            lines.extend([
                "",
                f"  Porownanie z wersja B (max Delta E: {ca.max_delta_e}):",
                f"  Spojnosc kolorow: {ca.color_consistency_score:.1f}/100",
            ])
            for comp in ca.comparisons:
                de_label = (
                    "niezauwazalne" if comp.delta_e < 2
                    else "drobna roznica" if comp.delta_e < 5
                    else "WIDOCZNA ZMIANA"
                )
                lines.append(
                    f"    {comp.color_a_hex} vs {comp.color_b_hex}: "
                    f"dE={comp.delta_e:.2f} ({de_label})"
                )
        lines.append("")

    # -- Pixel diff --
    if r.pixel_diff:
        pd = r.pixel_diff
        VERD_PX = {
            "identical": "IDENTYCZNE",
            "minor_changes": "DROBNE ZMIANY",
            "significant_changes": "ISTOTNE ZMIANY",
            "major_changes": "DUZE ZMIANY",
        }
        lines.extend([
            "-" * 40,
            "POROWNANIE PIKSELI",
            "-" * 40,
            f"  SSIM: {pd.ssim_score:.4f} (1.0 = identyczne)",
            f"  Zmienione piksele: {pd.changed_pixels_pct:.2f}% "
            f"({pd.changed_pixels:,} z {pd.total_pixels:,})",
            f"  Werdykt: {VERD_PX.get(pd.verdict, pd.verdict.upper())}",
        ])
        if pd.diff_regions:
            lines.append(f"  Regiony zmian ({len(pd.diff_regions)}):")
            for reg in pd.diff_regions:
                lines.append(
                    f"    [{reg.x},{reg.y} {reg.w}x{reg.h}] "
                    f"zmiana: {reg.change_pct:.1f}%"
                )
        lines.append("")

    # -- OCR text comparison --
    if r.ocr_comparison:
        ocr = r.ocr_comparison
        lines.extend([
            "-" * 40,
            "POROWNANIE TEKSTU (OCR)",
            "-" * 40,
            f"  Podobienstwo: {ocr.similarity_pct:.1f}%",
            f"  Zmiany: {ocr.total_changes}",
            f"  Pewnosc OCR: A={ocr.avg_confidence_a:.0%} B={ocr.avg_confidence_b:.0%}",
        ])
        if ocr.changes:
            lines.append("")
            CHG = {"added": "DODANO", "removed": "USUNIETO", "modified": "ZMIENIONO"}
            for ch in ocr.changes:
                chg_label = CHG.get(ch.change_type, ch.change_type.upper())
                lines.append(f"  [{chg_label}] linia {ch.line_number}")
                if ch.old_text:
                    lines.append(f'    Bylo: "{ch.old_text}"')
                if ch.new_text:
                    lines.append(f'    Jest: "{ch.new_text}"')
        lines.append("")

    # -- ICC profile --
    if r.icc_profile:
        icc = r.icc_profile
        lines.extend([
            "-" * 40,
            "PROFIL ICC",
            "-" * 40,
            f"  Profil: {'znaleziony' if icc.has_profile else 'BRAK'}",
        ])
        if icc.has_profile:
            lines.append(f"  Nazwa: {icc.profile_name}")
            lines.append(f"  Przestrzen: {icc.color_space}")
            lines.append(f"  Rendering intent: {icc.rendering_intent}")
        if icc.issues:
            for iss in icc.issues:
                lines.append(f"  ! {iss}")
        lines.append("")

    # -- Saliency --
    if r.saliency:
        sal = r.saliency
        lines.extend([
            "-" * 40,
            "ANALIZA UWAGI WIZUALNEJ",
            "-" * 40,
            f"  Model: {sal.model_used}",
            f"  Focus score: {sal.focus_score:.0f}/100",
        ])
        if sal.focus_metrics:
            fm = sal.focus_metrics
            lines.extend([
                f"    Entropia: {fm.entropy:.0f}/100",
                f"    Gini: {fm.gini:.3f}",
                f"    Klastry uwagi: {fm.cluster_count}",
            ])
        if sal.clarity:
            cl = sal.clarity
            lines.extend([
                f"  Czytelnosc: {cl.score:.0f}/100",
                f"    Gestosc krawedzi: {cl.edge_density:.4f}",
                f"    Kolory dominujace: {cl.color_complexity}",
                f"    Biala przestrzen: {cl.whitespace_ratio:.1%}",
                f"    Symetria: {cl.symmetry:.3f}",
            ])
        if sal.cognitive_load:
            cg = sal.cognitive_load
            lines.extend([
                f"  Obciazenie kognitywne: {cg.score:.0f}/100 "
                f"(latwosc przetwarzania: {cg.ease_score:.0f}/100)",
                f"    Zlozonosc czestotl.: {cg.frequency_complexity:.4f}",
                f"    Elementy wizualne: {cg.element_count}",
                f"    Roznorodnosc kolorow: {cg.color_diversity:.3f}",
                f"    Gestosc krawedzi: {cg.edge_density:.4f}",
            ])
        if sal.attention_regions:
            lines.append(f"  Regiony uwagi ({len(sal.attention_regions)}):")
            for reg in sal.attention_regions:
                lines.append(
                    f"    #{reg.rank}: {reg.attention_pct:.1f}% uwagi "
                    f"[{reg.x},{reg.y} {reg.w}x{reg.h}]"
                )
        lines.append("")

    # -- AI summary --
    if r.ai_summary:
        lines.extend([
            "-" * 40,
            "PODSUMOWANIE AI",
            "-" * 40,
            f"  {r.ai_summary}",
            "",
        ])
    if r.ai_recommendations:
        lines.append("REKOMENDACJE:")
        for i, rec in enumerate(r.ai_recommendations, 1):
            lines.append(f"  {i}. {rec}")
        lines.append("")

    lines.extend([
        "=" * 60,
        "Raport wygenerowany automatycznie — inspekcja artwork. BULT QA.",
        "=" * 60,
    ])

    return "\n".join(lines)
