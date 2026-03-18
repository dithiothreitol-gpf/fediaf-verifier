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

Odpowiedz WYLACZNIE poprawnym JSON (bez markdown). Pola:
cross_crude_protein/fat/fibre/moisture/crude_ash/calcium/phosphorus (liczby lub null),
cross_reading_notes,
detected_language (np. "pl"), detected_language_name (np. "polski"),
linguistic_issues (lista: [{issue_type, original, suggestion, context, explanation}]),
overall_language_quality ("excellent"/"good"/"needs_review"/"poor"),
language_summary."""

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
