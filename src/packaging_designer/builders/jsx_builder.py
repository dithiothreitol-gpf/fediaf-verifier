"""Adobe Illustrator ExtendScript (.jsx) builder for packaging design.

Generates a .jsx script that, when run in Illustrator, creates a complete
packaging document with:
- CMYK color swatches from the design palette
- Named layers (Dieline, Background, Graphics, Text, Regulatory, Technical)
- Editable area text frames with styling
- Placed asset files (barcodes, symbols, concept image)
- Artboard sized to packaging dimensions
- Bleed and crop marks on technical layer

The user runs the script via File > Scripts > Other Script...
The script expects an "assets" folder next to the .jsx file.

Illustrator coordinate system:
- Origin at BOTTOM-LEFT of artboard
- X increases rightward, Y increases UPWARD
- pathItems.rectangle(top, left, width, height) — top is Y of top edge
- position arrays are [left, top] = [x, y]
- All values in PostScript points (1pt = 1/72 inch ≈ 0.353mm)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from packaging_designer.utils.color import mm_to_pt

if TYPE_CHECKING:
    from packaging_designer.models.design_elements import (
        ColorSwatch,
        DesignAnalysis,
        TextBlock,
    )
    from packaging_designer.models.enrichment import EnrichmentResult, GeneratedAsset
    from packaging_designer.models.export_config import ExportConfig


def _esc(text: str) -> str:
    """Escape string for JavaScript single-quoted literal."""
    return (
        text.replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace("\n", "\\n")
        .replace("\r", "")
        .replace('"', '\\"')
    )


def _font_for_style(style: str) -> str:
    """Map font style hint to Illustrator textFont name.

    Illustrator uses PostScript font names like 'ArialMT', 'Arial-BoldMT'.
    Returns a name for app.textFonts.getByName(). Designer will adjust.
    """
    mapping = {
        "sans_bold": "Arial-BoldMT",
        "sans_regular": "ArialMT",
        "serif_bold": "TimesNewRomanPS-BoldMT",
        "serif_regular": "TimesNewRomanPSMT",
        "display": "Impact",
        "condensed": "ArialNarrow-Bold",
        "handwritten": "SegoeScript",
    }
    return mapping.get(style, "ArialMT")


def _build_swatches_js(swatches: list[ColorSwatch]) -> str:
    """Generate JS code to create CMYK process color swatches.

    Uses doc.swatches.add() for process CMYK colors (not doc.spots
    which is for Pantone/spot colors).
    """
    lines = [
        "    // ====== KOLORY CMYK ======",
        "    var swatchColors = {};",
    ]
    for i, s in enumerate(swatches):
        safe_name = _esc(s.name or f"Color_{i+1}")
        lines.append(f"    // {safe_name}: {s.hex} -> C{s.cyan} M{s.magenta} Y{s.yellow} K{s.key}")
        lines.append(f"    try {{")
        lines.append(f"        var cmyk{i} = new CMYKColor();")
        lines.append(f"        cmyk{i}.cyan = {s.cyan};")
        lines.append(f"        cmyk{i}.magenta = {s.magenta};")
        lines.append(f"        cmyk{i}.yellow = {s.yellow};")
        lines.append(f"        cmyk{i}.black = {s.key};")
        lines.append(f"        swatchColors['{safe_name}'] = cmyk{i};")
        # Add as named document swatch for the Swatches panel
        lines.append(f"        try {{")
        lines.append(f"            var sw{i} = doc.swatches.add();")
        lines.append(f"            sw{i}.name = '{safe_name}';")
        lines.append(f"            sw{i}.color = cmyk{i};")
        lines.append(f"        }} catch(e) {{}}  // swatch name may already exist")
        lines.append(f"    }} catch(e) {{}}")
    return "\n".join(lines)


def _build_layers_js() -> str:
    """Generate JS code to create named layers.

    Layers are added in reverse order because Illustrator prepends
    new layers on top. Final order (top to bottom):
    Reference > Technical > Regulatory > Text > Graphics > Background > Dieline
    """
    # Added bottom-to-top so first added = bottom layer
    layer_names = [
        "Dieline",
        "Background",
        "Graphics",
        "Text",
        "Regulatory",
        "Technical",
        "Reference (concept)",
    ]
    lines = [
        "    // ====== WARSTWY ======",
        "    var layers = {};",
        "    // Usun domyslna warstwe 'Layer 1' po dodaniu nowych",
        "    var defaultLayer = doc.layers[0];",
    ]
    for name in layer_names:
        safe = _esc(name)
        lines.append(f"    try {{")
        lines.append(f"        layers['{safe}'] = doc.layers.add();")
        lines.append(f"        layers['{safe}'].name = '{safe}';")
        lines.append(f"    }} catch(e) {{}}")

    # Remove default empty layer
    lines.append("    try { if (defaultLayer.pageItems.length === 0) defaultLayer.remove(); } catch(e) {}")
    # Set Reference layer properties
    lines.append("    try {")
    lines.append("        layers['Reference (concept)'].opacity = 40;")
    lines.append("    } catch(e) {}")
    return "\n".join(lines)


def _build_background_js(
    width_pt: float,
    height_pt: float,
    swatches: list[ColorSwatch],
) -> str:
    """Generate JS for background rectangle.

    pathItems.rectangle(top, left, width, height):
    - top = height_pt (Y of top edge = artboard top)
    - left = 0 (X of left edge = artboard left)
    """
    bg_swatch = next((s for s in swatches if s.role == "background"), None)
    if not bg_swatch:
        return "    // No background color detected"

    safe_name = _esc(bg_swatch.name)
    lines = [
        "    // ====== TLO ======",
        "    doc.activeLayer = layers['Background'];",
        f"    var bgRect = doc.pathItems.rectangle({height_pt:.2f}, 0, {width_pt:.2f}, {height_pt:.2f});",
        f"    if (swatchColors['{safe_name}']) bgRect.fillColor = swatchColors['{safe_name}'];",
        "    bgRect.stroked = false;",
    ]
    return "\n".join(lines)


def _build_text_frames_js(
    text_blocks: list[TextBlock],
    width_pt: float,
    height_pt: float,
    swatches: list[ColorSwatch],
) -> str:
    """Generate JS for editable AREA text frames.

    Uses pathItems.rectangle() to create a bounding box, then
    textFrames.areaText(rectPath) to make it an editable area text frame.
    This gives the text frame proper width/height (unlike point text).

    Coordinate conversion:
    - Normalized: origin top-left, Y down, range 0-1000
    - Illustrator: origin bottom-left, Y up, units in points
    """
    text_swatch = next((s for s in swatches if s.role == "text"), None)

    lines = [
        "    // ====== TEKST ======",
        "    doc.activeLayer = layers['Text'];",
    ]

    for i, tb in enumerate(text_blocks):
        if not tb.bbox or len(tb.bbox) < 4:
            continue

        nx, ny, nw, nh = tb.bbox
        # Convert to Illustrator points
        left = (nx / 1000.0) * width_pt
        w = max((nw / 1000.0) * width_pt, 20)  # min 20pt width
        h = max((nh / 1000.0) * height_pt, 14)  # min 14pt height
        # Y-flip: normalized top → Illustrator top
        top = height_pt - ((ny / 1000.0) * height_pt)

        font_name = _font_for_style(tb.font_style)
        font_size = tb.font_size_pt or 12
        content = _esc(tb.content)

        lines.append(f"    // Text block {i+1}: [{tb.role}] '{content[:40]}...'")
        lines.append(f"    try {{")
        # Create rect path as text frame boundary
        lines.append(f"        var textRect{i} = doc.pathItems.rectangle({top:.2f}, {left:.2f}, {w:.2f}, {h:.2f});")
        # Convert rect to area text frame
        lines.append(f"        var tf{i} = doc.textFrames.areaText(textRect{i});")
        lines.append(f"        tf{i}.contents = '{content}';")
        # Styling
        lines.append(f"        tf{i}.textRange.characterAttributes.size = {font_size};")
        lines.append(f"        try {{")
        lines.append(f"            tf{i}.textRange.characterAttributes.textFont = app.textFonts.getByName('{font_name}');")
        lines.append(f"        }} catch(fontErr) {{")
        lines.append(f"            // Font '{font_name}' not installed — using default")
        lines.append(f"        }}")
        if text_swatch:
            safe_name = _esc(text_swatch.name)
            lines.append(f"        if (swatchColors['{safe_name}']) tf{i}.textRange.characterAttributes.fillColor = swatchColors['{safe_name}'];")
        lines.append(f"    }} catch(e) {{")
        lines.append(f"        // Text block {i+1} failed: + e.message")
        lines.append(f"    }}")

    return "\n".join(lines)


def _build_regulatory_js(
    assets: list[GeneratedAsset],
    width_pt: float,
    height_pt: float,
) -> str:
    """Generate JS for placing regulatory assets (barcode, symbols).

    Assets are placed in a row near the bottom-right of the artboard.
    position is [left, top] in Illustrator coords (Y up from bottom).
    """
    if not assets:
        return "    // No regulatory assets to place"

    lines = [
        "    // ====== ELEMENTY REGULACYJNE ======",
        "    doc.activeLayer = layers['Regulatory'];",
        "    var scriptFile = new File($.fileName);",
        "    var assetsPath = scriptFile.parent.fsName + '/assets/';",
        "    // On Windows use backslash-aware path",
        "    if ($.os.indexOf('Windows') !== -1) {",
        "        assetsPath = scriptFile.parent.fsName + '\\\\assets\\\\';",
        "    }",
    ]

    margin_pt = mm_to_pt(5)
    # Start placing from right edge, Y near bottom
    x_cursor = width_pt - margin_pt
    y_pos = margin_pt + mm_to_pt(5)  # 5mm from artboard bottom

    for i, asset in enumerate(assets):
        w_pt = mm_to_pt(asset.width_mm)
        h_pt = mm_to_pt(asset.height_mm)
        x_cursor -= w_pt
        if x_cursor < margin_pt:
            x_cursor = width_pt - margin_pt - w_pt  # wrap to next row

        file_name = _esc(asset.file_name)
        # Illustrator position = [left, top], top = y_pos + h_pt
        top_y = y_pos + h_pt

        lines.append(f"    // {asset.element_id}")
        lines.append(f"    try {{")
        lines.append(f"        var assetFile{i} = new File(assetsPath + '{file_name}');")
        lines.append(f"        if (assetFile{i}.exists) {{")
        lines.append(f"            var placed{i} = doc.placedItems.add();")
        lines.append(f"            placed{i}.file = assetFile{i};")
        lines.append(f"            placed{i}.position = [{x_cursor:.2f}, {top_y:.2f}];")
        lines.append(f"            placed{i}.width = {w_pt:.2f};")
        lines.append(f"            placed{i}.height = {h_pt:.2f};")
        lines.append(f"        }} else {{")
        lines.append(f"            // Asset file not found: {file_name}")
        lines.append(f"        }}")
        lines.append(f"    }} catch(e) {{}}")

        x_cursor -= mm_to_pt(3)  # 3mm gap between assets

    return "\n".join(lines)


def _build_concept_reference_js(width_pt: float, height_pt: float) -> str:
    """Generate JS for placing the original concept image as reference layer.

    position [0, height_pt] = bottom-left x, top y = full artboard.
    """
    return f"""\
    // ====== KONCEPT REFERENCYJNY ======
    try {{
        doc.activeLayer = layers['Reference (concept)'];
        var scriptFile2 = new File($.fileName);
        var conceptPath = scriptFile2.parent.fsName + '/assets/concept_original.png';
        if ($.os.indexOf('Windows') !== -1) {{
            conceptPath = scriptFile2.parent.fsName + '\\\\assets\\\\concept_original.png';
        }}
        var conceptFile = new File(conceptPath);
        if (conceptFile.exists) {{
            var concept = doc.placedItems.add();
            concept.file = conceptFile;
            concept.position = [0, {height_pt:.2f}];
            concept.width = {width_pt:.2f};
            concept.height = {height_pt:.2f};
        }}
        layers['Reference (concept)'].locked = true;
    }} catch(e) {{}}"""


def _build_dieline_js(width_pt: float, height_pt: float, bleed_pt: float) -> str:
    """Generate JS for basic dieline (cut line + bleed).

    rectangle(top, left, width, height):
    - Cut line: exactly on artboard edges
    - Bleed line: extends bleed_pt outside artboard on all sides
    """
    return f"""\
    // ====== DIELINE ======
    doc.activeLayer = layers['Dieline'];

    // Kolor linii ciecia — Cyan 100% (latwo widoczny, nie drukuje sie)
    var dieColor = new CMYKColor();
    dieColor.cyan = 100; dieColor.magenta = 0;
    dieColor.yellow = 0; dieColor.black = 0;

    // Linia ciecia (solid) — dokladnie na krawedzi artboardu
    var cutLine = doc.pathItems.rectangle(
        {height_pt:.2f}, 0, {width_pt:.2f}, {height_pt:.2f}
    );
    cutLine.filled = false;
    cutLine.stroked = true;
    cutLine.strokeColor = dieColor;
    cutLine.strokeWidth = 0.5;

    // Linia spadu (dashed) — {bleed_pt/2.835:.1f}mm na zewnatrz
    var bleedLine = doc.pathItems.rectangle(
        {height_pt + bleed_pt:.2f}, -{bleed_pt:.2f},
        {width_pt + 2*bleed_pt:.2f}, {height_pt + 2*bleed_pt:.2f}
    );
    bleedLine.filled = false;
    bleedLine.stroked = true;
    bleedLine.strokeColor = dieColor;
    bleedLine.strokeWidth = 0.25;
    bleedLine.strokeDashes = [8, 4];"""


def _build_technical_js(width_pt: float, height_pt: float, bleed_pt: float) -> str:
    """Generate JS for technical info on Technical layer.

    Places info text below the artboard (negative Y).
    Uses point text (textFrames.add()) since this is a simple label.
    """
    return f"""\
    // ====== TECHNICZNE ======
    doc.activeLayer = layers['Technical'];

    // Tekst informacyjny ponizej artboardu
    var infoTf = doc.textFrames.add();
    infoTf.contents = 'AI Packaging Designer | '
        + Math.round({width_pt:.2f} / 2.835) + ' x '
        + Math.round({height_pt:.2f} / 2.835) + ' mm | '
        + 'Spad: ' + Math.round({bleed_pt:.2f} / 2.835) + ' mm';
    infoTf.position = [0, -{bleed_pt + 10:.2f}];
    infoTf.textRange.characterAttributes.size = 6;
    var techColor = new CMYKColor();
    techColor.cyan = 0; techColor.magenta = 0;
    techColor.yellow = 0; techColor.black = 40;
    infoTf.textRange.characterAttributes.fillColor = techColor;"""


def build_jsx(
    analysis: DesignAnalysis,
    enrichment: EnrichmentResult | None = None,
    config: ExportConfig | None = None,
    include_concept: bool = True,
) -> str:
    """Build complete Illustrator ExtendScript for the packaging design.

    Args:
        analysis: Design analysis from AI Vision.
        enrichment: Optional enrichment result with generated assets.
        config: Export configuration (bleed, etc.).
        include_concept: Whether to place concept image as reference.

    Returns:
        Complete .jsx script as string.
    """
    bleed_mm = config.bleed_mm if config else 3.0
    bleed_pt = mm_to_pt(bleed_mm)

    dims = analysis.package_spec.dimensions
    width_pt = dims.width_pt
    height_pt = dims.height_pt

    product_name = _esc(analysis.package_spec.product_name or "Packaging Design")
    brand_name = _esc(analysis.package_spec.brand_name or "")

    assets = enrichment.generated_assets if enrichment else []

    script = f"""\
// ==========================================================
// AI Packaging Designer — Illustrator Document Builder
// Produkt: {product_name}
// Marka: {brand_name}
// Typ: {analysis.package_spec.package_type.value}
// Wymiary: {dims.width_mm:.0f} x {dims.height_mm:.0f} mm ({width_pt:.1f} x {height_pt:.1f} pt)
// Spad: {bleed_mm:.1f} mm
// ==========================================================
// UZYCIE:
//   1. Uruchom: File > Scripts > Other Script... > ten plik
//   2. Folder 'assets/' musi byc obok pliku .jsx
//   3. Warstwy, kolory i teksty sa edytowalne
//   4. Warstwa 'Reference (concept)' — oryginalny koncept (zablokowana, 40% opacity)
//   5. Warstwa 'Dieline' — linie ciecia/spadu w kolorze Cyan
// ==========================================================

(function() {{
    // ====== WALIDACJA ======
    if (app.documents.length > 0) {{
        var proceed = confirm(
            'AI Packaging Designer\\n\\n'
            + 'Skrypt utworzy NOWY dokument.\\n'
            + 'Czy kontynuowac?'
        );
        if (!proceed) return;
    }}

    // ====== NOWY DOKUMENT CMYK ======
    var doc = app.documents.add(
        DocumentColorSpace.CMYK,
        {width_pt:.2f},   // szerokosc: {dims.width_mm:.0f} mm
        {height_pt:.2f}    // wysokosc: {dims.height_mm:.0f} mm
    );

{_build_swatches_js(analysis.color_swatches)}

{_build_layers_js()}

{_build_dieline_js(width_pt, height_pt, bleed_pt)}

{_build_background_js(width_pt, height_pt, analysis.color_swatches)}

{_build_text_frames_js(analysis.text_blocks, width_pt, height_pt, analysis.color_swatches)}

{_build_regulatory_js(assets, width_pt, height_pt)}

{"" if not include_concept else _build_concept_reference_js(width_pt, height_pt)}

{_build_technical_js(width_pt, height_pt, bleed_pt)}

    // ====== FINALIZACJA ======
    doc.activeLayer = layers['Text'];
    app.executeMenuCommand('fitall');

    alert(
        'Dokument wygenerowany!\\n\\n'
        + 'Warstwy (gora do dolu):\\n'
        + '  Reference (concept) — oryginal, 40%, locked\\n'
        + '  Technical — info techniczne\\n'
        + '  Regulatory — EAN, symbole\\n'
        + '  Text — edytowalne teksty\\n'
        + '  Graphics — elementy graficzne\\n'
        + '  Background — tlo\\n'
        + '  Dieline — linie ciecia (Cyan)\\n\\n'
        + 'Kolory CMYK dodane do panelu Swatches.\\n'
        + 'Dostosuj fonty i pozycje wg potrzeb.'
    );
}})();
"""
    return script
