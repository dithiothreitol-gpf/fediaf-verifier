"""System prompts for FEDIAF label verification — 2-call architecture."""

# -- CALL 1: Extraction prompt --------------------------------------------------------
# Simple: "describe what you see". No compliance judgments.

EXTRACTION_PROMPT = """\
Przeanalizuj etykiete karmy dla zwierzat domowych i wyekstrahuj WSZYSTKIE widoczne dane.
NIE oceniaj zgodnosci — tylko opisz co widzisz na etykiecie.

Dokument moze byc wielostronicowy (specyfikacja, karta produktu). \
Znajdz i analizuj TYLKO sekcje dotyczace etykiety: sklad, skladniki analityczne, \
dane producenta. Ignoruj strony z notatkami wewnetrznymi, kosztorysami, logistyka.
Jesli dokument zawiera wiele produktow — analizuj PIERWSZY produkt.

Odpowiedz WYLACZNIE poprawnym JSON (bez markdown, bez tekstu przed/po). Badz zwiezly.

Pola:
product_name, brand, species (surowy tekst np. "pies"/"dog"), \
lifestage (surowy tekst np. "adult"/"dorosly"), \
food_type_text (surowy tekst np. "karma sucha"), net_weight,
crude_protein/fat/fibre/moisture/crude_ash/calcium/phosphorus (liczby % as-fed lub null),
ingredients (lista skladnikow w kolejnosci z etykiety),
has_feeding_guidelines, has_storage_instructions, has_ingredients_list, \
has_analytical_constituents, has_manufacturer_info, has_net_weight, \
has_species_stated, has_batch_number, has_best_before_date, \
has_recycling_symbols, has_barcode, has_qr_code, has_species_emblem, \
has_date_marking_area, has_country_of_origin, has_e_symbol, \
has_establishment_number, has_free_contact_info, \
has_compliance_statement, has_gmo_declaration (wszystkie bool),
product_classification_text (surowy tekst np. "karma pelnoporcjowa"),
claims (lista claimow np. ["bez zboz", "70% miesa"]),
is_raw_product, has_raw_warnings, contains_insect_protein, \
has_insect_allergen_warning (bool),
extraction_confidence ("HIGH"/"MEDIUM"/"LOW"), \
values_requiring_check (lista),
font_legibility_ok (bool), font_legibility_notes,
languages_detected (lista np. ["pl","en"]), translations_complete, \
country_codes_present, polish_text_complete (bool)."""

# -- CALL 2: Secondary check (cross-check + linguistic) -------------------------------

SECONDARY_CHECK_PROMPT = """\
Wykonaj DWA niezalezne zadania na tej etykiecie:

ZADANIE 1 — WERYFIKACJA KRZYZOWA WARTOSCI:
Odczytaj PONOWNIE wartosci z tabeli 'Skladniki analityczne' / \
'Analytical constituents'. Podaj je DOKLADNIE tak jak sa napisane — \
bez obliczen, bez konwersji. Jesli nieczytelne — null.

ZADANIE 2 — WERYFIKACJA JEZYKOWA:
Sprawdz caly tekst na etykiecie pod katem:
- Ortografia (literowki, bledne zapisy)
- Znaki diakrytyczne (brakujace: a->a, e->e, s->s, c->c, z->z, l->l, n->n, o->o)
- Gramatyka (bledna odmiana, skladnia)
- Interpunkcja
- Spojnosc terminologii (mieszanie jezykow w jednym bloku, np. "bialko" obok "protein")
Automatycznie wykryj jezyk(i).
WAZNE: Pole "original" = DOKLADNA kopia tekstu z etykiety (z diakrytykami \
jesli widoczne). ZANIM zgloszisz brak diakrytyku — PRZYJRZYJ SIE uwaznie \
czy znak RZECZYWISCIE brakuje. Jesli nie jestes pewny — nie zglaszaj. \
Kazdy fragment zglaszaj MAX RAZ (bez duplikatow). \
NIE zglaszaj: tekstu poprawnego, celowej kapitalizacji w claimach, \
celowych zapisow dwujezycznych.

Odpowiedz WYLACZNIE poprawnym JSON (bez markdown). Badz ZWIEZLY — krotkie opisy, max 10 najwazniejszych bledow jezykowych. Pola:
cross_crude_protein/fat/fibre/moisture/crude_ash/calcium/phosphorus (liczby lub null),
cross_reading_notes,
detected_language (np. "pl"), detected_language_name (np. "polski"),
linguistic_issues (lista: [{issue_type, original, suggestion, context, explanation}]),
overall_language_quality ("excellent"/"good"/"needs_review"/"poor"),
language_summary."""

# -- Standalone linguistic check prompt ------------------------------------------------

LINGUISTIC_ONLY_PROMPT = """\
Sprawdz caly widoczny tekst na tej etykiecie karmy dla zwierzat pod katem:

1. ORTOGRAFIA — literowki, bledne zapisy slow
2. ZNAKI DIAKRYTYCZNE — brakujace lub bledne: \
a→ą, e→ę, s→ś, c→ć, z→ź/ż, l→ł, n→ń, o→ó
3. GRAMATYKA — bledna odmiana, skladnia, koncowki
4. INTERPUNKCJA — brak/nadmiar przecinkow, kropek, dwukropkow
5. SPOJNOSC TERMINOLOGII — mieszanie jezykow w jednym bloku \
(np. "bialko" obok "protein"), niespojne nazewnictwo

Automatycznie wykryj jezyk(i) na etykiecie.
Badz dokladny — sprawdz KAZDY fragment tekstu.

KRYTYCZNE ZASADY — przeczytaj zanim zaczniesz:

1. DOKLADNOSC TRANSKRYPCJI — w polu "original" wpisuj tekst DOKLADNIE \
tak jak widnieje na etykiecie, litera po literze. \
Jesli na obrazie widzisz "Składniki" ze znakiem ł — wpisz "Składniki". \
NIE zamieniaj liter na ich odpowiedniki bez diakrytykow. \
Pole "original" musi byc WIERNYM odwzorowaniem tego co jest na etykiecie.

2. WERYFIKACJA PRZED ZGLOSZENIEM — zanim zgloszisz brak diakrytyku, \
PRZYJRZYJ SIE UWAZNIE danemu slowu na obrazie. \
Znaki ł/l, ą/a, ę/e, ó/o moga byc trudne do rozroznienia przy malym foncie. \
Jesli NIE JESTES PEWNY czy znak diakrytyczny jest obecny — NIE zglaszaj. \
Lepiej pominac watpliwy przypadek niz zglaszac false positive.

3. BEZ DUPLIKATOW — kazdy fragment tekstu zglaszaj MAKSYMALNIE RAZ. \
Jesli "Skladniki" wystepuje 5 razy bez diakrytykow — zglos to RAZ \
z adnotacja ile razy wystepuje, nie 5 osobnych issues.

4. TYLKO BLEDY — nie umieszczaj w liście issues elementow poprawnych. \
Jesli tekst jest prawidlowy — nie dodawaj go.

5. KONWENCJE BRANZY PET FOOD — nie zglaszaj:
- Celowej kapitalizacji w claimach (np. "bez Soi", "bez GMO")
- Celowych zapisow dwujezycznych w ikonach/badge'ach
- Formatow wielojezycznych w polach formalnych

Odpowiedz WYLACZNIE poprawnym JSON (bez markdown). Pola:
detected_language (np. "pl"), detected_language_name (np. "polski"),
issues (lista: [{issue_type, original, suggestion, context, explanation}]),
issue_type: "spelling"/"grammar"/"punctuation"/"diacritics"/"terminology",
overall_quality ("excellent"/"good"/"needs_review"/"poor"),
summary (krotkie podsumowanie jakosci tekstu)."""

# -- Self-verification prompt (reflection step) ----------------------------------------

SELF_VERIFY_PROMPT = """\
Jestes recenzentem jakosci AI. Otrzymujesz:
1. ORYGINALNY OBRAZ etykiety
2. WYNIK ANALIZY w formacie JSON wygenerowany przez inny model AI

Twoje zadanie: ZWERYFIKUJ kazdy element wyniku porownujac go z tym \
co RZECZYWISCIE widac na obrazie. Szukaj:

A) FALSE POSITIVE — zgloszono problem ktorego NIE MA na obrazie:
   - Zgloszono brak diakrytyku ale na obrazie diakrytyk JEST widoczny
   - Zgloszono blad ortograficzny ale slowo jest poprawne
   - Zgloszono niezgodnosc ktora nie istnieje
   - Pole "original" nie odpowiada temu co jest na obrazie

B) DUPLIKATY — ten sam problem zgloszony wiecej niz raz

C) HALUCYNACJE — zgloszono tekst ktory w ogole nie wystepuje na etykiecie

Dla KAZDEGO elementu w wyniku:
- POROWNAJ z obrazem
- Jesli element jest POPRAWNY — zachowaj go
- Jesli element jest FALSE POSITIVE — USUN go
- Jesli pole "original" jest bledne — POPRAW je

WAZNE: Badz SUROWY. Lepiej usunac watpliwy element niz zostawic false positive.
W razie watpliwosci — USUN.

Zwroc POPRAWIONY wynik w IDENTYCZNYM formacie JSON jak wejscie \
(te same pola, ta sama struktura). Nie dodawaj nowych pol. \
Usun false-positive elementy z list. Zaktualizuj summary/quality \
jesli lista bledow sie zmienila.

WYNIK DO WERYFIKACJI (JSON poniżej):"""

# -- Targeted re-read prompt (OCR false-positive reduction) ----------------------------


def build_targeted_reread_prompt(words_json: str) -> str:
    """Build targeted re-read prompt with words to verify.

    Uses string concatenation (not .format()) to avoid issues
    with JSON curly braces in the prompt.
    """
    return (
        TARGETED_REREAD_PROMPT_PREFIX
        + "\n\n"
        + words_json
        + "\n\n"
        + TARGETED_REREAD_PROMPT_SUFFIX
    )


TARGETED_REREAD_PROMPT_PREFIX = """\
Jestes ekspertem od OCR. Otrzymujesz OBRAZ etykiety oraz liste SLOW, \
ktore zostaly zidentyfikowane jako potencjalne bledy ortograficzne. \
Twoje JEDYNE zadanie: odczytac PONOWNIE kazde z tych slow BEZPOSREDNIO \
z obrazu, litera po literze.

DLA KAZDEGO SLOWA:
1. Znajdz je na obrazie (uzyj podanego kontekstu do lokalizacji)
2. Odczytaj KAZDA litere osobno, uwzgledniajac znaki diakrytyczne
3. Podaj DOKLADNY odczyt z obrazu
4. Okresl czy slowo na obrazie jest POPRAWNE czy BLEDNE

KRYTYCZNE ZASADY:
- Patrzysz NA OBRAZ, nie na tekst ponizej — obraz jest zrodlem prawdy
- Kazda litera osobno — nie "domyslaj sie" calego slowa z kontekstu
- Znaki diakrytyczne (ą,ę,ś,ć,ź,ż,ł,ń,ó) — sprawdz BARDZO uwaznie \
czy sa obecne na obrazie
- Jesli nie mozesz odczytac slowa — wpisz "NIECZYTELNE"
- NIE poprawiaj tekstu — podaj DOKLADNIE co widzisz na obrazie
- Jesli na obrazie widzisz poprawne slowo (np. "Wartości" a nie "Waości") \
to znaczy ze pierwotny odczyt byl bledny — ustaw is_correct_on_image=true

SLOWA DO WERYFIKACJI:"""

TARGETED_REREAD_PROMPT_SUFFIX = """\
Odpowiedz WYLACZNIE poprawnym JSON (bez markdown):
{"reread_results": [
  {"original_flagged": "slowo zgloszne jako bledne", \
"context": "kontekst z etykiety", \
"reread_from_image": "co DOKLADNIE widzisz na obrazie", \
"is_correct_on_image": true/false, \
"confidence": "high"/"medium"/"low", \
"notes": "krotki komentarz"}
]}"""

# -- Label structure & font completeness check prompt ---------------------------------

LABEL_STRUCTURE_PROMPT = """\
Przeanalizuj etykiete karmy dla zwierzat pod katem STRUKTURY SEKCJI JEZYKOWYCH \
oraz KOMPLETNOSCI ZNAKOW W CZCIONCE.

KONTEKST: Etykiety wielojezykowe tworzone sa w Adobe Illustratorze. \
Kazdy jezyk ma oddzielna sekcje oznaczona markerem jezykowym \
(flaga, kod kraju np. PL/DE/EN/FR/CZ/HU/RO, ikona lub tekst). \
Podczas edycji czesto zdarzaja sie bledy: gina markery, pojawiaja sie luki, \
tekst z jednej sekcji "wlewa sie" do drugiej, a czcionka moze nie miec \
wszystkich znakow diakrytycznych — powodujac puste miejsca, "kwadraciki" (tofu) \
lub brakujace znaki.

ZADANIE 1 — STRUKTURA SEKCJI JEZYKOWYCH:
Dla KAZDEJ sekcji jezykowej widocznej na etykiecie podaj:
- Kod jezyka (ISO 639-1)
- Pelna nazwa jezyka
- Czy marker/emblemat jezykowy jest widoczny i jaki jest (flaga, kod, tekst, ikona)
- Dokladny tekst/opis markera tak jak widoczny na etykiecie
- Czy sekcja zawiera tresc (content_present)
- Czy tresc wyglada na kompletna (content_complete)
- Jakie elementy etykiety sa obecne w danej sekcji \
(ingredients, analytical_constituents, feeding_guidelines, \
storage_instructions, manufacturer_info, product_description, warnings)
- Jakie elementy BRAKUJA w tej sekcji ale sa obecne w innych sekcjach
Szukaj takze:
- Tekstu "osieroconego" — fragmentow miedzy sekcjami nie przypisanych do zadnego jezyka
- Uszkodzonych/nieczytelnych markerow
- Niespojnego porzadku sekcji (np. DE ma inne elementy niz PL)
- Brakujacych sekcji jezykowych (marker jest ale brak tresci lub odwrotnie)
- Duplikatow markerow

ZADANIE 2 — KOMPLETNOSC ZNAKOW W CZCIONCE:
Sprawdz KAZDA sekcje jezykowa pod katem znakow specjalnych/diakrytycznych:
- POLSKI: ą ę ś ć ź ż ł ń ó Ą Ę Ś Ć Ź Ż Ł Ń Ó
- NIEMIECKI: ä ö ü ß Ä Ö Ü
- CZESKI: ř š č ž ů ú ý á é í ě ň ť ď Ř Š Č Ž
- WEGIERSKI: á é í ó ö ő ú ü ű Á É Í Ó Ö Ő Ú Ü Ű
- RUMUNSKI: ă â î ș ț Ă Â Î Ș Ț
- FRANCUSKI: é è ê ë à â ù û ç ô î ï É È Ê Ë À Â
- WLOSKI: à è é ì ò ù À È É Ì Ò Ù
- HISZPANSKI: ñ á é í ó ú ü Ñ Á É Í Ó Ú Ü ¿ ¡
Dla kazdego jezyka sprawdz czy:
- Znaki diakrytyczne sa WIDOCZNE i poprawnie wyrenderowane
- Nie ma "kwadracikow" (tofu/missing glyph boxes) zamiast znakow
- Nie ma pustych miejsc / luk tam gdzie powinien byc znak diakrytyczny
- Nie ma zamiany znakow diakrytycznych na ich podstawowe odpowiedniki \
(np. "a" zamiast "ą", "s" zamiast "ś")
- Nie ma bledow enkodowania (np. "Ä…" zamiast "ą", "Å›" zamiast "ś")

ZADANIE 3 — LOKALIZACJA PROBLEMOW (WSPOLRZEDNE):
Dla KAZDEGO wykrytego problemu (structure_issues i glyph_issues) podaj \
przyblizone wspolrzedne prostokatu (bounding box) na obrazie etykiety. \
Wspolrzedne podawaj jako wartosci ZNORMALIZOWANE 0-1000, gdzie:
- (0, 0) = lewy gorny rog obrazu
- (1000, 1000) = prawy dolny rog obrazu
- bbox = [x, y, width, height] — x,y to lewy gorny rog prostokata
Jesli nie mozesz dokladnie okreslic pozycji — podaj najlepsza przyblizenie. \
Jesli w ogole nie jestes w stanie — podaj null.

Odpowiedz WYLACZNIE poprawnym JSON (bez markdown). Pola:
languages_expected (lista kodow jezykow wykrytych na etykiecie),
language_sections (lista: [{language_code, language_name, marker_present, \
marker_type ("flag"/"code"/"text"/"icon"/"none"), marker_text, \
content_present, content_complete, \
section_elements (lista), missing_elements (lista), notes, \
bbox ([x, y, w, h] znormalizowane 0-1000 lub null)}]),
structure_issues (lista: [{issue_type \
("missing_marker"/"orphaned_text"/"section_overlap"/"section_gap"/\
"marker_damaged"/"inconsistent_order"/"missing_section"/"duplicate_marker"), \
description, affected_languages (lista kodow), \
severity ("critical"/"warning"/"info"), location, \
bbox ([x, y, w, h] znormalizowane 0-1000 lub null)}]),
glyph_issues (lista: [{language_code, \
issue_type ("missing_glyph"/"substituted_glyph"/"blank_space"/\
"tofu_box"/"wrong_diacritic"/"encoding_error"), \
affected_text, expected_text, missing_characters (lista), location, explanation, \
bbox ([x, y, w, h] znormalizowane 0-1000 lub null)}]),
diacritics_check (obiekt: kod_jezyka -> bool, np. {"pl": false, "de": true}),
overall_status ("ok"/"warnings"/"errors"),
summary (krotkie podsumowanie po polsku),
section_count (ile sekcji jezykowych),
font_issues_count (ile problemow z czcionka/glifami)."""

# -- Market trends prompt (optional, uses web_search) ---------------------------------


def build_trend_instruction(market: str) -> str:
    """Build the market trends analysis instruction for the given country."""
    return f"""\
Uzyj narzedzia web_search aby wyszukac aktualne trendy rynkowe \
dla tej kategorii produktu w: {market}.

Na podstawie wynikow wyszukiwania podaj JSON:
country, summary (2-4 zdania), \
positioning ("trendy"/"standard"/"outdated"/"niche"), \
trend_notes (lista obserwacji)."""


# -- Translation prompt (dynamic — target language + user notes) -----------------------


def build_translation_prompt(
    target_language: str,
    target_language_name: str,
    user_notes: str = "",
    source_text: str = "",
) -> str:
    """Build translation prompt for label content.

    Args:
        target_language: ISO 639-1 code (e.g. "en", "de").
        target_language_name: Full name (e.g. "English", "Deutsch").
        user_notes: Optional user instructions for translation.
        source_text: If provided, text to translate (no image).
    """
    text_block = ""
    if source_text:
        text_block = (
            f"\n\nTEKST DO PRZETLUMACZENIA:\n"
            f'"""\n{source_text}\n"""\n'
        )

    notes_block = ""
    if user_notes.strip():
        notes_block = (
            f"\n\nDODATKOWE INSTRUKCJE OD UZYTKOWNIKA:\n{user_notes.strip()}\n"
        )

    return f"""\
Przetlumacz tresc etykiety karmy dla zwierzat domowych \
na jezyk: {target_language_name} ({target_language}).
{text_block}
ZASADY TLUMACZENIA:
- Wykryj jezyk zrodlowy automatycznie
- Podziel tresc na logiczne sekcje (sklad, skladniki analityczne, \
dawkowanie, przechowywanie, producent, opis produktu, claimy, ostrzezenia)
- Uzywaj oficjalnej terminologii regulacyjnej EU 767/2009 w jezyku docelowym:
  * "Skladniki analityczne" = "Analytical constituents" (EN) / \
"Analytische Bestandteile" (DE) / "Composants analytiques" (FR)
  * "Karma pelnoporcjowa" = "Complete feed" (EN) / "Alleinfuttermittel" (DE) / \
"Aliment complet" (FR)
  * "Dodatki" = "Additives" (EN) / "Zusatzstoffe" (DE) / "Additifs" (FR)
  * "Surowe bialko" = "Crude protein" (EN) / "Rohprotein" (DE) / \
"Proteine brute" (FR)
- Zachowaj DOKLADNIE: liczby, procenty, jednostki, nazwy marek, \
numery partii, daty, kody
- NIE tlumacz: nazwy wlasne marek, numery rejestracyjne, kody EAN
- Zachowaj formatowanie i strukture oryginalnego tekstu
- Jesli termin jest niejednoznaczny — dodaj uwage w polu "notes"
{notes_block}
Odpowiedz WYLACZNIE poprawnym JSON (bez markdown). Pola:
source_language (kod ISO np. "pl"), source_language_name (np. "polski"),
target_language ("{target_language}"), target_language_name ("{target_language_name}"),
sections (lista: [{{section_name, original_text, translated_text, notes}}]),
overall_notes (ogolne uwagi dotyczace tlumaczenia),
summary (krotkie podsumowanie w jezyku docelowym)."""


# -- Graphic design analysis prompt ----------------------------------------------------

DESIGN_ANALYSIS_PROMPT = """\
Przeanalizuj projekt etykiety karmy dla zwierzat domowych \
jako PROFESJONALISTA od designu opakowan w branzy pet food. \
Raport jest przeznaczony dla dzialu R&D — rekomendacje musza byc \
KONKRETNE i WYKONALNE (np. "zwieksz font dawkowania z ~6pt do min 8pt" \
zamiast "popraw czytelnosc").

Ocen nastepujace 10 KATEGORII w skali 0-100:

1. HIERARCHIA WIZUALNA (visual_hierarchy)
Czy nazwa produktu jest dominujaca? Czy kluczowe sekcje sa latwe do znalezienia? \
Jak wyglada naturalny flow czytania?

2. CZYTELNOSC (readability)
Rozmiary fontow, kontrast tekst-tlo, interlinia, czytelnosc z odleglosci 30cm. \
Czy tekst regulacyjny (sklad, tabela) jest czytelny?

3. UZYCIE KOLORU (color_usage)
Spojnosc palety z marka, psychologia koloru (apetycznosc, zaufanie), \
wyroznienie na polce wsrod konkurencji.

4. KOMPOZYCJA I UKLAD (layout_composition)
Balans elementow, whitespace, gestosc informacji, siatka/grid.

5. ELEMENTY OBOWIAZKOWE (regulatory_placement)
Czy tabela skladnikow analitycznych, lista skladnikow, dane producenta, \
masa netto, gatunek, partia/data sa wlasciwie umieszczone i czytelne?

6. WPLYW POLKOWY (shelf_impact)
Rozpoznawalnosc z dystansu 1-2m, wyroznienie na tle konkurencji, \
facing design (widok frontalny).

7. FOTOGRAFIA I GRAFIKA (imagery)
Jakosc zdjec/ilustracji, apetycznosc, trafnosc (czy pasuje do produktu), \
spojnosc stylu graficznego.

8. GRUPA DOCELOWA (target_audience)
Sygnaly premium vs economy vs standard, dopasowanie do pozycjonowania produktu, \
czy design przemawia do wlascicieli zwierzat w docelowym segmencie.

9. SYGNALY EKOLOGICZNE (sustainability)
Ikony recyklingu, komunikacja ekologiczna, materialy opakowania, \
zielone claimy — obecnosc i wiarygodnosc.

10. UKLAD WIELOJEZYCZNY (multilanguage_layout)
Organizacja tresci wielojezycznych, czytelnosc per jezyk, \
hierarchia jezykow, separatory/markery.

DLA KAZDEJ KATEGORII podaj:
- score (0-100)
- findings (lista obserwacji — co widzisz)
- recommendations (lista konkretnych rekomendacji)

DODATKOWO podaj:
- Konkretne PROBLEMY (issues) z severity: critical/major/minor/suggestion
- MOCNE STRONY (strengths) — co etykieta robi dobrze
- BENCHMARK KONKURENCYJNY — jak etykieta wypada na tle standardow branzy pet food
- TRENDY BRANZOWE — ktore aktualne trendy sa widoczne / ktorych brakuje
- PODSUMOWANIE DLA R&D — 3-5 najwazniejszych akcji do podjecia

Rubryk oceny:
- 80-100: Doskonale, wzorcowe w branzy
- 60-79: Dobre, spelnia standardy
- 40-59: Wymaga poprawy
- 0-39: Powazne problemy

Odpowiedz WYLACZNIE poprawnym JSON (bez markdown). Pola:
overall_score (0-100), overall_assessment (1-2 zdania),
category_scores (lista: [{{category, category_name, score, findings (lista), \
recommendations (lista)}}]),
issues (lista: [{{category, description, severity \
("critical"/"major"/"minor"/"suggestion"), location, recommendation}}]),
strengths (lista stringow),
competitive_benchmarks (lista: [{{aspect, current_level, industry_standard, \
suggestion}}]),
trend_alignment (lista stringow),
actionable_summary (podsumowanie dla R&D — konkretne akcje)."""


# -- Artwork inspection AI summary prompt -----------------------------------------------


def build_artwork_summary_prompt(findings_json: str) -> str:
    """Build prompt for AI to summarize deterministic artwork inspection findings.

    The AI receives structured JSON with pixel diff, color analysis, and
    print readiness results and produces a human-readable summary with
    actionable recommendations in Polish.

    Args:
        findings_json: JSON string with ArtworkInspectionReport data
            (pixel_diff, color_analysis, print_readiness sub-reports).
    """
    return f"""\
Jestes ekspertem od kontroli jakosci opakowan (artwork QA) w branzy pet food. \
Otrzymujesz wyniki DETERMINISTYCZNEJ inspekcji artwork etykiety — \
dane sa obiektywne (SSIM, Delta E, DPI, przestrzen barw).

Twoje zadanie:
1. Przeanalizuj wyniki i napisz ZWIEZLE podsumowanie po polsku (3-5 zdan)
2. Podaj liste KONKRETNYCH, WYKONALNYCH rekomendacji (max 7)
3. Skup sie na problemach ISTOTNYCH dla druku i produkcji

WYNIKI INSPEKCJI (JSON):
{findings_json}

WAZNE:
- Nie powtarzaj surowych danych liczbowych — interpretuj je
- Uzyj jezyka zrozumialego dla dzialu R&D / grafika
- Priorytetyzuj: najpierw problemy krytyczne (DPI, fonty), potem ostrzezenia
- Jesli SSIM > 0.99 i brak problemow — powiedz krotko ze jest OK
- Delta E < 2 = niezauwazalne, 2-5 = drobna roznica, >5 = widoczna zmiana
- DPI < 150 = krytyczne, 150-299 = ostrzezenie, >=300 = OK
- RGB zamiast CMYK = ostrzezenie (kolory moga sie roznic po druku)

Odpowiedz WYLACZNIE poprawnym JSON (bez markdown):
{{"ai_summary": "...", "ai_recommendations": ["...", "..."]}}"""


# -- Per-market compliance check prompt -------------------------------------------------


def build_market_check_prompt(market_code: str, market_name: str) -> str:
    """Build prompt for per-market regulatory compliance check.

    Loads rules from market_rules.py and asks AI to verify the label
    against base EU 767/2009 plus country-specific requirements.

    Args:
        market_code: ISO 3166-1 alpha-2 code (e.g. "DE", "FR").
        market_name: Full market name (e.g. "Niemcy", "Francja").
    """
    from fediaf_verifier.market_rules import MARKET_RULES

    rules = MARKET_RULES.get(market_code, {})
    regulations = rules.get("regulations", [])
    language_required = rules.get("language_required", "")

    # Format regulations list for prompt
    rules_text = ""
    for reg in regulations:
        rules_text += (
            f"- [{reg['id']}] ({reg['category']}): {reg['desc']}\n"
        )

    if not rules_text:
        rules_text = (
            "  Brak szczegolowych regul — sprawdz ogolne wymagania EU.\n"
        )

    return f"""\
Przeanalizuj etykiete karmy dla zwierzat domowych pod katem \
ZGODNOSCI REGULACYJNEJ na rynku: {market_name} ({market_code}).

ZADANIE 1 — BAZOWA ZGODNOSC EU 767/2009:
Sprawdz czy etykieta spelnia podstawowe wymagania Rozporzadzenia (WE) nr 767/2009:
- Lista skladnikow w kolejnosci malejacej
- Skladniki analityczne (surowe bialko, tluszcz, wlokno, popioly)
- Dane producenta / osoby odpowiedzialnej
- Masa netto / ilosc
- Gatunek zwierzecia docelowego
- Instrukcja dawkowania
- Numer partii lub data produkcji
- Termin przydatnosci

ZADANIE 2 — WYMAGANIA SPECYFICZNE DLA RYNKU {market_code}:
Jezyk wymagany: {language_required}

Sprawdz ponizsze wymagania specyficzne dla {market_name}:
{rules_text}
Dla KAZDEGO wymagania podaj:
- Czy etykieta jest zgodna (compliant: true/false)
- Co znaleziono na etykiecie (finding)
- Rekomendacje naprawcze (recommendation)
- Waznosc problemu (severity: critical/warning/info)

ZADANIE 3 — JEZYK:
Sprawdz czy tresc etykiety jest dostepna w wymaganym jezyku ({language_required}):
- Czy pelna tresc jest przetlumaczona
- Czy terminologia regulacyjna jest poprawna w danym jezyku
- Czy znaki diakrytyczne specyficzne dla tego jezyka sa poprawne
- Czy nie brakuje kluczowych sekcji w wymaganym jezyku

ZADANIE 4 — CERTYFIKATY:
Jesli na etykiecie widoczne sa claimy (bio, eco, organic, natural, grain-free, itp.) \
sprawdz czy wymagane certyfikaty sa obecne dla rynku {market_code}.

Odpowiedz WYLACZNIE poprawnym JSON (bez markdown). Pola:
target_market ("{market_name}"),
target_market_code ("{market_code}"),
base_eu_compliant (bool),
market_specific_requirements (lista: [{{requirement_id, category, description, \
regulation_reference, compliant (bool), finding, recommendation, \
severity ("critical"/"warning"/"info")}}]),
language_requirements_met (bool),
language_notes (string),
additional_certifications_recommended (lista stringow),
overall_compliance ("compliant"/"issues_found"/"non_compliant"),
score (0-100),
summary (krotkie podsumowanie po polsku)."""


# -- EAN/barcode extraction prompt -----------------------------------------------------

EAN_EXTRACTION_PROMPT = """\
Odczytaj WSZYSTKIE kody kreskowe i kody QR widoczne na etykiecie.

Dla KAZDEGO kodu kreskowego podaj:
- barcode_number: cyfry odczytane z kodu (dokladnie, cyfra po cyfrze)
- barcode_type: "EAN-13" (13 cyfr), "EAN-8" (8 cyfr), "UPC-A" (12 cyfr), \
lub "unknown" jesli nie mozesz okreslic
- barcode_readable: true jesli mozesz odczytac cyfry, false jesli nieczytelny

Dla KAZDEGO kodu QR podaj:
- present: true
- readable: true jesli mozesz odczytac zawartosc
- content: tekst/URL zawarty w QR (jesli czytelny)
- notes: uwagi

Jesli na etykiecie NIE MA kodow kreskowych ani QR — zwroc puste listy.

Odpowiedz WYLACZNIE poprawnym JSON (bez markdown). Pola:
barcodes (lista: [{{barcode_number, barcode_type, barcode_readable}}]),
qr_codes (lista: [{{present, readable, content, notes}}]),
summary (krotkie podsumowanie)."""


# -- Claims vs Composition check prompt ----------------------------------------

CLAIMS_CHECK_PROMPT = """\
Przeanalizuj etykiete karmy dla zwierzat domowych pod katem \
SPOJNOSCI CLAIMOW MARKETINGOWYCH Z RZECZYWISTYM SKLADEM.

ZADANIE 1 — EKSTRAKCJA:
- Wyekstrahuj WSZYSTKIE claimy/deklaracje marketingowe z etykiety \
(np. "bez zboz", "70% miesa", "bogaty w kurczaka", "wspiera stawy", \
"grain free", "hypoallergenic", "sensitive", itp.)
- Wyekstrahuj liste skladnikow WRAZ Z PROCENTAMI (jesli podane)
- Wyekstrahuj nazwe produktu (do weryfikacji reguly % w nazwie)
- Wyekstrahuj istotne wartosci odzywcze ze skladnikow analitycznych

ZADANIE 2 — WERYFIKACJA KAZDEGO CLAIMU:
Dla kazdego znalezionego claimu sprawdz czy jest SPOJNY ze skladem:
- Claimy procentowe: czy podany % sklada sie z rzeczywistego skladu?
- Claimy "bez X": czy skladnik X faktycznie NIE wystepuje w skladzie?
- Claimy o wyroznionym skladniku: czy skladnik jest obecny i w odpowiedniej ilosci?
- Claimy odzywcze: czy wartosci analityczne potwierdzaja claim?

ZADANIE 3 — REGULA PROCENTOWA W NAZWIE (EU 767/2009):
Sprawdz nazwe produktu pod katem regul nazewnictwa:
- "z X" (np. "z kurczakiem") = min 4% skladnika X
- "bogaty w X" / "bogata w X" = min 14% skladnika X
- X jako glowna nazwa (np. "Kurczak dla psa") = min 26% skladnika X
Jesli regula nie ma zastosowania — naming_rule_check = null.

ZADANIE 4 — CLAIM "BEZ ZBOZ" / "GRAIN FREE":
Jesli etykieta deklaruje "bez zboz" / "grain free" / "bezzbozowa":
- Sprawdz liste skladnikow pod katem: pszenica, jeczmien, owies, zyto, \
kukurydza, ryz, proso, sorgo, orkisz, wheat, barley, oat, rye, corn, \
maize, rice, millet, sorghum, spelt, cereals, grains
- Jesli brak claimu — grain_free_check_passed = null

ZADANIE 5 — CLAIMY TERAPEUTYCZNE (ZABRONIONE):
Wykryj claimy sugerujace dzialanie lecznicze lub terapeutyczne \
(zabronione per EU 767/2009 Art.13):
- "leczy", "zapobiega", "likwiduje", "eliminuje choroby"
- "zastepuje leczenie weterynaryjne"
- "terapeutyczny", "leczniczy", "medyczny"
UWAGA: dopuszczalne sa claimy funkcjonalne (np. "wspiera trawienie", \
"zdrowa siersc") — to NIE SA claimy terapeutyczne.

Odpowiedz WYLACZNIE poprawnym JSON (bez markdown). Badz ZWIEZLY. Pola:
claims_found (lista stringow — wszystkie znalezione claimy),
ingredients_with_percentages (lista stringow np. ["kurczak 30%", "ryz 15%"]),
claim_validations (lista: [{{claim_text, claim_category \
("percentage"/"grain_free"/"ingredient_highlight"/"nutritional"/\
"naming_rule"/"therapeutic"/"other"), \
is_consistent (bool), inconsistency_description, \
relevant_ingredients (lista), severity ("critical"/"warning"/"info"), \
recommendation}}]),
naming_rule_check ({{product_name, trigger_word, required_minimum_percent, \
ingredient_name, actual_percent (float lub null), compliant (bool), notes}} \
lub null jesli regula nie ma zastosowania),
grain_free_check_passed (bool lub null),
grain_ingredients_found (lista stringow),
therapeutic_claims_found (lista stringow),
overall_consistency ("consistent"/"inconsistencies_found"/"critical_issues"),
score (0-100, gdzie 100 = pelna spojnosc),
summary (krotkie podsumowanie po polsku)."""


# -- Commercial presentation compliance prompt ----------------------------------


PRESENTATION_CHECK_PROMPT = """\
Przeanalizuj etykiete karmy dla zwierzat domowych pod katem \
ZGODNOSCI PREZENTACJI HANDLOWEJ z przepisami EU 767/2009, \
FEDIAF Code of Good Labelling Practice i regulacjami krajowymi.

EKSTRAKCJA KONTEKSTU:
- Wyekstrahuj nazwe produktu, nazwe marki, klasyfikacje produktu \
(pelnoporcjowa/uzupelniajaca), typ karmy (sucha/mokra/polwilgotna), \
gatunek docelowy, etap zycia, liste skladnikow z procentami (jesli podane), \
liste dodatkow technologicznych i konserwantow.

SEKCJA 1 — RECEPTURY (recipe-level claims):
Znajdz i zweryfikuj KAZDY claim zwiazany z receptura:
- "oryginalna receptura", "nowa ulepszona formula" — czy uzasadniony? \
Jesli brak dowodu na porownanie z poprzednia wersja = warning.
- "Receptura opracowana przez weterynarzy" / "vet-formulated" — \
czy jest dowod (logo organizacji weterynaryjnej, podpis)? Jesli nie = warning.
- "Monobialkowa receptura" / "Single protein" — sprawdz czy faktycznie jest \
jedno zrodlo bialka w skladzie. Uwzglednij bialka ukryte w dodatkach \
(np. hydrolizat bialkowy, maczka rybna). Jesli wiele zrodel = critical.
- Klasyfikacja pelnoporcjowa vs uzupelniajaca — czy receptura spelnia wymogi \
FEDIAF dla karmy pelnoporcjowej? Jesli deklaracja "complete" ale brak \
kluczowych skladnikow odzywczych = critical.
- "Bez sztucznych konserwantow/barwnikow/aromatow" — sprawdz liste dodatkow \
technologicznych. Naturalne konserwanty (tokoferole, ekstrakt rozmarynu) \
i witaminy/mineraly sa dozwolone i NIE naruszaja tego claimu.
- Claimy procentowe o swiezym miesie (np. "70% swiezego miesa") — \
czy sklad to potwierdza? Pamietaj: "swiezy" oznacza przed obrobka, \
po wysuszeniu moze byc 3-4x mniej.
Dla kazdego claimu podaj: claim_text, claim_type \
("original_recipe"/"vet_developed"/"single_protein"/\
"complete_vs_complementary"/"no_artificial"/"fresh_meat_percentage"/"other"), \
compliant (bool), regulation_reference, finding, issue_description, \
recommendation, severity ("critical"/"warning"/"info").
recipe_section_score: 0-100.

SEKCJA 2 — NAZWY (EU 767/2009 Art.17 + FEDIAF CoGLP):
A) REGULY PROCENTOWE — dla KAZDEGO skladnika wyroznionego w nazwie produktu:
- Regula 100%: nazwa = sam skladnik (np. "Kurczak") = 95-100% tego skladnika \
(w karmie mokrej) lub praktycznie wylacznie ten skladnik
- Regula 26%: nazwa z opisem (np. "Obiad z kurczakiem", "Chicken Dinner") \
= min 26% kurczaka
- Regula 14%: "bogaty w X" / "rich in X" / "bogata w X" = min 14% skladnika X
- Regula 4%: "z X" / "with X" / "ze smakiem X" = min 4% skladnika X
- Ponizej 4%: "smak X" / "X flavour" = dopuszczalne bez minimalnego %
Dla KAZDEGO wyroznionego skladnika podaj: product_name, \
highlighted_ingredient, trigger_expression, applicable_rule \
("100_pct"/"26_pct"/"14_pct"/"4_pct"/"flavour"/"none"), \
required_minimum_percent, actual_percent (float lub null), compliant (bool), notes.

B) SPOJNOSC NAZWY — sprawdz:
- Nazwa vs typ karmy: np. "pasztet" / "pate" ale to karma sucha = niespojne (critical)
- Nazwa vs gatunek: np. produkt "Cat Delight" ale brak oznaczenia gatunku na etykiecie
- Nazwa vs etap zycia: np. "Puppy" w nazwie ale instrukcje karmienia dla doroslych
- Deskryptory marketingowe: "Premium", "Gourmet", "Luxury", "Super Premium" — \
czy uzasadnione skladem/jakoscia skladnikow? (FEDIAF CoGLP zaleca uzasadnienie)
- Spojnosc wielojezykowa: czy nazwy w roznych jezykach na etykiecie sa spojne \
(np. polska nazwa nie sugeruje czegos innego niz angielska)
Dla kazdego sprawdzenia podaj: check_type \
("name_vs_food_type"/"name_vs_species"/"name_vs_lifestage"/\
"misleading_descriptor"/"multilang_consistency"), \
description, finding, compliant (bool), issue_description, recommendation, \
severity ("critical"/"warning"/"info").
naming_section_score: 0-100.

SEKCJA 3 — MARKA (brand name compliance):
Przeanalizuj nazwe marki i elementy brandingowe pod katem:
- "Bio"/"Organic"/"Ekologiczny"/"Oko" — wymaga certyfikacji EU 2018/848. \
Czy na etykiecie jest logo EU organic leaf lub numer certyfikatu? \
Jesli nie = critical (EU 2018/848 Art.30).
- "Vet"/"Veterinary"/"Clinical"/"Kliniczny" — sugeruje dietetyczny srodek \
specjalnego przeznaczenia zywieniowego (EU 2020/354). \
Czy produkt ma taka klasyfikacje na etykiecie? Jesli nie = critical.
- "Natural"/"Naturalny" — wg FEDIAF Code of Practice: brak chemicznie \
syntetyzowanych skladnikow (dozwolone wyjatki: witaminy, skladniki mineralne, \
aminokwasy). Sprawdz liste dodatkow. Jesli sa sztuczne = warning.
- "Medical"/"Medicinal"/"Leczniczy"/"Terapeutyczny" — ZABRONIONE \
per EU 767/2009 Art.13. Zawsze severity=critical.
- Implikacje geograficzne w marce: np. "Scottish Farms", "Alpine Fresh", \
"Nordic" — czy produkt faktycznie pochodzi z tego regionu? \
Sprawdz kraj producenta na etykiecie. Jesli niezgodne = warning.
- "Holistic" — termin nieuregulowany prawnie w paszach, \
potencjalnie wprowadzajacy w blad. severity=info.
- "Human-grade" / "Human grade" — nieuregulowane w legislacji paszowej EU, \
potencjalnie misleading. severity=info.
- Nazwy ras w marce/nazwie: np. "Labrador Diet", "Persian Formula" — \
czy formulacja jest rzeczywiscie dostosowana do potrzeb rasy? \
Jesli brak uzasadnienia = warning.
Dla kazdego elementu podaj: brand_name, flagged_element, check_type \
("bio_organic"/"vet_veterinary"/"natural"/"medical_forbidden"/\
"country_origin"/"holistic"/"human_grade"/"breed_specific"/"other"), \
regulation_reference, compliant (bool), issue_description, recommendation, \
severity ("critical"/"warning"/"info").
brand_section_score: 0-100.

SEKCJA 4 — ZASTRZEZENIA / ZNAKI TOWAROWE (trademark / IP):
Przeanalizuj etykiete pod katem potencjalnych naruszen wlasnosci intelektualnej:
- Czy NAZWA PRODUKTU moze naruszac znane znaki towarowe w branzy pet food? \
Porownaj z markami: Royal Canin, Hill's, Purina, Pedigree, Whiskas, Sheba, \
Felix, Friskies, Eukanuba, Iams, Acana, Orijen, Taste of the Wild, \
Farmina, Brit, Josera, Happy Dog, Happy Cat, Carnilove, Wolfsblut, \
Applaws, Canidae, Merrick, Blue Buffalo, Wellness, Nutro.
- Czy NAZWA RECEPTURY lub FORMULY nie jest zastrzezona? \
Np. "ProPlan", "Science Diet", "Breed Health Nutrition" to zastrzezone nazwy.
- Czy uzyte symbole (R) ® i TM ™ sa prawidlowo stosowane? \
(R) = zarejestrowany znak towarowy (wymaga rejestracji w EUIPO/UPRP). \
TM = niezarejestrowane roszczenie do znaku towarowego. \
Sprawdz czy symbole sa uzyte przy wlasnych markach (poprawne) \
czy przy cudzych (potencjalnie misleading).
- Czy nazwy skladnikow nie sa zastrzezonymi markami handlowymi? \
Np. "FOS" (Orafti), "Yucca Schidigera Extract" (Desert King), \
"LID" (Natural Balance), "LifeSource Bits" (Blue Buffalo).
- Flaguj nazwy ZBIEZNE fonetycznie lub wizualnie z znanymi markami \
(np. "Royal Feast" vs "Royal Canin", "Hill Top" vs "Hill's").
Dla kazdego elementu podaj: element_text, element_type \
("product_name"/"recipe_name"/"ingredient_brand"/"symbol_usage"/"other"), \
potential_owner, trademark_symbol_found ("registered"/"tm"/"none"), \
risk_level ("high"/"medium"/"low"/"none"), \
issue_description, recommendation, severity ("critical"/"warning"/"info").
trademark_section_score: 0-100.

SCORING:
- recipe_section_score, naming_section_score, brand_section_score, \
trademark_section_score: kazda sekcja 0-100
- score = srednia wazona: receptury 25% + nazwy 30% + marka 25% + \
zastrzezenia 20%, zaokraglona do int
- overall_compliance: "compliant" jesli score>=90 I brak severity=critical, \
"issues_found" jesli score>=60, "critical_issues" jesli score<60 \
LUB jakikolwiek check ma severity=critical

Odpowiedz WYLACZNIE poprawnym JSON (bez markdown). Badz ZWIEZLY. Pola:
product_name, brand_name, product_classification, food_type, species, lifestage,
ingredients_with_percentages (lista), additives_list (lista),
recipe_claims_found (lista), recipe_claim_checks (lista RecipeClaimCheck),
recipe_section_score,
naming_convention_checks (lista NamingConventionCheck),
name_consistency_checks (lista NameConsistencyCheck),
naming_section_score,
brand_compliance_checks (lista BrandComplianceCheck),
brand_section_score,
trademark_checks (lista TrademarkCheck),
trademark_section_score,
overall_compliance, score, summary (po polsku)."""


# -- Label text generation prompt ------------------------------------------------


def build_label_text_prompt(
    species: str,
    lifestage: str,
    food_type: str,
    ingredients: str,
    nutrients: dict,
    target_language: str,
    target_language_name: str,
    product_name: str = "",
) -> str:
    """Build prompt for generating complete label text in the target language.

    Args:
        species: Target species (e.g. "dog", "cat").
        lifestage: Lifestage (e.g. "adult", "puppy").
        food_type: Food type (e.g. "dry", "wet").
        ingredients: Ingredients list as provided by the user.
        nutrients: Dict of analytical constituents (e.g. {"crude_protein": 26}).
        target_language: ISO 639-1 code (e.g. "en", "de", "pl").
        target_language_name: Full language name (e.g. "English", "Deutsch").
        product_name: Optional product name.

    Returns:
        Complete prompt string for label text generation.
    """
    # Format nutrients into readable text
    nutrient_lines = []
    nutrient_labels = {
        "crude_protein": "Crude protein / Bialko surowe",
        "crude_fat": "Crude fat / Tluszcz surowy",
        "crude_fibre": "Crude fibre / Wlokno surowe",
        "moisture": "Moisture / Wilgotnosc",
        "crude_ash": "Crude ash / Popiol surowy",
        "calcium": "Calcium / Wapn",
        "phosphorus": "Phosphorus / Fosfor",
    }
    for key, label in nutrient_labels.items():
        val = nutrients.get(key)
        if val is not None:
            nutrient_lines.append(f"  {label}: {val}%")
    nutrients_text = "\n".join(nutrient_lines) if nutrient_lines else "  (brak danych)"

    product_block = ""
    if product_name:
        product_block = f"\nNAZWA PRODUKTU: {product_name}\n"

    return f"""\
Wygeneruj KOMPLETNY tekst etykiety karmy dla zwierzat domowych \
w jezyku: {target_language_name} ({target_language}).

Uzyj oficjalnej terminologii regulacyjnej EU 767/2009 w jezyku docelowym.
{product_block}
DANE WEJSCIOWE:
Gatunek: {species}
Etap zycia: {lifestage}
Typ karmy: {food_type}

SKLADNIKI (lista w kolejnosci malejacej udzialu):
{ingredients}

SKLADNIKI ANALITYCZNE:
{nutrients_text}

WYMAGANE SEKCJE (wygeneruj KAZDA):

1. COMPOSITION / SKLAD:
   - Lista skladnikow w formacie regulacyjnym EU 767/2009
   - Skladniki w kolejnosci malejacej udzialu wagowego
   - Uzyj poprawnej terminologii w jezyku docelowym
   - Zachowaj procenty jesli podane w danych wejsciowych

2. ANALYTICAL CONSTITUENTS / SKLADNIKI ANALITYCZNE:
   - Tabela wartosci analitycznych w formacie regulacyjnym
   - Uzyj nazw regulacyjnych: "Crude protein" (EN), "Rohprotein" (DE), \
"Proteine brute" (FR), "Bialko surowe" (PL)

3. FEEDING GUIDELINES / DAWKOWANIE:
   - Tabela dawkowania na podstawie masy ciala zwierzecia
   - Dla psow: zakresy wagowe 2-5 kg, 5-10 kg, 10-20 kg, 20-30 kg, 30-40 kg, 40+ kg
   - Dla kotow: zakresy wagowe 2-4 kg, 4-6 kg, 6-8 kg, 8+ kg
   - Oblicz dawki na podstawie typu karmy i wartosci odzywczych
   - Dodaj uwage: "Dawki orientacyjne, dostosuj do aktywnosci i kondycji zwierzecia"

4. STORAGE INSTRUCTIONS / PRZECHOWYWANIE:
   - Standardowe instrukcje przechowywania dla danego typu karmy
   - Sucha: "Przechowywac w suchym, chlodnym miejscu"
   - Mokra: "Po otwarciu przechowywac w lodowce i zuzyc w ciagu 48h"

5. MANUFACTURER / PRODUCENT:
   - Wstaw placeholder: "[NAZWA PRODUCENTA]"
   - "[ADRES PRODUCENTA]"
   - "[NUMER REJESTRACYJNY ZAKLADU]"

6. WARNINGS / OSTRZEZENIA:
   - Dodaj ostrzezenia odpowiednie dla typu produktu:
   - Zawsze: "Zapewnic staly dostep do swiezej wody pitnej"
   - Mokra karma: "Po otwarciu przechowywac w lodowce"
   - Surowa karma (raw/BARF): ostrzezenia o higieny, mrozonej masy, \
mycia rak po kontakcie
   - Karma z owadami: informacja o mozliwosci reakcji alergicznej \
u zwierzat uczulonych na skorupiaki

Dla kazdej sekcji podaj:
- section_name: klucz wewnetrzny (np. "composition", "analytical_constituents")
- section_title: tytul sekcji w jezyku docelowym
- content: pelna tresc sekcji
- regulatory_reference: odniesienie do regulacji EU (np. "EU 767/2009 Art.17")
- notes: dodatkowe uwagi

DODATKOWO:
- feeding_table: lista wierszy tabeli dawkowania \
[{{weight_range, daily_amount}}]
- warnings: lista ostrzezen jako stringi
- complete_text: CALY tekst etykiety jako jeden string \
(wszystkie sekcje polaczone w czytelny format)
- summary: krotkie podsumowanie wygenerowanego tekstu

Odpowiedz WYLACZNIE poprawnym JSON (bez markdown). Pola:
product_name, species, lifestage, food_type, \
language ("{target_language}"), language_name ("{target_language_name}"),
sections (lista: [{{section_name, section_title, content, \
regulatory_reference, notes}}]),
feeding_table (lista: [{{weight_range, daily_amount}}]),
warnings (lista stringow),
complete_text (caly tekst etykiety jako jeden string),
summary (krotkie podsumowanie)."""


# -- Product description generation prompt -------------------------------------


_TONE_INSTRUCTIONS = {
    "premium": (
        "Styl PREMIUM / LUKSUSOWY: Uzywaj aspiracyjnego jezyka, podkreslaj "
        "ekskluzywnosc, rzemieślnicza jakosc, starannosc w doborze skladnikow. "
        "Slowa kluczowe: 'wyselekcjonowane', 'najwyzszej jakosci', 'wyjatkowa receptura'. "
        "Ton elegancki, pewny siebie, budujacy poczucie luksusu."
    ),
    "scientific": (
        "Styl NAUKOWY / WETERYNARYJNY: Uzywaj precyzyjnej terminologii naukowej, "
        "cytuj funkcje odzywcze, odwoluj sie do badan i standardow FEDIAF. "
        "Ton autorytatywny, merytoryczny, budujacy zaufanie profesjonalistow. "
        "Podkreslaj aspekty kliniczne i naukowo potwierdzone korzysci."
    ),
    "natural": (
        "Styl NATURALNY / WHOLESOME: Podkreslaj naturalne pochodzenie skladnikow, "
        "narracje 'od pola do miski', minimalne przetworzenie, bliskosc natury. "
        "Slowa kluczowe: 'naturalny', 'prawdziwy', 'starannie dobrany', "
        "'z naturalnych zrodel'. Ton ciepły, autentyczny, bliski naturze."
    ),
    "standard": (
        "Styl STANDARDOWY / NEUTRALNY: Jasny, informacyjny, zrownowazony ton "
        "odpowiedni do ogolnej sprzedazy detalicznej. Rzeczowy i przystepny, "
        "bez nadmiernej egzaltacji. Skupiony na faktach i korzyściach."
    ),
}


def build_product_description_prompt(
    species: str,
    lifestage: str,
    food_type: str,
    ingredients: str,
    nutrients: dict,
    target_language: str,
    target_language_name: str,
    tone: str,
    product_name: str = "",
    usps: str = "",
    brand: str = "",
) -> str:
    """Build prompt for generating a commercial product description.

    Args:
        species: Target species (e.g. "dog", "cat").
        lifestage: Lifestage (e.g. "adult", "puppy").
        food_type: Food type (e.g. "dry", "wet").
        ingredients: Ingredients list as text.
        nutrients: Dict of analytical constituents.
        target_language: ISO 639-1 code (e.g. "en", "de", "pl").
        target_language_name: Full language name.
        tone: Description tone: "premium", "scientific", "natural", "standard".
        product_name: Optional product name.
        usps: Optional unique selling points (free text).
        brand: Optional brand name.

    Returns:
        Complete prompt string for product description generation.
    """
    nutrient_lines = []
    nutrient_labels = {
        "crude_protein": "Crude protein / Bialko surowe",
        "crude_fat": "Crude fat / Tluszcz surowy",
        "crude_fibre": "Crude fibre / Wlokno surowe",
        "moisture": "Moisture / Wilgotnosc",
        "crude_ash": "Crude ash / Popiol surowy",
        "calcium": "Calcium / Wapn",
        "phosphorus": "Phosphorus / Fosfor",
    }
    for key, label in nutrient_labels.items():
        val = nutrients.get(key)
        if val is not None:
            nutrient_lines.append(f"  {label}: {val}%")
    nutrients_text = "\n".join(nutrient_lines) if nutrient_lines else "  (brak danych)"

    product_block = ""
    if product_name:
        product_block = f"\nNAZWA PRODUKTU: {product_name}\n"
    if brand:
        product_block += f"MARKA: {brand}\n"

    usps_block = ""
    if usps.strip():
        usps_block = (
            f"\nUNIKALNE CECHY PRODUKTU (USP):\n{usps.strip()}\n"
        )

    tone_instruction = _TONE_INSTRUCTIONS.get(tone, _TONE_INSTRUCTIONS["standard"])

    return f"""\
Jestes doswiadczonym copywriterem specjalizujacym sie w branzy pet food \
z gleboka znajomoscia regulacji FEDIAF i EU 767/2009. \
Wygeneruj KOMPLETNY OPIS KOMERCYJNY produktu karmy dla zwierzat \
w jezyku: {target_language_name} ({target_language}).

STYL OPISU:
{tone_instruction}
{product_block}
DANE WEJSCIOWE:
Gatunek: {species}
Etap zycia: {lifestage}
Typ karmy: {food_type}

SKLADNIKI (lista w kolejnosci malejacej udzialu):
{ingredients}

SKLADNIKI ANALITYCZNE:
{nutrients_text}
{usps_block}
WYGENERUJ NASTEPUJACE SEKCJE:

1. HEADLINE (section_name: "headline")
   Jedno zdanie — chwytliwy, przekonujacy opis pozycjonujacy produkt.
   Maks 15 slow. Podkresla glowna przewage produktu.

2. KEY BENEFITS (section_name: "key_benefits")
   3-5 zdań mapujacych KONKRETNE skladniki na KONKRETNE korzysci:
   - Bialko → utrzymanie szczuplej masy miesniowej
   - Kwasy omega → zdrowa skora i lsniaca siersc
   - Blonnik/prebiotyki → zdrowe trawienie i wchłanianie
   - Antyoksydanty → wsparcie ukladu odpornosciowego
   - Glukozamina/EPA → zdrowe stawy i mobilnosc
   - Wapn + fosfor → mocne kosci i zeby
   - L-karnityna → zdrowa masa ciala
   Uzywaj jezyka korzysci ("wspiera zdrowe trawienie") nie cech ("zawiera blonnik").

3. INGREDIENT STORY (section_name: "ingredient_story")
   2-4 zdania narracji o skladnikach: skad pochodza, co je wyróznia, \
   dlaczego zostaly wybrane. Podkresla glowne zrodlo bialka. \
   Jesli podano USP — wpleć je naturalnie.

4. TARGET ANIMAL PROFILE (section_name: "target_animal_profile")
   Dla kogo jest ta karma: gatunek, etap zycia, rozmiar, \
   potrzeby zdrowotne, poziom aktywnosci. 2-3 zdania.

5. NUTRITIONAL HIGHLIGHTS (section_name: "nutritional_highlights")
   Kluczowe skladniki odzywcze z wyjasnieniem funkcji. \
   Podaj konkretne wartosci % tam gdzie dostepne.

6. FEEDING SUMMARY (section_name: "feeding_summary")
   Uproszczone wskazowki dawkowania dla e-commerce (2-3 zdania). \
   Nie tabela — tylko ogolne zalecenia z adnotacja \
   "szczegolowe dawkowanie na opakowaniu".

7. CLAIMS & CERTIFICATIONS (section_name: "claims_certifications")
   Lista claimow marketingowych ktore MOZNA uzyc na podstawie skladu. \
   Kazdy claim musi byc UZASADNIONY danymi wejsciowymi.

8. SEO METADATA (obiekt "seo"):
   - meta_title: maks 60 znakow, z glownym slowem kluczowym
   - meta_description: maks 160 znakow, z CTA
   - keywords: 5-10 slow kluczowych (long-tail, z intencja zakupowa)
   - focus_keyword: glowne slowo kluczowe

GUARDRAILS REGULACYJNE (OBOWIAZKOWE):

A) REGULY NAZEWNICTWA FEDIAF (procent skladnika w nazwie/claimie):
   - "z X" / "with X" = minimum 4% skladnika X
   - "bogaty w X" / "rich in X" = minimum 14% skladnika X
   - X jako glowna nazwa = minimum 26% skladnika X
   Jesli dane procentowe sa dostepne — SPRAWDZ czy claim jest uzasadniony. \
   Jesli brak danych % — dodaj ostrzezenie w claims_warnings.

B) ZAKAZANE CLAIMY TERAPEUTYCZNE (EU 767/2009 Art.13):
   NIGDY nie uzywaj slow: "leczy", "zapobiega", "likwiduje", "eliminuje choroby", \
   "terapeutyczny", "leczniczy", "medyczny", "zastepuje leczenie weterynaryjne".
   Dopuszczalne claimy funkcjonalne: "wspiera trawienie", "zdrowa siersc".

C) CLAIM "NATURAL" — tylko jesli WSZYSTKIE skladniki sa naturalnego pochodzenia \
   (roslinne/zwierzece/mineralne) bez syntetycznych dodatkow. \
   Jesli na liscie sa syntetyczne witaminy — claim "natural" wymaga \
   zastrzezenia "z dodanymi witaminami i mineralami".

D) CLAIM "GRAIN-FREE" — tylko jesli ZADEN skladnik nie jest zbozen: \
   pszenica, jeczmien, owies, zyto, kukurydza, ryz, proso, sorgo, orkisz.

E) CLAIM "HYPOALLERGENIC" — wymaga rygorystycznego dowodu, nie uzywaj \
   bez wyraznej podstawy w skladzie (np. limitowane zrodla bialka).

Jesli JAKIKOLWIEK claim jest watpliwy — dodaj wpis do claims_warnings z polami:
claim_text, warning_type ("forbidden_therapeutic"/"unsubstantiated"/\
"naming_rule_violation"/"needs_evidence"), explanation, recommendation.

DODATKOWE POLA DO WYGENEROWANIA:

- headline: 1 zdanie hook (ten sam tekst co sekcja "headline")
- short_description: 2-3 zdania na karty produktowe / listingi
- bullet_points: 5-7 kluczowych punktow sprzedazowych (krotkie, z myślnikami)
- claims_used: lista claimow uzytyych w opisie (stringi)
- claims_warnings: lista ostrzezen (jesli sa)
- complete_html: caly opis jako HTML (uzyj <h2>, <p>, <ul><li>, <strong>)
- complete_text: caly opis jako plain text
- summary: 1 zdanie podsumowania

Dla KAZDEJ sekcji podaj:
- section_name: klucz wewnetrzny
- section_title: tytul w jezyku docelowym
- content: tresc plain text
- html_content: tresc w HTML

Odpowiedz WYLACZNIE poprawnym JSON (bez markdown). Pola:
product_name, species, lifestage, food_type, \
language ("{target_language}"), language_name ("{target_language_name}"), \
tone ("{tone}"), \
headline, short_description, bullet_points (lista stringow), \
sections (lista: [{{section_name, section_title, content, html_content}}]), \
seo ({{meta_title, meta_description, keywords (lista), focus_keyword}}), \
claims_used (lista stringow), \
claims_warnings (lista: [{{claim_text, warning_type, explanation, recommendation}}]), \
complete_html, complete_text, summary."""


def build_product_description_from_image_prompt(
    target_language: str,
    target_language_name: str,
    tone: str,
) -> str:
    """Build prompt for generating product description from a label image.

    Two-phase prompt: extract product data from image, then generate
    commercial description.

    Args:
        target_language: ISO 639-1 code.
        target_language_name: Full language name.
        tone: Description tone.

    Returns:
        Complete prompt string.
    """
    tone_instruction = _TONE_INSTRUCTIONS.get(tone, _TONE_INSTRUCTIONS["standard"])

    return f"""\
Jestes doswiadczonym copywriterem specjalizujacym sie w branzy pet food \
z gleboka znajomoscia regulacji FEDIAF i EU 767/2009.

FAZA 1 — EKSTRAKCJA DANYCH Z ETYKIETY:
Na podstawie obrazu etykiety wyekstrahuj:
- Nazwa produktu, marka
- Gatunek docelowy (pies/kot/inny)
- Etap zycia (szczenie/dorosly/senior)
- Typ karmy (sucha/mokra/przysmak)
- Lista skladnikow (z procentami jesli podane)
- Skladniki analityczne (bialko, tluszcz, wlokno, wilgotnosc, popiol, wapn, fosfor)
- Claimy widoczne na etykiecie
- Unikalne cechy produktu (USP)

FAZA 2 — GENERACJA OPISU KOMERCYJNEGO:
Na podstawie wyekstrahowanych danych wygeneruj KOMPLETNY OPIS KOMERCYJNY \
w jezyku: {target_language_name} ({target_language}).

STYL OPISU:
{tone_instruction}

WYMAGANE SEKCJE (8 sekcji):

1. HEADLINE (section_name: "headline") — 1 zdanie, chwytliwy hook, maks 15 slow.

2. KEY BENEFITS (section_name: "key_benefits") — 3-5 zdan mapujacych \
skladniki na korzysci (bialko→miesnie, omega→skora, blonnik→trawienie).

3. INGREDIENT STORY (section_name: "ingredient_story") — 2-4 zdania \
narracji o skladnikach i ich pochodzeniu.

4. TARGET ANIMAL PROFILE (section_name: "target_animal_profile") — 2-3 zdania \
dla kogo jest ta karma.

5. NUTRITIONAL HIGHLIGHTS (section_name: "nutritional_highlights") — kluczowe \
skladniki odzywcze z wyjasnieniem funkcji i wartosciami %.

6. FEEDING SUMMARY (section_name: "feeding_summary") — 2-3 zdania uproszczonych \
wskazowek dawkowania.

7. CLAIMS & CERTIFICATIONS (section_name: "claims_certifications") — lista \
uzasadnionych claimow.

8. SEO METADATA (obiekt "seo"): meta_title (60 zn.), meta_description (160 zn.), \
keywords (5-10), focus_keyword.

GUARDRAILS REGULACYJNE:
- Reguly nazewnictwa FEDIAF: "z X"=4%, "bogaty w X"=14%, X w nazwie=26%
- ZAKAZANE claimy terapeutyczne (EU 767/2009 Art.13)
- "Natural" tylko jesli wszystkie skladniki naturalne
- "Grain-free" tylko jesli brak zboz w skladzie
- "Hypoallergenic" wymaga rygorystycznego dowodu
- Watpliwe claimy → claims_warnings

Odpowiedz WYLACZNIE poprawnym JSON (bez markdown). Pola:
product_name, species, lifestage, food_type, \
language ("{target_language}"), language_name ("{target_language_name}"), \
tone ("{tone}"), \
headline, short_description (2-3 zdania), \
bullet_points (5-7 punktow), \
sections (lista: [{{section_name, section_title, content, html_content}}]), \
seo ({{meta_title, meta_description, keywords, focus_keyword}}), \
claims_used (lista), claims_warnings (lista: \
[{{claim_text, warning_type, explanation, recommendation}}]), \
complete_html, complete_text, summary."""


PRODUCT_DESCRIPTION_VERIFY_PROMPT = """\
Jestes recenzentem jakosci AI specjalizujacym sie w branzy pet food. \
Otrzymujesz WYGENEROWANY OPIS PRODUKTU w formacie JSON.

DANE WEJSCIOWE PRODUCENTA (ZRODLO PRAWDY):
{input_data}

Twoje zadanie: ZWERYFIKUJ opis porownujac go z DANYMI WEJSCIOWYMI. Szukaj:

A) HALUCYNACJE SKLADNIKOWE — opis wspomina skladniki, ktore NIE sa \
w danych wejsciowych (lista skladnikow). Usun lub popraw.

B) HALUCYNACJE LICZBOWE — opis podaje wartosci procentowe lub liczbowe, \
ktore NIE wynikaja z danych wejsciowych. Usun lub popraw.

C) NIEUZASADNIONE CLAIMY — opis zawiera twierdzenia, ktore nie wynikaja \
ze skladu (np. "bogaty w kurczaka" jesli kurczak nie jest na liscie \
lub jest < 14%). Dodaj ostrzezenie w claims_warnings.

D) ZAKAZANE CLAIMY TERAPEUTYCZNE — frazy sugerujace dzialanie lecznicze: \
"leczy", "zapobiega chorobom", "terapeutyczny", "medyczny". \
Zamien na dopuszczalne claimy funkcjonalne.

E) PRZESADZONY JEZYK — twierdzenia bez pokrycia w danych: \
"najlepszy na rynku", "jedyny taki", "gwarantuje zdrowie". Zlagodz.

F) NIESPOJNOSC — opis mowi o innym gatunku/etapie zycia/typie karmy \
niz dane wejsciowe. Popraw.

Dla KAZDEGO elementu:
- POROWNAJ z danymi wejsciowymi
- Jesli element jest POPRAWNY i UZASADNIONY — zachowaj
- Jesli element jest HALUCYNACJA — USUN lub POPRAW
- Jesli claim jest watpliwy — dodaj do claims_warnings

WAZNE: Badz SUROWY. Lepiej usunac watpliwy element niz zostawic halucynacje. \
Priorytet: DOKLADNOSC > kreatywnosc.

Zwroc POPRAWIONY wynik w IDENTYCZNYM formacie JSON jak wejscie \
(te same pola, ta sama struktura).

WYNIK DO WERYFIKACJI (JSON ponizej):"""


# -- Label version comparison (diff) prompt ------------------------------------

LABEL_DIFF_PROMPT = """\
Porownaj DWA obrazy etykiety tego samego produktu.
PIERWSZY obraz = STARA WERSJA. DRUGI obraz = NOWA WERSJA.

ZADANIE 1 — ZMIANY TRESCI:
Zidentyfikuj WSZYSTKIE roznice w tekscie miedzy wersjami:
- Zmiany w skladzie (dodane/usuniete skladniki, zmienione %)
- Zmiany w skladnikach analitycznych (wartosci)
- Zmiany w dawkowaniu
- Zmiany w danych producenta
- Zmiany w claimach
- Zmiany w ostrzezeniach
- Zmiany jezykowe (poprawki, nowe tlumaczenia)
Dla kazdej zmiany podaj: sekcja, typ (added/removed/modified/moved), \
stary tekst, nowy tekst, waga (critical/warning/info), wplyw regulacyjny.

ZADANIE 2 — ZMIANY UKLADU:
Zidentyfikuj zmiany w layoucie/designie:
- Zmieniona pozycja elementow
- Zmienione kolory, fonty, rozmiary
- Dodane/usuniete elementy graficzne
- Zmienione proporcje sekcji

ZADANIE 3 — NOWE PROBLEMY:
Czy zmiany WPROWADZILY nowe problemy regulacyjne? \
(np. usuniety wymagany element, bledna wartosc)

ZADANIE 4 — NAPRAWIONE PROBLEMY:
Czy zmiany NAPRAWILY problemy ktore istnialy w starej wersji?

ZADANIE 5 — OCENA RYZYKA:
Okresil poziom ryzyka zmian: low (kosmetyczne), medium (istotne ale bezpieczne), \
high (wymagaja weryfikacji regulacyjnej przed drukiem).

Odpowiedz WYLACZNIE poprawnym JSON (bez markdown). Pola:
old_label_summary (krotki opis starej wersji),
new_label_summary (krotki opis nowej wersji),
text_changes (lista: [{{section, change_type ("added"/"removed"/"modified"/"moved"), \
old_text, new_text, severity ("critical"/"warning"/"info"), regulatory_impact}}]),
layout_changes (lista: [{{description, area, severity}}]),
new_issues_introduced (lista: [{{description, severity, introduced_by_change}}]),
issues_resolved (lista stringow),
overall_assessment (1-2 zdania),
change_count (int),
risk_level ("low"/"medium"/"high"),
summary (krotkie podsumowanie po polsku)."""
