const fs = require('fs');
const filePath = __dirname + '/MANUAL_COMBINED.md';

let content = fs.readFileSync(filePath, 'utf8');
let lines = content.split('\n');

let before = lines.slice(0, 827).join('\n');
let section = lines.slice(827, 1733).join('\n');
let after = lines.slice(1733).join('\n');

// Second pass: words missed by the first script
const replacements = [
  // Words found still missing
  ["zycia", "życia"],
  ["Dostepne", "Dostępne"],
  ["Jesli", "Jeśli"],
  ["jesli", "jeśli"],
  ["byc", "być"],
  ["niz", "niż"],
  ["sie", "się"],
  ["ze", "że"],
  ["tresc", "treść"],
  ["Uzywane", "Używane"],
  ["Uzywany", "Używany"],
  ["Uzywana", "Używana"],
  ["tlumaczone", "tłumaczone"],
  ["raportow", "raportów"],
  ["wysyla", "wysyła"],
  ["liczbe", "liczbę"],
  ["Zdjecie", "Zdjęcie"],
  ["odbiorca", "odbiorcą"],
  ["etykiete", "etykietę"],
  ["polce", "półce"],
  ["Przemyslu", "Przemysłu"],
  ["Zwierzat", "Zwierząt"],
  ["skladnika", "składnika"],
  ["odzywczych", "odżywczych"],
  ["odzywczego", "odżywczego"],
  ["przeciwienstwie", "przeciwieństwie"],
  ["Prostokatny", "Prostokątny"],
  ["definiujacy", "definiujący"],
  ["przestrzen", "przestrzeń"],
  ["zidentyfikowac", "zidentyfikować"],
  ["warstwe", "warstwę"],
  ["wyswietlic", "wyświetlić"],
  ["dotyczace", "dotyczące"],
  ["dotyczaca", "dotycząca"],
  ["sugerujace", "sugerujące"],
  ["pokrywajaca", "pokrywająca"],
  ["odczytac", "odczytać"],
  ["zawierac", "zawierać"],
  ["ukryc", "ukryć"],
  ["usunac", "usunąć"],
  ["zadnej", "żadnej"],

  // More words likely still missing - comprehensive scan
  ["opisany", "opisany"],  // stays? No - "opisąny" was wrongly created. Let me check context.

  // Additional words found in the text that need fixing
  ["etykiecie", "etykiecie"],  // stays - locative
  ["miesa", "mięsa"],
  ["ciecia", "cięcia"],
  ["Sluzy", "Służy"],
  ["sluzy", "służy"],
  ["urzadzenia", "urządzenia"],
  ["urzadzenie", "urządzenie"],
  ["wlasciciel", "właściciel"],

  // Words ending in -enie/-anie that might be missed
  ["polaczenie", "połączenie"],

  // Verb forms
  ["dodaja", "dodają"],
  ["podlega", "podlega"],  // stays

  // More missing patterns
  ["tlumaczyc", "tłumaczyć"],
  ["wykorzystac", "wykorzystać"],
  ["przekazac", "przekazać"],
  ["wskazac", "wskazać"],
  ["oznaczy", "oznaczy"],  // stays
  ["oznaczy", "oznaczy"],  // stays

  // Adjective forms
  ["jezykowy", "językowy"],
  ["jezykowa", "językowa"],

  // More words from text
  ["przekazania", "przekazania"],  // stays
  ["wyeksportowanie", "wyeksportowanie"],  // stays

  // Additional check
  ["plikow", "plików"],
  ["wyswietlic", "wyświetlić"],
  ["mozliwe", "możliwe"],
  ["mozliwy", "możliwy"],

  // Corrections for words that the first pass incorrectly changed or didn't change
  ["samej", "samej"],  // stays
  ["Obslugiwany", "Obsługiwany"],

  // Additional words
  ["mieso", "mięso"],
  ["ryz", "ryż"],
  ["kukurydza", "kukurydza"],  // stays
  ["jeczmien", "jęczmień"],
  ["owies", "owies"],  // stays

  // More verbs
  ["zmiesci", "zmieści"],
  ["moze", "może"],
  ["tlumaczy", "tłumaczy"],

  // More nouns
  ["Tresci", "Treści"],

  // Specific patterns
  ["raportow", "raportów"],

  // Missing common words
  ["polce", "półce"],

  // Accusative forms
  ["caloksztaltu", "całokształtu"],
  ["slowna", "słowną"],

  // More from glossary section
  ["rozporzadzeniem", "rozporządzeniem"],
  ["rozporzadzenie", "rozporządzenie"],
  ["liste", "listę"],
  ["dotyczaca", "dotycząca"],
  ["dotyczace", "dotyczące"],
  ["etykiecie", "etykiecie"],  // stays (locative)

  // Remaining issues
  ["calego", "całego"],
  ["Uzycie", "Użycie"],
  ["uzycie", "użycie"],
  ["wyswietlic", "wyświetlić"],

  // More verbs
  ["mozliwe", "możliwe"],

  // Table entries
  ["Obslugiwany", "Obsługiwany"],

  // Additional two-letter fixes: "ze" = "że" is very common

  // Noun forms
  ["budzetu", "budżetu"],

  // Specific text: "samej" should stay, but "sa" -> "sa" might have been wrong
  // Let me check: "samosc" patterns

  // Verb conjugation patterns
  ["komunikuje", "komunikuje"],  // stays
  ["ignorowany", "ignorowany"],  // stays

  // Remaining from the scan
  ["Obslugiwany", "Obsługiwany"],
  ["obslugiwany", "obsługiwany"],

  // More
  ["zawierac", "zawierać"],
  ["odczytac", "odczytać"],
  ["przekazac", "przekazać"],
  ["wkleic", "wkleić"],
  ["pobrac", "pobrać"],

  // Context words
  ["wiekszych", "większych"],
  ["jednym", "jednym"],  // stays
];

// Filter no-ops and sort by length
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
  const regex = new RegExp('(?<![\\p{L}])' + escaped + '(?![\\p{L}])', 'gu');
  const matches = section.match(regex);
  if (matches) {
    changeCount += matches.length;
    section = section.replace(regex, to);
  }
}

console.log('Second pass: applied ' + changeCount + ' replacements');

// Now fix the "opisany" -> "opisąny" error from first pass (invalid - should be "opisany")
// The word "opisany" doesn't have diacritics in Polish
// Actually "opisąny" doesn't exist - the ą was wrongly inserted

// Also fix other potential errors from pass 1
// "sąmej" -> "samej" (the ą was wrongly applied)
// Let me check for these

const fixes = [
  ["opisąny", "opisany"],
  ["opisąniu", "opisaniu"],
  ["sąmej", "samej"],
  ["miesą", "mięsa"],  // "miesa" should become "mięsa" not "miesą"
  ["wpisąniu", "wpisaniu"],
  ["nieprzypisąny", "nieprzypisany"],
  ["masą", "masa"],  // depends on context, but "sucha masą" is wrong, should be "sucha masa"
];

// Actually let me be more careful. The issue is that "sa" -> "są" was applied too broadly.
// It was applied inside words like "opisany" -> "opisąny", "samej" -> "sąmej"
// Let me find and fix all instances where "są" appears incorrectly inside words

// Find words containing "są" that shouldn't have it
const wrongSaPatterns = section.match(/\b\w*są\w+\b/g) || [];
console.log('Words with "są" inside:', [...new Set(wrongSaPatterns)].join(', '));

// Also find words where "są" starts (wrongly)
const wrongSaStart = section.match(/\bsą\w+\b/g) || [];
console.log('Words starting with "są":', [...new Set(wrongSaStart)].join(', '));

const result = before + '\n' + section + '\n' + after;
fs.writeFileSync(filePath, result, 'utf8');
console.log('File saved');
