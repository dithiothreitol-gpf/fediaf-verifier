"""Shared test fixtures."""

import pytest

from fediaf_verifier.config import AppSettings
from fediaf_verifier.models import (
    ComplianceStatus,
    EULabellingCheck,
    ExtractionConfidence,
    FoodType,
    Lifestage,
    NutrientValues,
    Product,
    Species,
    VerificationReport,
)


@pytest.fixture
def settings() -> AppSettings:
    """Test settings with dummy API key."""
    return AppSettings(anthropic_api_key="sk-ant-test-key-for-testing", _env_file=None)  # type: ignore[call-arg]


@pytest.fixture
def dog_adult_dry() -> Product:
    return Product(
        species=Species.DOG, lifestage=Lifestage.ADULT, food_type=FoodType.DRY
    )


@pytest.fixture
def dog_puppy_dry() -> Product:
    return Product(
        species=Species.DOG, lifestage=Lifestage.PUPPY, food_type=FoodType.DRY
    )


@pytest.fixture
def cat_adult_wet() -> Product:
    return Product(
        species=Species.CAT, lifestage=Lifestage.ADULT, food_type=FoodType.WET
    )


@pytest.fixture
def cat_kitten_wet() -> Product:
    return Product(
        species=Species.CAT, lifestage=Lifestage.KITTEN, food_type=FoodType.WET
    )


@pytest.fixture
def compliant_nutrients() -> NutrientValues:
    """Dog adult dry — all above FEDIAF minimums."""
    return NutrientValues(
        crude_protein=22.0,
        crude_fat=8.0,
        crude_fibre=3.0,
        moisture=10.0,
        crude_ash=7.0,
        calcium=1.2,
        phosphorus=0.9,
    )


@pytest.fixture
def deficient_nutrients() -> NutrientValues:
    """Dog adult dry — protein below minimum (18% DM)."""
    return NutrientValues(
        crude_protein=15.0,
        crude_fat=8.0,
        moisture=10.0,
    )


@pytest.fixture
def eu_check_ok() -> EULabellingCheck:
    return EULabellingCheck(
        ingredients_listed=True,
        analytical_constituents_present=True,
        manufacturer_info=True,
        net_weight_declared=True,
        species_clearly_stated=True,
        batch_or_date_present=True,
    )


@pytest.fixture
def sample_report(
    dog_adult_dry: Product,
    compliant_nutrients: NutrientValues,
    eu_check_ok: EULabellingCheck,
) -> VerificationReport:
    """A sample compliant verification report."""
    return VerificationReport(
        product=dog_adult_dry,
        extracted_nutrients=compliant_nutrients,
        ingredients_list=["chicken", "rice", "salmon oil"],
        extraction_confidence=ExtractionConfidence.HIGH,
        values_requiring_manual_check=[],
        compliance_score=95,
        status=ComplianceStatus.COMPLIANT,
        issues=[],
        eu_labelling_check=eu_check_ok,
        recommendations=[],
    )
