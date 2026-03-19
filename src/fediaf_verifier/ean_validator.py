"""Deterministic EAN/barcode validation — no AI needed for check digit math."""

from __future__ import annotations


def validate_ean13(digits: str) -> tuple[bool, str]:
    """Validate EAN-13 check digit.

    Returns (is_valid, expected_check_digit).
    """
    cleaned = digits.strip().replace(" ", "").replace("-", "")
    if len(cleaned) != 13 or not cleaned.isdigit():
        return False, ""
    weights = [1, 3] * 6
    total = sum(int(d) * w for d, w in zip(cleaned[:12], weights))
    expected = (10 - total % 10) % 10
    return int(cleaned[12]) == expected, str(expected)


def validate_ean8(digits: str) -> tuple[bool, str]:
    """Validate EAN-8 check digit."""
    cleaned = digits.strip().replace(" ", "").replace("-", "")
    if len(cleaned) != 8 or not cleaned.isdigit():
        return False, ""
    weights = [3, 1, 3, 1, 3, 1, 3]
    total = sum(int(d) * w for d, w in zip(cleaned[:7], weights))
    expected = (10 - total % 10) % 10
    return int(cleaned[7]) == expected, str(expected)


def get_country_from_prefix(digits: str) -> tuple[str, str]:
    """Identify country from EAN prefix.

    Returns (prefix, country_name).
    """
    if not digits or len(digits) < 3:
        return "", ""

    d = digits[:3]

    # Single-range prefixes (most common for pet food markets)
    _PREFIXES: dict[str, str] = {
        "590": "Polska",
        "560": "Portugalia",
        "569": "Islandia",
        "570": "Dania",
        "599": "Wegry",
        "600": "Republika Poludniowej Afryki",
        "609": "Mauritius",
        "611": "Maroko",
        "613": "Algeria",
        "616": "Kenia",
        "621": "Syria",
        "628": "Arabia Saudyjska",
        "629": "Emiraty Arabskie",
        "690": "Chiny",
        "729": "Izrael",
        "730": "Szwecja",
        "740": "Gwatemala",
        "750": "Meksyk",
        "759": "Wenezuela",
        "770": "Kolumbia",
        "773": "Urugwaj",
        "775": "Peru",
        "777": "Boliwia",
        "779": "Argentyna",
        "780": "Chile",
        "784": "Paragwaj",
        "786": "Ekwador",
        "789": "Brazylia",
        "858": "Slowacja",
        "859": "Czechy",
        "860": "Serbia",
        "867": "Korea Polnocna",
        "868": "Turcja",
        "869": "Turcja",
        "870": "Holandia",
        "880": "Korea Poludniowa",
        "885": "Tajlandia",
        "888": "Singapur",
        "890": "Indie",
        "893": "Wietnam",
        "899": "Indonezja",
        "955": "Malezja",
        "958": "Makau",
    }

    # Range-based prefixes
    _RANGES: list[tuple[int, int, str]] = [
        (0, 19, "USA / Kanada"),
        (20, 29, "Kody wewnetrzne"),
        (30, 37, "Francja"),
        (380, 380, "Bulgaria"),
        (383, 383, "Slowenia"),
        (385, 385, "Chorwacja"),
        (387, 387, "Bosna i Hercegowina"),
        (389, 389, "Czarnogora"),
        (400, 440, "Niemcy"),
        (450, 459, "Japonia"),
        (460, 469, "Rosja"),
        (470, 470, "Kirgistan"),
        (471, 471, "Tajwan"),
        (474, 474, "Estonia"),
        (475, 475, "Lotwa"),
        (476, 476, "Azerbejdzan"),
        (477, 477, "Litwa"),
        (478, 478, "Uzbekistan"),
        (479, 479, "Sri Lanka"),
        (480, 480, "Filipiny"),
        (481, 481, "Bialorus"),
        (482, 482, "Ukraina"),
        (484, 484, "Moldawia"),
        (485, 485, "Armenia"),
        (486, 486, "Gruzja"),
        (487, 487, "Kazachstan"),
        (489, 489, "Hongkong"),
        (490, 499, "Japonia"),
        (500, 509, "Wielka Brytania"),
        (520, 521, "Grecja"),
        (528, 528, "Liban"),
        (529, 529, "Cypr"),
        (530, 530, "Albania"),
        (531, 531, "Macedonia"),
        (535, 535, "Malta"),
        (539, 539, "Irlandia"),
        (540, 549, "Belgia / Luksemburg"),
        (560, 560, "Portugalia"),
        (569, 569, "Islandia"),
        (570, 579, "Dania / Grenlandia"),
        (590, 590, "Polska"),
        (594, 594, "Rumunia"),
        (599, 599, "Wegry"),
        (600, 601, "RPA"),
        (608, 608, "Bahrajn"),
        (609, 609, "Mauritius"),
        (611, 611, "Maroko"),
        (613, 613, "Algeria"),
        (615, 615, "Nigeria"),
        (616, 616, "Kenia"),
        (618, 618, "Wybrzeze Kosci Sloniowej"),
        (619, 619, "Tunezja"),
        (620, 620, "Tanzania"),
        (621, 621, "Syria"),
        (622, 622, "Egipt"),
        (624, 624, "Libia"),
        (625, 625, "Jordania"),
        (626, 626, "Iran"),
        (627, 627, "Kuwejt"),
        (628, 628, "Arabia Saudyjska"),
        (629, 629, "ZEA"),
        (640, 649, "Finlandia"),
        (690, 699, "Chiny"),
        (700, 709, "Norwegia"),
        (729, 729, "Izrael"),
        (730, 739, "Szwecja"),
        (740, 740, "Gwatemala"),
        (741, 741, "Salwador"),
        (742, 742, "Honduras"),
        (743, 743, "Nikaragua"),
        (744, 744, "Kostaryka"),
        (745, 745, "Panama"),
        (746, 746, "Dominikana"),
        (750, 750, "Meksyk"),
        (754, 755, "Kanada"),
        (759, 759, "Wenezuela"),
        (760, 769, "Szwajcaria / Liechtenstein"),
        (770, 771, "Kolumbia"),
        (773, 773, "Urugwaj"),
        (775, 775, "Peru"),
        (777, 777, "Boliwia"),
        (778, 778, "Argentyna"),
        (779, 779, "Argentyna"),
        (780, 780, "Chile"),
        (784, 784, "Paragwaj"),
        (786, 786, "Ekwador"),
        (789, 790, "Brazylia"),
        (800, 839, "Wlochy"),
        (840, 849, "Hiszpania"),
        (850, 850, "Kuba"),
        (858, 858, "Slowacja"),
        (859, 859, "Czechy"),
        (860, 860, "Serbia"),
        (865, 865, "Mongolia"),
        (867, 867, "Korea Pln."),
        (868, 869, "Turcja"),
        (870, 879, "Holandia"),
        (880, 880, "Korea Pld."),
        (884, 884, "Kambodza"),
        (885, 885, "Tajlandia"),
        (888, 888, "Singapur"),
        (890, 890, "Indie"),
        (893, 893, "Wietnam"),
        (896, 896, "Pakistan"),
        (899, 899, "Indonezja"),
        (900, 919, "Austria"),
        (930, 939, "Australia"),
        (940, 949, "Nowa Zelandia"),
        (950, 950, "GS1 Global Office"),
        (955, 955, "Malezja"),
        (958, 958, "Makau"),
    ]

    # Try exact prefix first
    if d in _PREFIXES:
        return d, _PREFIXES[d]

    # Try range-based
    try:
        prefix_num = int(d)
    except ValueError:
        return d, ""

    for start, end, country in _RANGES:
        if start <= prefix_num <= end:
            return d, country

    return d, ""
