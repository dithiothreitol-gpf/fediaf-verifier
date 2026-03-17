"""Report export — JSON and TXT formatters."""


from fediaf_verifier.models import EnrichedReport


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
