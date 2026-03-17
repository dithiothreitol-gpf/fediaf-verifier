"""Streamlit application — BULT Quality Check."""

import sys
from pathlib import Path

import anthropic
import streamlit as st
from loguru import logger

from fediaf_verifier.config import AppSettings, get_settings
from fediaf_verifier.converter import file_to_base64, load_pdf_base64
from fediaf_verifier.exceptions import (
    ConfigurationError,
    ConversionError,
    FediafVerifierError,
)
from fediaf_verifier.export import to_json, to_text
from fediaf_verifier.models import EnrichedReport, ExtractionConfidence
from fediaf_verifier.verifier import create_client, verify_label

# -- Logging setup ---------------------------------------------------------------------
logger.remove()
logger.add(sys.stderr, level="INFO")
Path("logs").mkdir(exist_ok=True)
logger.add("logs/bult_{time}.log", rotation="10 MB", retention="30 days", level="DEBUG")

# -- Custom CSS for professional look --------------------------------------------------
_CUSTOM_CSS = """
<style>
    /* Clean card-style metric containers */
    [data-testid="stMetric"] {
        background: var(--secondary-background-color);
        border-radius: 12px;
        padding: 16px 20px;
        border: 1px solid rgba(128,128,128,0.1);
    }
    [data-testid="stMetric"] label {
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        opacity: 0.7;
    }

    /* Subtle dividers */
    hr { opacity: 0.15; }

    /* Tighter sidebar */
    section[data-testid="stSidebar"] > div { padding-top: 1.5rem; }

    /* Score progress bar */
    .score-bar-bg {
        height: 6px;
        border-radius: 3px;
        background: var(--secondary-background-color);
        margin: 4px 0 20px;
    }
    .score-bar-fill {
        height: 6px;
        border-radius: 3px;
        transition: width 0.4s ease;
    }

    /* Status banner styling */
    .status-banner {
        padding: 1rem 1.25rem;
        border-radius: 10px;
        margin: 0.5rem 0 1.25rem;
        font-size: 0.95rem;
        line-height: 1.5;
    }
    .status-pass {
        background: rgba(0,180,100,0.08);
        border-left: 4px solid #00b464;
        color: inherit;
    }
    .status-warn {
        background: rgba(255,180,0,0.08);
        border-left: 4px solid #ffb400;
        color: inherit;
    }
    .status-fail {
        background: rgba(220,50,50,0.08);
        border-left: 4px solid #dc3232;
        color: inherit;
    }

    /* EU check grid */
    .eu-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 8px;
        margin-top: 8px;
    }
    .eu-item {
        background: var(--secondary-background-color);
        border-radius: 8px;
        padding: 10px 14px;
        font-size: 0.88rem;
    }

    /* Download buttons side by side */
    .stDownloadButton > button {
        border-radius: 8px;
    }

    /* Footer text */
    .footer-text {
        font-size: 0.75rem;
        opacity: 0.5;
        text-align: center;
        padding: 2rem 0 1rem;
        line-height: 1.6;
    }
</style>
"""

# -- Page config -----------------------------------------------------------------------
st.set_page_config(
    page_title="BULT Quality Check",
    page_icon="\U0001f43e",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(_CUSTOM_CSS, unsafe_allow_html=True)

st.title("\U0001f43e BULT Quality Check")
st.caption(
    "Weryfikacja sk\u0142adu i zgodno\u015bci etykiet z wytycznymi FEDIAF "
    "oraz regulacjami EU \u2014 zanim produkt trafi do miski."
)


# -- Load settings ---------------------------------------------------------------------
@st.cache_resource
def _load_settings() -> AppSettings:
    return get_settings()


try:
    settings = _load_settings()
except Exception as e:
    st.error(
        f"**B\u0142\u0105d konfiguracji:** {e}\n\n"
        "Sprawdz plik `.env` \u2014 wymagany klucz `ANTHROPIC_API_KEY`."
    )
    st.stop()


@st.cache_resource
def _init_client(_api_key: str) -> anthropic.Anthropic:
    return create_client(settings)


client = _init_client(settings.anthropic_api_key)

# -- Session state ---------------------------------------------------------------------
if "report" not in st.session_state:
    st.session_state.report = None
if "report_filename" not in st.session_state:
    st.session_state.report_filename = ""
if "report_market" not in st.session_state:
    st.session_state.report_market = None

# -- Sidebar ---------------------------------------------------------------------------
MARKETS = [
    "\u2014 bez analizy trend\u00f3w \u2014",
    "Polska",
    "Niemcy",
    "Francja",
    "Wielka Brytania",
    "Czechy",
    "W\u0119gry",
    "Rumunia",
    "W\u0142ochy",
    "Hiszpania",
]

with st.sidebar:
    st.header("Parametry weryfikacji")

    market_selection = st.selectbox(
        "Rynek docelowy",
        options=MARKETS,
        help=(
            "Opcjonalne. Dodaj kraj, a raport uwzgl\u0119dni aktualne "
            "trendy rynkowe dla tej kategorii produktu."
        ),
    )
    selected_market = None if market_selection == MARKETS[0] else market_selection

    if selected_market:
        st.info(f"Rynek docelowy: **{selected_market}**")
    else:
        st.caption("Weryfikacja obejmie wy\u0142\u0105cznie FEDIAF i regulacje EU.")

    st.divider()

    pdf_path = settings.fediaf_pdf_path
    if pdf_path.is_file():
        size_mb = pdf_path.stat().st_size / 1_048_576
        st.success(f"FEDIAF Guidelines ({size_mb:.1f} MB) \u2713")
    else:
        st.error(
            f"Brak pliku `{pdf_path}`\n\n"
            "Pobierz FEDIAF Nutritional Guidelines ze strony fediaf.org "
            "i zapisz w folderze data/."
        )
        st.stop()

    with st.expander("O warstwach weryfikacji"):
        st.markdown("""
**Jak sprawdzamy rzetelno\u015b\u0107:**

1. Model ocenia pewno\u015b\u0107 odczytu ka\u017cdej warto\u015bci
2. Niezale\u017cny drugi odczyt warto\u015bci liczbowych
3. Progi FEDIAF zakodowane bezpo\u015brednio w Pythonie
4. Automatyczna eskalacja do eksperta przy w\u0105tpliwo\u015bciach
5. Zestaw testowy z r\u0119cznie potwierdzonymi wynikami

*Narz\u0119dzie wspomagaj\u0105ce prac\u0119 dzia\u0142u jako\u015bci.*
""")

    st.divider()
    st.caption("v1.0 \u00b7 BULT Quality Check")


# -- Upload section --------------------------------------------------------------------
uploaded = st.file_uploader(
    "Wgraj etykiet\u0119 produktu",
    type=["jpg", "jpeg", "png", "pdf", "docx"],
    help="JPG, PNG, PDF lub dokument Word (.docx)",
)

if uploaded:
    col_preview, col_info = st.columns([1, 2])
    with col_preview:
        if uploaded.type and uploaded.type.startswith("image"):
            st.image(uploaded, caption=uploaded.name, width="stretch")
        else:
            st.markdown(
                f'<div style="background:var(--secondary-background-color);'
                f"border-radius:10px;padding:2rem;text-align:center;\">"
                f'<span style="font-size:2.5rem;">\U0001f4c4</span><br>'
                f'<span style="opacity:0.7;font-size:0.85rem;">{uploaded.name}</span>'
                f"</div>",
                unsafe_allow_html=True,
            )
    with col_info:
        st.markdown(f"**Plik:** {uploaded.name}")
        st.markdown(f"**Rozmiar:** {uploaded.size / 1024:.1f} KB")
        st.markdown(f"**Rynek:** {selected_market or 'nie wybrano'}")
        if selected_market:
            st.caption(
                "Analiza z wyszukiwaniem trend\u00f3w \u2014 ok. 60\u201390 sekund."
            )
        else:
            st.caption("Analiza bez trend\u00f3w \u2014 ok. 30\u201360 sekund.")


# -- Verification ---------------------------------------------------------------------
def _run_verification(uploaded_file, market: str | None) -> None:
    spinner_msg = (
        "Analizuj\u0119 etykiet\u0119 i sprawdzam trendy rynkowe... "
        "(ok. 60\u201390 sekund)"
        if market
        else "Analizuj\u0119 etykiet\u0119 wzgl\u0119dem FEDIAF... "
        "(ok. 30\u201360 sekund)"
    )

    with st.spinner(spinner_msg):
        try:
            uploaded_file.seek(0)
            label_b64, media_type = file_to_base64(
                uploaded_file.read(), uploaded_file.name
            )
            fediaf_b64 = load_pdf_base64(settings.fediaf_pdf_path)
            result = verify_label(
                label_b64=label_b64,
                media_type=media_type,
                settings=settings,
                client=client,
                fediaf_b64=fediaf_b64,
                market=market,
            )
        except ConfigurationError as e:
            st.error(f"**B\u0142\u0105d konfiguracji:** {e}")
            return
        except ConversionError as e:
            st.error(f"**B\u0142\u0105d pliku:** {e}")
            return
        except FediafVerifierError as e:
            st.error(f"**B\u0142\u0105d API:** {e}")
            return
        except Exception as e:
            st.error(f"**Nieoczekiwany b\u0142\u0105d:** {e}")
            logger.exception("Unexpected error during verification")
            return

    st.session_state.report = result
    st.session_state.report_filename = uploaded_file.name
    st.session_state.report_market = market


if uploaded and st.button(
    "Sprawd\u017a etykiet\u0119", type="primary", use_container_width=True
):
    _run_verification(uploaded, selected_market)


# -- Report rendering -----------------------------------------------------------------
def _render_report(
    report: EnrichedReport, filename: str, market: str | None
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
                    st.markdown(
                        f"{icon} **[{type_label}]** "
                        f'~~{li.original}~~ \u2192 **{li.suggestion}**  \n'
                        f'<span style="opacity:0.6;font-size:0.85rem;">'
                        f"{li.explanation}</span>",
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
            use_container_width=True,
        )
    with col_b:
        st.download_button(
            "\u2b07 Pobierz raport TXT",
            data=to_text(report, filename, market),
            file_name=f"raport_{stem}.txt",
            mime="text/plain",
            use_container_width=True,
        )


# -- Render saved report ---------------------------------------------------------------
if st.session_state.report is not None:
    _render_report(
        st.session_state.report,
        st.session_state.report_filename,
        st.session_state.report_market,
    )
