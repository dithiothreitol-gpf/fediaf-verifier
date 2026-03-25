# IC Project Sync

Synchronizuj bieżący projekt z IC Project — twórz projekty, etapy, tablice, kolumny i zadania na podstawie historii git i stanu repozytorium.

## Konfiguracja

Dane IC Project są w pliku `~/.claude/icp-config.json`:
```json
{
  "apiKey": "...",
  "instanceSlug": "..."
}
```

Jeśli plik nie istnieje, zapytaj użytkownika o API Key i Instance Slug, a następnie zapisz je do tego pliku.

## Argumenty

Użytkownik może podać argumenty po `/icp-sync`:
- Bez argumentów — interaktywny tryb, pytaj co zrobić
- `$ARGUMENTS` — opis tego, co użytkownik chce zrobić

## Co potrafisz

### 1. Założyć projekt
- Utwórz projekt w IC Project przez `POST /project/projects` z polami: `identifier` (UUID), `name`, `status: "open"`, `dateStart`, `dateEnd`, `isBlameableRemovalEnabled: false`
- Nazwa projektu: zapytaj użytkownika lub użyj nazwy z `package.json` / `pyproject.toml` / nazwy katalogu

### 2. Zdefiniować etapy (stages)
- Utwórz etapy przez `POST /project/stages` z polami: `identifier`, `project` (ID projektu), `name`, `status: "open"`, `dateStart`, `dateEnd`, `isBlameableRemovalEnabled: false`
- Domyślne etapy: "Development", "Testing", "Release" — lub zapytaj użytkownika

### 3. Utworzyć tablicę z kolumnami
- Tablica: `POST /project/boards` z polami: `identifier`, `stage` (ID etapu), `name`, `status: "open"`, `dateStart`, `dateEnd`, `isBlameableRemovalEnabled: false`
- Kolumny: `POST /project/board-columns` z polami: `identifier`, `board` (ID tablicy), `name`, `status` (`todo`/`in-progress`/`done`), `decorator` (kolor Material Design: `#d32f2f` todo, `#f57f17` in-progress, `#00bfa5` done)

### 4. Tworzyć/aktualizować zadania
- Utwórz zadania: `POST /project/tasks` z polami: `identifier` (UUID), `boardColumn` (ID kolumny), `name`, `description`, `dateStart` (ISO 8601), `dateEnd` (ISO 8601), `priority` (`low`/`normal`/`high`/`critical`)
- Źródło danych dla zadań: historia git (`git log`), struktura plików, lub opis użytkownika
- Kolumna docelowa: zapytaj użytkownika (Do zrobienia / W trakcie / Zrobione)

## API Details

**Base URL:** `https://app.icproject.com/api/instance/{INSTANCE_SLUG}`

**Headers:**
```
X-Auth-Token: {API_KEY}
Accept: application/json
Content-Type: application/json
```

**Endpointy:**
- `GET /project/projects` — lista projektów
- `GET /project/projects/{id}` — szczegóły projektu
- `GET /project/projects/{id}/stages` — etapy projektu
- `GET /project/boards/{id}/tasks` — zadania tablicy
- `POST /project/projects` — utwórz projekt
- `POST /project/stages` — utwórz etap
- `POST /project/boards` — utwórz tablicę
- `POST /project/board-columns` — utwórz kolumnę
- `POST /project/tasks` — utwórz zadanie

**Pola wymagane przy tworzeniu:**
- Projekt: `identifier`, `name`, `status`, `dateStart`, `dateEnd`, `isBlameableRemovalEnabled`
- Etap: `identifier`, `project`, `name`, `status`, `dateStart`, `dateEnd`, `isBlameableRemovalEnabled`
- Tablica: `identifier`, `stage`, `name`, `status`, `dateStart`, `dateEnd`, `isBlameableRemovalEnabled`
- Kolumna: `identifier`, `board`, `name`, `status` (todo/in-progress/done), `decorator` (hex color z palety Material Design)
- Zadanie: `identifier`, `boardColumn`, `name`, `description`, `dateStart`, `dateEnd`, `priority`

## Instrukcje

1. Wczytaj konfigurację z `~/.claude/icp-config.json`. Jeśli brak — zapytaj użytkownika i zapisz.
2. Wszystkie wywołania API rób przez Bash z `node -e` (używaj `https` module, `crypto.randomUUID()`).
3. Przed utworzeniem sprawdź czy projekt/etap/tablica już istnieje (GET + szukanie po nazwie).
4. Zawsze potwierdzaj z użytkownikiem zanim utworzysz cokolwiek — wyświetl plan i zapytaj.
5. Po utworzeniu wyświetl podsumowanie z linkami do IC Project.
6. Daty zadań ustalaj na podstawie `git log` (daty commitów dodających pliki) — nie wymyślaj dat.
7. Opisy zadań powinny być na wysokim poziomie ogólności, nietechniczne, zrozumiałe dla PM-a.
8. Identyfikatory (UUID) generuj przez `crypto.randomUUID()`.
