# Weryfikator etykiet FEDIAF v2

Narzedzie do weryfikacji etykiet karmy dla zwierzat domowych.
Weryfikacja zgodnosci z FEDIAF Nutritional Guidelines 2021 + regulacje EU (Rozp. 767/2009).

## Jak dziala weryfikacja rzetelnosci

System stosuje 5 niezaleznych warstw:

1. **Confidence scoring** — model AI ocenia pewnosc kazdego odczytu (HIGH/MEDIUM/LOW)
2. **Weryfikacja krzyzowa** — drugi niezalezny odczyt wartosci liczbowych porownywany z pierwszym
3. **Reguly deterministyczne** — progi FEDIAF zakodowane w Pythonie, niezalezne od AI
4. **Human-in-the-loop** — automatyczna eskalacja do eksperta przy niskiej pewnosci lub problemach
5. **Zestaw testowy** — walidacja na etykietach z recznie zweryfikowanymi wynikami

## Wymagania

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (zalecany) lub pip
- Klucz API Anthropic ([console.anthropic.com](https://console.anthropic.com))
- Plik FEDIAF Nutritional Guidelines 2021 (PDF, [fediaf.org](https://fediaf.org) — bezplatny po rejestracji)

## Instalacja

```bash
# Zainstaluj zaleznosci
uv sync

# Skopiuj plik konfiguracyjny
cp .env.example .env

# Otworz .env i wpisz klucz ANTHROPIC_API_KEY

# Umiesc fediaf_guidelines_2021.pdf w folderze data/
```

## Uruchomienie

```bash
uv run streamlit run src/fediaf_verifier/app.py
```

## Obslugiwane formaty etykiet

JPG | PNG | PDF | DOCX (wymaga LibreOffice)

## Testy

```bash
# Testy jednostkowe (bez klucza API)
uv run pytest -m "not slow" -v

# Pelny zestaw testowy (wymaga klucza API + FEDIAF PDF + etykiety referencyjne)
uv run pytest -v
```

## Kiedy wynik wymaga weryfikacji eksperta

System automatycznie oznacza wynik jako wymagajacy przegladu gdy:
- Wynik zgodnosci < 70 punktow
- Pewnosc odczytu = NISKA (etykieta niewyrazna, zle zdjecie)
- Status = DO SPRAWDZENIA
- Rozbieznosc miedzy dwoma niezaleznymi odczytami > 0.5%

## Narzedzia deweloperskie

```bash
# Linting
uv run ruff check src/ tests/

# Formatowanie
uv run ruff format src/ tests/

# Sprawdzanie typow
uv run pyright src/
```

## Zastrzezenie

Narzedzie wspomagajace — nie zastepuje weryfikacji przez
wykwalifikowanego specjaliste ds. zywienia zwierzat.
