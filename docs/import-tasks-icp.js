/**
 * Import zadań BULT QA do IC Project
 *
 * Użycie:
 *   1. Uzupełnij API_KEY i INSTANCE_SLUG poniżej
 *   2. Uzupełnij BOARD_COLUMN_ID (kolumna "Zrobione")
 *   3. Uruchom: node docs/import-tasks-icp.js
 *
 * Jak znaleźć dane:
 *   - API_KEY:          IC Project → Ustawienia → Integracje → API → Klucz API
 *   - INSTANCE_SLUG:    fragment URL, np. app.icproject.com/instance/TUTAJ/...
 *   - BOARD_COLUMN_ID:  otwórz tablicę Kanban, kliknij "..." przy kolumnie "Zrobione",
 *                        lub pobierz listę kolumn przez API (skrypt wyświetli je jeśli
 *                        BOARD_COLUMN_ID zostawisz pusty)
 */

// ===================== UZUPEŁNIJ TUTAJ =====================
const API_KEY = '31fdaeb1-b850-4600-bcd9-548e5365bde2';           // np. 'abc123...'
const INSTANCE_SLUG = 'e70a1c';     // np. 'moja-firma'
const BOARD_COLUMN_ID = '';   // np. 'col_xyz' — zostaw puste, aby pobrać listę kolumn
// ===========================================================

const https = require('https');
const crypto = require('crypto');

const BASE = `https://app.icproject.com/api/instance/${INSTANCE_SLUG}`;

const TASKS = [
  {
    name: 'Inicjalizacja projektu i fundament aplikacji',
    description:
      'Utworzenie repozytorium, struktury projektu, konfiguracji.\n' +
      'Fundament: moduł weryfikacji, prompty AI, modele danych (Product, Nutrients, Report, Issues, EU Labelling, Cross-Check, Linguistic), eksport raportów, konwerter plików, interfejs Streamlit z trybem pełnej weryfikacji, reguły FEDIAF z progami żywieniowymi, testy jednostkowe, Dev Container.',
    dateStart: '2026-03-17',
    dateEnd: '2026-03-17',
    priority: 'high',
  },
  {
    name: 'Silnik compliance + multi-provider AI + Docker',
    description:
      'Deterministyczny silnik compliance: scoring 0-100, status COMPLIANT/REQUIRES_REVIEW/NON_COMPLIANT, model ekstrakcji danych, 30+ kontroli opakowania.\n' +
      'Abstrakcja multi-provider AI (Claude / Gemini / GPT).\n' +
      'Konteneryzacja Docker, reverse proxy Caddy, konfiguracja Streamlit.',
    dateStart: '2026-03-18',
    dateEnd: '2026-03-18',
    priority: 'high',
  },
  {
    name: '8 nowych trybów + eksporty JSX + renderery raportów',
    description:
      'Nowe tryby: Kontrola struktury i czcionki, Analiza designu, Tłumaczenie etykiety, Walidator claimów, Walidator EAN/kodów, Walidator rynkowy (14 krajów), Generator tekstu etykiety, Porównanie wersji.\n' +
      'Annotator PDF, generator skryptów JSX dla Adobe Illustrator.\n' +
      'Renderery raportów — wizualizacja wyników dla każdego trybu.',
    dateStart: '2026-03-19',
    dateEnd: '2026-03-19',
    priority: 'high',
  },
  {
    name: 'Optymalizacja promptów AI + zbieranie danych treningowych',
    description:
      'Tuning i optymalizacja promptów AI dla wszystkich trybów.\n' +
      'Moduł zbierania danych treningowych do przyszłego fine-tuningu.\n' +
      'Poprawki konwertera plików i providerów AI.',
    dateStart: '2026-03-20',
    dateEnd: '2026-03-20',
    priority: 'normal',
  },
  {
    name: 'Generator opisów e-commerce + spellcheck + artwork + benchmarki',
    description:
      'Generator opisów produktów (4 style tonalne, SEO, HTML, walidacja claimów).\n' +
      'Spellcheck Hunspell (9 języków) z detekcją OCR confusion.\n' +
      'Inspekcja artwork (SSIM, K-means, Delta E, DPI, ICC, saliency).\n' +
      'System benchmarków designu (8 segmentów × 10 kategorii).\n' +
      'Weryfikator prezentacji handlowej, manager rozszerzeń opcjonalnych.\n' +
      'Analiza konkurencyjna vs Neurons Predict i GlobalVision.',
    dateStart: '2026-03-23',
    dateEnd: '2026-03-23',
    priority: 'high',
  },
  {
    name: 'Spellcheck cross-validation + targeted re-read + testy',
    description:
      'Integracja Hunspell z AI: cross-walidacja (3 poziomy pewności).\n' +
      'Targeted re-read — ponowny odczyt słów z obrazu (eliminacja fałszywych alarmów OCR).\n' +
      'Self-verify (reflection step) — AI weryfikuje własne wyniki.\n' +
      'Rozbudowa compliance engine, testy konwertera.',
    dateStart: '2026-03-24',
    dateEnd: '2026-03-24',
    priority: 'normal',
  },
  {
    name: 'Podręcznik użytkownika dla Marketingu i R&D',
    description:
      'Kompletny podręcznik (docs/USER_MANUAL.md, 2291 linii):\n' +
      '10 rozdziałów + 4 załączniki, opis 13 trybów, słownik ~50 pojęć, FAQ, wskazówki workflow per dział, tabele FEDIAF, EU 767/2009, 14 krajów, 30+ kontroli opakowania.\n' +
      'Weryfikacja vs kod źródłowy — wszystkie nazwy UI, progi, kraje, języki, eksporty zgodne.',
    dateStart: '2026-03-25',
    dateEnd: '2026-03-25',
    priority: 'normal',
  },
];

// --- HTTP helper ---
function apiCall(method, path, body) {
  return new Promise((resolve, reject) => {
    const url = new URL(BASE + path);
    const data = body ? JSON.stringify(body) : null;
    const opts = {
      hostname: url.hostname,
      path: url.pathname + url.search,
      method,
      headers: {
        'X-Auth-Token': API_KEY,
        Accept: 'application/json',
        ...(data ? { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(data) } : {}),
      },
    };
    const req = https.request(opts, (res) => {
      let chunks = '';
      res.on('data', (c) => (chunks += c));
      res.on('end', () => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          try { resolve(JSON.parse(chunks)); } catch { resolve(chunks); }
        } else {
          reject(new Error(`HTTP ${res.statusCode}: ${chunks}`));
        }
      });
    });
    req.on('error', reject);
    if (data) req.write(data);
    req.end();
  });
}

async function main() {
  if (!API_KEY || !INSTANCE_SLUG) {
    console.error('❌ Uzupełnij API_KEY i INSTANCE_SLUG na górze skryptu.');
    process.exit(1);
  }

  if (!BOARD_COLUMN_ID) {
    console.log('ℹ️  BOARD_COLUMN_ID jest pusty — próbuję pobrać listę projektów i kolumn...\n');
    try {
      const projects = await apiCall('GET', '/project/projects');
      const list = projects.data || projects;
      if (Array.isArray(list)) {
        for (const p of list.slice(0, 10)) {
          console.log(`Projekt: "${p.name}" (id: ${p.id || p.identifier})`);
          if (p.boardColumns) {
            for (const col of p.boardColumns) {
              console.log(`   Kolumna: "${col.name}" → ID: ${col.id || col.identifier}`);
            }
          }
        }
      } else {
        console.log('Odpowiedź API:', JSON.stringify(list, null, 2).slice(0, 2000));
      }
    } catch (e) {
      console.error('Błąd pobierania projektów:', e.message);
    }
    console.log('\n→ Wklej odpowiedni ID kolumny "Zrobione" do BOARD_COLUMN_ID i uruchom ponownie.');
    process.exit(0);
  }

  console.log(`Tworzę ${TASKS.length} zadań w IC Project (kolumna: ${BOARD_COLUMN_ID})...\n`);

  for (const task of TASKS) {
    try {
      const body = {
        identifier: crypto.randomUUID(),
        boardColumn: BOARD_COLUMN_ID,
        name: task.name,
        description: task.description,
        dateStart: task.dateStart,
        dateEnd: task.dateEnd,
        priority: task.priority,
      };
      await apiCall('POST', '/project/tasks', body);
      console.log(`✅ ${task.dateStart} | ${task.name}`);
    } catch (e) {
      console.error(`❌ ${task.name}: ${e.message}`);
    }
  }

  console.log('\nGotowe!');
}

main();
