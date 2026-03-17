"""Accuracy tests — reliability Layer 5.

How to use:
1. Collect 20-30 labels with manually verified results (nutrition expert)
2. Place them in tests/reference_cases/
3. Create tests/reference_cases/ground_truth.json (format below)
4. Run: pytest tests/test_accuracy.py -v

Minimum target: >= 95% status accuracy (COMPLIANT/NON_COMPLIANT/REQUIRES_REVIEW)
"""

import json
from pathlib import Path

import pytest

GROUND_TRUTH_PATH = Path("tests/reference_cases/ground_truth.json")
MIN_ACCURACY = 0.95


def load_ground_truth() -> list[dict]:
    """Load ground truth data.

    Format of ground_truth.json:
    [
      {
        "file": "label_dog_adult_01.jpg",
        "expected_status": "COMPLIANT",
        "expected_score_min": 85,
        "notes": "Dry dog adult, all values above minimum"
      }
    ]
    """
    if not GROUND_TRUTH_PATH.exists():
        pytest.skip(
            f"Brak pliku {GROUND_TRUTH_PATH}. "
            "Dodaj etykiety referencyjne z recznie zweryfikowanymi wynikami."
        )

    with open(GROUND_TRUTH_PATH) as f:
        data = json.load(f)

    if not data:
        pytest.skip("ground_truth.json jest pusty. Dodaj przypadki testowe.")

    return data


@pytest.mark.slow
def test_status_accuracy():
    """Check status classification accuracy on the reference set."""
    from fediaf_verifier.config import get_settings
    from fediaf_verifier.converter import file_to_base64, load_pdf_base64
    from fediaf_verifier.verifier import create_client, verify_label

    settings = get_settings()
    client = create_client(settings)
    cases = load_ground_truth()
    fediaf_b64 = load_pdf_base64(settings.fediaf_pdf_path)

    correct = 0
    errors: list[dict] = []

    for case in cases:
        filepath = Path("tests/reference_cases") / case["file"]
        if not filepath.exists():
            errors.append({"file": case["file"], "error": "Plik nie istnieje"})
            continue

        label_b64, media_type = file_to_base64(filepath.read_bytes(), case["file"])
        result = verify_label(
            label_b64=label_b64,
            media_type=media_type,
            settings=settings,
            client=client,
            fediaf_b64=fediaf_b64,
        )

        expected = case["expected_status"]
        actual = result.status.value

        if actual == expected:
            correct += 1
        else:
            errors.append(
                {
                    "file": case["file"],
                    "expected": expected,
                    "got": actual,
                    "score": result.compliance_score,
                    "notes": case.get("notes", ""),
                }
            )

    accuracy = correct / len(cases) if cases else 0

    print(f"\nDokladnosc: {accuracy:.1%} ({correct}/{len(cases)})")
    if errors:
        print("\nBledne klasyfikacje:")
        for e in errors:
            print(
                f"  {e['file']}: oczekiwano {e.get('expected', '?')}, "
                f"otrzymano {e.get('got', 'ERROR')} (score: {e.get('score', '?')})"
            )

    assert accuracy >= MIN_ACCURACY, (
        f"Dokladnosc {accuracy:.1%} ponizej progu {MIN_ACCURACY:.1%}. "
        f"Sprawdz bledne klasyfikacje powyzej."
    )


def test_hard_rules_catch_known_violations():
    """Check that deterministic rules catch known violations.

    Uses synthetic data — no PDF or API needed.
    """
    from fediaf_verifier.models import FoodType, Lifestage, NutrientValues, Product, Species
    from fediaf_verifier.rules import hard_check

    # Dog adult dry with protein below minimum
    product = Product(
        species=Species.DOG, lifestage=Lifestage.ADULT, food_type=FoodType.DRY
    )
    nutrients = NutrientValues(
        crude_protein=15.0,  # Below 18% DM minimum
        crude_fat=8.0,
        moisture=10.0,
    )
    flags = hard_check(product, nutrients)
    assert any(f.code == "CRUDE_PROTEIN_BELOW_MIN" for f in flags), (
        "Rule should detect protein below minimum for adult dog"
    )

    # Compliant product — no flags
    nutrients_ok = NutrientValues(
        crude_protein=22.0,
        crude_fat=8.0,
        moisture=10.0,
    )
    flags_ok = hard_check(product, nutrients_ok)
    critical_ok = [f for f in flags_ok if f.severity.value == "CRITICAL"]
    assert len(critical_ok) == 0, f"No critical flags expected, got: {critical_ok}"
