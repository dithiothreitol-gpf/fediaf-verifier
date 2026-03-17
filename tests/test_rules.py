"""Unit tests for deterministic FEDIAF rules. No API calls needed."""

import pytest

from fediaf_verifier.models import (
    FoodType,
    Issue,
    Lifestage,
    NutrientValues,
    Product,
    Severity,
    Species,
)
from fediaf_verifier.rules import convert_to_dm, hard_check, merge_with_ai_issues


class TestConvertToDM:
    def test_dry_food_default_moisture(self):
        """Default moisture 10% -> value * 1/0.9."""
        result = convert_to_dm(18.0, None)
        assert result == pytest.approx(20.0)

    def test_wet_food_high_moisture(self):
        """75% moisture -> value / 0.25."""
        result = convert_to_dm(8.0, 75.0)
        assert result == pytest.approx(32.0)

    def test_zero_moisture(self):
        """0% moisture -> value unchanged."""
        assert convert_to_dm(18.0, 0.0) == pytest.approx(18.0)

    def test_moisture_100_returns_raw(self):
        """100% moisture is invalid — return raw value."""
        assert convert_to_dm(18.0, 100.0) == 18.0

    def test_typical_dry_food(self):
        """10% moisture -> divide by 0.9."""
        assert convert_to_dm(22.5, 10.0) == pytest.approx(25.0)


class TestHardCheck:
    def test_dog_adult_protein_below_min(self, dog_adult_dry, deficient_nutrients):
        flags = hard_check(dog_adult_dry, deficient_nutrients)
        codes = [f.code for f in flags]
        assert "CRUDE_PROTEIN_BELOW_MIN" in codes

    def test_dog_adult_compliant(self, dog_adult_dry, compliant_nutrients):
        flags = hard_check(dog_adult_dry, compliant_nutrients)
        critical = [f for f in flags if f.severity == Severity.CRITICAL]
        assert len(critical) == 0

    def test_unknown_species_returns_empty(self):
        product = Product(
            species=Species.UNKNOWN,
            lifestage=Lifestage.ADULT,
            food_type=FoodType.DRY,
        )
        nutrients = NutrientValues(crude_protein=5.0, moisture=10.0)
        assert hard_check(product, nutrients) == []

    def test_unknown_lifestage_returns_empty(self):
        product = Product(
            species=Species.DOG,
            lifestage=Lifestage.UNKNOWN,
            food_type=FoodType.DRY,
        )
        nutrients = NutrientValues(crude_protein=5.0, moisture=10.0)
        assert hard_check(product, nutrients) == []

    def test_all_none_nutrients_returns_empty(self, dog_adult_dry):
        nutrients = NutrientValues()
        assert hard_check(dog_adult_dry, nutrients) == []

    def test_flags_have_hard_rule_source(self, dog_adult_dry, deficient_nutrients):
        flags = hard_check(dog_adult_dry, deficient_nutrients)
        for flag in flags:
            assert flag.source == "HARD_RULE"

    def test_calcium_above_max_puppy(self, dog_puppy_dry):
        nutrients = NutrientValues(calcium=3.5, moisture=10.0)
        flags = hard_check(dog_puppy_dry, nutrients)
        codes = [f.code for f in flags]
        assert "CALCIUM_ABOVE_MAX" in codes

    @pytest.mark.parametrize(
        "species,lifestage,protein_raw,moisture,should_flag",
        [
            # Dog puppy: min 22.5% DM. 20% as-fed / 0.9 = 22.2% DM -> below
            ("dog", "puppy", 20.0, 10.0, True),
            # Dog puppy: 25% as-fed / 0.9 = 27.8% DM -> above
            ("dog", "puppy", 25.0, 10.0, False),
            # Cat adult: min 25% DM. 4% as-fed / 0.2 = 20% DM -> below
            ("cat", "adult", 4.0, 80.0, True),
            # Cat adult: 6% as-fed / 0.2 = 30% DM -> above
            ("cat", "adult", 6.0, 80.0, False),
            # Dog adult: min 18% DM. 16% as-fed / 0.9 = 17.8% DM -> below
            ("dog", "adult", 16.0, 10.0, True),
            # Dog adult: 20% as-fed / 0.9 = 22.2% DM -> above
            ("dog", "adult", 20.0, 10.0, False),
        ],
    )
    def test_protein_minimums_parametrized(
        self, species, lifestage, protein_raw, moisture, should_flag
    ):
        product = Product(
            species=Species(species),
            lifestage=Lifestage(lifestage),
            food_type=FoodType.DRY,
        )
        nutrients = NutrientValues(crude_protein=protein_raw, moisture=moisture)
        flags = hard_check(product, nutrients)
        has_protein_flag = any(f.code == "CRUDE_PROTEIN_BELOW_MIN" for f in flags)
        assert has_protein_flag == should_flag


class TestMergeWithAIIssues:
    def test_deduplicates_by_code(self):
        ai_issues = [
            Issue(
                severity=Severity.CRITICAL,
                code="CRUDE_PROTEIN_BELOW_MIN",
                description="AI detected low protein",
                source="AI",
            )
        ]
        hard_flags = [
            Issue(
                severity=Severity.CRITICAL,
                code="CRUDE_PROTEIN_BELOW_MIN",
                description="Rule detected low protein",
                source="HARD_RULE",
            )
        ]
        merged = merge_with_ai_issues(ai_issues, hard_flags)
        # Hard flag with same code should not be duplicated
        assert len(merged) == 1
        assert merged[0].source == "AI"

    def test_adds_unique_hard_flags(self):
        ai_issues = [
            Issue(
                severity=Severity.WARNING,
                code="SOME_OTHER_ISSUE",
                description="Some issue",
                source="AI",
            )
        ]
        hard_flags = [
            Issue(
                severity=Severity.CRITICAL,
                code="CALCIUM_ABOVE_MAX",
                description="Calcium too high",
                source="HARD_RULE",
            )
        ]
        merged = merge_with_ai_issues(ai_issues, hard_flags)
        assert len(merged) == 2
        codes = {i.code for i in merged}
        assert "SOME_OTHER_ISSUE" in codes
        assert "CALCIUM_ABOVE_MAX" in codes

    def test_empty_inputs(self):
        assert merge_with_ai_issues([], []) == []
