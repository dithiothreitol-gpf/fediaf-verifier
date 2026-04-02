"""Streamlit application — BULT Quality Assurance."""

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
from fediaf_verifier.providers import AIProvider
from fediaf_verifier.verifier import (
    create_providers,
    generate_label_text,
    generate_product_description,
    verify_artwork_inspection,
    verify_claims,
    verify_design_analysis,
    verify_ean,
    verify_label,
    verify_label_diff,
    verify_label_structure,
    verify_linguistic_only,
    verify_market_compliance,
    verify_presentation,
    verify_translation,
)

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
    page_title="BULT Quality Assurance",
    page_icon="\U0001f43e",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(_CUSTOM_CSS, unsafe_allow_html=True)

st.title("\U0001f43e BULT Quality Assurance")
st.caption(
    "Weryfikacja etykiet, inspekcja artwork\u00f3w, kontrola claim\u00f3w, "
    "spellcheck, t\u0142umaczenia i generowanie tekst\u00f3w \u2014 "
    "wszystko czego potrzebuje Tw\u00f3j produkt, zanim trafi na p\u00f3\u0142k\u0119."
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
if "structure_file_bytes" not in st.session_state:
    st.session_state.structure_file_bytes = None
if "structure_media_type" not in st.session_state:
    st.session_state.structure_media_type = ""
if "report_old_filename" not in st.session_state:
    st.session_state.report_old_filename = ""
if "report_new_filename" not in st.session_state:
    st.session_state.report_new_filename = ""
if "report_artwork_proof" not in st.session_state:
    st.session_state.report_artwork_proof = ""

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

_MODE_FULL = "\U0001f50d Pe\u0142na weryfikacja"
_MODE_LINGUISTIC = "\U0001f4dd Weryfikacja j\u0119zykowa"
_MODE_STRUCTURE = "\U0001f524 Kontrola struktury i czcionki"
_MODE_TRANSLATION = "\U0001f310 T\u0142umaczenie etykiety"
_MODE_DESIGN = "\U0001f3a8 Analiza projektu graficznego"
_MODE_EAN = "\U0001f4e6 Walidator EAN/kod\u00f3w"
_MODE_CLAIMS = "\u2713 Walidator claim\u00f3w"
_MODE_PRESENTATION = "\U0001f3f7\ufe0f Weryfikator nazw i zastrze\u017ce\u0144"
_MODE_MARKET = "\U0001f30d Walidator rynkowy"
_MODE_LABEL_TEXT = "\U0001f4dd Generator tekstu etykiety"
_MODE_DIFF = "\U0001f504 Por\u00f3wnanie wersji"
_MODE_PRODUCT_DESC = "\U0001f4dd Generator opis\u00f3w produkt\u00f3w"
_MODE_ARTWORK = "\U0001f50d Inspekcja artwork"
_MODE_PACKAGING = "\U0001f4e6 Packaging Designer"
_MODE_CATALOG_TRANSLATION = "\U0001f4d1 T\u0142umaczenie katalogu"

_TRANSLATION_LANGUAGES = {
    "en": "English",
    "de": "Deutsch",
    "fr": "Fran\u00e7ais",
    "cs": "\u010ce\u0161tina",
    "hu": "Magyar",
    "ro": "Rom\u00e2n\u0103",
    "it": "Italiano",
    "es": "Espa\u00f1ol",
    "nl": "Nederlands",
    "sk": "Sloven\u010dina",
    "bg": "\u0411\u044a\u043b\u0433\u0430\u0440\u0441\u043a\u0438",
    "hr": "Hrvatski",
    "pt": "Portugu\u00eas",
    "pl": "Polski",
}

with st.sidebar:
    # -- Two-level mode selector: segmented control + selectbox --
    _GROUP_VERIFY = "\U0001f50d Weryfikacja"
    _GROUP_TOOLS = "\U0001f527 Narz\u0119dzia"
    _GROUP_DESIGN = "\U0001f3a8 Design"
    _GROUP_PACKAGING = "\U0001f4e6 Packaging"

    st.header("\U0001f43e BULT QA")
    _mode_group = st.segmented_control(
        "Kategoria",
        [_GROUP_VERIFY, _GROUP_TOOLS, _GROUP_DESIGN, _GROUP_PACKAGING],
        default=_GROUP_VERIFY,
        label_visibility="collapsed",
    )
    # segmented_control can return None if nothing selected
    if _mode_group is None:
        _mode_group = _GROUP_VERIFY

    if _mode_group == _GROUP_VERIFY:
        verification_mode = st.selectbox(
            "Tryb",
            [_MODE_FULL, _MODE_LINGUISTIC, _MODE_STRUCTURE, _MODE_CLAIMS, _MODE_PRESENTATION, _MODE_MARKET, _MODE_ARTWORK],
            label_visibility="collapsed",
        )
    elif _mode_group == _GROUP_TOOLS:
        verification_mode = st.selectbox(
            "Narz\u0119dzie",
            [_MODE_TRANSLATION, _MODE_CATALOG_TRANSLATION, _MODE_LABEL_TEXT, _MODE_PRODUCT_DESC, _MODE_DIFF, _MODE_EAN],
            label_visibility="collapsed",
        )
    elif _mode_group == _GROUP_PACKAGING:
        verification_mode = _MODE_PACKAGING
        st.caption("Koncept AI \u2192 roboczy plik DTP (Illustrator/InDesign)")
    else:
        verification_mode = _MODE_DESIGN
        st.caption("Ocena designu etykiety z rekomendacjami dla R&D")

    is_linguistic_only = verification_mode == _MODE_LINGUISTIC
    is_structure_check = verification_mode == _MODE_STRUCTURE
    is_translation = verification_mode == _MODE_TRANSLATION
    is_design_analysis = verification_mode == _MODE_DESIGN
    is_ean_check = verification_mode == _MODE_EAN
    is_claims_check = verification_mode == _MODE_CLAIMS
    is_presentation_check = verification_mode == _MODE_PRESENTATION
    is_market_check = verification_mode == _MODE_MARKET
    is_label_text_gen = verification_mode == _MODE_LABEL_TEXT
    is_diff_check = verification_mode == _MODE_DIFF
    is_product_desc = verification_mode == _MODE_PRODUCT_DESC
    is_artwork_check = verification_mode == _MODE_ARTWORK
    is_packaging_designer = verification_mode == _MODE_PACKAGING
    is_catalog_translation = verification_mode == _MODE_CATALOG_TRANSLATION

    # -- Mode-specific options --
    st.divider()

    selected_market = None
    _translation_target_lang = ""
    _translation_target_name = ""
    _translation_notes = ""
    _market_target_code = ""
    _market_target_name = ""
    _pd_input_mode = "manual"
    _pd_tone = "standard"
    _pd_target_lang = "en"
    _pd_target_name = "English"

    if is_market_check:
        from fediaf_verifier.market_rules import MARKET_RULES as _MR
        st.subheader("Rynek docelowy")
        _market_display = [
            f"{v['name']} ({k})" for k, v in _MR.items()
        ]
        _market_selection = st.selectbox("Kraj", _market_display)
        _market_idx = _market_display.index(_market_selection)
        _market_codes = list(_MR.keys())
        _market_target_code = _market_codes[_market_idx]
        _market_target_name = list(_MR.values())[_market_idx]["name"]

    elif is_translation:
        st.subheader("Opcje t\u0142umaczenia")
        _tl_display = [
            f"{name} ({code})"
            for code, name in _TRANSLATION_LANGUAGES.items()
        ]
        _tl_selection = st.selectbox("J\u0119zyk docelowy", _tl_display)
        _tl_idx = _tl_display.index(_tl_selection)
        _tl_codes = list(_TRANSLATION_LANGUAGES.keys())
        _translation_target_lang = _tl_codes[_tl_idx]
        _translation_target_name = list(_TRANSLATION_LANGUAGES.values())[_tl_idx]

        _translation_notes = st.text_area(
            "Dodatkowe uwagi",
            max_chars=500,
            height=80,
            placeholder="np. u\u017cywaj terminologii weterynaryjnej, "
            "zachowaj styl formalny...",
        )

    elif is_catalog_translation:
        st.subheader("Opcje t\u0142umaczenia katalogu")
        _ct_tl_display = [
            f"{name} ({code})"
            for code, name in _TRANSLATION_LANGUAGES.items()
        ]
        _ct_tl_selection = st.selectbox("J\u0119zyk docelowy", _ct_tl_display, key="ct_lang")
        _ct_tl_idx = _ct_tl_display.index(_ct_tl_selection)
        _ct_tl_codes = list(_TRANSLATION_LANGUAGES.keys())
        _ct_target_lang = _ct_tl_codes[_ct_tl_idx]
        _ct_target_name = list(_TRANSLATION_LANGUAGES.values())[_ct_tl_idx]

        st.divider()

        _ct_glossary_file = st.file_uploader(
            "S\u0142ownik terminologii (opcjonalnie)",
            type=["json"],
            help="Plik JSON ze s\u0142ownikiem. Domy\u015blnie: pet_food_{lang}.json",
            key="ct_glossary",
        )

        _ct_page_range = st.text_input(
            "Zakres stron",
            value="all",
            help='np. "all", "1-10", "1,3,5-8"',
            key="ct_pages",
        )

        _ct_dry_run = st.checkbox(
            "Dry run (tylko ekstrakcja)",
            value=False,
            key="ct_dry",
        )

        _ct_validate = st.checkbox("Walidacja po t\u0142umaczeniu", value=True, key="ct_val")

    elif is_product_desc:
        st.subheader("Opcje opisu produktu")
        _pd_input_mode = st.radio(
            "Tryb wprowadzania",
            ["manual", "image"],
            format_func=lambda x: {
                "manual": "R\u0119czne dane",
                "image": "Z etykiety (obraz/PDF)",
            }[x],
            horizontal=True,
        )
        _pd_tone = st.selectbox(
            "Styl opisu",
            ["premium", "scientific", "natural", "standard"],
            format_func=lambda x: {
                "premium": "Premium / Luksusowy",
                "scientific": "Naukowy / Weterynaryjny",
                "natural": "Naturalny / Wholesome",
                "standard": "Standardowy / Neutralny",
            }[x],
        )
        _pd_lang_display = [
            f"{name} ({code})"
            for code, name in _TRANSLATION_LANGUAGES.items()
        ]
        _pd_lang_selection = st.selectbox(
            "J\u0119zyk opisu", _pd_lang_display, key="pd_lang"
        )
        _pd_lang_idx = _pd_lang_display.index(_pd_lang_selection)
        _pd_lang_codes = list(_TRANSLATION_LANGUAGES.keys())
        _pd_target_lang = _pd_lang_codes[_pd_lang_idx]
        _pd_target_name = list(_TRANSLATION_LANGUAGES.values())[_pd_lang_idx]

    elif not is_linguistic_only and not is_structure_check and not is_design_analysis and not is_ean_check and not is_claims_check and not is_presentation_check and not is_market_check and not is_label_text_gen and not is_diff_check and not is_product_desc and not is_artwork_check and not is_packaging_designer and not is_catalog_translation:
        # Full verification mode — market selector
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

    if not is_linguistic_only and not is_structure_check and not is_translation and not is_design_analysis and not is_ean_check and not is_claims_check and not is_presentation_check and not is_market_check and not is_label_text_gen and not is_diff_check and not is_product_desc and not is_artwork_check and not is_packaging_designer and not is_catalog_translation:
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

    if is_packaging_designer or is_catalog_translation:
        pass  # These modes render their own complete sidebar/UI
    else:
      st.divider()
      st.subheader("\U0001f4d6 Podr\u0119cznik u\u017cytkownika")

      # -- "Jak zacz\u0105\u0107?" — depends on mode --
      with st.expander("Jak zacz\u0105\u0107?"):
        if is_translation:
            st.markdown("""\
1. **Wgraj etykiet\u0119** (JPG/PNG/PDF) lub **wklej tekst** (max 2000 znak\u00f3w)
2. **Wybierz j\u0119zyk docelowy** w panelu bocznym
3. Opcjonalnie dodaj **uwagi** (np. "u\u017cywaj terminologii weterynaryjnej")
4. **Kliknij "Przet\u0142umacz"** \u2014 analiza trwa 20\u201340 sekund
5. **Przejrzyj t\u0142umaczenie** \u2014 orygina\u0142 i t\u0142umaczenie obok siebie
6. **Pobierz raport TXT** \u2014 do przekazania grafikowi lub korektorowi
""")
        elif is_design_analysis:
            st.markdown("""\
1. **Wgraj etykiet\u0119** \u2014 JPG, PNG lub PDF (najlepiej gotowy projekt)
2. **Kliknij "Analizuj design"** \u2014 analiza trwa 30\u201360 sekund
3. **Przejrzyj raport** \u2014 10 kategorii z ocenami, problemy, rekomendacje
4. **Pobierz raport** \u2014 TXT (do wydruku) lub JSON (do systemu)
5. **Przekaz do R&D** \u2014 sekcja "Podsumowanie dla R&D" z konkretnymi akcjami
""")
        elif is_structure_check:
            st.markdown("""\
1. **Wgraj etykiet\u0119** \u2014 JPG, PNG lub PDF (eksport z Illustratora)
2. **Kliknij "Sprawd\u017a struktur\u0119"** \u2014 analiza trwa 15\u201330 sekund
3. **Przejrzyj raport** \u2014 sekcje j\u0119zykowe, markery, problemy z czcionk\u0105
4. **Pobierz wyniki:**
   - **Raport TXT** \u2014 tekstowe podsumowanie do wydruku
   - **Skrypt .jsx** \u2014 otw\u00f3rz etykiet\u0119 w Illustratorze, \
potem File > Scripts > Other Script > wybierz plik. \
System doda warstw\u0119 "QC Annotations" z kolorowymi oznaczeniami
   - **Etykieta z oznaczeniami** \u2014 kopia PDF/PNG z naniesionymi \
prostok\u0105tami (dost\u0119pna dla plik\u00f3w PDF i obraz\u00f3w)
""")
        elif is_linguistic_only:
            st.markdown("""\
1. **Wgraj etykiet\u0119** \u2014 JPG, PNG, PDF lub DOCX
2. **Kliknij "Sprawd\u017a j\u0119zyk"** \u2014 analiza trwa 10\u201320 sekund
3. **Przejrzyj wynik** \u2014 lista b\u0142\u0119d\u00f3w z sugestiami poprawek
4. **Pobierz raport TXT** \u2014 do wydruku lub przekazania grafikowi
""")
        elif is_product_desc:
            st.markdown("""\
1. **Wybierz tryb** \u2014 "R\u0119czne dane" (formularz) lub "Z etykiety" (obraz/PDF)
2. **Ustaw styl i j\u0119zyk** \u2014 Premium, Naukowy, Naturalny lub Standardowy
3. **Wprowad\u017a dane / wgraj etykiet\u0119**
4. **Kliknij "Generuj opis"** \u2014 generacja trwa 30\u201360 sekund
5. **Przejrzyj wynik** \u2014 pe\u0142ny opis, kr\u00f3tki opis, bullet points, SEO, HTML
6. **Pobierz** \u2014 TXT, HTML lub JSON
""")
        elif is_claims_check:
            st.markdown("""\
1. **Wgraj etykiet\u0119** \u2014 JPG, PNG, PDF lub DOCX
2. **Kliknij "Sprawd\u017a claimy"** \u2014 analiza trwa 15\u201330 sekund
3. **Przejrzyj raport** \u2014 ka\u017cdy claim oceniony pod k\u0105tem sp\u00f3jno\u015bci ze sk\u0142adem
4. **Sprawd\u017a regu\u0142y %** \u2014 walidacja nazewnictwa wg EU 767/2009
5. **Pobierz raport TXT** \u2014 do wydruku lub przekazania dzia\u0142owi jako\u015bci
""")
        elif is_presentation_check:
            st.markdown("""\
1. **Wgraj etykiet\u0119** \u2014 JPG, PNG, PDF lub DOCX
2. **Kliknij "Sprawd\u017a prezentacj\u0119 handlow\u0105"** \u2014 analiza trwa 20\u201340 sekund
3. **Przejrzyj 4 sekcje:**
   - **Receptury** \u2014 czy claimy o recepturze s\u0105 uzasadnione
   - **Nazwy** \u2014 regu\u0142y % (EU 767/2009 Art.17) i sp\u00f3jno\u015b\u0107 nazwy
   - **Marka** \u2014 czy brand nie zawiera zabronionych termin\u00f3w
   - **Zastrze\u017cenia** \u2014 potencjalne naruszenia znak\u00f3w towarowych
4. **Pobierz raport TXT** \u2014 do wydruku lub przekazania dzia\u0142owi prawnemu
""")
        elif is_market_check:
            st.markdown("""\
1. **Wgraj etykiet\u0119** \u2014 JPG, PNG, PDF lub DOCX
2. **Wybierz rynek docelowy** w panelu bocznym
3. **Kliknij "Sprawd\u017a zgodno\u015b\u0107 rynkow\u0105"** \u2014 analiza trwa 20\u201340 sekund
4. **Przejrzyj raport** \u2014 wymogi regulacyjne dla wybranego kraju
5. **Pobierz raport TXT** \u2014 do wydruku lub przekazania dzia\u0142owi jako\u015bci
""")
        elif is_artwork_check:
            st.markdown("""\
1. **Wybierz tryb** \u2014 pojedynczy plik lub por\u00f3wnanie master vs proof
2. **Wgraj plik(i)** \u2014 JPG, PNG, PDF lub TIFF
3. **Ustaw czu\u0142o\u015b\u0107** \u2014 suwak threshold (domy\u015blnie 30)
4. **Kliknij "Inspekcja artwork"** \u2014 analiza trwa 10\u201330 sekund
5. **Przejrzyj raport:**
   - **Gotowosc do druku** \u2014 DPI, CMYK, fonty, bleed
   - **Kolory** \u2014 paleta + Delta E (przy porownaniu)
   - **Pixel diff** \u2014 SSIM + mapa roznic (przy porownaniu)
   - **Podsumowanie AI** \u2014 interpretacja wynikow
6. **Pobierz raport** \u2014 TXT lub JSON
""")
        else:
            st.markdown("""\
1. **Wgraj etykiet\u0119** \u2014 przeci\u0105gnij plik lub kliknij przycisk uploadu
2. **Wybierz rynek** \u2014 opcjonalnie, je\u015bli chcesz analiz\u0119 trend\u00f3w
3. **Kliknij "Sprawd\u017a etykiet\u0119"** \u2014 analiza trwa 30\u201390 sekund
4. **Przejrzyj raport** \u2014 przewi\u0144 w d\u00f3\u0142 po zako\u0144czeniu
5. **Pobierz raport** \u2014 JSON (do systemu) lub TXT (do wydruku)
""")

    # -- Formaty plik\u00f3w — shared, with mode-specific tips --
    with st.expander("Obs\u0142ugiwane formaty plik\u00f3w"):
        st.markdown("""\
| Format | Opis |
|--------|------|
| **JPG / PNG** | Zdj\u0119cie etykiety (najlepiej ca\u0142a etykieta, dobra ostro\u015b\u0107) |
| **PDF** | Specyfikacja lub eksport z Illustratora |
| **DOCX** | Dokument Word (wymaga LibreOffice do konwersji) |
""")
        if is_translation:
            st.markdown("""\
**T\u0142umaczenie \u2014 dwa tryby wej\u015bcia:**
- **Plik** \u2014 wgraj obraz lub PDF etykiety
- **Tekst** \u2014 wklej lub wpisz tre\u015b\u0107 (max 2000 znak\u00f3w)
- Je\u015bli wgrasz plik i wpiszesz tekst \u2014 plik ma priorytet
""")
        elif is_design_analysis:
            st.markdown("""\
**Wskaz\u00f3wki:**
- Wgraj gotowy projekt etykiety (nie szkic)
- Im wy\u017csza jako\u015b\u0107 obrazu, tym dok\u0142adniejsza analiza
- Najlepiej: eksport z Illustratora jako PDF lub PNG
""")
        elif is_structure_check:
            st.markdown("""\
**Wskaz\u00f3wki dla kontroli struktury:**
- Eksportuj z Illustratora jako PDF z w\u0142\u0105czon\u0105 \
kompatybilno\u015bci\u0105 PDF (domy\u015blnie w\u0142\u0105czona)
- Im wy\u017csza rozdzielczo\u015b\u0107 eksportu, tym dok\u0142adniejsze wykrywanie
- Upewnij si\u0119, \u017ce wszystkie sekcje j\u0119zykowe s\u0105 widoczne \
na eksportowanym pliku
- Dla plik\u00f3w .ai \u2014 u\u017cyj skryptu .jsx bezpo\u015brednio \
w Illustratorze zamiast eksportu
""")
        elif is_linguistic_only:
            st.markdown("""\
**Wskaz\u00f3wki:**
- Im lepsza jako\u015b\u0107 zdj\u0119cia, tym dok\u0142adniejsze wykrywanie b\u0142\u0119d\u00f3w
- Upewnij si\u0119, \u017ce tekst na etykiecie jest czytelny
""")
        elif is_claims_check or is_presentation_check:
            st.markdown("""\
**Wskaz\u00f3wki:**
- Wgraj pe\u0142n\u0105 etykiet\u0119 \u2014 front i ty\u0142 (je\u015bli to zdj\u0119cie)
- System analizuje nazwy, sk\u0142adniki, claimy i elementy marki
- Im wi\u0119cej tekstu widocznego na etykiecie, tym dok\u0142adniejsza analiza
""")
        else:
            st.markdown("""\
**Wskaz\u00f3wki:**
- Im lepsza jako\u015b\u0107 zdj\u0119cia, tym wy\u017csza pewno\u015b\u0107 odczytu
- Upewnij si\u0119, \u017ce tabela analityczna jest czytelna
- Wielostronicowe PDF \u2014 system analizuje pierwszy produkt
""")

    # -- Sekcje raportu — mode-specific --
    if is_translation:
        with st.expander("Co oznaczaj\u0105 sekcje raportu?"):
            st.markdown("""\
**Sekcje t\u0142umaczenia:**
Ka\u017cda sekcja etykiety (sk\u0142ad, sk\u0142adniki analityczne, dawkowanie, \
producent, claimy, ostrze\u017cenia) jest wy\u015bwietlana obok siebie: \
orygina\u0142 | t\u0142umaczenie.

**Uwagi t\u0142umacza:**
Pod ka\u017cd\u0105 sekcj\u0105 mog\u0105 pojawi\u0107 si\u0119 uwagi \u2014 np. \
alternatywne t\u0142umaczenia, niejednoznaczno\u015bci terminologiczne, \
r\u00f3\u017cnice mi\u0119dzy rynkami.

**Terminologia EU 767/2009:**
System u\u017cywa oficjalnych t\u0142umacze\u0144 termin\u00f3w regulacyjnych \
(np. "sk\u0142adniki analityczne" = "analytical constituents").
""")
    elif is_design_analysis:
        with st.expander("Co oznaczaj\u0105 sekcje raportu?"):
            st.markdown("""\
**Ocena og\u00f3lna (0\u2013100):**
- **80\u2013100** \u2014 doskona\u0142y design, wzorcowy w bran\u017cy
- **60\u201379** \u2014 dobry, spe\u0142nia standardy
- **40\u201359** \u2014 wymaga poprawy
- **0\u201339** \u2014 powa\u017cne problemy

**10 kategorii analizy:**
Hierarchia wizualna, czytelno\u015b\u0107, u\u017cycie koloru, \
kompozycja, elementy obowi\u0105zkowe, wp\u0142yw p\u00f3\u0142kowy, \
fotografia, grupa docelowa, ekologia, uk\u0142ad wieloj\u0119zyczny.

**Problemy** \u2014 z priorytetem:
- \U0001f534 Krytyczny \u2014 wymaga natychmiastowej korekty
- \U0001f7e0 Istotny \u2014 wp\u0142ywa na jako\u015b\u0107
- \U0001f7e1 Drobny \u2014 do rozwa\u017cenia
- \U0001f535 Sugestia \u2014 opcjonalna poprawa

**Benchmark konkurencyjny:**
Por\u00f3wnanie z praktykami bran\u017cy pet food.

**Podsumowanie R&D:**
3\u20135 najwa\u017cniejszych akcji do podj\u0119cia.
""")
    elif is_structure_check:
        with st.expander("Co oznaczaj\u0105 sekcje raportu?"):
            st.markdown("""\
**Status og\u00f3lny**
- **OK** \u2014 brak problem\u00f3w, etykieta gotowa do druku
- **Ostrze\u017cenia** \u2014 wykryto potencjalne problemy do sprawdzenia
- **B\u0142\u0119dy** \u2014 wymagana korekta przed drukiem

**Sekcje j\u0119zykowe**
Dla ka\u017cdej sekcji (PL, DE, EN, FR, CZ...) system sprawdza:
- Czy marker j\u0119zykowy jest widoczny (flaga, kod kraju, ikona)
- Czy tre\u015b\u0107 sekcji jest obecna i kompletna
- Jakie elementy etykiety zawiera (sk\u0142ad, sk\u0142adniki analityczne, \
dawkowanie, przechowywanie, producent, opis, ostrze\u017cenia)
- Jakich element\u00f3w brakuje w por\u00f3wnaniu z innymi sekcjami

**Kompletno\u015b\u0107 diakrytyk\u00f3w**
Sprawdzenie per j\u0119zyk, czy czcionka zawiera wymagane znaki:
- PL: \u0105 \u0119 \u015b \u0107 \u017a \u017c \u0142 \u0144 \u00f3
- DE: \u00e4 \u00f6 \u00fc \u00df
- CZ: \u0159 \u0161 \u010d \u017e \u016f \u011b
- HU, RO, FR, IT, ES \u2014 odpowiednie znaki narodowe

**Problemy strukturalne** (kolorowe oznaczenia):
- \U0001f534 **Krytyczny** \u2014 brak markera, brak ca\u0142ej sekcji
- \U0001f7e1 **Ostrze\u017cenie** \u2014 osierocony tekst, luki, nak\u0142adanie si\u0119
- \U0001f535 **Informacja** \u2014 niesp\u00f3jny porz\u0105dek, duplikat markera

**Problemy z czcionk\u0105/glifami:**
- \u274c **Brak glifa** \u2014 znak nie renderuje si\u0119 wcale
- \U0001f500 **Podmieniony glif** \u2014 znak z innej czcionki zamiast w\u0142a\u015bciwego
- \u2b1c **Puste miejsce** \u2014 luka gdzie powinien by\u0107 znak
- \u25a1 **Kwadracik (tofu)** \u2014 boks zamiast znaku
- \U0001f524 **Z\u0142y diakrytyk** \u2014 np. "a" zamiast "\u0105"
- \u26a0\ufe0f **B\u0142\u0105d enkodowania** \u2014 np. "\u00c4\u0085" zamiast "\u0105"
""")
    elif is_linguistic_only:
        with st.expander("Co oznaczaj\u0105 sekcje raportu?"):
            st.markdown("""\
**Jako\u015b\u0107 tekstu:**
- \u2705 **Doskona\u0142a** \u2014 tekst bez b\u0142\u0119d\u00f3w
- \U0001f535 **Dobra** \u2014 drobne uwagi
- \U0001f7e1 **Do poprawy** \u2014 kilka b\u0142\u0119d\u00f3w wymagaj\u0105cych korekty
- \U0001f534 **S\u0142aba** \u2014 liczne b\u0142\u0119dy, gruntowna korekta

**Typy wykrywanych b\u0142\u0119d\u00f3w:**
- \U0001f4dd **Ortografia** \u2014 liter\u00f3wki, b\u0142\u0119dne zapisy s\u0142\u00f3w
- \U0001f4d6 **Gramatyka** \u2014 b\u0142\u0119dna odmiana, sk\u0142adnia, ko\u0144c\u00f3wki
- \u270f\ufe0f **Interpunkcja** \u2014 brak/nadmiar przecink\u00f3w, kropek
- \U0001f524 **Diakrytyki** \u2014 brakuj\u0105ce \u0105\u0119\u015b\u0107\u017a\u017c\u0142\u0144\u00f3 \
(cz\u0119sty problem z czcionkami)
- \U0001f500 **Terminologia** \u2014 mieszanie j\u0119zyk\u00f3w w jednym bloku \
(np. "bia\u0142ko" obok "protein")

Ka\u017cdy b\u0142\u0105d zawiera: oryginalny tekst, sugestowan\u0105 poprawk\u0119 \
i kr\u00f3tkie wyja\u015bnienie.
""")
    elif is_claims_check:
        with st.expander("Co oznaczaj\u0105 sekcje raportu?"):
            st.markdown("""\
**Status sp\u00f3jno\u015bci:**
- \u2705 **Sp\u00f3jne** \u2014 wszystkie claimy zgodne ze sk\u0142adem
- \u26a0\ufe0f **Niesp\u00f3jno\u015bci** \u2014 wykryto rozbie\u017cno\u015bci
- \u26d4 **Krytyczne** \u2014 wymagana natychmiastowa korekta

**Walidacja claim\u00f3w:**
Ka\u017cdy claim sprawdzany pod k\u0105tem sp\u00f3jno\u015bci ze sk\u0142adem. \
Kategorie: procentowe, grain-free, sk\u0142adnikowe, od\u017cywcze, terapeutyczne.

**Regu\u0142a % w nazwie (EU 767/2009):**
"z X" = min 4%, "bogaty w X" = min 14%, nazwa = X = min 26%.
""")
    elif is_presentation_check:
        with st.expander("Co oznaczaj\u0105 sekcje raportu?"):
            st.markdown("""\
**4 sekcje raportu:**
Ka\u017cda sekcja oceniana osobno 0\u2013100.

**Receptury** \u2014 czy claimy o recepturze (oryginalna, monobia\u0142kowa, \
vet-developed, bez konserwant\u00f3w) s\u0105 uzasadnione sk\u0142adem i regulacjami.

**Nazwy** \u2014 regu\u0142y procentowe EU 767/2009 Art.17 \
(5 prog\u00f3w: 100%/26%/14%/4%/<4%) + sp\u00f3jno\u015b\u0107 nazwy z typem karmy, \
gatunkiem, etapem \u017cycia.

**Marka** \u2014 czy elementy marki nie naruszaj\u0105 regulacji \
(Bio, Vet, Natural, Medical, implikacje geograficzne).

**Zastrze\u017cenia** \u2014 potencjalne naruszenia znak\u00f3w towarowych, \
poprawno\u015b\u0107 symboli \u00ae i \u2122, zbie\u017cno\u015b\u0107 z markami konkurencji.

**Wynik og\u00f3lny** \u2014 \u015brednia wa\u017cona: receptury 25%, nazwy 30%, \
marka 25%, zastrze\u017cenia 20%.
""")
    else:
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

    # -- Jak dzia\u0142a system — mode-specific --
    with st.expander("Jak dzia\u0142a system?"):
        if is_translation:
            st.markdown("""\
**T\u0142umaczenie \u2014 1 wywo\u0142anie AI:**

System przyjmuje obraz etykiety lub wklejony tekst, \
automatycznie wykrywa j\u0119zyk \u017ar\u00f3d\u0142owy, dzieli tre\u015b\u0107 \
na logiczne sekcje i t\u0142umaczy na wybrany j\u0119zyk.

**Terminologia bran\u017cowa:**
System u\u017cywa oficjalnych t\u0142umacze\u0144 termin\u00f3w regulacyjnych \
EU 767/2009 (np. "sk\u0142adniki analityczne", "karma pe\u0142noporcjowa").

**Uwagi u\u017cytkownika:**
Dodatkowe instrukcje (np. styl, terminologia) s\u0105 \
uwzgl\u0119dniane przez AI przy t\u0142umaczeniu.

*Narz\u0119dzie wspomagaj\u0105ce \u2014 nie zast\u0119puje profesjonalnego t\u0142umacza.*
""")
        elif is_design_analysis:
            st.markdown("""\
**Analiza graficzna \u2014 1 wywo\u0142anie AI:**

System analizuje projekt etykiety jako profesjonalista \
od designu opakowan w bran\u017cy pet food.

**10 kategorii oceny:**
Ka\u017cda kategoria oceniana 0\u2013100 z konkretnymi obserwacjami \
i rekomendacjami. Rekomendacje s\u0105 precyzyjne \
(np. "zwi\u0119ksz font z 6pt do 8pt").

**Dla R&D:**
Raport zawiera benchmark konkurencyjny, analiz\u0119 trend\u00f3w \
i podsumowanie wykonawcze z 3\u20135 najwa\u017cniejszymi akcjami.

*Oceny s\u0105 subiektywn\u0105 analiz\u0105 AI, nie audytem certyfikacyjnym.*
""")
        elif is_structure_check:
            st.markdown("""\
**Kontrola struktury i czcionki \u2014 1 wywo\u0142anie AI:**

**1. Analiza sekcji j\u0119zykowych**
System identyfikuje ka\u017cd\u0105 sekcj\u0119 j\u0119zykow\u0105 na etykiecie, \
sprawdza obecno\u015b\u0107 marker\u00f3w (flagi, kody kraj\u00f3w) i por\u00f3wnuje \
zawarto\u015b\u0107 mi\u0119dzy sekcjami \u2014 czy ka\u017cda ma te same elementy.

**2. Weryfikacja czcionki**
Dla ka\u017cdego wykrytego j\u0119zyka system sprawdza, czy u\u017cyta \
czcionka zawiera pe\u0142en komplet znak\u00f3w diakrytycznych. \
Wykrywa puste miejsca, kwadraciki (tofu), podmiany znak\u00f3w \
i b\u0142\u0119dy enkodowania.

**3. Lokalizacja problem\u00f3w**
Ka\u017cdy wykryty problem jest oznaczany wsp\u00f3\u0142rz\u0119dnymi \
na obrazie etykiety, co pozwala na:
- Naniesienie oznacze\u0144 na kopi\u0119 PDF/obrazu
- Wygenerowanie skryptu .jsx dla Illustratora

**Kolory oznacze\u0144 w eksportach:**
- \U0001f534 Czerwony \u2014 problemy krytyczne
- \U0001f7e1 Pomara\u0144czowy \u2014 ostrze\u017cenia
- \U0001f535 Niebieski \u2014 informacje
- \U0001f7e3 Magenta (przerywany) \u2014 problemy z czcionk\u0105
- \U0001f7e2 Zielony (przerywany) \u2014 sekcje j\u0119zykowe bez b\u0142\u0119d\u00f3w
""")
        elif is_linguistic_only:
            st.markdown("""\
**Weryfikacja j\u0119zykowa \u2014 1 wywo\u0142anie AI:**

System automatycznie wykrywa j\u0119zyk(i) na etykiecie, \
a nast\u0119pnie sprawdza ca\u0142y widoczny tekst pod k\u0105tem:

1. **Ortografia** \u2014 liter\u00f3wki, b\u0142\u0119dne zapisy
2. **Diakrytyki** \u2014 brakuj\u0105ce \u0105, \u0119, \u015b, \u0107, \u017a, \u017c, \u0142, \u0144, \u00f3 \
(cz\u0119sty problem gdy czcionka nie ma polskich znak\u00f3w)
3. **Gramatyka** \u2014 odmiana, sk\u0142adnia, ko\u0144c\u00f3wki
4. **Interpunkcja** \u2014 przecinki, kropki, dwukropki
5. **Terminologia** \u2014 sp\u00f3jno\u015b\u0107 nazewnictwa \
(np. nie miesza\u0107 "bia\u0142ko" z "protein" w jednym bloku)

System zwraca maksymalnie 10 najwa\u017cniejszych b\u0142\u0119d\u00f3w \
z konkretnymi sugestiami poprawek.

*Tryb szybki \u2014 bez analizy sk\u0142adu i zgodno\u015bci.*
""")
        elif is_claims_check:
            st.markdown("""\
**Walidacja claim\u00f3w \u2014 1 wywo\u0142anie AI:**

System ekstrahuje z etykiety wszystkie claimy marketingowe \
i list\u0119 sk\u0142adnik\u00f3w z procentami, a nast\u0119pnie sprawdza:

1. Czy claimy procentowe zgadzaj\u0105 si\u0119 ze sk\u0142adem
2. Czy claimy "bez X" nie s\u0105 sprzeczne ze sk\u0142adnikami
3. Czy nazewnictwo spe\u0142nia regu\u0142y % (EU 767/2009)
4. Czy nie ma zabronionych claim\u00f3w terapeutycznych

Wynik poddawany jest samo-weryfikacji (usuwanie fa\u0142szywych alarm\u00f3w).
""")
        elif is_presentation_check:
            st.markdown("""\
**Weryfikacja prezentacji handlowej \u2014 1 wywo\u0142anie AI:**

System analizuje etykiet\u0119 pod k\u0105tem 4 aspekt\u00f3w regulacyjnych:

1. **Receptury** \u2014 weryfikacja claim\u00f3w o recepturze vs sk\u0142ad i dodatki
2. **Nazwy** \u2014 pe\u0142na walidacja EU 767/2009 Art.17 + sp\u00f3jno\u015b\u0107 nazwy
3. **Marka** \u2014 zgodno\u015b\u0107 brandu z EU 2018/848, FEDIAF CoGLP, EU 767/2009 Art.13
4. **Zastrze\u017cenia** \u2014 analiza IP/trademark vs znane marki bran\u017cy pet food

Wynik poddawany jest samo-weryfikacji AI (usuwanie fa\u0142szywych alarm\u00f3w). \
Score obliczany jako \u015brednia wa\u017cona 4 sekcji.
""")
        else:
            st.markdown("""\
**Pe\u0142na weryfikacja \u2014 2 wywo\u0142ania AI + analiza Python:**

**Wywo\u0142anie 1: Ekstrakcja danych**
System odczytuje z etykiety: nazw\u0119 produktu, sk\u0142ad, \
warto\u015bci od\u017cywcze (7 sk\u0142adnik\u00f3w), claimy, elementy opakowania, \
j\u0119zyki. Nie ocenia zgodno\u015bci \u2014 tylko opisuje co widzi.

**Python: Analiza deterministyczna**
Wyekstrahowane dane weryfikowane s\u0105 regu\u0142ami zakodowanymi \
w Pythonie (niezale\u017cnie od AI):
- Progi FEDIAF 2021 (min/max sk\u0142adnik\u00f3w od\u017cywczych)
- 6 wymaga\u0144 EU 767/2009
- 30+ punkt\u00f3w kontrolnych opakowania
- Sp\u00f3jno\u015b\u0107 claim\u00f3w ze sk\u0142adem

**Wywo\u0142anie 2: Weryfikacja krzy\u017cowa + j\u0119zykowa**
Niezale\u017cny, drugi odczyt warto\u015bci z tabeli analitycznej \
(tolerancja rozbie\u017cno\u015bci: 0.5%) oraz sprawdzenie j\u0119zykowe.

**Wynik:** compliance score 0\u2013100 obliczany na podstawie \
twardych regu\u0142, nie interpretacji AI.
""")

    # -- Kiedy konsultowa\u0107 z ekspertem — mode-specific --
    if is_translation:
        with st.expander("Kiedy konsultowa\u0107 z t\u0142umaczem?"):
            st.markdown("""\
**Zawsze zweryfikuj z t\u0142umaczem gdy:**
- Etykieta docelowa na nowy rynek eksportowy
- Terminologia bran\u017cowa specyficzna dla danego kraju
- T\u0142umaczenie claim\u00f3w funkcjonalnych (np. "skin & coat")
- Tekst regulacyjny (PARNUT, claimy zdrowotne)

**T\u0142umaczenie AI to propozycja:**
Dobre jako punkt wyj\u015bcia, ale t\u0142umacz powinien \
zweryfikowa\u0107 poprawno\u015b\u0107 terminologiczn\u0105 i stylistyczn\u0105 \
w kontek\u015bcie rynku docelowego.
""")
    elif is_design_analysis:
        with st.expander("Jak wykorzysta\u0107 raport w R&D?"):
            st.markdown("""\
**Priorytety dzia\u0142a\u0144:**
1. Problemy krytyczne i istotne \u2014 natychmiast
2. Rekomendacje z "Podsumowania R&D" \u2014 w kolejnej iteracji
3. Sugestie i drobne \u2014 przy okazji redesignu

**Benchmark konkurencyjny:**
U\u017cyj do argumentacji zmian przed zarz\u0105dem \u2014 \
"konkurencja robi X, my powinni\u015bmy Y".

**Oceny s\u0105 orientacyjne:**
AI analizuje obraz, nie zna kontekstu marki, bud\u017cetu \
ani strategii. Traktuj jako input, nie werdykt.
""")
    elif is_structure_check:
        with st.expander("Kiedy konsultowa\u0107 z grafikiem?"):
            st.markdown("""\
**Natychmiast przekazuj do korekty gdy:**
- Status raportu: "B\u0142\u0119dy"
- Brak markera j\u0119zykowego przy jakiejkolwiek sekcji
- Wykryto osierocony tekst mi\u0119dzy sekcjami
- Problemy z czcionk\u0105 (brakuj\u0105ce glify, kwadraciki)

**Przed drukiem zweryfikuj gdy:**
- Status: "Ostrze\u017cenia"
- Niesp\u00f3jny porz\u0105dek element\u00f3w mi\u0119dzy sekcjami
- Diakrytyki oznaczone jako "PROBLEM" dla kt\u00f3rego\u015b j\u0119zyka

**Jak u\u017cy\u0107 skryptu .jsx:**
1. Otw\u00f3rz oryginalny plik .ai w Illustratorze
2. File > Scripts > Other Script...
3. Wybierz pobrany plik .jsx
4. System doda zablokowana warstw\u0119 "QC Annotations"
5. Przejrzyj oznaczenia, popraw b\u0142\u0119dy
6. Usu\u0144 lub ukryj warstw\u0119 QC przed eksportem
""")
    elif is_linguistic_only:
        with st.expander("Kiedy konsultowa\u0107 z korektorem?"):
            st.markdown("""\
**Przekazuj do korekty gdy:**
- Jako\u015b\u0107 tekstu: "S\u0142aba" lub "Do poprawy"
- Wykryto b\u0142\u0119dy diakrytyk\u00f3w \u2014 cz\u0119sto oznacza problem z czcionk\u0105, \
nie z tre\u015bci\u0105. Rozwa\u017c tryb "Kontrola struktury i czcionki"
- Problemy terminologiczne \u2014 mieszanie j\u0119zyk\u00f3w w jednym bloku

**Sugestie to propozycje, nie rozkazy:**
System podaje najlepsz\u0105 sugestiowan\u0105 poprawk\u0119, ale korektor \
powinien zweryfikowa\u0107 kontekst. Terminologia bran\u017cowa \
(np. nazwy dodatk\u00f3w) mo\u017ce by\u0107 poprawna mimo zg\u0142oszenia.
""")
    elif is_claims_check:
        with st.expander("Kiedy konsultowa\u0107 z ekspertem?"):
            st.markdown("""\
**Przekazuj do eksperta gdy:**
- Wynik < 70 \u2014 znacz\u0105ce niesp\u00f3jno\u015bci
- Claim terapeutyczny wykryty \u2014 konsultacja z dzia\u0142em prawnym
- Regu\u0142a % w nazwie naruszona \u2014 weryfikacja z technologiem
- Produkt na rynek zagraniczny \u2014 regulacje mog\u0105 si\u0119 r\u00f3\u017cni\u0107

**Claimy AI jako sygnalizacja:**
System flaguje potencjalne problemy. Ostateczna ocena \
nale\u017cy do specjalisty ds. jako\u015bci lub dzia\u0142u prawnego.
""")
    elif is_presentation_check:
        with st.expander("Kiedy konsultowa\u0107 z prawnikiem/ekspertem?"):
            st.markdown("""\
**Natychmiast konsultuj z prawnikiem gdy:**
- Wykryto termin "Medical"/"Leczniczy" w marce \
(zabronione, EU 767/2009 Art.13)
- "Bio"/"Organic" bez certyfikatu \u2014 naruszenie EU 2018/848
- "Vet"/"Clinical" bez klasyfikacji dietetycznej \u2014 naruszenie EU 2020/354
- Wysokie ryzyko naruszenia znaku towarowego

**Konsultuj z technologiem \u017cywno\u015bci gdy:**
- Claim "monobia\u0142kowa" ale wykryto ukryte \u017ar\u00f3d\u0142a bia\u0142ka
- Claim "pe\u0142noporcjowa" przy niepe\u0142nym sk\u0142adzie od\u017cywczym
- Regu\u0142y procentowe w nazwie naruszone

**Raport jako sygnalizacja:**
Analiza AI flaguje potencjalne ryzyka regulacyjne i IP. \
Nie zast\u0119puje opinii prawnej ani audytu znak\u00f3w towarowych.
""")
    else:
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

    # -- S\u0142ownik — mode-specific --
    with st.expander("S\u0142ownik poj\u0119\u0107"):
        if is_translation:
            st.markdown("""\
| Poj\u0119cie | Znaczenie |
|---------|-----------|
| **EU 767/2009** | Regulacja UE dot. etykietowania karm \u2014 \u017ar\u00f3d\u0142o terminologii |
| **Sk\u0142adniki analityczne** | Analytical constituents (EN) / Analytische Bestandteile (DE) |
| **Karma pe\u0142noporcjowa** | Complete feed (EN) / Alleinfuttermittel (DE) |
| **Dodatki** | Additives (EN) / Zusatzstoffe (DE) |
| **J\u0119zyk \u017ar\u00f3d\u0142owy** | Automatycznie wykryty j\u0119zyk etykiety |
| **J\u0119zyk docelowy** | Wybrany j\u0119zyk t\u0142umaczenia |
""")
        elif is_design_analysis:
            st.markdown("""\
| Poj\u0119cie | Znaczenie |
|---------|-----------|
| **Hierarchia wizualna** | Porz\u0105dek wa\u017cno\u015bci element\u00f3w na etykiecie |
| **Shelf impact** | Jak etykieta wygl\u0105da na p\u00f3\u0142ce sklepowej z dystansu |
| **Facing** | Widok frontalny opakowania na p\u00f3\u0142ce |
| **Appetite appeal** | Apetyczno\u015b\u0107 \u2014 czy zdj\u0119cie/grafika budzi ch\u0119\u0107 zakupu |
| **Benchmark** | Por\u00f3wnanie z praktykami konkurencji |
| **Whitespace** | Pusta przestrze\u0144 \u2014 nie oznacza "zmarnowane miejsce" |
| **R&D** | Dzia\u0142 bada\u0144 i rozwoju (odbiorca raportu) |
""")
        elif is_structure_check:
            st.markdown("""\
| Poj\u0119cie | Znaczenie |
|---------|-----------|
| **Marker j\u0119zykowy** | Wizualne oznaczenie sekcji: flaga, kod kraju (PL/DE/EN), ikona |
| **Sekcja j\u0119zykowa** | Blok tekstu etykiety w jednym j\u0119zyku, oddzielony markerem |
| **Glif** | Wizualna reprezentacja znaku w czcionce |
| **Tofu** | Kwadracik wy\u015bwietlany gdy czcionka nie ma danego znaku |
| **Diakrytyk** | Znak modyfikuj\u0105cy liter\u0119: \u0105 \u0119 \u015b \u0107 \u017a \u017c \u0142 \u0144 \u00f3 \u00e4 \u00f6 \u00fc \u00df |
| **Osierocony tekst** | Fragment tekstu mi\u0119dzy sekcjami, nieprzypisany do \u017cadnego j\u0119zyka |
| **Bbox** | Prostok\u0105t otaczaj\u0105cy problem na etykiecie (bounding box) |
| **JSX** | Skrypt ExtendScript dla Adobe Illustratora |
| **QC Annotations** | Warstwa dodawana przez skrypt .jsx z oznaczeniami |
""")
        elif is_linguistic_only:
            st.markdown("""\
| Poj\u0119cie | Znaczenie |
|---------|-----------|
| **Diakrytyki** | Znaki \u0105 \u0119 \u015b \u0107 \u017a \u017c \u0142 \u0144 \u00f3 \u2014 cz\u0119sto gubione przez czcionki |
| **Terminologia** | Sp\u00f3jno\u015b\u0107 u\u017cywanych termin\u00f3w w obr\u0119bie etykiety |
| **Jako\u015b\u0107 tekstu** | Ocena og\u00f3lna: excellent / good / needs_review / poor |
""")
        elif is_claims_check:
            st.markdown("""\
| Poj\u0119cie | Znaczenie |
|---------|-----------|
| **Claim** | O\u015bwiadczenie marketingowe na etykiecie (np. "70% mi\u0119sa") |
| **EU 767/2009 Art.17** | Regu\u0142y nazewnictwa produkt\u00f3w paszowych |
| **Regu\u0142a 4%/14%/26%** | Minimalne % sk\u0142adnika wymaganego przez nazw\u0119 |
| **Grain-free** | Claim "bez zb\u00f3\u017c" \u2014 weryfikowany vs lista sk\u0142adnik\u00f3w |
| **Claim terapeutyczny** | O\u015bwiadczenie lecznicze \u2014 zabronione per Art.13 |
""")
        elif is_presentation_check:
            st.markdown("""\
| Poj\u0119cie | Znaczenie |
|---------|-----------|
| **Prezentacja handlowa** | Spos\u00f3b przedstawienia produktu na etykiecie |
| **EU 767/2009 Art.17** | Regu\u0142y procentowe w nazewnictwie karm |
| **FEDIAF CoGLP** | Code of Good Labelling Practice \u2014 dobre praktyki |
| **EU 2018/848** | Regulacja dot. produkt\u00f3w ekologicznych (Bio/Organic) |
| **EU 2020/354** | Lista zastosowa\u0144 karm dietetycznych (PARNUT) |
| **Znak towarowy (\u00ae)** | Zarejestrowany znak towarowy (EUIPO/UPRP) |
| **TM (\u2122)** | Niezarejestrowane roszczenie do znaku towarowego |
| **Monobia\u0142kowa** | Receptura z jednym \u017ar\u00f3d\u0142em bia\u0142ka zwierz\u0119cego |
| **Karma pe\u0142noporcjowa** | Pokrywaj\u0105ca 100% potrzeb \u017cywieniowych (complete feed) |
""")
        else:
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

    # -- FAQ — shared + mode-specific --
    with st.expander("FAQ"):
        if is_translation:
            st.markdown("""\
**Ile trwa t\u0142umaczenie?**
20\u201340 sekund.

**Czy mo\u017cna t\u0142umaczy\u0107 z dowolnego j\u0119zyka?**
Tak. System automatycznie wykrywa j\u0119zyk \u017ar\u00f3d\u0142owy.

**Czy t\u0142umaczenie uwzgl\u0119dnia terminologi\u0119 bran\u017cow\u0105?**
Tak. System u\u017cywa oficjalnych t\u0142umacze\u0144 termin\u00f3w \
z EU 767/2009 (np. "crude protein", "Rohprotein").

**Czy mog\u0119 wklei\u0107 tekst zamiast wgrywa\u0107 plik?**
Tak. Pod polem uploadu jest pole tekstowe (max 2000 znak\u00f3w). \
Je\u015bli wgrasz plik i wpiszesz tekst \u2014 plik ma priorytet.

**Czy t\u0142umaczenie zast\u0119puje t\u0142umacza?**
Nie. To punkt wyj\u015bcia do weryfikacji przez profesjonalnego \
t\u0142umacza, szczeg\u00f3lnie dla nowych rynk\u00f3w.
""")
        elif is_design_analysis:
            st.markdown("""\
**Ile trwa analiza?**
30\u201360 sekund.

**Czy oceny s\u0105 obiektywne?**
Nie. To subiektywna analiza AI oparta na praktykach bran\u017cy \
pet food. Traktuj jako profesjonaln\u0105 opini\u0119, nie audyt.

**Czy system por\u00f3wnuje z konkretnymi konkurentami?**
Nie z nazwy. Por\u00f3wnuje z og\u00f3lnymi standardami \
i trendami w bran\u017cy opakowan pet food.

**Dla kogo jest raport?**
G\u0142\u00f3wnie dla R&D i dzia\u0142u marketingu. \
Sekcja "Podsumowanie dla R&D" zawiera konkretne akcje.
""")
        elif is_structure_check:
            st.markdown("""\
**Ile trwa analiza?**
15\u201330 sekund.

**Czy system sprawdza sam plik .ai?**
Nie bezpo\u015brednio. System analizuje obraz etykiety (PDF, JPG, PNG). \
Dla natywnych plik\u00f3w .ai \u2014 u\u017cyj wygenerowanego skryptu .jsx, \
kt\u00f3ry dzia\u0142a bezpo\u015brednio w Illustratorze.

**Co je\u015bli etykieta jest jednoj\u0119zyczna?**
System wykryje jedn\u0105 sekcj\u0119 j\u0119zykow\u0105 i sprawdzi \
kompletno\u015b\u0107 czcionki dla tego j\u0119zyka. \
Kontrola struktury jest istotna g\u0142\u00f3wnie dla etykiet wieloj\u0119zycznych.

**Jak dok\u0142adne s\u0105 wsp\u00f3\u0142rz\u0119dne oznacze\u0144?**
Przybli\u017cone \u2014 AI podaje szacunkowe pozycje. \
Oznaczenia wskazuj\u0105 obszar problemu, nie precyzyjne piksele. \
Zawsze zweryfikuj wizualnie w Illustratorze.

**Czy skrypt .jsx modyfikuje m\u00f3j plik?**
Dodaje now\u0105 zablokowana warstw\u0119 "QC Annotations". \
Nie modyfikuje istniej\u0105cych warstw ani obiekt\u00f3w. \
Mo\u017cesz j\u0105 usun\u0105\u0107 lub ukry\u0107 po przegl\u0105dzie.
""")
        elif is_linguistic_only:
            st.markdown("""\
**Ile trwa analiza?**
10\u201320 sekund.

**Ile b\u0142\u0119d\u00f3w system wykrywa?**
System sprawdza ca\u0142y tekst i zwraca wszystkie znalezione b\u0142\u0119dy, \
priorytetyzuj\u0105c te o najwi\u0119kszym wp\u0142ywie na jako\u015b\u0107.

**Czy sprawdza wszystkie j\u0119zyki na etykiecie?**
Tak. System automatycznie wykrywa j\u0119zyk(i) i sprawdza \
ka\u017cdy fragment tekstu. Wykrywa te\u017c mieszanie j\u0119zyk\u00f3w.
""")
        elif is_claims_check:
            st.markdown("""\
**Ile trwa analiza?**
15\u201330 sekund.

**Czym si\u0119 r\u00f3\u017cni od pe\u0142nej weryfikacji?**
Pe\u0142na weryfikacja sprawdza sk\u0142ad od\u017cywczy vs FEDIAF + EU 767/2009. \
Walidator claim\u00f3w skupia si\u0119 na sp\u00f3jno\u015bci claim\u00f3w marketingowych \
ze sk\u0142adem.

**Czy system wykrywa wszystkie claimy?**
System ekstrahuje widoczne claimy z etykiety. Ukryte lub nieczytelne \
elementy mog\u0105 zosta\u0107 pomini\u0119te \u2014 jako\u015b\u0107 zdj\u0119cia ma znaczenie.
""")
        elif is_presentation_check:
            st.markdown("""\
**Ile trwa analiza?**
20\u201340 sekund.

**Czym si\u0119 r\u00f3\u017cni od walidatora claim\u00f3w?**
Walidator claim\u00f3w sprawdza sp\u00f3jno\u015b\u0107 claim\u00f3w ze sk\u0142adem. \
Weryfikator nazw i zastrze\u017ce\u0144 sprawdza zgodno\u015b\u0107 regulacyjn\u0105 \
prezentacji handlowej: nazewnictwo, marka, receptury i IP/trademark.

**Czy system mo\u017ce zast\u0105pi\u0107 opini\u0119 prawn\u0105?**
Nie. System flaguje potencjalne ryzyka, ale nie jest \u017ar\u00f3d\u0142em \
wiedzy prawnej. Kwestie znak\u00f3w towarowych wymagaj\u0105 weryfikacji \
w bazach EUIPO/UPRP.

**Jak dok\u0142adna jest analiza znak\u00f3w towarowych?**
Orientacyjna. System por\u00f3wnuje z baz\u0105 znanych marek pet food, \
ale nie ma dost\u0119pu do rejestru EUIPO. Traktuj jako sygnalizacj\u0119 \
do dalszej weryfikacji.
""")
        else:
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
""")

        # Shared FAQ items
        st.markdown("""\
**Czy dane s\u0105 przechowywane?**
Nie. Analiza odbywa si\u0119 w pami\u0119ci. Po zamkni\u0119ciu przegl\u0105darki \
dane znikaj\u0105. Raporty s\u0105 zapisywane tylko je\u015bli je pobierzesz.

**Co je\u015bli wyst\u0105pi b\u0142\u0105d "Rate limit"?**
System automatycznie ponawia pr\u00f3b\u0119 po 15\u201360 sekundach. \
Przy cz\u0119stych b\u0142\u0119dach \u2014 odczekaj minut\u0119 mi\u0119dzy analizami.
""")

    st.divider()

    # -- Optional features manager (install buttons for non-technical users) --
    from fediaf_verifier.deps import render_feature_manager

    render_feature_manager()

    # -- Issue reporting (GitHub) --
    if settings.github_issues_token and settings.github_issues_repo:
        st.divider()
        _issue_types = {
            "bug": "\U0001f41b B\u0142\u0105d / niepoprawny wynik",
            "feature": "\U0001f4a1 Propozycja funkcji",
            "question": "\u2753 Pytanie",
        }

        @st.dialog("Zg\u0142o\u015b problem")
        def _report_issue_dialog():
            issue_type = st.selectbox(
                "Typ zg\u0142oszenia",
                list(_issue_types.keys()),
                format_func=lambda k: _issue_types[k],
            )
            issue_title = st.text_input(
                "Tytu\u0142 (kr\u00f3tki opis)", max_chars=120,
            )
            issue_body = st.text_area(
                "Szczeg\u00f3\u0142owy opis",
                height=150,
                placeholder="Opisz problem, kroki do odtworzenia, "
                "oczekiwany vs rzeczywisty wynik...",
            )
            issue_contact = st.text_input(
                "E-mail kontaktowy (opcjonalnie)",
                max_chars=100,
            )

            if st.button("Wy\u015blij zg\u0142oszenie", type="primary", use_container_width=True):
                if not issue_title.strip():
                    st.error("Podaj tytu\u0142 zg\u0142oszenia.")
                    return
                if not issue_body.strip():
                    st.error("Podaj opis problemu.")
                    return

                # Build issue body
                body_parts = [issue_body.strip()]

                # Attach context if a report exists
                report = st.session_state.get("report")
                if report:
                    report_type = type(report).__name__
                    filename = st.session_state.get("report_filename", "")
                    body_parts.append(
                        f"\n---\n**Kontekst:** tryb `{report_type}`, "
                        f"plik: `{filename}`"
                    )

                if issue_contact.strip():
                    body_parts.append(f"\n**Kontakt:** {issue_contact.strip()}")

                full_body = "\n".join(body_parts)

                from fediaf_verifier.github_issues import create_issue

                with st.spinner("Wysy\u0142am zg\u0142oszenie..."):
                    result = create_issue(
                        token=settings.github_issues_token,
                        repo=settings.github_issues_repo,
                        title=f"[{issue_type}] {issue_title.strip()}",
                        body=full_body,
                        labels=[issue_type],
                    )

                if result.success:
                    st.success(
                        f"Zg\u0142oszenie #{result.number} utworzone. "
                        "Dzi\u0119kujemy za informacj\u0119!"
                    )
                else:
                    st.error(
                        f"Nie uda\u0142o si\u0119 wys\u0142a\u0107 zg\u0142oszenia: {result.error}"
                    )

        if st.button("\U0001f4e9 Zg\u0142o\u015b problem", use_container_width=True):
            _report_issue_dialog()

    st.caption("v1.0 \u00b7 BULT Quality Assurance")


# -- Upload section --------------------------------------------------------------------

# Clipboard paste support via JS injection
_PASTE_JS = """\
<div id="paste-zone" style="
    border: 2px dashed rgba(128,128,128,0.3);
    border-radius: 10px;
    padding: 1.2rem;
    text-align: center;
    cursor: pointer;
    margin-bottom: 1rem;
    transition: border-color 0.2s;
" tabindex="0">
    <span style="opacity:0.5; font-size:0.9rem;">
        \U0001f4cb Wklej screenshot (Ctrl+V)
    </span>
</div>
<script>
const pasteZone = document.getElementById('paste-zone');
document.addEventListener('paste', function(e) {
    const items = e.clipboardData?.items;
    if (!items) return;
    for (const item of items) {
        if (item.type.startsWith('image/')) {
            const blob = item.getAsFile();
            const reader = new FileReader();
            reader.onload = function() {
                const base64 = reader.result.split(',')[1];
                window.parent.postMessage({
                    type: 'streamlit:setComponentValue',
                    data: {base64: base64, name: 'clipboard_' +
                        new Date().toISOString().slice(0,19).replace(/:/g,'-')
                        + '.png'}
                }, '*');
            };
            reader.readAsDataURL(blob);
            pasteZone.innerHTML =
                '<span style="color:#4CAF50;">\u2705 Screenshot wklejony</span>';
            e.preventDefault();
            return;
        }
    }
});
pasteZone.addEventListener('click', function() { this.focus(); });
</script>
"""

# Clipboard paste via session state (camera_input as fallback for images)
if "pasted_image" not in st.session_state:
    st.session_state.pasted_image = None

# -- Artwork inspection mode: single or dual file uploaders -------------------------
_artwork_master = None
_artwork_proof = None
_artwork_mode = "single"
_artwork_threshold = 30

if is_artwork_check:
    st.subheader("\U0001f50d Inspekcja artwork")
    _artwork_mode = st.radio(
        "Tryb inspekcji",
        ["single", "compare"],
        format_func=lambda x: {
            "single": "Pojedynczy plik (print readiness + kolory)",
            "compare": "Por\u00f3wnanie: master vs proof (pixel diff + kolory + print)",
        }[x],
        horizontal=True,
        key="artwork_mode",
    )

    _artwork_threshold = st.slider(
        "Czu\u0142o\u015b\u0107 detekcji zmian (pixel threshold)",
        min_value=5, max_value=100, value=30, step=5,
        help="Ni\u017csza warto\u015b\u0107 = wi\u0119ksza czu\u0142o\u015b\u0107 na drobne r\u00f3\u017cnice",
        key="artwork_threshold",
    )

    if _artwork_mode == "compare":
        col_m, col_p = st.columns(2)
        with col_m:
            _artwork_master = st.file_uploader(
                "Master (referencja)",
                type=["jpg", "jpeg", "png", "pdf", "tiff", "tif"],
                help="Zatwierdzony artwork master",
                key="artwork_master",
            )
        with col_p:
            _artwork_proof = st.file_uploader(
                "Proof (do sprawdzenia)",
                type=["jpg", "jpeg", "png", "pdf", "tiff", "tif"],
                help="Proof do por\u00f3wnania z masterem",
                key="artwork_proof",
            )
    else:
        _artwork_master = st.file_uploader(
            "Wgraj etykiet\u0119 do inspekcji",
            type=["jpg", "jpeg", "png", "pdf", "tiff", "tif"],
            help="JPG, PNG, PDF lub TIFF",
            key="artwork_single",
        )

    # Don't use the standard uploader
    uploaded = None

# -- Diff mode: dual file uploaders ------------------------------------------------
uploaded_old = None
uploaded_new = None

if is_artwork_check:
    # Artwork mode has its own uploaders above — skip standard uploader
    uploaded = None
elif is_diff_check:
    st.subheader("Por\u00f3wnanie wersji etykiety")
    col_old, col_new = st.columns(2)
    with col_old:
        uploaded_old = st.file_uploader(
            "Stara wersja etykiety",
            type=["jpg", "jpeg", "png", "pdf", "docx"],
            help="Wgraj star\u0105 wersj\u0119 etykiety",
            key="diff_old",
        )
    with col_new:
        uploaded_new = st.file_uploader(
            "Nowa wersja etykiety",
            type=["jpg", "jpeg", "png", "pdf", "docx"],
            help="Wgraj now\u0105 wersj\u0119 etykiety",
            key="diff_new",
        )
    # Set uploaded to None — diff mode does not use the standard uploader
    uploaded = None
elif is_label_text_gen:
    # Label text mode does not use file uploader — uses form instead
    uploaded = None
elif is_product_desc and _pd_input_mode == "manual":
    # Product description manual mode — uses form instead of file uploader
    uploaded = None
elif is_catalog_translation:
    # Catalog Translator has its own complete UI — render and stop
    uploaded = None
    from catalog_translator.app import main as _catalog_main
    _catalog_main(
        target_lang=_ct_target_lang,
        target_lang_name=_ct_target_name,
        page_range=_ct_page_range,
        dry_run=_ct_dry_run,
        run_validation=_ct_validate,
        glossary_file=_ct_glossary_file,
    )
    st.stop()
elif is_packaging_designer:
    # Packaging Designer has its own complete UI — render and stop
    uploaded = None
    from packaging_designer.app import main as _packaging_main
    _packaging_main()
    st.stop()
else:
    uploaded = st.file_uploader(
        "Wgraj etykiet\u0119 produktu",
        type=["jpg", "jpeg", "png", "pdf", "docx"],
        help="JPG, PNG, PDF, DOCX lub wklej screenshot (Ctrl+V)",
    )

    # Camera input as clipboard alternative (works on all Streamlit versions)
    with st.expander("\U0001f4f7 Zr\u00f3b zdj\u0119cie lub wklej screenshot", expanded=False):
        camera_img = st.camera_input(
            "Zr\u00f3b zdj\u0119cie etykiety",
            help="Kliknij aby zrobi\u0107 zdj\u0119cie kamer\u0105 lub u\u017cyj jako "
            "alternatyw\u0119 dla wklejania screenshot\u00f3w.",
        )
        if camera_img is not None:
            uploaded = camera_img

if uploaded:
    col_preview, col_info = st.columns([1, 2])
    with col_preview:
        if uploaded.type and uploaded.type.startswith("image"):
            st.image(uploaded, caption=uploaded.name, use_container_width=True)
        else:
            st.markdown(
                f'<div style="background:var(--secondary-background-color);'
                f"border-radius:10px;padding:2rem;text-align:center;\">"
                f'<span style="font-size:2.5rem;">\U0001f4c4</span><br>'
                f'<span style="opacity:0.7;font-size:0.85rem;">'
                f"{__import__('html').escape(uploaded.name)}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
    with col_info:
        st.markdown(f"**Plik:** {uploaded.name}")
        st.markdown(f"**Rozmiar:** {uploaded.size / 1024:.1f} KB")
        if is_translation:
            st.markdown(
                f"**Tryb:** t\u0142umaczenie na {_translation_target_name}"
            )
            st.caption("T\u0142umaczenie \u2014 ok. 20\u201340 sekund.")
        elif is_design_analysis:
            st.markdown("**Tryb:** analiza projektu graficznego")
            st.caption("Analiza designu \u2014 ok. 30\u201360 sekund.")
        elif is_structure_check:
            st.markdown("**Tryb:** kontrola struktury i czcionki")
            st.caption(
                "Analiza sekcji j\u0119zykowych i kompletno\u015bci "
                "znak\u00f3w \u2014 ok. 15\u201330 sekund."
            )
        elif is_linguistic_only:
            st.markdown("**Tryb:** weryfikacja j\u0119zykowa")
            st.caption("Szybka analiza tekstu \u2014 ok. 10\u201320 sekund.")
        elif is_claims_check:
            st.markdown("**Tryb:** walidacja claim\u00f3w")
            st.caption("Analiza claim\u00f3w vs sk\u0142ad \u2014 ok. 15\u201330 sekund.")
        elif is_presentation_check:
            st.markdown("**Tryb:** walidacja prezentacji handlowej")
            st.caption("Analiza receptur, nazw, marki i zastrze\u017ce\u0144 \u2014 ok. 20\u201340 sekund.")
        elif is_market_check:
            st.markdown(f"**Tryb:** walidacja rynkowa ({_market_target_name})")
            st.caption("Analiza wymog\u00f3w krajowych \u2014 ok. 20\u201340 sekund.")
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

# -- Label text generation form (no file uploader) --------------------------------
_label_text_form_data = {}
if is_label_text_gen:
    st.subheader("Generator tekstu etykiety")

    _lt_species = st.selectbox(
        "Gatunek", ["dog", "cat"], format_func=lambda x: {"dog": "Pies", "cat": "Kot"}[x]
    )
    _lt_c1, _lt_c2, _lt_c3 = st.columns(3)
    with _lt_c1:
        _lt_lifestage = st.selectbox(
            "Etap \u017cycia",
            ["adult", "puppy", "kitten", "senior", "all_stages"],
            format_func=lambda x: {
                "adult": "Doros\u0142y", "puppy": "Szczeni\u0119",
                "kitten": "Koci\u0119", "senior": "Senior",
                "all_stages": "Wszystkie etapy",
            }[x],
        )
    with _lt_c2:
        _lt_food_type = st.selectbox(
            "Typ karmy",
            ["dry", "wet", "semi_moist", "treat"],
            format_func=lambda x: {
                "dry": "Sucha", "wet": "Mokra",
                "semi_moist": "P\u00f3\u0142wilgotna", "treat": "Przysmak",
            }[x],
        )
    with _lt_c3:
        _lt_language = st.selectbox(
            "J\u0119zyk etykiety",
            list(_TRANSLATION_LANGUAGES.keys()),
            format_func=lambda x: f"{_TRANSLATION_LANGUAGES[x]} ({x})",
        )

    _lt_product_name = st.text_input(
        "Nazwa produktu",
        placeholder="np. Premium Adult Dog Chicken & Rice",
    )
    _lt_ingredients = st.text_area(
        "Sk\u0142adniki (lista sk\u0142adu)",
        height=120,
        placeholder="np. mi\u0119so z kurczaka (30%), ry\u017c (20%), t\u0142uszcz drobiowy...",
    )

    st.markdown("**Sk\u0142adniki analityczne (%):**")
    _nt_c1, _nt_c2, _nt_c3, _nt_c4 = st.columns(4)
    with _nt_c1:
        _lt_protein = st.number_input("Bia\u0142ko", min_value=0.0, max_value=100.0, value=0.0, step=0.1, key="lt_protein")
        _lt_calcium = st.number_input("Wap\u0144", min_value=0.0, max_value=100.0, value=0.0, step=0.01, key="lt_calcium")
    with _nt_c2:
        _lt_fat = st.number_input("T\u0142uszcz", min_value=0.0, max_value=100.0, value=0.0, step=0.1, key="lt_fat")
        _lt_phosphorus = st.number_input("Fosfor", min_value=0.0, max_value=100.0, value=0.0, step=0.01, key="lt_phosphorus")
    with _nt_c3:
        _lt_fibre = st.number_input("W\u0142\u00f3kno", min_value=0.0, max_value=100.0, value=0.0, step=0.1, key="lt_fibre")
    with _nt_c4:
        _lt_moisture = st.number_input("Wilgotno\u015b\u0107", min_value=0.0, max_value=100.0, value=0.0, step=0.1, key="lt_moisture")
        _lt_ash = st.number_input("Popi\u00f3\u0142", min_value=0.0, max_value=100.0, value=0.0, step=0.1, key="lt_ash")

    _label_text_form_data = {
        "species": _lt_species,
        "lifestage": _lt_lifestage,
        "food_type": _lt_food_type,
        "language": _lt_language,
        "language_name": _TRANSLATION_LANGUAGES[_lt_language],
        "product_name": _lt_product_name,
        "ingredients": _lt_ingredients,
        "nutrients": {
            "crude_protein": _lt_protein,
            "crude_fat": _lt_fat,
            "crude_fibre": _lt_fibre,
            "moisture": _lt_moisture,
            "crude_ash": _lt_ash,
            "calcium": _lt_calcium,
            "phosphorus": _lt_phosphorus,
        },
    }


# -- Product description form (manual mode) ----------------------------------------
_product_desc_form_data = {}
if is_product_desc and _pd_input_mode == "manual":
    st.subheader("Generator opis\u00f3w produkt\u00f3w")

    _pd_species = st.selectbox(
        "Gatunek", ["dog", "cat"],
        format_func=lambda x: {"dog": "Pies", "cat": "Kot"}[x],
        key="pd_species",
    )
    _pd_c1, _pd_c2 = st.columns(2)
    with _pd_c1:
        _pd_lifestage = st.selectbox(
            "Etap \u017cycia",
            ["adult", "puppy", "kitten", "senior", "all_stages"],
            format_func=lambda x: {
                "adult": "Doros\u0142y", "puppy": "Szczeni\u0119",
                "kitten": "Koci\u0119", "senior": "Senior",
                "all_stages": "Wszystkie etapy",
            }[x],
            key="pd_lifestage",
        )
    with _pd_c2:
        _pd_food_type = st.selectbox(
            "Typ karmy",
            ["dry", "wet", "semi_moist", "treat"],
            format_func=lambda x: {
                "dry": "Sucha", "wet": "Mokra",
                "semi_moist": "P\u00f3\u0142wilgotna", "treat": "Przysmak",
            }[x],
            key="pd_food_type",
        )

    _pd_product_name = st.text_input(
        "Nazwa produktu",
        placeholder="np. Premium Adult Dog Chicken & Rice",
        key="pd_product_name",
    )
    _pd_brand = st.text_input(
        "Marka",
        placeholder="np. BULT Nutrition",
        key="pd_brand",
    )
    _pd_ingredients = st.text_area(
        "Sk\u0142adniki (lista sk\u0142adu)",
        height=120,
        placeholder="np. mi\u0119so z kurczaka (30%), ry\u017c (20%), t\u0142uszcz drobiowy...",
        key="pd_ingredients",
    )
    _pd_usps = st.text_area(
        "Unikalne cechy produktu (USP)",
        height=80,
        placeholder="np. receptura opracowana z weterynarzami, "
        "sk\u0142adniki z lokalnych farm, bez sztucznych konserwant\u00f3w...",
        key="pd_usps",
    )

    st.markdown("**Sk\u0142adniki analityczne (%):**")
    _pn_c1, _pn_c2, _pn_c3, _pn_c4 = st.columns(4)
    with _pn_c1:
        _pd_protein = st.number_input("Bia\u0142ko", min_value=0.0, max_value=100.0, value=0.0, step=0.1, key="pd_protein")
        _pd_calcium = st.number_input("Wap\u0144", min_value=0.0, max_value=100.0, value=0.0, step=0.01, key="pd_calcium")
    with _pn_c2:
        _pd_fat = st.number_input("T\u0142uszcz", min_value=0.0, max_value=100.0, value=0.0, step=0.1, key="pd_fat")
        _pd_phosphorus = st.number_input("Fosfor", min_value=0.0, max_value=100.0, value=0.0, step=0.01, key="pd_phosphorus")
    with _pn_c3:
        _pd_fibre = st.number_input("W\u0142\u00f3kno", min_value=0.0, max_value=100.0, value=0.0, step=0.1, key="pd_fibre")
    with _pn_c4:
        _pd_moisture = st.number_input("Wilgotno\u015b\u0107", min_value=0.0, max_value=100.0, value=0.0, step=0.1, key="pd_moisture")
        _pd_ash = st.number_input("Popi\u00f3\u0142", min_value=0.0, max_value=100.0, value=0.0, step=0.1, key="pd_ash")

    _product_desc_form_data = {
        "species": _pd_species,
        "lifestage": _pd_lifestage,
        "food_type": _pd_food_type,
        "product_name": _pd_product_name,
        "brand": _pd_brand,
        "ingredients": _pd_ingredients,
        "usps": _pd_usps,
        "nutrients": {
            "crude_protein": _pd_protein,
            "crude_fat": _pd_fat,
            "crude_fibre": _pd_fibre,
            "moisture": _pd_moisture,
            "crude_ash": _pd_ash,
            "calcium": _pd_calcium,
            "phosphorus": _pd_phosphorus,
        },
    }


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


def _run_structure_check(uploaded_file) -> None:
    with st.spinner(
        "Sprawdzam struktur\u0119 sekcji j\u0119zykowych i czcionk\u0119... "
        "(ok. 15\u201330 sekund)"
    ):
        try:
            uploaded_file.seek(0)
            raw_bytes = uploaded_file.read()
            label_b64, media_type = file_to_base64(
                raw_bytes, uploaded_file.name
            )
            result = verify_label_structure(
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
            logger.exception("Unexpected error during structure check")
            return

    st.session_state.report = result
    st.session_state.report_filename = uploaded_file.name
    st.session_state.report_market = None
    # Store raw bytes + media type for annotation generation
    st.session_state.structure_file_bytes = raw_bytes
    st.session_state.structure_media_type = media_type


# -- Translation: text input area (alternative to file upload) ---------------------
_translation_source_text = ""
if is_translation:
    _translation_source_text = st.text_area(
        "Lub wklej/wpisz tekst etykiety",
        max_chars=2000,
        height=150,
        placeholder="Wklej tre\u015b\u0107 etykiety do przet\u0142umaczenia (max 2000 znak\u00f3w)...",
        help="Alternatywa dla uploadu pliku. Mo\u017cesz wklei\u0107 tekst "
        "zamiast wgrywa\u0107 obraz/PDF.",
    )
    if uploaded and _translation_source_text:
        st.warning(
            "Wgrano plik i wpisano tekst \u2014 plik ma priorytet, "
            "tekst zostanie zignorowany."
        )


# -- Run functions for new modes ---------------------------------------------------
def _run_translation(
    uploaded_file, source_text: str, target_lang: str,
    target_name: str, user_notes: str,
) -> None:
    with st.spinner(
        f"T\u0142umacz\u0119 na {target_name}... (ok. 20\u201340 sekund)"
    ):
        try:
            label_b64 = ""
            media_type = ""
            if uploaded_file is not None:
                uploaded_file.seek(0)
                label_b64, media_type = file_to_base64(
                    uploaded_file.read(), uploaded_file.name
                )
            result = verify_translation(
                target_language=target_lang,
                target_language_name=target_name,
                provider=secondary_provider,
                settings=settings,
                label_b64=label_b64,
                media_type=media_type,
                source_text=source_text if not label_b64 else "",
                user_notes=user_notes,
            )
        except ConversionError as e:
            st.error(f"**B\u0142\u0105d pliku:** {e}")
            return
        except FediafVerifierError as e:
            st.error(f"**B\u0142\u0105d API:** {e}")
            return
        except Exception as e:
            st.error(f"**Nieoczekiwany b\u0142\u0105d:** {e}")
            logger.exception("Unexpected error during translation")
            return

    st.session_state.report = result
    st.session_state.report_filename = (
        uploaded_file.name if uploaded_file else "tekst_wklejony"
    )
    st.session_state.report_market = None


def _run_design_analysis(uploaded_file, segment: str = "premium_dry") -> None:
    with st.spinner(
        "Analizuj\u0119 projekt graficzny... (ok. 30\u201360 sekund)"
    ):
        try:
            uploaded_file.seek(0)
            label_b64, media_type = file_to_base64(
                uploaded_file.read(), uploaded_file.name
            )
            result = verify_design_analysis(
                label_b64=label_b64,
                media_type=media_type,
                provider=secondary_provider,
                settings=settings,
                segment=segment,
            )
        except ConversionError as e:
            st.error(f"**B\u0142\u0105d pliku:** {e}")
            return
        except FediafVerifierError as e:
            st.error(f"**B\u0142\u0105d API:** {e}")
            return
        except Exception as e:
            st.error(f"**Nieoczekiwany b\u0142\u0105d:** {e}")
            logger.exception("Unexpected error during design analysis")
            return

    st.session_state.report = result
    st.session_state.report_filename = uploaded_file.name
    st.session_state.report_market = None


def _run_ean_check(uploaded_file) -> None:
    with st.spinner(
        "Sprawdzam kody kreskowe i QR... (ok. 10\u201320 sekund)"
    ):
        try:
            uploaded_file.seek(0)
            label_b64, media_type = file_to_base64(
                uploaded_file.read(), uploaded_file.name
            )
            result = verify_ean(
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
            logger.exception("Unexpected error during EAN check")
            return

    st.session_state.report = result
    st.session_state.report_filename = uploaded_file.name
    st.session_state.report_market = None


def _run_claims_check(uploaded_file) -> None:
    with st.spinner(
        "Sprawdzam sp\u00f3jno\u015b\u0107 claim\u00f3w ze sk\u0142adem... "
        "(ok. 15\u201330 sekund)"
    ):
        try:
            uploaded_file.seek(0)
            label_b64, media_type = file_to_base64(
                uploaded_file.read(), uploaded_file.name
            )
            result = verify_claims(
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
            logger.exception("Unexpected error during claims check")
            return

    st.session_state.report = result
    st.session_state.report_filename = uploaded_file.name
    st.session_state.report_market = None


def _run_presentation_check(uploaded_file) -> None:
    with st.spinner(
        "Sprawdzam zgodno\u015b\u0107 prezentacji handlowej... "
        "(ok. 20\u201340 sekund)"
    ):
        try:
            uploaded_file.seek(0)
            label_b64, media_type = file_to_base64(
                uploaded_file.read(), uploaded_file.name
            )
            result = verify_presentation(
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
            logger.exception("Unexpected error during presentation check")
            return

    st.session_state.report = result
    st.session_state.report_filename = uploaded_file.name
    st.session_state.report_market = None


def _run_market_check(uploaded_file, market_code: str) -> None:
    with st.spinner(
        "Sprawdzam zgodno\u015b\u0107 z wymogami krajowymi... "
        "(ok. 20\u201340 sekund)"
    ):
        try:
            uploaded_file.seek(0)
            label_b64, media_type = file_to_base64(
                uploaded_file.read(), uploaded_file.name
            )
            result = verify_market_compliance(
                label_b64=label_b64,
                media_type=media_type,
                market_code=market_code,
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
            logger.exception("Unexpected error during market check")
            return

    st.session_state.report = result
    st.session_state.report_filename = uploaded_file.name
    st.session_state.report_market = None


def _run_label_text(form_data: dict) -> None:
    lang_name = form_data.get("language_name", "")
    with st.spinner(
        f"Generuj\u0119 tekst etykiety ({lang_name})... "
        "(ok. 20\u201340 sekund)"
    ):
        try:
            result = generate_label_text(
                species=form_data["species"],
                lifestage=form_data["lifestage"],
                food_type=form_data["food_type"],
                ingredients=form_data["ingredients"],
                nutrients=form_data["nutrients"],
                target_language=form_data["language"],
                target_language_name=lang_name,
                provider=secondary_provider,
                settings=settings,
                product_name=form_data.get("product_name", ""),
            )
        except FediafVerifierError as e:
            st.error(f"**B\u0142\u0105d API:** {e}")
            return
        except Exception as e:
            st.error(f"**Nieoczekiwany b\u0142\u0105d:** {e}")
            logger.exception("Unexpected error during label text generation")
            return

    st.session_state.report = result
    st.session_state.report_filename = form_data.get("product_name", "") or "tekst_etykiety"
    st.session_state.report_market = None


def _run_product_description(form_data: dict | None, uploaded_file=None) -> None:
    tone_labels = {
        "premium": "Premium", "scientific": "Naukowy",
        "natural": "Naturalny", "standard": "Standardowy",
    }
    tone_name = tone_labels.get(_pd_tone, _pd_tone)
    with st.spinner(
        f"Generuj\u0119 opis produktu ({_pd_target_name}, {tone_name})... "
        "(ok. 30\u201360 sekund)"
    ):
        try:
            label_b64 = ""
            media_type = ""
            if uploaded_file is not None:
                uploaded_file.seek(0)
                label_b64, media_type = file_to_base64(
                    uploaded_file.read(), uploaded_file.name
                )

            result = generate_product_description(
                provider=secondary_provider,
                settings=settings,
                target_language=_pd_target_lang,
                target_language_name=_pd_target_name,
                tone=_pd_tone,
                species=form_data.get("species", "") if form_data else "",
                lifestage=form_data.get("lifestage", "") if form_data else "",
                food_type=form_data.get("food_type", "") if form_data else "",
                ingredients=form_data.get("ingredients", "") if form_data else "",
                nutrients=form_data.get("nutrients") if form_data else None,
                product_name=form_data.get("product_name", "") if form_data else "",
                usps=form_data.get("usps", "") if form_data else "",
                brand=form_data.get("brand", "") if form_data else "",
                label_b64=label_b64,
                media_type=media_type,
            )
        except FediafVerifierError as e:
            st.error(f"**B\u0142\u0105d API:** {e}")
            return
        except Exception as e:
            st.error(f"**Nieoczekiwany b\u0142\u0105d:** {e}")
            logger.exception("Unexpected error during product description generation")
            return

    st.session_state.report = result
    st.session_state.report_filename = (
        uploaded_file.name if uploaded_file
        else (form_data.get("product_name", "") if form_data else "")
        or "opis_produktu"
    )
    st.session_state.report_market = None


def _run_artwork_inspection(
    master_file, proof_file=None, threshold: int = 30,
) -> None:
    mode_label = (
        "Por\u00f3wnuj\u0119 master vs proof..."
        if proof_file else "Analizuj\u0119 artwork..."
    )
    with st.spinner(f"{mode_label} (ok. 10\u201330 sekund)"):
        try:
            master_file.seek(0)
            master_b64, master_mt = file_to_base64(
                master_file.read(), master_file.name
            )
            proof_b64, proof_mt = None, None
            if proof_file:
                proof_file.seek(0)
                proof_b64, proof_mt = file_to_base64(
                    proof_file.read(), proof_file.name
                )
            result = verify_artwork_inspection(
                img_a_b64=master_b64,
                media_type_a=master_mt,
                provider=secondary_provider,
                settings=settings,
                img_b_b64=proof_b64,
                media_type_b=proof_mt,
                pixel_diff_threshold=threshold,
            )
        except ConversionError as e:
            st.error(f"**B\u0142\u0105d pliku:** {e}")
            return
        except FediafVerifierError as e:
            st.error(f"**B\u0142\u0105d API:** {e}")
            return
        except Exception as e:
            st.error(f"**Nieoczekiwany b\u0142\u0105d:** {e}")
            logger.exception("Unexpected error during artwork inspection")
            return

    st.session_state.report = result
    st.session_state.report_filename = master_file.name
    st.session_state.report_artwork_proof = (
        proof_file.name if proof_file else ""
    )
    st.session_state.report_market = None


def _run_diff_check(old_file, new_file) -> None:
    with st.spinner(
        "Por\u00f3wnuj\u0119 wersje etykiety... (ok. 20\u201340 sekund)"
    ):
        try:
            old_file.seek(0)
            old_b64, old_media_type = file_to_base64(
                old_file.read(), old_file.name
            )
            new_file.seek(0)
            new_b64, new_media_type = file_to_base64(
                new_file.read(), new_file.name
            )
            result = verify_label_diff(
                old_b64=old_b64,
                old_media_type=old_media_type,
                new_b64=new_b64,
                new_media_type=new_media_type,
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
            logger.exception("Unexpected error during diff check")
            return

    st.session_state.report = result
    st.session_state.report_filename = new_file.name
    st.session_state.report_old_filename = old_file.name
    st.session_state.report_new_filename = new_file.name
    st.session_state.report_market = None


# -- Buttons -----------------------------------------------------------------------
_has_translation_input = uploaded or bool(_translation_source_text.strip())

if is_translation and _has_translation_input and st.button(
    "Przet\u0142umacz", type="primary", width="stretch"
):
    _run_translation(
        uploaded if uploaded else None,
        _translation_source_text,
        _translation_target_lang,
        _translation_target_name,
        _translation_notes,
    )

if uploaded and is_claims_check and st.button(
    "Sprawd\u017a claimy", type="primary", width="stretch"
):
    _run_claims_check(uploaded)

if uploaded and is_presentation_check and st.button(
    "Sprawd\u017a prezentacj\u0119 handlow\u0105", type="primary", width="stretch"
):
    _run_presentation_check(uploaded)

if uploaded and is_market_check and st.button(
    "Sprawd\u017a zgodno\u015b\u0107 rynkow\u0105", type="primary", width="stretch"
):
    _run_market_check(uploaded, _market_target_code)

if is_label_text_gen and _label_text_form_data.get("ingredients", "").strip() and st.button(
    "Generuj tekst etykiety", type="primary", width="stretch"
):
    _run_label_text(_label_text_form_data)

if is_product_desc and _pd_input_mode == "manual" and _product_desc_form_data.get("ingredients", "").strip() and st.button(
    "Generuj opis produktu", type="primary", width="stretch"
):
    _run_product_description(_product_desc_form_data)

if is_product_desc and _pd_input_mode == "image" and uploaded and st.button(
    "Generuj opis produktu z etykiety", type="primary", width="stretch"
):
    _run_product_description(None, uploaded)

if is_diff_check and uploaded_old and uploaded_new and st.button(
    "Por\u00f3wnaj wersje", type="primary", width="stretch"
):
    _run_diff_check(uploaded_old, uploaded_new)

if uploaded and is_ean_check and st.button(
    "Sprawd\u017a kody", type="primary", width="stretch"
):
    _run_ean_check(uploaded)

_artwork_ready = (
    is_artwork_check
    and _artwork_master is not None
    and (_artwork_mode == "single" or _artwork_proof is not None)
)
if _artwork_ready and st.button(
    "Inspekcja artwork", type="primary", width="stretch"
):
    _run_artwork_inspection(_artwork_master, _artwork_proof, _artwork_threshold)

_SEGMENT_LABELS = {
    "premium_dry": "Premium sucha karma",
    "economy_dry": "Ekonomiczna sucha karma",
    "premium_wet": "Premium mokra karma",
    "economy_wet": "Ekonomiczna mokra karma",
    "treats": "Przysmaki",
    "supplements": "Suplementy",
    "barf_raw": "BARF / surowa",
    "veterinary": "Weterynaryjna",
}
if uploaded and is_design_analysis:
    _design_segment = st.selectbox(
        "Segment produktu (do benchmarku)",
        options=list(_SEGMENT_LABELS.keys()),
        format_func=lambda k: _SEGMENT_LABELS[k],
        index=0,
    )
    if st.button("Analizuj design", type="primary", width="stretch"):
        _run_design_analysis(uploaded, segment=_design_segment)

if uploaded and is_structure_check and st.button(
    "Sprawd\u017a struktur\u0119", type="primary", width="stretch"
):
    _run_structure_check(uploaded)

if uploaded and is_linguistic_only and st.button(
    "Sprawd\u017a j\u0119zyk", type="primary", width="stretch"
):
    _run_linguistic_only(uploaded)

if uploaded and not is_linguistic_only and not is_structure_check and not is_translation and not is_design_analysis and not is_ean_check and not is_claims_check and not is_presentation_check and not is_market_check and not is_label_text_gen and not is_diff_check and not is_product_desc and not is_artwork_check and st.button(
    "Sprawd\u017a etykiet\u0119", type="primary", width="stretch"
):
    _run_verification(uploaded, selected_market)


# -- Report rendering (imported from renderers.py) ------------------------------------
from fediaf_verifier.renderers import (
    render_artwork_inspection_report,
    render_claims_report,
    render_design_report,
    render_diff_report,
    render_ean_report,
    render_label_text_report,
    render_linguistic_report,
    render_market_report,
    render_presentation_report,
    render_product_description_report,
    render_report,
    render_structure_report,
    render_translation_report,
)


# -- Render saved report ---------------------------------------------------------------
if st.session_state.report is not None:
    report = st.session_state.report
    # Use class name for dispatch — robust against Streamlit hot-reload
    _report_type = type(report).__name__
    if _report_type == "ArtworkInspectionResult":
        render_artwork_inspection_report(
            report,
            st.session_state.report_filename,
            getattr(st.session_state, "report_artwork_proof", ""),
        )
    elif _report_type == "ClaimsCheckResult":
        render_claims_report(report, st.session_state.report_filename)
    elif _report_type == "PresentationCheckResult":
        render_presentation_report(report, st.session_state.report_filename)
    elif _report_type == "MarketCheckResult":
        render_market_report(report, st.session_state.report_filename)
    elif _report_type == "LabelTextResult":
        render_label_text_report(report, st.session_state.report_filename)
    elif _report_type == "ProductDescriptionResult":
        render_product_description_report(report, st.session_state.report_filename)
    elif _report_type == "LabelDiffResult":
        render_diff_report(
            report,
            st.session_state.report_old_filename,
            st.session_state.report_new_filename,
        )
    elif _report_type == "EANCheckResult":
        render_ean_report(report, st.session_state.report_filename)
    elif _report_type == "TranslationResult":
        render_translation_report(report, st.session_state.report_filename)
    elif _report_type == "DesignAnalysisResult":
        render_design_report(report, st.session_state.report_filename)
    elif _report_type == "LabelStructureCheckResult":
        render_structure_report(report, st.session_state.report_filename)
    elif _report_type == "LinguisticCheckResult":
        render_linguistic_report(report, st.session_state.report_filename)
    else:
        render_report(report, st.session_state.report_filename, st.session_state.report_market, settings)
