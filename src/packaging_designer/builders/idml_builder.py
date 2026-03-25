"""Adobe InDesign IDML builder for packaging design.

Generates a complete .idml file (ZIP archive with XML) that can be
opened directly in InDesign CS4+. Creates:
- Document with correct page dimensions
- CMYK color swatches in Graphic.xml
- Named layers in designmap.xml
- Text frames with content in Spreads + Stories
- Proper paragraph/character styles

IDML structure:
  mimetype                    (STORED, first entry)
  META-INF/container.xml
  designmap.xml               (layers, references)
  Resources/Graphic.xml       (colors)
  Resources/Fonts.xml
  Resources/Styles.xml        (paragraph/character styles)
  Resources/Preferences.xml   (page size, margins)
  Spreads/Spread_u100.xml     (page items: text frames, rectangles)
  Stories/Story_u*.xml         (text content)

Coordinate system: origin top-left, Y increases downward, units in points.
"""

from __future__ import annotations

import uuid
import zipfile
from io import BytesIO
from typing import TYPE_CHECKING
from xml.etree.ElementTree import Element, SubElement, tostring

from packaging_designer.utils.color import mm_to_pt

if TYPE_CHECKING:
    from packaging_designer.models.design_elements import (
        ColorSwatch,
        DesignAnalysis,
        TextBlock,
    )
    from packaging_designer.models.enrichment import EnrichmentResult
    from packaging_designer.models.export_config import ExportConfig

# IDML namespace
_NS = "http://ns.adobe.com/AdobeInDesign/idml/1.0/packaging"
_DOM_VERSION = "21.0"


def _uid() -> str:
    """Generate a unique ID for IDML elements."""
    return "u" + uuid.uuid4().hex[:8]


def _build_mimetype() -> bytes:
    return b"application/vnd.adobe.indesign-idml-package"


def _build_container_xml() -> bytes:
    root = Element("container", version="1.0")
    root.set("xmlns", "urn:oasis:names:tc:opendocument:xmlns:container")
    rootfiles = SubElement(root, "rootfiles")
    rf = SubElement(rootfiles, "rootfile")
    rf.set("full-path", "designmap.xml")
    rf.set("media-type", "text/xml")
    return b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + tostring(root, encoding="unicode").encode("utf-8")


def _build_graphic_xml(swatches: list[ColorSwatch]) -> bytes:
    """Build Resources/Graphic.xml with CMYK color definitions."""
    root = Element("idPkg:Graphic")
    root.set("xmlns:idPkg", _NS)
    root.set("DOMVersion", _DOM_VERSION)

    # Default colors
    for name, cmyk in [("Black", "0 0 0 100"), ("Paper", "0 0 0 0")]:
        c = SubElement(root, "Color")
        c.set("Self", f"Color/{name}")
        c.set("Name", name)
        c.set("Model", "Process")
        c.set("Space", "CMYK")
        c.set("ColorValue", cmyk)

    # Swatch/None
    sn = SubElement(root, "Swatch")
    sn.set("Self", "Swatch/None")
    sn.set("Name", "None")

    # Custom swatches from analysis
    for i, s in enumerate(swatches):
        c = SubElement(root, "Color")
        uid = f"Color/{_uid()}"
        c.set("Self", uid)
        c.set("Name", s.name or f"Color_{i+1}")
        c.set("Model", "Process")
        c.set("Space", "CMYK")
        c.set("ColorValue", f"{s.cyan:.1f} {s.magenta:.1f} {s.yellow:.1f} {s.key:.1f}")

    return b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + tostring(root, encoding="unicode").encode("utf-8")


def _build_fonts_xml() -> bytes:
    root = Element("idPkg:Fonts")
    root.set("xmlns:idPkg", _NS)
    root.set("DOMVersion", _DOM_VERSION)
    return b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + tostring(root, encoding="unicode").encode("utf-8")


def _build_styles_xml() -> bytes:
    """Build Resources/Styles.xml with basic paragraph and character styles."""
    root = Element("idPkg:Styles")
    root.set("xmlns:idPkg", _NS)
    root.set("DOMVersion", _DOM_VERSION)

    # Root paragraph style group
    rpsg = SubElement(root, "RootParagraphStyleGroup")
    rpsg.set("Self", "u10")
    ps = SubElement(rpsg, "ParagraphStyle")
    ps.set("Self", "ParagraphStyle/$ID/NormalParagraphStyle")
    ps.set("Name", "$ID/NormalParagraphStyle")
    ps.set("PointSize", "10")

    ps_heading = SubElement(rpsg, "ParagraphStyle")
    ps_heading.set("Self", "ParagraphStyle/Heading")
    ps_heading.set("Name", "Heading")
    ps_heading.set("PointSize", "24")
    ps_heading.set("FontStyle", "Bold")

    ps_body = SubElement(rpsg, "ParagraphStyle")
    ps_body.set("Self", "ParagraphStyle/Body")
    ps_body.set("Name", "Body")
    ps_body.set("PointSize", "9")

    # Root character style group
    rcsg = SubElement(root, "RootCharacterStyleGroup")
    rcsg.set("Self", "u11")
    cs = SubElement(rcsg, "CharacterStyle")
    cs.set("Self", "CharacterStyle/$ID/[No character style]")
    cs.set("Name", "$ID/[No character style]")

    # Root object style group
    rosg = SubElement(root, "RootObjectStyleGroup")
    rosg.set("Self", "u12")
    os_ = SubElement(rosg, "ObjectStyle")
    os_.set("Self", "ObjectStyle/$ID/[Normal Graphics Frame]")
    os_.set("Name", "$ID/[Normal Graphics Frame]")

    # Root table/cell style groups (required for valid IDML)
    rtsg = SubElement(root, "RootTableStyleGroup")
    rtsg.set("Self", "u13")
    rcsg2 = SubElement(root, "RootCellStyleGroup")
    rcsg2.set("Self", "u14")

    return b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + tostring(root, encoding="unicode").encode("utf-8")


def _build_preferences_xml(width_pt: float, height_pt: float, bleed_pt: float) -> bytes:
    """Build Resources/Preferences.xml with page dimensions."""
    root = Element("idPkg:Preferences")
    root.set("xmlns:idPkg", _NS)
    root.set("DOMVersion", _DOM_VERSION)

    dp = SubElement(root, "DocumentPreference")
    dp.set("PageHeight", f"{height_pt:.4f}")
    dp.set("PageWidth", f"{width_pt:.4f}")
    dp.set("PagesPerDocument", "1")
    dp.set("FacingPages", "false")
    dp.set("DocumentBleedTopOffset", f"{bleed_pt:.4f}")
    dp.set("DocumentBleedBottomOffset", f"{bleed_pt:.4f}")
    dp.set("DocumentBleedInsideOrLeftOffset", f"{bleed_pt:.4f}")
    dp.set("DocumentBleedOutsideOrRightOffset", f"{bleed_pt:.4f}")

    mp = SubElement(root, "MarginPreference")
    mp.set("Top", "36")
    mp.set("Bottom", "36")
    mp.set("Left", "36")
    mp.set("Right", "36")
    mp.set("ColumnCount", "1")

    return b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + tostring(root, encoding="unicode").encode("utf-8")


def _build_story_xml(story_id: str, text: str, style: str = "NormalParagraphStyle", font_size: float = 10, font_style: str = "Regular") -> bytes:
    """Build a Story XML file with text content."""
    root = Element("idPkg:Story")
    root.set("xmlns:idPkg", _NS)
    root.set("DOMVersion", _DOM_VERSION)

    story = SubElement(root, "Story")
    story.set("Self", story_id)
    story.set("AppliedTOCStyle", "n")
    story.set("UserText", "true")
    story.set("StoryTitle", "$ID/")

    sp = SubElement(story, "StoryPreference")
    sp.set("FrameType", "TextFrameType")

    psr = SubElement(story, "ParagraphStyleRange")
    psr.set("AppliedParagraphStyle", f"ParagraphStyle/$ID/{style}")

    csr = SubElement(psr, "CharacterStyleRange")
    csr.set("AppliedCharacterStyle", "CharacterStyle/$ID/[No character style]")
    csr.set("PointSize", f"{font_size:.2f}")
    csr.set("FontStyle", font_style)

    content = SubElement(csr, "Content")
    content.text = text

    return b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + tostring(root, encoding="unicode").encode("utf-8")


def _make_rect_points(x: float, y: float, w: float, h: float) -> str:
    """Create PathPointArray XML string for a rectangle.

    IDML coordinates: origin top-left, Y down. Points are [x, y].
    """
    return ""


def _build_spread_xml(
    spread_id: str,
    width_pt: float,
    height_pt: float,
    text_blocks: list[TextBlock],
    story_ids: list[str],
    layer_ids: dict[str, str],
    swatches: list[ColorSwatch],
) -> bytes:
    """Build a Spread XML with page items (text frames, rectangles)."""
    root = Element("idPkg:Spread")
    root.set("xmlns:idPkg", _NS)
    root.set("DOMVersion", _DOM_VERSION)

    spread = SubElement(root, "Spread")
    spread.set("Self", spread_id)
    spread.set("FlattenerOverride", "Default")
    spread.set("PageCount", "1")

    # Page
    page = SubElement(spread, "Page")
    page.set("Self", _uid())
    page.set("GeometricBounds", f"0 0 {height_pt:.4f} {width_pt:.4f}")
    page.set("ItemTransform", "1 0 0 1 0 0")

    mp = SubElement(page, "MarginPreference")
    mp.set("Top", "36")
    mp.set("Bottom", "36")
    mp.set("Left", "36")
    mp.set("Right", "36")

    # Background rectangle
    bg_swatch = next((s for s in swatches if s.role == "background"), None)
    if bg_swatch:
        bg_rect = SubElement(spread, "Rectangle")
        bg_rect.set("Self", _uid())
        bg_rect.set("ContentType", "Unassigned")
        bg_rect.set("ItemLayer", layer_ids.get("Background", ""))
        bg_rect.set("ItemTransform", "1 0 0 1 0 0")
        bg_rect.set("FillColor", f"Color/{bg_swatch.name}")
        bg_rect.set("StrokeColor", "Swatch/None")
        props = SubElement(bg_rect, "Properties")
        pg = SubElement(props, "PathGeometry")
        gpt = SubElement(pg, "GeometryPathType")
        gpt.set("PathOpen", "false")
        ppa = SubElement(gpt, "PathPointArray")
        for px, py in [(0, 0), (0, height_pt), (width_pt, height_pt), (width_pt, 0)]:
            pp = SubElement(ppa, "PathPointType")
            pp.set("Anchor", f"{px:.4f} {py:.4f}")
            pp.set("LeftDirection", f"{px:.4f} {py:.4f}")
            pp.set("RightDirection", f"{px:.4f} {py:.4f}")

    # Text frames
    for i, tb in enumerate(text_blocks):
        if i >= len(story_ids):
            break
        if not tb.bbox or len(tb.bbox) < 4:
            continue

        nx, ny, nw, nh = tb.bbox
        x = (nx / 1000.0) * width_pt
        y = (ny / 1000.0) * height_pt
        w = max((nw / 1000.0) * width_pt, 20)
        h = max((nh / 1000.0) * height_pt, 14)

        tf = SubElement(spread, "TextFrame")
        tf.set("Self", _uid())
        tf.set("ParentStory", story_ids[i])
        tf.set("ContentType", "TextType")
        tf.set("ItemLayer", layer_ids.get("Text", ""))
        tf.set("ItemTransform", f"1 0 0 1 {x:.4f} {y:.4f}")

        props = SubElement(tf, "Properties")
        pg = SubElement(props, "PathGeometry")
        gpt = SubElement(pg, "GeometryPathType")
        gpt.set("PathOpen", "false")
        ppa = SubElement(gpt, "PathPointArray")
        for px, py in [(0, 0), (0, h), (w, h), (w, 0)]:
            pp = SubElement(ppa, "PathPointType")
            pp.set("Anchor", f"{px:.4f} {py:.4f}")
            pp.set("LeftDirection", f"{px:.4f} {py:.4f}")
            pp.set("RightDirection", f"{px:.4f} {py:.4f}")

    return b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + tostring(root, encoding="unicode").encode("utf-8")


def _build_designmap_xml(
    spread_id: str,
    story_ids: list[str],
    layer_ids: dict[str, str],
) -> bytes:
    """Build designmap.xml — the root manifest."""
    root = Element("Document")
    root.set("xmlns:idPkg", _NS)
    root.set("DOMVersion", _DOM_VERSION)
    root.set("Self", "d")

    # Layers
    for name, lid in layer_ids.items():
        layer = SubElement(root, "Layer")
        layer.set("Self", lid)
        layer.set("Name", name)
        layer.set("Visible", "true")
        layer.set("Locked", "true" if name == "Reference" else "false")

    # Spread reference
    sp = SubElement(root, "idPkg:Spread")
    sp.set("src", f"Spreads/Spread_{spread_id}.xml")

    # Story references
    for sid in story_ids:
        st = SubElement(root, "idPkg:Story")
        st.set("src", f"Stories/Story_{sid}.xml")

    # Resource references
    for res in ["Graphic", "Fonts", "Styles", "Preferences"]:
        r = SubElement(root, f"idPkg:{res}")
        r.set("src", f"Resources/{res}.xml")

    return b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + tostring(root, encoding="unicode").encode("utf-8")


def build_idml(
    analysis: DesignAnalysis,
    enrichment: EnrichmentResult | None = None,
    config: ExportConfig | None = None,
) -> bytes:
    """Build a complete IDML file for InDesign.

    Args:
        analysis: Design analysis from AI Vision.
        enrichment: Optional enrichment with generated assets.
        config: Export configuration.

    Returns:
        IDML file as bytes (ZIP archive).
    """
    bleed_mm = config.bleed_mm if config else 3.0
    bleed_pt = mm_to_pt(bleed_mm)

    dims = analysis.package_spec.dimensions
    width_pt = dims.width_pt
    height_pt = dims.height_pt

    # Layer IDs
    layer_names = ["Dieline", "Background", "Graphics", "Text", "Regulatory", "Technical"]
    layer_ids = {name: _uid() for name in layer_names}

    # Create stories for each text block
    story_ids = []
    stories_data: list[tuple[str, bytes]] = []

    for tb in analysis.text_blocks:
        sid = _uid()
        story_ids.append(sid)
        font_size = tb.font_size_pt or 10
        font_style = "Bold" if "bold" in tb.font_style else "Regular"
        story_xml = _build_story_xml(
            story_id=sid,
            text=tb.content,
            font_size=font_size,
            font_style=font_style,
        )
        stories_data.append((f"Stories/Story_{sid}.xml", story_xml))

    # Spread
    spread_id = _uid()
    spread_xml = _build_spread_xml(
        spread_id=spread_id,
        width_pt=width_pt,
        height_pt=height_pt,
        text_blocks=analysis.text_blocks,
        story_ids=story_ids,
        layer_ids=layer_ids,
        swatches=analysis.color_swatches,
    )

    # Designmap
    designmap_xml = _build_designmap_xml(
        spread_id=spread_id,
        story_ids=story_ids,
        layer_ids=layer_ids,
    )

    # Assemble ZIP
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # mimetype MUST be first and STORED (uncompressed)
        zf.writestr(
            "mimetype",
            _build_mimetype(),
            compress_type=zipfile.ZIP_STORED,
        )

        # META-INF
        zf.writestr("META-INF/container.xml", _build_container_xml())

        # designmap.xml
        zf.writestr("designmap.xml", designmap_xml)

        # Resources
        zf.writestr("Resources/Graphic.xml", _build_graphic_xml(analysis.color_swatches))
        zf.writestr("Resources/Fonts.xml", _build_fonts_xml())
        zf.writestr("Resources/Styles.xml", _build_styles_xml())
        zf.writestr("Resources/Preferences.xml", _build_preferences_xml(width_pt, height_pt, bleed_pt))

        # Spreads
        zf.writestr(f"Spreads/Spread_{spread_id}.xml", spread_xml)

        # Stories
        for story_path, story_data in stories_data:
            zf.writestr(story_path, story_data)

    return buf.getvalue()
