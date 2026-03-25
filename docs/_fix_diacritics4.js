const fs = require('fs');
const filePath = __dirname + '/MANUAL_COMBINED.md';

let content = fs.readFileSync(filePath, 'utf8');
let lines = content.split('\n');

let before = lines.slice(0, 827).join('\n');
let section = lines.slice(827, 1733).join('\n');
let after = lines.slice(1733).join('\n');

const replacements = [
  // Words identified as still needing fixes
  ["czlowieka", "człowieka"],
  ["czytelnosci", "czytelności"],
  ["krzyzowa", "krzyżowa"],
  ["moglo", "mogło"],
  ["obsluguja", "obsługują"],
  ["opatrzona", "opatrzoną"],
  ["slowo", "słowo"],
  ["tlumaczen", "tłumaczeń"],
  ["tlumaczeniem", "tłumaczeniem"],
  ["tluszczu", "tłuszczu"],
  ["wlokna", "włókna"],
  ["wloski", "włoski"],
  ["zawartosc", "zawartość"],
  ["Zawartosc", "Zawartość"],
  ["zdolnosc", "zdolność"],
  ["zniknely", "zniknęły"],
  ["zablokowana", "zablokowana"],  // stays - no diacritic needed
  ["ilosci", "ilości"],
  ["slowacki", "słowacki"],
  ["Glownie", "Głównie"],
  ["Spojnosc", "Spójność"],
  ["Obslugiwane", "Obsługiwane"],
  ["wprowadzone", "wprowadzone"],  // stays
  ["wprowadzonych", "wprowadzonych"],  // stays

  // Additional words that likely still need fixing - going through the text more carefully
  ["Uzywany", "Używany"],
  ["Uzywane", "Używane"],
  ["Uzywana", "Używana"],

  // More words from scanning
  ["szablonu", "szablonu"],  // stays
  ["subiektywna", "subiektywną"],
  ["profesjonalna", "profesjonalną"],

  // Now do a comprehensive sweep of ALL remaining Polish words missing diacritics
  // Going through common Polish word patterns

  // Words with ż (z -> ż)
  ["mozliwe", "możliwe"],
  ["moze", "może"],
  ["moza", "możą"],
  ["kazda", "każda"],
  ["kazde", "każde"],
  ["uzytek", "użytek"],
  ["uzyciu", "użyciu"],
  ["zaden", "żaden"],

  // Words with ó (o -> ó)
  ["glowny", "główny"],
  ["sposob", "sposób"],
  ["ktorych", "których"],
  ["rowniez", "również"],
  ["mozliwosci", "możliwości"],
  ["krotko", "krótko"],

  // Words with ś (s -> ś)
  ["sciaga", "ściąga"],
  ["scisle", "ściśle"],

  // Words with ć (c -> ć)
  ["byc", "być"],
  ["miec", "mieć"],
  ["robic", "robić"],

  // Words with ą (a -> ą)
  ["znajac", "znając"],

  // Words with ę (e -> ę)
  ["miedzy", "między"],

  // Words with ł (l -> ł)
  ["wlasciwie", "właściwie"],

  // Words with ń (n -> ń)
  ["ostatni", "ostatni"],  // stays

  // Now fix remaining words from the text that I can see
  ["Orientacyjna", "Orientacyjna"],  // stays

  // Common verbs that are likely still ASCII
  ["oznacza", "oznacza"],  // stays - no diacritic needed

  // Additional check - words ending in "-osc" pattern
  ["czytelnosc", "czytelność"],

  // Words ending in "-nosci"
  ["czytelnosci", "czytelności"],

  // Polish words found in remaining scan
  ["Kompozycja", "Kompozycja"],  // stays

  // Fix specific remaining words
  ["umaczone", "tłumaczone"],  // this looks like a broken word from "tlumaczone"

  // More fixes
  ["Waznoscia", "Ważnością"],
  ["interpretacja", "interpretacją"],  // check context
];

// Filter no-ops and sort
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

console.log('Fourth pass: applied ' + changeCount + ' fixes');

// Now let me do a final comprehensive scan
// Find ALL words in the section that are pure ASCII and 3+ chars long
const allWords = section.match(/\b[a-zA-Z]{3,}\b/g) || [];
const uniqueAscii = [...new Set(allWords)].sort();

// Filter to only words that look Polish (not English/technical terms)
const englishWords = new Set([
  'above','added','adult','aliments','all','also','analytical','and','animaux',
  'appeal','appetite','art','artwork','average','barf','bbox','below','benchmark',
  'bestandteile','bio','black','bleed','bounding','box','bult','bullet','check',
  'chicken','claim','claims','cmyk','code','color','commerce','complete','compliance',
  'composition','constituents','critical','cross','cyan','delta','description',
  'design','digit','dots','dry','economy','english','europeenne','excellent',
  'extendscript','facing','familiers','feed','focus','format','free','full',
  'good','grain','headline','high','html','imagery','impact','inch','index',
  'industrie','info','jpeg','json','jsx','key','keyword','lab','labelling',
  'layout','libreoffice','limit','low','magenta','major','marker','master',
  'matter','measure','medium','meta','minor','moderate','multilanguage',
  'naming','natural','nutrition','online','openai','organic','parnut','particular',
  'per','placement','plain','points','practice','premium','product','profile',
  'proof','purposes','quality','rate','raw','readability','regulatory','rice',
  'rule','saliency','score','seo','shelf','similarity','ssim','streamlit',
  'structural','suggestion','supplements','sustainability','target','text',
  'title','trade','treats','trend','type','universal','usage','veterinary',
  'violation','visual','web','website','wet','whitespace','wholesome','word',
  'yellow','adobe','anthropic','annotation','annotations','assurance','audience',
  'baseline','blog','briefing','certyfikacji','cms','composition','deutsche','deutsch',
  'docx','dry','euipo','extendscript','federation','formato','google','hierarchy',
  'illustrator','illustratora','illustratorze','input','iteration','jpg','keywords',
  'listing','markdown','monitor','multilanguage','multipart','naming','new','old',
  'output','overview','pdf','percentile','percentyl','png','pozycjonowanie','proof',
  'qr','quality','question','range','raw','redesign','reference','report','rgb',
  'risk','rule','scan','script','section','segment','session','sgn','specification',
  'standard','step','style','suggest','summary','system','tab','table','template',
  'test','testing','tiff','tif','ton','tool','tracking','trend','type','upc',
  'upload','url','uprp','version','view','violation','virtual','warning','website',
  'with','workflow','workspace','worst','xml',
  // Technical Polish that stays unchanged
  'algorytm','analityczne','analitycznych','automatycznie','certyfikacyjny',
  'dawkowanie','dawkowania','deterministyczna','deterministyczne','deterministycznie',
  'dietetyczna','dietetyczne','dietetycznych','dietetycznym','ekologicznych',
  'eksportu','etykieta','etykiety','etykiet','etykiecie','etykietowania','formularz',
  'formularzu','gatunku','graficznego','graficznym','grafiki','grafika','graficzne',
  'grafikowi','informacyjny','informacyjnym','inspekcja','kategoria','kategorii',
  'kluczowe','kluczowy','kluczowego','kluczowych','kompresuje','kompresja',
  'kontaktu','kontekstu','kontrola','kontroli','kontrolna','kontrolne','kontrolnej',
  'korektorowi','lecznicze','lecznicze','luksusowego','marketingowe','marketingowych',
  'marketingowym','marketingowy','materialy','metadane','metrologiczny','neutralny',
  'numeryczne','numerycznych','opakowania','opakowaniu','orientacyjny','priorytet',
  'priorytetem','producenta','producenta','produktu','produktowej','procentowe',
  'procentowej','procentowych','promocyjne','regulacja','regulacje','regulacji',
  'regulacyjne','regulacyjnego','regulacyjnej','regulacyjny','regulacyjnym',
  'regulacyjnych','responsywny','referencyjne','referencyjnymi','referencyjnych',
  'sekcje','sekcji','sekcja','segmentu','segmentem','segmentowy','sekwencyjnie',
  'specjalistyczna','specjalistyczne','specjalistycznym','suplementy','terminologia',
  'terminologii','terminologiczny','terapeutyczny','terapeutyczne','walidacja',
  'walidator','waliduje','weryfikacja','weryfikacji','weryfikacyjne','weryfikacyjnych',
  'weryfikator','weryfikuje','wizyjny',
  'akcent','akcji','aktywny','aktualnymi','aktualnych','analiza','analizy',
  'argumentacja','automatyczny','automatycznie','bazowej','bazowy','bazowych',
  'briefing','brudnopisu','brudnopis','certyfikacji','certyfikacyjny','chorobom',
  'cyfrowo','cyfrowy','czytelny','czytelna','dane','danych','dawkowanie',
  'deterministyczna','dodaje','dodaje','dodatkowe','dodatkowych','dodatkowi',
  'dokument','drukarskim','dwuwymiarowy','dynamicznie','efekcie','ekstrakcji',
  'etykiety','europejski','ewentualnymi','formalny','formie','funkcjonalnych',
  'funkcjonalny','generowanie','generuje','generowany','graficzne','identyfikacja',
  'identyfikuje','informacje','informacji','instrukcja','internetowej','iteracji',
  'kilka','kliknie','kolorowe','kolorowymi','komentarz','kompletna','komunikuje',
  'konfiguracj','konfiguruje','konsumenta','kontrolne','korekte','korekty',
  'krajowe','kreskowe','kreskowy','kreskowych','krytyczne','krytyczny',
  'lista','logiczne','lokalizacji','marketingowe','marketingowych','materialy',
  'maksymalnie','maksymalny','naprzemiennie','naruszenie','naruszenia','naukowe',
  'naukowy','neutralny','nowej','nowy','obiektywne','obraz','obrazu','odczytu',
  'odczytuje','odniesieniem','orientacyjne','orientacyjny','osiem','opcja','opcjami',
  'opracowany','oryginalem','oryginalny','optymalnie','optymalny','podstawie',
  'pobierania','pobierz','podania','podsumowanie','poprawek','poprawka',
  'potwierdzone','pozycjonowanie','pozycjonowany','praktyki','praktyk',
  'precyzyjne','priorytetem','produktowej','procentowe','profesjonalista',
  'prowadzi','punktowe','receptura','referencyjne','rekomendacje','rekomendacji',
  'rynek','rynku','rynkowy','rynkowych','rynkami','roboczego','segmentowymi',
  'sekcja','sekcje','sekwencyjnie','seniorow','skanem','skompilowane',
  'strony','stronie','streszczenie','struktura','struktury','sumaryczna',
  'szerokim','technologa','tekstowe','tekstowy','tekstowym','terapeutyczny',
  'trwa','tworzenie','tworzenia','uruchomieniu','uruchomieniem','wersja','wersji',
  'weterynaryjny','weterynaryjne','weterynarzami','widoczne','widoczny',
  'wizualnej','wizualne','wzorcowy','zainstalowanego','zainstaluj',
  'zakazy','zatwierdzeniem','zdrowia','zestawu','zmian','zwierzecia'
]);

// Find remaining suspect ASCII-only Polish words
const remainingSuspect = uniqueAscii.filter(w => {
  const lower = w.toLowerCase();
  if (lower.length < 3) return false;
  if (englishWords.has(lower)) return false;
  // Skip words that have non-ASCII already (mixed)
  if (!/^[a-zA-Z]+$/.test(w)) return false;
  // Skip single-letter and very common non-diacritic Polish words
  if (['aby','ale','ani','bez','czy','dla','gdy','jak','lub','nad','nie','pod','pod',
       'przy','tak','ten','tym','wiec','zatem','ale','ani','jako','nawet','obok',
       'przed','przez','oraz','aby','gdyz','juz','tez','temu','tego','jest','ich',
       'jego','jej','nas','nam','was','oni','one','ono','nasz','wasz','kto','nic',
       'pan','pani'].includes(lower)) return false;
  return true;
});

console.log('\nRemaining pure-ASCII words (potential missing diacritics):');
console.log(remainingSuspect.filter(w => {
  const l = w.toLowerCase();
  // Only show ones that look like they might need diacritics
  return /zyc|osc|nosc|losc|zni|zlo|zro|tlu|slu|glo|wlo|pol[ck]|odzi|osci/.test(l);
}).join(', '));

const result = before + '\n' + section + '\n' + after;
fs.writeFileSync(filePath, result, 'utf8');
console.log('File saved');
