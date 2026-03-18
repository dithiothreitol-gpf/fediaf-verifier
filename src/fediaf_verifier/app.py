"""Streamlit application — BULT Quality Check."""

import sys
from pathlib import Path

import streamlit as st
from loguru import logger

from fediaf_verifier.config import AppSettings, get_settings
from fediaf_verifier.converter import file_to_base64
from fediaf_verifier.exceptions import (
    ConfigurationError,
    ConversionError,
    FediafVerifierError,
)
from fediaf_verifier.export import to_json, to_text
from fediaf_verifier.models import EnrichedReport, ExtractionConfidence, LinguisticCheckResult
from fediaf_verifier.providers import AIProvider
from fediaf_verifier.verifier import create_providers, verify_label, verify_linguistic_only

# -- Logging setup ---------------------------------------------------------------------
logger.remove()
logger.add(sys.stderr, level="INFO")
Path("logs").mkdir(exist_ok=True)
logger.add("logs/bult_{time}.log", rotation="10 MB", retention="30 days", level="DEBUG")

_FEDIAF_PDF_URL = (
    "https://europeanpetfood.org/wp-content/uploads/2025/09/"
    "FEDIAF-Nutritional-Guidelines_2025-ONLINE.pdf"
)


def _download_fediaf_pdf(pdf_path: Path) -> None:
    """Auto-download FEDIAF Guidelines PDF if missing."""
    import urllib.request

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with st.spinner("Pobieram FEDIAF Nutritional Guidelines..."):
            urllib.request.urlretrieve(_FEDIAF_PDF_URL, pdf_path)
            logger.info("FEDIAF PDF downloaded to {}", pdf_path)
    except Exception as e:
        logger.error("Failed to download FEDIAF PDF: {}", e)
        st.warning(
            f"Nie uda\u0142o si\u0119 pobra\u0107 automatycznie: {e}\n\n"
            "Pobierz r\u0119cznie z europeanpetfood.org i umie\u015b\u0107 w data/."
        )


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
        "Sprawdz plik `.env` \u2014 wymagany klucz API dla wybranego providera."
    )
    st.stop()


@st.cache_resource
def _init_providers(
    _settings: AppSettings,
) -> tuple[AIProvider, AIProvider]:
    return create_providers(_settings)


extraction_provider, secondary_provider = _init_providers(settings)

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

_MODE_FULL = "Pe\u0142na weryfikacja"
_MODE_LINGUISTIC = "Tylko weryfikacja j\u0119zykowa"

with st.sidebar:
    st.header("Parametry weryfikacji")

    verification_mode = st.selectbox(
        "Tryb weryfikacji",
        [_MODE_FULL, _MODE_LINGUISTIC],
        help=(
            "Pe\u0142na \u2014 analiza sk\u0142adu, FEDIAF, EU, opakowania + j\u0119zyk.\n"
            "J\u0119zykowa \u2014 szybka kontrola ortografii i gramatyki."
        ),
    )
    is_linguistic_only = verification_mode == _MODE_LINGUISTIC

    if is_linguistic_only:
        selected_market = None
    else:
        market_selection = st.selectbox(
            "Rynek docelowy",
            options=MARKETS,
            help=(
                "Opcjonalne. Dodaj kraj, a raport uwzgl\u0119dni aktualne "
                "trendy rynkowe dla tej kategorii produktu."
            ),
        )
        selected_market = (
            None if market_selection == MARKETS[0] else market_selection
        )

    if is_linguistic_only:
        st.caption(
            "Tryb j\u0119zykowy \u2014 szybka kontrola "
            "ortografii, gramatyki i diakrytyk\u00f3w."
        )
    elif selected_market:
        st.info(f"Rynek docelowy: **{selected_market}**")
    else:
        st.caption("Weryfikacja obejmie wy\u0142\u0105cznie FEDIAF i regulacje EU.")

    if not is_linguistic_only:
        st.divider()

        pdf_path = settings.fediaf_pdf_path
        if not pdf_path.is_file():
            _download_fediaf_pdf(pdf_path)

        if pdf_path.is_file():
            size_mb = pdf_path.stat().st_size / 1_048_576
            st.success(f"FEDIAF Guidelines ({size_mb:.1f} MB) \u2713")
        else:
            st.error("Nie uda\u0142o si\u0119 pobra\u0107 FEDIAF Guidelines.")
            st.stop()

    st.divider()
    st.subheader("\U0001f4d6 Podr\u0119cznik u\u017cytkownika")

    with st.expander("Jak zacz\u0105\u0107?"):
        st.markdown("""\
1. **Wgraj etykiet\u0119** \u2014 przeci\u0105gnij plik lub kliknij przycisk uploadu
2. **Wybierz rynek** \u2014 opcjonalnie, je\u015bli chcesz analiz\u0119 trend\u00f3w
3. **Kliknij "Sprawd\u017a etykiet\u0119"** \u2014 analiza trwa 30\u201390 sekund
4. **Przejrzyj raport** \u2014 przewi\u0144 w d\u00f3\u0142 po zako\u0144czeniu
5. **Pobierz raport** \u2014 JSON (do systemu) lub TXT (do wydruku)
""")

    with st.expander("Obs\u0142ugiwane formaty plik\u00f3w"):
        st.markdown("""\
| Format | Opis |
|--------|------|
| **JPG / PNG** | Zdj\u0119cie etykiety (najlepiej ca\u0142a etykieta, dobra ostro\u015b\u0107) |
| **PDF** | Wielostronicowa specyfikacja \u2014 system znajdzie sekcj\u0119 z etykiet\u0105 |
| **DOCX** | Dokument Word (wymaga LibreOffice do konwersji) |

**Wskaz\u00f3wki:**
- Im lepsza jako\u015b\u0107 zdj\u0119cia, tym wy\u017csza pewno\u015b\u0107 odczytu
- Upewnij si\u0119, \u017ce tabela analityczna jest czytelna
- Wielostronicowe PDF \u2014 system analizuje pierwszy produkt
""")

    with st.expander("Co oznaczaj\u0105 sekcje raportu?"):
        st.markdown("""\
**\u2705 Status i wynik zgodno\u015bci**
- **90\u2013100 pkt** \u2014 pe\u0142na zgodno\u015b\u0107, produkt gotowy
- **70\u201389 pkt** \u2014 drobne uwagi, dopuszczalny z zaleceniami
- **50\u201369 pkt** \u2014 istotne braki, wymaga korekty
- **0\u201349 pkt** \u2014 krytyczne niezgodno\u015bci

**\U0001f7e2\U0001f7e1\U0001f534 Pewno\u015b\u0107 odczytu**
- **Wysoka** \u2014 wszystkie warto\u015bci wyra\u017anie czytelne
- **\u015arednia** \u2014 1\u20132 pozycje budz\u0105 w\u0105tpliwo\u015bci
- **Niska** \u2014 znaczna cz\u0119\u015b\u0107 nieczytelna \u2014 wymagana weryfikacja

**Weryfikacja krzy\u017cowa**
Niezale\u017cny, drugi odczyt warto\u015bci liczbowych. \
Je\u015bli r\u00f3\u017cnica > 0.5%, system flaguje rozbie\u017cno\u015b\u0107.

**Weryfikacja j\u0119zykowa**
Sprawdzenie ortografii, gramatyki, znak\u00f3w diakrytycznych \
i sp\u00f3jno\u015bci terminologii na etykiecie.

**Regu\u0142y deterministyczne FEDIAF**
Progi zakodowane w Pythonie \u2014 dzia\u0142aj\u0105 niezale\u017cnie od AI. \
Nawet je\u015bli model si\u0119 pomyli, ta warstwa wy\u0142apie naruszenia.

**Wymagania EU (Rozp. 767/2009)**
6 obowi\u0105zkowych element\u00f3w etykiety: lista sk\u0142adnik\u00f3w, \
sk\u0142adniki analityczne, producent, masa netto, gatunek, partia/data.

**Kontrola opakowania**
Rozszerzona checklista: dawkowanie, przechowywanie, claimy vs sk\u0142ad, \
oznaczenia recyklingu, kody kreskowe, nr zak\u0142adu, GMO i wi\u0119cej.
""")

    with st.expander("Kiedy konsultowa\u0107 z ekspertem?"):
        st.markdown("""\
System automatycznie oznacza raport jako **wymagaj\u0105cy przegl\u0105du** gdy:

- \u26d4 Wynik < 60 punkt\u00f3w
- \U0001f534 Pewno\u015b\u0107 odczytu = Niska
- \u26a0\ufe0f Status = "Do sprawdzenia"
- \u274c Rozbie\u017cno\u015b\u0107 mi\u0119dzy odczytami > 0.5%
- \u26a0\ufe0f 2+ ostrze\u017cenia o rzetelno\u015bci

**Zawsze konsultuj z ekspertem je\u015bli:**
- Produkt przeznaczony na nowy rynek eksportowy
- Etykieta zawiera claimy funkcjonalne (np. "skin & coat")
- Produkt dietetyczny (PARNUT) \u2014 dodatkowe wymagania
- Masz w\u0105tpliwo\u015bci co do jako\u015bci zdj\u0119cia/dokumentu
""")

    with st.expander("S\u0142ownik poj\u0119\u0107"):
        st.markdown("""\
| Poj\u0119cie | Znaczenie |
|---------|-----------|
| **FEDIAF** | Europejska Federacja Przemys\u0142u Karm \u2014 wytyczne \u017cywieniowe |
| **Rozp. 767/2009** | G\u0142\u00f3wna regulacja UE dot. etykietowania karm |
| **DM (sucha masa)** | Warto\u015b\u0107 bez wilgotno\u015bci \u2014 do por\u00f3wna\u0144 |
| **As-fed** | Warto\u015b\u0107 "tak jak podano" \u2014 z uwzgl\u0119dnieniem wilgotno\u015bci |
| **Ca:P** | Stosunek wapnia do fosforu \u2014 krytyczny dla zdrowia ko\u015bci |
| **PARNUT** | Karma dietetyczna o szczeg\u00f3lnym przeznaczeniu \u017cywieniowym |
| **Tauryna** | Aminokwas niezb\u0119dny dla kot\u00f3w \u2014 minimum 0.1% DM |
| **Compliance score** | Wynik zgodno\u015bci 0\u2013100 obliczany automatycznie |
| **Cross-check** | Niezale\u017cny drugi odczyt warto\u015bci z etykiety |
| **Symbol \u2117** | Znak metrologiczny przy masie netto (wymag. prawne) |
| **Art.19** | Obowi\u0105zek podania kontaktu do info o dodatkach |
""")

    with st.expander("Jak dzia\u0142a system?"):
        st.markdown("""\
**3 warstwy weryfikacji:**

**1. Ekstrakcja danych**
System odczytuje z etykiety: sk\u0142ad, warto\u015bci od\u017cywcze, \
claimy, elementy widoczne na opakowaniu.

**2. Analiza zgodno\u015bci**
Wyekstrahowane dane s\u0105 weryfikowane wzgl\u0119dem:
- Prog\u00f3w FEDIAF 2021 (min/max sk\u0142adnik\u00f3w od\u017cywczych)
- Wymaga\u0144 EU 767/2009 (obowi\u0105zkowe elementy etykiety)
- Checklisty opakowania (30 punkt\u00f3w kontrolnych)
- Sp\u00f3jno\u015bci claim\u00f3w ze sk\u0142adem

**3. Niezale\u017cna weryfikacja**
Drugi, niezale\u017cny odczyt warto\u015bci liczbowych \
+ sprawdzenie j\u0119zykowe etykiety.

**Wynik:** powtarzalny compliance score obliczany \
na podstawie twardych regu\u0142, nie interpretacji.

*Narz\u0119dzie wspomagaj\u0105ce prac\u0119 dzia\u0142u jako\u015bci.*
""")

    with st.expander("FAQ"):
        st.markdown("""\
**Ile trwa analiza?**
30\u201360 sekund bez trend\u00f3w, 60\u201390 z trendami rynkowymi.

**Czy system zast\u0119puje eksperta?**
Nie. Eliminuje 80\u201390% rutynowej pracy. Przypadki graniczne \
zawsze eskaluje do cz\u0142owieka.

**Co je\u015bli zdj\u0119cie jest z\u0142ej jako\u015bci?**
System oznaczy pewno\u015b\u0107 jako "Niska" i zaleci weryfikacj\u0119 \
z orygina\u0142em. Spr\u00f3buj lepszego zdj\u0119cia.

**Jak dzia\u0142a cross-check?**
Niezale\u017cny, drugi odczyt pobiera TYLKO liczby z tabeli analitycznej. \
Je\u015bli r\u00f3\u017cni\u0105 si\u0119 od g\u0142\u00f3wnego odczytu > 0.5%, system flaguje.

**Czy dane s\u0105 przechowywane?**
Nie. Analiza odbywa si\u0119 w pami\u0119ci. Po zamkni\u0119ciu przegl\u0105darki \
dane znikaj\u0105. Raporty s\u0105 zapisywane tylko je\u015bli je pobierzesz.

**Co je\u015bli wyst\u0105pi b\u0142\u0105d "Rate limit"?**
System automatycznie ponawia pr\u00f3b\u0119 po 15\u201360 sekundach. \
Przy cz\u0119stych b\u0142\u0119dach \u2014 odczekaj minut\u0119 mi\u0119dzy analizami.
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
        if is_linguistic_only:
            st.markdown("**Tryb:** weryfikacja j\u0119zykowa")
            st.caption("Szybka analiza tekstu \u2014 ok. 10\u201320 sekund.")
        else:
            st.markdown(f"**Rynek:** {selected_market or 'nie wybrano'}")
            if selected_market:
                st.caption(
                    "Analiza z wyszukiwaniem trend\u00f3w "
                    "\u2014 ok. 60\u201390 sekund."
                )
            else:
                st.caption(
                    "Analiza bez trend\u00f3w \u2014 ok. 30\u201360 sekund."
                )


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
            result = verify_label(
                label_b64=label_b64,
                media_type=media_type,
                settings=settings,
                extraction_provider=extraction_provider,
                secondary_provider=secondary_provider,
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


def _run_linguistic_only(uploaded_file) -> None:
    with st.spinner(
        "Sprawdzam j\u0119zyk etykiety... (ok. 10\u201320 sekund)"
    ):
        try:
            uploaded_file.seek(0)
            label_b64, media_type = file_to_base64(
                uploaded_file.read(), uploaded_file.name
            )
            result = verify_linguistic_only(
                label_b64=label_b64,
                media_type=media_type,
                provider=secondary_provider,
                settings=settings,
            )
        except ConversionError as e:
            st.error(f"**B\u0142\u0105d pliku:** {e}")
            return
        except FediafVerifierError as e:
            st.error(f"**B\u0142\u0105d API:** {e}")
            return
        except Exception as e:
            st.error(f"**Nieoczekiwany b\u0142\u0105d:** {e}")
            logger.exception("Unexpected error during linguistic check")
            return

    st.session_state.report = result
    st.session_state.report_filename = uploaded_file.name
    st.session_state.report_market = None


if uploaded and is_linguistic_only and st.button(
    "Sprawd\u017a j\u0119zyk", type="primary", use_container_width=True
):
    _run_linguistic_only(uploaded)

if uploaded and not is_linguistic_only and st.button(
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


# -- Render linguistic-only report ----------------------------------------------------
def _render_linguistic_report(
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
        for li in lr.issues:
            icon = _ISSUE_ICONS.get(li.issue_type, "\u2022")
            label = _ISSUE_LABELS.get(li.issue_type, li.issue_type)
            st.markdown(
                f"{icon} **[{label}]** "
                f"~~{li.original}~~ \u2192 **{li.suggestion}**  \n"
                f'<span style="opacity:0.6;font-size:0.85rem;">'
                f"{li.explanation}</span>",
                unsafe_allow_html=True,
            )
    else:
        st.success(
            "Tekst na etykiecie bez b\u0142\u0119d\u00f3w "
            "\u2014 profesjonalna jako\u015b\u0107."
        )

    # Export
    from fediaf_verifier.export import linguistic_to_text

    st.divider()
    txt = linguistic_to_text(result, filename)
    stem = Path(filename).stem
    st.download_button(
        "\u2b07\ufe0f Pobierz raport j\u0119zykowy (TXT)",
        data=txt,
        file_name=f"jezyk_{stem}.txt",
        mime="text/plain",
        use_container_width=True,
    )


# -- Render saved report ---------------------------------------------------------------
if st.session_state.report is not None:
    report = st.session_state.report
    if isinstance(report, LinguisticCheckResult):
        _render_linguistic_report(
            report,
            st.session_state.report_filename,
        )
    else:
        _render_report(
            report,
            st.session_state.report_filename,
            st.session_state.report_market,
        )
