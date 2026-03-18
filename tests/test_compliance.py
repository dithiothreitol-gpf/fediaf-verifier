"""Deterministic compliance engine tests. No API calls needed."""


from fediaf_verifier.compliance import (
    analyze_compliance,
    build_cross_check_result,
    calculate_score,
)
from fediaf_verifier.models import (
    ComplianceStatus,
    Issue,
    LabelExtraction,
    SecondaryCheck,
    Severity,
)


class TestCalculateScore:
    def test_no_issues_gives_100(self):
        assert calculate_score([]) == 100

    def test_critical_deducts_15(self):
        issues = [
            Issue(severity=Severity.CRITICAL, code="X", description="x", source="RULE")
        ]
        assert calculate_score(issues) == 85

    def test_warning_deducts_5(self):
        issues = [
            Issue(severity=Severity.WARNING, code="X", description="x", source="RULE")
        ]
        assert calculate_score(issues) == 95

    def test_info_deducts_1(self):
        issues = [
            Issue(severity=Severity.INFO, code="X", description="x", source="RULE")
        ]
        assert calculate_score(issues) == 99

    def test_score_floors_at_0(self):
        issues = [
            Issue(severity=Severity.CRITICAL, code=f"X{i}", description="x", source="RULE")
            for i in range(10)
        ]
        assert calculate_score(issues) == 0

    def test_mixed_severities(self):
        issues = [
            Issue(severity=Severity.CRITICAL, code="A", description="x", source="RULE"),
            Issue(severity=Severity.WARNING, code="B", description="x", source="RULE"),
            Issue(severity=Severity.INFO, code="C", description="x", source="RULE"),
        ]
        assert calculate_score(issues) == 100 - 15 - 5 - 1  # 79


class TestAnalyzeCompliance:
    def test_compliant_dog_adult(self):
        ext = LabelExtraction(
            species="dog",
            lifestage="adult",
            food_type_text="dry",
            crude_protein=22.0,
            crude_fat=8.0,
            moisture=10.0,
            calcium=1.2,
            phosphorus=0.9,
            has_ingredients_list=True,
            has_analytical_constituents=True,
            has_manufacturer_info=True,
            has_net_weight=True,
            has_species_stated=True,
            has_batch_number=True,
            has_feeding_guidelines=True,
            has_free_contact_info=True,
            has_establishment_number=True,
            product_classification_text="karma pelnoporcjowa",
        )
        result = analyze_compliance(ext)
        assert result.status == ComplianceStatus.COMPLIANT
        assert result.score >= 70
        assert result.product.species.value == "dog"

    def test_protein_below_min_detected(self):
        ext = LabelExtraction(
            species="dog",
            lifestage="adult",
            food_type_text="dry",
            crude_protein=15.0,
            crude_fat=8.0,
            moisture=10.0,
            has_ingredients_list=True,
            has_analytical_constituents=True,
            has_manufacturer_info=True,
            has_net_weight=True,
            has_species_stated=True,
            has_batch_number=True,
        )
        result = analyze_compliance(ext)
        codes = [i.code for i in result.issues]
        assert "CRUDE_PROTEIN_BELOW_MIN" in codes

    def test_missing_eu_elements_flagged(self):
        ext = LabelExtraction(
            species="cat",
            lifestage="adult",
            food_type_text="wet",
            # All has_* default to False
        )
        result = analyze_compliance(ext)
        codes = [i.code for i in result.issues]
        assert "EU_NO_INGREDIENTS" in codes
        assert "EU_NO_MANUFACTURER" in codes

    def test_polish_species_mapped(self):
        ext = LabelExtraction(species="pies", lifestage="dorosly", food_type_text="sucha")
        result = analyze_compliance(ext)
        assert result.product.species.value == "dog"
        assert result.product.lifestage.value == "adult"
        assert result.product.food_type.value == "dry"

    def test_grain_free_claim_violated(self):
        ext = LabelExtraction(
            species="dog",
            lifestage="adult",
            food_type_text="dry",
            ingredients=["kurczak", "ryż", "marchew"],
            claims=["bez zbóż"],
            has_ingredients_list=True,
            has_analytical_constituents=True,
            has_manufacturer_info=True,
            has_net_weight=True,
            has_species_stated=True,
            has_batch_number=True,
        )
        result = analyze_compliance(ext)
        codes = [i.code for i in result.issues]
        assert "CLAIM_GRAIN_FREE_VIOLATED" in codes

    def test_raw_product_without_warning(self):
        ext = LabelExtraction(
            species="dog",
            lifestage="adult",
            food_type_text="wet",
            is_raw_product=True,
            has_raw_warnings=False,
            has_ingredients_list=True,
            has_analytical_constituents=True,
            has_manufacturer_info=True,
            has_net_weight=True,
            has_species_stated=True,
            has_batch_number=True,
        )
        result = analyze_compliance(ext)
        codes = [i.code for i in result.issues]
        assert "PKG_RAW_NO_WARNING" in codes


class TestBuildCrossCheckResult:
    def test_matching_values_pass(self):
        ext = LabelExtraction(crude_protein=22.0, crude_fat=8.0)
        sec = SecondaryCheck(cross_crude_protein=22.0, cross_crude_fat=8.0)
        result = build_cross_check_result(ext, sec, tolerance=0.5)
        assert result.passed is True
        assert len(result.discrepancies) == 0

    def test_discrepancy_detected(self):
        ext = LabelExtraction(crude_protein=22.0)
        sec = SecondaryCheck(cross_crude_protein=25.0)
        result = build_cross_check_result(ext, sec, tolerance=0.5)
        assert result.passed is False
        assert len(result.discrepancies) == 1
        assert result.discrepancies[0].difference == 3.0

    def test_none_secondary_returns_not_executed(self):
        ext = LabelExtraction(crude_protein=22.0)
        result = build_cross_check_result(ext, None, tolerance=0.5)
        assert result.passed is None
