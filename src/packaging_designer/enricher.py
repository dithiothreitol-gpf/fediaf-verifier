"""Missing packaging elements detection and enrichment.

Compares detected elements against regulatory requirements
and suggests additions.
"""

from __future__ import annotations

from packaging_designer.generators.barcode_gen import generate_ean13_svg
from packaging_designer.generators.symbols import (
    get_symbol_size_mm,
    load_symbol_svg,
)
from packaging_designer.models.design_elements import DesignAnalysis
from packaging_designer.models.enrichment import (
    ElementPriority,
    EnrichmentResult,
    GeneratedAsset,
    MissingElement,
)
from packaging_designer.models.package_spec import ProductCategory

# Required elements per product category
REQUIRED_ELEMENTS: dict[ProductCategory, list[dict]] = {
    ProductCategory.PET_FOOD: [
        {
            "id": "ean_barcode",
            "name": "Kod kreskowy EAN\u201113",
            "priority": ElementPriority.MANDATORY,
            "regulation": "Handel detaliczny",
            "description": "Kod kreskowy wymagany dla produktu detalicznego",
            "category": "regulatory",
        },
        {
            "id": "ingredients_list",
            "name": "Sk\u0142ad / Lista sk\u0142adnik\u00f3w",
            "priority": ElementPriority.MANDATORY,
            "regulation": "EU 767/2009 Art.17",
            "description": "Lista sk\u0142adnik\u00f3w w kolejno\u015bci malej\u0105cej masy",
            "category": "regulatory",
        },
        {
            "id": "nutrition_table",
            "name": "Sk\u0142adniki analityczne",
            "priority": ElementPriority.MANDATORY,
            "regulation": "EU 767/2009 Art.17",
            "description": "Bia\u0142ko, t\u0142uszcz, w\u0142\u00f3kno, popi\u00f3\u0142, wilgotno\u015b\u0107",
            "category": "regulatory",
        },
        {
            "id": "net_weight",
            "name": "Waga netto",
            "priority": ElementPriority.MANDATORY,
            "regulation": "EU 767/2009 Art.17",
            "description": "Masa netto produktu z symbolem e",
            "category": "regulatory",
        },
        {
            "id": "manufacturer_info",
            "name": "Dane producenta",
            "priority": ElementPriority.MANDATORY,
            "regulation": "EU 767/2009 Art.17",
            "description": "Nazwa i adres producenta/dystrybutora",
            "category": "regulatory",
        },
        {
            "id": "best_before",
            "name": "Data wa\u017cno\u015bci",
            "priority": ElementPriority.MANDATORY,
            "regulation": "EU 767/2009 Art.17",
            "description": "Obszar na dat\u0119 \u201eNajlepiej u\u017cy\u0107 przed\u2026\u201d",
            "category": "regulatory",
        },
        {
            "id": "lot_number",
            "name": "Numer partii / LOT",
            "priority": ElementPriority.MANDATORY,
            "regulation": "EU 767/2009 Art.17",
            "description": "Numer partii do identyfikacji",
            "category": "regulatory",
        },
        {
            "id": "feeding_guidelines",
            "name": "Zalecenia \u017cywieniowe",
            "priority": ElementPriority.MANDATORY,
            "regulation": "EU 767/2009 Art.17",
            "description": "Tabela dawkowania wg masy cia\u0142a",
            "category": "regulatory",
        },
        {
            "id": "country_of_origin",
            "name": "Kraj pochodzenia",
            "priority": ElementPriority.RECOMMENDED,
            "regulation": "EU 767/2009",
            "description": "Oznaczenie kraju produkcji",
            "category": "regulatory",
        },
        {
            "id": "recycling_mobius",
            "name": "Symbol recyklingu (Mobius loop)",
            "priority": ElementPriority.RECOMMENDED,
            "regulation": "EU PPWR 2025/40",
            "description": "Symbol recyklingu opakowania",
            "category": "regulatory",
        },
        {
            "id": "recycling_tidyman",
            "name": "Tidyman",
            "priority": ElementPriority.OPTIONAL,
            "regulation": None,
            "description": "Symbol zach\u0119caj\u0105cy do utylizacji",
            "category": "regulatory",
        },
        {
            "id": "recycling_green_dot",
            "name": "Zielony Punkt",
            "priority": ElementPriority.OPTIONAL,
            "regulation": None,
            "description": "Symbol Green Dot (w krajach wymagaj\u0105cych)",
            "category": "regulatory",
        },
    ],
    ProductCategory.FOOD: [
        {
            "id": "ean_barcode",
            "name": "Kod kreskowy EAN\u201113",
            "priority": ElementPriority.MANDATORY,
            "regulation": "Handel detaliczny",
            "description": "Kod kreskowy wymagany dla produktu detalicznego",
            "category": "regulatory",
        },
        {
            "id": "ingredients_list",
            "name": "Lista sk\u0142adnik\u00f3w",
            "priority": ElementPriority.MANDATORY,
            "regulation": "EU 1169/2011 Art.9",
            "description": "Lista sk\u0142adnik\u00f3w w kolejno\u015bci malej\u0105cej masy",
            "category": "regulatory",
        },
        {
            "id": "nutrition_table",
            "name": "Tabela warto\u015bci od\u017cywczych",
            "priority": ElementPriority.MANDATORY,
            "regulation": "EU 1169/2011 Art.9",
            "description": "Energia, t\u0142uszcz, w\u0119glowodany, bia\u0142ko, s\u00f3l",
            "category": "regulatory",
        },
        {
            "id": "net_weight",
            "name": "Waga netto",
            "priority": ElementPriority.MANDATORY,
            "regulation": "EU 1169/2011 Art.9",
            "description": "Ilo\u015b\u0107 netto \u017cywno\u015bci",
            "category": "regulatory",
        },
        {
            "id": "manufacturer_info",
            "name": "Dane producenta",
            "priority": ElementPriority.MANDATORY,
            "regulation": "EU 1169/2011 Art.9",
            "description": "Nazwa i adres podmiotu odpowiedzialnego",
            "category": "regulatory",
        },
        {
            "id": "best_before",
            "name": "Data minimalnej trwa\u0142o\u015bci",
            "priority": ElementPriority.MANDATORY,
            "regulation": "EU 1169/2011 Art.9",
            "description": "\u201eNajlepiej spo\u017cy\u0107 przed\u2026\u201d lub \u201eNale\u017cy spo\u017cy\u0107 do\u2026\u201d",
            "category": "regulatory",
        },
        {
            "id": "allergens",
            "name": "Alergeny",
            "priority": ElementPriority.MANDATORY,
            "regulation": "EU 1169/2011 Art.21",
            "description": "Alergeny wyr\u00f3\u017cnione w sk\u0142adzie (bold/underline)",
            "category": "regulatory",
        },
        {
            "id": "recycling_mobius",
            "name": "Symbol recyklingu",
            "priority": ElementPriority.RECOMMENDED,
            "regulation": "EU PPWR 2025/40",
            "description": "Oznakowanie materia\u0142owe opakowania",
            "category": "regulatory",
        },
    ],
}

# Default for categories not explicitly listed
_DEFAULT_REQUIRED = [
    {
        "id": "ean_barcode",
        "name": "Kod kreskowy EAN\u201113",
        "priority": ElementPriority.RECOMMENDED,
        "regulation": None,
        "description": "Kod kreskowy produktu",
        "category": "regulatory",
    },
    {
        "id": "recycling_mobius",
        "name": "Symbol recyklingu",
        "priority": ElementPriority.RECOMMENDED,
        "regulation": "EU PPWR 2025/40",
        "description": "Symbol recyklingu opakowania",
        "category": "regulatory",
    },
]


def detect_missing_elements(analysis: DesignAnalysis) -> list[MissingElement]:
    """Compare detected elements against requirements and return missing ones."""
    category = analysis.package_spec.product_category
    required = REQUIRED_ELEMENTS.get(category, _DEFAULT_REQUIRED)

    existing_ids = set(analysis.existing_elements)
    missing = []

    for req in required:
        if req["id"] not in existing_ids:
            missing.append(
                MissingElement(
                    element_id=req["id"],
                    display_name=req["name"],
                    priority=req["priority"],
                    regulation=req.get("regulation"),
                    description=req["description"],
                    category=req.get("category", "regulatory"),
                )
            )

    # Sort: mandatory first, then recommended, then optional
    priority_order = {
        ElementPriority.MANDATORY: 0,
        ElementPriority.RECOMMENDED: 1,
        ElementPriority.OPTIONAL: 2,
    }
    missing.sort(key=lambda m: priority_order.get(m.priority, 99))

    return missing


def generate_selected_assets(
    selected_ids: list[str],
    ean_number: str | None = None,
) -> list[GeneratedAsset]:
    """Generate SVG assets for selected missing elements.

    Args:
        selected_ids: List of element IDs to generate.
        ean_number: EAN-13 number (required if 'ean_barcode' selected).

    Returns:
        List of generated assets with SVG content.
    """
    assets = []

    for element_id in selected_ids:
        if element_id == "ean_barcode" and ean_number:
            svg = generate_ean13_svg(ean_number)
            assets.append(
                GeneratedAsset(
                    element_id="ean_barcode",
                    file_name="ean_barcode.svg",
                    svg_content=svg,
                    width_mm=37,
                    height_mm=26,
                )
            )
        elif element_id.startswith("recycling_") or element_id in ("ce_mark", "triman"):
            svg = load_symbol_svg(element_id)
            if svg:
                size = get_symbol_size_mm(element_id)
                assets.append(
                    GeneratedAsset(
                        element_id=element_id,
                        file_name=f"{element_id}.svg",
                        svg_content=svg,
                        width_mm=size,
                        height_mm=size,
                    )
                )

    return assets


def enrich(
    analysis: DesignAnalysis,
    selected_ids: list[str] | None = None,
    ean_number: str | None = None,
) -> EnrichmentResult:
    """Full enrichment pipeline: detect missing → generate selected assets.

    If selected_ids is None, returns only the missing elements list
    (user hasn't selected yet).
    """
    missing = detect_missing_elements(analysis)

    if selected_ids is None:
        return EnrichmentResult(missing_elements=missing)

    assets = generate_selected_assets(selected_ids, ean_number=ean_number)

    return EnrichmentResult(
        missing_elements=missing,
        selected_additions=selected_ids,
        generated_assets=assets,
    )
