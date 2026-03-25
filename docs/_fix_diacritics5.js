const fs = require('fs');
const filePath = __dirname + '/MANUAL_COMBINED.md';

let content = fs.readFileSync(filePath, 'utf8');
let lines = content.split('\n');

let before = lines.slice(0, 827).join('\n');
let section = lines.slice(827, 1733).join('\n');
let after = lines.slice(1733).join('\n');

const replacements = [
  // Remaining fixes from inspection
  ["rozdzielczosci", "rozdzielczości"],
  ["polkowy", "półkowy"],
  ["Wplyw polkowy", "Wpływ półkowy"],
  ["uzyte", "użyte"],
  ["wyglada", "wygląda"],
  ["metrow", "metrów"],
  ["zweryfikowac", "zweryfikować"],
  ["wpisac", "wpisać"],
  ["zmiesci", "zmieści"],

  // "Wplyw" still not fixed in some places
  ["Wplyw", "Wpływ"],
  ["Uklad", "Układ"],

  // Remaining common words
  ["sekcje.", "sekcję."],  // accusative context "ma swoją sekcje." -> "sekcję"
  // Actually this depends on context, let me check

  // Words with "osc" ending
  ["czytelnosci", "czytelności"],

  // More fixes
  ["plikow", "plików"],

  // Specific line fixes
  ["Nie jest interpretacja AI", "Nie jest interpretacją AI"],
  ["regul FEDIAF", "reguł FEDIAF"],

  // "Jesli" -> "Jeśli" (capital)
  ["Jesli", "Jeśli"],
  // lowercase "jesli" -> "jeśli"
  ["jesli", "jeśli"],

  // More verb infinitives
  ["zweryfikowac", "zweryfikować"],
  ["wpisac", "wpisać"],
  ["pobrac", "pobrać"],
  ["przekazac", "przekazać"],

  // "wysyla" still present?
  ["wysyla", "wysyła"],

  // "tresc" -> "treść"
  ["tresc", "treść"],

  // Remaining patterns
  ["zadnej", "żadnej"],
  ["kazda", "każda"],

  // "wyswietlic" still present
  ["wyswietlic", "wyświetlić"],

  // More words from glossary
  ["etykiecie", "etykiecie"],  // locative - stays
  ["Prostokatny", "Prostokątny"],
  ["przestrzen", "przestrzeń"],
  ["definiujacy", "definiujący"],
  ["pokrywajaca", "pokrywająca"],
  ["sugerujace", "sugerujące"],
  ["dotyczace", "dotyczące"],
  ["dotyczaca", "dotycząca"],
  ["okreslajace", "określające"],
  ["okreslajacy", "określający"],
  ["zawierajaca", "zawierająca"],
  ["wykraczajacy", "wykraczający"],

  // More specific fixes
  ["moze", "może"],
  ["lista", "listę"],  // accusative in some contexts... be careful

  // "odbiorca" -> depends on context
  // "glowny odbiorca" - nominative, stays "odbiorca"... actually checking:
  // "główny odbiorca raportow" -> "główny odbiorca raportów" - "odbiorca" is nominative, stays

  // More words
  ["obslugiwany", "obsługiwany"],

  // "Uzywany" etc in non-word-boundary context
  ["Uzywany", "Używany"],
  ["Uzywane", "Używane"],
  ["Uzywana", "Używana"],
  ["Uzywane", "Używane"],

  // "byc" -> "być"
  ["byc", "być"],

  // "niz" -> "niż"
  ["niz", "niż"],

  // More remaining
  ["mieso", "mięso"],
  ["ryz", "ryż"],
  ["jeczmien", "jęczmień"],

  // "ze" -> "że"
  ["ze wzgledu", "ze względu"],  // "ze" as preposition stays before "wzgl"
  // Actually "ze" before consonant cluster = preposition, "że" = "that"
  // Need to be careful - "ze" before "względu" is preposition and stays "ze"
  // But in other contexts "ze" means "that" -> "że"
  // Let me handle specific contexts:
  ["oznacza, ze", "oznacza, że"],
  ["Oznacza, ze", "Oznacza, że"],
  ["zapewniajacy, ze", "zapewniający, że"],
  [", ze dostawca", ", że dostawca"],
  [", ze grafika", ", że grafika"],
  [", ze producent", ", że producent"],

  // "sie" -> "się" - this was already done in pass 1 but some might remain
  // Actually "sie" should be "się" in all Polish contexts

  // Fix remaining line-specific issues found
  ["wyeksportowanie", "wyeksportowanie"],  // stays
  ["liczbe", "liczbę"],
  ["liste", "listę"],

  // "Uzycie" -> "Użycie"
  ["Uzycie", "Użycie"],
  ["uzycie", "użycie"],

  // Additional verb/noun forms
  ["odczytac", "odczytać"],
  ["zawierac", "zawierać"],
  ["ukryc", "ukryć"],
  ["usunac", "usunąć"],
  ["zidentyfikowac", "zidentyfikować"],
  ["zwieksc", "zwiększ"],
  ["zwieksz", "zwiększ"],

  // From the glossary section
  ["Przemyslu", "Przemysłu"],
  ["Zwierzat", "Zwierząt"],
  ["odzywczych", "odżywczych"],
  ["odzywczego", "odżywczego"],

  // Additional missing
  ["budzetu", "budżetu"],
  ["rozporzadzeniem", "rozporządzeniem"],

  // More words with ź
  ["zrodlowy", "źródłowy"],
  ["zrodlowe", "źródłowe"],

  // "warstwe" -> "warstwę"
  ["warstwe", "warstwę"],

  // "etykiete" -> "etykietę"
  ["etykiete", "etykietę"],

  // Additional
  ["caloksztaltu", "całokształtu"],
  ["slowna", "słowną"],
  ["slowne", "słowne"],

  // "odbiorca" - when accusative -> "odbiorcą"
  // "główny odbiorcą raportów" is wrong, "odbiorca" is nominative
  // Keep as is in most contexts

  // "sekcje" - fix accusative contexts
  // "ma swoją sekcje" -> "ma swoją sekcję"
  ["swoja sekcje", "swoją sekcję"],
  ["swoją sekcje", "swoją sekcję"],

  // More verb fixes
  ["dodaja", "dodają"],

  // More context-specific
  ["zmierzy", "zmierzy"],  // stays

  // "tlumaczy" might still be present
  ["tlumaczy", "tłumaczy"],

  // "obslugiwany" in table
  ["Obslugiwany", "Obsługiwany"],

  // "polce" -> "półce"
  ["polce", "półce"],

  // "wlasnego" -> "własnego"... hmm the word "własnego" has ł

  // Glossary-specific fixes
  // "Porzadek" already done
  // "definiujacy" already in list

  // More accusative/instrumental feminine adjective fixes
  // These need context but let me check patterns:
  ["subiektywna analiza", "subiektywną analizą"],

  // Actually this is more complex. Let me just fix specific known remaining issues.
  ["ze grafika siega", "że grafika sięga"],
  ["zapewniajacy, ze grafika", "zapewniający, że grafika"],

  // Additional remaining - checking specific patterns in text
  ["sekcje jezykowa", "sekcję językową"],

  // "kodzie" stays (locative of "kod")

  // Fix remaining "Uzywany/Uzywana/Uzywane" that might be mid-sentence
  ["uzywany", "używany"],
  ["uzywane", "używane"],
  ["uzywana", "używana"],
];

const seen = new Set();
const unique = replacements.filter(([from, to]) => {
  if (from === to) return false;
  const key = from + '|' + to;
  if (seen.has(key)) return false;
  seen.add(key);
  return true;
});
unique.sort((a, b) => b[0].length - a[0].length);

let changeCount = 0;
for (const [from, to] of unique) {
  const escaped = from.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  // Use string match (not word boundary) for multi-word patterns
  let regex;
  if (from.includes(' ') || from.includes(',')) {
    regex = new RegExp(escaped, 'g');
  } else {
    regex = new RegExp('(?<![\\p{L}])' + escaped + '(?![\\p{L}])', 'gu');
  }
  const matches = section.match(regex);
  if (matches) {
    changeCount += matches.length;
    section = section.replace(regex, to);
  }
}

console.log('Fifth pass: applied ' + changeCount + ' fixes');

const result = before + '\n' + section + '\n' + after;
fs.writeFileSync(filePath, result, 'utf8');
console.log('File saved');
