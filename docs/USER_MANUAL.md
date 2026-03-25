# BULT Quality Assurance --- Podręcznik użytkownika

**Wersja aplikacji:** 1.0
**Data dokumentu:** marzec 2026
**Dotyczy:** BULT Quality Assurance — system weryfikacji etykiet karm dla zwierząt

---

## Spis treści

1. [Wprowadzenie](#1-wprowadzenie)
   - 1.1 [Architektura systemu](#11-architektura-systemu)
   - 1.2 [Jak uruchomić aplikację](#12-jak-uruchomić-aplikację)
2. [Szybki start](#2-szybki-start)
   - 2.1 [Krok po kroku — pierwsza analiza](#21-krok-po-kroku--pierwsza-analiza)
3. [Kategoria "Weryfikacja" — 7 trybów](#3-kategoria-weryfikacja--7-trybów)
   - 3.1 [Pełna weryfikacja](#31-pełna-weryfikacja)
   - 3.2 [Weryfikacja językowa](#32-weryfikacja-językowa)
   - 3.3 [Kontrola struktury i czcionki](#33-kontrola-struktury-i-czcionki)
   - 3.4 [Walidator claimów](#34-walidator-claimów)
   - 3.5 [Weryfikator nazw i zastrzeżeń](#35-weryfikator-nazw-i-zastrzeżeń)
   - 3.6 [Walidator rynkowy](#36-walidator-rynkowy)
   - 3.7 [Inspekcja artwork](#37-inspekcja-artwork)
4. [Kategoria "Narzędzia" — 5 trybów](#4-kategoria-narzędzia--5-trybów)
   - 4.1 [Tłumaczenie etykiety](#41-tłumaczenie-etykiety)
   - 4.2 [Generator tekstu etykiety](#42-generator-tekstu-etykiety)
   - 4.3 [Generator opisów produktów](#43-generator-opisów-produktów)
   - 4.4 [Porównanie wersji](#44-porównanie-wersji)
   - 4.5 [Walidator EAN/kodów](#45-walidator-eankodów)
5. [Kategoria "Design" — 1 tryb](#5-kategoria-design--1-tryb)
   - 5.1 [Analiza projektu graficznego](#51-analiza-projektu-graficznego)
6. [Słownik pojęć](#6-słownik-pojęć)
7. [FAQ — Najczęściej zadawane pytania](#7-faq--najczęściej-zadawane-pytania)
8. [Wskazówki dla Marketingu vs R&D](#rozdział-8-wskazówki-dla-marketingu-vs-rd)
   - 8.1 [Dla działu Marketingu](#81-dla-działu-marketingu)
   - 8.2 [Dla działu R&D](#82-dla-działu-rd)
   - 8.3 [Współpraca między działami](#83-współpraca-między-działami)
9. [Formaty eksportu — tabela referencyjna](#rozdział-9-formaty-eksportu--tabela-referencyjna)
10. [Funkcje opcjonalne](#rozdział-10-funkcje-opcjonalne)
- [Załącznik A: Lista krajów walidatora rynkowego](#załącznik-a-lista-krajów-walidatora-rynkowego)
- [Załącznik B: Progi FEDIAF 2021](#załącznik-b-progi-fediaf-2021)
- [Załącznik C: 6 wymagań EU 767/2009](#załącznik-c-6-wymagań-eu-7672009)
- [Załącznik D: Checklista kontroli opakowania](#załącznik-d-checklista-kontroli-opakowania)

---

## 1. Wprowadzenie

### Czym jest BULT Quality Assurance?

BULT Quality Assurance (BULT QA) to aplikacja wspomagająca weryfikację etykiet karm dla zwierząt domowych. System sprawdza etykiety pod kątem zgodności z:

- **FEDIAF Nutritional Guidelines 2021** — europejskie wytyczne żywieniowe dla karm, definiujące minimalne i maksymalne wartości składników odżywczych w zależności od gatunku, etapu życia i typu karmy.
- **Rozporządzenie UE 767/2009** — główna regulacja Unii Europejskiej dotycząca wprowadzania do obrotu i stosowania pasz (w tym karm dla zwierząt domowych), określająca obowiązkowe elementy etykiety.

Aplikacja nie zastępuje eksperta ds. jakości ani audytu certyfikacyjnego. Jest narzędziem przyspieszającym pracę — eliminuje 80–90% rutynowej kontroli i sygnalizuje potencjalne problemy wymagające uwagi człowieka.

### 5 warstw niezawodności

System opiera się na pięciu niezależnych warstwach weryfikacji, dzięki czemu błąd jednej warstwy nie propaguje się na wynik końcowy:

| # | Warstwa | Opis |
|---|---------|------|
| 1 | **AI Confidence Scoring** | Każdy odczyt z etykiety otrzymuje poziom pewności: HIGH, MEDIUM lub LOW. Niska pewność automatycznie flaguje raport do ręcznego sprawdzenia. |
| 2 | **Cross-Check (weryfikacja krzyżowa)** | Niezależny, drugi odczyt wartości liczbowych z tabeli analitycznej. Jeśli różnica między odczytami przekracza 0,5%, system raportuje rozbieżność. |
| 3 | **Deterministyczne reguły FEDIAF** | Progi żywieniowe zakodowane w Pythonie — działają niezależnie od AI. Nawet jeśli model AI się pomyli, ta warstwa wyłapie naruszenia progów minimalnych i maksymalnych. |
| 4 | **Human-in-the-loop** | System automatycznie oznacza raporty wymagające przeglądu przez człowieka na podstawie wyniku, pewności odczytu i liczby problemów. |
| 5 | **Test set validation** | Zestaw referencyjnych etykiet z ręcznie zweryfikowanymi wynikami, służący do ciągłej walidacji dokładności systemu. |

### Dla kogo jest ten podręcznik?

Podręcznik jest przeznaczony dla dwóch grup odbiorców:

- **Dział marketingu** — osoby przygotowujące projekty etykiet, briefy dla grafików, opisy produktów i materiały handlowe. BULT QA pomaga zweryfikować etykietę przed drukiem i wychwycić problemy regulacyjne zanim produkt trafi na półkę.
- **Dział R&D (badania i rozwój)** — technolodzy żywności, specjaliści ds. jakości i osoby odpowiedzialne za formulacje. BULT QA sprawdza zgodność składu odżywczego z FEDIAF, waliduje claimy marketingowe względem rzeczywistego składu i generuje szczegółowe raporty techniczne.

Nie jest wymagana wiedza techniczna ani programistyczna. Interfejs jest całkowicie graficzny i dostępny przez przeglądarkę internetową.

### Obsługiwane formaty plików

| Format | Rozszerzenia | Opis |
|--------|-------------|------|
| **Obrazy** | `.jpg`, `.jpeg`, `.png` | Zdjęcie etykiety — najlepiej cała etykieta, dobra ostrość |
| **PDF** | `.pdf` | Specyfikacja produktu lub eksport z Adobe Illustratora |
| **Word** | `.docx` | Dokument Word (wymaga LibreOffice do konwersji) |
| **TIFF** | `.tiff`, `.tif` | Tylko w trybie "🔍 Inspekcja artwork" — format drukarski |

### Maksymalny rozmiar pliku

Limit uploadu wynosi **50 MB** na plik. W przypadku wielostronicowych PDF system analizuje pierwszy produkt. Dla najlepszych wyników zalecamy pliki o rozmiarze poniżej 10 MB.

### Zastrzeżenie (disclaimer)

BULT Quality Assurance jest narzędziem wspomagającym, a nie zastępującym profesjonalną ocenę. W szczególności:

- Wyniki analiz AI mają charakter orientacyjny i mogą zawierać błędy.
- System nie ma dostępu do rejestrów znaków towarowych (EUIPO, UPRP) — analiza IP jest sygnalizacyjna.
- Tłumaczenia generowane przez AI wymagają weryfikacji przez profesjonalnego tłumacza.
- Raporty nie stanowią opinii prawnej ani certyfikatu zgodności.
- Przed wprowadzeniem produktu na nowy rynek eksportowy zawsze skonsultuj etykietę ze specjalistą ds. regulacji danego kraju.

---

### 1.1 Architektura systemu

BULT QA składa się z trzech współpracujących komponentów:

**Komponent 1 — Ekstrakcja danych (AI)**
System odczytuje z przesłanego obrazu lub dokumentu wszystkie dane widoczne na etykiecie: nazwę produktu, skład, wartości odżywcze, claimy, elementy opakowania i języki. Na tym etapie AI nie ocenia zgodności — wyłącznie opisuje co widzi na etykiecie.

**Komponent 2 — Analiza deterministyczna (Python)**
Wyekstrahowane dane trafiają do silnika reguł napisanego w Pythonie. Tutaj odbywa się właściwa weryfikacja: porównanie wartości odżywczych z progami FEDIAF, sprawdzenie 6 wymagań EU 767/2009, weryfikacja ponad 30 punktów kontrolnych opakowania oraz analiza spójności claimów ze składem. Ten komponent działa całkowicie niezależnie od AI.

**Komponent 3 — Weryfikacja krzyżowa i językowa (AI)**
Niezależne, drugie wywołanie AI odczytuje ponownie wartości liczbowe z tabeli analitycznej i porównuje je z pierwszym odczytem (tolerancja: 0,5%). Jednocześnie sprawdzana jest jakość językowa tekstu na etykiecie.

**Wynik końcowy** — compliance score (0–100 punktów) — jest obliczany na podstawie twardych reguł deterministycznych, nie interpretacji AI. Kary za poszczególne typy problemów:

| Typ problemu | Kara punktowa |
|-------------|---------------|
| CRITICAL (krytyczny) | -15 punktów |
| WARNING (ostrzeżenie) | -5 punktów |
| INFO (informacja) | -1 punkt |

Progi decyzyjne:

| Wynik | Status | Działanie |
|-------|--------|-----------|
| 70–100 | COMPLIANT | Etykieta zgodna |
| 50–69 | REQUIRES_REVIEW | Wymaga przeglądu eksperta |
| 0–49 | NON_COMPLIANT | Niezgodna — wymaga korekty |

> **Uwaga:** W konfiguracji aplikacji istnieją dodatkowe progi UI: `auto_approve_threshold = 85` (baner zielony) i `manual_required_threshold = 60` (automatyczne flagowanie do ręcznego przeglądu). Te progi wpływają na wygląd raportów, ale sam status compliance (COMPLIANT / REQUIRES_REVIEW / NON_COMPLIANT) jest przypisywany na podstawie progów 70/50.

---

### 1.2 Jak uruchomić aplikację

BULT QA jest aplikacją przeglądarkową opartą na platformie Streamlit. Nie wymaga instalacji na komputerze użytkownika — wystarczy przeglądarka internetowa.

**Krok 1.** Otwórz przeglądarkę (Chrome, Firefox, Edge lub Safari).

**Krok 2.** Wpisz adres aplikacji przekazany przez administratora (zazwyczaj `http://localhost:8501` lub adres serwera firmowego).

**Krok 3.** Aplikacja otworzy się z ciemnym motywem (dark theme) i tytułem "🐾 BULT Quality Assurance" na górze strony.

**Krok 4.** Jeśli zobaczysz komunikat "Błąd konfiguracji" — skontaktuj się z administratorem. Oznacza to brak klucza API w pliku konfiguracyjnym `.env`.

Przy pierwszym uruchomieniu w trybie pełnej weryfikacji system automatycznie pobierze plik FEDIAF Nutritional Guidelines (~5 MB). Pobranie następuje jednorazowo — przy kolejnych uruchomieniach plik jest ładowany z dysku.

---

## 2. Szybki start

### Układ interfejsu

Interfejs BULT QA składa się z dwóch obszarów: **panelu bocznego** (sidebar) po lewej stronie oraz **obszaru głównego** po prawej.

#### Panel boczny (sidebar)

Panel boczny jest stale widoczny i zawiera następujące elementy od góry do dołu:

1. **Nagłówek "🐾 BULT QA"** — logo i nazwa aplikacji.

2. **Segmented control (przełącznik kategorii)** — trzy segmenty z etykietami:
   - "🔍 Weryfikacja" — tryby weryfikacyjne i kontrolne
   - "🔧 Narzędzia" — tryby generowania i konwersji
   - "🎨 Design" — analiza projektu graficznego

3. **Selectbox trybu** — rozwijana lista trybów dostępnych w wybranej kategorii:

   | Kategoria | Dostępne tryby |
   |-----------|---------------|
   | 🔍 Weryfikacja | "🔍 Pełna weryfikacja", "📝 Weryfikacja językowa", "🔤 Kontrola struktury i czcionki", "✓ Walidator claimów", "🏷️ Weryfikator nazw i zastrzeżeń", "🌍 Walidator rynkowy", "🔍 Inspekcja artwork" |
   | 🔧 Narzędzia | "🌐 Tłumaczenie etykiety", "📝 Generator tekstu etykiety", "📝 Generator opisów produktów", "🔄 Porównanie wersji", "📦 Walidator EAN/kodów" |
   | 🎨 Design | "🎨 Analiza projektu graficznego" (jedyny tryb w kategorii) |

4. **Opcje specyficzne dla trybu** — w zależności od wybranego trybu mogą pojawić się:
   - Selectbox "Rynek docelowy" (w trybie pełnej weryfikacji) — lista rynków: "— bez analizy trendów —", "Polska", "Niemcy", "Francja", "Wielka Brytania", "Czechy", "Węgry", "Rumunia", "Włochy", "Hiszpania"
   - Selectbox "Kraj" (w trybie walidatora rynkowego) — 14 krajów z kodami
   - Selectbox "Język docelowy" i pole "Dodatkowe uwagi" (w trybie tłumaczenia)
   - Radio "Tryb wprowadzania", selectbox "Styl opisu" i "Język opisu" (w generatorze opisów)

5. **Sekcja "📖 Podręcznik użytkownika"** — rozwijane sekcje pomocy:
   - "Jak zacząć?" — instrukcja krok po kroku dla aktywnego trybu
   - "Obsługiwane formaty plików" — tabela formatów z wskazówkami
   - "Co oznaczają sekcje raportu?" — objaśnienie struktury wyników
   - "Jak działa system?" — opis techniczny procesu analizy
   - "Kiedy konsultować z ekspertem?" — wytyczne eskalacji
   - "Słownik pojęć" — definicje terminów branżowych i technicznych
   - "FAQ" — najczęściej zadawane pytania

6. **Informacja o FEDIAF Guidelines** — status pliku PDF z wytycznymi (dotyczy trybu pełnej weryfikacji).

7. **Stopka "v1.0 · BULT Quality Assurance"** — wersja aplikacji.

#### Obszar główny (main area)

Obszar główny zajmuje około 75% szerokości ekranu i zawiera:

1. **Tytuł i podtytuł** — "🐾 BULT Quality Assurance" z opisem: "Weryfikacja etykiet, inspekcja artworków, kontrola claimów, spellcheck, tłumaczenia i generowanie tekstów — wszystko czego potrzebuje Twój produkt, zanim trafi na półkę."

2. **Pole uploadu pliku** — strefa przeciągania pliku ("Wgraj etykietę produktu") z obsługą formatów JPG, PNG, PDF, DOCX. W trybie artwork również TIFF. W trybach z dwoma plikami (porównanie wersji, porównanie artwork) wyświetlane są dwa pola uploadu obok siebie.

3. **Podgląd i informacje o pliku** — po wgraniu pliku wyświetlany jest podgląd (dla obrazów) lub ikona dokumentu (dla PDF/DOCX), nazwa pliku, rozmiar w KB, wybrany tryb i szacowany czas analizy.

4. **Przycisk akcji** — przycisk uruchamiający analizę. Etykieta przycisku zależy od trybu (np. "Sprawdź etykietę", "Sprawdź język", "Przetłumacz"). Przycisk jest wyróżniony kolorem (primary) i rozciągnięty na pełną szerokość.

5. **Raport wynikowy** — po zakończeniu analizy wyświetlany jest raport ze szczegółowymi wynikami, dostosowany do trybu.

6. **Przyciski pobierania** — możliwość pobrania raportu w formatach TXT, JSON, JSX lub HTML (w zależności od trybu).

---

### 2.1 Krok po kroku — pierwsza analiza

Poniższa instrukcja opisuje przeprowadzenie pełnej weryfikacji etykiety — najpopularniejszego trybu pracy.

**Krok 1. Upewnij się, że wybrany jest tryb "🔍 Pełna weryfikacja"**

W panelu bocznym sprawdź, czy segmented control jest ustawiony na "🔍 Weryfikacja", a w selectboxie trybu widnieje "🔍 Pełna weryfikacja". Jest to tryb domyślny po uruchomieniu aplikacji.

**Krok 2. Opcjonalnie wybierz rynek docelowy**

W panelu bocznym, w selectboxie "Rynek docelowy", możesz wybrać kraj, dla którego przeznaczona jest etykieta. System doda do raportu analizę trendów rynkowych dla tego kraju. Jeśli nie chcesz analizy trendów, pozostaw domyślną wartość "— bez analizy trendów —".

> Uwaga: wybranie rynku wydłuża analizę z 30–60 sekund do 60–90 sekund.

**Krok 3. Wgraj plik etykiety**

W obszarze głównym przeciągnij plik na pole uploadu lub kliknij "Browse files" i wybierz plik z dysku. Obsługiwane formaty: JPG, PNG, PDF, DOCX. Maksymalny rozmiar: 50 MB.

Alternatywnie: rozwiń sekcję "📷 Zrób zdjęcie lub wklej screenshot" i użyj kamery komputera.

**Krok 4. Sprawdź podgląd**

Po wgraniu pliku system wyświetli podgląd etykiety (dla obrazów) oraz informacje: nazwę pliku, rozmiar, wybrany rynek i szacowany czas analizy.

Upewnij się, że:
- Etykieta jest czytelna i kompletna (front i tył, jeśli to możliwe)
- Tabela analityczna (wartości odżywcze) jest widoczna i ostra
- Tekst na etykiecie nie jest obcięty ani zasłonięty

**Krok 5. Kliknij "Sprawdź etykietę"**

Kliknij przycisk "Sprawdź etykietę" na dole obszaru głównego. Rozpocznie się analiza. Na ekranie pojawi się spinner z komunikatem:
- "Analizuję etykietę względem FEDIAF... (ok. 30–60 sekund)" — bez trendów
- "Analizuję etykietę i sprawdzam trendy rynkowe... (ok. 60–90 sekund)" — z trendami

Nie zamykaj karty przeglądarki podczas analizy.

**Krok 6. Przejrzyj raport**

Po zakończeniu analizy raport pojawi się automatycznie poniżej przycisku. Przewiń w dół, aby zobaczyć wszystkie sekcje. Kluczowe elementy raportu:

- **Baner statusu** — kolorowy pasek: zielony (zgodny), żółty (do sprawdzenia), czerwony (niezgodny)
- **4 metryki** — Status, Wynik zgodności X/100, Pewność odczytu, Problemy
- **Pasek wyniku** — wizualizacja wyniku 0–100
- **Wyniki cross-check** — porównanie dwóch niezależnych odczytów
- **Weryfikacja językowa** — błędy ortograficzne, gramatyczne, diakrytyki
- **Reguły FEDIAF** — naruszenia progów żywieniowych
- **Dane produktu + 7 składników odżywczych** — białko, tłuszcz, włókno, wilgotność, popiół, wapń, fosfor
- **Problemy regulacyjne** — kwestie EU 767/2009
- **Checklista EU** — 6 obowiązkowych elementów etykiety
- **Kontrola opakowania** — ponad 30 punktów kontrolnych
- **Rekomendacje** — konkretne działania naprawcze
- **Trendy rynkowe** — jeśli wybrano rynek docelowy

**Krok 7. Pobierz raport**

Na dole raportu znajdują się przyciski pobierania:
- **JSON** — format maszynowy, do integracji z systemami jakości
- **TXT** — format tekstowy, do wydruku lub przekazania drogą e-mail

---

## 3. Kategoria "Weryfikacja" — 7 trybów

Kategoria "🔍 Weryfikacja" zawiera siedem trybów pracy, każdy dedykowany innemu aspektowi kontroli etykiety. Poniżej szczegółowy opis każdego z nich.

---

### 3.1 Pełna weryfikacja

**Tryb:** "🔍 Pełna weryfikacja"

#### 1. Przeznaczenie

Kompleksowa weryfikacja etykiety karmy dla zwierząt domowych obejmująca: ekstrakcję danych, analizę składu odżywczego vs FEDIAF, sprawdzenie wymagań EU 767/2009, kontrolę opakowania, walidację claimów, weryfikację krzyżową wartości liczbowych oraz analizę językową. Opcjonalnie dołączana jest analiza trendów rynkowych dla wybranego kraju.

#### 2. Korzyści

- Jednorazowa, kompletna kontrola etykiety w 30–90 sekund zamiast kilku godzin ręcznej pracy.
- Deterministyczny wynik (score 0–100) oparty na twardych regułach, nie subiektywnej ocenie.
- Weryfikacja krzyżowa eliminuje błędy odczytu AI — dwa niezależne odczyty wartości liczbowych.
- Automatyczna eskalacja przypadków granicznych do eksperta (human-in-the-loop).
- Pełna dokumentacja w formacie JSON, gotowa do archiwizacji w systemie jakości.

#### 3. Przypadki użycia — Marketing

- Weryfikacja nowego projektu etykiety przed przekazaniem do druku.
- Kontrola etykiety po zmianach graficznych — czy wszystkie obowiązkowe elementy pozostały na miejscu.
- Szybka ocena etykiety konkurencji (np. pod kątem claimów i regulacji).
- Przygotowanie etykiety do eksportu — sprawdzenie przed tłumaczeniem.

#### 4. Przypadki użycia — R&D

- Walidacja składu odżywczego nowej formulacji vs progi FEDIAF.
- Sprawdzenie spójności claimów ze składem (np. "70% mięsa", "bez zbóż").
- Kontrola stosunek Ca:P i zawartości tauryny (dla kotów).
- Przegląd kompletności etykiety przed audytem wewnętrznym.
- Generowanie dokumentacji compliance dla partii produkcyjnej.

#### 5. Dane wejściowe

| Element | Opis |
|---------|------|
| **Plik etykiety** | JPG, JPEG, PNG, PDF lub DOCX — przeciągnij na pole uploadu lub kliknij "Browse files" |
| **Rynek docelowy** | Opcjonalny selectbox w panelu bocznym: "— bez analizy trendów —", "Polska", "Niemcy", "Francja", "Wielka Brytania", "Czechy", "Węgry", "Rumunia", "Włochy", "Hiszpania" |
| **Maks. rozmiar** | 50 MB |

#### 6. Przebieg analizy

Po kliknięciu przycisku "Sprawdź etykietę" system wykonuje trzy kroki:

1. **Wywołanie 1 — Ekstrakcja** (AI): Odczytanie z obrazu etykiety wszystkich danych: nazwa produktu, marka, gatunek, etap życia, typ karmy, skład, wartości odżywcze (7 składników), claimy, elementy opakowania, języki.

2. **Analiza deterministyczna** (Python): Reguły FEDIAF (progi min/max dla białka, tłuszczu, włókna, wapnia, fosforu, Ca:P, tauryny), 6 wymagań EU 767/2009 (lista składników, składniki analityczne, producent, masa netto, gatunek, partia/data), ponad 30 punktów kontrolnych opakowania, spójność claimów ze składem.

3. **Wywołanie 2 — Cross-check + językowa** (AI): Niezależny, drugi odczyt wartości z tabeli analitycznej (tolerancja rozbieżności: 0,5%) oraz sprawdzenie ortografii, gramatyki, diakrytyków i terminologii.

#### 7. Raport wynikowy

| Sekcja raportu | Opis |
|---------------|------|
| **Baner statusu** | Kolorowy pasek: zielony = zgodny, żółty = do sprawdzenia, czerwony = niezgodny |
| **4 metryki** | Status, Wynik zgodności X/100, Pewność odczytu (HIGH/MEDIUM/LOW), Liczba problemów |
| **Pasek wyniku** | Wizualizacja score 0–100 z kolorowym wypełnieniem |
| **Wyniki cross-check** | Tabela porównania dwóch odczytów wartości odżywczych z zaznaczeniem rozbieżności |
| **Weryfikacja językowa** | Lista błędów: ortografia, gramatyka, interpunkcja, diakrytyki, terminologia |
| **Reguły FEDIAF** | Naruszenia progów żywieniowych z referencjami do tabeli FEDIAF |
| **Dane produktu** | Nazwa, marka, gatunek, etap życia, typ karmy, masa netto |
| **7 składników odżywczych** | Białko, tłuszcz, włókno, wilgotność, popiół, wapń, fosfor — wartości as-fed i DM |
| **Problemy regulacyjne** | Lista problemów z kodem, opisem i referencją prawną |
| **Checklista EU** | 6 obowiązkowych elementów: lista składników, składniki analityczne, producent, masa netto, gatunek, partia/data |
| **Kontrola opakowania** | Ponad 30 punktów: dawkowanie, przechowywanie, klasyfikacja, claimy vs skład, recykling, kody kreskowe, nr zakładu, GMO, surowość, owady, czcionka i inne |
| **Rekomendacje** | Lista konkretnych działań naprawczych |
| **Trendy rynkowe** | Analiza trendów i preferencji konsumentów na wybranym rynku (jeśli wybrano kraj) |

**Progi decyzyjne:**

| Wynik | Status | Kolor | Działanie |
|-------|--------|-------|-----------|
| ≥ 70 | COMPLIANT | Zielony | Etykieta zgodna — gotowa do dalszych kroków |
| 50–69 | REQUIRES_REVIEW | Żółty | Wymaga przeglądu — zalecana konsultacja z ekspertem |
| < 50 | NON_COMPLIANT | Czerwony | Niezgodna — wymaga korekty przed wprowadzeniem na rynek |

> Dodatkowo: wynik ≥ 85 wyświetla baner "automatyczna akceptacja", a wynik < 60 automatycznie flaguje raport do ręcznego przeglądu (progi UI z konfiguracji).

#### 8. Formaty eksportu

- **JSON** — pełna struktura danych, do integracji z systemami jakości
- **TXT** — czytelny raport tekstowy, do wydruku lub e-mail

#### 9. Czas przetwarzania

- **Bez trendów rynkowych:** 30–60 sekund
- **Z trendami rynkowymi:** 60–90 sekund

---

### 3.2 Weryfikacja językowa

**Tryb:** "📝 Weryfikacja językowa"

#### 1. Przeznaczenie

Szybka analiza jakości tekstu na etykiecie — wykrywanie błędów ortograficznych, gramatycznych, interpunkcyjnych, brakujących znaków diakrytycznych oraz niespójności terminologicznych. Tryb nie analizuje składu odżywczego ani zgodności regulacyjnej — skupia się wyłącznie na języku.

#### 2. Korzyści

- Szybka kontrola (10–20 sekund) — najszybszy tryb w systemie.
- Wykrywanie problemów niewidocznych gołym okiem (np. "a" zamiast "ą" w niewłaściwej czcionce).
- Podwójna walidacja: silnik Hunspell + AI — wyższe zaufanie do wyników.
- Celowany re-read (targeted re-read) — system ponownie odczytuje z obrazu konkretne słowa, w których podejrzewa błąd, eliminując fałszywe alarmy OCR.

#### 3. Przypadki użycia — Marketing

- Kontrola etykiety przed drukiem — ostatni sprawdzian tekstu.
- Weryfikacja po zmianach graficznych — czy grafik nie uszkodził tekstu.
- Szybkie sprawdzenie etykiety obcojęzycznej — czy diakrytyki są kompletne.
- Walidacja tekstu po konwersji czcionek.

#### 4. Przypadki użycia — R&D

- Sprawdzenie poprawności nazewnictwa składników w języku polskim.
- Kontrola spójności terminologii (np. czy nie mieszamy "białko" z "protein" w jednym bloku tekstowym).
- Weryfikacja tekstu regulacyjnego (instrukcja dawkowania, ostrzeżenia).

#### 5. Dane wejściowe

| Element | Opis |
|---------|------|
| **Plik etykiety** | JPG, JPEG, PNG, PDF lub DOCX |
| **Maks. rozmiar** | 50 MB |

Brak dodatkowych opcji w panelu bocznym — tryb nie wymaga konfiguracji.

#### 6. Przebieg analizy

Po kliknięciu przycisku "Sprawdź język" system wykonuje:

1. **Odczyt tekstu** (AI) — ekstrakcja wszystkich widocznych fragmentów tekstu z etykiety z automatycznym wykryciem języka.
2. **Weryfikacja Hunspell** — sprawdzenie ortografii za pomocą deterministycznego słownika Hunspell dla wykrytego języka.
3. **Weryfikacja AI** — niezależne sprawdzenie ortografii, gramatyki, interpunkcji, diakrytyków i terminologii przez model AI.
4. **Targeted re-read** — dla słów, w których wykryto potencjalny błąd, system ponownie odczytuje te konkretne fragmenty z obrazu etykiety, aby wyeliminować fałszywe alarmy wynikające z nieczytelności.
5. **Porównanie wyników** — przypisanie poziomu pewności na podstawie zgodności między Hunspell a AI.

**5 typów wykrywanych błędów:**

| Typ | Opis | Przykład |
|-----|------|---------|
| **Ortografia** | Literówki, błędne zapisy słów | "bialko" zamiast "białko" |
| **Gramatyka** | Błędna odmiana, składnia, końcówki | "dla psów dorosłego" |
| **Interpunkcja** | Brak/nadmiar przecinków, kropek | brak przecinka w liście składników |
| **Diakrytyki** | Brakujące ą, ę, ś, ć, ź, ż, ł, ń, ó | "zlozone" zamiast "złożone" |
| **Terminologia** | Mieszanie języków w jednym bloku | "białko" obok "protein" w sekcji PL |

**3 poziomy pewności:**

| Poziom | Warunek | Znaczenie |
|--------|---------|-----------|
| **HIGH** (wysoki) | AI i Hunspell zgodne co do błędu | Bardzo prawdopodobny rzeczywisty błąd |
| **MEDIUM** (średni) | Tylko AI zgłasza błąd | Prawdopodobny błąd, warto sprawdzić |
| **LOW** (niski) | AI i Hunspell się nie zgadzają | Może być fałszywy alarm — zweryfikuj ręcznie |

#### 7. Raport wynikowy

- **Jakość tekstu** — ocena ogólna: doskonała / dobra / do poprawy / słaba.
- **Lista błędów** — każdy błąd zawiera: oryginalny tekst, sugerowaną poprawkę, typ błędu, poziom pewności i krótkie wyjaśnienie.

#### 8. Formaty eksportu

- **TXT** — raport tekstowy z listą błędów i sugestii

#### 9. Czas przetwarzania

10–20 sekund.

---

### 3.3 Kontrola struktury i czcionki

**Tryb:** "🔤 Kontrola struktury i czcionki"

#### 1. Przeznaczenie

Analiza struktury wielojęzycznej etykiety — identyfikacja sekcji językowych, sprawdzenie markerów (flagi, kody krajów), porównanie kompletności między sekcjami oraz weryfikacja, czy użyta czcionka zawiera pełen komplet znaków diakrytycznych dla każdego wykrytego języka. Tryb szczególnie przydatny dla etykiet eksportowych z wieloma wersjami językowymi.

#### 2. Korzyści

- Wykrywanie brakujących glifów i problemów z czcionką przed drukiem — oszczędność kosztów dodruku.
- Generowanie skryptu `.jsx` dla Adobe Illustratora — adnotacje nakładane bezpośrednio na oryginalny plik `.ai`.
- Generowanie etykiety z naniesionymi oznaczeniami (annotated image) w formacie PDF lub PNG.
- Porównanie kompletności sekcji między językami — czy każdy język ma te same elementy.

#### 3. Przypadki użycia — Marketing

- Kontrola etykiety wielojęzycznej przed drukiem — czy każdy język ma marker, kompletny tekst i prawidłowe diakrytyki.
- Przekazanie skryptu `.jsx` grafikowi z precyzyjnymi oznaczeniami problemów.
- Weryfikacja po zmianie czcionki — czy nowa czcionka obsługuje wszystkie potrzebne znaki.

#### 4. Przypadki użycia — R&D

- Sprawdzenie kompletności etykiety dla nowego rynku eksportowego — czy dodana sekcja językowa jest pełna.
- Kontrola jakości po aktualizacji layoutu — czy żadna sekcja nie została uszkodzona.
- Weryfikacja diakrytyków czeskich, węgierskich, rumuńskich (częste problemy z czcionkami).

#### 5. Dane wejściowe

| Element | Opis |
|---------|------|
| **Plik etykiety** | JPG, JPEG, PNG lub PDF (najlepiej eksport z Illustratora) |
| **Maks. rozmiar** | 50 MB |

Brak dodatkowych opcji w panelu bocznym.

#### 6. Przebieg analizy

Po kliknięciu przycisku "Sprawdź strukturę" system wykonuje:

1. **Detekcja sekcji językowych** — identyfikacja każdej sekcji językowej na etykiecie (PL, DE, EN, FR, CZ, HU, RO itd.).
2. **Sprawdzenie markerów** — czy każda sekcja ma wizualne oznaczenie: flagę, kod kraju lub ikonę.
3. **Porównanie kompletności** — czy każda sekcja zawiera te same elementy (skład, składniki analityczne, dawkowanie, przechowywanie, producent, opis, ostrzeżenia). Brakujące elementy w porównaniu z innymi sekcjami są raportowane.
4. **Weryfikacja glifów** — dla każdego wykrytego języka system sprawdza, czy czcionka zawiera wymagane znaki diakrytyczne (np. PL: ą ę ś ć ź ż ł ń ó; DE: ä ö ü ß; CZ: ř š č ž ů ě).
5. **Lokalizacja problemów** — każdy wykryty problem jest oznaczany przybliżonymi współrzędnymi na obrazie etykiety.

**6 typów problemów z czcionką/glifami:**

| Typ | Opis | Jak wygląda |
|-----|------|-------------|
| **missing_glyph** | Brak glifa — znak nie renderuje się wcale | Puste miejsce w tekście |
| **substituted_glyph** | Podmieniony glif — znak z innej czcionki | Widocznie inny krój litery |
| **blank_space** | Luka gdzie powinien być znak | Podwójna spacja w środku słowa |
| **tofu_box** | Kwadracik zamiast znaku | □ lub ▯ w tekście |
| **wrong_diacritic** | Zły diakrytyk | "a" zamiast "ą" |
| **encoding_error** | Błąd enkodowania | "Ä…" zamiast "ą" |

**Walidacja diakrytyków per język:**

| Język | Wymagane znaki |
|-------|---------------|
| Polski (PL) | ą ę ś ć ź ż ł ń ó |
| Niemiecki (DE) | ä ö ü ß |
| Czeski (CZ) | ř š č ž ů ě |
| Węgierski (HU) | á é í ó ö ő ú ü ű |
| Rumuński (RO) | ă â î ș ț |
| Francuski (FR) | à â ç é è ê ë î ï ô ù û ü ÿ œ |
| Włoski (IT) | à è é ì ò ù |
| Hiszpański (ES) | á é í ó ú ñ ¿ ¡ |

#### 7. Raport wynikowy

- **Status ogólny** — OK / Ostrzeżenia / Błędy.
- **Lista sekcji językowych** — dla każdej sekcji: język, marker, obecne elementy, brakujące elementy.
- **Kompletność diakrytyków** — per język: status OK lub PROBLEM z listą brakujących znaków.
- **Problemy strukturalne** — z priorytetem: krytyczny (brak markera, brak sekcji), ostrzeżenie (osierocony tekst, luki, nakładanie się), informacja (niespójny porządek, duplikat markera).
- **Problemy z czcionką** — lista z typem, opisem, lokalizacją i dotkniętym tekstem.

#### 8. Formaty eksportu

- **TXT** — raport tekstowy ze wszystkimi wynikami
- **JSX** — skrypt Adobe Illustratora: otwórz etykietę w Illustratorze, następnie File > Scripts > Other Script > wybierz plik. System doda zablokowaną warstwę "QC Annotations" z kolorowymi oznaczeniami problemów.
- **Etykieta z oznaczeniami** — kopia PDF lub PNG z naniesionymi kolorowymi prostokątami oznaczającymi problemy (dostępna dla plików PDF i obrazów).

#### 9. Czas przetwarzania

15–30 sekund.

---

### 3.4 Walidator claimów

**Tryb:** "✓ Walidator claimów"

#### 1. Przeznaczenie

Analiza spójności claimów (oświadczeń marketingowych) na etykiecie z rzeczywistym składem produktu. System ekstrahuje z etykiety wszystkie claimy i listę składników z procentami, a następnie weryfikuje, czy deklaracje odpowiadają temu, co faktycznie zawiera produkt.

#### 2. Korzyści

- Wykrywanie niespójności przed kontrolą regulatora — np. claim "bez zbóż" przy kukurydzy w składzie.
- Automatyczna walidacja reguł procentowych EU 767/2009 w nazewnictwie.
- Identyfikacja zabronionych claimów terapeutycznych (Art. 13 EU 767/2009).
- Samo-weryfikacja (self-verify step) — AI weryfikuje własne wyniki, redukując fałszywe alarmy.

#### 3. Przypadki użycia — Marketing

- Weryfikacja nowych claimów przed umieszczeniem na etykiecie.
- Kontrola etykiet po aktualizacji formulacji — czy claimy nadal są prawdziwe.
- Sprawdzenie claimów na etykietach konkurencji.
- Przygotowanie argumentacji dla działu prawnego.

#### 4. Przypadki użycia — R&D

- Walidacja claimów procentowych po zmianie receptury (np. zmiana % mięsa).
- Sprawdzenie, czy claim "grain-free" jest uzasadniony po modyfikacji składu.
- Kontrola nazewnictwa produktu vs progi procentowe (Art. 17 EU 767/2009).
- Weryfikacja claimów odżywczych (np. "bogaty w białko") vs wartości analityczne.

#### 5. Dane wejściowe

| Element | Opis |
|---------|------|
| **Plik etykiety** | JPG, JPEG, PNG, PDF lub DOCX |
| **Maks. rozmiar** | 50 MB |

Brak dodatkowych opcji w panelu bocznym.

#### 6. Przebieg analizy

Po kliknięciu przycisku "Sprawdź claimy" system wykonuje:

1. **Ekstrakcja** (AI) — odczytanie z etykiety: listy claimów marketingowych, listy składników z procentami, nazwy produktu, typu karmy.
2. **Walidacja claimów** — każdy claim jest sprawdzany pod kątem spójności ze składem:
   - **Claimy procentowe** — czy deklarowany % odpowiada pozycji w składzie.
   - **Claimy "grain-free"** — czy w składzie nie ma zbóż (pszenica, żyto, jęczmień, owies, kukurydza, ryż, proso, sorgo).
   - **Claimy składnikowe** (ingredient_highlight) — czy wyróżniony składnik jest obecny.
   - **Claimy odżywcze** (nutritional) — czy claim odpowiada wartościom analitycznym.
   - **Reguła % w nazwie** (naming_rule) — EU 767/2009 Art. 17: "z X" wymaga min 4% składnika X, "bogaty w X" wymaga min 14%, X jako główna nazwa wymaga min 26%.
   - **Claimy terapeutyczne** — zabronione per Art. 13 EU 767/2009 (np. "leczy", "zapobiega", "leczniczy").
3. **Samo-weryfikacja** (self-verify) — AI weryfikuje własne wyniki, eliminując fałszywe alarmy.

#### 7. Raport wynikowy

- **Status spójności** — ogólna ocena: spójne / niespójności / krytyczne.
- **Lista claimów** — każdy claim z kategorią, statusem walidacji, wyjaśnieniem i referencją prawną.
- **Reguły procentowe** — szczegółowa walidacja nazewnictwa wg EU 767/2009.
- **Alerty** — wyróżnione problemy krytyczne (np. claim terapeutyczny, grain-free naruszony).

#### 8. Formaty eksportu

- **TXT** — raport tekstowy z pełną listą wyników

#### 9. Czas przetwarzania

15–30 sekund.

---

### 3.5 Weryfikator nazw i zastrzeżeń

**Tryb:** "🏷️ Weryfikator nazw i zastrzeżeń"

#### 1. Przeznaczenie

Kompleksowa analiza prezentacji handlowej produktu: weryfikacja receptur, nazewnictwa, elementów marki i potencjalnych naruszeń znaków towarowych. System sprawdza, czy sposób przedstawienia produktu na etykiecie jest zgodny z regulacjami EU 767/2009, EU 2018/848 (produkty ekologiczne), FEDIAF Code of Good Labelling Practice oraz regułami dotyczącymi znaków towarowych.

#### 2. Korzyści

- Cztery obszary analizy w jednym raporcie: receptury, nazwy, marka i zastrzeżenia.
- Wykrywanie potencjalnych naruszeń IP/trademark przed wprowadzeniem na rynek.
- Walidacja nazewnictwa wg pięciu progów procentowych EU 767/2009.
- Identyfikacja zabronionych terminów w nazwie marki (Bio, Vet, Medical, implikacje geograficzne).

#### 3. Przypadki użycia — Marketing

- Weryfikacja nazwy nowego produktu przed rejestracją.
- Kontrola, czy elementy marki nie naruszają regulacji (np. "Natural" w nazwie).
- Sprawdzenie ryzyka zbieżności z markami konkurencji.
- Przygotowanie briefu dla działu prawnego z listą potencjalnych problemów.

#### 4. Przypadki użycia — R&D

- Walidacja claimów o recepturze (oryginalna, monobiałkowa, vet-developed, bez konserwantów) vs rzeczywisty skład.
- Sprawdzenie klasyfikacji produktu (pełnoporcjowa/uzupełniająca) vs claimy na etykiecie.
- Weryfikacja reguł procentowych w nazwie po zmianie formulacji.

#### 5. Dane wejściowe

| Element | Opis |
|---------|------|
| **Plik etykiety** | JPG, JPEG, PNG, PDF lub DOCX |
| **Maks. rozmiar** | 50 MB |

Brak dodatkowych opcji w panelu bocznym.

#### 6. Przebieg analizy

Po kliknięciu przycisku "Sprawdź prezentację handlową" system wykonuje:

1. **Ekstrakcja** (AI) — odczytanie z etykiety: nazwy produktu, elementów marki, claimów, składu, dodatków, oznaczeń ® i ™.
2. **Analiza 4 sekcji:**
   - **Receptury (waga: 25%)** — czy claimy o recepturze (oryginalna, monobiałkowa, vet-developed, bez konserwantów, bez GMO) są uzasadnione składem i regulacjami.
   - **Nazwy (waga: 30%)** — pełna walidacja reguł procentowych EU 767/2009 Art. 17 (5 progów: 100%/26%/14%/4%/<4%) + spójność nazwy z typem karmy, gatunkiem i etapem życia.
   - **Marka (waga: 25%)** — czy elementy marki nie naruszają regulacji: "Bio"/"Organic" bez certyfikatu (EU 2018/848), "Vet"/"Clinical" bez klasyfikacji dietetycznej, "Natural" niezgodne z FEDIAF CoGLP, "Medical"/"Leczniczy" (zabronione per Art. 13), implikacje geograficzne.
   - **Zastrzeżenia (waga: 20%)** — analiza IP/trademark: poprawność symboli ® i ™, zbieżność z markami konkurencji w branży pet food, potencjalne naruszenia znaków towarowych.
3. **Samo-weryfikacja** (AI) — redukcja fałszywych alarmów.
4. **Obliczenie wyniku ogólnego** — średnia ważona 4 sekcji: receptury 25%, nazwy 30%, marka 25%, zastrzeżenia 20%.

#### 7. Raport wynikowy

- **Wynik ogólny** — score 0–100, średnia ważona 4 sekcji.
- **Sekcja Receptury** — ocena 0–100, claimy o recepturze, problemy, rekomendacje.
- **Sekcja Nazwy** — ocena 0–100, walidacja reguł %, spójność nazwy.
- **Sekcja Marka** — ocena 0–100, compliance brandu, terminy zabronione.
- **Sekcja Zastrzeżenia** — ocena 0–100, analiza IP/trademark, symbole ® i ™.

#### 8. Formaty eksportu

- **TXT** — raport tekstowy z pełną analizą 4 sekcji

#### 9. Czas przetwarzania

20–40 sekund.

---

### 3.6 Walidator rynkowy

**Tryb:** "🌍 Walidator rynkowy"

#### 1. Przeznaczenie

Weryfikacja etykiety pod kątem wymogów regulacyjnych specyficznych dla wybranego rynku docelowego. System sprawdza, czy etykieta spełnia krajowe wymagania dotyczące języka, oznakowania, claimów, przepisów prawnych i opakowania, wykraczające poza ogólnounijne rozporządzenie EU 767/2009.

#### 2. Korzyści

- Kontrola przed eksportem — upewnienie się, że etykieta spełnia wymogi docelowego kraju.
- Pokrycie 14 rynków europejskich z krajowymi regulacjami.
- Identyfikacja wymogów, o których łatwo zapomnieć (np. Triman we Francji, UKCA w Wielkiej Brytanii, NEBIH na Węgrzech).
- Unikanie kosztownych poprawek po wysyłce towaru.

#### 3. Przypadki użycia — Marketing

- Weryfikacja etykiety przed wprowadzeniem produktu na nowy rynek.
- Kontrola wielojęzycznej etykiety dla wielu krajów — oddzielna analiza per rynek.
- Sprawdzenie, czy claimy marketingowe są dopuszczalne w danym kraju.

#### 4. Przypadki użycia — R&D

- Przegląd wymogów dotyczących oznakowania (wielkość czcionki, symbole, numery rejestracyjne).
- Weryfikacja, czy certyfikaty bio/eco spełniają wymogi danego kraju (np. DE-ÖKO-XXX, FR-BIO-XX, IT-BIO-XXX).
- Sprawdzenie wymogów dotyczących danych importera dla rynków wymagających lokalnego adresu.

#### 5. Dane wejściowe

| Element | Opis |
|---------|------|
| **Plik etykiety** | JPG, JPEG, PNG, PDF lub DOCX |
| **Rynek docelowy** | Selectbox "Kraj" w panelu bocznym — 14 krajów |
| **Maks. rozmiar** | 50 MB |

**Dostępne rynki (14 krajów):**

| Kod | Kraj | Język wymagany |
|-----|------|---------------|
| DE | Niemcy | Niemiecki |
| FR | Francja | Francuski |
| CZ | Czechy | Czeski |
| HU | Węgry | Węgierski |
| RO | Rumunia | Rumuński |
| IT | Włochy | Włoski |
| ES | Hiszpania | Hiszpański |
| UK | Wielka Brytania | Angielski |
| NL | Holandia | Niderlandzki |
| SK | Słowacja | Słowacki |
| BG | Bułgaria | Bułgarski |
| HR | Chorwacja | Chorwacki |
| PT | Portugalia | Portugalski |
| PL | Polska | Polski |

#### 6. Przebieg analizy

Po kliknięciu przycisku "Sprawdź zgodność rynkową" system wykonuje:

1. **Ekstrakcja** (AI) — odczytanie z etykiety elementów istotnych dla danego rynku: język, oznakowanie, claimy, dane producenta/importera, symbole, certyfikaty.
2. **Walidacja wymogów krajowych** — sprawdzenie etykiety vs baza reguł dla wybranego kraju, pogrupowanych w 5 kategorii:
   - **language** — czy etykieta jest w wymaganym języku krajowym.
   - **labeling** — wymogi dotyczące oznakowania (czcionka, diakrytyki, numery partii, symbole).
   - **claims** — czy claimy spełniają krajowe wymogi (certyfikaty bio, claimy zdrowotne).
   - **legal** — wymogi prawne (numer rejestracyjny krajowy, dane importera, podmiot odpowiedzialny).
   - **packaging** — wymogi dotyczące opakowania (symbole recyklingu, oznaczenia materiałowe).

#### 7. Raport wynikowy

- **Status ogólny** — ocena zgodności z wymogami wybranego kraju.
- **Lista wymogów** — każdy wymóg z kategorią, opisem, statusem (spełniony / niespełniony / do weryfikacji) i referencją prawną.
- **Rekomendacje** — konkretne działania dostosowawcze.

#### 8. Formaty eksportu

- **TXT** — raport tekstowy z pełną listą wymogów

#### 9. Czas przetwarzania

20–40 sekund.

---

### 3.7 Inspekcja artwork

**Tryb:** "🔍 Inspekcja artwork"

#### 1. Przeznaczenie

Techniczna inspekcja pliku graficznego etykiety pod kątem gotowości do druku. Tryb łączy deterministyczne analizy (pixel diff, analiza kolorów, sprawdzenie DPI/CMYK) z opcjonalnym podsumowaniem AI. Dostępne dwa podtryby: analiza pojedynczego pliku (print readiness) lub porównanie dwóch plików (master vs proof).

#### 2. Korzyści

- Deterministyczne wyniki (SSIM, Delta E, DPI) — nie opinia AI, lecz pomiar techniczny.
- Porównanie pixel-by-pixel master vs proof — wykrywanie zmian niewidocznych gołym okiem.
- Obsługa formatów drukarskich (TIFF) — brak konieczności konwersji.
- Regulowany suwak czułości — dostosowanie do typu projektu (od 5 do 100, domyślnie 30).
- Analiza palety kolorów (K-means) z obliczeniem różnic kolorystycznych (Delta E CIE2000).

#### 3. Przypadki użycia — Marketing

- Porównanie proofa z drukarni z zatwierdzonym masterem — wykrycie nieautoryzowanych zmian.
- Kontrola wersji — czy nowa iteracja projektu nie zawiera niezamierzonych modyfikacji.
- Weryfikacja kolorów przed drukiem — czy paleta odpowiada identyfikacji wizualnej.

#### 4. Przypadki użycia — R&D

- Sprawdzenie gotowości pliku do druku: DPI ≥ 300, przestrzeń kolorów CMYK, bleed.
- Kontrola profilu ICC — zgodność z wymogami drukarni.
- Weryfikacja OCR — opcjonalne sprawdzenie czytelności tekstu na artwork.
- Analiza saliency — opcjonalne sprawdzenie, które elementy etykiety przyciągają wzrok.

#### 5. Dane wejściowe

| Element | Opis |
|---------|------|
| **Plik artwork** | JPG, JPEG, PNG, PDF, TIFF lub TIF |
| **Tryb inspekcji** | Radio: "Pojedynczy plik (print readiness + kolory)" lub "Porównanie: master vs proof (pixel diff + kolory + print)" |
| **Czułość detekcji** | Suwak "Czułość detekcji zmian (pixel threshold)": 5–100, domyślnie 30. Niższa wartość = większa czułość na drobne różnice |
| **Maks. rozmiar** | 50 MB per plik |

W trybie "Porównanie" wyświetlane są dwa pola uploadu obok siebie:
- "Master (referencja)" — zatwierdzony artwork master
- "Proof (do sprawdzenia)" — proof do porównania z masterem

#### 6. Przebieg analizy

Po kliknięciu przycisku "Inspekcja artwork" system wykonuje (w zależności od podtrybu):

**Tryb "Pojedynczy plik":**
1. **Print readiness** — sprawdzenie DPI (minimum 300 dla druku), przestrzeni kolorów (CMYK preferowany), obecności bleeda, statusu fontów.
2. **Analiza kolorów** — ekstrakcja palety kolorów algorytmem K-means, obliczenie dominujących barw.
3. **Profil ICC** — sprawdzenie osadzonego profilu kolorów.
4. **OCR** (opcjonalne) — odczyt tekstu z artwork i weryfikacja czytelności.
5. **Saliency** (opcjonalne) — mapa uwagi wizualnej — które elementy etykiety przyciągają wzrok.
6. **Podsumowanie AI** — interpretacja wyników deterministycznych w przystępnej formie.

**Tryb "Porównanie: master vs proof":**
1. **Pixel diff** — porównanie pixel-by-pixel z obliczeniem SSIM (Structural Similarity Index) i generacją mapy różnic.
2. **Analiza kolorów** — porównanie palet kolorów obu plików z obliczeniem Delta E CIE2000 dla każdej pary kolorów.
3. **Print readiness** — sprawdzenie obu plików pod kątem DPI, CMYK, bleed.
4. **OCR** (opcjonalne) — porównanie tekstu między masterem a proofem.
5. **Profil ICC** — porównanie profili kolorów.
6. **Podsumowanie AI** — interpretacja różnic i rekomendacje.

**Deterministyczne analizy (bez udziału AI):**

| Analiza | Metoda | Opis |
|---------|--------|------|
| Pixel diff | SSIM (Structural Similarity Index) | Porównanie strukturalne dwóch obrazów — wartość 1.0 = identyczne |
| Kolory | K-means + Delta E CIE2000 | Ekstrakcja palety + perceptualna różnica kolorystyczna |
| Print readiness | Analiza metadanych | DPI ≥ 300, przestrzeń CMYK, obecność bleed |
| OCR | Opcjonalne | Odczyt tekstu z obrazu |
| Profil ICC | Analiza metadanych | Sprawdzenie osadzonego profilu kolorów |
| Saliency | Opcjonalne | Mapa uwagi wizualnej |

#### 7. Raport wynikowy

- **Gotowość do druku** — status DPI, przestrzeni kolorów, fontów, bleed.
- **Paleta kolorów** — dominujące kolory z wartościami.
- **Pixel diff** (tylko w trybie porównania) — wartość SSIM + mapa różnic z wizualizacją.
- **Delta E** (tylko w trybie porównania) — różnice kolorystyczne między masterem a proofem.
- **Profil ICC** — informacje o osadzonym profilu.
- **Podsumowanie AI** — przystępna interpretacja wyników technicznych.

#### 8. Formaty eksportu

- **TXT** — raport tekstowy z wynikami inspekcji
- **JSON** — pełna struktura danych ze wszystkimi pomiarami

#### 9. Czas przetwarzania

10–30 sekund (w zależności od rozmiaru pliku i liczby analiz).

---

## 4. Kategoria "Narzędzia" -- 5 trybów

Kategoria **"Narzędzia"** grupuje tryby generatywne i porównawcze, które nie oceniają zgodnosci regulacyjnej, lecz **tworzą nowe treści** lub **porównują wersje**. Dostep do kategorii: panel boczny > przycisk segmentowy "Narzędzia".

Kazdy tryb opisany jest według jednolitego szablonu:

| Element szablonu | Opis |
|------------------|------|
| Przeznaczenie | Do czego służy tryb |
| Korzyści | Co zyskuje użytkownik |
| Przypadki użycia | Scenariusze dla Marketingu i R&D |
| Dane wejsciowe | Co należy dostarczyć |
| Przebieg analizy | Kroki wykonywane przez system |
| Raport wynikowy | Struktura wyniku |
| Formaty eksportu | Dostepne pliki do pobrania |
| Czas przetwarzania | Orientacyjny czas oczekiwania |

---

### 4.1 Tłumaczenie etykiety

**Przycisk:** "Przetłumacz"
**Czas przetwarzania:** 20--40 sekund

#### Przeznaczenie

Tryb tłumaczenia generuje pełne tłumaczenie etykiety karmy na jeden z 14 języków docelowych, zachowując oficjalna terminologię regulacyjna EU 767/2009. Tłumaczenie obejmuje wszystkie sekcje etykiety: skład, składniki analityczne, dawkowanie, producenta, claimy i ostrzeżenia.

#### Korzyści

- Eliminacja ręcznego tłumaczenia sekcji regulacyjnych -- terminy takie jak "składniki analityczne", "karma pełnoporcjowa" czy "dodatki" sa tlumaczone zgodnie z oficjalnym słownictwem EU.
- Uwagi tłumacza przy każdej sekcji -- system sygnalizuje niejednoznaczności, alternatywne tłumaczenia i różnice między rynkami.
- Dwa tryby wejscia -- można wgrać plik (obraz/PDF) lub wkleić tekst, co pozwala tłumaczyć zarówno z gotowej etykiety, jak i z roboczego dokumentu.

#### Przypadki użycia

| Marketing | R&D |
|-----------|-----|
| Przygotowanie etykiety na nowy rynek eksportowy | Weryfikacja poprawności terminów w tłumaczeniu dostawcy |
| Szybkie tłumaczenie treści marketingowych etykiety | Porównanie terminologii między wersjami jezykowymi |
| Tłumaczenie claimów funkcjonalnych z zachowaniem kontekstu regulacyjnego | Przygotowanie brudnopisu etykiety wielojezycznej |

#### Dane wejsciowe

System akceptuje dane w dwoch trybach -- użytkownik wybiera jeden:

1. **Upload pliku** -- obraz JPG/PNG lub dokument PDF etykiety. System odczytuje tresc za pomoca AI (OCR wizyjny).
2. **Wklejenie tekstu** -- pole tekstowe "Lub wklej/wpisz tekst etykiety" (maksymalnie 2000 znaków). Uzywane, gdy etykieta jest dostepna tylko w formie tekstowej.

> Jeżeli użytkownik wgra plik i jednocześnie wpisze tekst, plik ma priorytet -- tekst zostanie zignorowany. System wyświetli stosowne ostrzezenie.

Dodatkowe parametry (panel boczny):

- **Język docelowy** -- lista rozwijana z 14 językami: English (en), Deutsch (de), Francais (fr), Cestina (cs), Magyar (hu), Romana (ro), Italiano (it), Espanol (es), Nederlands (nl), Slovencina (sk), Bulgarski (bg), Hrvatski (hr), Portugues (pt), Polski (pl).
- **Dodatkowe uwagi** -- pole tekstowe (maksymalnie 500 znaków) na instrukcje dla AI, np. "uzywaj terminologii weterynaryjnej", "zachowaj styl formalny", "stosuj nazwy lacinskie składników".

#### Przebieg analizy

1. System przyjmuje obraz etykiety lub wklejony tekst.
2. Automatycznie wykrywa język źródłowy.
3. Dzieli tresc na logiczne sekcje etykiety (skład, składniki analityczne, dawkowanie, producent, claimy, ostrzeżenia).
4. Tlumaczy każda sekcje na wybrany język docelowy, stosujac oficjalne tłumaczenia terminów regulacyjnych EU 767/2009.
5. Uwzglednia dodatkowe uwagi użytkownika (np. styl, terminologia).
6. Generuje uwagi tłumacza dla sekcji, w których wystepuja niejednoznaczności.

Caly proces realizowany jest w ramach jednego wywolania AI.

#### Raport wynikowy

Raport zawiera:

- **Język źródłowy** -- automatycznie wykryty (np. "polski").
- **Język docelowy** -- wybrany przez użytkownika.
- **Sekcje tłumaczenia** -- każda sekcja etykiety wyswietlana w układzie: oryginal | tłumaczenie.
- **Uwagi tłumacza** -- pod każda sekcja mogą pojawic sie uwagi dotyczace alternatywnych tlumaczen, niejednoznaczności terminologicznych lub roznic między rynkami.
- **Uwagi ogólne** -- obserwacje dotyczace calej etykiety.
- **Podsumowanie** -- krótkie streszczenie tłumaczenia.

#### Formaty eksportu

| Format | Opis |
|--------|------|
| **TXT** | Raport tekstowy z tlumaczeniem sekcja po sekcji -- do przekazania grafikowi lub korektorowi |

#### Czas przetwarzania

20--40 sekund. Czas zależy od długości tekstu etykiety i obciążenia API.

---

### 4.2 Generator tekstu etykiety

**Przycisk:** "Generuj tekst etykiety"
**Czas przetwarzania:** 20--40 sekund

#### Przeznaczenie

Tryb generuje pełny tekst regulacyjny etykiety karmy na podstawie danych wprowadzonych w formularzu. Wynik obejmuje wszystkie wymagane sekcje etykiety wraz z odniesieniami do regulacji, tabela dawkowania i ostrzezeniami. Jest to narzędzie do tworzenia pierwszej wersji tekstu etykiety ("brudnopisu"), który następnie weryfikuje technolog lub dział jakości.

#### Korzyści

- Pelny tekst etykiety w wybranym jezyku -- gotowy do przekazania grafikowi.
- Automatyczne odniesienia regulacyjne (EU 767/2009) przy każdej sekcji.
- Tabela dawkowania dostosowana do gatunku, etapu zycia i typu karmy.
- Ostrzezenia generowane kontekstowo -- np. dla karm mokrych, kociat, seniorow.

#### Przypadki użycia

| Marketing | R&D |
|-----------|-----|
| Szybkie przygotowanie tekstu etykiety dla nowego produktu | Generowanie tekstu referencyjnego do porównania z istniejaca etykieta |
| Tworzenie wersji jezykowych etykiety z jednego zestawu danych | Weryfikacja kompletnosci sekcji regulacyjnych |
| Przygotowanie tekstu na targi lub materialy promocyjne | Tworzenie szablonow etykiet dla linii produktowej |

#### Dane wejsciowe

Tryb nie używa uploadu pliku -- wszystkie dane wprowadzane sa przez formularz:

| Pole | Typ | Opcje / Opis |
|------|-----|-------------|
| Gatunek | Lista rozwijana | Pies / Kot |
| Etap zycia | Lista rozwijana | Dorosły / Szczenię / Kocie / Senior / Wszystkie etapy |
| Typ karmy | Lista rozwijana | Sucha / Mokra / Półwilgotna / Przysmak |
| Język etykiety | Lista rozwijana | 14 języków (English, Deutsch, Francais, Cestina, Magyar, Romana, Italiano, Espanol, Nederlands, Slovencina, Bulgarski, Hrvatski, Portugues, Polski) |
| Nazwa produktu | Pole tekstowe | np. "Premium Adult Dog Chicken & Rice" |
| Składniki | Pole tekstowe (obszar) | Lista składu, np. "mieso z kurczaka (30%), ryz (20%), tłuszcz drobiowy..." |
| Białko (%) | Pole numeryczne | Wartość 0.0--100.0, krok 0.1 |
| Tłuszcz (%) | Pole numeryczne | Wartość 0.0--100.0, krok 0.1 |
| Włókno (%) | Pole numeryczne | Wartość 0.0--100.0, krok 0.1 |
| Wilgotność (%) | Pole numeryczne | Wartość 0.0--100.0, krok 0.1 |
| Popiół (%) | Pole numeryczne | Wartość 0.0--100.0, krok 0.1 |
| Wapń (%) | Pole numeryczne | Wartość 0.0--100.0, krok 0.01 |
| Fosfor (%) | Pole numeryczne | Wartość 0.0--100.0, krok 0.01 |

Przycisk "Generuj tekst etykiety" staje sie aktywny dopiero po wpisaniu składników.

#### Przebieg analizy

1. System zbiera dane z formularza.
2. Na podstawie gatunku, etapu zycia i typu karmy dobiera wymagania regulacyjne.
3. Generuje pełny tekst etykiety w wybranym jezyku, podzielony na sekcje.
4. Kazda sekcja opatrzona jest odniesieniem do odpowiedniego artykulu regulacji (np. "EU 767/2009 Art.17").
5. System generuje tabele dawkowania dostosowana do parametrow produktu.
6. Dodaje kontekstowe ostrzeżenia (np. "Zapewnic staly dostep do świeżej wody").

#### Raport wynikowy

Raport zawiera:

- **Informacje o produkcie** -- nazwa, gatunek, etap zycia, typ karmy, język.
- **Sekcje tekstu etykiety** -- każda sekcja z nagłówkiem w wybranym jezyku, treścią, odniesieniem regulacyjnym i ewentualnymi uwagami.
- **Tabela dawkowania** -- wiersze z zakresem masy ciała zwierzęcia i rekomendowana dzienna porcją.
- **Ostrzezenia** -- lista ostrzeżeń kontekstowych.
- **Pelny tekst** -- wszystkie sekcje połączone w gotowy tekst etykiety.
- **Podsumowanie** -- krótki opis wygenerowanego tekstu.

#### Formaty eksportu

| Format | Opis |
|--------|------|
| **TXT** | Pełny tekst etykiety gotowy do przekazania grafikowi |
| **JSX** | Skrypt Adobe Illustrator — tworzy ramki tekstowe z wygenerowanymi sekcjami etykiety, gotowe do umieszczenia w layoucie |

#### Czas przetwarzania

20--40 sekund.

---

### 4.3 Generator opisów produktów

**Przyciski:** "Generuj opis produktu" (tryb ręczny) / "Generuj opis produktu z etykiety" (tryb z obrazu)
**Czas przetwarzania:** 30--60 sekund

#### Przeznaczenie

Tryb generuje opis produktu do wykorzystania w e-commerce, na stronie internetowej lub w materiałach marketingowych. Opis obejmuje headline, krótki opis, bullet points, pełny opis w sekcjach, metadane SEO oraz wersje HTML. System automatycznie weryfikuje uzyte claimy marketingowe i sygnalizuje potencjalne naruszenia regulacyjne.

#### Korzyści

- Pelny opis produktu w 4 stylach tonalnych -- od luksusowego po neutralny.
- Gotowe metadane SEO: tytuł (do 60 znaków), meta description (do 160 znaków), słowa kluczowe i focus keyword.
- Automatyczna walidacja claimów -- system ostrzega przed claimami zabronionymi, nieudokumentowanymi lub naruszającymi reguły nazewnictwa.
- Wersja HTML gotowa do wklejenia na strone e-commerce.
- Dwa tryby wprowadzania danych -- ręczny (formularz) lub automatyczny (z obrazu etykiety).

#### Przypadki użycia

| Marketing | R&D |
|-----------|-----|
| Tworzenie opisów produktów do sklepow internetowych | Weryfikacja, czy opis nie zawiera zabronionych claimów |
| Przygotowanie treści SEO pod pozycjonowanie | Generowanie opisów w różnych tonach do testow A/B |
| Szybkie tworzenie opisów dla calej linii produktowej | Sprawdzenie spójności claimów między etykieta a opisem online |

#### Dane wejsciowe

System oferuje dwa tryby wprowadzania danych, wybierane w panelu bocznym:

**Tryb 1: Ręczne dane (formularz)**

| Pole | Typ | Opis |
|------|-----|------|
| Gatunek | Lista rozwijana | Pies / Kot |
| Etap zycia | Lista rozwijana | Dorosły / Szczenię / Kocie / Senior / Wszystkie etapy |
| Typ karmy | Lista rozwijana | Sucha / Mokra / Półwilgotna / Przysmak |
| Nazwa produktu | Pole tekstowe | Nazwa handlowa produktu |
| Marka | Pole tekstowe | Nazwa marki (np. "BULT Nutrition") |
| Składniki | Pole tekstowe (obszar) | Lista składu z procentami |
| Unikalne cechy produktu (USP) | Pole tekstowe (obszar) | np. "receptura opracowana z weterynarzami, składniki z lokalnych farm" |
| Składniki analityczne | 7 pol numerycznych | Białko, Tłuszcz, Włókno, Wilgotność, Popiół, Wapń, Fosfor |

**Tryb 2: Z etykiety (obraz/PDF)**

Uzytkownik wgrywa obraz lub PDF etykiety. System automatycznie ekstrahuje dane produktu i generuje opis na ich podstawie.

**Wspolne parametry (panel boczny):**

- **Styl opisu** -- lista rozwijana z 4 opcjami:
  - "Premium / Luksusowy" -- język ekskluzywny, podkreslenie jakości premium
  - "Naukowy / Weterynaryjny" -- terminologia specjalistyczna, dane naukowe
  - "Naturalny / Wholesome" -- akcent na naturalnosc, pochodzenie składników
  - "Standardowy / Neutralny" -- rzeczowy, informacyjny ton
- **Język opisu** -- 14 języków docelowych (identyczna lista jak w trybie tłumaczenia).

#### Przebieg analizy

1. System zbiera dane z formularza lub ekstrahuje je z obrazu etykiety.
2. Na podstawie wybranego stylu (tonu) generuje opis produktu.
3. Tworzy headline (1 zdanie), krótki opis (2--3 zdania), bullet points (5--7 punktow) i pełne sekcje opisowe.
4. Generuje metadane SEO: meta_title (do 60 znaków), meta_description (do 160 znaków), 5--10 slow kluczowych i focus keyword.
5. Automatycznie skanuje wygenerowany tekst pod katem claimów marketingowych.
6. Dla każdego problematycznego claimu generuje ostrzezenie z kategoryzacja (zabroniony terapeutyczny, nieudokumentowany, naruszenie reguły nazewnictwa, wymaga dowodow) i rekomendacja alternatywy.
7. Generuje wersje HTML i plain text.

#### Raport wynikowy

Raport zawiera:

- **Headline** -- 1-zdaniowe pozycjonowanie produktu.
- **Krotki opis** -- 2--3 zdania do karty produktu / listingu.
- **Bullet points** -- 5--7 kluczowych zalet produktu.
- **Sekcje opisowe** -- rozbudowane sekcje (np. historia składników, korzyści żywieniowe, dla kogo).
- **Metadane SEO:**
  - `meta_title` -- do 60 znaków
  - `meta_description` -- do 160 znaków
  - `keywords` -- 5--10 slow kluczowych
  - `focus_keyword` -- glowne slowo kluczowe
- **Uzyte claimy** -- lista claimów marketingowych zawartych w opisie.
- **Ostrzezenia o claimach** -- lista ostrzeżeń z typem problemu, wyjasnieniem i rekomendacja.
- **Pelny tekst** -- caly opis w formacie plain text.
- **Pelny HTML** -- caly opis w formacie HTML gotowym do wklejenia.

#### Formaty eksportu

| Format | Opis |
|--------|------|
| **TXT** | Opis w formacie tekstowym |
| **HTML** | Opis w formacie HTML gotowym do wklejenia na strone |
| **JSON** | Ustrukturyzowane dane (sekcje, SEO, claimy) do integracji z systemem CMS |

#### Czas przetwarzania

30--60 sekund. Tryb z obrazu moze byc nieznacznie dłuższy niz tryb ręczny ze wzgledu na ekstrakcje danych.

---

### 4.4 Porównanie wersji

**Przycisk:** "Porownaj wersje"
**Czas przetwarzania:** 20--40 sekund

#### Przeznaczenie

Tryb porównuje dwie wersje etykiety (stara i nowa) i generuje szczegolowy raport roznic. Identyfikuje zmiany tekstowe (dodane, usuniete, zmodyfikowane, przeniesione elementy) wraz z ocena ich wplywu regulacyjnego, zmiany layoutu oraz nowe problemy wprowadzone przez modyfikacje. Kazda zmiana opatrzona jest poziomem ryzyka.

#### Korzyści

- Automatyczne wykrywanie wszystkich roznic między wersjami -- bez ręcznego porownywania tekstu.
- Ocena wplywu regulacyjnego każdej zmiany -- np. czy zmiana w skladzie wpływa na zgodnosc z EU 767/2009.
- Identyfikacja nowych problemow wprowadzonych przez zmiany.
- Podsumowanie z poziomem ryzyka (niski / sredni / wysoki) -- szybka decyzja, czy nowa wersja wymaga dodatkowej weryfikacji.

#### Przypadki użycia

| Marketing | R&D |
|-----------|-----|
| Weryfikacja, czy redesign nie zmienil informacji regulacyjnych | Porównanie wersji po korekcie składu |
| Sprawdzenie, czy nowa wersja jezykowa jest kompletna | Weryfikacja poprawek po audycie jakości |
| Kontrola zmian przed zatwierdzeniem do druku | Sledzenie ewolucji etykiety między rewizjami |

#### Dane wejsciowe

System wymaga dwoch plikow, wgrywanych obok siebie w układzie dwukolumnowym:

- **"Stara wersja etykiety"** -- plik JPG, PNG, PDF lub DOCX z poprzednia wersja.
- **"Nowa wersja etykiety"** -- plik JPG, PNG, PDF lub DOCX z nowa wersja.

Przycisk "Porownaj wersje" staje sie aktywny dopiero po wgraniu obu plikow.

#### Przebieg analizy

1. System konwertuje oba pliki do formatu analizowalnego przez AI.
2. Odczytuje i porównuje tresc obu etykiet sekcja po sekcji.
3. Klasyfikuje każda zmiane według typu:
   - **added** -- nowy element, którego nie bylo w starej wersji
   - **removed** -- element usuniety z nowej wersji
   - **modified** -- element zmieniony (z pokazaniem starego i nowego tekstu)
   - **moved** -- element przeniesiony w inne miejsce
4. Ocenia wpływ regulacyjny każdej zmiany tekstowej.
5. Identyfikuje zmiany layoutu (układ, rozmieszczenie elementow).
6. Wykrywa nowe problemy wprowadzone przez zmiany.
7. Identyfikuje problemy rozwiazane (obecne w starej wersji, nieobecne w nowej).
8. Oblicza ogolny poziom ryzyka.

#### Raport wynikowy

Raport zawiera:

- **Podsumowanie starej wersji** -- krótki opis etykiety bazowej.
- **Podsumowanie nowej wersji** -- krótki opis nowej etykiety.
- **Zmiany tekstowe** -- lista zmian z polami:
  - Sekcja (np. "ingredients", "analytical_constituents", "claims")
  - Typ zmiany (added / removed / modified / moved)
  - Stary tekst / nowy tekst
  - Waznosc (critical / warning / info)
  - Wplyw regulacyjny
- **Zmiany layoutu** -- zmiany wizualne/ukladowe z opisem, obszarem i waznoscia.
- **Nowe problemy** -- problemy wprowadzone przez zmiany, z waznoscia i identyfikacja zmiany sprawczej.
- **Rozwiazane problemy** -- lista problemow, które zniknely w nowej wersji.
- **Ocena ogolna** -- slowna ocena caloksztaltu zmian.
- **Liczba zmian** -- sumaryczna liczba wykrytych roznic.
- **Poziom ryzyka** -- ocena ogolna: low (niski), medium (sredni), high (wysoki).

#### Formaty eksportu

| Format | Opis |
|--------|------|
| **TXT** | Raport tekstowy ze wszystkimi zmianami -- do wydruku lub przekazania dzialowi jakości |

#### Czas przetwarzania

20--40 sekund.

---

### 4.5 Walidator EAN/kodów

**Przycisk:** "Sprawdz kody"
**Czas przetwarzania:** 10--20 sekund

#### Przeznaczenie

Tryb weryfikuje kody kreskowe i QR widoczne na etykiecie. System odczytuje numery EAN/UPC z obrazu, waliduje cyfre kontrolna za pomoca algorytmu deterministycznego (niezaleznego od AI) i identyfikuje kraj pochodzenia na podstawie prefiksu. Dodatkowo wykrywa obecnosc kodów QR i odczytuje ich zawartosc.

#### Korzyści

- Deterministyczna walidacja cyfry kontrolnej -- wynik jest pewny, nie zależy od interpretacji AI.
- Automatyczna identyfikacja typu kodu (EAN-13, EAN-8, UPC-A).
- Rozpoznawanie kraju na podstawie prefiksu -- obsluga ponad 100 prefixow krajowych (np. 590 = Polska, 400-440 = Niemcy, 300-379 = Francja, 500-509 = Wielka Brytania).
- Wykrywanie i odczyt kodów QR.

#### Przypadki użycia

| Marketing | R&D |
|-----------|-----|
| Weryfikacja kodu EAN przed zatwierdzeniem etykiety do druku | Kontrola poprawności kodu na proofie drukarskim |
| Sprawdzenie, czy prefix kraju odpowiada rynkowi docelowemu | Szybka walidacja po zmianie kodu produktu |
| Potwierdzenie czytelności kodu QR z linkiem promocyjnym | Weryfikacja, czy kod QR prowadzi do właściwego URL |

#### Dane wejsciowe

- **Upload pliku** -- obraz JPG/PNG lub PDF etykiety z widocznym kodem kreskowym.

Przycisk "Sprawdz kody" jest aktywny po wgraniu pliku.

#### Przebieg analizy

1. AI odczytuje z obrazu numery kodów kreskowych i identyfikuje ich typ.
2. Dla każdego wykrytego kodu EAN/UPC system uruchamia deterministyczna walidacje:
   - Algorytm sumy wazonej -- dla EAN-13 wagi naprzemiennie 1 i 3, dla EAN-8 wagi 3 i 1.
   - Obliczenie oczekiwanej cyfry kontrolnej.
   - Porównanie z cyfra zapisana w kodzie.
3. Na podstawie 3-cyfrowego prefiksu system identyfikuje kraj rejestracji kodu.
4. System wykrywa obecnosc kodów QR i probuje odczytac ich zawartosc (URL lub tekst).

#### Raport wynikowy

Raport zawiera:

- **Liczba znalezionych kodów** -- ile kodów kreskowych wykryto na etykiecie.
- **Wyniki EAN/UPC** (dla każdego kodu):
  - Numer kodu
  - Typ (EAN-13 / EAN-8 / UPC-A / unknown)
  - Czytelność -- czy AI moglo odczytac kod
  - Walidacja cyfry kontrolnej -- poprawna / niepoprawna
  - Oczekiwana cyfra kontrolna (jesli niepoprawna)
  - Prefix krajowy i nazwa kraju
  - Uwagi
- **Kody QR** (dla każdego kodu):
  - Obecnosc
  - Czytelność
  - Zawartosc (URL lub tekst)
  - Uwagi
- **Status ogolny** -- czy wszystkie kody sa poprawne.
- **Podsumowanie** -- zwiezla ocena.

#### Formaty eksportu

| Format | Opis |
|--------|------|
| **TXT** | Raport tekstowy z wynikami walidacji każdego kodu |

#### Czas przetwarzania

10--20 sekund. Najszybszy tryb w aplikacji -- większość logiki realizowana jest deterministycznie w Pythonie.

---

## 5. Kategoria "Design" -- 1 tryb

Kategoria **"Design"** zawiera jeden tryb dedykowany ocenie projektu graficznego etykiety. Dostep: panel boczny > przycisk segmentowy "Design".

---

### 5.1 Analiza projektu graficznego

**Przycisk:** "Analizuj design"
**Czas przetwarzania:** 30--60 sekund

#### Przeznaczenie

Tryb analizuje projekt graficzny etykiety karmy jako profesjonalista od designu opakowan w branży pet food. System ocenia 10 kategorii designu (każda w skali 0--100), identyfikuje problemy z priorytetem, porównuje wyniki z benchmarkami segmentowymi i generuje podsumowanie wykonawcze z konkretnymi rekomendacjami dla działu R&D.

#### Korzyści

- 10 kategorii oceny z konkretnymi obserwacjami i rekomendacjami -- nie ogolniki, lecz precyzyjne wskazówki (np. "zwieksz font z 6pt do 8pt").
- Benchmark konkurencyjny -- porównanie z danymi branży pet food w wybranym segmencie produktowym.
- Priorytetyzacja problemow -- od krytycznych (natychmiastowa korekta) do sugestii (opcjonalna poprawa).
- Podsumowanie R&D -- 3-5 najwazniejszych akcji do podjecia, gotowe do przekazania zespolowi.
- Analiza trendow -- identyfikacja obecnych trendow branzowych, które etykieta realizuje lub pomija.

#### Przypadki użycia

| Marketing | R&D |
|-----------|-----|
| Ocena designu przed zatwierdzeniem do druku | Briefing dla agencji designowej z konkretnymi rekomendacjami |
| Porównanie wlasnej etykiety z benchmarkiem branży | Priorytetyzacja poprawek w kolejnej iteracji projektu |
| Argumentacja zmian designu przed zarzadem na podstawie benchmarkow | Analiza trendow do strategii opakowan |

#### Dane wejsciowe

- **Upload pliku** -- obraz JPG/PNG lub PDF gotowego projektu etykiety (nie szkic).
- **Segment produktu (do benchmarku)** -- lista rozwijana z 8 segmentami:

| Klucz segmentu | Nazwa wyswietlana |
|-----------------|-------------------|
| `premium_dry` | Premium sucha karma |
| `economy_dry` | Ekonomiczna sucha karma |
| `premium_wet` | Premium mokra karma |
| `economy_wet` | Ekonomiczna mokra karma |
| `treats` | Przysmaki |
| `supplements` | Suplementy |
| `barf_raw` | BARF / surowa |
| `veterinary` | Weterynaryjna |

Wybor segmentu wpływa na wartości referencyjne w benchmarku -- np. etykieta premium sucha oceniana jest wzgledem innych etykiet premium suchych, nie wzgledem calego rynku.

#### Przebieg analizy

1. System konwertuje plik do formatu analizowalnego przez AI.
2. AI analizuje projekt graficzny w 10 kategoriach:

| Nr | Kategoria | Klucz |
|----|-----------|-------|
| 1 | Hierarchia wizualna | `visual_hierarchy` |
| 2 | Czytelność | `readability` |
| 3 | Uzycie koloru | `color_usage` |
| 4 | Kompozycja | `layout_composition` |
| 5 | Elementy obowiązkowe | `regulatory_placement` |
| 6 | Wplyw półkowy | `shelf_impact` |
| 7 | Fotografia / grafika | `imagery` |
| 8 | Grupa docelowa | `target_audience` |
| 9 | Ekologia | `sustainability` |
| 10 | Uklad wielojęzyczny | `multilanguage_layout` |

3. Dla każdej kategorii system generuje ocene 0--100, obserwacje i rekomendacje.
4. Identyfikuje problemy i klasyfikuje je według ważności:
   - **critical** -- wymaga natychmiastowej korekty (np. nieczytelny tekst regulacyjny)
   - **major** -- wpływa na jakość (np. slaba hierarchia wizualna)
   - **minor** -- do rozwazenia (np. nieoptymalny układ wielojęzyczny)
   - **suggestion** -- opcjonalna poprawa (np. trend, który warto rozwazyc)
5. Porownuje wyniki z benchmarkami segmentowymi:
   - Wartosci referencyjne: p25 (25. percentyl), mediana, p75 (75. percentyl)
   - Oblicza percentyl etykiety w segmencie (0--100)
   - Przypisuje werdykt: `below_average`, `average`, `above_average`, `excellent`
6. Identyfikuje mocne strony etykiety.
7. Generuje porównania konkurencyjne (aspekt, poziom etykiety, standard branży, sugestia).
8. Analizuje zgodnosc z aktualnymi trendami branży pet food.
9. Tworzy podsumowanie wykonawcze dla R&D.

#### Raport wynikowy

Raport zawiera:

- **Ocena ogolna (0--100)** z interpretacja:
  - 80--100: doskonaly design, wzorcowy w branży
  - 60--79: dobry, spełnia standardy
  - 40--59: wymaga poprawy
  - 0--39: powazne problemy
- **Ocena ogolna slowna** -- 1--2 zdania podsumowania.
- **Oceny kategorii** -- dla każdej z 10 kategorii:
  - Ocena 0--100
  - Obserwacje (co zauwazono)
  - Rekomendacje (konkretne działania)
- **Problemy** -- lista z priorytetem (critical/major/minor/suggestion), opisem, lokalizacja na etykiecie i rekomendacja naprawy.
- **Mocne strony** -- lista elementow, które etykieta realizuje dobrze.
- **Porownania benchmarkowe** -- dla każdej kategorii:
  - Ocena etykiety vs p25 / mediana / p75 segmentu
  - Percentyl w segmencie
  - Werdykt (below_average / average / above_average / excellent)
- **Benchmark konkurencyjny** -- porównanie z praktykami branży (aspekt, obecny poziom, standard branży, sugestia).
- **Zgodnosc z trendami** -- lista trendow realizowanych lub pomijanych.
- **Podsumowanie dla R&D** -- 3--5 najwazniejszych akcji do podjecia.

#### Formaty eksportu

| Format | Opis |
|--------|------|
| **TXT** | Pelny raport tekstowy do wydruku lub przekazania zespolowi |
| **JSON** | Ustrukturyzowane dane do integracji z systemami wewnetrznymi |

#### Czas przetwarzania

30--60 sekund. Analiza realizowana jest w ramach jednego wywolania AI.

> **Uwaga:** Oceny sa subiektywna analiza AI opartą na praktykach branży pet food. Traktuj je jako profesjonalna opinie, nie audyt certyfikacyjny. AI analizuje obraz -- nie zna kontekstu marki, budzetu ani strategii.

---

## 6. Słownik pojęć

Ponizszy słownik zawiera wszystkie terminy specjalistyczne uzywane w aplikacji BULT Quality Assurance, skompilowane ze slownikow wszystkich trybów. Terminy ulozone sa alfabetycznie.

| Pojecie | Znaczenie |
|---------|-----------|
| **Appetite appeal** | Apetycznosc -- miara tego, czy zdjęcie lub grafika na etykiecie budzi chec zakupu u wlasciciela zwierzęcia. |
| **Art.19** | Artykul 19 rozporzadzenia EU 767/2009 -- obowiazek podania danych kontaktowych do uzyskania informacji o dodatkach zawartych w karmie. |
| **As-fed** | Wartość "tak jak podano" -- zawartosc składników odzywczych z uwzględnieniem wilgotności (w przeciwienstwie do wartości DM). |
| **Bbox (bounding box)** | Prostokatny obszar otaczający problem na etykiecie, określony wspolrzednymi. Uzywany w raportach struktury i skryptach JSX do lokalizacji defektow. |
| **Benchmark** | Porównanie wyników etykiety z danymi referencyjnymi branży pet food w danym segmencie produktowym. |
| **Bleed** | Spad -- margines drukarski wykraczajacy poza linie ciecia, zapewniajacy, ze grafika siega do samej krawedzi po obcieciu. |
| **Ca:P** | Stosunek wapnia do fosforu -- krytyczny parametr dla zdrowia kości, szczególnie u rosnacych zwierzat. FEDIAF okresla dopuszczalne zakresy. |
| **Check digit** | Cyfra kontrolna -- ostatnia cyfra kodu EAN/UPC, obliczana algorytmem sumy wazonej. Sluzy do weryfikacji poprawności calego numeru. |
| **Claim** | Oswiadczenie marketingowe na etykiecie (np. "70% miesa", "grain-free", "bogaty w kurczaka"). Podlega regulacjom EU 767/2009. |
| **Claim terapeutyczny** | Oswiadczenie sugerujace właściwości lecznicze (np. "leczy", "zapobiega chorobom") -- zabronione na etykietach karm na mocy Art.13 EU 767/2009. |
| **CMYK** | Model kolorów uzywany w druku (Cyan, Magenta, Yellow, Key/Black). Etykiety powinny byc przygotowane w tym modelu, nie w RGB. |
| **Compliance score** | Wynik zgodnosci 0--100 obliczany automatycznie na podstawie twardych regul FEDIAF i EU 767/2009. Nie jest interpretacja AI. |
| **Cross-check** | Niezależny, drugi odczyt wartości liczbowych z etykiety (składniki analityczne). Jesli roznica między odczytami przekracza 0,5%, system flaguje rozbieznosc. |
| **Delta E** | Miara różnicy między dwoma kolorami w przestrzeni CIE LAB. Delta E < 1 jest niezauwazalna, > 5 jest wyraznie widoczna. Uzywana w inspekcji artwork. |
| **Diakrytyk** | Znak modyfikujący litere, np. polskie: a e s c z z l n o, niemieckie: a o u ss, czeskie: r s c z u e. Czesty problem na etykietach wielojęzycznych, gdy czcionka nie zawiera pełnego zestawu znaków. |
| **DM (sucha masa)** | Dry matter -- wartość skladnika odzywczego po odjęciu wilgotności. Uzywana do porownywania karm o roznej wilgotności (np. sucha vs mokra). |
| **DPI** | Dots Per Inch -- rozdzielczosc obrazu. Etykiety do druku wymagają minimum 300 DPI. |
| **EAN-13** | Europejski kod kreskowy 13-cyfrowy. Najpopularniejszy format kodów kreskowych na etykietach karm w Europie. Prefix 590 = Polska. |
| **EAN-8** | Skrocony kod kreskowy 8-cyfrowy, uzywany na malych opakowaniach, gdzie EAN-13 nie zmiesci sie. |
| **EU 2018/848** | Rozporzadzenie UE dotyczace produktów ekologicznych. Uzycie terminów "Bio" lub "Organic" na etykiecie wymaga certyfikacji zgodnie z tym rozporzadzeniem. |
| **EU 2020/354** | Rozporzadzenie UE okreslajace liste zastosowan karm dietetycznych o szczególnym przeznaczeniu zywieniowym (PARNUT). |
| **EU 767/2009** | Glowna regulacja UE dotyczaca wprowadzania do obrotu i stosowania pasz (w tym karm dla zwierzat domowych). Okresla wymagania etykietowania, reguły nazewnictwa i zakazy. |
| **EU 767/2009 Art.17** | Artykul 17 -- reguły procentowe w nazewnictwie karm: "z X" = min 4%, "bogaty w X" = min 14%, nazwa = X = min 26%, "calkowicie z X" = min 100%. |
| **Facing** | Widok frontalny opakowania na półce sklepowej -- to, co konsument widzi jako pierwsze. |
| **FEDIAF** | Europejska Federacja Przemyslu Karm dla Zwierzat Domowych (Federation Europeenne de l'Industrie des Aliments pour Animaux Familiers). Wydaje wytyczne żywieniowe okreslajace minimalne i maksymalne wartości składników odzywczych. |
| **FEDIAF CoGLP** | Code of Good Labelling Practice -- kodeks dobrych praktyk etykietowania opracowany przez FEDIAF. |
| **Focus keyword** | Glowne slowo kluczowe dla SEO -- termin, na który opis produktu powinien byc najlepiej pozycjonowany. |
| **Glif** | Wizualna reprezentacja znaku w czcionce. Jesli czcionka nie zawiera glifa dla danego znaku, moze wyswietlic kwadracik (tofu), puste miejsce lub znak z innej czcionki. |
| **Grain-free** | Claim "bez zboz" -- weryfikowany poprzez sprawdzenie listy składników pod katem obecnosci zboz (pszenica, kukurydza, ryz, jeczmien, owies itp.). |
| **Hierarchia wizualna** | Porzadek ważności elementow na etykiecie -- od najwazniejszych (nazwa, marka) do najmniej istotnych (dane producenta). Dobrze zaprojektowana hierarchia prowadzi wzrok konsumenta. |
| **ICC Profile** | Profil kolorów definiujacy przestrzen barwna urzadzenia (monitora, drukarki). Zapewnia spójne odwzorowanie kolorów między projektantem a drukarnia. |
| **Język docelowy** | Język, na który system tłumaczy etykiete (wybrany przez użytkownika). |
| **Język źródłowy** | Język oryginalny etykiety, automatycznie wykrywany przez system. |
| **JSX** | Skrypt ExtendScript dla Adobe Illustratora. System BULT generuje skrypty JSX, które po uruchomieniu w Illustratorze dodaja warstwe "QC Annotations" z kolorowymi oznaczeniami problemow. |
| **Karma pełnoporcjowa** | Complete feed (EN) / Alleinfuttermittel (DE) -- karma pokrywajaca 100% potrzeb żywieniowych zwierzęcia dla danego gatunku i etapu zycia. |
| **Marker językowy** | Wizualne oznaczenie sekcji jezykowej na etykiecie: flaga, kod kraju (PL/DE/EN), ikona. Pozwala zidentyfikowac, który blok tekstu jest w którym jezyku. |
| **Meta description** | Opis strony wyświetlany w wynikach wyszukiwania Google. Optymalnie do 160 znaków. |
| **Meta title** | Tytul strony wyświetlany w wynikach wyszukiwania Google. Optymalnie do 60 znaków. |
| **Monoproteinowa** | Receptura z jednym źródłem bialka zwierzęcego. Claim weryfikowany przez sprawdzenie, czy w skladzie nie wystepuja ukryte źródła bialka (np. hydrolizat, maczka). |
| **Osierocony tekst** | Fragment tekstu między sekcjami jezykowymi, nieprzypisany do żadnego jezyka. Czesty problem na etykietach wielojęzycznych. |
| **PARNUT** | Karma dietetyczna o szczególnym przeznaczeniu zywieniowym (Particular Nutritional Purposes). Podlega dodatkowym wymaganiom regulacyjnym (EU 2020/354). |
| **QC Annotations** | Warstwa dodawana przez skrypt JSX w Adobe Illustratorze, zawierajaca kolorowe oznaczenia problemow wykrytych przez system. Warstwa jest zablokowana i można ja ukryc lub usunac po przegladzie. |
| **QR Code** | Dwuwymiarowy kod kreskowy mogacy zawierac URL, tekst lub dane. Na etykietach karm czesto prowadzi do strony produktu lub informacji dodatkowych. |
| **R&D** | Dzial badan i rozwoju -- główny odbiorca raportow z trybu "Analiza projektu graficznego". |
| **Regula 4%/14%/26%** | Reguly procentowe EU 767/2009 Art.17 okreslajace minimalna zawartosc skladnika wymienionego w nazwie: "z X" >= 4%, "bogaty w X" >= 14%, nazwa = X >= 26%. |
| **Saliency** | Mapa uwagi wizualnej -- analiza, które elementy etykiety najsilniej przyciagaja wzrok. |
| **Sekcja jezykowa** | Blok tekstu etykiety w jednym jezyku, oddzielony markerem jezykowym. Na etykietach wielojęzycznych każdy język ma swoja sekcje. |
| **Shelf impact** | Wplyw półkowy -- jak etykieta wygląda na półce sklepowej z dystansu 1--2 metrow. Mierzy zdolnosc przyciagniecia uwagi konsumenta. |
| **Składniki analityczne** | Analytical constituents (EN) / Analytische Bestandteile (DE) -- obowiazkowa tabela na etykiecie karmy zawierajaca wartości bialka, tluszczu, wlokna, popiolu i wilgotności. |
| **SSIM** | Structural Similarity Index Measure -- miara podobienstwa dwoch obrazow (0--1). Uzywana w inspekcji artwork do wykrywania roznic między master a proof. |
| **Symbol ℮** | Znak metrologiczny umieszczany przy masie netto na opakowaniu. Oznacza, ze producent stosuje system kontroli ilosci zgodny z dyrektywami UE. |
| **Tauryna** | Aminokwas niezbędny dla kotow -- FEDIAF wymaga minimum 0,1% w suchej masie. Brak tauryny w karmie dla kotow jest krytycznym defektem. |
| **TM (™)** | Trade Mark -- symbol niezarejestrowanego roszczenia do znaku towarowego. Nie daje ochrony prawnej, jedynie sygnalizuje zamiar. |
| **Tofu** | Potoczna nazwa kwadracika wyswietlanego gdy czcionka nie zawiera glifa dla danego znaku. Nazwa pochodzi od bialego kwadratu przypominajacego kostkę tofu. |
| **UPC-A** | Universal Product Code -- 12-cyfrowy kod kreskowy uzywany głównie w USA i Kanadzie. System BULT waliduje go analogicznie do EAN. |
| **Whitespace** | Pusta przestrzen na etykiecie -- nie oznacza "zmarnowanego miejsca". Odpowiednia ilosc whitespace poprawia czytelność i hierarchie wizualna. |
| **Znak towarowy (®)** | Zarejestrowany znak towarowy (np. w EUIPO lub UPRP). Uzycie symbolu ® bez rejestracji jest niezgodne z prawem. |

---

## 7. FAQ -- Najczesciej zadawane pytania

### Pytania ogólne

**Ile trwa analiza w poszczegolnych trybach?**

| Tryb | Kategoria | Orientacyjny czas |
|------|-----------|-------------------|
| Pelna weryfikacja (bez trendow) | Weryfikacja | 30--60 s |
| Pelna weryfikacja (z trendami rynkowymi) | Weryfikacja | 60--90 s |
| Weryfikacja jezykowa | Weryfikacja | 10--20 s |
| Kontrola struktury i czcionki | Weryfikacja | 15--30 s |
| Walidator claimów | Weryfikacja | 15--30 s |
| Weryfikator nazw i zastrzeżeń | Weryfikacja | 20--40 s |
| Walidator rynkowy | Weryfikacja | 20--40 s |
| Inspekcja artwork | Weryfikacja | 10--30 s |
| Tłumaczenie etykiety | Narzędzia | 20--40 s |
| Generator tekstu etykiety | Narzędzia | 20--40 s |
| Generator opisów produktów | Narzędzia | 30--60 s |
| Porównanie wersji | Narzędzia | 20--40 s |
| Walidator EAN/kodów | Narzędzia | 10--20 s |
| Analiza projektu graficznego | Design | 30--60 s |

Czasy sa orientacyjne i zaleza od rozmiaru pliku, złożoności etykiety i obciążenia API.

---

**Czy moje dane sa przechowywane?**

Nie. Analiza odbywa sie w pamięci sesji przeglądarki. Po zamknieciu karty przeglądarki dane znikają. Raporty sa zapisywane na dysku użytkownika tylko jesli ten swiadomie kliknie przycisk pobierania. System nie wysyla danych do zadnej bazy danych ani nie przechowuje historii analiz.

---

**Co jesli wystąpi błąd "Rate limit"?**

System automatycznie ponawia próbę po 15--60 sekundach. Przy częstych błędach -- odczekaj minutę między analizami. Blad rate limit oznacza, ze dostawca API (np. OpenAI, Anthropic) tymczasowo ograniczyl liczbe zapytan. Nie jest to błąd aplikacji ani danych użytkownika.

---

**Jakie formaty plikow sa obslugiwane?**

| Format | Opis | Uwagi |
|--------|------|-------|
| **JPG / JPEG** | Zdjecie etykiety | Najlepiej cala etykieta, dobra ostrosc |
| **PNG** | Obraz etykiety | Wyzsza jakość niz JPG, większy rozmiar pliku |
| **PDF** | Specyfikacja lub eksport z Illustratora | Najlepsza jakość dla etykiet projektowanych cyfrowo |
| **DOCX** | Dokument Word | Wymaga zainstalowanego LibreOffice do konwersji |
| **TIFF / TIF** | Obraz wysokiej jakości | Obslugiwany w trybie inspekcji artwork |

---

**Jaki jest maksymalny rozmiar pliku?**

Maksymalny rozmiar pliku wynosi 50 MB. Dla plikow wiekszych niz 20 MB system automatycznie kompresuje obraz, aby zmiescic sie w limitach API. Kompresja moze nieznacznie wplynac na jakość odczytu -- w takim przypadku zaleca sie uzycie pliku o mniejszym rozmiarze lub wyeksportowanie etykiety w nizszej rozdzielczosci.

---

**Czy system zastepuje eksperta?**

Nie. System eliminuje 80--90% rutynowej pracy weryfikacyjnej. Przypadki graniczne, produkty na nowe rynki eksportowe, karmy dietetyczne (PARNUT) i etykiety z claimami funkcjonalnymi zawsze powinny byc weryfikowane przez specjaliste ds. jakości, technologa zywnosci lub prawnika.

Dokladniej:
- **Pelna weryfikacja** -- zastepuje ręczne sprawdzanie tabeli analitycznej i checklisty EU, ale krytyczne niezgodnosci powinny byc potwierdzone.
- **Tłumaczenie** -- to punkt wyjscia do weryfikacji przez profesjonalnego tłumacza, szczególnie dla nowych rynkow.
- **Analiza designu** -- subiektywna ocena AI, nie audyt certyfikacyjny.
- **Walidator claimów** -- flaguje potencjalne problemy, ale ostateczna ocena należy do działu jakości.
- **Walidator EAN** -- walidacja cyfry kontrolnej jest deterministyczna i pewna, ale czytelność kodu na wydruku wymaga testu skanem.

---

**Jakiej jakości powinno byc zdjęcie etykiety?**

Im lepsza jakość zdjęcia, tym dokladniejsze wyniki analizy. Zalecenia:

- Cala etykieta powinna byc widoczna na zdjeciu (front i tyl, jesli to możliwe).
- Tekst musi byc czytelny -- unikaj rozmytych, zaciemnionych lub zbyt malych zdjec.
- Najlepsza opcja: eksport z Illustratora jako PDF lub PNG w wysokiej rozdzielczosci.
- Jesli system oznaczy pewność odczytu jako "Niska", sprobuj lepszego zdjęcia.
- Dla trybu inspekcji artwork optymalna rozdzielczosc to minimum 300 DPI.

---

**Czy moge analizowac etykiety w dowolnym jezyku?**

Tak. System automatycznie wykrywa język(i) na etykiecie. Wszystkie tryby weryfikacyjne dzialaja z etykietami w dowolnym jezyku europejskim. Tryby tłumaczenia i generowania obsluguja 14 języków docelowych: angielski, niemiecki, francuski, czeski, wegierski, rumunski, wloski, hiszpanski, holenderski, slowacki, bulgarski, chorwacki, portugalski i polski.

---

**Czy system wymaga polaczenia z internetem?**

Tak. System komunikuje sie z dostawcami AI (API) w celu analizy obrazow i generowania raportow. Jedyna czesc dzialajaca calkowicie offline to deterministyczna walidacja (reguły FEDIAF, cyfra kontrolna EAN, reguły procentowe).

---

### Pytania dotyczace trybów weryfikacyjnych

**Jak działa weryfikacja krzyzowa (cross-check)?**

W trybie "Pelna weryfikacja" system wykonuje dwa niezalezne odczyty tabeli składników analitycznych. Pierwszy odczyt jest czescia glownej ekstrakcji danych. Drugi odczyt pobiera TYLKO wartości liczbowe z tabeli -- jako niezalezne potwierdzenie. Jesli roznica między odczytami przekracza 0,5% dla dowolnego skladnika, system flaguje rozbieznosc i oznacza raport jako wymagajacy przegladu czlowieka.

---

**Co jesli zdjęcie jest złej jakości?**

System oznaczy pewność odczytu jako "Niska" i zaleci weryfikacje z oryginalem. W takiej sytuacji:
- Raport jest automatycznie oznaczany jako "wymagajacy przegladu".
- Wartosci liczbowe mogą byc niedokladne.
- Zalecenie: sprobuj lepszego zdjęcia lub uzyj eksportu PDF z programu graficznego.

---

**Czy walidator claimów wykrywa wszystkie claimy?**

System ekstrahuje widoczne claimy z etykiety. Ukryte lub nieczytelne elementy mogą zostać pominięte -- jakość zdjęcia ma znaczenie. System wykrywa claimy procentowe, skladnikowe ("grain-free", "bogaty w..."), odzywcze i terapeutyczne. Dla każdego sprawdza spójność ze składem i zgodnosc z regulami EU 767/2009.

---

**Czym sie rozni "Walidator claimów" od "Weryfikatora nazw i zastrzeżeń"?**

| Aspekt | Walidator claimów | Weryfikator nazw i zastrzeżeń |
|--------|-------------------|-------------------------------|
| Fokus | Spojnosc claimów ze składem | Zgodnosc regulacyjna prezentacji handlowej |
| Zakres | Claimy marketingowe | Nazewnictwo + marka + receptury + IP/trademark |
| Reguly | Spojnosc % ze skladnikami | EU 767/2009 Art.17, EU 2018/848, FEDIAF CoGLP |
| Wynik | Lista claimów z ocena spójności | 4 sekcje z ocenami + wynik ogolny |

---

**Czy skrypt JSX (tryb kontroli struktury) modyfikuje moj plik?**

Nie. Skrypt dodaje nowa, zablokowana warstwe "QC Annotations" z kolorowymi oznaczeniami problemow. Nie modyfikuje istniejacych warstw ani obiektow w pliku. Po przegladzie można warstwe ukryc lub usunac. Instrukcja użycia:

1. Otworz oryginalny plik .ai w Adobe Illustratorze.
2. File > Scripts > Other Script...
3. Wybierz pobrany plik .jsx.
4. Przejrzyj oznaczenia kolorowe na warstwie "QC Annotations".
5. Usun lub ukryj warstwe przed eksportem do druku.

---

### Pytania dotyczace trybów narzediowych

**Czy moge tlumaczyc etykiete z dowolnego jezyka?**

Tak. System automatycznie wykrywa język źródłowy. Nie trzeba go wskazywac ręcznie. Obslugiwane sa wszystkie jezyki europejskie jako zrodlowe. Jezyki docelowe to 14 języków dostepnych w liscie rozwijanej.

---

**Czy tłumaczenie uwzględnia terminologię branzowa?**

Tak. System używa oficjalnych tlumaczen terminów regulacyjnych z EU 767/2009. Przyklady:
- "składniki analityczne" = "analytical constituents" (EN) = "Analytische Bestandteile" (DE)
- "karma pełnoporcjowa" = "complete feed" (EN) = "Alleinfuttermittel" (DE)
- "dodatki" = "additives" (EN) = "Zusatzstoffe" (DE)

---

**Czy moge wkleić tekst zamiast wgrywac plik do tłumaczenia?**

Tak. Pod polem uploadu znajduje sie pole tekstowe "Lub wklej/wpisz tekst etykiety" (maksymalnie 2000 znaków). Jesli wgrasz plik i wpiszesz tekst jednocześnie, plik ma priorytet -- tekst zostanie zignorowany. System wyświetli stosowne ostrzezenie.

---

**Co generuje "Generator tekstu etykiety" -- cala etykiete?**

Tak. System generuje pełny tekst etykiety podzielony na sekcje:
- Skład (lista składników)
- Składniki analityczne
- Dawkowanie (tabela)
- Ostrzezenia
- Informacje o producencie
- Dodatkowe sekcje wymagane regulacyjnie

Kazda sekcja opatrzona jest odniesieniem do odpowiedniego artykulu regulacji. Tekst jest gotowy do przekazania grafikowi jako punkt wyjscia -- nie zastepuje weryfikacji przez technologa.

---

**Jakie style (tony) sa dostępne w generatorze opisów produktów?**

Cztery style tonalne:

| Styl | Opis | Dla kogo |
|------|------|----------|
| **Premium / Luksusowy** | Język ekskluzywny, podkreslenie jakości i wyjatkowosci | Marki premium, super-premium |
| **Naukowy / Weterynaryjny** | Terminologia specjalistyczna, dane naukowe, odwolania do badan | Marki weterynaryjne, dietetyczne |
| **Naturalny / Wholesome** | Akcent na naturalnosc, pochodzenie składników, brak sztucznych dodatkow | Marki naturalne, ekologiczne |
| **Standardowy / Neutralny** | Rzeczowy, informacyjny ton bez emocjonalnego zabarwienia | Marki ekonomiczne, private label |

---

**Czy generator opisów sprawdza claimy?**

Tak. System automatycznie skanuje wygenerowany opis pod katem claimów marketingowych i generuje ostrzeżenia dla claimów problematycznych. Typy ostrzeżeń:
- **forbidden_therapeutic** -- claim sugerujacy właściwości lecznicze (zabroniony)
- **unsubstantiated** -- claim bez pokrycia w danych produktu
- **naming_rule_violation** -- naruszenie regul procentowych EU 767/2009
- **needs_evidence** -- claim wymagajacy dodatkowych dowodow

Kazde ostrzezenie zawiera wyjasnienie i rekomendacje alternatywy.

---

**Co dokladnie porównuje tryb "Porównanie wersji"?**

System porównuje dwie etykiety holistycznie:
- **Tekst** -- skład, składniki analityczne, claimy, dawkowanie, dane producenta, ostrzeżenia.
- **Layout** -- rozmieszczenie elementow, rozmiary czcionek, hierarchia.
- **Elementy regulacyjne** -- czy zmiany wplywaja na zgodnosc z EU 767/2009.

Dla każdej zmiany system ocenia:
- Typ: dodano / usunieto / zmodyfikowano / przeniesiono
- Waznosc: krytyczna / ostrzezenie / informacja
- Wplyw regulacyjny: czy zmiana wymaga dodatkowej weryfikacji

---

**Jak dokładna jest walidacja EAN?**

Walidacja cyfry kontrolnej jest **deterministyczna i w 100% dokładna** -- uzywany jest algorytm matematyczny, nie interpretacja AI. Jesli system odczyta numer poprawnie, wynik walidacji jest pewny.

Natomiast sam odczyt numeru z obrazu zależy od jakości zdjęcia. AI odczytuje cyfry z obrazu, co moze byc niedokladne przy niskiej rozdzielczosci lub niewyraznym druku. W razie watpliwosci warto wpisac numer ręcznie i zweryfikowac go niezależnie.

Identyfikacja kraju na podstawie prefiksu obsluguje ponad 100 prefixow krajowych, w tym:
- 590 = Polska
- 400--440 = Niemcy
- 300--379 = Francja
- 500--509 = Wielka Brytania
- 800--839 = Wlochy
- 840--849 = Hiszpania

---

**Czy system wykrywa kody QR?**

Tak. Oproc kodów kreskowych EAN/UPC system wykrywa obecnosc kodów QR na etykiecie. Jesli kod QR jest czytelny, system odczytuje jego zawartosc (np. URL strony produktu) i raportuje ja w wynikach.

---

### Pytania dotyczace trybu Design

**Czy oceny designu sa obiektywne?**

Nie. Oceny sa subiektywna analiza AI oparta na praktykach branży pet food. System nie ma dostępu do kontekstu marki, budzetu, strategii marketingowej ani grupy docelowej. Traktuj oceny jako profesjonalna opinie -- wartość dodana do wlasnej ekspertyzy, nie ostateczny werdykt.

---

**Jak interpretowac benchmarki segmentowe?**

System porównuje ocene etykiety z danymi referencyjnymi dla wybranego segmentu (np. "Premium sucha karma"). Wartosci:
- **p25** -- 25. percentyl: 75% etykiet w segmencie ma wyzsza ocene.
- **Mediana** -- 50. percentyl: polowa etykiet jest lepsza, polowa gorsza.
- **p75** -- 75. percentyl: tylko 25% etykiet w segmencie ma wyzsza ocene.
- **Percentyl etykiety** -- gdzie na tle segmentu plasuje sie analizowana etykieta.

Werdykty:
- **below_average** -- poniżej przecietnej w segmencie
- **average** -- przecietna
- **above_average** -- powyzej przecietnej
- **excellent** -- doskonala, w czolowce segmentu

---

**Dla kogo jest raport z analizy designu?**

Glownie dla działu R&D i marketingu. Sekcja "Podsumowanie dla R&D" zawiera 3--5 konkretnych akcji do podjecia. Raport można również wykorzystac:
- Jako briefing dla agencji designowej
- Jako argument przy prezentacji zmian designu przed zarzadem (dzieki benchmarkom)
- Jako input do strategii opakowan (dzieki analizie trendow)

---

**Czy system porównuje z konkretnymi konkurentami?**

Nie z nazwy. System porównuje z ogólnymi standardami i trendami w branży opakowan pet food. Benchmarki segmentowe oparte sa na zagregowanych danych, nie na konkretnych markach. Sekcja "Benchmark konkurencyjny" opisuje praktyki branży (np. "większość marek premium używa fotografii appetite appeal"), nie wymienia nazw konkurentow.

---

### Pytania techniczne

**Czy potrzebuje konta aby korzystac z aplikacji?**

Konfiguracja wymaga klucza API dostawcy AI (np. OpenAI, Anthropic). Klucz konfiguruje sie w pliku `.env`. Sama aplikacja nie wymaga tworzenia konta użytkownika.

---

**Czy moge uruchomic kilka analiz jednocześnie?**

Nie. Kazda analiza jest wykonywana sekwencyjnie. Rozpoczecie nowej analizy zastepuje wyniki poprzedniej. Jesli potrzebujesz zachowac wyniki, pobierz raport przed uruchomieniem kolejnej analizy.

---

**Co jesli LibreOffice nie jest zainstalowane?**

Pliki DOCX wymagają LibreOffice do konwersji na format analizowalny przez AI. Jesli LibreOffice nie jest zainstalowany, system wyświetli błąd przy probie wgrania pliku DOCX. Rozwiazanie: zainstaluj LibreOffice lub przekonwertuj dokument na PDF ręcznie przed wgraniem.

---

**Czy system działa na urzadzeniach mobilnych?**

Aplikacja oparta jest na Streamlit i działa w przegladarce. Interfejs jest responsywny, ale ze wzgledu na zlozona strukture raportow i formularz danych najwygodniej korzystac z komputera z szerokim ekranem.



# Rozdział 8: Wskazówki dla Marketingu vs R&D

## 8.1 Dla działu Marketingu

Dział marketingu najczęściej odpowiada za stronę wizualną i komunikacyjną etykiety — od claimów reklamowych, przez poprawność językową, po końcową prezentację graficzną. Poniżej przedstawiono rekomendowany przepływ pracy oraz wskazówki dotyczące interpretacji wyników.

### Rekomendowany przepływ pracy

Optymalną kolejnością trybów dla działu marketingu jest:

1. **Weryfikacja językowa** — sprawdzenie poprawności ortograficznej, gramatycznej i stylistycznej wszystkich wersji językowych na etykiecie.
2. **Walidator claimów** — weryfikacja, czy deklaracje marketingowe (np. „bogaty w kurczaka", „bez zbóż") są spójne ze składem i zgodne z przepisami.
3. **Analiza designu** — ocena czytelności, hierarchii wizualnej i zgodności z dobrymi praktykami projektowania opakowań.
4. **Pełna weryfikacja** — kompleksowa kontrola obejmująca wszystkie aspekty, przeprowadzana przed zatwierdzeniem do druku.
5. **Inspekcja artwork** — końcowa kontrola pliku produkcyjnego (PDF/grafika) pod kątem parametrów technicznych.

### Kiedy używać poszczególnych trybów

| Etap procesu | Tryb | Cel |
|---|---|---|
| Przygotowanie tekstów | Weryfikacja językowa | Wyeliminowanie błędów językowych przed zatwierdzeniem copywritingu |
| Opracowanie claimów | Walidator claimów | Upewnienie się, że każdy claim jest uzasadniony składem produktu |
| Przygotowanie nazwy produktu | Nazwy i zastrzeżenia | Weryfikacja reguły procentowej w nazwie (Art. 17 EU 767/2009) |
| Projekt graficzny | Analiza designu | Ocena czytelności i atrakcyjności wizualnej opakowania |
| Wersja do wewnętrznego zatwierdzenia | Pełna weryfikacja | Kompleksowy raport do dołączenia do karty akceptacji |
| Plik gotowy do druku | Inspekcja artwork | Kontrola techniczna pliku PDF lub grafiki rastrowej |
| Przygotowanie wersji na nowy rynek | Walidator rynkowy | Sprawdzenie zgodności z wymogami docelowego kraju |

### Interpretacja wyników — decyzje go/no-go

Aplikacja BULT przypisuje poszczególnym sprawdzeniom statusy, które można przełożyć na decyzje biznesowe:

- **Wszystkie sprawdzenia pozytywne (brak ostrzeżeń i błędów)** — etykieta gotowa do zatwierdzenia. Można przekazać do druku.
- **Obecne ostrzeżenia (warnings), brak błędów krytycznych** — etykieta wymaga przeglądu wskazanych elementów. Ostrzeżenia często dotyczą zaleceń dobrych praktyk, a nie twardych wymogów prawnych. Decyzja o akceptacji leży po stronie osoby odpowiedzialnej.
- **Obecne błędy krytyczne (errors)** — etykieta nie powinna być zatwierdzana. Błędy krytyczne oznaczają niezgodność z przepisami (np. brak składników analitycznych, brak informacji o producencie, claima sprzeczna ze składem).

Jako regułę ogólną można przyjąć: **zero błędów krytycznych = warunek konieczny do zatwierdzenia**.

### Formaty eksportu przydatne dla marketingu

- **TXT** — prosty raport tekstowy, wygodny do wklejenia w e-mail lub narzędzie do zarządzania projektem (np. Asana, Jira).
- **JSON** — przydatny, gdy dział marketingu współpracuje z zespołem IT lub automatyzuje przepływ informacji.
- **HTML** — dostępny w trybie generatora opisów; gotowy fragment do wykorzystania na stronie internetowej lub w materiałach e-commerce.

---

## 8.2 Dla działu R&D

Dział badawczo-rozwojowy odpowiada za stronę merytoryczną etykiety — od wartości odżywczych i składu, przez zgodność z normami FEDIAF, po iteracje projektowe uwzględniające zmiany formulacji.

### Rekomendowany przepływ pracy

Optymalną kolejnością trybów dla działu R&D jest:

1. **Pełna weryfikacja** — kompleksowa kontrola składu, wartości odżywczych i zgodności z normami FEDIAF.
2. **Kontrola struktury** — analiza układu etykiety, obecności wymaganych sekcji i ich wzajemnego rozmieszczenia.
3. **Walidator claimów** — potwierdzenie, że deklaracje marketingowe mają pokrycie w faktycznym składzie.
4. **Walidator rynkowy** — sprawdzenie wymogów specyficznych dla rynku docelowego (rejestracje, certyfikaty, formaty).
5. **Analiza designu** — weryfikacja, czy zmiany formulacji zostały poprawnie odzwierciedlone w projekcie graficznym.

### Wykorzystanie danych benchmarkowych

Tryb **Analiza designu** generuje dane porównawcze, które można wykorzystać w iteracjach projektowych:

- Raport w formacie **JSON** zawiera ustrukturyzowane dane liczbowe (np. proporcje kolorów, oceny czytelności), które dział R&D może porównywać między wersjami.
- Eksport **TXT** zawiera opis słowny tych samych parametrów — przydatny do dokumentacji technicznej produktu.
- Porównując wyniki kolejnych iteracji, zespół R&D może obiektywnie ocenić, czy zmiany formulacji (i wynikające z nich zmiany na etykiecie) poprawiły czy pogorszyły ogólną jakość projektu.

### Skrypty JSX w przepływie pracy z Adobe Illustrator

Tryb **Kontrola struktury** umożliwia eksport w formacie **JSX** — skryptu wykonywalnego w programie Adobe Illustrator. Skrypt ten:

- Automatycznie zaznacza na artworku obszary, w których wykryto problemy strukturalne.
- Tworzy nową warstwę z adnotacjami, nie modyfikując oryginalnego projektu.
- Pozwala grafikowi natychmiast zobaczyć, które elementy wymagają korekty.

Aby użyć skryptu JSX: w programie Adobe Illustrator należy wybrać menu **Plik → Skrypty → Inny skrypt...**, a następnie wskazać wyeksportowany plik `.jsx`.

Tryb kontroli struktury generuje także **obraz z adnotacjami** — plik graficzny z nałożonymi oznaczeniami problemów. Jest to wygodna alternatywa dla osób, które nie korzystają z Illustratora.

### Generator tekstu etykiety po zmianie formulacji

Gdy dział R&D zmienia formulację produktu (np. zmiana udziału składników, dodanie nowego składnika), tryb **Generator tekstu** pozwala szybko wygenerować zaktualizowany tekst etykiety. Generator uwzględnia:

- Zaktualizowaną listę składników w kolejności malejącej.
- Przeliczone wartości składników analitycznych.
- Dostosowane claimy zgodne z nowym składem.

Pozwala to zaoszczędzić czas i uniknąć ręcznych pomyłek przy aktualizacji tekstów po reformulacji.

### Porównanie wersji — śledzenie zmian

Tryb **Porównanie wersji** jest szczególnie przydatny w procesie iteracyjnym R&D:

- Pozwala wczytać dwie wersje etykiety (np. wersję sprzed i po zmianie formulacji) i automatycznie wygenerować raport różnic.
- Raport (eksport TXT) wskazuje dokładnie, które elementy uległy zmianie — od składu, przez wartości odżywcze, po claimy.
- Jest to narzędzie dokumentacyjne przydatne przy audytach wewnętrznych i przeglądach jakościowych.

---

## 8.3 Współpraca między działami

### Przepływ zatwierdzania etykiety z użyciem wielu trybów

Poniższy schemat przedstawia rekomendowany przepływ współpracy między działami z wykorzystaniem różnych trybów aplikacji BULT:

| Krok | Dział odpowiedzialny | Tryb BULT | Rezultat |
|------|---------------------|-----------|----------|
| 1. Opracowanie formulacji | R&D | Generator tekstu | Wygenerowany tekst bazowy etykiety |
| 2. Weryfikacja składu i wartości | R&D | Pełna weryfikacja | Raport zgodności z FEDIAF i EU 767/2009 |
| 3. Opracowanie claimów | Marketing | Walidator claimów | Lista zatwierdzonych i odrzuconych claimów |
| 4. Weryfikacja nazwy produktu | Marketing + R&D | Nazwy i zastrzeżenia | Potwierdzenie zgodności nazwy z Art. 17 |
| 5. Przygotowanie wersji językowych | Marketing | Weryfikacja językowa | Raport poprawności tekstów |
| 6. Adaptacja na rynki docelowe | Marketing + Regulatory | Walidator rynkowy | Raporty per kraj |
| 7. Projekt graficzny | Marketing + Grafik | Kontrola struktury + Analiza designu | Adnotacje i benchmarki |
| 8. Końcowa akceptacja | Dział Jakości | Pełna weryfikacja | Raport końcowy dołączony do dokumentacji |
| 9. Kontrola pliku do druku | R&D / Dział Jakości | Inspekcja artwork | Raport techniczny pliku produkcyjnego |

### Kiedy eskalować problem

Nie wszystkie problemy zidentyfikowane przez aplikację BULT mogą być rozwiązane wewnętrznie. Poniżej przedstawiono sytuacje wymagające eskalacji:

**Eskalacja do działu prawnego (lub zewnętrznego prawnika):**
- Wątpliwości dotyczące znaków towarowych (np. nazwa produktu koliduje z zarejestrowanym znakiem).
- Claimy terapeutyczne lub zdrowotne wykryte na etykiecie — wymagają oceny prawnej pod kątem rozporządzenia o oświadczeniach zdrowotnych.
- Niejasności dotyczące statusu regulacyjnego produktu na nowym rynku (np. wymóg rejestracji APHA w Wielkiej Brytanii po Brexicie).

**Eskalacja do działu jakości / technologa:**
- Wartości odżywcze poniżej minimów FEDIAF — wymaga weryfikacji formulacji i ewentualnej reformulacji.
- Niespójność między deklarowanym składem a claimami — wymaga decyzji, czy zmienić formulację, czy zrezygnować z claima.
- Problemy z proporcją Ca:P lub przekroczenie maksimów dla składników mineralnych.

**Eskalacja do eksperta zewnętrznego:**
- Złożone kwestie regulacyjne dotyczące nowych składników (np. białko owadzie, składniki GMO).
- Wymogi specyficzne dla rynków pozaeuropejskich (jeśli planowana jest dystrybucja poza 14 krajami obsługiwanymi przez walidator rynkowy).
- Wątpliwości dotyczące zgodności z lokalnymi normami weterynaryjnymi.

Ogólna zasada: jeśli aplikacja BULT wskazuje błąd krytyczny, a zespół wewnętrzny nie jest pewien interpretacji — należy eskalować do odpowiedniego specjalisty przed zatwierdzeniem etykiety.

---

# Rozdział 9: Formaty eksportu — tabela referencyjna

## 9.1 Przegląd formatów

Aplikacja BULT oferuje kilka formatów eksportu wyników. Dostępność poszczególnych formatów zależy od trybu weryfikacji.

### Tabela dostępności formatów

| Tryb | TXT | JSON | HTML | JSX | Obraz z adnotacjami |
|------|:---:|:----:|:----:|:---:|:-------------------:|
| Pełna weryfikacja | ✓ | ✓ | | | |
| Weryfikacja językowa | ✓ | | | | |
| Kontrola struktury | ✓ | | | ✓ | ✓ |
| Walidator claimów | ✓ | | | | |
| Nazwy i zastrzeżenia | ✓ | | | | |
| Walidator rynkowy | ✓ | | | | |
| Inspekcja artwork | ✓ | ✓ | | | |
| Tłumaczenie | ✓ | | | | |
| Generator tekstu | ✓ | | | ✓ | |
| Generator opisów | ✓ | ✓ | ✓ | | |
| Porównanie wersji | ✓ | | | | |
| Walidator EAN | ✓ | | | | |
| Analiza designu | ✓ | ✓ | | | |

## 9.2 Opis poszczególnych formatów

### TXT — raport tekstowy

- **Dostępność:** wszystkie tryby.
- **Zawartość:** pełny raport w postaci zwykłego tekstu, zawierający listę sprawdzeń, ich statusy (pass/fail/warning) oraz szczegółowe komentarze.
- **Zastosowanie:** dokumentacja wewnętrzna, załączniki do e-maili, wklejanie do systemów zarządzania projektami, archiwizacja. Jest to format uniwersalny i czytelny bez dodatkowego oprogramowania.

### JSON — dane ustrukturyzowane

- **Dostępność:** Pełna weryfikacja, Inspekcja artwork, Generator opisów, Analiza designu.
- **Zawartość:** wyniki weryfikacji w formacie JSON — pary klucz-wartość odpowiadające poszczególnym sprawdzeniom, statusy, wartości liczbowe, listy problemów.
- **Zastosowanie:** integracja z systemami zewnętrznymi (np. PIM, DAM, ERP), automatyzacja przepływów pracy, porównywanie wyników między wersjami programowo, zasilanie dashboardów jakościowych.

### HTML — strona internetowa

- **Dostępność:** Generator opisów.
- **Zawartość:** gotowy fragment HTML zawierający sformatowany opis produktu — tekst, tabele wartości odżywczych, wyróżnione claimy. Fragment jest gotowy do osadzenia na stronie e-commerce lub w karcie produktu.
- **Zastosowanie:** publikacja opisów produktów online, materiały do sklepów internetowych, karty produktowe.

### JSX — skrypt Adobe Illustrator

- **Dostępność:** Kontrola struktury.
- **Zawartość:** skrypt ExtendScript (.jsx) wykonywalny w programie Adobe Illustrator. Po uruchomieniu tworzy nową warstwę z adnotacjami wizualnymi (ramki, strzałki, etykiety tekstowe) wskazującymi problemy strukturalne wykryte na etykiecie.
- **Zastosowanie:** bezpośrednia praca grafika nad korektą artworku. Eliminuje konieczność ręcznego odnajdywania problemów na podstawie raportu tekstowego. Skrypt nie modyfikuje istniejących warstw projektu.

### Obraz z adnotacjami

- **Dostępność:** Kontrola struktury.
- **Zawartość:** plik graficzny (PNG lub JPEG) przedstawiający obraz etykiety z nałożonymi oznaczeniami wizualnymi — kolorowymi ramkami i etykietami wskazującymi problematyczne obszary.
- **Zastosowanie:** szybki przegląd wizualny wyników kontroli struktury bez konieczności uruchamiania Illustratora. Wygodny do udostępniania w komunikatorach, prezentacjach i raportach.

## 9.3 Jak eksportować wyniki

Po zakończeniu weryfikacji w dowolnym trybie:

1. Przejdź do sekcji wyników w dolnej części ekranu.
2. Kliknij przycisk eksportu odpowiadający wybranemu formatowi (ikony lub etykiety formatów).
3. Wskaż lokalizację zapisu pliku lub skopiuj zawartość do schowka (w zależności od formatu).

Jeśli dany format nie jest dostępny dla aktualnie wybranego trybu, odpowiedni przycisk eksportu będzie nieaktywny (wyszarzony).

---

# Rozdział 10: Funkcje opcjonalne

## 10.1 Przegląd

Aplikacja BULT oferuje trzy funkcje opcjonalne, które wymagają dodatkowej instalacji zależności. Funkcje te rozszerzają możliwości aplikacji o zaawansowane analizy, ale nie są wymagane do podstawowej pracy. Ich instalacja zwiększa rozmiar aplikacji na dysku.

Sekcja instalacji dostępna jest w panelu bocznym aplikacji, w części zatytułowanej **„Dodatkowe funkcje"**.

## 10.2 OCR Text Comparison — porównanie tekstu OCR

- **Zależności:** `easyocr` (~200 MB dodatkowej przestrzeni dyskowej).
- **Funkcja:** umożliwia automatyczne porównanie tekstu między dwiema wersjami etykiety za pomocą rozpoznawania znaków optycznych (OCR). Aplikacja odczytuje tekst z obu obrazów etykiety i generuje raport różnic.
- **Zastosowanie:** tryb Porównanie wersji — gdy użytkownik nie dysponuje plikami tekstowymi, a jedynie obrazami lub skanami etykiet. OCR automatycznie wyodrębnia tekst z grafiki, umożliwiając porównanie bez ręcznego przepisywania.
- **Instalacja:** w panelu bocznym, w sekcji „Dodatkowe funkcje", kliknij przycisk instalacji przy pozycji „OCR Text Comparison". Instalacja wymaga połączenia z internetem i może potrwać kilka minut w zależności od prędkości łącza.

## 10.3 Analiza uwagi wizualnej

- **Zależności:** `deepgaze-pytorch`, `torch`, `scipy` (~800 MB dodatkowej przestrzeni dyskowej).
- **Funkcja:** generuje heatmapę predykcji uwagi konsumenta na podstawie modelu DeepGaze IIE. Model analizuje obraz etykiety i przewiduje, na które obszary oko konsumenta zwróci uwagę w pierwszej kolejności.
- **Zastosowanie:** tryb Analiza designu — pozwala działowi marketingu ocenić, czy kluczowe elementy etykiety (nazwa produktu, główny claim, zdjęcie) znajdują się w strefach wysokiej uwagi wizualnej. Pomaga optymalizować układ graficzny pod kątem skuteczności komunikacyjnej.
- **Instalacja:** w panelu bocznym, w sekcji „Dodatkowe funkcje", kliknij przycisk instalacji przy pozycji „Analiza uwagi wizualnej". Ze względu na rozmiar zależności (~800 MB) instalacja może potrwać dłużej. Wymagane jest połączenie z internetem.

> **Uwaga:** Funkcja analizy uwagi wizualnej wymaga znacznych zasobów obliczeniowych. Na komputerach z kartą graficzną NVIDIA (CUDA) analiza przebiega znacznie szybciej niż na samym procesorze (CPU).

## 10.4 Zaawansowana analiza PDF

- **Zależności:** `pymupdf` (~30 MB dodatkowej przestrzeni dyskowej).
- **Funkcja:** umożliwia szczegółową analizę plików PDF pod kątem parametrów technicznych przygotowania do druku — w tym analizę fontów (osadzenie, typ, rozmiar), sprawdzenie bleedu (spadów) oraz weryfikację profili kolorystycznych ICC.
- **Zastosowanie:** tryb Inspekcja artwork — niezbędna przy kontroli plików produkcyjnych przed wysłaniem do drukarni. Bez tej funkcji inspekcja artwork obsługuje jedynie pliki graficzne (PNG, JPEG, TIFF). Po zainstalowaniu zależności obsługiwane są także pliki PDF.
- **Instalacja:** w panelu bocznym, w sekcji „Dodatkowe funkcje", kliknij przycisk instalacji przy pozycji „Zaawansowana analiza PDF". Instalacja jest szybka ze względu na niewielki rozmiar pakietu (~30 MB).

## 10.5 Zarządzanie funkcjami opcjonalnymi

Każdą funkcję opcjonalną można zainstalować niezależnie od pozostałych. W panelu bocznym przy każdej pozycji wyświetlany jest aktualny status:

- **Nie zainstalowano** — funkcja niedostępna; widoczny przycisk „Zainstaluj".
- **Zainstalowano** — funkcja aktywna i gotowa do użycia.

W przypadku problemów z instalacją (np. brak połączenia z internetem, niewystarczająca ilość miejsca na dysku) aplikacja wyświetli komunikat z opisem błędu.

---

# Dodatek A: Lista krajów walidatora rynkowego

## A.1 Obsługiwane rynki

Walidator rynkowy obsługuje 14 krajów europejskich. Dla każdego kraju zdefiniowane są specyficzne wymogi regulacyjne, językowe i formalne.

| Kod | Kraj | Język wymagany | Kluczowe przepisy i wymogi |
|-----|------|----------------|---------------------------|
| DE | Niemcy | niemiecki (de) | LMIV — minimalna czcionka ≥1,2 mm; pełna wersja niemiecka; certyfikat DE-ÖKO dla produktów bio; adres producenta w UE |
| FR | Francja | francuski (fr) | Loi Toubon — cały tekst musi być w języku francuskim; wymagany numer LOT (partii); certyfikat FR-BIO dla produktów ekologicznych; oznaczenie pochodzenia; symbole Triman i Info-tri |
| CZ | Czechy | czeski (cs) | Pełna wersja czeska; rejestracja SVS (Státní veterinární správa); poprawna czeska diakrytyka (háčky, čárky); czeskie nazwy dodatków |
| HU | Węgry | węgierski (hu) | Pełna wersja węgierska; rejestracja NÉBIH (Nemzeti Élelmiszerlánc-biztonsági Hivatal); poprawna węgierska diakrytyka; tabela karmienia z podaniem mas ciała |
| RO | Rumunia | rumuński (ro) | Pełna wersja rumuńska; rejestracja ANSVSA; poprawna rumuńska diakrytyka (ș/ț z cedillą, nie z przecinkiem); adres importera |
| IT | Włochy | włoski (it) | Pełna wersja włoska (D.Lgs. 142/2012); numer stabilimento (zakładu produkcyjnego); oznaczenie pochodzenia zwierzęcego; D.Lgs. 116/2020 — oznakowanie opakowań; certyfikat IT-BIO |
| ES | Hiszpania | hiszpański (es) | Pełna wersja hiszpańska (kastylijska); numer rejestru RGSEAA; minimalna czcionka ≥1,2 mm; certyfikat ES-ECO dla produktów ekologicznych |
| UK | Wielka Brytania | angielski (en) | Pełna wersja angielska; rejestracja APHA (Animal and Plant Health Agency); oznaczenie UKCA (zamiast CE); odpowiedzialna strona z adresem w GB; zgodność claimów z wymogami FSA |
| NL | Holandia | niderlandzki (nl) | Pełna wersja niderlandzka; zgodność z wymogami NVWA (Nederlandse Voedsel- en Warenautoriteit); dowody naukowe zgodne ze standardami RvA; symbole recyklingu Afvalfonds |
| SK | Słowacja | słowacki (sk) | Pełna wersja słowacka; rejestracja ŠVPS (Štátna veterinárna a potravinová správa); poprawna słowacka diakrytyka; adres importera |
| BG | Bułgaria | bułgarski (bg) | Pełna wersja bułgarska w piśmie cyrylickim; rejestracja BFSA (Bulgarian Food Safety Agency); walidacja poprawności zapisu cyrylickiego; adres importera |
| HR | Chorwacja | chorwacki (hr) | Pełna wersja chorwacka; zgodność z wymogami HAPIH (Hrvatska agencija za poljoprivredu i hranu); poprawna chorwacka diakrytyka; adres importera |
| PT | Portugalia | portugalski (pt) | Pełna wersja portugalska; rejestracja DGAV (Direção-Geral de Alimentação e Veterinária); poprawna portugalska diakrytyka; symbol Ponto Verde |
| PL | Polska | polski (pl) | Pełna wersja polska; rejestracja GIW (Główny Inspektorat Weterynarii); poprawna polska diakrytyka; tabela karmienia; lista claimów zgodna z wymogami PIW |

## A.2 Uwagi ogólne

- Walidator rynkowy sprawdza wymogi specyficzne dla wybranego kraju **dodatkowo** — nie zastępuje kontroli ogólnounijnej (EU 767/2009).
- Dla każdego rynku można uruchomić osobną walidację. Jeśli produkt jest przeznaczony na kilka rynków, zaleca się przeprowadzenie walidacji dla każdego z nich osobno.
- Wymogi dotyczące diakrytyki są szczególnie istotne w językach środkowoeuropejskich (czeski, węgierski, słowacki, rumuński, chorwacki) — błędna diakrytyka może być traktowana jako naruszenie wymogów językowych.
- W krajach wymagających rejestracji weterynaryjnej (np. SVS, NÉBIH, ANSVSA, APHA, GIW) walidator sprawdza obecność numeru rejestracyjnego na etykiecie, ale nie weryfikuje jego poprawności w zewnętrznych bazach danych.

---

# Dodatek B: Progi FEDIAF 2021

## B.1 Minimalne wartości odżywcze (% suchej masy)

Poniższe tabele przedstawiają minimalne wymagane poziomy składników odżywczych zgodnie z wytycznymi FEDIAF (Fédération Européenne de l'Industrie des Aliments pour Animaux Familiers) w wersji z 2021 roku.

### Psy

| Etap życia | Typ karmy | Białko (min.) | Tłuszcz (min.) | Wapń (min.) | Fosfor (min.) |
|------------|-----------|:-------------:|:---------------:|:-----------:|:-------------:|
| Szczenię (Puppy) | Sucha / Mokra | 22,5% | 8,0% | 1,0% | 0,8% |
| Dorosły (Adult) | Sucha / Mokra | 18,0% | 5,0% | 0,5% | 0,4% |
| Senior | Sucha / Mokra | 18,0% | 5,0% | 0,5% | 0,4% |
| Wszystkie etapy (All-stages) | Sucha / Mokra | 22,5% | 8,0% | 1,0% | 0,8% |

### Koty

| Etap życia | Typ karmy | Białko (min.) | Tłuszcz (min.) | Wapń (min.) | Fosfor (min.) |
|------------|-----------|:-------------:|:---------------:|:-----------:|:-------------:|
| Kocię (Kitten) | Sucha / Mokra | 28,0% | 9,0% | 0,8% | 0,6% |
| Dorosły (Adult) | Sucha / Mokra | 25,0% | 9,0% | 0,6% | 0,5% |
| Senior | Sucha / Mokra | 25,0% | 9,0% | 0,6% | 0,5% |
| Wszystkie etapy (All-stages) | Sucha / Mokra | 28,0% | 9,0% | 0,8% | 0,6% |

> **Uwaga:** Kategoria „Wszystkie etapy" (All-stages) stosuje wartości najwyższe, odpowiadające wymogom dla szczeniąt/kociąt — ponieważ karma musi spełniać normy dla każdego etapu życia.

## B.2 Maksymalne wartości odżywcze (% suchej masy)

### Psy

| Etap życia | Wapń (maks.) | Fosfor (maks.) |
|------------|:------------:|:--------------:|
| Szczenię (Puppy) | 3,3% | 2,5% |
| Dorosły (Adult) | 4,5% | 4,0% |
| Senior | 4,5% | 4,0% |

### Koty

| Etap życia | Wapń (maks.) | Fosfor (maks.) |
|------------|:------------:|:--------------:|
| Kocię (Kitten) | 3,0% | 2,5% |
| Dorosły (Adult) | 4,0% | 3,5% |
| Senior | 4,0% | 3,5% |

> **Uwaga:** Przekroczenie wartości maksymalnych wapnia i fosforu jest szczególnie niebezpieczne dla młodych zwierząt (szczeniąt i kociąt), u których może prowadzić do zaburzeń rozwoju układu kostnego.

## B.3 Formuła przeliczeniowa: z „as fed" na suchą masę

Wartości podawane na etykietach karm mokrych (i niekiedy suchych) są wyrażone w przeliczeniu „as fed" — czyli z uwzględnieniem wilgotności produktu. Aby porównać je z progami FEDIAF (wyrażonymi w % suchej masy), należy zastosować przeliczenie:

```
wartość_SM = wartość_as_fed / (1 − wilgotność / 100)
```

Gdzie:
- **wartość_SM** — wartość w przeliczeniu na suchą masę (% DM, dry matter).
- **wartość_as_fed** — wartość deklarowana na etykiecie (% w produkcie gotowym).
- **wilgotność** — zawartość wilgoci w produkcie (%).

**Domyślna wilgotność:** jeśli wartość wilgotności nie jest podana na etykiecie, aplikacja przyjmuje domyślnie **10%** (typowe dla karm suchych).

### Przykład przeliczenia

Karma mokra dla dorosłego psa deklaruje:
- Białko: 8% (as fed)
- Wilgotność: 78%

Przeliczenie:

```
białko_SM = 8 / (1 − 78/100) = 8 / 0,22 = 36,36%
```

Wartość 36,36% suchej masy jest powyżej minimum FEDIAF dla dorosłego psa (18,0%) — wymóg spełniony.

---

# Dodatek C: 6 wymagań EU 767/2009

## C.1 Wprowadzenie

Rozporządzenie (WE) nr 767/2009 Parlamentu Europejskiego i Rady z dnia 13 lipca 2009 r. w sprawie wprowadzania na rynek i stosowania pasz ustanawia obowiązkowe wymagania dotyczące etykietowania karm dla zwierząt domowych. Aplikacja BULT weryfikuje sześć kluczowych wymagań wynikających z tego rozporządzenia.

## C.2 Szczegółowy opis wymagań

### 1. Lista składników (ingredients_listed)

**Wymóg:** etykieta musi zawierać pełną listę składników w kolejności malejącej według masy w momencie ich użycia w procesie produkcyjnym.

**Co sprawdza BULT:** obecność sekcji „Skład" lub „Składniki" (lub odpowiednika w języku docelowym) zawierającej listę składników. Aplikacja weryfikuje, czy lista jest niepusta.

**Typowe problemy:** brak listy składników (najczęściej na prototypowych etykietach), niekompletna lista, nieprawidłowa kolejność składników.

### 2. Składniki analityczne (analytical_constituents_present)

**Wymóg:** etykieta musi zawierać deklarację składników analitycznych, w tym co najmniej: białko surowe, tłuszcz surowy, włókno surowe i popiół surowy (substancje mineralne).

**Co sprawdza BULT:** obecność sekcji „Składniki analityczne" (lub odpowiednika) z wartościami liczbowymi dla wymaganych parametrów.

**Typowe problemy:** brak jednego lub więcej obowiązkowych parametrów, nieprawidłowe jednostki (np. mg zamiast %), brak sekcji na etykietach wielojęzycznych w jednej z wersji językowych.

### 3. Dane producenta (manufacturer_info)

**Wymóg:** etykieta musi zawierać nazwę i adres podmiotu odpowiedzialnego za etykietowanie (producent, pakujący, importer lub sprzedawca) w formie umożliwiającej identyfikację i kontakt.

**Co sprawdza BULT:** obecność nazwy firmy i adresu (ulica, kod pocztowy, miasto, kraj) w treści etykiety.

**Typowe problemy:** brak adresu (podana tylko nazwa firmy), niekompletny adres (brak kodu pocztowego lub kraju), adres nieczytelny ze względu na zbyt małą czcionkę.

### 4. Masa netto (net_weight_declared)

**Wymóg:** etykieta musi zawierać deklarację masy netto produktu wyrażoną w jednostkach masy (g, kg) lub objętości (ml, l) zgodnie z systemem metrycznym.

**Co sprawdza BULT:** obecność wartości liczbowej z jednostką masy lub objętości w treści etykiety.

**Typowe problemy:** brak deklaracji masy netto, nieprawidłowa jednostka, brak symbolu ℮ (choć sam symbol ℮ jest opcjonalny — jego obecność oznacza zgodność z dyrektywą o ilościach nominalnych i jest sprawdzana osobno w checkliście opakowaniowej).

### 5. Gatunek docelowy (species_clearly_stated)

**Wymóg:** etykieta musi jednoznacznie określać gatunek zwierzęcia, dla którego karma jest przeznaczona (np. „dla psów", „dla kotów", „dla psów i kotów").

**Co sprawdza BULT:** obecność jednoznacznego wskazania gatunku docelowego w treści etykiety lub nazwie produktu.

**Typowe problemy:** brak jawnego wskazania gatunku (poleganie wyłącznie na grafice — np. zdjęciu psa), niejednoznaczne sformułowanie.

### 6. Numer partii / data ważności (batch_or_date_present)

**Wymóg:** etykieta musi zawierać numer partii produkcyjnej (LOT) lub datę minimalnej trwałości (najlepiej spożyć przed / best before), lub oba te elementy.

**Co sprawdza BULT:** obecność co najmniej jednego z następujących elementów: numer partii (LOT), data minimalnej trwałości (BBD/BBE), data produkcji.

**Typowe problemy:** brak strefy przeznaczonej na numer partii lub datę (szczególnie na prototypach graficznych), numer partii nieczytelny, brak oznaczenia formatu daty.

## C.3 Podsumowanie

| Nr | Identyfikator | Opis | Podstawa prawna |
|----|--------------|------|-----------------|
| 1 | ingredients_listed | Lista składników | Art. 17 ust. 1 lit. f) |
| 2 | analytical_constituents_present | Składniki analityczne | Art. 17 ust. 1 lit. f) |
| 3 | manufacturer_info | Dane producenta | Art. 17 ust. 1 lit. a) |
| 4 | net_weight_declared | Masa netto | Art. 17 ust. 1 lit. d) |
| 5 | species_clearly_stated | Gatunek docelowy | Art. 17 ust. 1 lit. b) |
| 6 | batch_or_date_present | Numer partii / data ważności | Art. 17 ust. 1 lit. e) |

Wszystkie sześć wymagań musi być spełnionych, aby etykieta mogła być uznana za zgodną z rozporządzeniem EU 767/2009 w zakresie obowiązkowych informacji na etykiecie.

---

# Dodatek D: Checklista kontroli opakowania

## D.1 Wprowadzenie

Moduł kontroli opakowania w aplikacji BULT sprawdza ponad 30 elementów pogrupowanych w kategorie tematyczne. Poniżej przedstawiono pełną listę z opisem każdego elementu.

## D.2 Informacje żywieniowe i karmienie

| Identyfikator | Opis | Wyjaśnienie |
|--------------|------|-------------|
| feeding_guidelines_present | Wytyczne karmienia | Sprawdza obecność tabeli lub instrukcji karmienia z zalecanymi porcjami dziennymi, zwykle w zależności od masy ciała zwierzęcia. |
| product_classification | Klasyfikacja produktu | Weryfikuje, czy produkt jest oznaczony jako: **complete** (karma pełnoporcjowa), **complementary** (karma uzupełniająca), **treat** (przysmak) lub **not_stated** (brak klasyfikacji — co stanowi błąd). |
| storage_instructions_present | Instrukcje przechowywania | Sprawdza obecność informacji o warunkach przechowywania (np. „Przechowywać w suchym i chłodnym miejscu", „Po otwarciu przechowywać w lodówce i zużyć w ciągu 48 godzin"). |

## D.3 Claimy i deklaracje

| Identyfikator | Opis | Wyjaśnienie |
|--------------|------|-------------|
| claims_consistent_with_composition | Spójność claimów ze składem | Sprawdza, czy wszystkie deklaracje marketingowe (np. „bogaty w łososia", „bez zbóż", „hipoalergiczny") mają pokrycie w zadeklarowanym składzie produktu. |
| claims_inconsistencies | Lista niespójności | W przypadku wykrycia niespójności — zwraca szczegółową listę claimów, które są sprzeczne ze składem (np. claim „bez kurczaka" przy obecności „mączki z drobiu" na liście składników). |
| meat_percentage_claim_consistent | Spójność claima % mięsa | Weryfikuje, czy deklarowany procent mięsa (np. „60% kurczaka") jest spójny z pozycją tego składnika na liście i zadeklarowanym udziałem procentowym. |
| no_therapeutic_claims | Brak claimów terapeutycznych | Sprawdza, czy etykieta nie zawiera niedozwolonych oświadczeń terapeutycznych lub leczniczych (np. „leczy alergie", „zapobiega chorobom nerek"). Takie claimy są zakazane dla karm i przysmaków. |
| naming_percentage_rule_ok | Reguła % w nazwie | Weryfikuje zgodność nazwy produktu z Art. 17 rozporządzenia EU 767/2009, który określa minimalne udziały procentowe składnika wymienionego w nazwie (np. „z kurczakiem" wymaga min. 4%, „bogaty w kurczaka" wymaga min. 14%, „kurczak" jako główna nazwa wymaga min. 26%). |
| naming_percentage_notes | Notatki do reguły % | Dodatkowe komentarze i wyjaśnienia dotyczące weryfikacji reguły procentowej w nazwie produktu. |

## D.4 Oznakowanie prawne i identyfikacja

| Identyfikator | Opis | Wyjaśnienie |
|--------------|------|-------------|
| net_weight_e_symbol | Symbol ℮ przy masie netto | Sprawdza obecność symbolu ℮ (e-mark) obok deklaracji masy netto. Symbol ten oznacza, że producent gwarantuje zgodność ilości nominalnej z dyrektywą 76/211/EWG. |
| country_of_origin_stated | Kraj pochodzenia | Weryfikuje obecność informacji o kraju pochodzenia lub miejscu produkcji. |
| compliance_statement_present | Oświadczenie o zgodności | Sprawdza obecność oświadczenia o zgodności z obowiązującymi przepisami (np. „Karma pełnoporcjowa zgodna z rozporządzeniem (WE) nr 767/2009"). |
| establishment_approval_number | Numer zatwierdzenia zakładu | Weryfikuje obecność numeru zatwierdzenia zakładu produkcyjnego nadanego przez właściwy organ weterynaryjny (np. numer nadany przez PIW w Polsce). |
| date_marking_area_present | Strefa oznaczenia daty | Sprawdza, czy na etykiecie wyznaczono strefę przeznaczoną na nadruk daty ważności i/lub numeru partii (LOT). |

## D.5 GMO i składniki specjalne

| Identyfikator | Opis | Wyjaśnienie |
|--------------|------|-------------|
| gmo_declaration_required | Wymóg deklaracji GMO | Sprawdza, czy na podstawie składu produktu wymagana jest deklaracja dotycząca organizmów genetycznie zmodyfikowanych. |
| gmo_declaration_present | Obecność deklaracji GMO | Jeśli deklaracja jest wymagana — weryfikuje jej obecność na etykiecie. |
| gmo_notes | Uwagi GMO | Dodatkowe komentarze dotyczące statusu GMO składników. |
| contains_insect_protein | Zawiera białko owadzie | Wykrywa obecność białka owadziego w składzie (np. larwa Hermetia illucens, mączka z owadów). |
| insect_allergen_warning | Ostrzeżenie o alergenie (owady) | Sprawdza obecność ostrzeżenia o potencjalnej reakcji alergicznej u zwierząt uczulonych na białko owadzie (wymagane w przypadku obecności tego składnika). |
| irradiation_declared_if_applicable | Napromieniowanie | Weryfikuje obecność informacji o napromieniowaniu, jeśli którykolwiek ze składników został poddany napromieniowaniu jonizującemu. |

## D.6 Produkty surowe (raw)

| Identyfikator | Opis | Wyjaśnienie |
|--------------|------|-------------|
| is_raw_product | Produkt surowy | Wykrywa, czy produkt jest karmą surową (np. BARF, raw food). |
| raw_warning_present | Ostrzeżenia dla produktu surowego | Sprawdza obecność wymaganych ostrzeżeń dotyczących bezpieczeństwa przy obchodzeniu się z karmą surową (np. „Myć ręce po kontakcie", „Przechowywać oddzielnie od żywności"). |

## D.7 Wilgotność

| Identyfikator | Opis | Wyjaśnienie |
|--------------|------|-------------|
| moisture_declaration_required | Wymóg deklaracji wilgotności | Sprawdza, czy deklaracja wilgotności jest wymagana. Zgodnie z przepisami, deklaracja jest obowiązkowa, gdy wilgotność produktu przekracza 14%. |
| moisture_declaration_present | Obecność deklaracji wilgotności | Jeśli deklaracja jest wymagana — weryfikuje jej obecność na etykiecie. |

## D.8 Informacja o dodatkach i kontakt

| Identyfikator | Opis | Wyjaśnienie |
|--------------|------|-------------|
| free_contact_for_info | Bezpłatny kontakt do informacji o dodatkach | Sprawdza obecność bezpłatnego numeru kontaktowego lub adresu, pod którym konsument może uzyskać informację o dodatkach paszowych użytych w produkcie (wymóg Art. 19 rozporządzenia EU 767/2009). |

## D.9 Elementy wizualne i techniczne

| Identyfikator | Opis | Wyjaśnienie |
|--------------|------|-------------|
| recycling_symbols_present | Symbole recyklingu | Sprawdza obecność symboli informujących o sposobie segregacji i recyklingu opakowania (np. symbol Möbiusa, oznaczenia materiałowe). |
| barcode_visible | Kod kreskowy widoczny | Weryfikuje obecność i widoczność kodu kreskowego (EAN/UPC) na opakowaniu. |
| qr_code_visible | Kod QR | Sprawdza obecność kodu QR (element opcjonalny, ale coraz częściej wymagany przez sieci handlowe). |
| species_emblem_present | Emblemat gatunku | Weryfikuje obecność wizualnego oznaczenia gatunku docelowego (np. ikona psa, ikona kota) ułatwiającego identyfikację produktu na półce. |
| font_legibility_ok | Czytelność czcionki | Ocenia, czy czcionka użyta na etykiecie spełnia wymogi czytelności (minimalny rozmiar, kontrast z tłem). |
| font_legibility_notes | Uwagi dotyczące czytelności | Szczegółowe komentarze dotyczące wykrytych problemów z czytelnością tekstu. |

## D.10 Wersje językowe

| Identyfikator | Opis | Wyjaśnienie |
|--------------|------|-------------|
| translations_complete | Kompletność tłumaczeń | Sprawdza, czy wszystkie wymagane sekcje etykiety (skład, składniki analityczne, instrukcje, claimy) są przetłumaczone we wszystkich zadeklarowanych wersjach językowych. |
| country_codes_for_languages | Kody krajów przy sekcjach językowych | Weryfikuje obecność kodów krajów (np. PL, DE, FR) przy poszczególnych sekcjach językowych — ułatwiających identyfikację wersji językowej na etykiecie wielojęzycznej. |
| polish_language_complete | Kompletność tekstu polskiego | Szczegółowe sprawdzenie kompletności wersji polskojęzycznej — wszystkie obowiązkowe sekcje muszą mieć pełne tłumaczenie na język polski. |

## D.11 Pozostałe

| Identyfikator | Opis | Wyjaśnienie |
|--------------|------|-------------|
| packaging_notes | Notatki dodatkowe | Pole na dodatkowe uwagi i komentarze wykryte podczas kontroli opakowania, które nie pasują do żadnej z powyższych kategorii. Mogą dotyczyć np. nietypowego formatu opakowania, niestandarowego układu informacji lub innych obserwacji. |

## D.12 Podsumowanie

Checklista kontroli opakowania zawiera łącznie ponad 30 punktów sprawdzeń. Nie wszystkie punkty mają zastosowanie do każdego produktu — np. sprawdzenia dotyczące GMO, białka owadziego czy produktu surowego są aktywowane warunkowo, na podstawie zidentyfikowanego składu.

Wynik kontroli opakowania jest prezentowany w formie listy z oznaczeniem statusu każdego punktu:
- **Spełniony** — wymaganie jest obecne i poprawne.
- **Niespełniony** — wymaganie nie jest spełnione; wymaga korekty.
- **Nie dotyczy** — sprawdzenie nie ma zastosowania do danego produktu.
- **Wymaga weryfikacji manualnej** — aplikacja nie jest w stanie jednoznacznie ocenić tego elementu automatycznie; wymagana jest ocena człowieka.