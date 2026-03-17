"""Deterministic FEDIAF rules — independent of AI model.

Source: FEDIAF Nutritional Guidelines 2021, Tables 9-14.
Values in % dry matter (DM).
Conversion from as-fed: value_DM = value_as_fed / (1 - moisture/100)
"""

from fediaf_verifier.models import Issue, NutrientValues, Product, Severity

# -- Minimum nutrient levels (% DM) ---------------------------------------------------
# Key: (species, lifestage, food_type)
FEDIAF_MINIMUMS_DM: dict[tuple[str, str, str], dict[str, float]] = {
    # Dogs
    ("dog", "puppy", "dry"): {
        "crude_protein": 22.5,
        "crude_fat": 8.0,
        "calcium": 1.0,
        "phosphorus": 0.8,
    },
    ("dog", "puppy", "wet"): {
        "crude_protein": 22.5,
        "crude_fat": 8.0,
        "calcium": 1.0,
        "phosphorus": 0.8,
    },
    ("dog", "adult", "dry"): {
        "crude_protein": 18.0,
        "crude_fat": 5.0,
        "calcium": 0.5,
        "phosphorus": 0.4,
    },
    ("dog", "adult", "wet"): {
        "crude_protein": 18.0,
        "crude_fat": 5.0,
        "calcium": 0.5,
        "phosphorus": 0.4,
    },
    ("dog", "senior", "dry"): {
        "crude_protein": 18.0,
        "crude_fat": 5.0,
        "calcium": 0.5,
        "phosphorus": 0.4,
    },
    ("dog", "senior", "wet"): {
        "crude_protein": 18.0,
        "crude_fat": 5.0,
        "calcium": 0.5,
        "phosphorus": 0.4,
    },
    ("dog", "all_stages", "dry"): {
        "crude_protein": 22.5,
        "crude_fat": 8.0,
        "calcium": 1.0,
        "phosphorus": 0.8,
    },
    ("dog", "all_stages", "wet"): {
        "crude_protein": 22.5,
        "crude_fat": 8.0,
        "calcium": 1.0,
        "phosphorus": 0.8,
    },
    # Cats
    ("cat", "kitten", "dry"): {
        "crude_protein": 28.0,
        "crude_fat": 9.0,
        "calcium": 0.8,
        "phosphorus": 0.6,
    },
    ("cat", "kitten", "wet"): {
        "crude_protein": 28.0,
        "crude_fat": 9.0,
        "calcium": 0.8,
        "phosphorus": 0.6,
    },
    ("cat", "adult", "dry"): {
        "crude_protein": 25.0,
        "crude_fat": 9.0,
        "calcium": 0.6,
        "phosphorus": 0.5,
    },
    ("cat", "adult", "wet"): {
        "crude_protein": 25.0,
        "crude_fat": 9.0,
        "calcium": 0.6,
        "phosphorus": 0.5,
    },
    ("cat", "senior", "dry"): {
        "crude_protein": 25.0,
        "crude_fat": 9.0,
        "calcium": 0.6,
        "phosphorus": 0.5,
    },
    ("cat", "senior", "wet"): {
        "crude_protein": 25.0,
        "crude_fat": 9.0,
        "calcium": 0.6,
        "phosphorus": 0.5,
    },
    ("cat", "all_stages", "dry"): {
        "crude_protein": 28.0,
        "crude_fat": 9.0,
        "calcium": 0.8,
        "phosphorus": 0.6,
    },
    ("cat", "all_stages", "wet"): {
        "crude_protein": 28.0,
        "crude_fat": 9.0,
        "calcium": 0.8,
        "phosphorus": 0.6,
    },
}

# -- Maximum nutrient levels (% DM) ---------------------------------------------------
# Key: (species, lifestage, "any") — applies to all food types
FEDIAF_MAXIMUMS_DM: dict[tuple[str, str, str], dict[str, float]] = {
    ("dog", "puppy", "any"): {"calcium": 3.3, "phosphorus": 2.5},
    ("dog", "adult", "any"): {"calcium": 4.5, "phosphorus": 4.0},
    ("dog", "senior", "any"): {"calcium": 4.5, "phosphorus": 4.0},
    ("cat", "kitten", "any"): {"calcium": 3.0, "phosphorus": 2.5},
    ("cat", "adult", "any"): {"calcium": 4.0, "phosphorus": 3.5},
    ("cat", "senior", "any"): {"calcium": 4.0, "phosphorus": 3.5},
}

# -- FEDIAF references ----------------------------------------------------------------
FEDIAF_REFERENCES: dict[str, str] = {
    "crude_protein": "FEDIAF 2021, Table 9-10 (cats) / Table 11-12 (dogs)",
    "crude_fat": "FEDIAF 2021, Table 9-10 (cats) / Table 11-12 (dogs)",
    "calcium": "FEDIAF 2021, Table 13 (minerals)",
    "phosphorus": "FEDIAF 2021, Table 13 (minerals)",
}


def convert_to_dm(value: float, moisture: float | None) -> float:
    """Convert as-fed value to dry matter (DM).

    If moisture is unknown, assumes 10% (typical for dry food).
    If moisture >= 100, returns value unchanged (invalid data guard).
    """
    if moisture is None:
        moisture = 10.0
    if moisture >= 100:
        return value
    return value / (1.0 - moisture / 100.0)


def hard_check(product: Product, nutrients: NutrientValues) -> list[Issue]:
    """Deterministic FEDIAF threshold verification.

    Independent of AI model — AI errors do not affect this layer.

    Returns:
        List of Issue objects with source="HARD_RULE".
        Empty list if species or lifestage is unknown.
    """
    flags: list[Issue] = []

    species = product.species.value
    lifestage = product.lifestage.value
    food_type = product.food_type.value

    if species == "unknown" or lifestage == "unknown":
        return []

    # Treats and supplements are not subject to FEDIAF complete food minimums
    if food_type in ("treat", "supplement"):
        return []

    # Normalize food_type for minimum lookup
    ft_lookup = food_type if food_type in ("dry", "wet") else "dry"

    # -- Check minimums ----------------------------------------------------------------
    minimums = FEDIAF_MINIMUMS_DM.get((species, lifestage, ft_lookup), {})

    for nutrient, min_dm in minimums.items():
        actual_raw = getattr(nutrients, nutrient, None)
        if actual_raw is None:
            continue

        actual_dm = convert_to_dm(actual_raw, nutrients.moisture)

        if actual_dm < min_dm:
            flags.append(
                Issue(
                    source="HARD_RULE",
                    severity=Severity.CRITICAL,
                    code=f"{nutrient.upper()}_BELOW_MIN",
                    description=(
                        f"{nutrient.replace('_', ' ').title()} ({actual_raw}% as-fed, "
                        f"{actual_dm:.1f}% DM) ponizej minimum FEDIAF "
                        f"({min_dm}% DM) dla {species} {lifestage}."
                    ),
                    found_value=round(actual_dm, 2),
                    required_value=f"min. {min_dm}% DM",
                    fediaf_reference=FEDIAF_REFERENCES.get(nutrient, "FEDIAF 2021"),
                )
            )

    # -- Check maximums ----------------------------------------------------------------
    maximums = FEDIAF_MAXIMUMS_DM.get((species, lifestage, "any")) or FEDIAF_MAXIMUMS_DM.get(
        (species, "all_stages", "any"), {}
    )

    for nutrient, max_dm in maximums.items():
        actual_raw = getattr(nutrients, nutrient, None)
        if actual_raw is None:
            continue

        actual_dm = convert_to_dm(actual_raw, nutrients.moisture)

        if actual_dm > max_dm:
            flags.append(
                Issue(
                    source="HARD_RULE",
                    severity=Severity.CRITICAL,
                    code=f"{nutrient.upper()}_ABOVE_MAX",
                    description=(
                        f"{nutrient.replace('_', ' ').title()} ({actual_raw}% as-fed, "
                        f"{actual_dm:.1f}% DM) powyzej maksimum FEDIAF "
                        f"({max_dm}% DM) dla {species} {lifestage}."
                    ),
                    found_value=round(actual_dm, 2),
                    required_value=f"max. {max_dm}% DM",
                    fediaf_reference=FEDIAF_REFERENCES.get(nutrient, "FEDIAF 2021"),
                )
            )

    return flags


def merge_with_ai_issues(ai_issues: list[Issue], hard_flags: list[Issue]) -> list[Issue]:
    """Merge AI issues with deterministic rule flags.

    Deduplicates by code — if a hard_rule has the same code as an AI issue,
    keeps the AI version and skips the duplicate hard_rule flag.
    """
    ai_codes = {issue.code for issue in ai_issues}
    unique_hard = [f for f in hard_flags if f.code not in ai_codes]
    return ai_issues + unique_hard
