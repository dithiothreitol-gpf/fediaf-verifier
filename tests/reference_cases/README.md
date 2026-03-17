# Zbior referencyjny — etykiety z recznie zweryfikowanymi wynikami

## Jak dodac przypadek testowy

1. Umiesc plik etykiety w tym folderze (JPG, PNG, PDF lub DOCX)
2. Popros eksperta zywieniowego o reczna weryfikacje zgodnosci z FEDIAF
3. Dodaj wpis do `ground_truth.json`

## Format ground_truth.json

```json
[
  {
    "file": "nazwa_pliku.jpg",
    "expected_status": "COMPLIANT",
    "expected_score_min": 85,
    "verified_by": "Imie Nazwisko, data",
    "notes": "Karma sucha pies dorosly — wszystkie wartosci powyzej minimum FEDIAF"
  }
]
```

## Cel minimalny

Minimum 20 przypadkow testowych przed uruchomieniem produkcyjnym.
Docelowo: >= 95% dokladnosci klasyfikacji statusu.

## Typy przypadkow do uwzglednienia

- Karma sucha pies dorosly — zgodna
- Karma sucha pies dorosly — bialko ponizej minimum
- Karma mokra kot dorosly — zgodna
- Karma dla szczeniat — wapn powyzej maksimum
- Etykieta z brakujacymi wartosciami (popiol, wapn)
- Etykieta niewyrazna / zlej jakosci zdjecie
- Produkt "all life stages" pies
