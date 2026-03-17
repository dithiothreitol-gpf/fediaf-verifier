# Plan implementacji: Weryfikator etykiet FEDIAF v2
> Dokument dla Claude Code — wykonaj kroki w podanej kolejności

---

## Kontekst projektu

Narzędzie do weryfikacji etykiet karmy dla zwierząt domowych pod kątem:
1. **Zgodności z FEDIAF Nutritional Guidelines 2021** (wymaganie główne)
2. **Trendów rynkowych w wybranym kraju EU** (nice to have, opcjonalne)

**Użytkownicy:** pracownicy biurowi (brak wiedzy technicznej)
**Interfejs:** aplikacja webowa Streamlit uruchamiana lokalnie
**Wolumen:** 100–200 etykiet miesięcznie
**Dane:** niewrażliwe
**Model:** Claude Sonnet 4.6 API
**Koszt operacyjny:** ~4–12 USD miesięcznie

### Filozofia rzetelności

System AI jest pierwszą linią weryfikacji, nie ostatnią. Eliminuje 80–90% ręcznej
pracy przy prostych przypadkach. Dla przypadków granicznych zawsze eskaluje do człowieka.

Rzetelność zapewniana przez pięć niezależnych warstw:
1. Structured outputs z confidence scoring
2. Weryfikacja krzyżowa wartości liczbowych
3. Deterministyczne reguły FEDIAF (niezależne od AI)
4. Human-in-the-loop dla przypadków granicznych
5. Zestaw testowy z ręcznie zweryfikowanymi wynikami

---

## Struktura projektu do utworzenia

```
fediaf-verifier/
├── app.py                      # Główna aplikacja Streamlit
├── verifier.py                 # Logika weryfikacji (wywołania API)
├── verifier_rules.py           # Deterministyczne reguły FEDIAF (warstwa 3)
├── verifier_cross_check.py     # Weryfikacja krzyżowa wartości (warstwa 2)
├── converter.py                # Konwersja formatów etykiet
├── schemas.py                  # JSON Schema dla structured outputs
├── prompts.py                  # Prompty systemowe
├── requirements.txt            # Zależności Python
├── .env.example                # Wzorzec pliku konfiguracyjnego
├── README.md                   # Instrukcja uruchomienia
├── tests/
│   ├── test_accuracy.py        # Testy dokładności na zbiorze referencyjnym
│   ├── test_rules.py           # Testy jednostkowe reguł deterministycznych
│   └── reference_cases/        # Folder na etykiety z ręcznie zweryfikowanymi wynikami
│       └── README.md           # Instrukcja jak dodawać przypadki testowe
└── data/
    └── fediaf_guidelines_2021.pdf   # PLACEHOLDER — użytkownik dostarcza plik
```

---

## Krok 1 — Plik zależności

Utwórz `requirements.txt`:

```
anthropic>=0.40.0
streamlit>=1.40.0
python-dotenv>=1.0.0
Pillow>=10.0.0
python-docx>=1.1.0
docx2pdf>=0.1.8
pdf2image>=1.17.0
pytest>=8.0.0
```

---

## Krok 2 — Plik konfiguracyjny

Utwórz `.env.example`:

```
# Skopiuj ten plik jako .env i uzupełnij klucz API
# Klucz dostępny na: console.anthropic.com → API Keys
ANTHROPIC_API_KEY=sk-ant-twoj-klucz-tutaj
```

---

## Krok 3 — JSON Schema raportu weryfikacyjnego

Utwórz `schemas.py`.
WAŻNE: schemat zawiera pola confidence scoring — kluczowe dla warstwy 1.

```python
VERIFICATION_SCHEMA = {
    "type": "object",
    "properties": {

        # ── Produkt ──────────────────────────────────────────────────────────
        "product": {
            "type": "object",
            "properties": {
                "name":       {"type": ["string", "null"]},
                "brand":      {"type": ["string", "null"]},
                "species":    {"type": "string", "enum": ["dog", "cat", "other", "unknown"]},
                "lifestage":  {"type": "string",
                               "enum": ["puppy", "kitten", "adult", "senior",
                                        "all_stages", "unknown"]},
                "food_type":  {"type": "string",
                               "enum": ["dry", "wet", "semi_moist", "treat",
                                        "supplement", "unknown"]},
                "net_weight": {"type": ["string", "null"]}
            },
            "required": ["species", "lifestage", "food_type"]
        },

        # ── Wartości odżywcze ─────────────────────────────────────────────
        "extracted_nutrients": {
            "type": "object",
            "description": "Wartości wyekstrahowane z etykiety w %",
            "properties": {
                "crude_protein":    {"type": ["number", "null"]},
                "crude_fat":        {"type": ["number", "null"]},
                "crude_fibre":      {"type": ["number", "null"]},
                "moisture":         {"type": ["number", "null"]},
                "crude_ash":        {"type": ["number", "null"]},
                "calcium":          {"type": ["number", "null"]},
                "phosphorus":       {"type": ["number", "null"]}
            }
        },

        # ── Składniki ─────────────────────────────────────────────────────
        "ingredients_list": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Lista składników w kolejności deklaracji z etykiety"
        },

        # ── Confidence scoring (WARSTWA 1) ────────────────────────────────
        "extraction_confidence": {
            "type": "string",
            "enum": ["HIGH", "MEDIUM", "LOW"],
            "description": (
                "HIGH: wszystkie wartości wyraźnie widoczne i czytelne. "
                "MEDIUM: większość wartości czytelna, pojedyncze wątpliwości. "
                "LOW: znaczna część wartości niewyraźna lub trudna do odczytania."
            )
        },
        "values_requiring_manual_check": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Lista konkretnych wartości odczytanych z niepewnością. "
                "Np. ['crude_protein: cyfra mogła być 21 lub 24', "
                "'calcium: wartość niewidoczna']. "
                "Pusta lista jeśli wszystko czytelne."
            )
        },

        # ── Wyniki weryfikacji ────────────────────────────────────────────
        "compliance_score": {
            "type": "integer",
            "minimum": 0,
            "maximum": 100,
            "description": (
                "90–100: pełna zgodność. "
                "70–89: drobne uwagi, produkt dopuszczalny. "
                "50–69: istotne braki wymagające korekty. "
                "0–49: krytyczne niezgodności."
            )
        },
        "status": {
            "type": "string",
            "enum": ["COMPLIANT", "NON_COMPLIANT", "REQUIRES_REVIEW"]
        },

        # ── Problemy ─────────────────────────────────────────────────────
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "severity":         {"type": "string",
                                        "enum": ["CRITICAL", "WARNING", "INFO"]},
                    "code":             {"type": "string",
                                        "description": "Np. PROTEIN_BELOW_MIN"},
                    "description":      {"type": "string"},
                    "fediaf_reference": {"type": ["string", "null"],
                                        "description": "Np. Table 11, section 3.2"},
                    "found_value":      {"type": ["number", "string", "null"]},
                    "required_value":   {"type": ["string", "null"]}
                },
                "required": ["severity", "code", "description"]
            }
        },

        # ── Wymagania etykietowania EU ────────────────────────────────────
        "eu_labelling_check": {
            "type": "object",
            "description": "Wymagania etykietowania UE (Rozp. 767/2009)",
            "properties": {
                "ingredients_listed":              {"type": "boolean"},
                "analytical_constituents_present": {"type": "boolean"},
                "manufacturer_info":               {"type": "boolean"},
                "net_weight_declared":             {"type": "boolean"},
                "species_clearly_stated":          {"type": "boolean"},
                "batch_or_date_present":           {"type": "boolean"}
            }
        },

        # ── Rekomendacje ──────────────────────────────────────────────────
        "recommendations": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Konkretne działania naprawcze dla wykrytych problemów"
        },

        # ── Trendy rynkowe (opcjonalne) ───────────────────────────────────
        "market_trends": {
            "type": ["object", "null"],
            "description": "Sekcja opcjonalna — tylko gdy wybrano kraj",
            "properties": {
                "country":     {"type": "string"},
                "summary":     {"type": "string"},
                "positioning": {"type": "string",
                                "enum": ["trendy", "standard", "outdated", "niche"]},
                "trend_notes": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["country", "summary", "positioning"]
        }
    },
    "required": [
        "product", "extracted_nutrients", "extraction_confidence",
        "values_requiring_manual_check", "compliance_score", "status",
        "issues", "eu_labelling_check", "recommendations"
    ]
}


# Schemat uproszczony — tylko wartości liczbowe (używany przez weryfikację krzyżową)
NUTRIENTS_ONLY_SCHEMA = {
    "type": "object",
    "properties": {
        "crude_protein":    {"type": ["number", "null"]},
        "crude_fat":        {"type": ["number", "null"]},
        "crude_fibre":      {"type": ["number", "null"]},
        "moisture":         {"type": ["number", "null"]},
        "crude_ash":        {"type": ["number", "null"]},
        "calcium":          {"type": ["number", "null"]},
        "phosphorus":       {"type": ["number", "null"]},
        "reading_notes":    {"type": "string",
                             "description": "Uwagi o jakości odczytu, np. 'cyfra 3 lub 8 niewyraźna'"}
    }
}
```

---

## Krok 4 — Deterministyczne reguły FEDIAF (warstwa 3)

Utwórz `verifier_rules.py`.
Ten plik nie używa AI. Zawiera progi zakodowane ręcznie na podstawie FEDIAF.
Nawet jeśli model AI się myli — ta warstwa wyłapie krytyczne przekroczenia.

```python
"""
Deterministyczne reguły FEDIAF — niezależne od modelu AI.
Źródło: FEDIAF Nutritional Guidelines 2021, tabele 9–14.

Wartości podane w % suchej masy (DM).
Konwersja z as-fed: wartość_DM = wartość_as_fed / (1 - wilgotność/100)
"""

# ── Minimalne poziomy składników odżywczych ───────────────────────────────────
# Klucz: (species, lifestage, food_type)
# food_type "any" stosuje się do wszystkich typów

FEDIAF_MINIMUMS_DM: dict[tuple, dict] = {
    # PSY
    ("dog", "puppy",      "dry"):  {"crude_protein": 22.5, "crude_fat": 8.0,  "calcium": 1.0, "phosphorus": 0.8},
    ("dog", "puppy",      "wet"):  {"crude_protein": 22.5, "crude_fat": 8.0,  "calcium": 1.0, "phosphorus": 0.8},
    ("dog", "adult",      "dry"):  {"crude_protein": 18.0, "crude_fat": 5.0,  "calcium": 0.5, "phosphorus": 0.4},
    ("dog", "adult",      "wet"):  {"crude_protein": 18.0, "crude_fat": 5.0,  "calcium": 0.5, "phosphorus": 0.4},
    ("dog", "senior",     "dry"):  {"crude_protein": 18.0, "crude_fat": 5.0,  "calcium": 0.5, "phosphorus": 0.4},
    ("dog", "senior",     "wet"):  {"crude_protein": 18.0, "crude_fat": 5.0,  "calcium": 0.5, "phosphorus": 0.4},
    ("dog", "all_stages", "dry"):  {"crude_protein": 22.5, "crude_fat": 8.0,  "calcium": 1.0, "phosphorus": 0.8},
    ("dog", "all_stages", "wet"):  {"crude_protein": 22.5, "crude_fat": 8.0,  "calcium": 1.0, "phosphorus": 0.8},
    # KOTY
    ("cat", "kitten",     "dry"):  {"crude_protein": 28.0, "crude_fat": 9.0,  "calcium": 0.8, "phosphorus": 0.6},
    ("cat", "kitten",     "wet"):  {"crude_protein": 28.0, "crude_fat": 9.0,  "calcium": 0.8, "phosphorus": 0.6},
    ("cat", "adult",      "dry"):  {"crude_protein": 25.0, "crude_fat": 9.0,  "calcium": 0.6, "phosphorus": 0.5},
    ("cat", "adult",      "wet"):  {"crude_protein": 25.0, "crude_fat": 9.0,  "calcium": 0.6, "phosphorus": 0.5},
    ("cat", "senior",     "dry"):  {"crude_protein": 25.0, "crude_fat": 9.0,  "calcium": 0.6, "phosphorus": 0.5},
    ("cat", "senior",     "wet"):  {"crude_protein": 25.0, "crude_fat": 9.0,  "calcium": 0.6, "phosphorus": 0.5},
    ("cat", "all_stages", "dry"):  {"crude_protein": 28.0, "crude_fat": 9.0,  "calcium": 0.8, "phosphorus": 0.6},
    ("cat", "all_stages", "wet"):  {"crude_protein": 28.0, "crude_fat": 9.0,  "calcium": 0.8, "phosphorus": 0.6},
}

# ── Maksymalne poziomy składników odżywczych ──────────────────────────────────
FEDIAF_MAXIMUMS_DM: dict[tuple, dict] = {
    ("dog", "puppy",  "any"): {"calcium": 3.3,  "phosphorus": 2.5},
    ("dog", "adult",  "any"): {"calcium": 4.5,  "phosphorus": 4.0},
    ("dog", "senior", "any"): {"calcium": 4.5,  "phosphorus": 4.0},
    ("cat", "kitten", "any"): {"calcium": 3.0,  "phosphorus": 2.5},
    ("cat", "adult",  "any"): {"calcium": 4.0,  "phosphorus": 3.5},
    ("cat", "senior", "any"): {"calcium": 4.0,  "phosphorus": 3.5},
}

# ── Referencje do wytycznych ─────────────────────────────────────────────────
FEDIAF_REFERENCES = {
    "crude_protein": "FEDIAF 2021, Table 9–10 (cats) / Table 11–12 (dogs)",
    "crude_fat":     "FEDIAF 2021, Table 9–10 (cats) / Table 11–12 (dogs)",
    "calcium":       "FEDIAF 2021, Table 13 (minerals)",
    "phosphorus":    "FEDIAF 2021, Table 13 (minerals)",
}


def convert_to_dm(value: float, moisture: float | None) -> float:
    """
    Przelicza wartość z as-fed na dry matter (DM).
    Jeśli wilgotność nieznana, zakłada 10% (typowa dla karmy suchej).
    """
    if moisture is None:
        moisture = 10.0
    if moisture >= 100:
        return value  # nie przeliczaj — błędna wartość
    return value / (1.0 - moisture / 100.0)


def hard_check(result: dict) -> list[dict]:
    """
    Deterministyczna weryfikacja progów FEDIAF.
    Niezależna od modelu AI — błąd AI nie wpływa na tę warstwę.

    Args:
        result: wynik weryfikacji AI (słownik zgodny z VERIFICATION_SCHEMA)

    Returns:
        Lista problemów wykrytych przez reguły deterministyczne.
        Każdy element zawiera: severity, code, description, source="HARD_RULE",
        found_value, required_value, fediaf_reference.
    """
    flags = []

    species   = result.get("product", {}).get("species", "unknown")
    lifestage = result.get("product", {}).get("lifestage", "unknown")
    food_type = result.get("product", {}).get("food_type", "unknown")
    nutrients = result.get("extracted_nutrients", {})
    moisture  = nutrients.get("moisture")

    if species == "unknown" or lifestage == "unknown":
        return []  # nie można sprawdzić bez klasyfikacji

    # Normalizuj food_type dla lookup minimów
    ft_lookup = food_type if food_type in ("dry", "wet") else "dry"

    # ── Sprawdź minima ────────────────────────────────────────────────────────
    minimums = FEDIAF_MINIMUMS_DM.get((species, lifestage, ft_lookup), {})

    for nutrient, min_dm in minimums.items():
        actual_raw = nutrients.get(nutrient)
        if actual_raw is None:
            continue

        actual_dm = convert_to_dm(actual_raw, moisture)

        if actual_dm < min_dm:
            flags.append({
                "source":          "HARD_RULE",
                "severity":        "CRITICAL",
                "code":            f"{nutrient.upper()}_BELOW_MIN",
                "description": (
                    f"{nutrient.replace('_', ' ').title()} ({actual_raw}% as-fed, "
                    f"{actual_dm:.1f}% DM) poniżej minimum FEDIAF "
                    f"({min_dm}% DM) dla {species} {lifestage}."
                ),
                "found_value":     round(actual_dm, 2),
                "required_value":  f"min. {min_dm}% DM",
                "fediaf_reference": FEDIAF_REFERENCES.get(nutrient, "FEDIAF 2021"),
            })

    # ── Sprawdź maxima ────────────────────────────────────────────────────────
    # Szukaj dla konkretnego lifestage lub "all_stages"
    maximums = (
        FEDIAF_MAXIMUMS_DM.get((species, lifestage, "any")) or
        FEDIAF_MAXIMUMS_DM.get((species, "all_stages", "any")) or
        {}
    )

    for nutrient, max_dm in maximums.items():
        actual_raw = nutrients.get(nutrient)
        if actual_raw is None:
            continue

        actual_dm = convert_to_dm(actual_raw, moisture)

        if actual_dm > max_dm:
            flags.append({
                "source":          "HARD_RULE",
                "severity":        "CRITICAL",
                "code":            f"{nutrient.upper()}_ABOVE_MAX",
                "description": (
                    f"{nutrient.replace('_', ' ').title()} ({actual_raw}% as-fed, "
                    f"{actual_dm:.1f}% DM) powyżej maksimum FEDIAF "
                    f"({max_dm}% DM) dla {species} {lifestage}."
                ),
                "found_value":     round(actual_dm, 2),
                "required_value":  f"max. {max_dm}% DM",
                "fediaf_reference": FEDIAF_REFERENCES.get(nutrient, "FEDIAF 2021"),
            })

    return flags


def merge_with_ai_results(ai_issues: list[dict], hard_flags: list[dict]) -> list[dict]:
    """
    Łączy problemy z AI z problemami z reguł deterministycznych.
    Usuwa duplikaty — jeśli hard_rule pokrywa się z AI issue, zostawia hard_rule
    (jest bardziej precyzyjny).
    """
    # Kody problemów już wykrytych przez AI
    ai_codes = {i.get("code", "") for i in ai_issues}

    # Dodaj tylko te hard_rule które AI nie wykryło
    unique_hard = [f for f in hard_flags if f["code"] not in ai_codes]

    return ai_issues + unique_hard
```

---

## Krok 5 — Weryfikacja krzyżowa wartości liczbowych (warstwa 2)

Utwórz `verifier_cross_check.py`.
Dla każdej etykiety wysyła osobne, uproszczone zapytanie tylko o liczby.
Porównuje z wynikami głównej weryfikacji i flaguje rozbieżności.

```python
"""
Weryfikacja krzyżowa wartości liczbowych — warstwa 2 rzetelności.
Wysyła osobne zapytanie do API tylko po wartości z tabeli analitycznej.
Porównuje z wynikami głównej ekstrakcji i flaguje rozbieżności > TOLERANCE.
"""
import json
import anthropic
from schemas import NUTRIENTS_ONLY_SCHEMA

# Tolerancja rozbieżności — powyżej tego progu wymagana ręczna weryfikacja
TOLERANCE_PERCENT = 0.5  # różnica > 0.5% punktu procentowego = flag


CROSS_CHECK_PROMPT = """Z tego obrazu etykiety odczytaj WYŁĄCZNIE liczby
z tabeli 'Analytical constituents', 'Składniki analityczne' lub odpowiednika
w dowolnym języku.

Podaj je DOKŁADNIE tak jak są napisane na etykiecie — bez żadnych obliczeń,
przeliczania ani konwersji. Jeśli cyfra jest nieczytelna, wpisz null.

W polu reading_notes opisz krótko jakość odczytu (np. 'wszystko czytelne'
lub 'liczba przy tłuszczu mogła być 8 lub 6 — niewyraźna')."""


def cross_check_nutrients(
    label_b64:    str,
    image_format: str,
    main_nutrients: dict,
    client: anthropic.Anthropic
) -> dict:
    """
    Wykonuje niezależny odczyt wartości odżywczych i porównuje z głównym wynikiem.

    Args:
        label_b64:       etykieta zakodowana base64
        image_format:    typ MIME obrazu
        main_nutrients:  wartości z głównej weryfikacji AI
        client:          klient Anthropic

    Returns:
        Słownik z kluczami:
        - passed (bool): True jeśli brak istotnych rozbieżności
        - discrepancies (list): lista rozbieżności > TOLERANCE_PERCENT
        - cross_check_values (dict): wartości z niezależnego odczytu
        - reading_notes (str): uwagi o jakości odczytu
    """
    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            output_config={
                "format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name":   "nutrients_cross_check",
                        "schema": NUTRIENTS_ONLY_SCHEMA
                    }
                }
            },
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type":       "base64",
                            "media_type": image_format,
                            "data":       label_b64
                        }
                    },
                    {"type": "text", "text": CROSS_CHECK_PROMPT}
                ]
            }]
        )

        cross_values = json.loads(response.content[0].text)
        reading_notes = cross_values.pop("reading_notes", "")

        discrepancies = []

        for nutrient, cross_val in cross_values.items():
            main_val = main_nutrients.get(nutrient)

            if cross_val is None or main_val is None:
                continue  # nie można porównać

            diff = abs(float(cross_val) - float(main_val))
            if diff > TOLERANCE_PERCENT:
                discrepancies.append({
                    "nutrient":    nutrient,
                    "main_value":  main_val,
                    "cross_value": cross_val,
                    "difference":  round(diff, 2)
                })

        return {
            "passed":             len(discrepancies) == 0,
            "discrepancies":      discrepancies,
            "cross_check_values": cross_values,
            "reading_notes":      reading_notes
        }

    except Exception as e:
        # Błąd weryfikacji krzyżowej nie blokuje głównego wyniku
        # ale jest odnotowany w raporcie
        return {
            "passed":             None,   # None = nie wykonano
            "discrepancies":      [],
            "cross_check_values": {},
            "reading_notes":      f"Błąd weryfikacji krzyżowej: {e}",
            "error":              str(e)
        }
```

---

## Krok 6 — Prompty systemowe

Utwórz `prompts.py`:

```python
SYSTEM_PROMPT_BASE = """Jesteś ekspertem ds. zgodności etykiet karmy dla zwierząt domowych.

Posiadasz wiedzę z zakresu:
- FEDIAF Nutritional Guidelines (załączony PDF)
- Rozporządzenie (WE) nr 767/2009 o wprowadzaniu na rynek pasz dla zwierząt domowych
- Wymagania etykietowania UE dla pet food

Twoje zadanie przy każdej weryfikacji:
1. Wyekstrahuj wszystkie dane z etykiety: składniki, wartości odżywcze, informacje o produkcie
2. Zidentyfikuj gatunek zwierzęcia i etap życia
3. Zweryfikuj zgodność wartości odżywczych z minimalnymi/maksymalnymi poziomami FEDIAF
4. Sprawdź wymagania etykietowania UE z Rozporządzenia 767/2009
5. Oceń pewność odczytu (extraction_confidence) i wymień wartości niepewne
6. Przypisz wynik compliance_score i status
7. Podaj konkretne rekomendacje naprawcze

Skala oceny:
- 90–100: pełna zgodność, produkt gotowy do rynku
- 70–89: drobne uwagi, produkt dopuszczalny z zaleceniami
- 50–69: istotne braki wymagające korekty przed wdrożeniem
- 0–49: krytyczne niezgodności, produkt nie może trafić na rynek

WAŻNE dotyczące extraction_confidence:
- HIGH: wszystkie wartości liczbowe są wyraźnie widoczne i jednoznaczne
- MEDIUM: większość wartości czytelna, ale 1–2 pozycje budzą wątpliwości
- LOW: znaczna część tabeli analitycznej nieczytelna lub niewidoczna

Zawsze odwołuj się do konkretnych sekcji i tabel FEDIAF (np. "Table 11").
Jeśli wartość nie jest widoczna na etykiecie, wpisz null — nie zakładaj wartości domyślnych.

Odpowiedz WYŁĄCZNIE poprawnym JSON zgodnym z podanym schematem."""


def build_trend_instruction(market: str) -> str:
    return f"""
Po weryfikacji FEDIAF, użyj narzędzia web_search aby wyszukać aktualne trendy rynkowe
dla tej kategorii produktu w: {market}.

Przykładowe zapytania do wyszukania:
- trendy składy karma [gatunek] {market} 2024 2025
- popular ingredients pet food {market} trends
- grain-free insect protein raw [gatunek] {market} popularity

Na podstawie wyników wyszukiwania wypełnij sekcję "market_trends" w JSON:
- positioning: oceń czy skład jest "trendy", "standard", "outdated" lub "niche"
- summary: krótki opis kontekstu rynkowego (2–4 zdania)
- trend_notes: lista konkretnych obserwacji

Sekcja trendów jest informacyjna — wyraźnie oddziel ją od oceny regulacyjnej."""
```

---

## Krok 7 — Konwersja formatów etykiet

Utwórz `converter.py`:

```python
"""Konwersja etykiet z różnych formatów do base64 PNG/JPEG."""
import base64
import io
import tempfile
import os
from pathlib import Path


def file_to_base64(file_bytes: bytes, filename: str) -> tuple[str, str]:
    """
    Konwertuje plik etykiety do base64.

    Returns:
        Tuple (base64_string, media_type)

    Raises:
        ValueError: dla nieobsługiwanych formatów
        RuntimeError: gdy konwersja docx nie powiedzie się
    """
    suffix = Path(filename).suffix.lower()

    if suffix in (".jpg", ".jpeg"):
        return base64.b64encode(file_bytes).decode(), "image/jpeg"

    if suffix == ".png":
        return base64.b64encode(file_bytes).decode(), "image/png"

    if suffix == ".docx":
        return _docx_to_base64(file_bytes)

    raise ValueError(
        f"Nieobsługiwany format pliku: {suffix}. Użyj JPG, PNG lub DOCX."
    )


def _docx_to_base64(docx_bytes: bytes) -> tuple[str, str]:
    """Konwertuje .docx → PDF → PNG (pierwsza strona)."""
    try:
        from docx2pdf import convert
        from pdf2image import convert_from_path
    except ImportError as e:
        raise RuntimeError(
            f"Brakująca biblioteka do konwersji DOCX: {e}. "
            "Uruchom: pip install docx2pdf pdf2image"
        )

    with tempfile.TemporaryDirectory() as tmpdir:
        docx_path = os.path.join(tmpdir, "label.docx")
        pdf_path  = os.path.join(tmpdir, "label.pdf")

        with open(docx_path, "wb") as f:
            f.write(docx_bytes)

        convert(docx_path, pdf_path)

        pages = convert_from_path(pdf_path, dpi=200)
        if not pages:
            raise RuntimeError("Nie udało się wczytać stron z pliku DOCX.")

        img_buffer = io.BytesIO()
        pages[0].save(img_buffer, format="PNG")
        img_buffer.seek(0)

        return base64.b64encode(img_buffer.read()).decode(), "image/png"


def load_pdf_base64(pdf_path: str) -> str:
    """Wczytuje PDF (np. FEDIAF Guidelines) jako base64."""
    with open(pdf_path, "rb") as f:
        return base64.b64encode(f.read()).decode()
```

---

## Krok 8 — Logika weryfikacji z wszystkimi warstwami

Utwórz `verifier.py`.
Ten plik koordynuje wszystkie pięć warstw rzetelności.

```python
"""
Weryfikacja etykiet FEDIAF — pełny pipeline z warstwami rzetelności.

Warstwy:
  1. Structured outputs + confidence scoring      → parametr extraction_confidence
  2. Weryfikacja krzyżowa wartości liczbowych     → cross_check_nutrients()
  3. Deterministyczne reguły FEDIAF              → hard_check()
  4. Human-in-the-loop (logika w app.py)         → na podstawie score + confidence
  5. Zestaw testowy                              → tests/test_accuracy.py
"""
import json
import os
import anthropic
from dotenv import load_dotenv

from schemas        import VERIFICATION_SCHEMA
from prompts        import SYSTEM_PROMPT_BASE, build_trend_instruction
from verifier_rules import hard_check, merge_with_ai_results
from verifier_cross_check import cross_check_nutrients

load_dotenv()

FEDIAF_PDF_PATH = os.path.join("data", "fediaf_guidelines_2021.pdf")

_client = None

def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "Brak klucza ANTHROPIC_API_KEY. "
                "Utwórz plik .env na podstawie .env.example."
            )
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def verify_label(
    label_b64:    str,
    fediaf_b64:   str,
    image_format: str       = "image/jpeg",
    market:       str | None = None,
) -> dict:
    """
    Weryfikuje etykietę — pełny pipeline z 5 warstwami rzetelności.

    Args:
        label_b64:    etykieta zakodowana base64
        fediaf_b64:   PDF wytycznych FEDIAF zakodowany base64
        image_format: typ MIME obrazu etykiety
        market:       kraj rynku docelowego lub None

    Returns:
        Słownik z raportem weryfikacyjnym, rozszerzony o:
        - hard_rule_flags:    problemy wykryte przez reguły deterministyczne
        - cross_check_result: wyniki weryfikacji krzyżowej
        - reliability_flags:  lista ostrzeżeń o rzetelności
        - requires_human_review: bool — czy wymagana weryfikacja człowieka
    """
    client = get_client()

    # ── Warstwa 1: Główna weryfikacja AI z confidence scoring ─────────────────
    system_prompt = SYSTEM_PROMPT_BASE
    if market:
        system_prompt += "\n\n" + build_trend_instruction(market)

    tools = [{"type": "web_search_20250305", "name": "web_search"}] if market else []

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8096,
        system=system_prompt,
        tools=tools if tools else anthropic.NOT_GIVEN,
        output_config={
            "format": {
                "type": "json_schema",
                "json_schema": {
                    "name":   "fediaf_verification_report",
                    "schema": VERIFICATION_SCHEMA
                }
            }
        },
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type":       "base64",
                        "media_type": "application/pdf",
                        "data":       fediaf_b64
                    },
                    "cache_control": {"type": "ephemeral"}
                },
                {
                    "type": "image",
                    "source": {
                        "type":       "base64",
                        "media_type": image_format,
                        "data":       label_b64
                    }
                },
                {
                    "type": "text",
                    "text": (
                        f"Zweryfikuj tę etykietę produktu pet food.\n"
                        f"Rynek: {market if market else 'nie określono'}.\n"
                        f"Zwróć kompletny raport JSON z oceną confidence."
                    )
                }
            ]
        }]
    )

    result = json.loads(next(b.text for b in response.content if b.type == "text"))

    # ── Warstwa 2: Weryfikacja krzyżowa wartości liczbowych ───────────────────
    main_nutrients = result.get("extracted_nutrients", {})
    cross_check = cross_check_nutrients(
        label_b64, image_format, main_nutrients, client
    )
    result["cross_check_result"] = cross_check

    # ── Warstwa 3: Deterministyczne reguły FEDIAF ─────────────────────────────
    hard_flags = hard_check(result)
    if hard_flags:
        result["issues"] = merge_with_ai_results(result.get("issues", []), hard_flags)
        # Przelicz status jeśli reguły wykryły krytyczne problemy
        has_critical = any(f["severity"] == "CRITICAL" for f in hard_flags)
        if has_critical and result.get("status") == "COMPLIANT":
            result["status"] = "NON_COMPLIANT"
            result["compliance_score"] = min(result.get("compliance_score", 100), 49)

    result["hard_rule_flags"] = hard_flags

    # ── Warstwa 4: Określenie czy wymagany przegląd człowieka ─────────────────
    reliability_flags = _assess_reliability(result, cross_check)
    result["reliability_flags"]    = reliability_flags
    result["requires_human_review"] = _requires_human_review(result, reliability_flags)

    return result


def _assess_reliability(result: dict, cross_check: dict) -> list[str]:
    """
    Ocenia rzetelność wyniku i zwraca listę ostrzeżeń.
    Nie zmienia wyniku — tylko informuje aplikację o ryzyku.
    """
    flags = []
    confidence = result.get("extraction_confidence", "HIGH")

    if confidence == "LOW":
        flags.append(
            "Niska pewność odczytu — znaczna część wartości może być błędnie "
            "odczytana z obrazu. Zalecana weryfikacja z oryginalną etykietą."
        )
    elif confidence == "MEDIUM":
        flags.append(
            "Średnia pewność odczytu — pojedyncze wartości odczytane z wątpliwością."
        )

    uncertain = result.get("values_requiring_manual_check", [])
    if uncertain:
        flags.append(
            f"Wartości wymagające sprawdzenia: {', '.join(uncertain)}"
        )

    if cross_check.get("passed") is False:
        discrepancies = cross_check.get("discrepancies", [])
        for d in discrepancies:
            flags.append(
                f"Rozbieżność w odczycie {d['nutrient']}: "
                f"główny odczyt {d['main_value']}%, "
                f"weryfikacja krzyżowa {d['cross_value']}% "
                f"(różnica {d['difference']}%). "
                "Sprawdź oryginał."
            )

    if cross_check.get("passed") is None:
        flags.append(
            "Weryfikacja krzyżowa nie została wykonana — "
            "wyniki opierają się wyłącznie na głównym odczycie."
        )

    hard_flags = result.get("hard_rule_flags", [])
    if hard_flags:
        flags.append(
            f"Reguły deterministyczne FEDIAF wykryły {len(hard_flags)} "
            "dodatkowych problemów niezależnie od analizy AI."
        )

    return flags


def _requires_human_review(result: dict, reliability_flags: list[str]) -> bool:
    """
    Określa czy wynik wymaga przeglądu przez specjalistę.
    Zwraca True dla przypadków granicznych lub niskiej pewności.
    """
    score      = result.get("compliance_score", 0)
    confidence = result.get("extraction_confidence", "HIGH")
    status     = result.get("status", "REQUIRES_REVIEW")
    cross_ok   = result.get("cross_check_result", {}).get("passed", True)

    return (
        score < 70 or
        confidence == "LOW" or
        status == "REQUIRES_REVIEW" or
        cross_ok is False or
        len(reliability_flags) >= 2
    )
```

---

## Krok 9 — Główna aplikacja Streamlit

Utwórz `app.py`:

```python
"""Aplikacja Streamlit — Weryfikator etykiet FEDIAF."""
import json
import os
import streamlit as st
from pathlib import Path

from converter import file_to_base64, load_pdf_base64
from verifier  import verify_label, FEDIAF_PDF_PATH

# ── Stałe progi decyzyjne ─────────────────────────────────────────────────────
AUTO_APPROVE_THRESHOLD  = 85   # score >= 85 + confidence HIGH → wynik automatyczny
MANUAL_REQUIRED_THRESHOLD = 60  # score < 60 LUB confidence LOW → blokada

# ── Konfiguracja Streamlit ────────────────────────────────────────────────────
st.set_page_config(
    page_title="Weryfikator etykiet FEDIAF",
    page_icon="🐾",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🐾 Weryfikator etykiet karmy")
st.caption(
    "Weryfikacja zgodności z FEDIAF Nutritional Guidelines + regulacje EU  |  "
    "5 warstw weryfikacji rzetelności"
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Ustawienia weryfikacji")

    MARKETS = [
        "— bez analizy trendów —", "Polska", "Niemcy", "Francja",
        "Wielka Brytania", "Czechy", "Węgry", "Rumunia", "Włochy", "Hiszpania"
    ]
    market_selection = st.selectbox(
        "Analiza trendów rynkowych",
        options=MARKETS,
        help=(
            "Opcjonalne. Jeśli wybierzesz kraj, raport zawiera sekcję "
            "z aktualnymi trendami rynkowymi dla tej kategorii."
        )
    )
    selected_market = None if market_selection == MARKETS[0] else market_selection

    if selected_market:
        st.info(f"Kontekst rynkowy: **{selected_market}**")
    else:
        st.caption("Weryfikacja obejmie wyłącznie FEDIAF i regulacje EU.")

    st.divider()

    if os.path.exists(FEDIAF_PDF_PATH):
        size_mb = os.path.getsize(FEDIAF_PDF_PATH) / 1_048_576
        st.success(f"FEDIAF Guidelines ({size_mb:.1f} MB) ✓")
    else:
        st.error(
            f"Brak pliku: `{FEDIAF_PDF_PATH}`\n\n"
            "Pobierz ze strony fediaf.org i zapisz w folderze data/."
        )
        st.stop()

    with st.expander("O warstwach weryfikacji"):
        st.markdown("""
**Jak zapewniamy rzetelność:**

1. **Confidence scoring** — model ocenia pewność odczytu każdej wartości
2. **Weryfikacja krzyżowa** — drugi niezależny odczyt wartości liczbowych
3. **Reguły deterministyczne** — progi FEDIAF zakodowane w Pythonie, niezależne od AI
4. **Human-in-the-loop** — automatyczne eskalacje do człowieka przy niskiej pewności
5. **Zestaw testowy** — weryfikacja na etykietach z ręcznie potwierdzonymi wynikami

*System jest narzędziem wspomagającym, nie zastępuje eksperta żywieniowego.*
""")

    st.divider()
    st.caption("v2.0 · Claude Sonnet 4.6")

# ── Upload etykiety ───────────────────────────────────────────────────────────
uploaded = st.file_uploader(
    "Wgraj etykietę produktu",
    type=["jpg", "jpeg", "png", "docx"],
    help="Obsługiwane formaty: JPG, PNG, DOCX"
)

if uploaded:
    col_preview, col_info = st.columns([1, 2])
    with col_preview:
        if uploaded.type.startswith("image"):
            st.image(uploaded, caption=uploaded.name, use_container_width=True)
        else:
            st.info(f"📄 {uploaded.name}")
    with col_info:
        st.write(f"**Plik:** {uploaded.name}")
        st.write(f"**Rozmiar:** {uploaded.size / 1024:.1f} KB")
        st.write(f"**Rynek:** {selected_market or 'nie wybrano'}")
        if selected_market:
            st.caption("Weryfikacja z web search będzie trwać ~60–90 sekund.")
        else:
            st.caption("Weryfikacja bez trendów ~30–60 sekund.")

# ── Weryfikacja ───────────────────────────────────────────────────────────────
if uploaded:
    if st.button("▶ Weryfikuj etykietę", type="primary", use_container_width=True):
        _run_verification(uploaded, selected_market)


def _run_verification(uploaded_file, market: str | None):
    spinner_msg = (
        "Weryfikuję + analizuję trendy... (ok. 60–90 sekund)"
        if market else
        "Weryfikuję etykietę... (ok. 30–60 sekund)"
    )

    with st.spinner(spinner_msg):
        try:
            label_b64, image_format = file_to_base64(
                uploaded_file.read(), uploaded_file.name
            )
            fediaf_b64 = load_pdf_base64(FEDIAF_PDF_PATH)
            result = verify_label(
                label_b64=label_b64,
                fediaf_b64=fediaf_b64,
                image_format=image_format,
                market=market
            )
        except EnvironmentError as e:
            st.error(f"**Błąd konfiguracji:** {e}")
            return
        except ValueError as e:
            st.error(f"**Błąd pliku:** {e}")
            return
        except Exception as e:
            st.error(f"**Błąd API:** {e}")
            return

    _render_report(result, uploaded_file.name, market)


def _render_report(result: dict, filename: str, market: str | None):
    """Renderuje raport z pełną informacją o rzetelności."""

    st.divider()
    st.subheader("Wyniki weryfikacji")

    product    = result.get("product", {})
    score      = result.get("compliance_score", 0)
    status     = result.get("status", "UNKNOWN")
    confidence = result.get("extraction_confidence", "?")
    issues     = result.get("issues", [])
    critical   = sum(1 for i in issues if i.get("severity") == "CRITICAL")
    warnings   = sum(1 for i in issues if i.get("severity") == "WARNING")
    requires_human = result.get("requires_human_review", False)

    # ── Baner wymagania ręcznej weryfikacji (WARSTWA 4) ───────────────────────
    if requires_human:
        if score < MANUAL_REQUIRED_THRESHOLD or confidence == "LOW":
            st.error(
                "⛔ **Ten wynik wymaga weryfikacji przez specjalistę przed użyciem.**  \n"
                "Pobierz raport i przekaż do sprawdzenia przez eksperta żywieniowego."
            )
        else:
            st.warning(
                "⚠️ **Zalecana weryfikacja przez specjalistę** przed podjęciem "
                "decyzji regulacyjnej."
            )
    else:
        st.success("✅ Wynik automatyczny — wysoka pewność odczytu i pełna zgodność.")

    # ── Metryki główne ────────────────────────────────────────────────────────
    STATUS_LABELS = {
        "COMPLIANT":       "✅ ZGODNA",
        "NON_COMPLIANT":   "❌ NIEZGODNA",
        "REQUIRES_REVIEW": "⚠️ DO SPRAWDZENIA"
    }
    CONF_LABELS = {"HIGH": "🟢 Wysoka", "MEDIUM": "🟡 Średnia", "LOW": "🔴 Niska"}

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Status",           STATUS_LABELS.get(status, status))
    col2.metric("Wynik zgodności",  f"{score}/100")
    col3.metric("Pewność odczytu",  CONF_LABELS.get(confidence, confidence))
    col4.metric("Problemy",         f"{critical} kryt. / {warnings} ostrzeż.")

    # Pasek postępu
    bar_color = "green" if score >= 90 else ("orange" if score >= 70 else "red")
    st.markdown(
        f'<div style="height:8px;border-radius:4px;background:var(--secondary-background-color);margin:8px 0 16px">'
        f'<div style="width:{score}%;height:8px;border-radius:4px;background:{bar_color}"></div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # ── Ostrzeżenia o rzetelności ─────────────────────────────────────────────
    reliability_flags = result.get("reliability_flags", [])
    if reliability_flags:
        with st.expander(f"⚠️ Ostrzeżenia o rzetelności ({len(reliability_flags)})", expanded=True):
            for flag in reliability_flags:
                st.warning(flag)

    # ── Weryfikacja krzyżowa ──────────────────────────────────────────────────
    cross = result.get("cross_check_result", {})
    if cross:
        cross_status = cross.get("passed")
        discrepancies = cross.get("discrepancies", [])
        with st.expander("Weryfikacja krzyżowa wartości liczbowych"):
            if cross_status is True:
                st.success("Oba odczyty zgodne — wartości potwierdzone.")
            elif cross_status is False:
                st.error(
                    f"Rozbieżności między odczytami ({len(discrepancies)}) — "
                    "sprawdź oryginał etykiety."
                )
                for d in discrepancies:
                    st.write(
                        f"• **{d['nutrient']}**: odczyt główny {d['main_value']}%, "
                        f"weryfikacja {d['cross_value']}% (różnica {d['difference']}%)"
                    )
            else:
                st.info("Weryfikacja krzyżowa nie była możliwa.")
            if cross.get("reading_notes"):
                st.caption(f"Uwagi: {cross['reading_notes']}")

    # ── Reguły deterministyczne ───────────────────────────────────────────────
    hard_flags = result.get("hard_rule_flags", [])
    if hard_flags:
        with st.expander(f"🔒 Reguły deterministyczne FEDIAF ({len(hard_flags)} problemów)"):
            st.caption(
                "Poniższe problemy zostały wykryte przez reguły zakodowane bezpośrednio "
                "w Pythonie — niezależnie od odpowiedzi modelu AI."
            )
            for flag in hard_flags:
                st.error(
                    f"**[{flag['code']}]** {flag['description']}  \n"
                    f"Odniesienie: {flag.get('fediaf_reference', '—')}"
                )

    # ── Dane produktu ─────────────────────────────────────────────────────────
    with st.expander("Dane produktu i wartości odżywcze", expanded=False):
        p = result.get("product", {})
        c1, c2, c3 = st.columns(3)
        c1.write(f"**Gatunek:** {p.get('species','—')}")
        c2.write(f"**Etap życia:** {p.get('lifestage','—')}")
        c3.write(f"**Typ karmy:** {p.get('food_type','—')}")
        if p.get("name"):  st.write(f"**Nazwa:** {p['name']}")
        if p.get("brand"): st.write(f"**Marka:** {p['brand']}")

        nutrients = result.get("extracted_nutrients", {})
        uncertain = set(result.get("values_requiring_manual_check", []))
        if any(v is not None for v in nutrients.values()):
            st.markdown("**Wyekstrahowane wartości odżywcze:**")
            LABELS = {
                "crude_protein": "Białko surowe",
                "crude_fat":     "Tłuszcz surowy",
                "crude_fibre":   "Włókno surowe",
                "moisture":      "Wilgotność",
                "crude_ash":     "Popiół surowy",
                "calcium":       "Wapń",
                "phosphorus":    "Fosfor"
            }
            items = [(label, nutrients.get(k), k in str(uncertain))
                     for k, label in LABELS.items() if nutrients.get(k) is not None]
            n_cols = st.columns(4)
            for idx, (label, val, uncertain_flag) in enumerate(items):
                suffix = " ⚠️" if uncertain_flag else ""
                n_cols[idx % 4].metric(label + suffix, f"{val}%")

    # ── Problemy regulacyjne ──────────────────────────────────────────────────
    st.subheader(f"Kwestie regulacyjne ({len(issues)})")
    if not issues:
        st.success("Nie wykryto problemów regulacyjnych.")
    else:
        SEV_ICONS  = {"CRITICAL": "🔴", "WARNING": "🟡", "INFO": "🔵"}
        SEV_LABELS = {"CRITICAL": "Krytyczne", "WARNING": "Ostrzeżenie", "INFO": "Informacja"}
        for issue in issues:
            sev   = issue.get("severity", "INFO")
            src   = " [REGUŁA]" if issue.get("source") == "HARD_RULE" else ""
            label = SEV_LABELS.get(sev, sev)
            with st.expander(
                f"{SEV_ICONS.get(sev,'⚪')} [{label}{src}] {issue.get('description','')}"
            ):
                cols = st.columns(2)
                if issue.get("fediaf_reference"):
                    cols[0].write(f"**Odniesienie FEDIAF:** {issue['fediaf_reference']}")
                if issue.get("found_value") is not None:
                    cols[0].write(f"**Znaleziono:** {issue['found_value']}")
                if issue.get("required_value"):
                    cols[1].write(f"**Wymagane:** {issue['required_value']}")
                if issue.get("code"):
                    cols[1].write(f"**Kod:** `{issue['code']}`")

    # ── EU labelling ──────────────────────────────────────────────────────────
    eu_check = result.get("eu_labelling_check", {})
    if eu_check:
        st.subheader("Wymagania etykietowania EU (Rozp. 767/2009)")
        EU_LABELS = {
            "ingredients_listed":              "Lista składników",
            "analytical_constituents_present": "Składniki analityczne",
            "manufacturer_info":               "Dane producenta",
            "net_weight_declared":             "Masa netto",
            "species_clearly_stated":          "Gatunek zwierzęcia",
            "batch_or_date_present":           "Numer partii / data"
        }
        eu_cols = st.columns(3)
        for idx, (key, label) in enumerate(EU_LABELS.items()):
            val  = eu_check.get(key)
            icon = "✅" if val is True else ("❌" if val is False else "—")
            eu_cols[idx % 3].write(f"{icon} {label}")

    # ── Rekomendacje ──────────────────────────────────────────────────────────
    recs = result.get("recommendations", [])
    if recs:
        st.subheader("Rekomendacje")
        for rec in recs:
            st.write(f"→ {rec}")

    # ── Trendy rynkowe ────────────────────────────────────────────────────────
    trends = result.get("market_trends")
    if trends and market:
        st.divider()
        st.subheader(f"📊 Trendy rynkowe — {market}")
        POSITIONING_LABELS = {
            "trendy":   ("🟢", "Zgodny z trendami"),
            "standard": ("🔵", "Standardowy skład"),
            "outdated": ("🔴", "Przestarzały skład"),
            "niche":    ("🟡", "Niszowy / rosnący")
        }
        pos = trends.get("positioning", "standard")
        pos_icon, pos_label = POSITIONING_LABELS.get(pos, ("⚪", pos))
        st.metric("Pozycjonowanie składu", f"{pos_icon} {pos_label}")
        st.info(trends.get("summary", ""))
        notes = trends.get("trend_notes", [])
        if notes:
            with st.expander("Szczegółowe obserwacje"):
                for note in notes:
                    st.write(f"• {note}")

    # ── Stopka z zastrzeżeniem ────────────────────────────────────────────────
    st.divider()
    st.caption(
        "⚠️ **Zastrzeżenie:** Raport wygenerowany automatycznie przez system AI. "
        "Wyniki poniżej 85 punktów lub oznaczone jako REQUIRES_REVIEW wymagają "
        "weryfikacji przez wykwalifikowanego specjalistę ds. żywienia zwierząt "
        "przed podjęciem jakiejkolwiek decyzji regulacyjnej. "
        "Producent narzędzia nie ponosi odpowiedzialności za decyzje podjęte "
        "wyłącznie na podstawie automatycznego raportu."
    )

    # ── Eksport ───────────────────────────────────────────────────────────────
    stem = Path(filename).stem
    col_a, col_b = st.columns(2)
    with col_a:
        st.download_button(
            "⬇ Pobierz raport JSON",
            data=json.dumps(result, ensure_ascii=False, indent=2),
            file_name=f"raport_{stem}.json",
            mime="application/json",
            use_container_width=True
        )
    with col_b:
        st.download_button(
            "⬇ Pobierz raport TXT",
            data=_format_text_report(result, filename, market),
            file_name=f"raport_{stem}.txt",
            mime="text/plain",
            use_container_width=True
        )


def _format_text_report(result: dict, filename: str, market: str | None) -> str:
    lines = [
        "=" * 60,
        "RAPORT WERYFIKACJI FEDIAF",
        "=" * 60,
        f"Plik:            {filename}",
        f"Rynek:           {market or 'nie określono'}",
        f"Status:          {result.get('status','—')}",
        f"Wynik zgodności: {result.get('compliance_score',0)}/100",
        f"Pewność odczytu: {result.get('extraction_confidence','—')}",
        f"Wymaga przeglądu: {'TAK' if result.get('requires_human_review') else 'NIE'}",
        "",
    ]

    reliability_flags = result.get("reliability_flags", [])
    if reliability_flags:
        lines.append("OSTRZEŻENIA O RZETELNOŚCI:")
        for flag in reliability_flags:
            lines.append(f"  ! {flag}")
        lines.append("")

    hard_flags = result.get("hard_rule_flags", [])
    if hard_flags:
        lines.append("PROBLEMY WYKRYTE PRZEZ REGUŁY DETERMINISTYCZNE:")
        for flag in hard_flags:
            lines.append(f"  [REGUŁA][{flag['severity']}] {flag['description']}")
        lines.append("")

    issues = result.get("issues", [])
    lines.append(f"PROBLEMY REGULACYJNE ({len(issues)}):")
    for issue in issues:
        lines.append(f"  [{issue.get('severity','INFO')}] {issue.get('description','')}")
        if issue.get("fediaf_reference"):
            lines.append(f"    Odniesienie: {issue['fediaf_reference']}")
        if issue.get("found_value") is not None:
            lines.append(f"    Znaleziono: {issue['found_value']} | Wymagane: {issue.get('required_value','—')}")

    recs = result.get("recommendations", [])
    if recs:
        lines += ["", "REKOMENDACJE:"] + [f"  -> {r}" for r in recs]

    trends = result.get("market_trends")
    if trends and market:
        lines += [
            "", f"TRENDY RYNKOWE — {market}:",
            f"  Pozycjonowanie: {trends.get('positioning','—')}",
            f"  {trends.get('summary','')}",
        ]

    lines += [
        "", "=" * 60,
        "ZASTRZEŻENIE: Raport wygenerowany automatycznie przez system AI.",
        "Wyniki < 85 pkt lub REQUIRES_REVIEW wymagają weryfikacji eksperta",
        "ds. żywienia zwierząt przed podjęciem decyzji regulacyjnej.",
        "=" * 60,
    ]
    return "\n".join(lines)
```

---

## Krok 10 — Testy dokładności (warstwa 5)

Utwórz `tests/test_accuracy.py`:

```python
"""
Testy dokładności — warstwa 5 rzetelności.

Jak używać:
1. Zbierz 20–30 etykiet z ręcznie zweryfikowanymi wynikami (ekspert żywieniowy)
2. Umieść je w tests/reference_cases/
3. Utwórz plik tests/reference_cases/ground_truth.json (format poniżej)
4. Uruchom: pytest tests/test_accuracy.py -v

Cel minimalny: >= 95% dokładności statusu (COMPLIANT/NON_COMPLIANT/REQUIRES_REVIEW)
"""
import json
import pytest
from pathlib import Path

GROUND_TRUTH_PATH = Path("tests/reference_cases/ground_truth.json")
MIN_ACCURACY = 0.95


def load_ground_truth() -> list[dict]:
    """
    Format ground_truth.json:
    [
      {
        "file": "etykieta_pies_adult_01.jpg",
        "expected_status": "COMPLIANT",
        "expected_score_min": 85,
        "notes": "Karma sucha pies dorosły, wszystkie wartości powyżej minimum"
      },
      ...
    ]
    """
    if not GROUND_TRUTH_PATH.exists():
        pytest.skip(
            f"Brak pliku {GROUND_TRUTH_PATH}. "
            "Dodaj etykiety referencyjne z ręcznie zweryfikowanymi wynikami."
        )
    with open(GROUND_TRUTH_PATH) as f:
        return json.load(f)


def test_status_accuracy():
    """Sprawdza dokładność klasyfikacji statusu na zbiorze referencyjnym."""
    from converter import file_to_base64, load_pdf_base64
    from verifier  import verify_label, FEDIAF_PDF_PATH

    cases       = load_ground_truth()
    fediaf_b64  = load_pdf_base64(FEDIAF_PDF_PATH)
    correct     = 0
    errors      = []

    for case in cases:
        filepath = Path("tests/reference_cases") / case["file"]
        if not filepath.exists():
            errors.append({"file": case["file"], "error": "Plik nie istnieje"})
            continue

        label_b64, image_format = file_to_base64(filepath.read_bytes(), case["file"])
        result = verify_label(label_b64, fediaf_b64, image_format)

        expected = case["expected_status"]
        actual   = result["status"]

        if actual == expected:
            correct += 1
        else:
            errors.append({
                "file":     case["file"],
                "expected": expected,
                "got":      actual,
                "score":    result["compliance_score"],
                "notes":    case.get("notes", "")
            })

    accuracy = correct / len(cases) if cases else 0

    print(f"\nDokładność: {accuracy:.1%} ({correct}/{len(cases)})")
    if errors:
        print("\nBłędne klasyfikacje:")
        for e in errors:
            print(f"  {e['file']}: oczekiwano {e.get('expected','?')}, "
                  f"otrzymano {e.get('got','ERROR')} (score: {e.get('score','?')})")

    assert accuracy >= MIN_ACCURACY, (
        f"Dokładność {accuracy:.1%} poniżej progu {MIN_ACCURACY:.1%}. "
        f"Sprawdź błędne klasyfikacje powyżej."
    )


def test_hard_rules_catch_known_violations():
    """
    Sprawdza czy reguły deterministyczne wykrywają znane naruszenia.
    Używa syntetycznych danych — nie wymaga pliku PDF ani API.
    """
    from verifier_rules import hard_check

    # Karma sucha pies dorosły z białkiem poniżej minimum
    result_below_min = {
        "product": {"species": "dog", "lifestage": "adult", "food_type": "dry"},
        "extracted_nutrients": {
            "crude_protein": 15.0,   # poniżej minimum 18% DM
            "crude_fat": 8.0,
            "moisture": 10.0
        },
        "issues": []
    }
    flags = hard_check(result_below_min)
    assert any(f["code"] == "CRUDE_PROTEIN_BELOW_MIN" for f in flags), (
        "Reguła powinna wykryć białko poniżej minimum dla psa dorosłego"
    )

    # Produkt zgodny — brak flag
    result_ok = {
        "product": {"species": "dog", "lifestage": "adult", "food_type": "dry"},
        "extracted_nutrients": {
            "crude_protein": 22.0,
            "crude_fat": 8.0,
            "moisture": 10.0
        },
        "issues": []
    }
    flags_ok = hard_check(result_ok)
    critical_ok = [f for f in flags_ok if f["severity"] == "CRITICAL"]
    assert len(critical_ok) == 0, (
        f"Brak krytycznych flag oczekiwany, otrzymano: {critical_ok}"
    )
```

Utwórz `tests/reference_cases/README.md`:

```markdown
# Zbiór referencyjny — etykiety z ręcznie zweryfikowanymi wynikami

## Jak dodać przypadek testowy

1. Umieść plik etykiety w tym folderze (JPG, PNG lub DOCX)
2. Poproś eksperta żywieniowego o ręczną weryfikację zgodności z FEDIAF
3. Dodaj wpis do `ground_truth.json`

## Format ground_truth.json

```json
[
  {
    "file": "nazwa_pliku.jpg",
    "expected_status": "COMPLIANT",
    "expected_score_min": 85,
    "verified_by": "Imię Nazwisko, data",
    "notes": "Karma sucha pies dorosły — wszystkie wartości powyżej minimum FEDIAF"
  }
]
```

## Cel minimalny

Minimum 20 przypadków testowych przed uruchomieniem produkcyjnym.
Docelowo: >= 95% dokładności klasyfikacji statusu.

## Typy przypadków do uwzględnienia

- Karma sucha pies dorosły — zgodna
- Karma sucha pies dorosły — białko poniżej minimum
- Karma mokra kot dorosły — zgodna
- Karma dla szczeniąt — wapń powyżej maksimum
- Etykieta z brakującymi wartościami (popiół, wapń)
- Etykieta niewyraźna / złej jakości zdjęcie
- Produkt "all life stages" pies
```

---

## Krok 11 — Plik README dla użytkowników

Utwórz `README.md`:

```markdown
# Weryfikator etykiet FEDIAF v2

Narzędzie do weryfikacji etykiet karmy dla zwierząt domowych.
Weryfikacja zgodności z FEDIAF Nutritional Guidelines 2021 + regulacje EU.

## Jak działa weryfikacja rzetelności

System stosuje 5 niezależnych warstw:
1. Model AI ocenia pewność każdego odczytu (HIGH/MEDIUM/LOW)
2. Drugi niezależny odczyt wartości liczbowych porównywany z pierwszym
3. Progi FEDIAF zakodowane w Pythonie — niezależne od AI
4. Automatyczna eskalacja do eksperta przy niskiej pewności lub problemach
5. Zestaw testowy z ręcznie zweryfikowanymi wynikami

## Wymagania

- Python 3.11+
- Klucz API Anthropic (console.anthropic.com)
- Plik FEDIAF Nutritional Guidelines 2021 (PDF, fediaf.org — bezpłatny po rejestracji)

## Instalacja (jednorazowo)

```bash
pip install -r requirements.txt
cp .env.example .env
# Otwórz .env i wpisz klucz ANTHROPIC_API_KEY
# Umieść fediaf_guidelines_2021.pdf w folderze data/
```

## Uruchomienie

```bash
streamlit run app.py
```

## Obsługiwane formaty etykiet

JPG · PNG · DOCX (Word)

## Kiedy wynik wymaga weryfikacji eksperta

System automatycznie oznacza wynik jako wymagający przeglądu gdy:
- Wynik zgodności < 70 punktów
- Pewność odczytu = NISKA (etykieta niewyraźna, złe zdjęcie)
- Status = DO SPRAWDZENIA
- Rozbieżność między dwoma niezależnymi odczytami > 0.5%

## Zastrzeżenie

Narzędzie wspomagające — nie zastępuje weryfikacji przez
wykwalifikowanego specjalistę ds. żywienia zwierząt.
```

---

## Krok 12 — Weryfikacja instalacji

Po utworzeniu wszystkich plików wykonaj w kolejności:

```bash
# 1. Struktura projektu
ls -la fediaf-verifier/

# 2. Zależności
cd fediaf-verifier
pip install -r requirements.txt

# 3. Konfiguracja API
python -c "from verifier import get_client; get_client(); print('API OK')"

# 4. Testy jednostkowe reguł (nie wymagają API ani PDF)
pytest tests/test_accuracy.py::test_hard_rules_catch_known_violations -v

# 5. Uruchomienie aplikacji
streamlit run app.py
```

---

## Podsumowanie warstw rzetelności

| Warstwa | Plik | Co robi |
|---|---|---|
| 1. Confidence scoring | `schemas.py`, `verifier.py` | Model ocenia pewność każdego odczytu |
| 2. Weryfikacja krzyżowa | `verifier_cross_check.py` | Drugi niezależny odczyt liczb, porównanie |
| 3. Reguły deterministyczne | `verifier_rules.py` | Progi FEDIAF w Pythonie, niezależne od AI |
| 4. Human-in-the-loop | `app.py` | Blokada/ostrzeżenie przy niskiej pewności |
| 5. Zestaw testowy | `tests/` | Walidacja na etykietach z ręcznymi wynikami |
