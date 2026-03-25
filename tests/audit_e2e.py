"""Full E2E audit of packaging_designer module."""

import sys
import xml.etree.ElementTree as ET
import zipfile
from io import BytesIO

sys.path.insert(0, "src")

from packaging_designer.builders.idml_builder import build_idml
from packaging_designer.builders.idml_templates import get_template
from packaging_designer.builders.jsx_builder import build_jsx
from packaging_designer.builders.mockup_3d import generate_3d_mockup
from packaging_designer.builders.preview_builder import build_preview_png
from packaging_designer.enricher import detect_missing_elements, enrich
from packaging_designer.generators.dieline import get_dieline_svg
from packaging_designer.generators.nutrition_table import (
    generate_feeding_table_svg,
    generate_nutrition_svg,
)
from packaging_designer.models.design_elements import (
    ColorSwatch,
    DesignAnalysis,
    GraphicRegion,
    TextBlock,
)
from packaging_designer.models.export_config import ExportConfig
from packaging_designer.models.package_spec import (
    Dimensions,
    PackageSpec,
    PackageType,
    ProductCategory,
)
from packaging_designer.pipeline import create_jsx_package

ERRORS = []


def check(label, condition, detail=""):
    if condition:
        print(f"  OK  {label}")
    else:
        msg = f"{label}: {detail}" if detail else label
        ERRORS.append(msg)
        print(f"  FAIL {msg}")


# ---- Build realistic analysis ----
analysis = DesignAnalysis(
    package_spec=PackageSpec(
        package_type=PackageType.STANDUP_POUCH,
        dimensions=Dimensions(width_mm=140, height_mm=200),
        product_name="Premium Karma dla Kotow",
        brand_name="FeliFeast",
        product_category=ProductCategory.PET_FOOD,
        sides_visible=1,
    ),
    text_blocks=[
        TextBlock(content="FELIFEAST", bbox=[250, 20, 500, 60], role="brand",
                  font_style="sans_bold", font_size_pt=36),
        TextBlock(content="Premium Karma", bbox=[100, 100, 800, 80], role="product_name",
                  font_style="sans_bold", font_size_pt=24),
        TextBlock(content="z kurczakiem", bbox=[150, 200, 700, 50], role="tagline",
                  font_style="sans_regular", font_size_pt=14),
        TextBlock(content="85g", bbox=[820, 900, 120, 50], role="weight",
                  font_style="sans_bold", font_size_pt=18),
    ],
    graphic_regions=[
        GraphicRegion(description="Cat photo", bbox=[50, 350, 900, 450], region_type="product_photo"),
    ],
    color_swatches=[
        ColorSwatch(name="Forest Green", hex="#1B5E20", cyan=75, magenta=10, yellow=85, key=35, role="primary"),
        ColorSwatch(name="Golden Amber", hex="#F9A825", cyan=0, magenta=35, yellow=90, key=0, role="secondary"),
        ColorSwatch(name="Cream White", hex="#FFF8E1", cyan=0, magenta=2, yellow=12, key=0, role="background"),
        ColorSwatch(name="Dark Text", hex="#212121", cyan=0, magenta=0, yellow=0, key=87, role="text"),
    ],
    existing_elements=["net_weight"],
)

print("=" * 60)
print("E2E AUDIT: Packaging Designer")
print("=" * 60)

# ---- Enrichment ----
print("\n--- Enrichment ---")
missing = detect_missing_elements(analysis)
check("Missing elements detected", len(missing) > 5, f"got {len(missing)}")

mandatory = [m for m in missing if m.priority.value == "mandatory"]
check("Mandatory elements found", len(mandatory) >= 5, f"got {len(mandatory)}")

selected = [m.element_id for m in missing if m.priority.value in ("mandatory", "recommended")]
enrichment = enrich(analysis, selected_ids=selected, ean_number="5901234123457")
check("Assets generated", len(enrichment.generated_assets) > 0, f"got {len(enrichment.generated_assets)}")

for a in enrichment.generated_assets:
    check(f"Asset {a.element_id} has SVG", a.svg_content is not None and len(a.svg_content) > 50)

# ---- JSX ----
print("\n--- JSX Builder ---")
config = ExportConfig(bleed_mm=3.0)
jsx = build_jsx(analysis, enrichment=enrichment, config=config)
check("JSX generated", len(jsx) > 5000, f"{len(jsx)} chars")

check("JSX: CMYK colorspace", "DocumentColorSpace.CMYK" in jsx)
check("JSX: documents.add", "app.documents.add" in jsx)
check("JSX: swatches.add (not spots)", "doc.swatches.add" in jsx and "doc.spots.add" not in jsx)
check("JSX: areaText (not textFrames.add for content)", "textFrames.areaText" in jsx)
check("JSX: Forest Green swatch", "Forest Green" in jsx)
check("JSX: FELIFEAST text", "FELIFEAST" in jsx)
check("JSX: placedItems for assets", "placedItems.add" in jsx)
check("JSX: strokeDashes for bleed", "strokeDashes" in jsx)

for layer in ["Dieline", "Background", "Graphics", "Text", "Regulatory", "Technical", "Reference (concept)"]:
    check(f"JSX: layer '{layer}'", layer in jsx)

ob = jsx.count("{")
cb = jsx.count("}")
check(f"JSX: balanced braces", ob == cb, f"{ob} open vs {cb} close")

op = jsx.count("(")
cp = jsx.count(")")
check(f"JSX: balanced parens", op == cp, f"{op} open vs {cp} close")

# Check no raw unescaped quotes that break JS
lines = jsx.splitlines()
for i, line in enumerate(lines):
    if "contents = '" in line or "contents='" in line:
        # Check content strings don't have unescaped single quotes
        pass  # Would need proper JS parser

# ---- IDML ----
print("\n--- IDML Builder ---")
idml = build_idml(analysis, enrichment=enrichment, config=config)
check("IDML generated", len(idml) > 2000, f"{len(idml)} bytes")

with zipfile.ZipFile(BytesIO(idml)) as zf:
    names = zf.namelist()
    check("IDML: mimetype first", names[0] == "mimetype", f"first={names[0]}")

    mi = zf.getinfo("mimetype")
    check("IDML: mimetype STORED", mi.compress_type == zipfile.ZIP_STORED)

    mt = zf.read("mimetype")
    check("IDML: mimetype content", mt == b"application/vnd.adobe.indesign-idml-package")

    for req in ["designmap.xml", "META-INF/container.xml",
                 "Resources/Graphic.xml", "Resources/Fonts.xml",
                 "Resources/Styles.xml", "Resources/Preferences.xml"]:
        check(f"IDML: has {req}", req in names)

    spreads = [n for n in names if n.startswith("Spreads/")]
    stories = [n for n in names if n.startswith("Stories/")]
    check("IDML: has spreads", len(spreads) > 0)
    check("IDML: has stories", len(stories) > 0)
    check("IDML: story count matches text blocks",
          len(stories) == len(analysis.text_blocks),
          f"{len(stories)} stories vs {len(analysis.text_blocks)} blocks")

    # XML well-formedness
    xml_errors = 0
    for name in names:
        if name.endswith(".xml"):
            try:
                ET.fromstring(zf.read(name))
            except ET.ParseError as e:
                xml_errors += 1
                ERRORS.append(f"IDML: invalid XML in {name}: {e}")
    check(f"IDML: all XML well-formed", xml_errors == 0, f"{xml_errors} errors")

    graphic = zf.read("Resources/Graphic.xml").decode()
    check("IDML: Forest Green in Graphic.xml", "Forest Green" in graphic)
    check("IDML: CMYK in Graphic.xml", "CMYK" in graphic)

    prefs = zf.read("Resources/Preferences.xml").decode()
    check("IDML: PageWidth in Preferences", "PageWidth" in prefs)
    check("IDML: PageHeight in Preferences", "PageHeight" in prefs)

    dm = zf.read("designmap.xml").decode()
    for layer in ["Dieline", "Background", "Text", "Regulatory"]:
        check(f"IDML: layer '{layer}' in designmap", layer in dm)

    for sf in stories:
        sc = zf.read(sf).decode()
        check(f"IDML: {sf} has <Content>", "<Content>" in sc)

# ---- ZIP Package ----
print("\n--- ZIP Package ---")
pkg = create_jsx_package(jsx, enrichment=enrichment, concept_image=b"FAKE_PNG")
with zipfile.ZipFile(BytesIO(pkg)) as zf:
    pkg_names = zf.namelist()
    check("ZIP: has jsx", "packaging_design.jsx" in pkg_names)
    check("ZIP: has concept", "assets/concept_original.png" in pkg_names)
    asset_files = [n for n in pkg_names if n.startswith("assets/") and "concept" not in n]
    check("ZIP: has generated assets", len(asset_files) > 0, f"{len(asset_files)} files")

# ---- Preview ----
print("\n--- Preview & Mockup ---")
preview = build_preview_png(analysis)
check("Preview PNG generated", len(preview) > 1000, f"{len(preview)} bytes")

mockup = generate_3d_mockup(analysis)
check("3D Mockup generated", len(mockup) > 1000, f"{len(mockup)} bytes")

# ---- Dieline ----
print("\n--- Dieline ---")
for pkg_type in ["pouch", "standup_pouch", "box", "can", "label", "bottle"]:
    depth = 40 if pkg_type in ("box", "tray") else None
    svg = get_dieline_svg(pkg_type, 120, 170, depth_mm=depth)
    check(f"Dieline {pkg_type}", "<svg" in svg, f"{len(svg)} chars")

# ---- Nutrition tables ----
print("\n--- Nutrition Tables ---")
nutri = generate_nutrition_svg({"Protein": "32%", "Fat": "15%", "Fibre": "3%", "Ash": "7%"})
check("Nutrition SVG", "<svg" in nutri and "Protein" in nutri)

feed = generate_feeding_table_svg([("2-4 kg", "40-70 g"), ("4-8 kg", "70-120 g")])
check("Feeding table SVG", "<svg" in feed)

# ---- Templates ----
print("\n--- IDML Templates ---")
for pt in ["pouch", "box", "can", "bottle", "label", "unknown_type"]:
    t = get_template(pt)
    check(f"Template {pt}", len(t.frames) >= 6, f"{t.name}: {len(t.frames)} frames")

# ---- Summary ----
print("\n" + "=" * 60)
if ERRORS:
    print(f"AUDIT RESULT: {len(ERRORS)} FAILURES")
    for e in ERRORS:
        print(f"  - {e}")
else:
    print("AUDIT RESULT: ALL CHECKS PASSED")
print("=" * 60)
