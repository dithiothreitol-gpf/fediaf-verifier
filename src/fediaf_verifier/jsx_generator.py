"""Generate Adobe Illustrator ExtendScript (.jsx) for annotating labels.

The generated script adds a "QC Annotations" layer with rectangles and
text labels marking detected issues. The user runs it via:
  File > Scripts > Other Script... > select the .jsx file

Coordinate system note:
  AI returns normalized 0-1000 coords (origin = top-left).
  Illustrator uses points with origin at bottom-left (Y increases upward).
  The generated script reads target area bounds at runtime and converts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fediaf_verifier.models.label_structure import LabelStructureReport


def _escape_js(text: str) -> str:
    """Escape a string for use inside JavaScript single-quoted string."""
    return (
        text.replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace("\n", "\\n")
        .replace("\r", "")
    )


def generate_jsx(
    report: LabelStructureReport,
    filename: str = "",
) -> str:
    """Generate an Illustrator ExtendScript (.jsx) that annotates the label.

    The script:
      1. Asks user to choose mapping target (selection / artboard / all content)
      2. Creates a new layer "QC Annotations"
      3. Draws colored rectangles at detected issue locations
      4. Adds text labels describing each issue
      5. User can toggle visibility or delete the layer after review

    Args:
        report: Label structure report with bbox coordinates.
        filename: Original label filename (for the script header comment).

    Returns:
        Complete .jsx script as a string.
    """
    # Collect all annotation items
    annotations: list[dict] = []

    # Structure issues
    for issue in report.structure_issues:
        if not issue.bbox:
            continue
        color_map = {
            "critical": {"r": 220, "g": 50, "b": 50},
            "warning": {"r": 255, "g": 180, "b": 0},
            "info": {"r": 50, "g": 130, "b": 230},
        }
        color = color_map.get(issue.severity, color_map["warning"])
        annotations.append({
            "bbox": issue.bbox,
            "color": color,
            "label": f"[{issue.issue_type}]",
            "description": issue.description,
            "stroke_width": 2,
            "dashed": False,
        })

    # Glyph issues
    for glyph in report.glyph_issues:
        if not glyph.bbox:
            continue
        annotations.append({
            "bbox": glyph.bbox,
            "color": {"r": 204, "g": 0, "b": 153},
            "label": f"[{glyph.language_code.upper()}] {glyph.issue_type}",
            "description": (
                f"{glyph.affected_text} -> {glyph.expected_text}"
            ),
            "stroke_width": 2,
            "dashed": True,
        })

    # Language section boundaries
    for sec in report.language_sections:
        if not sec.bbox:
            continue
        ok = sec.content_complete and sec.marker_present
        color = (
            {"r": 60, "g": 180, "b": 60}
            if ok
            else {"r": 255, "g": 180, "b": 0}
        )
        annotations.append({
            "bbox": sec.bbox,
            "color": color,
            "label": sec.language_code.upper(),
            "description": sec.language_name,
            "stroke_width": 1,
            "dashed": True,
        })

    if not annotations:
        return (
            "// BULT Quality Assurance -- brak problemow z bbox do oznaczenia.\n"
            "// Etykieta nie wymaga wizualnych adnotacji.\n"
            "alert('Brak problemow do oznaczenia.');\n"
        )

    # Build the annotations array as JS literal
    js_annotations = "[\n"
    for ann in annotations:
        bx, by, bw, bh = ann["bbox"]
        c = ann["color"]
        label = _escape_js(ann["label"])
        desc = _escape_js(ann["description"])
        js_annotations += (
            f"  {{"
            f"bx:{bx},by:{by},bw:{bw},bh:{bh},"
            f"r:{c['r']},g:{c['g']},b:{c['b']},"
            f"sw:{ann['stroke_width']},"
            f"dashed:{str(ann['dashed']).lower()},"
            f"label:'{label}',"
            f"desc:'{desc}'"
            f"}},\n"
        )
    js_annotations += "]"

    escaped_filename = _escape_js(filename)

    script = f"""\
// ==========================================================
// BULT Quality Assurance -- Annotacje QC
// Plik zrodlowy: {escaped_filename}
// Wygenerowano automatycznie -- NIE edytuj recznie.
// ==========================================================
// Uzycie:
//   1. Otworz etykiete w Illustratorze
//   2. OPCJONALNIE: zaznacz prostokat/obiekt obejmujacy
//      obszar etykiety ktora analizowales
//   3. File > Scripts > Other Script... > wybierz ten plik
//   4. Wybierz tryb mapowania w dialogu
// ==========================================================

(function() {{
    if (app.documents.length === 0) {{
        alert('Brak otwartego dokumentu.\\nOtworz etykiete i uruchom ponownie.');
        return;
    }}

    var doc = app.activeDocument;

    // ====== KROK 1: Wybor obszaru mapowania ======
    // AI analizowalo wyeksportowany obraz (PDF/JPG/PNG).
    // Musimy okreslic, ktory obszar w pliku .ai odpowiada temu obrazowi.

    var hasSelection = doc.selection && doc.selection.length > 0;

    var modeDialog = new Window('dialog', 'BULT QA - Obszar mapowania');
    modeDialog.orientation = 'column';
    modeDialog.alignChildren = ['fill', 'top'];

    var infoGroup = modeDialog.add('group');
    infoGroup.alignment = ['fill', 'top'];
    var infoText = infoGroup.add('statictext', undefined,
        'Wybierz obszar, do ktorego dopasowac oznaczenia:', {{multiline: true}});
    infoText.preferredSize = [350, 30];

    var radioGroup = modeDialog.add('group');
    radioGroup.orientation = 'column';
    radioGroup.alignChildren = ['left', 'center'];

    var optSelection = radioGroup.add('radiobutton', undefined,
        'Zaznaczony obiekt (najdokladniejszy)');
    var optArtboard = radioGroup.add('radiobutton', undefined,
        'Aktywny artboard');
    var optContent = radioGroup.add('radiobutton', undefined,
        'Wszystkie obiekty (visibleBounds)');

    if (hasSelection) {{
        optSelection.value = true;
    }} else {{
        optSelection.enabled = false;
        optArtboard.value = true;
    }}

    var hintText = modeDialog.add('statictext', undefined,
        hasSelection
            ? 'Wykryto zaznaczenie - zalecamy opcje 1.'
            : 'Brak zaznaczenia. Zaznacz obszar etykiety przed uruchomieniem skryptu dla najlepszych wynikow.',
        {{multiline: true}});
    hintText.preferredSize = [350, 40];

    var btnGroup = modeDialog.add('group');
    btnGroup.add('button', undefined, 'OK', {{name: 'ok'}});
    btnGroup.add('button', undefined, 'Anuluj', {{name: 'cancel'}});

    if (modeDialog.show() !== 1) {{
        return; // user cancelled
    }}

    // Determine target bounds: [left, top, right, bottom]
    // Illustrator: top > bottom (Y up), left < right (X right)
    var targetRect;

    if (optSelection.value && hasSelection) {{
        // Use bounding box of the selected object(s)
        var sel = doc.selection;
        if (sel.length === 1) {{
            targetRect = sel[0].visibleBounds;
        }} else {{
            // Multiple selection: compute union of all bounds
            var minX = Infinity, maxX = -Infinity;
            var minY = Infinity, maxY = -Infinity;
            for (var s = 0; s < sel.length; s++) {{
                var b = sel[s].visibleBounds;
                if (b[0] < minX) minX = b[0];
                if (b[2] > maxX) maxX = b[2];
                if (b[3] < minY) minY = b[3]; // bottom
                if (b[1] > maxY) maxY = b[1]; // top
            }}
            targetRect = [minX, maxY, maxX, minY];
        }}
    }} else if (optContent.value) {{
        // Use visible bounds of all document content
        // Compute from all page items
        var allItems = doc.pageItems;
        if (allItems.length === 0) {{
            alert('Dokument nie zawiera obiektow.');
            return;
        }}
        var minX = Infinity, maxX = -Infinity;
        var minY = Infinity, maxY = -Infinity;
        for (var p = 0; p < allItems.length; p++) {{
            try {{
                var b = allItems[p].visibleBounds;
                if (b[0] < minX) minX = b[0];
                if (b[2] > maxX) maxX = b[2];
                if (b[3] < minY) minY = b[3];
                if (b[1] > maxY) maxY = b[1];
            }} catch(e) {{}}
        }}
        targetRect = [minX, maxY, maxX, minY];
    }} else {{
        // Use active artboard
        var ab = doc.artboards[doc.artboards.getActiveArtboardIndex()];
        targetRect = ab.artboardRect;
    }}

    var tLeft = targetRect[0];
    var tTop = targetRect[1];
    var tRight = targetRect[2];
    var tBottom = targetRect[3];
    var tW = tRight - tLeft;
    var tH = tTop - tBottom; // positive (top > bottom in AI coords)

    if (tW <= 0 || tH <= 0) {{
        alert('Nieprawidlowy obszar mapowania (zerowa szerokosc lub wysokosc).');
        return;
    }}

    // ====== KROK 2: Warstwa QC ======
    var layerName = 'QC Annotations';
    var qcLayer;
    try {{
        qcLayer = doc.layers.getByName(layerName);
        // Unlock before clearing (layer was locked on previous run)
        qcLayer.locked = false;
        while (qcLayer.pageItems.length > 0) {{
            qcLayer.pageItems[0].remove();
        }}
    }} catch(e) {{
        qcLayer = doc.layers.add();
        qcLayer.name = layerName;
    }}

    // Deselect all to avoid accidentally modifying selection
    doc.selection = null;

    // ====== KROK 3: Helper - kolor wg trybu dokumentu ======
    var isCMYK = (doc.documentColorSpace === DocumentColorSpace.CMYK);

    function makeColor(r, g, b) {{
        if (isCMYK) {{
            // Convert RGB 0-255 to CMYK (approximate)
            var rn = r / 255.0, gn = g / 255.0, bn = b / 255.0;
            var k = 1 - Math.max(rn, gn, bn);
            var c, m, y;
            if (k >= 1) {{
                c = 0; m = 0; y = 0;
            }} else {{
                c = (1 - rn - k) / (1 - k) * 100;
                m = (1 - gn - k) / (1 - k) * 100;
                y = (1 - bn - k) / (1 - k) * 100;
            }}
            var cmyk = new CMYKColor();
            cmyk.cyan = Math.round(c);
            cmyk.magenta = Math.round(m);
            cmyk.yellow = Math.round(y);
            cmyk.black = Math.round(k * 100);
            return cmyk;
        }} else {{
            var rgb = new RGBColor();
            rgb.red = r;
            rgb.green = g;
            rgb.blue = b;
            return rgb;
        }}
    }}

    // ====== KROK 4: Rysowanie adnotacji ======
    var annotations = {js_annotations};

    for (var i = 0; i < annotations.length; i++) {{
        var a = annotations[i];

        // Convert normalized 0-1000 coords to Illustrator points
        // Input:  origin top-left, Y increases downward, range 0-1000
        // Output: origin bottom-left, Y increases upward, points
        var x0 = tLeft + (a.bx / 1000.0) * tW;
        var y0 = tTop  - (a.by / 1000.0) * tH;  // flip Y
        var rW = (a.bw / 1000.0) * tW;
        var rH = (a.bh / 1000.0) * tH;

        // pathItems.rectangle(top, left, width, height)
        if (rW < 1) rW = 1;
        if (rH < 1) rH = 1;
        var rect = qcLayer.pathItems.rectangle(y0, x0, rW, rH);
        rect.filled = false;
        rect.stroked = true;
        rect.strokeColor = makeColor(a.r, a.g, a.b);
        rect.strokeWidth = a.sw;

        if (a.dashed) {{
            rect.strokeDashes = [4, 3];
        }}

        // Text label above the rectangle
        var labelText = qcLayer.textFrames.add();
        labelText.contents = a.label;
        // Position label above rect, clamped to target area
        var labelY = Math.min(y0 + 10, tTop);
        labelText.position = [x0, labelY];

        var textRange = labelText.textRange;
        textRange.characterAttributes.size = Math.max(5, Math.min(8, tH / 120));
        textRange.characterAttributes.fillColor = makeColor(a.r, a.g, a.b);
    }}

    // Lock layer
    qcLayer.locked = true;

    alert(
        'BULT Quality Assurance\\n\\n' +
        'Dodano ' + annotations.length + ' adnotacji na warstwie "' + layerName + '".\\n' +
        'Obszar mapowania: ' + Math.round(tW) + ' x ' + Math.round(tH) + ' pt\\n\\n' +
        'Po przejrzeniu mozesz:\\n' +
        '- Ukryc warstwe (ikona oka w panelu Layers)\\n' +
        '- Usunac warstwe (prawy klik > Delete Layer)\\n\\n' +
        'Jesli oznaczenia nie pasuja:\\n' +
        '- Zaznacz obszar etykiety narzedziem Selection (V)\\n' +
        '- Uruchom skrypt ponownie'
    );
}})();
"""
    return script
