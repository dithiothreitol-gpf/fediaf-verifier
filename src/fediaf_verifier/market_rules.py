"""Per-country regulatory rules for pet food labelling beyond EU 767/2009."""

MARKET_RULES: dict[str, dict] = {
    "DE": {
        "name": "Niemcy",
        "language_required": "de",
        "regulations": [
            {
                "id": "DE_LMIV_FONT",
                "category": "labeling",
                "desc": "Minimalna wielkosc czcionki 1.2mm wg LMIV (EU 1169/2011)",
            },
            {
                "id": "DE_LANGUAGE",
                "category": "language",
                "desc": "Pelna tresc w jezyku niemieckim wymagana",
            },
            {
                "id": "DE_BIO",
                "category": "claims",
                "desc": "Oznaczenie bio wymaga certyfikatu DE-OKO-XXX",
            },
            {
                "id": "DE_MANUFACTURER",
                "category": "legal",
                "desc": "Dane producenta lub importera z adresem w UE",
            },
        ],
    },
    "FR": {
        "name": "Francja",
        "language_required": "fr",
        "regulations": [
            {
                "id": "FR_LANGUAGE",
                "category": "language",
                "desc": "Cala tresc etykiety musi byc w jezyku francuskim (Loi Toubon)",
            },
            {
                "id": "FR_LOT",
                "category": "labeling",
                "desc": "Numer partii (LOT) wymagany na opakowaniu",
            },
            {
                "id": "FR_BIO",
                "category": "claims",
                "desc": "Claimy bio/ekologiczne wymagaja certyfikatu FR-BIO-XX",
            },
            {
                "id": "FR_ORIGIN",
                "category": "legal",
                "desc": "Kraj pochodzenia surowcow wymagany dla claimow origin",
            },
            {
                "id": "FR_RECYCLING",
                "category": "packaging",
                "desc": "Oznaczenie Triman + Info-tri wymagane (od 2023)",
            },
        ],
    },
    "CZ": {
        "name": "Czechy",
        "language_required": "cs",
        "regulations": [
            {
                "id": "CZ_LANGUAGE",
                "category": "language",
                "desc": "Etykieta musi byc w jezyku czeskim",
            },
            {
                "id": "CZ_DIACRITICS",
                "category": "labeling",
                "desc": "Czeskie znaki diakrytyczne (hacky, carky) musza byc poprawne",
            },
            {
                "id": "CZ_SVS",
                "category": "legal",
                "desc": "Numer rejestracyjny SVS (Statni veterinarni sprava) dla importowanych karm",
            },
            {
                "id": "CZ_ADDITIVES",
                "category": "claims",
                "desc": "Dodatki technologiczne musza byc wymienione wg czeskiej nomenklatury",
            },
        ],
    },
    "HU": {
        "name": "Wegry",
        "language_required": "hu",
        "regulations": [
            {
                "id": "HU_LANGUAGE",
                "category": "language",
                "desc": "Pelna tresc w jezyku wegierskim wymagana",
            },
            {
                "id": "HU_NEBIH",
                "category": "legal",
                "desc": "Numer rejestracyjny NEBIH dla zakladow produkcyjnych",
            },
            {
                "id": "HU_DIACRITICS",
                "category": "labeling",
                "desc": "Wegierskie znaki diakrytyczne (ekezetek) musza byc poprawne",
            },
            {
                "id": "HU_FEEDING",
                "category": "labeling",
                "desc": "Tabela dawkowania musi zawierac kategorie wagowe zwierzat",
            },
        ],
    },
    "RO": {
        "name": "Rumunia",
        "language_required": "ro",
        "regulations": [
            {
                "id": "RO_LANGUAGE",
                "category": "language",
                "desc": "Etykieta musi byc w jezyku rumunskim",
            },
            {
                "id": "RO_ANSVSA",
                "category": "legal",
                "desc": "Numer rejestracyjny ANSVSA wymagany dla importu",
            },
            {
                "id": "RO_DIACRITICS",
                "category": "labeling",
                "desc": "Rumunskie znaki diakrytyczne (s-cedilla, t-cedilla) poprawne",
            },
            {
                "id": "RO_IMPORTER",
                "category": "legal",
                "desc": "Dane importera z adresem w Rumunii wymagane dla produktow zagranicznych",
            },
        ],
    },
    "IT": {
        "name": "Wlochy",
        "language_required": "it",
        "regulations": [
            {
                "id": "IT_LANGUAGE",
                "category": "language",
                "desc": "Pelna tresc w jezyku wloskim wymagana (D.Lgs. 142/2012)",
            },
            {
                "id": "IT_STABILIMENTO",
                "category": "legal",
                "desc": "Numer zakladu produkcyjnego (stabilimento) wymagany",
            },
            {
                "id": "IT_ORIGIN",
                "category": "labeling",
                "desc": "Kraj pochodzenia surowcow zwierzecych wymagany",
            },
            {
                "id": "IT_RECYCLING",
                "category": "packaging",
                "desc": "Oznaczenie materialow opakowaniowych wg D.Lgs. 116/2020",
            },
            {
                "id": "IT_ORGANIC",
                "category": "claims",
                "desc": "Claimy biologico wymagaja certyfikatu IT-BIO-XXX",
            },
        ],
    },
    "ES": {
        "name": "Hiszpania",
        "language_required": "es",
        "regulations": [
            {
                "id": "ES_LANGUAGE",
                "category": "language",
                "desc": "Etykieta musi byc w jezyku hiszpanskim (kastylijskim)",
            },
            {
                "id": "ES_RGSEAA",
                "category": "legal",
                "desc": "Numer rejestru RGSEAA wymagany dla zakladow",
            },
            {
                "id": "ES_FONT",
                "category": "labeling",
                "desc": "Minimalna wielkosc czcionki 1.2mm dla informacji obowiazkowych",
            },
            {
                "id": "ES_ECO",
                "category": "claims",
                "desc": "Claimy ecologico wymagaja certyfikatu ES-ECO-XXX",
            },
        ],
    },
    "UK": {
        "name": "Wielka Brytania",
        "language_required": "en",
        "regulations": [
            {
                "id": "UK_LANGUAGE",
                "category": "language",
                "desc": "Pelna tresc w jezyku angielskim wymagana",
            },
            {
                "id": "UK_APHA",
                "category": "legal",
                "desc": "Rejestracja APHA wymagana dla importowanych karm",
            },
            {
                "id": "UK_UKCA",
                "category": "labeling",
                "desc": "Oznaczenie UKCA zamiast CE po Brexicie (od 2025)",
            },
            {
                "id": "UK_GB_ADDRESS",
                "category": "legal",
                "desc": "Dane podmiotu odpowiedzialnego z adresem w GB wymagane",
            },
            {
                "id": "UK_FSA",
                "category": "claims",
                "desc": "Claimy zdrowotne musza byc zgodne z wytycznymi FSA/PFMA",
            },
        ],
    },
    "NL": {
        "name": "Holandia",
        "language_required": "nl",
        "regulations": [
            {
                "id": "NL_LANGUAGE",
                "category": "language",
                "desc": "Etykieta musi byc w jezyku niderlandzkim",
            },
            {
                "id": "NL_NVWA",
                "category": "legal",
                "desc": "Zgodnosc z wytycznymi NVWA dot. karm dla zwierzat",
            },
            {
                "id": "NL_CLAIMS",
                "category": "claims",
                "desc": "Claimy funkcjonalne wymagaja uzasadnienia naukowego wg RvA",
            },
            {
                "id": "NL_RECYCLING",
                "category": "packaging",
                "desc": "Oznaczenie Afval (recykling) zgodne z wytycznymi Afvalfonds",
            },
        ],
    },
    "SK": {
        "name": "Slowacja",
        "language_required": "sk",
        "regulations": [
            {
                "id": "SK_LANGUAGE",
                "category": "language",
                "desc": "Etykieta musi byc w jezyku slowackim",
            },
            {
                "id": "SK_SVPS",
                "category": "legal",
                "desc": "Numer rejestracyjny SVPS (Statna veterinarna a potravova sprava)",
            },
            {
                "id": "SK_DIACRITICS",
                "category": "labeling",
                "desc": "Slowackie znaki diakrytyczne (dlzen, makcen) musza byc poprawne",
            },
            {
                "id": "SK_IMPORTER",
                "category": "legal",
                "desc": "Dane importera z adresem w SR dla produktow zagranicznych",
            },
        ],
    },
    "BG": {
        "name": "Bulgaria",
        "language_required": "bg",
        "regulations": [
            {
                "id": "BG_LANGUAGE",
                "category": "language",
                "desc": "Etykieta musi byc w jezyku bulgarskim (alfabet cyrylicki)",
            },
            {
                "id": "BG_BFSA",
                "category": "legal",
                "desc": "Numer rejestracyjny BFSA (Bulgarska Agencja Bezpieczenstwa Zywnosci)",
            },
            {
                "id": "BG_CYRILLIC",
                "category": "labeling",
                "desc": "Tresc musi uzywac poprawnego alfabetu cyrylickiego",
            },
            {
                "id": "BG_IMPORTER",
                "category": "legal",
                "desc": "Dane importera z adresem w Bulgarii dla produktow importowanych",
            },
        ],
    },
    "HR": {
        "name": "Chorwacja",
        "language_required": "hr",
        "regulations": [
            {
                "id": "HR_LANGUAGE",
                "category": "language",
                "desc": "Etykieta musi byc w jezyku chorwackim",
            },
            {
                "id": "HR_HAPIH",
                "category": "legal",
                "desc": "Zgodnosc z wymaganiami HAPIH (Chorwacka Agencja ds. Zywnosci)",
            },
            {
                "id": "HR_DIACRITICS",
                "category": "labeling",
                "desc": "Chorwackie znaki diakrytyczne (c, c, z, s, d) musza byc poprawne",
            },
            {
                "id": "HR_IMPORTER",
                "category": "legal",
                "desc": "Dane importera z adresem w HR wymagane dla produktow z poza EU",
            },
        ],
    },
    "PT": {
        "name": "Portugalia",
        "language_required": "pt",
        "regulations": [
            {
                "id": "PT_LANGUAGE",
                "category": "language",
                "desc": "Etykieta musi byc w jezyku portugalskim",
            },
            {
                "id": "PT_DGAV",
                "category": "legal",
                "desc": "Numer rejestracyjny DGAV (Direcao-Geral de Alimentacao e Veterinaria)",
            },
            {
                "id": "PT_DIACRITICS",
                "category": "labeling",
                "desc": "Portugalskie znaki diakrytyczne (acentos, til, cedilha) poprawne",
            },
            {
                "id": "PT_RECYCLING",
                "category": "packaging",
                "desc": "Oznaczenie Ponto Verde dla opakowan wymagane",
            },
        ],
    },
    "PL": {
        "name": "Polska",
        "language_required": "pl",
        "regulations": [
            {
                "id": "PL_LANGUAGE",
                "category": "language",
                "desc": "Pelna tresc etykiety w jezyku polskim wymagana",
            },
            {
                "id": "PL_GLOWNY_INSPEKTORAT",
                "category": "legal",
                "desc": "Numer rejestracyjny GIW (Glowny Inspektorat Weterynarii) dla zakladow",
            },
            {
                "id": "PL_DIACRITICS",
                "category": "labeling",
                "desc": "Polskie znaki diakrytyczne (ogonki, kreski) musza byc poprawne",
            },
            {
                "id": "PL_FEEDING_TABLE",
                "category": "labeling",
                "desc": "Tabela dawkowania z podziałem na mase ciala w kg wymagana",
            },
            {
                "id": "PL_CLAIMS",
                "category": "claims",
                "desc": "Claimy zdrowotne musza byc zgodne z wykazem PIW",
            },
        ],
    },
}
