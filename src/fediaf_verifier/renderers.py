"""Report rendering functions for Streamlit UI.

Extracted from app.py to keep the main module manageable.
Each function renders a specific report type using Streamlit widgets.
"""

from html import escape as _esc
from pathlib import Path

import streamlit as st

from fediaf_verifier.export import (
    artwork_inspection_to_text,
    claims_to_text,
    design_to_text,
    diff_to_text,
    ean_to_text,
    label_text_to_text,
    linguistic_to_text,
    market_check_to_text,
    presentation_to_text,
    product_description_to_text,
    structure_to_text,
    to_json,
    to_text,
    translation_to_text,
)
from fediaf_verifier.models import (
    EnrichedReport,
    ExtractionConfidence,
    LabelStructureCheckResult,
    LinguisticCheckResult,
)


def render_report(
    report: EnrichedReport, filename: str, market: str | None, settings,
) -> None:
    st.divider()
    st.subheader("Wyniki weryfikacji")

    score = report.compliance_score
    status = report.status.value
    confidence = report.extraction_confidence
    issues = report.issues
    critical = sum(1 for i in issues if i.severity.value == "CRITICAL")
    warnings = sum(1 for i in issues if i.severity.value == "WARNING")

    # -- Status banner (Layer 4) -------------------------------------------------------
    if report.requires_human_review:
        if (
            score < settings.manual_required_threshold
            or confidence == ExtractionConfidence.LOW
        ):
            st.markdown(
                '<div class="status-banner status-fail">'
                "\u26d4 <strong>Sk\u0142ad wymaga korekty przed dopuszczeniem "
                "do sprzeda\u017cy.</strong><br>"
                "Pobierz raport i przeka\u017c do specjalisty ds. \u017cywienia."
                "</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="status-banner status-warn">'
                "\u26a0\ufe0f <strong>S\u0105 kwestie do sprawdzenia</strong> "
                "\u2014 przejrzyj raport z ekspertem."
                "</div>",
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            '<div class="status-banner status-pass">'
            "\u2705 <strong>Sk\u0142ad zgodny</strong> "
            "\u2014 produkt gotowy do rynku."
            "</div>",
            unsafe_allow_html=True,
        )

    # -- Main metrics ------------------------------------------------------------------
    STATUS_LABELS = {
        "COMPLIANT": "\u2705 Zgodna",
        "NON_COMPLIANT": "\u274c Niezgodna",
        "REQUIRES_REVIEW": "\u26a0\ufe0f Do sprawdzenia",
    }
    CONF_LABELS = {
        ExtractionConfidence.HIGH: "\U0001f7e2 Wysoka",
        ExtractionConfidence.MEDIUM: "\U0001f7e1 \u015arednia",
        ExtractionConfidence.LOW: "\U0001f534 Niska",
    }

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Status", STATUS_LABELS.get(status, status))
    col2.metric("Wynik zgodno\u015bci", f"{score}/100")
    col3.metric("Pewno\u015b\u0107 odczytu", CONF_LABELS.get(confidence, str(confidence)))
    col4.metric("Problemy", f"{critical} kryt. / {warnings} ostrze\u017c.")

    # Score bar
    bar_color = "#00b464" if score >= 90 else ("#ffb400" if score >= 70 else "#dc3232")
    st.markdown(
        f'<div class="score-bar-bg">'
        f'<div class="score-bar-fill" style="width:{score}%;'
        f'background:{bar_color}"></div></div>',
        unsafe_allow_html=True,
    )

    # -- Reliability flags -------------------------------------------------------------
    if report.reliability_flags:
        with st.expander(
            f"\u26a0\ufe0f Ostrze\u017cenia o rzetelno\u015bci "
            f"({len(report.reliability_flags)})",
            expanded=True,
        ):
            for flag in report.reliability_flags:
                st.warning(flag)

    # -- Cross-check -------------------------------------------------------------------
    cross = report.cross_check_result
    with st.expander("Weryfikacja krzy\u017cowa warto\u015bci liczbowych"):
        if cross.passed is True:
            st.success(
                "Oba odczyty zgodne \u2014 warto\u015bci potwierdzone."
            )
        elif cross.passed is False:
            st.error(
                f"Rozbie\u017cno\u015bci mi\u0119dzy odczytami "
                f"({len(cross.discrepancies)}) \u2014 "
                "sprawd\u017a orygina\u0142 etykiety."
            )
            for d in cross.discrepancies:
                st.write(
                    f"\u2022 **{d.nutrient}**: odczyt g\u0142\u00f3wny "
                    f"{d.main_value}%, weryfikacja {d.cross_value}% "
                    f"(r\u00f3\u017cnica {d.difference}%)"
                )
        else:
            st.info("Weryfikacja krzy\u017cowa nie by\u0142a mo\u017cliwa.")
        if cross.reading_notes:
            st.caption(f"Uwagi: {cross.reading_notes}")

    # -- Linguistic check --------------------------------------------------------------
    ling = report.linguistic_check_result
    if ling.performed and ling.report:
        lr = ling.report
        issue_count = len(lr.issues)
        QUALITY_LABELS = {
            "excellent": ("\U0001f7e2", "Doskonala"),
            "good": ("\U0001f535", "Dobra"),
            "needs_review": ("\U0001f7e1", "Do poprawy"),
            "poor": ("\U0001f534", "Slaba"),
        }
        q_icon, q_label = QUALITY_LABELS.get(
            lr.overall_quality, ("\u26aa", lr.overall_quality)
        )

        with st.expander(
            f"\U0001f4dd Weryfikacja j\u0119zykowa "
            f"({issue_count} {'problem' if issue_count == 1 else 'problem\u00f3w'})",
            expanded=issue_count > 0,
        ):
            mc1, mc2 = st.columns(2)
            mc1.metric(
                "J\u0119zyk", f"{lr.detected_language_name} ({lr.detected_language})"
            )
            mc2.metric("Jako\u015b\u0107 tekstu", f"{q_icon} {q_label}")

            if lr.summary:
                st.caption(lr.summary)

            if lr.issues:
                ISSUE_ICONS = {
                    "spelling": "\U0001f4dd",
                    "grammar": "\U0001f4d6",
                    "punctuation": "\u270f\ufe0f",
                    "diacritics": "\U0001f524",
                    "terminology": "\U0001f500",
                }
                ISSUE_LABELS_PL = {
                    "spelling": "Ortografia",
                    "grammar": "Gramatyka",
                    "punctuation": "Interpunkcja",
                    "diacritics": "Diakrytyki",
                    "terminology": "Terminologia",
                }
                for li in lr.issues:
                    icon = ISSUE_ICONS.get(li.issue_type, "\u2022")
                    type_label = ISSUE_LABELS_PL.get(
                        li.issue_type, li.issue_type
                    )
                    from html import escape as _esc

                    st.markdown(
                        f"{icon} **[{type_label}]** "
                        f'<s>{_esc(li.original)}</s> \u2192 '
                        f"<strong>{_esc(li.suggestion)}</strong>  \n"
                        f'<span style="opacity:0.6;font-size:0.85rem;">'
                        f"{_esc(li.explanation)}</span>",
                        unsafe_allow_html=True,
                    )
            else:
                st.success(
                    "Tekst na etykiecie bez b\u0142\u0119d\u00f3w "
                    "\u2014 profesjonalna jako\u015b\u0107."
                )
    elif ling.error:
        with st.expander("\U0001f4dd Weryfikacja j\u0119zykowa"):
            st.info(
                "Weryfikacja j\u0119zykowa nie by\u0142a mo\u017cliwa."
            )

    # -- Hard rules --------------------------------------------------------------------
    if report.hard_rule_flags:
        with st.expander(
            f"\U0001f512 Regu\u0142y deterministyczne FEDIAF "
            f"({len(report.hard_rule_flags)} problem\u00f3w)"
        ):
            st.caption(
                "Poni\u017csze problemy zosta\u0142y wykryte przez regu\u0142y "
                "zakodowane bezpo\u015brednio w Pythonie \u2014 "
                "niezale\u017cnie od odpowiedzi modelu AI."
            )
            for flag in report.hard_rule_flags:
                st.error(
                    f"**[{flag.code}]** {flag.description}  \n"
                    f"Odniesienie: {flag.fediaf_reference or '\u2014'}"
                )

    # -- Product data ------------------------------------------------------------------
    with st.expander("Dane produktu i warto\u015bci od\u017cywcze", expanded=False):
        p = report.product
        c1, c2, c3 = st.columns(3)
        c1.write(f"**Gatunek:** {p.species.value}")
        c2.write(f"**Etap \u017cycia:** {p.lifestage.value}")
        c3.write(f"**Typ karmy:** {p.food_type.value}")
        if p.name:
            st.write(f"**Nazwa:** {p.name}")
        if p.brand:
            st.write(f"**Marka:** {p.brand}")

        nutrients = report.extracted_nutrients
        uncertain_strs = set(report.values_requiring_manual_check)

        NUTRIENT_LABELS = {
            "crude_protein": "Bia\u0142ko surowe",
            "crude_fat": "T\u0142uszcz surowy",
            "crude_fibre": "W\u0142\u00f3kno surowe",
            "moisture": "Wilgotno\u015b\u0107",
            "crude_ash": "Popi\u00f3\u0142 surowy",
            "calcium": "Wap\u0144",
            "phosphorus": "Fosfor",
        }

        items = []
        for key, label in NUTRIENT_LABELS.items():
            val = getattr(nutrients, key)
            if val is not None:
                is_uncertain = any(key in s for s in uncertain_strs)
                items.append((label, val, is_uncertain))

        if items:
            st.markdown("**Wyekstrahowane warto\u015bci od\u017cywcze:**")
            n_cols = st.columns(4)
            for idx, (label, val, uncertain_flag) in enumerate(items):
                suffix = " \u26a0\ufe0f" if uncertain_flag else ""
                n_cols[idx % 4].metric(label + suffix, f"{val}%")

    # -- Regulatory issues -------------------------------------------------------------
    st.subheader(f"Kwestie regulacyjne ({len(issues)})")
    if not issues:
        st.success("Nie wykryto problem\u00f3w regulacyjnych.")
    else:
        SEV_ICONS = {
            "CRITICAL": "\U0001f534",
            "WARNING": "\U0001f7e1",
            "INFO": "\U0001f535",
        }
        SEV_LABELS = {
            "CRITICAL": "Krytyczne",
            "WARNING": "Ostrze\u017cenie",
            "INFO": "Informacja",
        }
        for issue in issues:
            sev = issue.severity.value
            src = " [REGU\u0141A]" if issue.source == "HARD_RULE" else ""
            label = SEV_LABELS.get(sev, sev)
            with st.expander(
                f"{SEV_ICONS.get(sev, '\u26aa')} [{label}{src}] "
                f"{issue.description}"
            ):
                cols = st.columns(2)
                if issue.fediaf_reference:
                    cols[0].write(
                        f"**Odniesienie FEDIAF:** {issue.fediaf_reference}"
                    )
                if issue.found_value is not None:
                    cols[0].write(f"**Znaleziono:** {issue.found_value}")
                if issue.required_value:
                    cols[1].write(f"**Wymagane:** {issue.required_value}")
                if issue.code:
                    cols[1].write(f"**Kod:** `{issue.code}`")

    # -- EU labelling ------------------------------------------------------------------
    eu_check = report.eu_labelling_check
    st.subheader("Wymagania etykietowania EU (Rozp. 767/2009)")
    EU_LABELS = {
        "ingredients_listed": "Lista sk\u0142adnik\u00f3w",
        "analytical_constituents_present": "Sk\u0142adniki analityczne",
        "manufacturer_info": "Dane producenta",
        "net_weight_declared": "Masa netto",
        "species_clearly_stated": "Gatunek zwierz\u0119cia",
        "batch_or_date_present": "Numer partii / data",
    }
    eu_html = '<div class="eu-grid">'
    for key, label in EU_LABELS.items():
        val = getattr(eu_check, key)
        icon = "\u2705" if val else "\u274c"
        eu_html += f'<div class="eu-item">{icon} {label}</div>'
    eu_html += "</div>"
    st.markdown(eu_html, unsafe_allow_html=True)

    # -- Packaging check --------------------------------------------------------------
    pkg = report.packaging_check
    st.subheader("Kontrola opakowania")

    CLASSIFICATION_LABELS = {
        "complete": "Karma pe\u0142noporcjowa",
        "complementary": "Karma uzupe\u0142niaj\u0105ca",
        "treat": "Przysmak",
        "not_stated": "Nie okre\u015blono",
    }

    pkg_items_1 = {
        "Instrukcja dawkowania": pkg.feeding_guidelines_present,
        "Przechowywanie": pkg.storage_instructions_present,
        "Symbol \u2117 przy masie": pkg.net_weight_e_symbol,
        "Kraj pochodzenia": pkg.country_of_origin_stated,
        "Oznaczenia recyklingu": pkg.recycling_symbols_present,
        "Kod EAN widoczny": pkg.barcode_visible,
    }
    pkg_items_2 = {
        "Kod QR widoczny": pkg.qr_code_visible,
        "Emblemat gatunku": pkg.species_emblem_present,
        "Miejsce na dat\u0119/parti\u0119": pkg.date_marking_area_present,
        "T\u0142umaczenia kompletne": pkg.translations_complete,
        "Kody kraj\u00f3w": pkg.country_codes_for_languages,
        "O\u015bwiadczenie FEDIAF": pkg.compliance_statement_present,
        "Kontakt do info (Art.19)": pkg.free_contact_for_info,
        "Nr zatwierdzenia zak\u0142adu": pkg.establishment_approval_number,
        "Czytelno\u015b\u0107 fontu": pkg.font_legibility_ok,
        "Polski kompletny": pkg.polish_language_complete,
    }

    pkg_html = '<div class="eu-grid">'
    for label, val in {**pkg_items_1, **pkg_items_2}.items():
        icon = "\u2705" if val else "\u274c"
        pkg_html += f'<div class="eu-item">{icon} {label}</div>'
    pkg_html += "</div>"
    st.markdown(pkg_html, unsafe_allow_html=True)

    # Classification
    cls_label = CLASSIFICATION_LABELS.get(
        pkg.product_classification.value,
        pkg.product_classification.value,
    )
    st.markdown(
        f"**Klasyfikacja produktu:** {cls_label}"
    )

    # Claims consistency — the most important part
    if not pkg.claims_consistent_with_composition or pkg.claims_inconsistencies:
        st.markdown("**Sp\u00f3jno\u015b\u0107 claim\u00f3w ze sk\u0142adem:**")
        if pkg.claims_inconsistencies:
            for inc in pkg.claims_inconsistencies:
                st.error(f"\u274c {inc}")
        if not pkg.no_therapeutic_claims:
            st.error(
                "\u274c Wykryto claimy o charakterze leczniczym "
                "(naruszenie EU 767/2009 Art.13)"
            )
    if not pkg.naming_percentage_rule_ok and pkg.naming_percentage_notes:
        st.warning(
            f"\u26a0\ufe0f Regu\u0142a % w nazwie: {pkg.naming_percentage_notes}"
        )
    # Regulatory alerts
    if not pkg.free_contact_for_info:
        st.warning(
            "\u26a0\ufe0f Brak bezp\u0142atnego kontaktu do info o dodatkach "
            "i sk\u0142adnikach (wymaganie Art.19 Reg 767/2009)"
        )
    if not pkg.establishment_approval_number:
        st.warning(
            "\u26a0\ufe0f Brak numeru zatwierdzenia/rejestracji zak\u0142adu "
            "(wymaganie Reg 767/2009 + Reg 183/2005)"
        )
    if pkg.is_raw_product and not pkg.raw_warning_present:
        st.error(
            "\u274c Surowa karma wymaga ostrze\u017ce\u0144: "
            '"PET FOOD ONLY" + "NOT FOR HUMAN CONSUMPTION" '
            "(Reg 142/2011)"
        )
    if pkg.gmo_declaration_required and not pkg.gmo_declaration_present:
        st.error(
            "\u274c Sk\u0142adnik GMO >0.9% — brak obowi\u0105zkowej deklaracji "
            "(Reg 1829/2003)"
        )
    if pkg.gmo_notes:
        st.info(f"GMO: {pkg.gmo_notes}")
    if pkg.contains_insect_protein and not pkg.insect_allergen_warning:
        st.warning(
            "\u26a0\ufe0f Bia\u0142ko owad\u00f3w — brak ostrze\u017cenia "
            "o alergii krzy\u017cowej (EFSA guidance)"
        )
    if pkg.moisture_declaration_required and not pkg.moisture_declaration_present:
        st.warning(
            "\u26a0\ufe0f Wilgotno\u015b\u0107 >14% — deklaracja obowi\u0105zkowa "
            "(767/2009 Annex V)"
        )
    if not pkg.font_legibility_ok and pkg.font_legibility_notes:
        st.warning(
            f"\u26a0\ufe0f Czytelno\u015b\u0107: {pkg.font_legibility_notes}"
        )
    if pkg.packaging_notes:
        with st.expander("Dodatkowe uwagi"):
            for note in pkg.packaging_notes:
                st.write(f"\u2022 {note}")

    # -- Recommendations ---------------------------------------------------------------
    recs = report.recommendations
    if recs:
        st.subheader("Rekomendacje")
        for rec in recs:
            st.write(f"\u2192 {rec}")

    # -- Market trends -----------------------------------------------------------------
    trends = report.market_trends
    if trends and market:
        st.divider()
        st.subheader(f"\U0001f4ca Trendy rynkowe \u2014 {market}")
        POSITIONING_LABELS = {
            "trendy": ("\U0001f7e2", "Zgodny z trendami"),
            "standard": ("\U0001f535", "Standardowy sk\u0142ad"),
            "outdated": ("\U0001f534", "Przestarza\u0142y sk\u0142ad"),
            "niche": ("\U0001f7e1", "Niszowy / rosn\u0105cy"),
        }
        pos = trends.positioning.value
        pos_icon, pos_label = POSITIONING_LABELS.get(pos, ("\u26aa", pos))
        st.metric(
            "Pozycjonowanie sk\u0142adu", f"{pos_icon} {pos_label}"
        )
        st.info(trends.summary)
        if trends.trend_notes:
            with st.expander("Szczeg\u00f3\u0142owe obserwacje"):
                for note in trends.trend_notes:
                    st.write(f"\u2022 {note}")

    # -- Disclaimer footer -------------------------------------------------------------
    st.markdown(
        '<div class="footer-text">'
        "Raport wygenerowany automatycznie. Wyniki poni\u017cej 85 pkt "
        "lub oznaczone jako DO SPRAWDZENIA powinny zosta\u0107 "
        "zweryfikowane przez specjalist\u0119 przed podj\u0119ciem decyzji.<br>"
        "BULT \u00b7 Global Pet\u2019s Food \u00b7 Ko\u017amin Wlkp."
        "</div>",
        unsafe_allow_html=True,
    )

    # -- Export buttons ----------------------------------------------------------------
    stem = Path(filename).stem
    col_a, col_b = st.columns(2)
    with col_a:
        st.download_button(
            "\u2b07 Pobierz raport JSON",
            data=to_json(report),
            file_name=f"raport_{stem}.json",
            mime="application/json",
            width="stretch",
        )
    with col_b:
        st.download_button(
            "\u2b07 Pobierz raport TXT",
            data=to_text(report, filename, market),
            file_name=f"raport_{stem}.txt",
            mime="text/plain",
            width="stretch",
        )


# -- Render linguistic-only report ----------------------------------------------------
def render_linguistic_report(
    result: LinguisticCheckResult, filename: str,
) -> None:
    """Render standalone linguistic check results."""
    st.divider()

    if not result.performed or not result.report:
        st.error(
            f"**Weryfikacja j\u0119zykowa nie powiod\u0142a si\u0119.**\n\n"
            f"{result.error or 'Nieznany b\u0142\u0105d.'}"
        )
        return

    lr = result.report
    issue_count = len(lr.issues)

    # Quality banner
    _QUALITY_MAP = {
        "excellent": (
            "success", "\u2705 Tekst bez b\u0142\u0119d\u00f3w "
            "\u2014 profesjonalna jako\u015b\u0107."
        ),
        "good": (
            "success", "\u2705 Tekst dobrej jako\u015bci "
            "\u2014 drobne uwagi poni\u017cej."
        ),
        "needs_review": (
            "warning", "\u26a0\ufe0f Tekst wymaga korekty "
            "\u2014 przejrzyj uwagi poni\u017cej."
        ),
        "poor": (
            "error", "\u26d4 Tekst wymaga gruntownej korekty "
            "\u2014 liczne b\u0142\u0119dy."
        ),
    }
    banner_type, banner_msg = _QUALITY_MAP.get(
        lr.overall_quality, ("info", lr.overall_quality)
    )
    getattr(st, banner_type)(banner_msg)

    # Metrics
    _QUALITY_LABELS = {
        "excellent": "\u2705 Doskona\u0142a",
        "good": "\U0001f535 Dobra",
        "needs_review": "\U0001f7e1 Do poprawy",
        "poor": "\U0001f534 S\u0142aba",
    }
    quality_label = _QUALITY_LABELS.get(
        lr.overall_quality, lr.overall_quality
    )

    mc1, mc2, mc3 = st.columns([2, 2, 1])
    mc1.metric("J\u0119zyk", lr.detected_language_name)
    mc2.metric("Jako\u015b\u0107", quality_label)
    mc3.metric("Problemy", str(issue_count))

    if lr.summary:
        st.caption(lr.summary)

    # Issues
    if lr.issues:
        _ISSUE_ICONS = {
            "spelling": "\U0001f4dd",
            "grammar": "\U0001f4d6",
            "punctuation": "\u270f\ufe0f",
            "diacritics": "\U0001f524",
            "terminology": "\U0001f500",
        }
        _ISSUE_LABELS = {
            "spelling": "Ortografia",
            "grammar": "Gramatyka",
            "punctuation": "Interpunkcja",
            "diacritics": "Diakrytyki",
            "terminology": "Terminologia",
        }
        st.subheader("Znalezione problemy")
        from html import escape as _esc

        _CONF_BADGES = {
            "high": (
                '<span style="background:#22c55e;color:#fff;padding:1px 6px;'
                'border-radius:4px;font-size:0.7rem;margin-left:6px;">'
                "potwierdzone</span>"
            ),
            "medium": (
                '<span style="background:#eab308;color:#fff;padding:1px 6px;'
                'border-radius:4px;font-size:0.7rem;margin-left:6px;">'
                "do weryfikacji</span>"
            ),
            "low": (
                '<span style="background:#ef4444;color:#fff;padding:1px 6px;'
                'border-radius:4px;font-size:0.7rem;margin-left:6px;">'
                "mo\u017cliwa halucynacja</span>"
            ),
        }
        for li in lr.issues:
            icon = _ISSUE_ICONS.get(li.issue_type, "\u2022")
            label = _ISSUE_LABELS.get(li.issue_type, li.issue_type)
            conf = getattr(li, "confidence", "medium")
            conf_badge = _CONF_BADGES.get(conf, "")
            st.markdown(
                f"{icon} **[{label}]** "
                f'<s>{_esc(li.original)}</s> \u2192 '
                f"<strong>{_esc(li.suggestion)}</strong>"
                f"{conf_badge}  \n"
                f'<span style="opacity:0.6;font-size:0.85rem;">'
                f"{_esc(li.explanation)}</span>",
                unsafe_allow_html=True,
            )
    else:
        st.success(
            "Tekst na etykiecie bez b\u0142\u0119d\u00f3w "
            "\u2014 profesjonalna jako\u015b\u0107."
        )

    # Export
    st.divider()
    txt = linguistic_to_text(result, filename)
    stem = Path(filename).stem
    st.download_button(
        "\u2b07\ufe0f Pobierz raport j\u0119zykowy (TXT)",
        data=txt,
        file_name=f"jezyk_{stem}.txt",
        mime="text/plain",
        width="stretch",
    )


# -- Render structure check report -----------------------------------------------------
def render_structure_report(
    result: LabelStructureCheckResult, filename: str,
) -> None:
    """Render label structure & font check results."""
    st.divider()

    if not result.performed or not result.report:
        st.error(
            f"**Kontrola struktury nie powiod\u0142a si\u0119.**\n\n"
            f"{result.error or 'Nieznany b\u0142\u0105d.'}"
        )
        return

    r = result.report

    # Status banner
    _STATUS_MAP = {
        "ok": ("success", "\u2705 Struktura etykiety poprawna \u2014 "
               "wszystkie sekcje j\u0119zykowe i czcionka w porz\u0105dku."),
        "warnings": ("warning", "\u26a0\ufe0f Wykryto potencjalne problemy \u2014 "
                     "przejrzyj uwagi poni\u017cej."),
        "errors": ("error", "\u26d4 Wykryto b\u0142\u0119dy w strukturze lub czcionce \u2014 "
                   "wymagana korekta przed drukiem."),
    }
    banner_type, banner_msg = _STATUS_MAP.get(
        r.overall_status, ("info", r.overall_status)
    )
    getattr(st, banner_type)(banner_msg)

    # Metrics
    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("Sekcje j\u0119zykowe", str(r.section_count))
    mc2.metric("Problemy strukturalne", str(len(r.structure_issues)))
    mc3.metric("Problemy z czcionk\u0105", str(r.font_issues_count))

    if r.summary:
        st.caption(r.summary)

    # -- Language sections overview --
    if r.language_sections:
        st.subheader("Sekcje j\u0119zykowe")
        for sec in r.language_sections:
            marker_icon = "\u2705" if sec.marker_present else "\u274c"
            content_icon = "\u2705" if sec.content_present else "\u274c"
            complete_icon = "\u2705" if sec.content_complete else "\u26a0\ufe0f"

            with st.expander(
                f"{marker_icon} [{sec.language_code.upper()}] "
                f"{sec.language_name}",
                expanded=not sec.content_complete or not sec.marker_present,
            ):
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"**Marker:** {marker_icon} "
                           f"{sec.marker_type}: \"{sec.marker_text}\""
                           if sec.marker_present
                           else f"**Marker:** {marker_icon} BRAK")
                c2.markdown(f"**Tre\u015b\u0107:** {content_icon}")
                c3.markdown(f"**Kompletna:** {complete_icon}")

                if sec.section_elements:
                    st.markdown(
                        "**Obecne elementy:** "
                        + ", ".join(sec.section_elements)
                    )
                if sec.missing_elements:
                    st.warning(
                        "**Brakuj\u0105ce elementy:** "
                        + ", ".join(sec.missing_elements)
                    )
                if sec.notes:
                    st.caption(sec.notes)

    # -- Diacritics check per language --
    if r.diacritics_check:
        st.subheader("Kompletno\u015b\u0107 diakrytyk\u00f3w")
        _LANG_DIACRITICS = {
            "pl": "\u0105\u0119\u015b\u0107\u017a\u017c\u0142\u0144\u00f3",
            "de": "\u00e4\u00f6\u00fc\u00df",
            "cs": "\u0159\u0161\u010d\u017e\u016f\u011b",
            "hu": "\u00e1\u00e9\u00ed\u00f3\u00f6\u0151\u00fa\u00fc\u0171",
            "ro": "\u0103\u00e2\u00ee\u0219\u021b",
            "fr": "\u00e9\u00e8\u00ea\u00e7\u00e0\u00f4",
            "it": "\u00e0\u00e8\u00e9\u00ec\u00f2\u00f9",
            "es": "\u00f1\u00e1\u00e9\u00ed\u00f3\u00fa\u00fc",
        }
        cols = st.columns(min(len(r.diacritics_check), 4))
        for idx, (lang, ok) in enumerate(r.diacritics_check.items()):
            col = cols[idx % len(cols)]
            icon = "\u2705" if ok else "\u274c"
            chars = _LANG_DIACRITICS.get(lang, "")
            col.markdown(
                f"{icon} **{lang.upper()}**"
                + (f"  \n{chars}" if chars else "")
            )

    # -- Structure issues --
    if r.structure_issues:
        st.subheader(
            f"Problemy strukturalne ({len(r.structure_issues)})"
        )
        _SEV_ICONS = {
            "critical": "\U0001f534",
            "warning": "\U0001f7e1",
            "info": "\U0001f535",
        }
        _SEV_LABELS = {
            "critical": "Krytyczny",
            "warning": "Ostrze\u017cenie",
            "info": "Informacja",
        }
        _TYPE_LABELS = {
            "missing_marker": "Brak markera",
            "orphaned_text": "Osierocony tekst",
            "section_overlap": "Nak\u0142adanie si\u0119 sekcji",
            "section_gap": "Luka mi\u0119dzy sekcjami",
            "marker_damaged": "Uszkodzony marker",
            "inconsistent_order": "Niesp\u00f3jny porz\u0105dek",
            "missing_section": "Brak sekcji",
            "duplicate_marker": "Duplikat markera",
        }
        from html import escape as _esc

        for si in r.structure_issues:
            sev_icon = _SEV_ICONS.get(si.severity, "\u26aa")
            sev_label = _SEV_LABELS.get(si.severity, si.severity)
            type_label = _TYPE_LABELS.get(si.issue_type, si.issue_type)
            langs = ", ".join(
                c.upper() for c in si.affected_languages
            ) if si.affected_languages else "\u2014"

            st.markdown(
                f"{sev_icon} **[{sev_label}] {type_label}** \u2014 "
                f"{_esc(si.description)}  \n"
                f'<span style="opacity:0.6;font-size:0.85rem;">'
                f"J\u0119zyki: {_esc(langs)}"
                f"{f' | Lokalizacja: {_esc(si.location)}' if si.location else ''}"
                f"</span>",
                unsafe_allow_html=True,
            )

    # -- Glyph/font issues --
    if r.glyph_issues:
        st.subheader(
            f"Problemy z czcionk\u0105 / glifami ({len(r.glyph_issues)})"
        )
        _GLYPH_ICONS = {
            "missing_glyph": "\u274c",
            "substituted_glyph": "\U0001f500",
            "blank_space": "\u2b1c",
            "tofu_box": "\u25a1",
            "wrong_diacritic": "\U0001f524",
            "encoding_error": "\u26a0\ufe0f",
        }
        _GLYPH_LABELS = {
            "missing_glyph": "Brak glifa",
            "substituted_glyph": "Podmieniony glif",
            "blank_space": "Puste miejsce",
            "tofu_box": "Kwadracik (tofu)",
            "wrong_diacritic": "Z\u0142y diakrytyk",
            "encoding_error": "B\u0142\u0105d enkodowania",
        }
        for gi in r.glyph_issues:
            g_icon = _GLYPH_ICONS.get(gi.issue_type, "\u2022")
            g_label = _GLYPH_LABELS.get(gi.issue_type, gi.issue_type)
            chars_str = (
                " \u2014 brakuje: " + " ".join(gi.missing_characters)
                if gi.missing_characters else ""
            )
            from html import escape as _esc

            # Use HTML for affected/expected text to avoid markdown escaping
            st.markdown(
                f"{g_icon} **[{gi.language_code.upper()}] [{g_label}]** "
                f'<s>{_esc(gi.affected_text)}</s> \u2192 '
                f"<strong>{_esc(gi.expected_text)}</strong>"
                f"{chars_str}  \n"
                f'<span style="opacity:0.6;font-size:0.85rem;">'
                f"{_esc(gi.explanation)}"
                f"{f' | {_esc(gi.location)}' if gi.location else ''}"
                f"</span>",
                unsafe_allow_html=True,
            )

    if not r.structure_issues and not r.glyph_issues:
        st.success(
            "Nie wykryto problem\u00f3w strukturalnych ani z czcionk\u0105 "
            "\u2014 etykieta gotowa do druku."
        )

    # Export section
    st.divider()
    st.subheader("Pobierz wyniki")
    stem = Path(filename).stem

    # Row 1: TXT report + JSX script
    col_txt, col_jsx = st.columns(2)
    with col_txt:
        txt = structure_to_text(result, filename)
        st.download_button(
            "\u2b07\ufe0f Raport (TXT)",
            data=txt,
            file_name=f"struktura_{stem}.txt",
            mime="text/plain",
            width="stretch",
        )

    with col_jsx:
        from fediaf_verifier.jsx_generator import generate_jsx

        jsx_script = generate_jsx(result.report, filename)
        st.download_button(
            "\u2b07\ufe0f Skrypt Illustrator (.jsx)",
            data=jsx_script,
            file_name=f"qc_{stem}.jsx",
            mime="application/javascript",
            width="stretch",
            help=(
                "Otw\u00f3rz etykiet\u0119 w Illustratorze, "
                "potem File > Scripts > Other Script > wybierz ten plik. "
                "Doda warstw\u0119 'QC Annotations' z oznaczeniami."
            ),
        )

    # Row 2: Annotated PDF/image (if source file available)
    file_bytes = st.session_state.get("structure_file_bytes")
    media_type = st.session_state.get("structure_media_type", "")

    if file_bytes and result.report:
        from fediaf_verifier.annotator import annotate_file

        annotated_bytes, out_mime = annotate_file(
            file_bytes, media_type, result.report,
        )
        if annotated_bytes:
            ext = "pdf" if "pdf" in out_mime else "png"
            st.download_button(
                f"\u2b07\ufe0f Etykieta z oznaczeniami (.{ext})",
                data=annotated_bytes,
                file_name=f"annotated_{stem}.{ext}",
                mime=out_mime,
                width="stretch",
                help=(
                    "Kopia etykiety z naniesionymi prostok\u0105tami "
                    "oznaczaj\u0105cymi wykryte problemy."
                ),
            )
        elif media_type not in ("application/pdf", "image/jpeg", "image/png"):
            st.caption(
                "Adnotacje wizualne dost\u0119pne tylko dla PDF i obraz\u00f3w. "
                "Dla plik\u00f3w .ai u\u017cyj skryptu JSX powy\u017cej."
            )


# -- Render translation report ---------------------------------------------------------
def render_translation_report(result, filename: str) -> None:
    st.divider()

    if not result.performed or not result.report:
        st.error(
            f"**T\u0142umaczenie nie powiod\u0142o si\u0119.**\n\n"
            f"{result.error or 'Nieznany b\u0142\u0105d.'}"
        )
        return

    r = result.report
    st.success(
        f"\u2705 T\u0142umaczenie uko\u0144czone: "
        f"{r.source_language_name} \u2192 {r.target_language_name}"
    )

    mc1, mc2, mc3 = st.columns(3)
    mc1.metric(
        "J\u0119zyk \u017ar\u00f3d\u0142owy",
        f"{r.source_language_name} ({r.source_language})",
    )
    mc2.metric(
        "J\u0119zyk docelowy",
        f"{r.target_language_name} ({r.target_language})",
    )
    mc3.metric("Sekcje", str(len(r.sections)))

    if r.summary:
        st.caption(r.summary)

    # Sections side-by-side
    for sec in r.sections:
        with st.expander(
            f"\U0001f4c4 {sec.section_name}", expanded=True
        ):
            col_orig, col_trans = st.columns(2)
            with col_orig:
                st.markdown(f"**Orygina\u0142:**")
                st.text(sec.original_text)
            with col_trans:
                st.markdown(f"**T\u0142umaczenie:**")
                st.text(sec.translated_text)
            if sec.notes:
                st.caption(f"\U0001f4dd {sec.notes}")

    if r.overall_notes:
        st.info(f"**Uwagi:** {r.overall_notes}")

    # Export
    st.divider()
    stem = Path(filename).stem
    st.download_button(
        "\u2b07\ufe0f Pobierz t\u0142umaczenie (TXT)",
        data=translation_to_text(result, filename),
        file_name=f"tlumaczenie_{stem}.txt",
        mime="text/plain",
        width="stretch",
    )


# -- Render design analysis report -----------------------------------------------------
def render_design_report(result, filename: str) -> None:
    from html import escape as _esc

    st.divider()

    if not result.performed or not result.report:
        st.error(
            f"**Analiza graficzna nie powiod\u0142a si\u0119.**\n\n"
            f"{result.error or 'Nieznany b\u0142\u0105d.'}"
        )
        return

    r = result.report
    score = r.overall_score

    # Status banner
    if score >= 80:
        st.success(
            f"\u2705 **Ocena: {score}/100** \u2014 {r.overall_assessment}"
        )
    elif score >= 60:
        st.warning(
            f"\u26a0\ufe0f **Ocena: {score}/100** \u2014 {r.overall_assessment}"
        )
    else:
        st.error(
            f"\u26d4 **Ocena: {score}/100** \u2014 {r.overall_assessment}"
        )

    # Metrics
    best_cat = max(r.category_scores, key=lambda c: c.score) if r.category_scores else None
    worst_cat = min(r.category_scores, key=lambda c: c.score) if r.category_scores else None

    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("Ocena og\u00f3lna", f"{score}/100")
    mc2.metric("Problemy", str(len(r.issues)))
    if best_cat:
        mc3.metric("Najlepsza", f"{best_cat.category_name} ({best_cat.score})")
    if worst_cat:
        mc4.metric("Najs\u0142absza", f"{worst_cat.category_name} ({worst_cat.score})")

    # Score bar
    bar_color = "#00b464" if score >= 80 else ("#ffb400" if score >= 60 else "#dc3232")
    st.markdown(
        f'<div class="score-bar-bg">'
        f'<div class="score-bar-fill" style="width:{score}%;'
        f'background:{bar_color}"></div></div>',
        unsafe_allow_html=True,
    )

    # Strengths
    if r.strengths:
        with st.expander(
            f"\u2705 Mocne strony ({len(r.strengths)})", expanded=True
        ):
            for s in r.strengths:
                st.markdown(f"\u2022 {_esc(s)}", unsafe_allow_html=True)

    # Category scores
    if r.category_scores:
        st.subheader("Oceny per kategoria")
        for cat in r.category_scores:
            cat_color = (
                "\U0001f7e2" if cat.score >= 80
                else ("\U0001f7e1" if cat.score >= 60 else "\U0001f534")
            )
            with st.expander(
                f"{cat_color} {cat.category_name} \u2014 {cat.score}/100",
                expanded=cat.score < 60,
            ):
                if cat.findings:
                    st.markdown("**Obserwacje:**")
                    for f in cat.findings:
                        st.write(f"\u2022 {f}")
                if cat.recommendations:
                    st.markdown("**Rekomendacje:**")
                    for rec in cat.recommendations:
                        st.write(f"\u2192 {rec}")

    # Issues sorted by severity
    if r.issues:
        _SEV_ICONS = {
            "critical": "\U0001f534",
            "major": "\U0001f7e0",
            "minor": "\U0001f7e1",
            "suggestion": "\U0001f535",
        }
        _SEV_LABELS = {
            "critical": "Krytyczny",
            "major": "Istotny",
            "minor": "Drobny",
            "suggestion": "Sugestia",
        }
        _SEV_ORDER = {"critical": 0, "major": 1, "minor": 2, "suggestion": 3}
        sorted_issues = sorted(
            r.issues, key=lambda i: _SEV_ORDER.get(i.severity, 9)
        )
        st.subheader(f"Problemy ({len(r.issues)})")
        for issue in sorted_issues:
            icon = _SEV_ICONS.get(issue.severity, "\u26aa")
            label = _SEV_LABELS.get(issue.severity, issue.severity)
            st.markdown(
                f"{icon} **[{label}]** {_esc(issue.description)}  \n"
                f'<span style="opacity:0.6;font-size:0.85rem;">'
                f"\u2192 {_esc(issue.recommendation)}"
                f"{f' | {_esc(issue.location)}' if issue.location else ''}"
                f"</span>",
                unsafe_allow_html=True,
            )

    # Competitive benchmarks (AI-generated, qualitative)
    if r.competitive_benchmarks:
        with st.expander(
            f"\U0001f4ca Benchmark konkurencyjny ({len(r.competitive_benchmarks)})"
        ):
            for bm in r.competitive_benchmarks:
                st.markdown(f"**{bm.aspect}**")
                c1, c2 = st.columns(2)
                c1.write(f"Obecny: {bm.current_level}")
                c2.write(f"Standard: {bm.industry_standard}")
                st.write(f"\u2192 {bm.suggestion}")
                st.divider()

    # Quantitative benchmark comparisons (radar chart + table)
    if r.benchmark_comparisons:
        _VERDICT_LABELS = {
            "excellent": ("\U0001f7e2", "Doskonaly"),
            "above_average": ("\U0001f7e2", "Powyzej sredniej"),
            "average": ("\U0001f7e1", "Sredni"),
            "below_average": ("\U0001f534", "Ponizej sredniej"),
        }
        segment_label = r.benchmark_comparisons[0].segment if r.benchmark_comparisons else ""

        with st.expander(
            f"\U0001f4ca Benchmark vs segment: {segment_label}", expanded=True
        ):
            # Radar chart using plotly (needs >= 3 categories for a polygon)
            try:
                import plotly.graph_objects as go

                if len(r.benchmark_comparisons) < 3:
                    raise ValueError("Za malo kategorii dla wykresu radarowego")

                categories = [bc.category_name for bc in r.benchmark_comparisons]
                scores = [bc.score for bc in r.benchmark_comparisons]
                medians = [bc.benchmark_median for bc in r.benchmark_comparisons]
                highs = [bc.benchmark_high for bc in r.benchmark_comparisons]

                # Close the radar polygon
                categories_closed = categories + [categories[0]]
                scores_closed = scores + [scores[0]]
                medians_closed = medians + [medians[0]]
                highs_closed = highs + [highs[0]]

                fig = go.Figure()
                fig.add_trace(go.Scatterpolar(
                    r=highs_closed, theta=categories_closed,
                    fill="toself", name="Top 25% branzy",
                    opacity=0.15, line=dict(color="#00b464", dash="dot"),
                ))
                fig.add_trace(go.Scatterpolar(
                    r=medians_closed, theta=categories_closed,
                    fill="toself", name="Mediana branzy",
                    opacity=0.2, line=dict(color="#ffb400"),
                ))
                fig.add_trace(go.Scatterpolar(
                    r=scores_closed, theta=categories_closed,
                    fill="toself", name="Twoja etykieta",
                    opacity=0.4, line=dict(color="#3b82f6", width=2),
                ))
                fig.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                    showlegend=True,
                    height=420,
                    margin=dict(l=60, r=60, t=30, b=30),
                )
                st.plotly_chart(fig, use_container_width=True)
            except ImportError:
                st.caption("Zainstaluj plotly dla wykresu radarowego: pip install plotly")
            except ValueError:
                pass  # < 3 categories, skip chart, table below is enough

            # Table
            for bc in r.benchmark_comparisons:
                icon, label = _VERDICT_LABELS.get(bc.verdict, ("\u26aa", _esc(bc.verdict)))
                st.markdown(
                    f"{icon} **{_esc(bc.category_name)}**: {bc.score}/100 "
                    f"(percentyl: {bc.percentile}) — {label}  \n"
                    f'<span style="opacity:0.6;font-size:0.85rem;">'
                    f"Segment {_esc(bc.segment)}: "
                    f"p25={bc.benchmark_low} | mediana={bc.benchmark_median} "
                    f"| p75={bc.benchmark_high}</span>",
                    unsafe_allow_html=True,
                )

    # Trend alignment
    if r.trend_alignment:
        with st.expander(
            f"\U0001f4c8 Trendy bran\u017cowe ({len(r.trend_alignment)})"
        ):
            for t in r.trend_alignment:
                st.write(f"\u2022 {t}")

    # Executive summary for R&D
    if r.actionable_summary:
        st.subheader("\U0001f3af Podsumowanie dla R&D")
        st.info(r.actionable_summary)

    # Export
    st.divider()
    stem = Path(filename).stem
    col_a, col_b = st.columns(2)
    with col_a:
        st.download_button(
            "\u2b07\ufe0f Raport (TXT)",
            data=design_to_text(result, filename),
            file_name=f"design_{stem}.txt",
            mime="text/plain",
            width="stretch",
        )
    with col_b:
        st.download_button(
            "\u2b07\ufe0f Raport (JSON)",
            data=result.report.model_dump_json(indent=2, exclude_none=True),
            file_name=f"design_{stem}.json",
            mime="application/json",
            width="stretch",
        )


# -- Render EAN/barcode report ---------------------------------------------------------
def render_ean_report(result, filename: str) -> None:
    st.divider()

    if not result.performed or not result.report:
        st.error(
            f"**Walidacja kod\u00f3w nie powiod\u0142a si\u0119.**\n\n"
            f"{result.error or 'Nieznany b\u0142\u0105d.'}"
        )
        return

    r = result.report

    # Banner
    if r.all_valid:
        st.success(
            f"\u2705 Wszystkie kody poprawne ({r.barcodes_found} "
            f"kod\u00f3w kreskowych)"
        )
    elif r.barcodes_found == 0:
        st.info("Nie wykryto kod\u00f3w kreskowych na etykiecie.")
    else:
        invalid = sum(1 for e in r.ean_results if not e.check_digit_valid)
        st.error(
            f"\u274c {invalid} z {r.barcodes_found} kod\u00f3w ma "
            f"b\u0142\u0119dn\u0105 cyfr\u0119 kontroln\u0105"
        )

    # Metrics
    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("Kody kreskowe", str(r.barcodes_found))
    mc2.metric("Kody QR", str(len(r.qr_codes)))
    valid_count = sum(1 for e in r.ean_results if e.check_digit_valid)
    mc3.metric("Poprawne", f"{valid_count}/{r.barcodes_found}")

    if r.summary:
        st.caption(r.summary)

    # Barcode details
    if r.ean_results:
        st.subheader("Kody kreskowe")
        for ean in r.ean_results:
            icon = "\u2705" if ean.check_digit_valid else "\u274c"
            with st.expander(
                f"{icon} {ean.barcode_type}: {ean.barcode_number}",
                expanded=not ean.check_digit_valid,
            ):
                c1, c2, c3 = st.columns(3)
                c1.metric("Typ", ean.barcode_type)
                c2.metric(
                    "Cyfra kontrolna",
                    "\u2705 OK" if ean.check_digit_valid else "\u274c B\u0142\u0119dna",
                )
                if ean.country_name:
                    c3.metric("Kraj", f"{ean.country_name} ({ean.country_prefix})")

                if not ean.check_digit_valid and ean.expected_check_digit:
                    st.warning(
                        f"Oczekiwana cyfra kontrolna: **{ean.expected_check_digit}** "
                        f"(ostatnia cyfra kodu powinna by\u0107 "
                        f"{ean.expected_check_digit}, jest {ean.barcode_number[-1] if ean.barcode_number else '?'})"
                    )
                if ean.notes:
                    st.caption(ean.notes)

    # QR codes
    if r.qr_codes:
        st.subheader("Kody QR")
        for qr in r.qr_codes:
            icon = "\u2705" if qr.readable else "\u26a0\ufe0f"
            st.markdown(
                f"{icon} **{'Czytelny' if qr.readable else 'Nieczytelny'}**"
            )
            if qr.content:
                st.code(qr.content)
            if qr.notes:
                st.caption(qr.notes)

    # Export
    st.divider()
    stem = Path(filename).stem
    st.download_button(
        "\u2b07\ufe0f Raport (TXT)",
        data=ean_to_text(result, filename),
        file_name=f"ean_{stem}.txt",
        mime="text/plain",
        width="stretch",
    )


# -- Render claims check report -------------------------------------------------------
def render_claims_report(result, filename: str) -> None:
    """Render claims vs composition check results."""
    st.divider()

    if not result.performed or not result.report:
        st.error(
            f"**Walidacja claim\u00f3w nie powiod\u0142a si\u0119.**\n\n"
            f"{result.error or 'Nieznany b\u0142\u0105d.'}"
        )
        return

    r = result.report

    # Banner
    _CONSISTENCY_MAP = {
        "consistent": (
            "success",
            "\u2705 Wszystkie claimy sp\u00f3jne ze sk\u0142adem.",
        ),
        "inconsistencies_found": (
            "warning",
            "\u26a0\ufe0f Wykryto niesp\u00f3jno\u015bci mi\u0119dzy claimami a sk\u0142adem.",
        ),
        "critical_issues": (
            "error",
            "\u26d4 Krytyczne problemy z claimami \u2014 wymagana korekta.",
        ),
    }
    banner_type, banner_msg = _CONSISTENCY_MAP.get(
        r.overall_consistency, ("info", r.overall_consistency)
    )
    getattr(st, banner_type)(banner_msg)

    # Metrics
    inconsistent_count = sum(
        1 for cv in r.claim_validations if not cv.is_consistent
    )
    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("Claimy znalezione", str(len(r.claims_found)))
    mc2.metric("Wynik", f"{r.score}/100")
    mc3.metric("Niesp\u00f3jno\u015bci", str(inconsistent_count))

    # Score bar
    bar_color = (
        "#00b464" if r.score >= 90
        else ("#ffb400" if r.score >= 70 else "#dc3232")
    )
    st.markdown(
        f'<div class="score-bar-bg">'
        f'<div class="score-bar-fill" style="width:{r.score}%;'
        f'background:{bar_color}"></div></div>',
        unsafe_allow_html=True,
    )

    if r.summary:
        st.caption(r.summary)

    # Per-claim validations
    if r.claim_validations:
        st.subheader("Walidacja claim\u00f3w")
        _SEV_ICONS = {
            "critical": "\U0001f534",
            "warning": "\U0001f7e1",
            "info": "\U0001f535",
        }
        for cv in r.claim_validations:
            icon = "\u2705" if cv.is_consistent else _SEV_ICONS.get(cv.severity, "\u274c")
            with st.expander(
                f"{icon} {_esc(cv.claim_text)}",
                expanded=not cv.is_consistent,
            ):
                c1, c2 = st.columns(2)
                c1.write(f"**Kategoria:** {_esc(cv.claim_category)}")
                c2.write(
                    f"**Status:** "
                    f"{'Sp\u00f3jny' if cv.is_consistent else 'Niesp\u00f3jny'}"
                )
                if cv.relevant_ingredients:
                    st.write(
                        f"**Powi\u0105zane sk\u0142adniki:** "
                        f"{', '.join(_esc(i) for i in cv.relevant_ingredients)}"
                    )
                if cv.inconsistency_description:
                    st.warning(f"\u26a0\ufe0f {_esc(cv.inconsistency_description)}")
                if cv.recommendation:
                    st.info(f"\u2192 {_esc(cv.recommendation)}")

    # Naming rule check
    if r.naming_rule_check:
        nr = r.naming_rule_check
        st.subheader("Regu\u0142a % w nazwie (EU 767/2009)")
        nr_icon = "\u2705" if nr.compliant else "\u274c"
        st.markdown(
            f"{nr_icon} **{_esc(nr.product_name)}**  \n"
            f'S\u0142owo kluczowe: "{_esc(nr.trigger_word)}" '
            f"\u2192 minimum {nr.required_minimum_percent}% "
            f"sk\u0142adnika \"{_esc(nr.ingredient_name)}\"  \n"
            f"Znaleziono: "
            f"{nr.actual_percent if nr.actual_percent is not None else 'brak danych'}%",
            unsafe_allow_html=True,
        )
        if nr.notes:
            st.caption(nr.notes)

    # Grain-free check
    if r.grain_free_check_passed is not None:
        st.subheader("Grain-free")
        if r.grain_free_check_passed:
            st.success("\u2705 Claim \"grain-free\" sp\u00f3jny \u2014 brak zb\u00f3\u017c w sk\u0142adzie.")
        else:
            st.error(
                f"\u274c Claim \"grain-free\" niesp\u00f3jny! "
                f"Znalezione zbo\u017ca: {', '.join(_esc(g) for g in r.grain_ingredients_found)}"
            )

    # Therapeutic claims warning
    if r.therapeutic_claims_found:
        st.subheader("\u26a0\ufe0f Claimy lecznicze")
        st.error(
            "Wykryto claimy o charakterze leczniczym "
            "(naruszenie EU 767/2009 Art.13):"
        )
        for tc in r.therapeutic_claims_found:
            st.write(f"\u274c {_esc(tc)}")

    # Export
    st.divider()
    stem = Path(filename).stem
    st.download_button(
        "\u2b07\ufe0f Raport claim\u00f3w (TXT)",
        data=claims_to_text(result, filename),
        file_name=f"claimy_{stem}.txt",
        mime="text/plain",
        width="stretch",
    )


# -- Render presentation compliance report ----------------------------------------


def render_presentation_report(result, filename: str) -> None:
    """Render commercial presentation compliance check results."""
    st.divider()

    if not result.performed or not result.report:
        st.error(
            f"**Walidacja prezentacji handlowej nie powiodła się.**\n\n"
            f"{result.error or 'Nieznany błąd.'}"
        )
        return

    r = result.report

    # Banner
    _COMPLIANCE_MAP = {
        "compliant": (
            "success",
            "\u2705 Prezentacja handlowa zgodna z regulacjami.",
        ),
        "issues_found": (
            "warning",
            "\u26a0\ufe0f Wykryto niezgodności w prezentacji handlowej.",
        ),
        "critical_issues": (
            "error",
            "\u26d4 Krytyczne problemy z prezentacją — wymagana korekta.",
        ),
    }
    banner_type, banner_msg = _COMPLIANCE_MAP.get(
        r.overall_compliance, ("info", r.overall_compliance)
    )
    getattr(st, banner_type)(banner_msg)

    # Metrics — 4 section scores
    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("Receptury", f"{r.recipe_section_score}/100")
    mc2.metric("Nazwy", f"{r.naming_section_score}/100")
    mc3.metric("Marka", f"{r.brand_section_score}/100")
    mc4.metric("Zastrzeżenia", f"{r.trademark_section_score}/100")

    # Overall score bar
    bar_color = (
        "#00b464" if r.score >= 90
        else ("#ffb400" if r.score >= 70 else "#dc3232")
    )
    st.markdown(
        f'<div class="score-bar-bg">'
        f'<div class="score-bar-fill" style="width:{r.score}%;'
        f'background:{bar_color}"></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown(f"**Wynik ogólny: {r.score}/100**")

    if r.summary:
        st.caption(r.summary)

    # Product context expander
    with st.expander("Kontekst produktu", expanded=False):
        ctx_c1, ctx_c2 = st.columns(2)
        ctx_c1.write(f"**Nazwa produktu:** {_esc(r.product_name or 'brak danych')}")
        ctx_c1.write(f"**Marka:** {_esc(r.brand_name or 'brak danych')}")
        ctx_c1.write(
            f"**Klasyfikacja:** {_esc(r.product_classification or 'brak danych')}"
        )
        ctx_c2.write(f"**Typ karmy:** {_esc(r.food_type or 'brak danych')}")
        ctx_c2.write(f"**Gatunek:** {_esc(r.species or 'brak danych')}")
        ctx_c2.write(f"**Etap życia:** {_esc(r.lifestage or 'brak danych')}")
        if r.ingredients_with_percentages:
            st.write("**Składniki z %:**")
            for ing in r.ingredients_with_percentages:
                st.write(f"- {_esc(ing)}")
        if r.additives_list:
            st.write("**Dodatki:**")
            for add in r.additives_list:
                st.write(f"- {_esc(add)}")

    _SEV_ICONS = {
        "critical": "\U0001f534",
        "warning": "\U0001f7e1",
        "info": "\U0001f535",
    }

    # Tabs for 4 sections
    tab_rec, tab_name, tab_brand, tab_tm = st.tabs([
        f"Receptury ({r.recipe_section_score})",
        f"Nazwy ({r.naming_section_score})",
        f"Marka ({r.brand_section_score})",
        f"Zastrzeżenia ({r.trademark_section_score})",
    ])

    # -- Tab 1: Recipes --------------------------------------------------------
    with tab_rec:
        if r.recipe_claims_found:
            st.write(
                f"**Znalezione claimy recepturowe:** "
                f"{len(r.recipe_claims_found)}"
            )
            for claim in r.recipe_claims_found:
                st.write(f"- {_esc(claim)}")

        if r.recipe_claim_checks:
            for rc in r.recipe_claim_checks:
                icon = (
                    "\u2705" if rc.compliant
                    else _SEV_ICONS.get(rc.severity, "\u274c")
                )
                with st.expander(
                    f"{icon} {_esc(rc.claim_text)}",
                    expanded=not rc.compliant,
                ):
                    c1, c2 = st.columns(2)
                    c1.write(f"**Typ:** {_esc(rc.claim_type)}")
                    c2.write(
                        f"**Status:** "
                        f"{'Zgodny' if rc.compliant else 'Niezgodny'}"
                    )
                    if rc.regulation_reference:
                        st.write(
                            f"**Podstawa prawna:** "
                            f"{_esc(rc.regulation_reference)}"
                        )
                    if rc.finding:
                        st.write(f"**Ustalenie:** {_esc(rc.finding)}")
                    if not rc.compliant and rc.issue_description:
                        st.warning(f"\u26a0\ufe0f {_esc(rc.issue_description)}")
                    if rc.recommendation:
                        st.info(f"\u2192 {_esc(rc.recommendation)}")
        elif not r.recipe_claims_found:
            st.info("Brak claimów recepturowych na etykiecie.")

    # -- Tab 2: Names ----------------------------------------------------------
    with tab_name:
        # A) Naming convention (% rules)
        if r.naming_convention_checks:
            st.markdown("##### Reguły procentowe (EU 767/2009 Art.17)")
            for nc in r.naming_convention_checks:
                icon = "\u2705" if nc.compliant else "\u274c"
                with st.expander(
                    f"{icon} {_esc(nc.highlighted_ingredient)} "
                    f"— \"{_esc(nc.trigger_expression)}\" "
                    f"({nc.applicable_rule})",
                    expanded=not nc.compliant,
                ):
                    st.write(f"**Nazwa produktu:** {_esc(nc.product_name)}")
                    st.write(
                        f"**Wymagane:** min {nc.required_minimum_percent}%"
                    )
                    if nc.actual_percent is not None:
                        st.write(f"**Znalezione:** {nc.actual_percent}%")
                    else:
                        st.write("**Znalezione:** brak danych na etykiecie")
                    if nc.notes:
                        st.caption(nc.notes)

        # B) Name consistency
        if r.name_consistency_checks:
            st.markdown("##### Spójność nazwy")
            for ncc in r.name_consistency_checks:
                icon = (
                    "\u2705" if ncc.compliant
                    else _SEV_ICONS.get(ncc.severity, "\u274c")
                )
                with st.expander(
                    f"{icon} {_esc(ncc.check_type)}: {_esc(ncc.description)}",
                    expanded=not ncc.compliant,
                ):
                    if ncc.finding:
                        st.write(f"**Ustalenie:** {_esc(ncc.finding)}")
                    if not ncc.compliant and ncc.issue_description:
                        st.warning(f"\u26a0\ufe0f {_esc(ncc.issue_description)}")
                    if ncc.recommendation:
                        st.info(f"\u2192 {_esc(ncc.recommendation)}")

        if not r.naming_convention_checks and not r.name_consistency_checks:
            st.info("Brak elementów do weryfikacji w nazewnictwie.")

    # -- Tab 3: Brand ----------------------------------------------------------
    with tab_brand:
        if r.brand_compliance_checks:
            for bc in r.brand_compliance_checks:
                icon = (
                    "\u2705" if bc.compliant
                    else _SEV_ICONS.get(bc.severity, "\u274c")
                )
                with st.expander(
                    f"{icon} \"{_esc(bc.flagged_element)}\" "
                    f"({_esc(bc.check_type)})",
                    expanded=not bc.compliant,
                ):
                    st.write(f"**Marka:** {_esc(bc.brand_name)}")
                    if bc.regulation_reference:
                        st.write(
                            f"**Podstawa prawna:** "
                            f"{_esc(bc.regulation_reference)}"
                        )
                    st.write(
                        f"**Status:** "
                        f"{'Zgodny' if bc.compliant else 'Niezgodny'}"
                    )
                    if not bc.compliant and bc.issue_description:
                        st.warning(f"\u26a0\ufe0f {_esc(bc.issue_description)}")
                    if bc.recommendation:
                        st.info(f"\u2192 {_esc(bc.recommendation)}")
        else:
            st.info("Brak elementów do weryfikacji w marce.")

    # -- Tab 4: Trademarks -----------------------------------------------------
    with tab_tm:
        _RISK_COLORS = {
            "high": "\U0001f534",
            "medium": "\U0001f7e1",
            "low": "\U0001f7e0",
            "none": "\u2705",
        }
        if r.trademark_checks:
            for tc in r.trademark_checks:
                risk_icon = _RISK_COLORS.get(tc.risk_level, "\u2753")
                with st.expander(
                    f"{risk_icon} \"{_esc(tc.element_text)}\" "
                    f"({_esc(tc.element_type)})",
                    expanded=tc.risk_level in ("high", "medium"),
                ):
                    st.write(f"**Poziom ryzyka:** {_esc(tc.risk_level)}")
                    if tc.potential_owner:
                        st.write(
                            f"**Potencjalny właściciel:** "
                            f"{_esc(tc.potential_owner)}"
                        )
                    if (
                        tc.trademark_symbol_found
                        and tc.trademark_symbol_found != "none"
                    ):
                        sym = (
                            "\u00ae" if tc.trademark_symbol_found == "registered"
                            else "\u2122"
                        )
                        st.write(f"**Symbol na etykiecie:** {sym}")
                    if tc.issue_description:
                        st.warning(f"\u26a0\ufe0f {_esc(tc.issue_description)}")
                    if tc.recommendation:
                        st.info(f"\u2192 {_esc(tc.recommendation)}")
        else:
            st.info("Brak potencjalnych naruszeń znaków towarowych.")

    # Export
    st.divider()
    stem = Path(filename).stem
    st.download_button(
        "\u2b07\ufe0f Raport prezentacji handlowej (TXT)",
        data=presentation_to_text(result, filename),
        file_name=f"prezentacja_{stem}.txt",
        mime="text/plain",
        width="stretch",
    )


# -- Render market compliance report --------------------------------------------------
def render_market_report(result, filename: str) -> None:
    """Render per-market regulatory compliance check results."""
    st.divider()

    if not result.performed or not result.report:
        st.error(
            f"**Walidacja rynkowa nie powiod\u0142a si\u0119.**\n\n"
            f"{result.error or 'Nieznany b\u0142\u0105d.'}"
        )
        return

    r = result.report

    # Banner
    _COMPLIANCE_MAP = {
        "compliant": (
            "success",
            f"\u2705 Etykieta zgodna z wymogami rynku {_esc(r.target_market)}.",
        ),
        "issues_found": (
            "warning",
            f"\u26a0\ufe0f Wykryto problemy ze zgodno\u015bci\u0105 na rynku {_esc(r.target_market)}.",
        ),
        "non_compliant": (
            "error",
            f"\u26d4 Etykieta niezgodna z wymogami rynku {_esc(r.target_market)}.",
        ),
    }
    banner_type, banner_msg = _COMPLIANCE_MAP.get(
        r.overall_compliance, ("info", r.overall_compliance)
    )
    getattr(st, banner_type)(banner_msg)

    # Metrics
    total_reqs = len(r.market_specific_requirements)
    met_reqs = sum(1 for req in r.market_specific_requirements if req.compliant)
    lang_icon = "\u2705" if r.language_requirements_met else "\u274c"

    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("Wynik", f"{r.score}/100")
    mc2.metric("Wymogi spe\u0142nione", f"{met_reqs}/{total_reqs}")
    mc3.metric("J\u0119zyk", f"{lang_icon} {'OK' if r.language_requirements_met else 'Problem'}")

    # Score bar
    bar_color = (
        "#00b464" if r.score >= 90
        else ("#ffb400" if r.score >= 70 else "#dc3232")
    )
    st.markdown(
        f'<div class="score-bar-bg">'
        f'<div class="score-bar-fill" style="width:{r.score}%;'
        f'background:{bar_color}"></div></div>',
        unsafe_allow_html=True,
    )

    if r.summary:
        st.caption(r.summary)

    # Market requirements
    if r.market_specific_requirements:
        st.subheader(f"Wymogi rynku {_esc(r.target_market)}")
        _SEV_ICONS = {
            "critical": "\U0001f534",
            "warning": "\U0001f7e1",
            "info": "\U0001f535",
        }
        for req in r.market_specific_requirements:
            icon = "\u2705" if req.compliant else _SEV_ICONS.get(req.severity, "\u274c")
            with st.expander(
                f"{icon} {_esc(req.description)}",
                expanded=not req.compliant,
            ):
                c1, c2 = st.columns(2)
                c1.write(f"**ID:** {_esc(req.requirement_id)}")
                c2.write(f"**Kategoria:** {_esc(req.category)}")
                if req.regulation_reference:
                    st.write(f"**Regulacja:** {_esc(req.regulation_reference)}")
                if req.finding:
                    st.write(f"**Znaleziono:** {_esc(req.finding)}")
                if req.recommendation:
                    st.info(f"\u2192 {_esc(req.recommendation)}")

    # Language requirements
    st.subheader("Wymogi j\u0119zykowe")
    if r.language_requirements_met:
        st.success(
            f"\u2705 Wymagany j\u0119zyk obecny i kompletny."
        )
    else:
        st.error(
            f"\u274c Wymogi j\u0119zykowe niespe\u0142nione."
        )
    if r.language_notes:
        st.caption(r.language_notes)

    # Certifications
    if r.additional_certifications_recommended:
        st.subheader("Rekomendowane certyfikaty")
        for cert in r.additional_certifications_recommended:
            st.write(f"\u2022 {_esc(cert)}")

    # Export
    st.divider()
    stem = Path(filename).stem
    st.download_button(
        "\u2b07\ufe0f Raport rynkowy (TXT)",
        data=market_check_to_text(result, filename),
        file_name=f"rynek_{stem}.txt",
        mime="text/plain",
        width="stretch",
    )


# -- Render label text generation report ----------------------------------------------
def render_label_text_report(result, filename: str) -> None:
    """Render generated label text results."""
    st.divider()

    if not result.performed or not result.report:
        st.error(
            f"**Generowanie tekstu nie powiod\u0142o si\u0119.**\n\n"
            f"{result.error or 'Nieznany b\u0142\u0105d.'}"
        )
        return

    r = result.report

    # Banner
    st.success(
        f"\u2705 Tekst etykiety wygenerowany \u2014 "
        f"{_esc(r.language_name)} ({r.language})"
    )

    # Metrics
    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("Sekcje", str(len(r.sections)))
    mc2.metric("J\u0119zyk", r.language_name)
    mc3.metric("Produkt", r.product_name or "\u2014")

    if r.summary:
        st.caption(r.summary)

    # Sections
    if r.sections:
        st.subheader("Sekcje etykiety")
        for sec in r.sections:
            with st.expander(
                f"\U0001f4c4 {_esc(sec.section_title or sec.section_name)}",
                expanded=True,
            ):
                st.text(sec.content)
                if sec.regulatory_reference:
                    st.caption(f"Regulacja: {_esc(sec.regulatory_reference)}")
                if sec.notes:
                    st.caption(f"\U0001f4dd {_esc(sec.notes)}")

    # Feeding table
    if r.feeding_table:
        st.subheader("Tabela dawkowania")
        table_data = [
            {"Masa zwierz\u0119cia": fg.weight_range, "Dzienna porcja": fg.daily_amount}
            for fg in r.feeding_table
        ]
        st.table(table_data)

    # Warnings
    if r.warnings:
        st.subheader("Ostrze\u017cenia")
        for w in r.warnings:
            st.warning(w)

    # Complete text — copyable block
    if r.complete_text:
        st.subheader("Pe\u0142ny tekst etykiety")
        st.code(r.complete_text, language=None)

    # Export
    st.divider()
    stem = Path(filename).stem if filename else "etykieta"

    col_a, col_b = st.columns(2)
    with col_a:
        st.download_button(
            "\u2b07\ufe0f Tekst etykiety (TXT)",
            data=label_text_to_text(result, filename),
            file_name=f"etykieta_{stem}.txt",
            mime="text/plain",
            width="stretch",
        )
    with col_b:
        from fediaf_verifier.jsx_text_generator import generate_text_jsx

        jsx_sections = [
            {"title": sec.section_title or sec.section_name, "content": sec.content}
            for sec in r.sections
        ]
        jsx_script = generate_text_jsx(
            jsx_sections, r.language_name, filename or ""
        )
        st.download_button(
            "\u2b07\ufe0f Skrypt Illustrator (.jsx)",
            data=jsx_script,
            file_name=f"tekst_{stem}.jsx",
            mime="application/javascript",
            width="stretch",
            help=(
                "Otw\u00f3rz etykiet\u0119 w Illustratorze, "
                "potem File > Scripts > Other Script > wybierz ten plik. "
                "Doda warstw\u0119 z ramkami tekstowymi."
            ),
        )


# -- Render product description report ------------------------------------------------
def render_product_description_report(result, filename: str) -> None:
    """Render generated product description results."""
    st.divider()

    if not result.performed or not result.report:
        st.error(
            f"**Generowanie opisu nie powiod\u0142o si\u0119.**\n\n"
            f"{result.error or 'Nieznany b\u0142\u0105d.'}"
        )
        return

    r = result.report

    TONE_LABELS = {
        "premium": "Premium",
        "scientific": "Naukowy",
        "natural": "Naturalny",
        "standard": "Standardowy",
    }

    # Human review warning
    _has_claim_warnings = bool(r.claims_warnings)
    if _has_claim_warnings:
        st.markdown(
            '<div class="status-banner status-warn">'
            "\u26a0\ufe0f <strong>Opis wymaga przej\u015bcia przez specjalist\u0119"
            "</strong> \u2014 wykryto "
            f"{len(r.claims_warnings)} ostrze\u017ce\u0144 "
            "dotycz\u0105cych claim\u00f3w marketingowych."
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        st.success(
            f"\u2705 Opis produktu wygenerowany \u2014 "
            f"{_esc(r.language_name)} ({r.language}), "
            f"styl: {TONE_LABELS.get(r.tone, r.tone)}"
        )

    st.info(
        "\U0001f4cb **Uwaga:** Opis wygenerowany przez AI przeszed\u0142 "
        "weryfikacj\u0119 krzy\u017cow\u0105 (reflection step) i "
        "deterministyczn\u0105 walidacj\u0119 claim\u00f3w. "
        "Mimo to **wymagany jest przegl\u0105d cz\u0142owieka** przed "
        "publikacj\u0105 \u2014 szczeg\u00f3lnie claim\u00f3w marketingowych "
        "i danych liczbowych.",
        icon="\u26a0\ufe0f",
    )

    # Metrics
    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("Produkt", r.product_name or "\u2014")
    mc2.metric("J\u0119zyk", r.language_name)
    mc3.metric("Styl", TONE_LABELS.get(r.tone, r.tone))
    mc4.metric("Sekcje", str(len(r.sections)))

    if r.summary:
        st.caption(r.summary)

    # Tabs
    tab_full, tab_short, tab_bullets, tab_seo, tab_html = st.tabs([
        "Pe\u0142ny opis",
        "Kr\u00f3tki opis",
        "Bullet Points",
        "SEO",
        "HTML",
    ])

    with tab_full:
        if r.sections:
            for sec in r.sections:
                with st.expander(
                    f"\U0001f4c4 {_esc(sec.section_title or sec.section_name)}",
                    expanded=True,
                ):
                    st.markdown(sec.content)

        if r.complete_text:
            st.subheader("Pe\u0142ny tekst (kopiowanie)")
            st.code(r.complete_text, language=None)

    with tab_short:
        if r.short_description:
            st.info(r.short_description)
        else:
            st.caption("Brak kr\u00f3tkiego opisu.")

    with tab_bullets:
        if r.bullet_points:
            for bp in r.bullet_points:
                st.markdown(f"- {_esc(bp)}")
        else:
            st.caption("Brak punkt\u00f3w sprzeda\u017cowych.")

    with tab_seo:
        if r.seo:
            seo = r.seo
            st.markdown(f"**Meta title** ({len(seo.meta_title)}/60 zn.):")
            st.code(seo.meta_title, language=None)
            st.markdown(
                f"**Meta description** ({len(seo.meta_description)}/160 zn.):"
            )
            st.code(seo.meta_description, language=None)
            if seo.focus_keyword:
                st.markdown(f"**Focus keyword:** {_esc(seo.focus_keyword)}")
            if seo.keywords:
                st.markdown(
                    "**Keywords:** " + ", ".join(f"`{_esc(k)}`" for k in seo.keywords)
                )
        else:
            st.caption("Brak metadanych SEO.")

    with tab_html:
        if r.complete_html:
            st.subheader("Podgl\u0105d")
            st.markdown(r.complete_html, unsafe_allow_html=True)
            st.subheader("Kod \u017ar\u00f3d\u0142owy")
            st.code(r.complete_html, language="html")
        else:
            st.caption("Brak wersji HTML.")

    # Claims warnings
    if r.claims_warnings:
        st.divider()
        st.subheader(
            f"\u26a0\ufe0f Ostrze\u017cenia dotycz\u0105ce claim\u00f3w "
            f"({len(r.claims_warnings)})"
        )
        WARNING_TYPE_LABELS = {
            "forbidden_therapeutic": "\u26d4 Zakazany claim terapeutyczny",
            "unsubstantiated": "\u26a0\ufe0f Brak uzasadnienia",
            "naming_rule_violation": "\u26a0\ufe0f Naruszenie regu\u0142y nazewnictwa",
            "needs_evidence": "\U0001f4cb Wymaga dowodu",
        }
        for cw in r.claims_warnings:
            wt_label = WARNING_TYPE_LABELS.get(
                cw.warning_type, cw.warning_type.upper()
            )
            st.warning(
                f"**{wt_label}:** {_esc(cw.claim_text)}\n\n"
                f"{_esc(cw.explanation)}\n\n"
                f"\u2192 {_esc(cw.recommendation)}"
            )

    # Claims used
    if r.claims_used:
        with st.expander(
            f"\u2713 Claimy u\u017cyte w opisie ({len(r.claims_used)})",
            expanded=False,
        ):
            for c in r.claims_used:
                st.markdown(f"- {_esc(c)}")

    # Export
    st.divider()
    stem = Path(filename).stem if filename else "opis_produktu"

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.download_button(
            "\u2b07\ufe0f Opis (TXT)",
            data=product_description_to_text(result, filename),
            file_name=f"opis_{stem}.txt",
            mime="text/plain",
            width="stretch",
        )
    with col_b:
        st.download_button(
            "\u2b07\ufe0f Opis (HTML)",
            data=r.complete_html or r.complete_text,
            file_name=f"opis_{stem}.html",
            mime="text/html",
            width="stretch",
        )
    with col_c:
        st.download_button(
            "\u2b07\ufe0f Opis (JSON)",
            data=r.model_dump_json(indent=2, exclude_none=True),
            file_name=f"opis_{stem}.json",
            mime="application/json",
            width="stretch",
        )


# -- Render label diff report ---------------------------------------------------------
def render_diff_report(
    result, old_filename: str, new_filename: str,
) -> None:
    """Render label version comparison results."""
    st.divider()

    if not result.performed or not result.report:
        st.error(
            f"**Por\u00f3wnanie wersji nie powiod\u0142o si\u0119.**\n\n"
            f"{result.error or 'Nieznany b\u0142\u0105d.'}"
        )
        return

    r = result.report

    # Banner by risk level
    _RISK_MAP = {
        "low": (
            "success",
            "\u2705 Niskie ryzyko \u2014 zmiany nie wprowadzaj\u0105 nowych problem\u00f3w.",
        ),
        "medium": (
            "warning",
            "\u26a0\ufe0f \u015arednie ryzyko \u2014 przejrzyj wykryte zmiany.",
        ),
        "high": (
            "error",
            "\u26d4 Wysokie ryzyko \u2014 zmiany mog\u0105 wprowadza\u0107 problemy regulacyjne.",
        ),
    }
    banner_type, banner_msg = _RISK_MAP.get(
        r.risk_level, ("info", r.risk_level)
    )
    getattr(st, banner_type)(banner_msg)

    # Metrics
    _RISK_LABELS = {
        "low": "\U0001f7e2 Niskie",
        "medium": "\U0001f7e1 \u015arednie",
        "high": "\U0001f534 Wysokie",
    }
    risk_label = _RISK_LABELS.get(r.risk_level, r.risk_level)

    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("Zmiany", str(r.change_count))
    mc2.metric("Ryzyko", risk_label)
    mc3.metric("Nowe problemy", str(len(r.new_issues_introduced)))
    mc4.metric("Rozwi\u0105zane", str(len(r.issues_resolved)))

    if r.summary:
        st.caption(r.summary)

    # Text changes
    if r.text_changes:
        st.subheader(f"Zmiany tekstowe ({len(r.text_changes)})")
        _CHANGE_ICONS = {
            "added": "\U0001f7e2",
            "removed": "\U0001f534",
            "modified": "\U0001f7e1",
            "moved": "\U0001f535",
        }
        _CHANGE_LABELS = {
            "added": "Dodano",
            "removed": "Usuni\u0119to",
            "modified": "Zmieniono",
            "moved": "Przeniesiono",
        }
        _SEV_ICONS = {
            "critical": "\U0001f534",
            "warning": "\U0001f7e1",
            "info": "\U0001f535",
        }
        for tc in r.text_changes:
            change_icon = _CHANGE_ICONS.get(tc.change_type, "\u26aa")
            change_label = _CHANGE_LABELS.get(tc.change_type, tc.change_type)
            sev_icon = _SEV_ICONS.get(tc.severity, "")

            with st.expander(
                f"{change_icon} [{change_label}] {_esc(tc.section)} "
                f"{sev_icon}",
                expanded=tc.severity == "critical",
            ):
                if tc.old_text:
                    st.markdown(
                        f'<div style="background:rgba(220,50,50,0.08);'
                        f'padding:8px 12px;border-radius:6px;margin-bottom:8px;">'
                        f'<s>{_esc(tc.old_text)}</s></div>',
                        unsafe_allow_html=True,
                    )
                if tc.new_text:
                    st.markdown(
                        f'<div style="background:rgba(0,180,100,0.08);'
                        f'padding:8px 12px;border-radius:6px;">'
                        f'<strong>{_esc(tc.new_text)}</strong></div>',
                        unsafe_allow_html=True,
                    )
                if tc.regulatory_impact:
                    st.caption(
                        f"\u26a0\ufe0f Wp\u0142yw regulacyjny: {_esc(tc.regulatory_impact)}"
                    )

    # Layout changes
    if r.layout_changes:
        st.subheader(f"Zmiany uk\u0142adu ({len(r.layout_changes)})")
        _SEV_ICONS_L = {
            "critical": "\U0001f534",
            "warning": "\U0001f7e1",
            "info": "\U0001f535",
        }
        for lc in r.layout_changes:
            icon = _SEV_ICONS_L.get(lc.severity, "\u26aa")
            st.markdown(
                f"{icon} {_esc(lc.description)}"
                + (f"  \n*Obszar: {_esc(lc.area)}*" if lc.area else ""),
                unsafe_allow_html=True,
            )

    # New issues introduced
    if r.new_issues_introduced:
        st.subheader(f"\u26a0\ufe0f Nowe problemy ({len(r.new_issues_introduced)})")
        for ni in r.new_issues_introduced:
            _NI_ICONS = {
                "critical": "\U0001f534",
                "warning": "\U0001f7e1",
                "info": "\U0001f535",
            }
            icon = _NI_ICONS.get(ni.severity, "\u26aa")
            st.markdown(
                f"{icon} {_esc(ni.description)}",
                unsafe_allow_html=True,
            )
            if ni.introduced_by_change:
                st.caption(
                    f"Spowodowane zmian\u0105: {_esc(ni.introduced_by_change)}"
                )

    # Issues resolved
    if r.issues_resolved:
        st.subheader(f"\u2705 Rozwi\u0105zane problemy ({len(r.issues_resolved)})")
        for ir_text in r.issues_resolved:
            st.write(f"\u2705 {_esc(ir_text)}")

    # Overall assessment
    if r.overall_assessment:
        st.subheader("Ocena og\u00f3lna")
        st.info(r.overall_assessment)

    # Export
    st.divider()
    stem = Path(new_filename).stem if new_filename else "diff"
    st.download_button(
        "\u2b07\ufe0f Raport por\u00f3wnania (TXT)",
        data=diff_to_text(result, old_filename, new_filename),
        file_name=f"diff_{stem}.txt",
        mime="text/plain",
        width="stretch",
    )


# -- Render artwork inspection report ---------------------------------------------------
def render_artwork_inspection_report(
    result, filename_a: str, filename_b: str = "",
) -> None:
    """Render artwork inspection results: pixel diff, colors, print readiness."""
    import base64

    st.divider()

    if not result.performed or not result.report:
        st.error(
            f"**Inspekcja artwork nie powiod\u0142a si\u0119.**\n\n"
            f"{result.error or 'Nieznany b\u0142\u0105d.'}"
        )
        return

    r = result.report
    score = r.overall_score

    # Banner
    if r.overall_verdict == "pass":
        st.success(f"\u2705 **Inspekcja pozytywna \u2014 {score}/100**")
    elif r.overall_verdict == "review":
        st.warning(f"\u26a0\ufe0f **Wymaga przegl\u0105du \u2014 {score}/100**")
    else:
        st.error(f"\u26d4 **Inspekcja negatywna \u2014 {score}/100**")

    # Hints about missing optional features
    from fediaf_verifier.deps import is_available

    _missing_hints = []
    if not r.ocr_comparison and not is_available("ocr"):
        _missing_hints.append(
            "\U0001f4dd **OCR text comparison** \u2014 "
            "zainstaluj w panelu bocznym (\u2699\ufe0f Dodatkowe funkcje)"
        )
    if not r.saliency and not is_available("saliency"):
        _missing_hints.append(
            "\U0001f441\ufe0f **Analiza uwagi wizualnej (DeepGaze)** \u2014 "
            "zainstaluj w panelu bocznym (\u2699\ufe0f Dodatkowe funkcje)"
        )
    if _missing_hints:
        with st.expander(
            f"\U0001f4e6 Dost\u0119pne rozszerzenia ({len(_missing_hints)})",
            expanded=False,
        ):
            for hint in _missing_hints:
                st.markdown(hint)

    # Metrics row
    n_print_issues = len(r.print_readiness.issues) if r.print_readiness else 0
    n_color_mismatches = (
        sum(1 for c in r.color_analysis.comparisons if c.verdict == "mismatch")
        if r.color_analysis else 0
    )
    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("Ocena", f"{score}/100")
    mc2.metric("Problemy druku", str(n_print_issues))
    mc3.metric(
        "SSIM",
        f"{r.pixel_diff.ssim_score:.3f}" if r.pixel_diff else "N/A",
    )
    mc4.metric("Kolory mismatch", str(n_color_mismatches))

    # Score bar
    bar_color = "#00b464" if score >= 85 else ("#ffb400" if score >= 60 else "#dc3232")
    st.markdown(
        f'<div style="background:#e0e0e0;border-radius:6px;height:12px;margin:8px 0 16px;">'
        f'<div style="width:{score}%;background:{bar_color};'
        f'height:100%;border-radius:6px;"></div></div>',
        unsafe_allow_html=True,
    )

    # Tabs
    tab_names = ["\U0001f5a8\ufe0f Gotowosc do druku", "\U0001f3a8 Kolory"]
    if r.pixel_diff:
        tab_names.append("\U0001f50d Pixel diff")
    if r.ocr_comparison:
        tab_names.append("\U0001f4dd Tekst OCR")
    if r.icc_profile:
        tab_names.append("\U0001f3a8 ICC profil")
    if r.saliency:
        tab_names.append("\U0001f441\ufe0f Uwaga wizualna")
    tab_names.append("\U0001f916 Podsumowanie AI")

    tabs = st.tabs(tab_names)
    tab_idx = 0

    # ---- Print readiness tab ----
    with tabs[tab_idx]:
        tab_idx += 1
        if r.print_readiness:
            pr = r.print_readiness
            pr_status = "\u2705 Gotowy do druku" if pr.print_ready else "\u274c Nie gotowy"
            st.subheader(f"{pr_status} ({pr.score}/100)")

            c1, c2, c3 = st.columns(3)
            c1.metric("DPI", f"{pr.dpi:.0f}" if pr.dpi > 0 else "brak danych")
            c2.metric("Kolory", pr.color_space)
            c3.metric("Format", pr.file_format)

            info_cols = st.columns(4)
            info_cols[0].markdown(
                f"**DPI:** {'OK' if pr.dpi_sufficient else 'Za niskie'}"
            )
            info_cols[1].markdown(
                f"**CMYK:** {'Tak' if pr.color_space_print_ready else 'Nie'}"
            )
            info_cols[2].markdown(
                f"**Bleed:** {'Tak' if pr.has_bleed else 'Nie'}"
            )
            if pr.fonts_embedded is not None:
                info_cols[3].markdown(
                    f"**Fonty:** {'Osadzone' if pr.fonts_embedded else 'Brak!'}"
                )
            if pr.page_size_mm:
                st.caption(
                    f"Rozmiar: {pr.page_size_mm[0]:.1f} \u00d7 "
                    f"{pr.page_size_mm[1]:.1f} mm"
                )

            if pr.issues:
                _SEV_I = {
                    "critical": "\U0001f534",
                    "warning": "\U0001f7e1",
                    "info": "\U0001f535",
                }
                for iss in pr.issues:
                    icon = _SEV_I.get(iss.severity, "\u26aa")
                    with st.expander(
                        f"{icon} {iss.description}",
                        expanded=iss.severity == "critical",
                    ):
                        if iss.recommendation:
                            st.write(f"\u2192 {iss.recommendation}")
                        if iss.value_found:
                            st.caption(
                                f"Znaleziono: {iss.value_found} "
                                f"| Wymagane: {iss.value_expected}"
                            )
        else:
            st.info("Brak analizy gotowo\u015bci do druku.")

    # ---- Color analysis tab ----
    with tabs[tab_idx]:
        tab_idx += 1
        if r.color_analysis:
            ca = r.color_analysis
            st.subheader(
                f"Paleta kolorow ({ca.color_space_detected})"
            )

            # Show color swatches
            swatch_html = ""
            for c in ca.dominant_colors:
                swatch_html += (
                    f'<div style="display:inline-block;margin:4px;">'
                    f'<div style="width:48px;height:48px;background:{c.hex};'
                    f'border:1px solid #ccc;border-radius:6px;"></div>'
                    f'<div style="font-size:0.7rem;text-align:center;">'
                    f'{c.hex}<br>{c.percentage:.0f}%</div></div>'
                )
            st.markdown(swatch_html, unsafe_allow_html=True)

            # Color comparisons
            if ca.comparisons:
                st.subheader("Por\u00f3wnanie kolorow (Delta E CIE2000)")
                st.metric(
                    "Spojnosc kolorow",
                    f"{ca.color_consistency_score:.0f}/100",
                )
                for comp in ca.comparisons:
                    if comp.verdict == "match":
                        icon = "\u2705"
                    elif comp.verdict == "close":
                        icon = "\U0001f7e1"
                    else:
                        icon = "\U0001f534"
                    st.markdown(
                        f"{icon} `{comp.color_a_hex}` \u2192 "
                        f"`{comp.color_b_hex}` "
                        f"\u2014 \u0394E = **{comp.delta_e:.2f}** "
                        f"({comp.verdict})"
                    )
        else:
            st.info("Brak analizy kolorow.")

    # ---- Pixel diff tab ----
    if r.pixel_diff:
        with tabs[tab_idx]:
            tab_idx += 1
            pd = r.pixel_diff
            _VERD_LABELS = {
                "identical": "\u2705 Identyczne",
                "minor_changes": "\U0001f7e1 Drobne zmiany",
                "significant_changes": "\U0001f7e0 Istotne zmiany",
                "major_changes": "\U0001f534 Du\u017ce zmiany",
            }
            st.subheader(
                _VERD_LABELS.get(pd.verdict, pd.verdict)
            )

            vc1, vc2, vc3 = st.columns(3)
            vc1.metric("SSIM", f"{pd.ssim_score:.4f}")
            vc2.metric("Zmienione px", f"{pd.changed_pixels_pct:.2f}%")
            vc3.metric("Regiony zmian", str(len(pd.diff_regions)))

            # Diff overlay image
            if pd.diff_image_b64:
                try:
                    diff_bytes = base64.b64decode(pd.diff_image_b64)
                    st.image(
                        diff_bytes,
                        caption="Mapa roznic (czerwony = zmiana)",
                        use_container_width=True,
                    )
                except Exception:
                    st.warning("Nie uda\u0142o si\u0119 wy\u015bwietli\u0107 mapy r\u00f3\u017cnic.")

            if pd.diff_regions:
                st.caption(f"Wykryte regiony zmian: {len(pd.diff_regions)}")
                for i, reg in enumerate(pd.diff_regions, 1):
                    st.write(
                        f"{i}. Pozycja [{reg.x}, {reg.y}] "
                        f"rozmiar {reg.w}\u00d7{reg.h} px "
                        f"\u2014 zmiana: {reg.change_pct:.1f}%"
                    )

    # ---- OCR text comparison tab ----
    if r.ocr_comparison:
        with tabs[tab_idx]:
            tab_idx += 1
            ocr = r.ocr_comparison
            st.subheader(
                f"Por\u00f3wnanie tekstu \u2014 {ocr.similarity_pct:.1f}% zgodno\u015bci"
            )

            oc1, oc2, oc3 = st.columns(3)
            oc1.metric("Podobienstwo", f"{ocr.similarity_pct:.1f}%")
            oc2.metric("Zmiany", str(ocr.total_changes))
            oc3.metric(
                "Pewnosc OCR",
                f"{(ocr.avg_confidence_a + ocr.avg_confidence_b) / 2:.0%}",
            )

            if ocr.changes:
                _CHANGE_ICONS_OCR = {
                    "added": "\U0001f7e2",
                    "removed": "\U0001f534",
                    "modified": "\U0001f7e1",
                }
                for ch in ocr.changes:
                    icon = _CHANGE_ICONS_OCR.get(ch.change_type, "\u26aa")
                    label = {
                        "added": "Dodano",
                        "removed": "Usuni\u0119to",
                        "modified": "Zmieniono",
                    }.get(ch.change_type, ch.change_type)
                    with st.expander(
                        f"{icon} [{label}] linia {ch.line_number}",
                        expanded=ch.change_type != "added",
                    ):
                        if ch.old_text:
                            st.markdown(
                                f'<div style="background:rgba(220,50,50,0.08);'
                                f'padding:8px 12px;border-radius:6px;margin-bottom:8px;">'
                                f'<s>{_esc(ch.old_text)}</s></div>',
                                unsafe_allow_html=True,
                            )
                        if ch.new_text:
                            st.markdown(
                                f'<div style="background:rgba(0,180,100,0.08);'
                                f'padding:8px 12px;border-radius:6px;">'
                                f'<strong>{_esc(ch.new_text)}</strong></div>',
                                unsafe_allow_html=True,
                            )
            else:
                st.success("Brak r\u00f3\u017cnic tekstowych.")

            with st.expander("Pelny tekst (master)"):
                st.code(ocr.text_a or "(brak tekstu)", language=None)
            with st.expander("Pelny tekst (proof)"):
                st.code(ocr.text_b or "(brak tekstu)", language=None)

    # ---- ICC profile tab ----
    if r.icc_profile:
        with tabs[tab_idx]:
            tab_idx += 1
            icc = r.icc_profile
            if icc.has_profile:
                st.success(f"\u2705 Profil ICC: {icc.profile_name or 'znaleziony'}")
                ic1, ic2, ic3 = st.columns(3)
                ic1.metric("Przestrzen", icc.color_space or "?")
                ic2.metric("Rendering", icc.rendering_intent or "?")
                ic3.metric("PCS", icc.pcs or "?")
            else:
                st.warning("\u26a0\ufe0f Brak profilu ICC")

            if icc.issues:
                for iss in icc.issues:
                    st.warning(iss)

            if r.icc_profile_b:
                st.divider()
                icc_b = r.icc_profile_b
                st.subheader("Profil ICC (proof)")
                if icc_b.has_profile:
                    st.success(f"Profil: {icc_b.profile_name or 'znaleziony'} ({icc_b.color_space})")
                else:
                    st.warning("Brak profilu ICC w pliku proof")
                if icc_b.issues:
                    for iss in icc_b.issues:
                        st.warning(iss)

    # ---- Saliency tab ----
    if r.saliency:
        with tabs[tab_idx]:
            tab_idx += 1
            sal = r.saliency
            st.subheader(f"Analiza uwagi wizualnej ({sal.model_used})")

            # --- Main metrics row ---
            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric("Focus", f"{sal.focus_score:.0f}/100")
            if sal.clarity:
                mc2.metric("Czytelnosc", f"{sal.clarity.score:.0f}/100")
            if sal.cognitive_load:
                mc3.metric("Latwosc przetwarzania", f"{sal.cognitive_load.ease_score:.0f}/100")
            mc4.metric("Regiony uwagi", str(len(sal.attention_regions)))

            st.caption(
                "Focus = koncentracja uwagi | Czytelnosc = porzadek wizualny "
                "| Latwosc przetwarzania = niski wysilek mentalny "
                "(estymacja heurystyczna)"
            )

            if sal.heatmap_b64:
                try:
                    hm_bytes = base64.b64decode(sal.heatmap_b64)
                    st.image(
                        hm_bytes,
                        caption="Heatmapa uwagi (ciep\u0142e = wysoka uwaga)",
                        use_container_width=True,
                    )
                except Exception:
                    st.warning("Nie udalo sie wyswietlic heatmapy.")

            # --- Focus details ---
            if sal.focus_metrics:
                with st.expander("Szczegoly Focus Score"):
                    fm = sal.focus_metrics
                    fc1, fc2, fc3 = st.columns(3)
                    fc1.metric("Entropia", f"{fm.entropy:.0f}/100",
                               help="Niska entropia = uwaga skoncentrowana w malej liczbie punktow")
                    fc2.metric("Gini", f"{fm.gini:.2f}",
                               help="Wysoki wspolczynnik Gini = wieksza nierownosc (koncentracja)")
                    fc3.metric("Klastry uwagi", str(fm.cluster_count),
                               help="Mniej klastrow = bardziej skoncentrowana uwaga")

            # --- Clarity details ---
            if sal.clarity:
                with st.expander("Szczegoly Czytelnosci"):
                    cl = sal.clarity
                    cc1, cc2, cc3, cc4 = st.columns(4)
                    cc1.metric("Gestosc krawedzi", f"{cl.edge_density:.3f}",
                               help="Nizsza = czystszy design (< 0.05 = dobrze)")
                    cc2.metric("Kolory dominujace", str(cl.color_complexity),
                               help="Mniej = spojniejsza paleta (2-4 = optymalnie)")
                    cc3.metric("Biala przestrzen", f"{cl.whitespace_ratio:.0%}",
                               help="Wiecej = lzejszy, czytelniejszy design")
                    cc4.metric("Symetria", f"{cl.symmetry:.2f}",
                               help="Korelacja lewa-prawa (1.0 = idealnie symetryczny)")

            # --- Cognitive Load details ---
            if sal.cognitive_load:
                with st.expander("Szczegoly Obciazenia Kognitywnego"):
                    cg = sal.cognitive_load
                    cg1, cg2, cg3, cg4 = st.columns(4)
                    cg1.metric("Zlozonosc czestotl.", f"{cg.frequency_complexity:.2f}",
                               help="Energia wysokich czestotliwosci — drobne detale i tekstury")
                    cg2.metric("Elementy wizualne", str(cg.element_count),
                               help="Liczba odrębnych elementow na etykiecie")
                    cg3.metric("Roznorodnosc kolorow", f"{cg.color_diversity:.2f}",
                               help="Rozklad odcieni chromatycznych (0-1)")
                    cg4.metric("Gestosc krawedzi", f"{cg.edge_density:.3f}",
                               help="Wspoldzielona z metryką czytelnosci")

            # --- Attention regions ---
            if sal.attention_regions:
                st.subheader("Top regiony uwagi")
                for reg in sal.attention_regions:
                    st.write(
                        f"**#{reg.rank}** \u2014 {reg.attention_pct:.1f}% uwagi "
                        f"[{reg.x},{reg.y} {reg.w}\u00d7{reg.h}px]"
                    )

    # ---- AI Summary tab ----
    with tabs[tab_idx]:
        if r.ai_summary:
            st.subheader("Podsumowanie AI")
            st.info(r.ai_summary)
        if r.ai_recommendations:
            st.subheader("Rekomendacje")
            for i, rec in enumerate(r.ai_recommendations, 1):
                st.write(f"{i}. {rec}")
        if not r.ai_summary and not r.ai_recommendations:
            st.info("Podsumowanie AI niedost\u0119pne.")

    # Export
    st.divider()
    stem_a = Path(filename_a).stem
    col_a, col_b = st.columns(2)
    with col_a:
        st.download_button(
            "\u2b07\ufe0f Raport (TXT)",
            data=artwork_inspection_to_text(result, filename_a, filename_b),
            file_name=f"artwork_{stem_a}.txt",
            mime="text/plain",
            width="stretch",
        )
    with col_b:
        json_data = result.report.model_dump_json(
            indent=2,
            exclude_none=True,
            exclude={"pixel_diff": {"diff_image_b64"}},
        )
        st.download_button(
            "\u2b07\ufe0f Raport (JSON)",
            data=json_data,
            file_name=f"artwork_{stem_a}.json",
            mime="application/json",
            width="stretch",
        )
