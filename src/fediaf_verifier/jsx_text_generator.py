"""Generate Illustrator ExtendScript (.jsx) for placing label text frames.

The generated script creates a new layer with text frames for each
section of the generated label text. Unlike jsx_generator.py (which
draws annotation rectangles over existing artwork), this module creates
*content* text frames that the designer can reposition and style.

Usage in Illustrator:
  File > Scripts > Other Script... > select the .jsx file
"""

from __future__ import annotations


def _escape_js(text: str) -> str:
    """Escape a string for use inside JavaScript single-quoted string."""
    return (
        text.replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace("\n", "\\n")
        .replace("\r", "")
    )


def generate_text_jsx(
    sections: list[dict],
    language_name: str,
    filename: str = "",
) -> str:
    """Generate an Illustrator ExtendScript that creates text frames.

    Each section dict should have:
      - "title": str  (section heading, rendered bold 10pt)
      - "content": str (section body, rendered regular 8pt)

    The script:
      1. Asks user to choose mapping target (selection / artboard / all content)
      2. Creates a new layer "Label Text - {language}"
      3. For each section, creates a text frame with title + content
      4. Stacks sections vertically with spacing
      5. Supports CMYK/RGB document color spaces
      6. Locks the layer after creation

    Args:
        sections: List of section dicts with "title" and "content" keys.
        language_name: Display language name (e.g. "English", "Deutsch").
        filename: Original source filename (for the script header comment).

    Returns:
        Complete .jsx script as a string.
    """
    if not sections:
        return (
            "// BULT Quality Assurance -- brak sekcji tekstowych do utworzenia.\n"
            "alert('Brak sekcji tekstowych do utworzenia.');\n"
        )

    # Build JS array of sections
    js_sections = "[\n"
    for sec in sections:
        title = _escape_js(str(sec.get("title", "")))
        content = _escape_js(str(sec.get("content", "")))
        js_sections += f"  {{title:'{title}',content:'{content}'}},\n"
    js_sections += "]"

    escaped_filename = _escape_js(filename)
    escaped_language = _escape_js(language_name)
    layer_name = f"Label Text - {_escape_js(language_name)}"

    script = f"""\
// ==========================================================
// BULT Quality Assurance -- Tekst etykiety ({escaped_language})
// Plik zrodlowy: {escaped_filename}
// Wygenerowano automatycznie -- NIE edytuj recznie.
// ==========================================================
// Uzycie:
//   1. Otworz etykiete w Illustratorze
//   2. OPCJONALNIE: zaznacz prostokat/obiekt obejmujacy
//      obszar docelowy dla tekstu
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
    var hasSelection = doc.selection && doc.selection.length > 0;

    var modeDialog = new Window('dialog', 'BULT QA - Obszar dla tekstu');
    modeDialog.orientation = 'column';
    modeDialog.alignChildren = ['fill', 'top'];

    var infoGroup = modeDialog.add('group');
    infoGroup.alignment = ['fill', 'top'];
    var infoText = infoGroup.add('statictext', undefined,
        'Wybierz obszar, w ktorym umiescic tekst etykiety:', {{multiline: true}});
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
            ? 'Wykryto zaznaczenie - tekst zostanie umieszczony w tym obszarze.'
            : 'Brak zaznaczenia. Zaznacz obszar docelowy przed uruchomieniem dla najlepszych wynikow.',
        {{multiline: true}});
    hintText.preferredSize = [350, 40];

    var btnGroup = modeDialog.add('group');
    btnGroup.add('button', undefined, 'OK', {{name: 'ok'}});
    btnGroup.add('button', undefined, 'Anuluj', {{name: 'cancel'}});

    if (modeDialog.show() !== 1) {{
        return;
    }}

    // Determine target bounds: [left, top, right, bottom]
    var targetRect;

    if (optSelection.value && hasSelection) {{
        var sel = doc.selection;
        if (sel.length === 1) {{
            targetRect = sel[0].visibleBounds;
        }} else {{
            var minX = Infinity, maxX = -Infinity;
            var minY = Infinity, maxY = -Infinity;
            for (var s = 0; s < sel.length; s++) {{
                var b = sel[s].visibleBounds;
                if (b[0] < minX) minX = b[0];
                if (b[2] > maxX) maxX = b[2];
                if (b[3] < minY) minY = b[3];
                if (b[1] > maxY) maxY = b[1];
            }}
            targetRect = [minX, maxY, maxX, minY];
        }}
    }} else if (optContent.value) {{
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
        var ab = doc.artboards[doc.artboards.getActiveArtboardIndex()];
        targetRect = ab.artboardRect;
    }}

    var tLeft = targetRect[0];
    var tTop = targetRect[1];
    var tRight = targetRect[2];
    var tBottom = targetRect[3];
    var tW = tRight - tLeft;
    var tH = tTop - tBottom;

    if (tW <= 0 || tH <= 0) {{
        alert('Nieprawidlowy obszar (zerowa szerokosc lub wysokosc).');
        return;
    }}

    // ====== KROK 2: Warstwa tekstowa ======
    var layerName = '{layer_name}';
    var textLayer;
    try {{
        textLayer = doc.layers.getByName(layerName);
        textLayer.locked = false;
        while (textLayer.pageItems.length > 0) {{
            textLayer.pageItems[0].remove();
        }}
    }} catch(e) {{
        textLayer = doc.layers.add();
        textLayer.name = layerName;
    }}

    doc.selection = null;

    // ====== KROK 3: Helper - kolor wg trybu dokumentu ======
    var isCMYK = (doc.documentColorSpace === DocumentColorSpace.CMYK);

    function makeColor(r, g, b) {{
        if (isCMYK) {{
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

    // ====== KROK 4: Tworzenie ramek tekstowych ======
    var sections = {js_sections};

    var titleSize = 10;
    var bodySize = 8;
    var sectionSpacing = 14;
    var margin = 10;
    var frameWidth = tW - 2 * margin;
    var cursorY = tTop - margin;
    var blackColor = makeColor(0, 0, 0);
    var titleColor = makeColor(30, 30, 120);

    for (var i = 0; i < sections.length; i++) {{
        var sec = sections[i];

        // Estimate frame height: title line + content lines
        var contentLines = sec.content.split('\\n');
        var estimatedLines = 1 + contentLines.length;
        var estimatedHeight = (titleSize + 4) + (estimatedLines * (bodySize + 2)) + 8;

        // Clamp frame within target area
        if (cursorY - estimatedHeight < tBottom) {{
            estimatedHeight = cursorY - tBottom;
        }}
        if (estimatedHeight < titleSize + bodySize + 8) {{
            break; // No more space
        }}

        // Create area text frame
        var frameTop = cursorY;
        var frameLeft = tLeft + margin;
        var frameRect = textLayer.pathItems.rectangle(
            frameTop, frameLeft, frameWidth, estimatedHeight
        );
        frameRect.filled = false;
        frameRect.stroked = false;

        var textFrame = textLayer.textFrames.areaText(frameRect);

        // Add title
        textFrame.contents = sec.title + '\\n' + sec.content;

        // Style title portion (first line)
        var titleLen = sec.title.length;
        if (titleLen > 0 && textFrame.characters.length >= titleLen) {{
            var titleRange = textFrame.characters;
            for (var t = 0; t < titleLen; t++) {{
                try {{
                    titleRange[t].characterAttributes.size = titleSize;
                    titleRange[t].characterAttributes.textFont =
                        app.textFonts.getByName('ArialMT');
                    titleRange[t].characterAttributes.fillColor = titleColor;
                }} catch(ef) {{
                    // Font not available - use default
                    titleRange[t].characterAttributes.size = titleSize;
                    titleRange[t].characterAttributes.fillColor = titleColor;
                }}
            }}
        }}

        // Style body portion (after title + newline)
        var bodyStart = titleLen + 1; // +1 for the newline
        if (bodyStart < textFrame.characters.length) {{
            for (var c = bodyStart; c < textFrame.characters.length; c++) {{
                try {{
                    textFrame.characters[c].characterAttributes.size = bodySize;
                    textFrame.characters[c].characterAttributes.fillColor = blackColor;
                }} catch(ef2) {{}}
            }}
        }}

        // Move cursor down
        cursorY = frameTop - estimatedHeight - sectionSpacing;
    }}

    // Lock layer
    textLayer.locked = true;

    alert(
        'BULT Quality Assurance\\n\\n' +
        'Utworzono ' + sections.length + ' sekcji tekstowych na warstwie "' + layerName + '".\\n\\n' +
        'Mozesz:\\n' +
        '- Odblokowac warstwe i przesunac/zmienic rozmiar ramek\\n' +
        '- Zmienic czcionke na docelowa\\n' +
        '- Dostosowac rozmiary i kolory tekstu\\n' +
        '- Usunac warstwe (prawy klik > Delete Layer)\\n\\n' +
        'UWAGA: Sprawdz czy wybrana czcionka zawiera\\n' +
        'wszystkie znaki diakrytyczne dla danego jezyka.'
    );
}})();
"""
    return script
