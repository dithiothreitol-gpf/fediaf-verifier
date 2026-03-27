"""AI prompt builders for catalog batch translation."""

from __future__ import annotations

import json

from .models.units import TranslationUnit


def build_catalog_translation_prompt(
    units: list[TranslationUnit],
    target_lang: str,
    target_lang_name: str,
    glossary_section: str,
    domain: str = "pet_food",
) -> str:
    """Build the full prompt for translating a batch of units.

    Returns a single string combining system instructions and user request.
    The AI is expected to return a JSON array of translated units.
    """
    # Prepare items as JSON for the user prompt
    items = []
    for u in units:
        items.append({
            "id": u.unit_id,
            "text": u.source_text,
            "category": u.category.value,
            "detected_language": u.detected_language,
            "do_not_translate": u.do_not_translate,
        })

    items_json = json.dumps(items, ensure_ascii=False, indent=2)

    page_number = units[0].page_number if units else "?"
    section_name = units[0].section_name if units else ""

    system_part = _build_system_prompt(target_lang, target_lang_name, glossary_section, domain)
    user_part = _build_user_prompt(page_number, section_name, items_json)

    return f"{system_part}\n\n---\n\n{user_part}"


def _build_system_prompt(
    target_lang: str,
    target_lang_name: str,
    glossary_section: str,
    domain: str,
) -> str:
    domain_rules = ""
    if domain == "pet_food":
        domain_rules = """
TERMINOLOGIA KARMY DLA ZWIERZAT ({target_lang_name}):
- "Zusammensetzung" (nie "Zutaten" - to dla zywnosci ludzkiej) [DE]
- "Inhaltsstoffe" jako odpowiednik "Ingredients" [DE]
- "Mineralstoffe" (nie "Mineralien") [DE]
- "pflanzliche Erzeugnisse" (nie "Pflanzenprodukte") [DE]
- "Innereien" dla "podroby/offal" [DE]
- "Nebenerzeugnisse" dla "produkty uboczne" [DE]
- "Alleinfuttermittel" = karma pelnoporcjowa [DE]
- "Ergaenzungsfuttermittel" = karma uzupelniajaca [DE]
- Kontekst regulacyjny: EU Reg. 767/2009 (labelling of feed)
""".replace("{target_lang_name}", target_lang_name)

    return f"""Jestes profesjonalnym tlumaczem specjalizujacym sie w branzy karmy dla zwierzat.
Tlumaczysz katalog produktowy z PL/EN na {target_lang_name} ({target_lang}).

KRYTYCZNE ZASADY:

1. TERMINOLOGIA DZIEDZINOWA: Uzywaj oficjalnej terminologii branzowej w jezyku docelowym.
{domain_rules}

2. ZNAKI DIAKRYTYCZNE: Zachowaj poprawne znaki diakrytyczne jezyka docelowego.
   W kolumnie oryginalu zachowaj polskie znaki: a, e, l, n, o, s, z, z.

3. GRAMATYKA:
   - Zachowaj liczbe (singularis/pluralis) zgodnie z oryginalem
   - Poprawna deklinacja i odmiana w zdaniach
   - Wielkie litery wg regul jezyka docelowego

4. FORMAT:
   - Zachowaj formatowanie: procenty, jednostki, interpunkcje
   - Nie zmieniaj nazw wlasnych marki
   - Nie tlumacz URL-i, adresow email
   - Zachowaj strukture nawiasow i wyliczen ze skladu

5. SPOJNOSC: Uzywaj ZAWSZE tych samych tlumaczen dla powtarzajacych sie fraz.

6. UWAGI DLA GRAFIKA: Jesli zauwazysc:
   - Literowke w oryginale -> dodaj uwage w polu "note"
   - Tekst ktory sie nie zmienia (URL, gramatura) -> zaznacz "Bez zmian"
   - Element graficzny (badge, baner) -> opisz typ elementu

7. Elementy z "do_not_translate": true — przepisz oryginal bez zmian.

{glossary_section}

Odpowiedz WYLACZNIE w formacie JSON (bez markdown, bez komentarzy):
[
  {{
    "id": "<unit_id>",
    "translated_text": "<tlumaczenie>",
    "note": "<uwaga lub pusty string>"
  }},
  ...
]"""


def _build_user_prompt(
    page_number: int | str,
    section_name: str,
    items_json: str,
) -> str:
    section_line = f"\nSekcja: {section_name}" if section_name else ""

    return f"""Przetlumacz ponizsze elementy ze strony {page_number} katalogu.{section_line}

{items_json}

Pamietaj:
- Odpowiedz TYLKO JSON-em, bez markdown, bez komentarzy
- Zachowaj id z inputu
- Kazdy element musi miec "id", "translated_text" i "note"
"""
