# FEDIAF Verifier vs Neurons Predict vs GlobalVision

> Kompletne porownanie trzech narzedzi w ekosystemie opakowan karmy dla zwierzat.
> Stan na: marzec 2026.

---

## 1. Pozycjonowanie

| | **FEDIAF Verifier** | **Neurons Predict** | **GlobalVision** |
|---|---|---|---|
| **Glowne pytanie** | Czy etykieta jest regulacyjnie poprawna? | Czy konsument zauwazy co trzeba? | Czy artwork jest identyczny z zatwierdzonym masterem? |
| **Kategoria** | Regulatory compliance + QA | Neuromarketing / uwaga wizualna | Artwork proofing / QC |
| **Technologia bazowa** | LLM (Claude/Gemini/GPT) + deterministyczne reguly + OpenCV | AI eye-tracking prediction (180K uczestnikow) | OCR + pixel comparison + barcode engines |
| **Rynek docelowy** | Producenci karmy, zespoly regulacyjne | Brand managerowie, agencje kreatywne | Farma, FMCG, drukarnie |
| **Cennik** | Koszt API calls (~0.05-0.30 USD/analiza) | ~15K EUR/rok (Standard, 5 miejsc) | Enterprise, custom quotes |

---

## 2. Macierz funkcji

### 2.1 Weryfikacja regulacyjna

| Funkcja | FEDIAF Verifier | Neurons | GlobalVision |
|---|:---:|:---:|:---:|
| Weryfikacja FEDIAF 2021 (normy skladnikow) | **Tak** — deterministyczne progi per gatunek/faza zycia/typ karmy | Nie | Nie |
| EU 767/2009 (etykietowanie pasz) | **Tak** — pelna checklista 20+ elementow | Nie | Nie |
| Regula nazewnicza 4/14/26% | **Tak** — AI + reguły | Nie | Nie |
| Walidacja dodatkow paszowych (EU Register) | **Tak** — baza danych z EU Feed Additives Register | Nie | Nie |
| Oświadczenia vs skład | **Tak** — AI + post-check | Nie | Nie |
| Prezentacja handlowa (recepty, brand, IP) | **Tak** — 4-sekcyjna analiza | Nie | Nie |
| Zgodnos rynkowa per kraj (DE, FR, CZ, HU...) | **Tak** — 8+ rynkow | Nie | Czesciowo (generyczne reguly) |
| EU 1169/2011 (zywnosc dla ludzi) | Nie | Nie | **Tak** |
| FDA 21 CFR Part 11 audit trail | Nie | Nie | **Tak** |

**Werdykt:** FEDIAF Verifier jest **jedynym** narzedziem z trojki ktore rozumie regulacje karmy dla zwierzat. GlobalVision pokrywa compliance dla zywnosci/farma, ale nie pet food. Neurons nie robi compliance w ogole.

---

### 2.2 Analiza jezykowa i spell-check

| Funkcja | FEDIAF Verifier | Neurons | GlobalVision |
|---|:---:|:---:|:---:|
| Spell check | **Tak** — Hunspell (spylls) + AI crosscheck | Nie | **Tak** — AI, 42 jezyki |
| Liczba jezykow | 9 (PL, DE, FR, EN, IT, ES, CZ, HU, RO) | 0 | 42 |
| Slownik branzowy (pet food) | **Tak** — wbudowany whitelist | Nie | Mozliwy (custom dict) |
| Diakrytyki per jezyk | **Tak** — deterministyczna walidacja | Nie | Nie podane |
| Gramatyka / interpunkcja | **Tak** — AI | Nie | Czesciowo |
| Confidence scoring (AI vs Hunspell) | **Tak** — high/medium/low | N/A | Nie podane |

**Werdykt:** GlobalVision ma wieksza szerokosc jezykow (42 vs 9). FEDIAF Verifier ma **glebsza** analize per jezyk (diakrytyki, terminologia pet food, crosscheck AI vs Hunspell).

---

### 2.3 Artwork inspection / proofing

| Funkcja | FEDIAF Verifier | Neurons | GlobalVision |
|---|:---:|:---:|:---:|
| Porownanie pikseli (diff) | **Tak** — SSIM + OpenCV | Nie | **Tak** — natywne, 30 lat rozwoju |
| Analiza kolorow / Delta E | **Tak** — CIE2000 | Nie | **Tak** + Pantone integration |
| Barcode/QR walidacja | **Tak** — check digit + kraj | Nie | **Tak** — ANSI/CEN/ISO grading |
| Barcode grading (kontrast, quiet zone) | Nie | Nie | **Tak** |
| Braille | Nie | Nie | **Tak** — 44 jezyki |
| Print readiness (DPI, CMYK, bleed, fonty) | **Tak** | Nie | **Tak** |
| ICC profil | **Tak** (PDF) | Nie | **Tak** |
| OCR porownanie tekstu | **Tak** — EasyOCR (opcjonalnie) | Nie | **Tak** — natywne |
| Min. font size check | Czesciowo (AI) | Nie | **Tak** — deterministyczny |
| Batch processing | Nie | Nie | **Tak** |
| API do integracji workflow | Nie (Streamlit UI) | **Tak** | **Tak** (Verify API) |

**Werdykt:** GlobalVision jest **liderem** artwork proofing — Braille, barcode grading, Pantone, batch, API, 30 lat doswiadczenia. FEDIAF Verifier pokrywa ~70% use cases ale na mniejszej glebokosci. Neurons nie robi proofingu.

---

### 2.4 Uwaga wizualna / neuromarketing

| Metryka | FEDIAF Verifier | Neurons | GlobalVision |
|---|:---:|:---:|:---:|
| Heatmapa uwagi | **Tak** — DeepGaze IIE lub heurystyka | **Tak** — wlasny model (95%+ korelacja z eye-tracking) | Nie |
| Focus Score | **Tak** — entropy histogram + Gini + cluster count | **Tak** — naukowy, walidowany | Nie |
| Clarity Score | **Tak** — edge density + color complexity + whitespace + symmetry | **Tak** — beta, EEG-validated | Nie |
| Cognitive Load | **Tak** — FFT freq analysis + element count + edge density + color diversity | **Tak** — EEG-validated | Nie |
| Engagement Score | Nie | **Tak** — beta | Nie |
| Areas of Interest (AOI) | Czesciowo (top 8 regionow automatycznie) | **Tak** — dowolne ksztalty, Time Spent, % Seen | Nie |
| Brand tracking | Czesciowo (brand_attention_pct) | **Tak** — automatyczna detekcja logo, CTA, twarzy | Nie |
| Industry benchmarks | **Tak** — 8 segmentow x 10 kategorii, samoučace | **Tak** — tysiace real packagingow | Nie |
| Video analysis | Nie | **Tak** | Nie |

**Werdykt:** Neurons jest **zdecydowanym liderem** — model walidowany na 180K uczestnikach eye-tracking/EEG z 95%+ korelacja. FEDIAF Verifier oferuje **heurystyczne aproksymacje** (uczciwie oznaczone w UI). Szczegolowe porownanie metryk ponizej.

---

### 2.5 Generowanie tresci

| Funkcja | FEDIAF Verifier | Neurons | GlobalVision |
|---|:---:|:---:|:---:|
| Generowanie tekstu etykiety | **Tak** — pelne sekcje regulacyjne | Nie | Nie |
| Opis e-commerce (SEO, HTML) | **Tak** — z walidacja claimow | Nie | Nie |
| Tlumaczenie etykiet | **Tak** | Nie | Nie |
| Analiza designu (AI) | **Tak** — 10 kategorii, 0-100 per kategoria | Nie | Nie |

**Werdykt:** Unikalna funkcjonalnosc FEDIAF Verifier — zaden z konkurentow nie generuje tresci.

---

## 3. Glebokie porownanie metryk wizualnych

### 3.1 Focus Score

| Aspekt | FEDIAF Verifier | Neurons Predict |
|---|---|---|
| **Metoda** | Entropia 256-bin histogramu mapy saliency (0.4) + wspolczynnik Gini (0.3) + liczba klastrow uwagi (0.3) | Predykcja eye-tracking z modelu AI wytrenowanego na 180K uczestnikach |
| **Baza naukowa** | Entropia Shannona (teoria informacji), Gini (ekonometria), connected components (CV) | Rzeczywiste dane eye-tracking, walidowane na MIT1003 i innych benchmarkach |
| **Resolution-independence** | Tak — histogram 256-binowy, max_entropy = 8.0 niezaleznie od rozdzielczosci | Tak — model operuje na feature maps |
| **Walidacja** | Brak walidacji na ludziach | 95%+ korelacja z real eye-tracking |
| **Ograniczenia** | Heurystyka obrazowa — nie uwzglednia semantyki (tekst vs zdjecie), kontekstu kulturowego, znajomosci marki | Bias ku centrum, moze nie odzwierciedlac specyficznych populacji |

### 3.2 Clarity Score

| Aspekt | FEDIAF Verifier | Neurons Predict |
|---|---|---|
| **Metoda** | Edge density Canny (0.30) + K-means color complexity (0.25) + whitespace ratio HSV (0.25) + L/R symmetry Pearson (0.20) | Model AI walidowany na danych EEG (beta) |
| **Baza naukowa** | Rosenholtz visual clutter research (2005+), Gestalt principles | Dane EEG — bezposredni pomiar aktywnosci mozgu |
| **Co mierzy** | Porzadek wizualny: mniej krawedzi, mniej kolorow, wiecej bieli, wiecej symetrii = wyzszy score | Subiektywna percepcja czytelnosci — czy ludzie *czuja* ze design jest czysty |
| **Edge cases** | K-means clampowany do min(8, N) pikseli. Symetria guard na obrazy <4px szerokosci | Nie podane publicznie |

### 3.3 Cognitive Load

| Aspekt | FEDIAF Verifier | Neurons Predict |
|---|---|---|
| **Metoda** | FFT high-freq energy (0.30) + element count kontury (0.25) + edge density (0.25) + hue diversity histogram (0.20). FFT downsampled do max 1024px | Model AI walidowany na EEG cognitive load measurements |
| **Baza naukowa** | Analiza czestotliwosciowa (Fourier), wizualna zlozonosc (Mack & Oliva 2004) | Rzeczywiste pomiary EEG potencjalow P300/N400 |
| **Co mierzy** | Zlozonosc obrazowa: drobne detale, duzo elementow, roznorodnosc kolorow = wysoki load | Faktyczny wysilek mentalny przy przetwarzaniu — ile mózg "pracuje" |
| **Skala** | 0-100 (wysoki = trudny), odwrocony jako "latwosc przetwarzania" w UI | 0-100 (walidowany na EEG) |

### 3.4 Benchmarki branzowe

| Aspekt | FEDIAF Verifier | Neurons Predict |
|---|---|---|
| **Zrodlo danych** | Statyczne baseline'y (szacunek domenowy) + JSON persistence — po 20+ analizach przechodzi na realne percentyle z wlasnych uzytkownikow | Tysiace real packagingow z bazy Neurons |
| **Segmenty** | 8: premium_dry, economy_dry, premium_wet, economy_wet, treats, supplements, barf_raw, veterinary | Per-industry (food, beverage, beauty, etc.), per-platform |
| **Kategorie** | 10: visual_hierarchy, readability, color_usage, layout_composition, regulatory_placement, shelf_impact, imagery, target_audience, sustainability, multilanguage_layout | Focus, Clarity, Cognitive Demand, Engagement + per-AOI metryki |
| **Wizualizacja** | Radar chart (plotly) + tabela z percentylami | Dashboard z porownaniem vs normy branzowe |
| **Cold start** | Statyczne szacunki do czasu zebrania 20 analiz per segment/kategoria | Brak problemu — gotowa baza |

---

## 4. Architektura techniczna

| Warstwa | FEDIAF Verifier | Neurons | GlobalVision |
|---|---|---|---|
| **Backend** | Python 3.12+, Pydantic v2 | Cloud SaaS | Cloud SaaS + On-premise |
| **AI** | Claude Sonnet 4.6 / Gemini / GPT (multi-provider) | Wlasny model neuroscience | Wlasne OCR/CV engines |
| **Image processing** | OpenCV, scikit-image, Pillow, numpy FFT | Wlasne | Wlasne |
| **Saliency model** | DeepGaze IIE (opcjonalnie, ~800MB) lub heurystyka fallback | Wlasny (95%+ accuracy) | N/A |
| **OCR** | EasyOCR (opcjonalnie, ~200MB) | N/A | Wlasne |
| **Spell check** | Hunspell via spylls (9 jezykow) | N/A | Wlasne AI (42 jezyki) |
| **PDF** | PyMuPDF (opcjonalnie, ~30MB) | N/A | Wlasne |
| **UI** | Streamlit (web) | Web app + Figma plugin + Chrome extension | Desktop + Web + API |
| **API** | Brak (tylko UI) | Tak | Tak (Verify API) |
| **Deployment** | Self-hosted (pip install) | Cloud | Cloud + On-premise |
| **Multi-user** | Nie (single session) | Tak (team plans) | Tak (enterprise) |

---

## 5. Niezawodnosc i walidacja

| Aspekt | FEDIAF Verifier | Neurons | GlobalVision |
|---|---|---|---|
| **Anty-halucynacje** | 5 warstw: confidence scoring, cross-check (double AI read), Hunspell crosscheck, deterministyczne reguly, self-reflection | N/A (nie generuje tresci) | N/A (deterministyczne porownanie) |
| **Deterministyczna baza** | Tak — FEDIAF reguly, EAN check digit, Hunspell, Delta E, SSIM sa 100% deterministyczne | Nie — calosc AI | Tak — pixel comparison, barcode grading |
| **False positive rate** | Nieznany (brak publicznej walidacji), ale cross-check redukuje | Publikowane: 95%+ korelacja z eye-tracking | Publikowane: 100% detection accuracy (G2/Capterra) |
| **Audit trail** | Nie | Nie | Tak (FDA 21 CFR Part 11) |
| **Walidacja na ludziach** | Brak (metryki wizualne sa heurystykami) | 180K uczestnikow | 30 lat produkcji |

---

## 6. Mocne strony i slabosci

### FEDIAF Verifier

| Mocne strony | Slabosci |
|---|---|
| Jedyne narzedzie z regulacja pet food (FEDIAF + EU 767/2009) | Brak API — tylko Streamlit UI |
| Generowanie tresci (tekst etykiety, e-commerce, tlumaczenia) | Metryki wizualne to heurystyki, nie neuroscience |
| Multi-provider AI (Claude/Gemini/GPT) | Spell check: 9 jezykow vs 42 (GlobalVision) |
| 5-warstwowy system anty-halucynacyjny | Brak Braille, barcode grading ANSI/CEN/ISO |
| Koszt ~0.05-0.30 USD/analiza | Brak audit trail |
| Self-hosted, pelna kontrola danych | Single user, brak multi-tenancy |
| Graceful degradation (opcjonalne ciezkie deps) | Benchmarki startuja od szacunkow (cold start) |
| Samoučace benchmarki (poprawiaja sie z uzyciem) | Brak walidacji metryk na prawdziwych uzytkownikach |

### Neurons Predict

| Mocne strony | Slabosci |
|---|---|
| 95%+ korelacja z real eye-tracking | Zero compliance / regulacji |
| EEG-validated Clarity i Cognitive Load | Nie weryfikuje poprawnosci tresci |
| Ogromna baza benchmarkow | ~15K EUR/rok |
| Figma plugin, Chrome extension, API | Brak spell check, barcode, Braille |
| Video analysis | Bias demograficzny (dane glownie z zachodnich populacji) |
| Areas of Interest z Time Spent / % Seen | Nie pokrywa pet food jako branza |

### GlobalVision

| Mocne strony | Slabosci |
|---|---|
| 30 lat artwork proofing | Nie robi regulacji pet food |
| Braille 44 jezyki | Nie robi uwagi wizualnej |
| Barcode grading ANSI/CEN/ISO | Enterprise pricing |
| Pantone color inspection | Memory-intensive |
| FDA 21 CFR Part 11 audit trail | Nie generuje tresci |
| Spell check 42 jezyki | Wymaga zatwierdzonego mastera do porownania |
| Batch processing + API | Nie robi analizy designu |

---

## 7. Kiedy uzyc ktorego narzedzia

| Scenariusz | Najlepsze narzedzie | Dlaczego |
|---|---|---|
| "Czy etykieta spelnia FEDIAF i EU 767/2009?" | **FEDIAF Verifier** | Jedyne z trojki |
| "Czy skladniki i claimy sa spojne?" | **FEDIAF Verifier** | Jedyne z trojki |
| "Wygeneruj tekst etykiety / opis e-commerce" | **FEDIAF Verifier** | Jedyne z trojki |
| "Czy artwork pasuje do zatwierdzonego mastera?" | **GlobalVision** | 30 lat, pixel-perfect, batch, Braille |
| "Czy barcode ma poprawny grading?" | **GlobalVision** | ANSI/CEN/ISO certification |
| "Czy konsumenci zauważa brand na polce?" | **Neurons** | 95%+ accuracy eye-tracking |
| "Ktory z 3 wariantow designu lepiej przyciaga uwage?" | **Neurons** | A/B z naukowymi metrykami |
| "Ogolna kontrola jakosci etykiety" | **FEDIAF Verifier** | Najszersza pokrycie (compliance + design + artwork + linguistic) |
| "Audit trail dla FDA/regulatora" | **GlobalVision** | 21 CFR Part 11 |
| "Szybki check designu z benchmarkiem" | **FEDIAF Verifier** | Radar chart + benchmarki per segment |
| "Professional pre-press QC" | **GlobalVision** | Batch, Pantone, fonty, bleed |

---

## 8. Kluczowy wniosek

Te trzy narzedzia **nie konkuruja ze soba bezposrednio**. Pokrywaja rozne etapy workflow:

```
1. FEDIAF Verifier  →  "Czy TRESC etykiety jest poprawna?"    (compliance + content)
2. GlobalVision     →  "Czy ARTWORK wiernie odwzorowuje tresc?" (proofing + QC)
3. Neurons Predict  →  "Czy KONSUMENT zauważy co trzeba?"       (perception + neuro)
```

FEDIAF Verifier zajmuje **nisze, ktorej zaden z konkurentow nie pokrywa** — weryfikacje regulacyjna karmy dla zwierzat. Jednoczesnie oferuje "good enough" wersje funkcji artworkowych i wizualnych, ktore u konkurentow sa core business.

Realnym zagrozeniem nie sa Neurons/GlobalVision, tylko ewentualny produkt budowany **bezposrednio pod FEDIAF compliance** — na razie takiego nie ma na rynku.

---

## 9. Uczciwosc metryk wizualnych

Nasze metryki Focus/Clarity/Cognitive Load sa **heurystykami obrazowymi**, nie neuroscience:

| Metryka | Nasza metoda | Naukowa podstawa | Korelacja z percepcja | Oznaczenie w UI |
|---|---|---|---|---|
| Focus | Entropy + Gini + clusters | Teoria informacji, ekonometria | Umiarkowana (brak walidacji) | "estymacja heurystyczna" |
| Clarity | Edge density + colors + whitespace + symmetry | Rosenholtz visual clutter (2005) | Umiarkowana-dobra (akademickie papers) | "estymacja heurystyczna" |
| Cognitive Load | FFT + elements + edges + hue diversity | Fourier analysis, Mack & Oliva (2004) | Umiarkowana (brak bezposredniej walidacji EEG) | "estymacja heurystyczna" |
| Benchmarki | Statyczne szacunki + samoučenie | Ekspertyza domenowa | Poprawia sie z uzyciem | Pokazany zrodlo (static/real) |

To jak porownanie termometru IR za 50 zl vs termokamery FLIR za 50K — oba mierza, ale na roznym poziomie dokladnosci.

---

*Dokument wygenerowany na podstawie audytu kodu zrodlowego FEDIAF Verifier, publicznych informacji o Neurons Predict (neuronsinc.com) i GlobalVision (globalvision.co), oraz recenzji G2/Capterra/TrustRadius.*
