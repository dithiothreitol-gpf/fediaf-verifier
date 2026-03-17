"""Cross-validation of numeric values — reliability Layer 2.

Sends a separate, simplified API call to read only the analytical constituents table.
Compares with the main extraction and flags discrepancies > tolerance.
"""

import anthropic
from loguru import logger

from fediaf_verifier.config import AppSettings
from fediaf_verifier.models import (
    NUTRIENT_FIELDS,
    CrossCheckResult,
    Discrepancy,
    NutrientsOnly,
    NutrientValues,
)
from fediaf_verifier.prompts import CROSS_CHECK_PROMPT
from fediaf_verifier.utils import extract_json


def cross_check_nutrients(
    label_b64: str,
    media_type: str,
    main_nutrients: NutrientValues,
    client: anthropic.Anthropic,
    settings: AppSettings,
) -> CrossCheckResult:
    """Perform an independent nutrient reading and compare with the main extraction.

    Args:
        label_b64: Label image/document encoded as base64.
        media_type: MIME type of the label (image/jpeg, image/png, application/pdf).
        main_nutrients: Nutrient values from the main AI verification.
        client: Anthropic client instance.
        settings: Application settings.

    Returns:
        CrossCheckResult with comparison outcome.
        On failure, returns CrossCheckResult(passed=None) — non-blocking.
    """
    try:
        # Build label content block based on media type
        if media_type == "application/pdf":
            label_block = {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": label_b64,
                },
            }
        else:
            label_block = {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": label_b64,
                },
            }

        prompt_with_schema = (
            CROSS_CHECK_PROMPT
            + "\n\nOdpowiedz WYLACZNIE poprawnym JSON (bez markdown). "
            "Pola: crude_protein, crude_fat, crude_fibre, moisture, "
            "crude_ash, calcium, phosphorus (liczby lub null), "
            "reading_notes (string)."
        )

        response = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=settings.max_tokens_cross_check,
            messages=[
                {
                    "role": "user",
                    "content": [
                        label_block,
                        {"type": "text", "text": prompt_with_schema},
                    ],
                }
            ],
        )

        raw_text = response.content[0].text
        json_text = extract_json(raw_text)
        cross_values = NutrientsOnly.model_validate_json(json_text)

        # Compare nutrient values
        discrepancies: list[Discrepancy] = []
        cross_values_dict: dict[str, float | None] = {}

        for field_name in NUTRIENT_FIELDS:
            main_val = getattr(main_nutrients, field_name)
            cross_val = getattr(cross_values, field_name)
            cross_values_dict[field_name] = cross_val

            if main_val is None or cross_val is None:
                continue

            diff = abs(float(main_val) - float(cross_val))
            if diff > settings.cross_check_tolerance:
                discrepancies.append(
                    Discrepancy(
                        nutrient=field_name,
                        main_value=main_val,
                        cross_value=cross_val,
                        difference=round(diff, 2),
                    )
                )

        logger.info(
            "Cross-check completed: {} discrepancies found",
            len(discrepancies),
        )

        return CrossCheckResult(
            passed=len(discrepancies) == 0,
            discrepancies=discrepancies,
            cross_check_values=cross_values_dict,
            reading_notes=cross_values.reading_notes,
        )

    except anthropic.APIError as e:
        logger.warning("Cross-check API error (non-blocking): {}", e)
        return CrossCheckResult(
            passed=None,
            reading_notes=f"Blad weryfikacji krzyzowej: {e}",
            error=str(e),
        )
    except Exception as e:
        logger.warning("Cross-check unexpected error (non-blocking): {}", e)
        return CrossCheckResult(
            passed=None,
            reading_notes=f"Blad weryfikacji krzyzowej: {e}",
            error=str(e),
        )
