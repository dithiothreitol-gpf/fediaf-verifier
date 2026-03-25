"""Missing packaging elements detection and enrichment.

Compares detected elements against regulatory requirements
and suggests additions.
"""

from __future__ import annotations

from packaging_designer.generators.barcode import generate_ean13_svg
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
            "name": "Kod kreskowy EAN-13",
            "priority": ElementPriority.MANDATORY,
            "regulation": "Handel detaliczny",
            "description": "Kod kreskowy wymagany dla produktu detalicznego",
            "category": "regulatory",
        },
        {
            "id": "ingredients_list",
            "name": "Skład / Lista składników",
            "priority": ElementPriority.MANDATORY,
            "regulation": "EU 767/2009 Art.17",
            "description": "Lista składników w kolejności malejącej masy",
            "category": "regulatory",
        },
        {
            "id": "nutrition_table",
            "name": "Składniki analityczne",
            "priority": ElementPriority.MANDATORY,
            "regulation": "EU 767/2009 Art.17",
            "description": "Białko, tłuszcz, włókno, popiół, wilgotność",
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
            "name": "Data ważności",
            "priority": ElementPriority.MANDATORY,
            "regulation": "EU 767/2009 Art.17",
            "description": "Obszar na datę 'Najlepiej użyć przed...'",
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
            "name": "Zalecenia żywieniowe",
            "priority": ElementPriority.MANDATORY,
            "regulation": "EU 767/2009 Art.17",
            "description": "Tabela dawkowania wg masy ciała",
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
            "description": "Symbol zachęcający do utylizacji",
            "category": "regulatory",
        },
        {
            "id": "recycling_green_dot",
            "name": "Zielony Punkt",
            "priority": ElementPriority.OPTIONAL,
            "regulation": None,
            "description": "Symbol Green Dot (w krajach wymagających)",
            "category": "regulatory",
        },
    ],
    ProductCategory.FOOD: [
        {
            "id": "ean_barcode",
            "name": "Kod kreskowy EAN-13",
            "priority": ElementPriority.MANDATORY,
            "regulation": "Handel detaliczny",
            "description": "Kod kreskowy wymagany dla produktu detalicznego",
            "category": "regulatory",
        },
        {
            "id": "ingredients_list",
            "name": "Lista składników",
            "priority": ElementPriority.MANDATORY,
            "regulation": "EU 1169/2011 Art.9",
            "description": "Lista składników w kolejności malejącej masy",
            "category": "regulatory",
        },
        {
            "id": "nutrition_table",
            "name": "Tabela wartości odżywczych",
            "priority": ElementPriority.MANDATORY,
            "regulation": "EU 1169/2011 Art.9",
            "description": "Energia, tłuszcz, węglowodany, białko, sól",
            "category": "regulatory",
        },
        {
            "id": "net_weight",
            "name": "Waga netto",
            "priority": ElementPriority.MANDATORY,
            "regulation": "EU 1169/2011 Art.9",
            "description": "Ilość netto żywności",
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
            "name": "Data minimalnej trwałości",
            "priority": ElementPriority.MANDATORY,
            "regulation": "EU 1169/2011 Art.9",
            "description": "'Najlepiej spożyć przed...' lub 'Należy spożyć do...'",
            "category": "regulatory",
        },
        {
            "id": "allergens",
            "name": "Alergeny",
            "priority": ElementPriority.MANDATORY,
            "regulation": "EU 1169/2011 Art.21",
            "description": "Alergeny wyróżnione w składzie (bold/underline)",
            "category": "regulatory",
        },
        {
            "id": "recycling_mobius",
            "name": "Symbol recyklingu",
            "priority": ElementPriority.RECOMMENDED,
            "regulation": "EU PPWR 2025/40",
            "description": "Oznakowanie materiałowe opakowania",
            "category": "regulatory",
        },
    ],
}

# Default for categories not explicitly listed
_DEFAULT_REQUIRED = [
    {
        "id": "ean_barcode",
        "name": "Kod kreskowy EAN-13",
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
