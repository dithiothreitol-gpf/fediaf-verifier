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
