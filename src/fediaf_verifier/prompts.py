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

Odpowiedz WYLACZNIE poprawnym JSON (bez markdown). Pola:
detected_language (np. "pl"), detected_language_name (np. "polski"),
issues (lista: [{issue_type, original, suggestion, context, explanation}]),
issue_type: "spelling"/"grammar"/"punctuation"/"diacritics"/"terminology",
overall_quality ("excellent"/"good"/"needs_review"/"poor"),
summary (krotkie podsumowanie jakosci tekstu)."""

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
