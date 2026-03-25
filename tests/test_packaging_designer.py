"""Unit tests for packaging_designer module."""

from __future__ import annotations

import json

import pytest

# ---------------------------------------------------------------------------
# Utils: color conversion
# ---------------------------------------------------------------------------


class TestColorConversion:
    def test_hex_to_rgb_standard(self):
        from packaging_designer.utils.color import hex_to_rgb

        assert hex_to_rgb("#FF0000") == (255, 0, 0)
        assert hex_to_rgb("#00FF00") == (0, 255, 0)
        assert hex_to_rgb("#0000FF") == (0, 0, 255)
        assert hex_to_rgb("#FFFFFF") == (255, 255, 255)
        assert hex_to_rgb("#000000") == (0, 0, 0)

    def test_hex_to_rgb_no_hash(self):
        from packaging_designer.utils.color import hex_to_rgb

        assert hex_to_rgb("FF0000") == (255, 0, 0)

    def test_hex_to_rgb_short_format(self):
        from packaging_designer.utils.color import hex_to_rgb

        assert hex_to_rgb("#F00") == (255, 0, 0)
        assert hex_to_rgb("#FFF") == (255, 255, 255)

    def test_hex_to_rgb_invalid(self):
        from packaging_designer.utils.color import hex_to_rgb

        assert hex_to_rgb("invalid") == (0, 0, 0)
        assert hex_to_rgb("") == (0, 0, 0)

    def test_rgb_to_cmyk_black(self):
        from packaging_designer.utils.color import rgb_to_cmyk

        assert rgb_to_cmyk(0, 0, 0) == (0.0, 0.0, 0.0, 100.0)

    def test_rgb_to_cmyk_white(self):
        from packaging_designer.utils.color import rgb_to_cmyk

        assert rgb_to_cmyk(255, 255, 255) == (0.0, 0.0, 0.0, 0.0)

    def test_rgb_to_cmyk_pure_red(self):
        from packaging_designer.utils.color import rgb_to_cmyk

        c, m, y, k = rgb_to_cmyk(255, 0, 0)
        assert c == 0.0
        assert m == 100.0
        assert y == 100.0
        assert k == 0.0

    def test_rgb_to_cmyk_mid_blue(self):
        from packaging_designer.utils.color import rgb_to_cmyk

        c, m, y, k = rgb_to_cmyk(42, 92, 170)
        assert c > 50  # should be strongly cyan
        assert k > 0  # not pure

    def test_hex_to_cmyk(self):
        from packaging_designer.utils.color import hex_to_cmyk

        c, m, y, k = hex_to_cmyk("#FF0000")
        assert c == 0.0
        assert m == 100.0
        assert y == 100.0
        assert k == 0.0

    def test_mm_to_pt(self):
        from packaging_designer.utils.color import mm_to_pt

        # 1mm ≈ 2.835pt
        assert abs(mm_to_pt(1) - 2.835) < 0.01
        assert abs(mm_to_pt(210) - 595.28) < 0.1  # A4 width

    def test_pt_to_mm(self):
        from packaging_designer.utils.color import pt_to_mm

        assert abs(pt_to_mm(72) - 25.4) < 0.01  # 72pt = 1 inch = 25.4mm


# ---------------------------------------------------------------------------
# Utils: coordinate transforms
# ---------------------------------------------------------------------------


class TestCoordTransforms:
    def test_normalized_to_illustrator_top_left(self):
        from packaging_designer.utils.coords import normalized_to_illustrator

        # Top-left corner element
        x, y, w, h = normalized_to_illustrator(
            [0, 0, 100, 100], 500, 700
        )
        assert x == 0
        assert abs(y - (700 - 70)) < 0.1  # should be near top in AI coords
        assert abs(w - 50) < 0.1
        assert abs(h - 70) < 0.1

    def test_normalized_to_illustrator_center(self):
        from packaging_designer.utils.coords import normalized_to_illustrator

        x, y, w, h = normalized_to_illustrator(
            [500, 500, 200, 200], 500, 700
        )
        assert abs(x - 250) < 0.1  # center horizontally
        # Y should be near middle after flip

    def test_normalized_to_idml_passthrough(self):
        from packaging_designer.utils.coords import normalized_to_idml

        # IDML has same orientation as normalized (top-left, Y down)
        x, y, w, h = normalized_to_idml([100, 200, 300, 400], 500, 700)
        assert abs(x - 50) < 0.1
        assert abs(y - 140) < 0.1
        assert abs(w - 150) < 0.1
        assert abs(h - 280) < 0.1


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class TestModels:
    def test_package_spec_dimensions_pt(self):
        from packaging_designer.models.package_spec import Dimensions

        d = Dimensions(width_mm=120, height_mm=170)
        assert abs(d.width_pt - 340.16) < 0.1
        assert abs(d.height_pt - 481.89) < 0.1

    def test_design_analysis_from_json(self):
        from packaging_designer.models.design_elements import DesignAnalysis

        data = {
            "package_spec": {
                "package_type": "pouch",
                "dimensions": {"width_mm": 120, "height_mm": 170},
                "product_name": "Test",
            },
            "text_blocks": [
                {
                    "content": "Hello",
                    "bbox": [0, 0, 500, 100],
                    "role": "product_name",
                }
            ],
            "color_swatches": [
                {
                    "name": "Blue",
                    "hex": "#0000FF",
                    "cyan": 100,
                    "magenta": 100,
                    "yellow": 0,
                    "key": 0,
                    "role": "primary",
                }
            ],
            "existing_elements": ["ean_barcode"],
        }
        analysis = DesignAnalysis.model_validate(data)
        assert analysis.package_spec.package_type == "pouch"
        assert len(analysis.text_blocks) == 1
        assert analysis.text_blocks[0].content == "Hello"
        assert len(analysis.color_swatches) == 1

    def test_color_swatch_cmyk_tuple(self):
        from packaging_designer.models.design_elements import ColorSwatch

        s = ColorSwatch(
            name="Test", hex="#000", cyan=10, magenta=20, yellow=30, key=40
        )
        assert s.cmyk_tuple == (10, 20, 30, 40)

    def test_missing_element_priority_sorting(self):
        from packaging_designer.models.enrichment import (
            ElementPriority,
            MissingElement,
        )

        elements = [
            MissingElement(
                element_id="a",
                display_name="Optional",
                priority=ElementPriority.OPTIONAL,
            ),
            MissingElement(
                element_id="b",
                display_name="Mandatory",
                priority=ElementPriority.MANDATORY,
            ),
            MissingElement(
                element_id="c",
                display_name="Recommended",
                priority=ElementPriority.RECOMMENDED,
            ),
        ]
        prio = {
            ElementPriority.MANDATORY: 0,
            ElementPriority.RECOMMENDED: 1,
            ElementPriority.OPTIONAL: 2,
        }
        sorted_e = sorted(elements, key=lambda e: prio[e.priority])
        assert sorted_e[0].display_name == "Mandatory"
        assert sorted_e[1].display_name == "Recommended"
        assert sorted_e[2].display_name == "Optional"


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------


class TestBarcode:
    def test_generate_ean13_svg(self):
        from packaging_designer.generators.barcode import generate_ean13_svg

        svg = generate_ean13_svg("5901234123457")
        assert svg.startswith("<?xml")
        assert "<svg" in svg
        assert "5901234123457" in svg or "590123412345" in svg

    def test_generate_ean13_svg_12_digits(self):
        from packaging_designer.generators.barcode import generate_ean13_svg

        # 12 digits — check digit calculated automatically
        svg = generate_ean13_svg("590123412345")
        assert "<svg" in svg

    def test_generate_ean13_invalid(self):
        from packaging_designer.generators.barcode import generate_ean13_svg

        with pytest.raises(Exception):
            generate_ean13_svg("123")  # too short


class TestSymbols:
    def test_get_available_symbols(self):
        from packaging_designer.generators.symbols import get_available_symbols

        symbols = get_available_symbols()
        assert len(symbols) >= 5
        ids = [s["id"] for s in symbols]
        assert "recycling_mobius" in ids
        assert "recycling_tidyman" in ids
        assert "ce_mark" in ids

    def test_load_symbol_svg(self):
        from packaging_designer.generators.symbols import load_symbol_svg

        svg = load_symbol_svg("recycling_mobius")
        assert svg is not None
        assert "<svg" in svg

    def test_load_unknown_symbol(self):
        from packaging_designer.generators.symbols import load_symbol_svg

        assert load_symbol_svg("nonexistent_symbol") is None


# ---------------------------------------------------------------------------
# Enricher
# ---------------------------------------------------------------------------


class TestEnricher:
    def _make_analysis(self, existing=None):
        from packaging_designer.models.design_elements import DesignAnalysis
        from packaging_designer.models.package_spec import (
            Dimensions,
            PackageSpec,
            PackageType,
        )

        return DesignAnalysis(
            package_spec=PackageSpec(
                package_type=PackageType.POUCH,
                dimensions=Dimensions(width_mm=120, height_mm=170),
            ),
            existing_elements=existing or [],
        )

    def test_detect_all_missing_for_empty_packaging(self):
        from packaging_designer.enricher import detect_missing_elements

        analysis = self._make_analysis()
        missing = detect_missing_elements(analysis)
        assert len(missing) > 5  # pet_food has many requirements
        ids = [m.element_id for m in missing]
        assert "ean_barcode" in ids
        assert "ingredients_list" in ids
        assert "nutrition_table" in ids

    def test_detect_missing_respects_existing(self):
        from packaging_designer.enricher import detect_missing_elements

        analysis = self._make_analysis(
            existing=["ean_barcode", "ingredients_list", "nutrition_table"]
        )
        missing = detect_missing_elements(analysis)
        ids = [m.element_id for m in missing]
        assert "ean_barcode" not in ids
        assert "ingredients_list" not in ids

    def test_mandatory_sorted_first(self):
        from packaging_designer.enricher import detect_missing_elements
        from packaging_designer.models.enrichment import ElementPriority

        analysis = self._make_analysis()
        missing = detect_missing_elements(analysis)
        # First elements should be mandatory
        assert missing[0].priority == ElementPriority.MANDATORY

    def test_generate_barcode_asset(self):
        from packaging_designer.enricher import generate_selected_assets

        assets = generate_selected_assets(
            ["ean_barcode"], ean_number="5901234123457"
        )
        assert len(assets) == 1
        assert assets[0].element_id == "ean_barcode"
        assert assets[0].svg_content is not None
        assert "<svg" in assets[0].svg_content

    def test_generate_symbol_asset(self):
        from packaging_designer.enricher import generate_selected_assets

        assets = generate_selected_assets(["recycling_mobius"])
        assert len(assets) == 1
        assert assets[0].element_id == "recycling_mobius"
        assert assets[0].svg_content is not None

    def test_enrich_full_pipeline(self):
        from packaging_designer.enricher import enrich

        analysis = self._make_analysis()
        # Phase 1: detect only
        result1 = enrich(analysis)
        assert len(result1.missing_elements) > 0
        assert len(result1.generated_assets) == 0

        # Phase 2: generate selected
        result2 = enrich(
            analysis,
            selected_ids=["ean_barcode", "recycling_mobius"],
            ean_number="5901234123457",
        )
        assert len(result2.generated_assets) == 2


# ---------------------------------------------------------------------------
# JSX Builder
# ---------------------------------------------------------------------------


class TestJSXBuilder:
    def _make_analysis(self):
        from packaging_designer.models.design_elements import (
            ColorSwatch,
            DesignAnalysis,
            TextBlock,
        )
        from packaging_designer.models.package_spec import (
            Dimensions,
            PackageSpec,
            PackageType,
        )

        return DesignAnalysis(
            package_spec=PackageSpec(
                package_type=PackageType.BOX,
                dimensions=Dimensions(width_mm=200, height_mm=300),
                product_name="Test Product",
                brand_name="TestBrand",
            ),
            text_blocks=[
                TextBlock(
                    content="KARMA DLA KOTOW",
                    bbox=[100, 50, 800, 100],
                    role="product_name",
                    font_style="sans_bold",
                    font_size_pt=28,
                ),
                TextBlock(
                    content="Z kurczakiem i ryzem",
                    bbox=[100, 200, 800, 60],
                    role="tagline",
                    font_style="sans_regular",
                    font_size_pt=14,
                ),
            ],
            color_swatches=[
                ColorSwatch(
                    name="Dark Navy",
                    hex="#1A2E4A",
                    cyan=85,
                    magenta=55,
                    yellow=10,
                    key=40,
                    role="primary",
                ),
                ColorSwatch(
                    name="Warm White",
                    hex="#FFF8F0",
                    cyan=0,
                    magenta=2,
                    yellow=6,
                    key=0,
                    role="background",
                ),
                ColorSwatch(
                    name="Text Black",
                    hex="#1A1A1A",
                    cyan=0,
                    magenta=0,
                    yellow=0,
                    key=90,
                    role="text",
                ),
            ],
            existing_elements=["net_weight"],
        )

    def test_jsx_generates_valid_script(self):
        from packaging_designer.builders.jsx_builder import build_jsx

        analysis = self._make_analysis()
        jsx = build_jsx(analysis)

        assert jsx.startswith("// ====")
        assert "(function()" in jsx
        assert "})();" in jsx

    def test_jsx_contains_document_creation(self):
        from packaging_designer.builders.jsx_builder import build_jsx

        jsx = build_jsx(self._make_analysis())
        assert "DocumentColorSpace.CMYK" in jsx
        assert "app.documents.add" in jsx

    def test_jsx_contains_layers(self):
        from packaging_designer.builders.jsx_builder import build_jsx

        jsx = build_jsx(self._make_analysis())
        for layer_name in [
            "Dieline",
            "Background",
            "Graphics",
            "Text",
            "Regulatory",
            "Technical",
            "Reference (concept)",
        ]:
            assert layer_name in jsx

    def test_jsx_contains_cmyk_swatches(self):
        from packaging_designer.builders.jsx_builder import build_jsx

        jsx = build_jsx(self._make_analysis())
        assert "CMYKColor" in jsx
        assert "Dark Navy" in jsx
        assert "doc.swatches.add" in jsx
        # Should NOT use spots.add for process colors
        assert "doc.spots.add" not in jsx

    def test_jsx_contains_area_text_frames(self):
        from packaging_designer.builders.jsx_builder import build_jsx

        jsx = build_jsx(self._make_analysis())
        # Should use areaText, not just textFrames.add() for text blocks
        assert "textFrames.areaText" in jsx
        assert "KARMA DLA KOTOW" in jsx
        assert "Z kurczakiem i ryzem" in jsx

    def test_jsx_contains_dieline(self):
        from packaging_designer.builders.jsx_builder import build_jsx

        jsx = build_jsx(self._make_analysis())
        assert "pathItems.rectangle" in jsx
        assert "strokeDashes" in jsx  # dashed bleed line

    def test_jsx_font_references(self):
        from packaging_designer.builders.jsx_builder import build_jsx

        jsx = build_jsx(self._make_analysis())
        assert "textFonts.getByName" in jsx
        # PostScript font names, not display names
        assert "Arial-BoldMT" in jsx or "ArialMT" in jsx

    def test_jsx_handles_empty_analysis(self):
        from packaging_designer.builders.jsx_builder import build_jsx
        from packaging_designer.models.design_elements import DesignAnalysis
        from packaging_designer.models.package_spec import (
            Dimensions,
            PackageSpec,
            PackageType,
        )

        minimal = DesignAnalysis(
            package_spec=PackageSpec(
                package_type=PackageType.LABEL,
                dimensions=Dimensions(width_mm=80, height_mm=50),
            ),
        )
        jsx = build_jsx(minimal)
        assert "app.documents.add" in jsx
        assert "(function()" in jsx

    def test_jsx_escapes_special_chars(self):
        from packaging_designer.builders.jsx_builder import build_jsx
        from packaging_designer.models.design_elements import (
            DesignAnalysis,
            TextBlock,
        )
        from packaging_designer.models.package_spec import (
            Dimensions,
            PackageSpec,
            PackageType,
        )

        analysis = DesignAnalysis(
            package_spec=PackageSpec(
                package_type=PackageType.POUCH,
                dimensions=Dimensions(width_mm=100, height_mm=150),
                product_name="O'Brien's \"Special\" Mix",
            ),
            text_blocks=[
                TextBlock(
                    content="It's a 'test' with \"quotes\"",
                    bbox=[0, 0, 500, 100],
                    role="product_name",
                ),
            ],
        )
        jsx = build_jsx(analysis)
        # Should not have unescaped quotes breaking JS
        assert "\\'" in jsx  # escaped single quote
        assert '\\"' in jsx  # escaped double quote

    def test_jsx_no_syntax_errors_basic(self):
        """Basic check that generated JSX has balanced braces/parens."""
        from packaging_designer.builders.jsx_builder import build_jsx

        jsx = build_jsx(self._make_analysis())
        # Count braces (approximate — doesn't handle strings)
        open_braces = jsx.count("{") - jsx.count("\\{")
        close_braces = jsx.count("}") - jsx.count("\\}")
        assert open_braces == close_braces, (
            f"Unbalanced braces: {open_braces} open vs {close_braces} close"
        )

        open_parens = jsx.count("(")
        close_parens = jsx.count(")")
        assert open_parens == close_parens, (
            f"Unbalanced parens: {open_parens} open vs {close_parens} close"
        )


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


class TestPipeline:
    def test_create_jsx_package(self):
        from packaging_designer.pipeline import create_jsx_package

        zip_bytes = create_jsx_package(
            jsx_content="// test script",
            concept_image=b"fake_png_data",
        )
        assert len(zip_bytes) > 0
        # Verify it's a valid ZIP
        import zipfile
        from io import BytesIO

        with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
            names = zf.namelist()
            assert "packaging_design.jsx" in names
            assert "assets/concept_original.png" in names

    def test_create_jsx_package_with_assets(self):
        from packaging_designer.enricher import enrich
        from packaging_designer.models.design_elements import DesignAnalysis
        from packaging_designer.models.package_spec import (
            Dimensions,
            PackageSpec,
            PackageType,
        )
        from packaging_designer.pipeline import create_jsx_package

        analysis = DesignAnalysis(
            package_spec=PackageSpec(
                package_type=PackageType.POUCH,
                dimensions=Dimensions(width_mm=120, height_mm=170),
            ),
        )
        enrichment = enrich(
            analysis,
            selected_ids=["ean_barcode", "recycling_mobius"],
            ean_number="5901234123457",
        )

        zip_bytes = create_jsx_package(
            jsx_content="// test",
            enrichment=enrichment,
        )

        import zipfile
        from io import BytesIO

        with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
            names = zf.namelist()
            assert "assets/ean_barcode.svg" in names
            assert "assets/recycling_mobius.svg" in names
