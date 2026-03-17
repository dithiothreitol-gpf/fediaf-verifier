"""Pydantic model validation tests."""

import pytest
from pydantic import ValidationError

from fediaf_verifier.models import (
    ComplianceStatus,
    CrossCheckResult,
    Discrepancy,
    EULabellingCheck,
    ExtractionConfidence,
    FoodType,
    Issue,
    Lifestage,
    MarketTrends,
    NutrientsOnly,
    NutrientValues,
    Positioning,
    Product,
    Severity,
    Species,
    VerificationReport,
)


class TestProduct:
    def test_minimal_valid(self):
        p = Product(
            species=Species.DOG,
            lifestage=Lifestage.ADULT,
            food_type=FoodType.DRY,
        )
        assert p.name is None
        assert p.brand is None

    def test_full_product(self):
        p = Product(
            name="Premium Adult",
            brand="BestPet",
            species=Species.CAT,
            lifestage=Lifestage.KITTEN,
            food_type=FoodType.WET,
            net_weight="400g",
        )
        assert p.species == Species.CAT

    def test_invalid_species_rejected(self):
        with pytest.raises(ValidationError):
            Product(
                species="hamster",  # type: ignore[arg-type]
                lifestage=Lifestage.ADULT,
                food_type=FoodType.DRY,
            )


class TestNutrientValues:
    def test_all_none_valid(self):
        nv = NutrientValues()
        assert nv.crude_protein is None
        assert nv.calcium is None

    def test_partial_values(self):
        nv = NutrientValues(crude_protein=22.0, moisture=10.0)
        assert nv.crude_protein == 22.0
        assert nv.crude_fat is None


class TestNutrientsOnly:
    def test_reading_notes_default_empty(self):
        no = NutrientsOnly()
        assert no.reading_notes == ""

    def test_with_reading_notes(self):
        no = NutrientsOnly(crude_protein=22.0, reading_notes="all clear")
        assert no.reading_notes == "all clear"


class TestIssue:
    def test_source_defaults_to_none(self):
        issue = Issue(
            severity=Severity.CRITICAL,
            code="TEST",
            description="test issue",
        )
        assert issue.source is None

    def test_source_can_be_set(self):
        issue = Issue(
            severity=Severity.WARNING,
            code="TEST",
            description="test",
            source="HARD_RULE",
        )
        assert issue.source == "HARD_RULE"


class TestVerificationReport:
    def test_compliance_score_must_be_0_100(self, sample_report):
        assert 0 <= sample_report.compliance_score <= 100

    def test_score_below_0_rejected(self):
        with pytest.raises(ValidationError):
            VerificationReport(
                product=Product(
                    species=Species.DOG,
                    lifestage=Lifestage.ADULT,
                    food_type=FoodType.DRY,
                ),
                extracted_nutrients=NutrientValues(),
                extraction_confidence=ExtractionConfidence.HIGH,
                compliance_score=-1,
                status=ComplianceStatus.COMPLIANT,
                eu_labelling_check=EULabellingCheck(
                    ingredients_listed=True,
                    analytical_constituents_present=True,
                    manufacturer_info=True,
                    net_weight_declared=True,
                    species_clearly_stated=True,
                    batch_or_date_present=True,
                ),
            )

    def test_score_above_100_rejected(self):
        with pytest.raises(ValidationError):
            VerificationReport(
                product=Product(
                    species=Species.DOG,
                    lifestage=Lifestage.ADULT,
                    food_type=FoodType.DRY,
                ),
                extracted_nutrients=NutrientValues(),
                extraction_confidence=ExtractionConfidence.HIGH,
                compliance_score=101,
                status=ComplianceStatus.COMPLIANT,
                eu_labelling_check=EULabellingCheck(
                    ingredients_listed=True,
                    analytical_constituents_present=True,
                    manufacturer_info=True,
                    net_weight_declared=True,
                    species_clearly_stated=True,
                    batch_or_date_present=True,
                ),
            )

    def test_market_trends_optional(self, sample_report):
        assert sample_report.market_trends is None

    def test_issues_default_empty(self, sample_report):
        assert sample_report.issues == []


class TestCrossCheckResult:
    def test_default_values(self):
        r = CrossCheckResult()
        assert r.passed is None
        assert r.discrepancies == []
        assert r.error is None

    def test_with_discrepancies(self):
        r = CrossCheckResult(
            passed=False,
            discrepancies=[
                Discrepancy(
                    nutrient="crude_protein",
                    main_value=22.0,
                    cross_value=20.0,
                    difference=2.0,
                )
            ],
        )
        assert r.passed is False
        assert len(r.discrepancies) == 1


class TestMarketTrends:
    def test_valid_market_trends(self):
        mt = MarketTrends(
            country="Polska",
            summary="Growing market for grain-free products.",
            positioning=Positioning.TRENDY,
            trend_notes=["Insect protein rising"],
        )
        assert mt.positioning == Positioning.TRENDY
