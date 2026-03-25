const fs = require('fs');
const filePath = __dirname + '/MANUAL_COMBINED.md';

let content = fs.readFileSync(filePath, 'utf8');
let lines = content.split('\n');

let before = lines.slice(0, 827).join('\n');
let section = lines.slice(827, 1733).join('\n');
let after = lines.slice(1733).join('\n');

// Fix false positives from "sa" -> "są" replacement that happened inside words
const falseSaFixes = [
  ["opisąny", "opisany"],
  ["opisąniu", "opisaniu"],
  ["wpisąniu", "wpisaniu"],
  ["wpisąnie", "wpisanie"],
  ["zapisąn", "zapisan"],
  ["zapisąne", "zapisane"],
  ["sąmej", "samej"],
  ["sąm", "sam"],
  ["color_usąge", "color_usage"],
  ["nieprzypisąny", "nieprzypisany"],
  ["Universąl", "Universal"],
  ["Zusątzstoffe", "Zusatzstoffe"],
];

let changeCount = 0;
for (const [from, to] of falseSaFixes) {
  const escaped = from.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const regex = new RegExp(escaped, 'g');
  const matches = section.match(regex);
  if (matches) {
    changeCount += matches.length;
    section = section.replace(regex, to);
  }
}

// Check for any remaining "są" inside words (not standalone)
const remainingBadSa = section.match(/\w+są\w+/g) || [];
if (remainingBadSa.length > 0) {
  console.log('Remaining words with internal "są":', [...new Set(remainingBadSa)].join(', '));
}

// Also fix "masą" -> check contexts. "sucha masą" is wrong, should be "sucha masa" or "suchą masę"
// "DM (sucha masą)" - this should be "DM (sucha masa)"
section = section.replace(/sucha masą\)/g, 'sucha masa)');

// Fix "miesą" which was wrong - should be "mięsa"
section = section.replace(/miesą/g, 'mięsa');

// Now let's also check for more remaining ASCII-only Polish words
// Look for common patterns that indicate missing diacritics
const wordsToCheck = section.match(/\b[a-zA-Z]+\b/g) || [];
const uniqueWords = [...new Set(wordsToCheck)].sort();

// Known words that should have diacritics but might still be ASCII
const additionalFixes = [
  // Common missed words found in verification
  ["Dostepne", "Dostępne"],
  ["dotyczace", "dotyczące"],
  ["dotyczaca", "dotycząca"],
  ["sugerujace", "sugerujące"],
  ["odbiorca", "odbiorcą"],
  ["slowna", "słowną"],
  ["caloksztaltu", "całokształtu"],
  ["liste", "listę"],
  ["budzetu", "budżetu"],
  ["rozporzadzeniem", "rozporządzeniem"],
  ["Uzycie", "Użycie"],
  ["uzycie", "użycie"],

  // Adjective/participle endings
  ["pokrywajaca", "pokrywająca"],

  // Preposition/conjunction

  // Additional common words
  ["plikow", "plików"],
  ["Obslugiwany", "Obsługiwany"],
  ["obslugiwany", "obsługiwany"],

  // Noun forms
  ["Przemyslu", "Przemysłu"],
  ["przemyslu", "przemysłu"],

  // Adjective forms missed
  ["definiujacy", "definiujący"],

  // Corrections
  ["przekazac", "przekazać"],
  ["wskazac", "wskazać"],
  ["pobrac", "pobrać"],

  // More from the glossary/FAQ text
  ["Zwierzat", "Zwierząt"],
  ["zwierzat", "zwierząt"],
  ["odzywczych", "odżywczych"],
  ["odzywczego", "odżywczego"],
  ["odzywczy", "odżywczy"],
  ["mieso", "mięso"],

  // More verb forms
  ["moze", "może"],
  ["tlumaczyc", "tłumaczyć"],
];

for (const [from, to] of additionalFixes) {
  const escaped = from.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const regex = new RegExp('(?<![\\p{L}])' + escaped + '(?![\\p{L}])', 'gu');
  const matches = section.match(regex);
  if (matches) {
    changeCount += matches.length;
    section = section.replace(regex, to);
  }
}

console.log('Third pass: applied ' + changeCount + ' fixes');

const result = before + '\n' + section + '\n' + after;
fs.writeFileSync(filePath, result, 'utf8');
console.log('File saved');

// Final check: scan for remaining suspect words
const finalWords = section.match(/\b[a-zA-Z]{4,}\b/g) || [];
const finalUnique = [...new Set(finalWords)].sort();

// Print words that have suspicious patterns (likely missing diacritics)
const suspectWords = finalUnique.filter(w => {
  const lower = w.toLowerCase();
  // Skip English words and technical terms
  if (['benchmark', 'above', 'average', 'below', 'critical', 'major', 'minor', 'suggestion',
       'complete', 'feed', 'premium', 'economy', 'treats', 'supplements', 'veterinary',
       'shelf', 'impact', 'imagery', 'target', 'audience', 'sustainability', 'visual',
       'hierarchy', 'readability', 'color', 'usage', 'layout', 'composition', 'regulatory',
       'placement', 'multilanguage', 'excellent', 'added', 'removed', 'modified', 'moved',
       'warning', 'info', 'analytical', 'constituents', 'ingredients', 'claims', 'grain',
       'free', 'focus', 'keyword', 'meta', 'title', 'description', 'plain', 'text',
       'headline', 'bullet', 'points', 'upload', 'proof', 'master', 'artwork',
       'english', 'deutsch', 'francais', 'cestina', 'magyar', 'romana', 'italiano',
       'espanol', 'nederlands', 'slovencina', 'bulgarski', 'hrvatski', 'portugues',
       'polski', 'cyber', 'dots', 'inch', 'code', 'good', 'labelling', 'practice',
       'federation', 'europeenne', 'industrie', 'aliments', 'animaux', 'familiers',
       'alleinfuttermittel', 'analytische', 'bestandteile', 'additives', 'zusatzstoffe',
       'rate', 'limit', 'product', 'universal', 'chicken', 'rice', 'adult',
       'nutrition', 'bult', 'quality', 'assurance', 'extendscript', 'adobe',
       'illustrator', 'annotations', 'organic', 'parnut', 'particular', 'nutritional',
       'purposes', 'delta', 'ssim', 'similarity', 'index', 'measure', 'structural',
       'saliency', 'facing', 'cmyk', 'cyan', 'magenta', 'yellow', 'black',
       'compliance', 'score', 'cross', 'check', 'digit', 'appeal', 'appetite',
       'bleed', 'streamlit', 'libreoffice', 'docx', 'word', 'tiff', 'jpeg',
       'illustratora', 'illustratorze', 'google', 'openai', 'anthropic',
       'wholesome', 'barf', 'label', 'website', 'commerce', 'html', 'json',
       'json', 'seo', 'usps', 'cms'].includes(lower)) return false;

  // Check for patterns that suggest missing Polish diacritics
  if (/zyc|zyci|zywo|zywie|zyz|zon|zor|zol|zod|zel|zni|zlo|zro|tlu|slu|slo|glo|wlo|blo|osc$|nosc|mosc|losc|rosc|wosc|kosc/.test(lower)) return true;

  return false;
});

if (suspectWords.length > 0) {
  console.log('\nPotentially remaining suspect words:');
  suspectWords.forEach(w => console.log('  ' + w));
}
