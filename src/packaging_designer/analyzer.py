"""Packaging concept image analyzer — uses Claude Vision to extract design data.

Analyzes an uploaded concept image and returns a structured DesignAnalysis
containing package type, dimensions, text blocks, graphic regions, colors,
and existing regulatory elements.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from packaging_designer.models.design_elements import DesignAnalysis
from packaging_designer.utils.color import hex_to_cmyk

if TYPE_CHECKING:
    from fediaf_verifier.providers import AIProvider

ANALYSIS_PROMPT = """\
You are an expert packaging designer and print production specialist.
Analyze the attached product packaging concept image in detail.

Return a JSON object matching this EXACT schema (no markdown, no explanation):

{
  "package_spec": {
    "package_type": "<box|pouch|standup_pouch|can|bottle|sachet|tube|label|tray|bag|other>",
    "dimensions": {
      "width_mm": <estimated width in mm>,
      "height_mm": <estimated height in mm>,
      "depth_mm": <estimated depth in mm or null>
    },
    "sides_visible": <number of packaging sides visible: 1 or 2>,
    "product_category": "<pet_food|food|cosmetics|supplements|other>",
    "dieline_type": "<tuck_end|pillow_pouch|standup|sleeve|wrap|label_roll|other|null>",
    "product_name": "<detected product name or empty string>",
    "brand_name": "<detected brand name or empty string>"
  },
  "text_blocks": [
    {
      "content": "<exact text content>",
      "bbox": [<x>, <y>, <width>, <height>],
      "font_style": "<serif_bold|serif_regular|sans_bold|sans_regular|display|handwritten|condensed>",
      "font_size_pt": <estimated size in points or null>,
      "role": "<product_name|tagline|brand|ingredients|weight|legal|nutritional|barcode_number|other>"
    }
  ],
  "graphic_regions": [
    {
      "description": "<what this element depicts>",
      "bbox": [<x>, <y>, <width>, <height>],
      "region_type": "<logo|product_photo|pattern|icon|illustration|background|decorative>"
    }
  ],
  "color_swatches": [
    {
      "name": "<descriptive name, e.g. 'Deep Navy'>",
      "hex": "<#RRGGBB>",
      "role": "<primary|secondary|accent|text|background>"
    }
  ],
  "existing_elements": [
    "<list of regulatory/informational elements already present on the packaging>"
  ],
  "typography_style": "<modern_sans|classic_serif|display_decorative|handwritten|mixed>",
  "layout_description": "<brief description of the visual layout and hierarchy>",
  "ai_summary": "<2-3 sentence summary of the packaging concept>"
}

RULES FOR BOUNDING BOXES:
- All bbox values are normalized to 0-1000 range
- Origin is TOP-LEFT corner of the image
- Format: [x, y, width, height] where x,y is top-left of the element
- Be as precise as possible with element boundaries

RULES FOR COLORS:
- Extract 4-8 most significant colors from the design
- Include background color, primary text color, and accent colors
- Use accurate hex values

RULES FOR EXISTING ELEMENTS:
Use these standard IDs when detected:
- "ean_barcode" - EAN/UPC barcode
- "qr_code" - QR code
- "recycling_mobius" - Mobius loop / recycling arrows
- "recycling_tidyman" - Tidyman (person throwing trash)
- "recycling_pao" - Period After Opening symbol
- "recycling_green_dot" - Green Dot (Der Grune Punkt)
- "nutrition_table" - Nutritional information table
- "ingredients_list" - Ingredients/composition list
- "feeding_guidelines" - Feeding/usage guidelines
- "manufacturer_info" - Manufacturer name and address
- "net_weight" - Net weight declaration
- "best_before" - Best before / expiry date area
- "lot_number" - Batch/LOT number
- "country_of_origin" - Country of origin statement
- "ce_mark" - CE marking
- "organic_logo" - Organic certification logo

IMPORTANT: Return ONLY the JSON object, no markdown code fences, no explanation.
"""


def analyze_concept(
    image_bytes: bytes,
    media_type: str,
    provider: AIProvider,
    max_tokens: int = 4096,
    product_context: str = "",
) -> DesignAnalysis:
    """Analyze a packaging concept image using AI Vision.

    Args:
        image_bytes: Raw image bytes (PNG/JPG/PDF).
        media_type: MIME type of the image.
        provider: AI provider instance (Claude/GPT/Gemini).
        max_tokens: Max tokens for response.
        product_context: Optional additional context about the product.

    Returns:
        DesignAnalysis with all extracted design data.
    """
    media_b64 = base64.b64encode(image_bytes).decode("utf-8")

    prompt = ANALYSIS_PROMPT
    if product_context:
        prompt += f"\n\nADDITIONAL PRODUCT CONTEXT:\n{product_context}"

    logger.info("Analyzing packaging concept image...")
    raw_response = provider.call(
        prompt=prompt,
        media_b64=media_b64,
        media_type=media_type,
        max_tokens=max_tokens,
    )

    # Strip markdown code fences if present
    text = raw_response.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    data = json.loads(text)

    # Enrich color swatches with CMYK values
    for swatch in data.get("color_swatches", []):
        if "hex" in swatch and "cyan" not in swatch:
            c, m, y, k = hex_to_cmyk(swatch["hex"])
            swatch["cyan"] = c
            swatch["magenta"] = m
            swatch["yellow"] = y
            swatch["key"] = k

    analysis = DesignAnalysis.model_validate(data)
    logger.info(
        f"Analysis complete: {analysis.package_spec.package_type}, "
        f"{len(analysis.text_blocks)} text blocks, "
        f"{len(analysis.color_swatches)} colors, "
        f"{len(analysis.existing_elements)} existing elements"
    )
    return analysis


def analyze_from_file(
    file_path: str | Path,
    provider: AIProvider,
    max_tokens: int = 4096,
    product_context: str = "",
) -> DesignAnalysis:
    """Convenience: analyze from file path."""
    path = Path(file_path)
    image_bytes = path.read_bytes()

    suffix = path.suffix.lower()
    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".pdf": "application/pdf",
        ".webp": "image/webp",
    }
    media_type = media_types.get(suffix, "image/png")

    return analyze_concept(
        image_bytes=image_bytes,
        media_type=media_type,
        provider=provider,
        max_tokens=max_tokens,
        product_context=product_context,
    )
