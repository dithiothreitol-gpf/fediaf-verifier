"""Back label generator \u2014 AI generates regulatory back side content.

Takes the front side analysis + product data and generates complete
back label text: ingredients, analytical constituents, feeding guidelines,
manufacturer info, storage instructions, etc.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from loguru import logger
from pydantic import BaseModel, Field

from fediaf_verifier.models.base import NullSafeBase

if TYPE_CHECKING:
    from fediaf_verifier.providers import AIProvider
    from packaging_designer.models.design_elements import DesignAnalysis


class BackLabelSection(NullSafeBase):
    """Single section of the back label."""

    section_id: str = Field(default="", description="Key: composition, analytical, feeding, etc.")
    title: str = Field(default="", description="Section title in target language")
    content: str = Field(default="", description="Section content text")
    is_table: bool = Field(default=False, description="Whether content is tabular data")


class FeedingRow(NullSafeBase):
    """Single row in feeding guidelines table."""

    weight_range: str = Field(default="")
    daily_amount: str = Field(default="")


class BackLabelContent(NullSafeBase):
    """Complete back label content."""

    sections: list[BackLabelSection] = Field(default_factory=list)
    feeding_table: list[FeedingRow] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    complete_text: str = Field(default="", description="All sections as final text")


BACK_LABEL_PROMPT = """\
You are an expert in EU food/pet food packaging regulations.
Generate complete BACK LABEL text for the following product packaging.

PRODUCT INFO:
- Product name: {product_name}
- Brand: {brand_name}
- Category: {product_category}
- Package type: {package_type}
- Target language: {language}

FRONT SIDE ANALYSIS:
- Detected texts: {front_texts}
- Existing elements: {existing_elements}

ADDITIONAL CONTEXT FROM USER:
{user_context}

Generate a complete back label with ALL mandatory sections for {product_category} in {language}.
Return JSON matching this schema:

{{
  "sections": [
    {{
      "section_id": "composition",
      "title": "<title in {language}>",
      "content": "<ingredients list, descending by weight>",
      "is_table": false
    }},
    {{
      "section_id": "analytical_constituents",
      "title": "<title in {language}>",
      "content": "<protein X%, fat X%, fibre X%, ash X%, moisture X%>",
      "is_table": false
    }},
    {{
      "section_id": "additives",
      "title": "<title in {language}>",
      "content": "<nutritional/technological additives>",
      "is_table": false
    }},
    {{
      "section_id": "feeding_guidelines",
      "title": "<title in {language}>",
      "content": "<intro text for feeding table>",
      "is_table": true
    }},
    {{
      "section_id": "storage",
      "title": "<title in {language}>",
      "content": "<storage instructions>",
      "is_table": false
    }},
    {{
      "section_id": "manufacturer",
      "title": "<title in {language}>",
      "content": "<manufacturer name, address, contact>",
      "is_table": false
    }},
    {{
      "section_id": "best_before",
      "title": "",
      "content": "<best before / use by text with placeholder>",
      "is_table": false
    }},
    {{
      "section_id": "lot",
      "title": "",
      "content": "<LOT number placeholder>",
      "is_table": false
    }}
  ],
  "feeding_table": [
    {{"weight_range": "2-4 kg", "daily_amount": "40-70 g"}},
    {{"weight_range": "4-6 kg", "daily_amount": "70-100 g"}}
  ],
  "warnings": ["<any mandatory warnings>"],
  "complete_text": "<all sections combined as final label text>"
}}

RULES:
- Use realistic, regulatory-compliant content
- For pet food: follow EU 767/2009 and FEDIAF guidelines
- For food: follow EU 1169/2011
- If user didn't provide ingredients, generate plausible ones based on product name
- Feeding table should have 4-6 rows
- Include placeholder markers: [DATA], [LOT], [EAN] where dynamic content goes
- Return ONLY JSON, no markdown fences
"""


def generate_back_label(
    analysis: DesignAnalysis,
    provider: AIProvider,
    language: str = "pl",
    user_context: str = "",
    max_tokens: int = 4096,
) -> BackLabelContent:
    """Generate back label content using AI.

    Args:
        analysis: Front side design analysis.
        provider: AI provider instance.
        language: Target language code.
        user_context: Additional product info from user.
        max_tokens: Max response tokens.

    Returns:
        BackLabelContent with all sections.
    """
    spec = analysis.package_spec
    front_texts = "; ".join(
        f"[{tb.role}] {tb.content}" for tb in analysis.text_blocks
    )

    prompt = BACK_LABEL_PROMPT.format(
        product_name=spec.product_name or "Unknown Product",
        brand_name=spec.brand_name or "Unknown Brand",
        product_category=spec.product_category.value,
        package_type=spec.package_type.value,
        language=language,
        front_texts=front_texts or "none detected",
        existing_elements=", ".join(analysis.existing_elements) or "none",
        user_context=user_context or "No additional context provided.",
    )

    logger.info("Generating back label content...")
    raw = provider.call(prompt=prompt, max_tokens=max_tokens)

    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    data = json.loads(text)
    result = BackLabelContent.model_validate(data)

    logger.info(
        f"Back label generated: {len(result.sections)} sections, "
        f"{len(result.feeding_table)} feeding rows"
    )
    return result
