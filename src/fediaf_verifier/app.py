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
from fediaf_verifier.export import (
    design_to_text,
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
from fediaf_verifier.providers import AIProvider
from fediaf_verifier.verifier import (
    create_providers,
    verify_design_analysis,
    verify_label,
    verify_label_structure,
    verify_linguistic_only,
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
if "structure_file_bytes" not in st.session_state:
    st.session_state.structure_file_bytes = None
if "structure_media_type" not in st.session_state:
    st.session_state.structure_media_type = ""

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
    # CSS: visual separator between verification group (items 1-3) and tools (4-5)
    st.markdown("""
<style>
    /* Separator line between 3rd and 4th radio option */
    section[data-testid="stSidebar"] div[role="radiogroup"] > label:nth-child(4) {
        border-top: 1px solid rgba(128,128,128,0.2);
        margin-top: 0.6rem;
        padding-top: 0.6rem;
    }
    /* Compact radio spacing */
    section[data-testid="stSidebar"] div[role="radiogroup"] > label {
        padding: 0.25rem 0;
    }
</style>
""", unsafe_allow_html=True)

    verification_mode = st.radio(
        "Tryb pracy",
        [
            _MODE_FULL,
            _MODE_LINGUISTIC,
            _MODE_STRUCTURE,
            _MODE_TRANSLATION,
            _MODE_DESIGN,
        ],
        captions=[
            "Sk\u0142ad, FEDIAF, EU, opakowanie, j\u0119zyk",
            "Ortografia, gramatyka, diakrytyki",
            "Sekcje j\u0119zykowe, markery, czcionka",
            "T\u0142umaczenie tre\u015bci na wybrany j\u0119zyk",
            "Ocena designu z rekomendacjami dla R&D",
        ],
    )

    is_linguistic_only = verification_mode == _MODE_LINGUISTIC
    is_structure_check = verification_mode == _MODE_STRUCTURE
    is_translation = verification_mode == _MODE_TRANSLATION
    is_design_analysis = verification_mode == _MODE_DESIGN

    # -- Mode-specific options --
    st.divider()

    selected_market = None
    _translation_target_lang = ""
    _translation_target_name = ""
    _translation_notes = ""

    if is_translation:
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

    elif not is_linguistic_only and not is_structure_check and not is_design_analysis:
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

    if not is_linguistic_only and not is_structure_check and not is_translation and not is_design_analysis:
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
    st.caption("v1.0 \u00b7 BULT Quality Check")


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
            st.image(uploaded, caption=uploaded.name, width="stretch")
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


def _run_design_analysis(uploaded_file) -> None:
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


# -- Buttons -----------------------------------------------------------------------
_has_translation_input = uploaded or bool(_translation_source_text.strip())

if is_translation and _has_translation_input and st.button(
    "Przet\u0142umacz", type="primary", use_container_width=True
):
    _run_translation(
        uploaded if uploaded else None,
        _translation_source_text,
        _translation_target_lang,
        _translation_target_name,
        _translation_notes,
    )

if uploaded and is_design_analysis and st.button(
    "Analizuj design", type="primary", use_container_width=True
):
    _run_design_analysis(uploaded)

if uploaded and is_structure_check and st.button(
    "Sprawd\u017a struktur\u0119", type="primary", use_container_width=True
):
    _run_structure_check(uploaded)

if uploaded and is_linguistic_only and st.button(
    "Sprawd\u017a j\u0119zyk", type="primary", use_container_width=True
):
    _run_linguistic_only(uploaded)

if uploaded and not is_linguistic_only and not is_structure_check and not is_translation and not is_design_analysis and st.button(
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
        from html import escape as _esc

        for li in lr.issues:
            icon = _ISSUE_ICONS.get(li.issue_type, "\u2022")
            label = _ISSUE_LABELS.get(li.issue_type, li.issue_type)
            st.markdown(
                f"{icon} **[{label}]** "
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


# -- Render structure check report -----------------------------------------------------
def _render_structure_report(
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
            use_container_width=True,
        )

    with col_jsx:
        from fediaf_verifier.jsx_generator import generate_jsx

        jsx_script = generate_jsx(result.report, filename)
        st.download_button(
            "\u2b07\ufe0f Skrypt Illustrator (.jsx)",
            data=jsx_script,
            file_name=f"qc_{stem}.jsx",
            mime="application/javascript",
            use_container_width=True,
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
                use_container_width=True,
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
def _render_translation_report(result, filename: str) -> None:
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
        use_container_width=True,
    )


# -- Render design analysis report -----------------------------------------------------
def _render_design_report(result, filename: str) -> None:
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

    # Competitive benchmarks
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
            use_container_width=True,
        )
    with col_b:
        st.download_button(
            "\u2b07\ufe0f Raport (JSON)",
            data=result.report.model_dump_json(indent=2, exclude_none=True),
            file_name=f"design_{stem}.json",
            mime="application/json",
            use_container_width=True,
        )


# -- Render saved report ---------------------------------------------------------------
if st.session_state.report is not None:
    report = st.session_state.report
    # Use class name for dispatch — robust against Streamlit hot-reload
    _report_type = type(report).__name__
    if _report_type == "TranslationResult":
        _render_translation_report(
            report,
            st.session_state.report_filename,
        )
    elif _report_type == "DesignAnalysisResult":
        _render_design_report(
            report,
            st.session_state.report_filename,
        )
    elif _report_type == "LabelStructureCheckResult":
        _render_structure_report(
            report,
            st.session_state.report_filename,
        )
    elif _report_type == "LinguisticCheckResult":
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
