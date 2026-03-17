"""Linguistic verification of label text — spelling, grammar, diacritics, terminology.

Sends a separate API call focused on text quality analysis.
Non-blocking: errors do not stop the main pipeline.
"""

import anthropic
from loguru import logger

from fediaf_verifier.config import AppSettings
from fediaf_verifier.models import LinguisticCheckResult, LinguisticReport
from fediaf_verifier.prompts import LINGUISTIC_CHECK_PROMPT
from fediaf_verifier.utils import extract_json


def perform_linguistic_check(
    label_b64: str,
    media_type: str,
    client: anthropic.Anthropic,
    settings: AppSettings,
) -> LinguisticCheckResult:
    """Perform linguistic verification of label text.

    Analyzes spelling, grammar, punctuation, diacritical marks,
    and terminology consistency. Auto-detects language.

    Args:
        label_b64: Label image/document encoded as base64.
        media_type: MIME type of the label.
        client: Anthropic client instance.
        settings: Application settings.

    Returns:
        LinguisticCheckResult. On failure, returns performed=False — non-blocking.
    """
    try:
        # Build label content block based on media type
        if media_type == "application/pdf":
            label_block: dict = {
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

        prompt_with_json = (
            LINGUISTIC_CHECK_PROMPT
            + "\n\nOdpowiedz WYLACZNIE poprawnym JSON (bez markdown)."
        )

        response = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=settings.max_tokens_linguistic,
            messages=[
                {
                    "role": "user",
                    "content": [
                        label_block,
                        {"type": "text", "text": prompt_with_json},
                    ],
                }
            ],
        )

        raw_text = response.content[0].text
        json_text = extract_json(raw_text)
        report = LinguisticReport.model_validate_json(json_text)

        logger.info(
            "Linguistic check completed: {} issues found, quality={}",
            len(report.issues),
            report.overall_quality,
        )

        return LinguisticCheckResult(performed=True, report=report)

    except anthropic.APIError as e:
        logger.warning("Linguistic check API error (non-blocking): {}", e)
        return LinguisticCheckResult(
            performed=False,
            error=str(e),
        )
    except Exception as e:
        logger.warning("Linguistic check unexpected error (non-blocking): {}", e)
        return LinguisticCheckResult(
            performed=False,
            error=str(e),
        )
