"""Deterministic artwork inspection: pixel diff, color analysis, print readiness.

All functions operate on raw image bytes / PIL Images — no AI calls.
External dependencies: opencv-python, scikit-image, colormath, Pillow.
"""

from __future__ import annotations

import base64
import io

from loguru import logger
from PIL import Image

# ---------------------------------------------------------------------------
# Lazy imports for heavy optional deps
# ---------------------------------------------------------------------------


def _import_numpy():
    try:
        import numpy as np
        return np
    except ImportError as e:
        raise ImportError(
            "numpy jest wymagany dla inspekcji artwork. "
            "Zainstaluj: pip install numpy"
        ) from e


def _import_cv2():
    try:
        import cv2
        return cv2
    except ImportError as e:
        raise ImportError(
            "opencv-python jest wymagany dla inspekcji artwork. "
            "Zainstaluj: pip install opencv-python"
        ) from e


def _import_ssim():
    try:
        from skimage.metrics import structural_similarity
        return structural_similarity
    except ImportError as e:
        raise ImportError(
            "scikit-image jest wymagany dla inspekcji artwork. "
            "Zainstaluj: pip install scikit-image"
        ) from e


def _import_colormath():
    """Import colormath with numpy compatibility patch.

    colormath 3.x uses numpy.asscalar() which was removed in numpy 1.24.
    We monkey-patch it before importing colormath.
    """
    try:
        import numpy as _np
        if not hasattr(_np, "asscalar"):
            _np.asscalar = lambda a: a.item()  # type: ignore[attr-defined]

        from colormath.color_conversions import convert_color
        from colormath.color_diff import delta_e_cie2000
        from colormath.color_objects import LabColor, sRGBColor
        return convert_color, delta_e_cie2000, LabColor, sRGBColor
    except ImportError as e:
        raise ImportError(
            "colormath jest wymagany dla analizy kolorow. "
            "Zainstaluj: pip install colormath"
        ) from e


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _b64_to_pil(b64: str) -> Image.Image:
    """Decode base64 string to PIL Image."""
    data = base64.b64decode(b64)
    return Image.open(io.BytesIO(data))


def _pil_to_cv2(img: Image.Image):
    """Convert PIL Image (RGB) to OpenCV BGR numpy array."""
    np = _import_numpy()
    rgb = np.array(img.convert("RGB"))
    cv2 = _import_cv2()
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def _cv2_to_b64_png(arr) -> str:
    """Encode OpenCV BGR image to base64 PNG string."""
    cv2 = _import_cv2()
    _, buf = cv2.imencode(".png", arr)
    return base64.b64encode(buf.tobytes()).decode("ascii")


def _approximate_color_name(r: int, g: int, b: int) -> str:
    """Return a rough human-readable color name."""
    # Simple heuristic — not exhaustive
    h, s, v = _rgb_to_hsv_int(r, g, b)
    if v < 30:
        return "czarny"
    if s < 20 and v > 200:
        return "bialy"
    if s < 20:
        return "szary"
    if h < 15 or h >= 345:
        return "czerwony"
    if h < 45:
        return "pomaranczowy"
    if h < 70:
        return "zolty"
    if h < 160:
        return "zielony"
    if h < 250:
        return "niebieski"
    if h < 330:
        return "fioletowy"
    return "czerwony"


def _rgb_to_hsv_int(r: int, g: int, b: int) -> tuple[int, int, int]:
    """Convert RGB (0-255) to HSV with H in 0-360, S/V in 0-255."""
    r_, g_, b_ = r / 255.0, g / 255.0, b / 255.0
    mx, mn = max(r_, g_, b_), min(r_, g_, b_)
    diff = mx - mn
    # Hue
    if diff == 0:
        h = 0
    elif mx == r_:
        h = (60 * ((g_ - b_) / diff) + 360) % 360
    elif mx == g_:
        h = (60 * ((b_ - r_) / diff) + 120) % 360
    else:
        h = (60 * ((r_ - g_) / diff) + 240) % 360
    # Saturation
    s = 0 if mx == 0 else (diff / mx) * 255
    # Value
    v = mx * 255
    return int(h), int(s), int(v)


# ---------------------------------------------------------------------------
# 1. PIXEL DIFF
# ---------------------------------------------------------------------------


def compute_pixel_diff(
    img_a_b64: str,
    img_b_b64: str,
    threshold: int = 30,
    min_region_area: int = 100,
) -> "PixelDiffReport":
    """Compare two images pixel-by-pixel.

    Args:
        img_a_b64: Base64-encoded master image.
        img_b_b64: Base64-encoded proof/new version image.
        threshold: Pixel intensity threshold for change detection (0–255).
        min_region_area: Minimum contour area (px) to report as a change region.

    Returns:
        PixelDiffReport with SSIM, changed pixel stats, diff regions, and overlay image.
    """
    from fediaf_verifier.models.artwork_inspection import PixelDiffRegion, PixelDiffReport

    np = _import_numpy()
    cv2 = _import_cv2()
    ssim_fn = _import_ssim()

    # Decode
    pil_a = _b64_to_pil(img_a_b64)
    pil_b = _b64_to_pil(img_b_b64)

    # Resize B to match A dimensions for fair comparison
    if pil_a.size != pil_b.size:
        logger.info(
            "Rozne rozmiary obrazow: A={}  B={} — skaluje B do A",
            pil_a.size, pil_b.size,
        )
        pil_b = pil_b.resize(pil_a.size, Image.LANCZOS)

    bgr_a = _pil_to_cv2(pil_a)
    bgr_b = _pil_to_cv2(pil_b)

    # Grayscale for SSIM and diff
    gray_a = cv2.cvtColor(bgr_a, cv2.COLOR_BGR2GRAY)
    gray_b = cv2.cvtColor(bgr_b, cv2.COLOR_BGR2GRAY)

    # SSIM
    ssim_val, ssim_diff = ssim_fn(gray_a, gray_b, full=True)
    ssim_val = float(ssim_val)

    # Absolute difference
    abs_diff = cv2.absdiff(gray_a, gray_b)
    _, binary_mask = cv2.threshold(abs_diff, threshold, 255, cv2.THRESH_BINARY)

    total_px = int(gray_a.shape[0] * gray_a.shape[1])
    changed_px = int(np.count_nonzero(binary_mask))
    changed_pct = (changed_px / total_px * 100) if total_px > 0 else 0.0

    # Find contour regions
    contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    regions: list[PixelDiffRegion] = []
    overlay = bgr_b.copy()

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_region_area:
            continue
        x, y, w, h = cv2.boundingRect(cnt)
        region_mask = binary_mask[y : y + h, x : x + w]
        region_changed = int(np.count_nonzero(region_mask))
        region_total = w * h
        region_pct = (region_changed / region_total * 100) if region_total > 0 else 0.0

        regions.append(
            PixelDiffRegion(x=x, y=y, w=w, h=h, change_pct=round(region_pct, 1))
        )
        # Draw red rectangle on overlay
        cv2.rectangle(overlay, (x, y), (x + w, y + h), (0, 0, 255), 2)

    # Colorize diff: red channel = changes
    diff_vis = np.zeros_like(bgr_a)
    diff_vis[:, :, 2] = binary_mask  # red channel
    blended = cv2.addWeighted(bgr_a, 0.6, diff_vis, 0.4, 0)

    # Verdict
    if changed_pct < 0.01:
        verdict = "identical"
    elif changed_pct < 1.0:
        verdict = "minor_changes"
    elif changed_pct < 5.0:
        verdict = "significant_changes"
    else:
        verdict = "major_changes"

    return PixelDiffReport(
        ssim_score=round(ssim_val, 4),
        changed_pixels_pct=round(changed_pct, 2),
        total_pixels=total_px,
        changed_pixels=changed_px,
        diff_regions=regions,
        diff_image_b64=_cv2_to_b64_png(blended),
        threshold_used=threshold,
        verdict=verdict,
    )


# ---------------------------------------------------------------------------
# 2. COLOR ANALYSIS
# ---------------------------------------------------------------------------


def extract_dominant_colors(
    img_b64: str,
    n_colors: int = 6,
    sample_size: int = 50_000,
) -> "ColorAnalysisReport":
    """Extract dominant colors from a label image using K-means clustering.

    Args:
        img_b64: Base64-encoded image.
        n_colors: Number of dominant colors to extract.
        sample_size: Max pixels to sample (for performance).

    Returns:
        ColorAnalysisReport with dominant colors and color space info.
    """
    from fediaf_verifier.models.artwork_inspection import ColorAnalysisReport, DominantColor

    np = _import_numpy()
    cv2 = _import_cv2()

    pil_img = _b64_to_pil(img_b64)

    # Detect color space from PIL mode
    color_space = "RGB"
    is_cmyk = False
    if pil_img.mode == "CMYK":
        color_space = "CMYK"
        is_cmyk = True
    elif pil_img.mode == "L":
        color_space = "Grayscale"
    elif pil_img.mode == "LAB" or pil_img.mode == "Lab":
        color_space = "LAB"

    # Convert to RGB for analysis
    rgb_img = pil_img.convert("RGB")
    pixels = np.array(rgb_img).reshape(-1, 3).astype(np.float32)

    # Guard: ensure enough pixels for K-means
    effective_colors = min(n_colors, len(pixels))
    if effective_colors < 1:
        return ColorAnalysisReport(
            color_space_detected=color_space,
            is_cmyk=is_cmyk,
        )

    # Subsample for performance
    if len(pixels) > sample_size:
        indices = np.random.default_rng(42).choice(len(pixels), sample_size, replace=False)
        pixels = pixels[indices]

    # K-means clustering
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
    _, labels, centers = cv2.kmeans(
        pixels, effective_colors, None, criteria, 10, cv2.KMEANS_PP_CENTERS
    )

    # Count pixels per cluster
    unique, counts = np.unique(labels, return_counts=True)
    total = counts.sum()

    colors: list[DominantColor] = []
    # Sort by count descending
    order = np.argsort(-counts)
    for idx in order:
        c = centers[int(unique[idx])]
        r, g, b = int(c[0]), int(c[1]), int(c[2])
        pct = float(counts[idx] / total * 100)
        hex_code = f"#{r:02x}{g:02x}{b:02x}"
        colors.append(
            DominantColor(
                hex=hex_code,
                r=r, g=g, b=b,
                percentage=round(pct, 1),
                name=_approximate_color_name(r, g, b),
            )
        )

    return ColorAnalysisReport(
        dominant_colors=colors,
        color_space_detected=color_space,
        is_cmyk=is_cmyk,
    )


def compare_colors(
    report_a: "ColorAnalysisReport",
    report_b: "ColorAnalysisReport",
) -> tuple["ColorAnalysisReport", "ColorAnalysisReport"]:
    """Compare dominant color palettes of two images using Delta E CIE2000.

    Mutates report_a in place by filling comparisons, max_delta_e,
    and color_consistency_score.

    Returns (report_a, report_b) for convenience.
    """
    from fediaf_verifier.models.artwork_inspection import ColorComparison

    convert_color, delta_e_cie2000, LabColor, sRGBColor = _import_colormath()

    comparisons: list[ColorComparison] = []
    max_de = 0.0

    # Match colors by palette order (top N from each)
    n = min(len(report_a.dominant_colors), len(report_b.dominant_colors))

    for i in range(n):
        ca = report_a.dominant_colors[i]
        cb = report_b.dominant_colors[i]

        lab_a = convert_color(
            sRGBColor(ca.r / 255, ca.g / 255, ca.b / 255), LabColor
        )
        lab_b = convert_color(
            sRGBColor(cb.r / 255, cb.g / 255, cb.b / 255), LabColor
        )

        de = float(delta_e_cie2000(lab_a, lab_b))

        if de < 2:
            verdict = "match"
        elif de < 5:
            verdict = "close"
        else:
            verdict = "mismatch"

        comparisons.append(
            ColorComparison(
                color_a_hex=ca.hex,
                color_b_hex=cb.hex,
                delta_e=round(de, 2),
                verdict=verdict,
            )
        )
        if de > max_de:
            max_de = de

    # Consistency score: 100 if all delta_e = 0, decays with max delta_e
    if comparisons:
        avg_de = sum(c.delta_e for c in comparisons) / len(comparisons)
        consistency = max(0.0, 100.0 - avg_de * 10)
    else:
        consistency = 100.0

    report_a.comparisons = comparisons
    report_a.max_delta_e = round(max_de, 2)
    report_a.color_consistency_score = round(consistency, 1)

    return report_a, report_b


# ---------------------------------------------------------------------------
# 2b. OCR TEXT COMPARISON
# ---------------------------------------------------------------------------


def _import_easyocr():
    try:
        import easyocr
        return easyocr
    except ImportError as e:
        raise ImportError(
            "easyocr jest wymagany dla porownania tekstu OCR. "
            "Zainstaluj: pip install easyocr"
        ) from e


_ocr_readers: dict[tuple[str, ...], object] = {}


def _get_ocr_reader(languages: tuple[str, ...]):
    """Get or create a cached EasyOCR Reader for the given languages."""
    if languages not in _ocr_readers:
        easyocr = _import_easyocr()
        _ocr_readers[languages] = easyocr.Reader(
            list(languages), gpu=False, verbose=False
        )
        logger.info("EasyOCR Reader zainicjalizowany: {}", languages)
    return _ocr_readers[languages]


def ocr_extract_text(
    img_b64: str,
    languages: list[str] | None = None,
) -> tuple[str, list["OCRTextBlock"]]:
    """Extract text from a label image using EasyOCR.

    Args:
        img_b64: Base64-encoded image.
        languages: Language codes for OCR (default: ['en', 'pl', 'de', 'fr']).

    Returns:
        Tuple of (full_text, list_of_blocks).
    """
    from fediaf_verifier.models.artwork_inspection import OCRTextBlock

    np = _import_numpy()
    easyocr = _import_easyocr()

    if languages is None:
        languages = ["en", "pl", "de", "fr"]

    pil_img = _b64_to_pil(img_b64)
    img_array = np.array(pil_img.convert("RGB"))

    reader = _get_ocr_reader(tuple(languages))
    results = reader.readtext(img_array)

    blocks: list[OCRTextBlock] = []
    lines: list[str] = []

    for bbox_pts, text, conf in results:
        # bbox_pts is [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
        xs = [p[0] for p in bbox_pts]
        ys = [p[1] for p in bbox_pts]
        bbox = [int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))]
        blocks.append(OCRTextBlock(text=text, confidence=float(conf), bbox=bbox))
        lines.append(text)

    full_text = "\n".join(lines)
    return full_text, blocks


def compare_ocr_texts(
    img_a_b64: str,
    img_b_b64: str,
    languages: list[str] | None = None,
) -> "OCRComparisonReport":
    """Extract text from two images via OCR and compare them.

    Returns:
        OCRComparisonReport with diffs, similarity score, and extracted text blocks.
    """
    import difflib

    from fediaf_verifier.models.artwork_inspection import (
        OCRComparisonReport,
        TextDiffChange,
    )

    text_a, blocks_a = ocr_extract_text(img_a_b64, languages)
    text_b, blocks_b = ocr_extract_text(img_b_b64, languages)

    # Compute similarity
    matcher = difflib.SequenceMatcher(None, text_a, text_b)
    similarity = matcher.ratio() * 100

    # Line-by-line diff
    lines_a = text_a.splitlines()
    lines_b = text_b.splitlines()

    changes: list[TextDiffChange] = []
    diff_ops = difflib.SequenceMatcher(None, lines_a, lines_b).get_opcodes()

    for tag, i1, i2, j1, j2 in diff_ops:
        if tag == "equal":
            continue
        elif tag == "replace":
            for k in range(max(i2 - i1, j2 - j1)):
                old = lines_a[i1 + k] if (i1 + k) < i2 else ""
                new = lines_b[j1 + k] if (j1 + k) < j2 else ""
                changes.append(TextDiffChange(
                    change_type="modified",
                    old_text=old,
                    new_text=new,
                    line_number=i1 + k + 1,
                ))
        elif tag == "delete":
            for k in range(i1, i2):
                changes.append(TextDiffChange(
                    change_type="removed",
                    old_text=lines_a[k],
                    line_number=k + 1,
                ))
        elif tag == "insert":
            for k in range(j1, j2):
                changes.append(TextDiffChange(
                    change_type="added",
                    new_text=lines_b[k],
                    line_number=k + 1,
                ))

    avg_conf_a = (
        sum(b.confidence for b in blocks_a) / len(blocks_a) if blocks_a else 0.0
    )
    avg_conf_b = (
        sum(b.confidence for b in blocks_b) / len(blocks_b) if blocks_b else 0.0
    )

    return OCRComparisonReport(
        text_a=text_a,
        text_b=text_b,
        blocks_a=blocks_a,
        blocks_b=blocks_b,
        changes=changes,
        similarity_pct=round(similarity, 1),
        total_changes=len(changes),
        avg_confidence_a=round(avg_conf_a, 3),
        avg_confidence_b=round(avg_conf_b, 3),
    )


# ---------------------------------------------------------------------------
# 2c. ICC COLOR PROFILE EXTRACTION
# ---------------------------------------------------------------------------


def extract_icc_profile(
    img_b64: str,
    media_type: str = "image/png",
) -> "ICCProfileInfo":
    """Extract ICC profile information from an image or PDF.

    Returns:
        ICCProfileInfo with profile details or has_profile=False.
    """
    from fediaf_verifier.models.artwork_inspection import ICCProfileInfo

    raw_bytes = base64.b64decode(img_b64)
    issues: list[str] = []

    is_pdf = media_type == "application/pdf" or raw_bytes[:5] == b"%PDF-"

    # For PDF, try extracting ICC via PyMuPDF
    if is_pdf:
        return _extract_icc_from_pdf(raw_bytes)

    # For images, use Pillow
    try:
        pil_img = Image.open(io.BytesIO(raw_bytes))
    except Exception:
        return ICCProfileInfo(issues=["Nie mozna otworzyc pliku"])

    icc_data = pil_img.info.get("icc_profile")
    if not icc_data:
        issues.append("Brak osadzonego profilu ICC — druk moze dac nieoczekiwane kolory")
        return ICCProfileInfo(has_profile=False, issues=issues)

    try:
        from PIL import ImageCms

        profile = ImageCms.getOpenProfile(io.BytesIO(icc_data))

        # Description
        desc = ""
        try:
            desc = ImageCms.getProfileDescription(profile) or ""
        except Exception:
            pass

        # Color space — access via profile.profile.xcolor_space
        cs = ""
        try:
            cs = profile.profile.xcolor_space.strip()
        except Exception:
            pass

        # Rendering intent — from profile header
        intent = ""
        intent_map = {0: "perceptual", 1: "relative_colorimetric",
                      2: "saturation", 3: "absolute_colorimetric"}
        try:
            intent = intent_map.get(profile.profile.rendering_intent, "")
        except Exception:
            pass

        # PCS (Profile Connection Space)
        pcs = ""
        try:
            pcs = profile.profile.pcs or ""
        except Exception:
            pass

        # Version
        version = ""
        try:
            version = str(profile.profile.version or "")
        except Exception:
            pass

        # Validate for print
        cs_upper = cs.upper()
        if cs_upper and cs_upper != "CMYK":
            issues.append(
                f"Profil ICC w przestrzeni {cs_upper} — druk wymaga profilu CMYK"
            )

        return ICCProfileInfo(
            has_profile=True,
            profile_name=desc.strip(),
            color_space=cs_upper,
            rendering_intent=intent,
            pcs=pcs,
            version=version,
            issues=issues,
        )
    except Exception as e:
        return ICCProfileInfo(
            has_profile=True,
            issues=[f"Profil ICC znaleziony ale nie mozna go odczytac: {e}"],
        )


def _extract_icc_from_pdf(pdf_bytes: bytes) -> "ICCProfileInfo":
    """Extract ICC profile info from PDF using PyMuPDF."""
    from fediaf_verifier.models.artwork_inspection import ICCProfileInfo

    try:
        import fitz
    except ImportError:
        return ICCProfileInfo(issues=["PyMuPDF wymagany do analizy ICC w PDF"])

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page = doc[0]

        # Check page colorspace
        # PyMuPDF doesn't directly expose ICC but we can check image colorspaces
        images = page.get_images(full=True)
        has_cmyk = False
        has_rgb = False

        for img_info in images:
            xref = img_info[0]
            try:
                pix = fitz.Pixmap(doc, xref)
                cs_name = pix.colorspace.name if pix.colorspace else ""
                if "cmyk" in cs_name.lower():
                    has_cmyk = True
                elif "rgb" in cs_name.lower():
                    has_rgb = True
                elif pix.n == 4 and not pix.alpha:
                    has_cmyk = True  # 4 channels without alpha → likely CMYK
                elif pix.n == 3:
                    has_rgb = True
                pix = None
            except Exception:
                pass

        doc.close()

        issues: list[str] = []
        if has_rgb and not has_cmyk:
            issues.append("PDF zawiera obrazy w RGB — druk wymaga CMYK")
        elif has_rgb and has_cmyk:
            issues.append("PDF zawiera mieszane przestrzenie barw (RGB + CMYK)")

        return ICCProfileInfo(
            has_profile=has_cmyk,
            color_space="CMYK" if has_cmyk else ("RGB" if has_rgb else "unknown"),
            issues=issues,
        )
    except Exception as e:
        return ICCProfileInfo(issues=[f"Blad analizy ICC w PDF: {e}"])


# ---------------------------------------------------------------------------
# 2d. SALIENCY / VISUAL ATTENTION (DeepGaze IIE or heuristic fallback)
# ---------------------------------------------------------------------------


def compute_saliency(
    img_b64: str,
    use_deepgaze: bool = True,
) -> "SaliencyReport":
    """Compute visual attention saliency map for a label image.

    Tries DeepGaze IIE first (if torch available), falls back to
    heuristic saliency based on contrast/color/edges.

    Returns:
        SaliencyReport with heatmap overlay and attention regions.
    """
    from fediaf_verifier.models.artwork_inspection import AttentionRegion, SaliencyReport

    np = _import_numpy()
    cv2 = _import_cv2()

    pil_img = _b64_to_pil(img_b64)
    img_rgb = np.array(pil_img.convert("RGB"))
    img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    h, w = img_bgr.shape[:2]

    # Try DeepGaze IIE
    saliency_map = None
    model_used = ""

    if use_deepgaze:
        try:
            saliency_map = _deepgaze_saliency(img_rgb)
            model_used = "DeepGaze IIE"
        except Exception as e:
            logger.info("DeepGaze niedostepny ({}), fallback na heurystyki", e)

    # Fallback: heuristic saliency
    if saliency_map is None:
        saliency_map = _heuristic_saliency(img_bgr)
        model_used = "heuristic (contrast+color+edges)"

    # Normalize to 0-255
    sal_min, sal_max = saliency_map.min(), saliency_map.max()
    if sal_max > sal_min:
        saliency_norm = ((saliency_map - sal_min) / (sal_max - sal_min) * 255).astype(
            np.uint8
        )
    else:
        saliency_norm = np.zeros((h, w), dtype=np.uint8)

    # Generate heatmap overlay
    heatmap_color = cv2.applyColorMap(saliency_norm, cv2.COLORMAP_JET)
    heatmap_color = cv2.resize(heatmap_color, (w, h))
    overlay = cv2.addWeighted(img_bgr, 0.5, heatmap_color, 0.5, 0)
    heatmap_b64 = _cv2_to_b64_png(overlay)

    # Find top attention regions via thresholding
    _, thresh = cv2.threshold(saliency_norm, 180, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    total_attention = float(saliency_norm.sum()) or 1.0
    regions: list[AttentionRegion] = []

    for cnt in sorted(contours, key=cv2.contourArea, reverse=True)[:8]:
        if cv2.contourArea(cnt) < 100:
            continue
        rx, ry, rw, rh = cv2.boundingRect(cnt)
        region_attention = float(saliency_norm[ry : ry + rh, rx : rx + rw].sum())
        att_pct = region_attention / total_attention * 100
        regions.append(AttentionRegion(
            rank=len(regions) + 1,
            x=rx, y=ry, w=rw, h=rh,
            attention_pct=round(att_pct, 1),
        ))

    # --- Advanced metrics ---
    focus_metrics = _compute_focus_metrics(saliency_norm, regions)
    focus_score = _compute_composite_focus(focus_metrics)
    clarity = _compute_clarity(img_bgr)
    cognitive_load = _compute_cognitive_load(img_bgr)

    return SaliencyReport(
        heatmap_b64=heatmap_b64,
        attention_regions=regions,
        focus_score=round(focus_score, 1),
        focus_metrics=focus_metrics,
        clarity=clarity,
        cognitive_load=cognitive_load,
        model_used=model_used,
    )


_deepgaze_model = None


def _get_deepgaze_model():
    """Get or create cached DeepGaze IIE model."""
    global _deepgaze_model
    if _deepgaze_model is None:
        import torch

        import deepgaze_pytorch

        device = torch.device("cpu")
        _deepgaze_model = deepgaze_pytorch.DeepGazeIIE(pretrained=True).to(device)
        _deepgaze_model.eval()
        logger.info("DeepGaze IIE model loaded")
    return _deepgaze_model


def _make_centerbias(h: int, w: int):
    """Create a Gaussian centerbias prior (log-density).

    Real eye-tracking data shows people tend to look at the center of images.
    This is a smooth Gaussian approximation of the MIT1003 centerbias.
    """
    np = _import_numpy()
    cy, cx = h / 2.0, w / 2.0
    sigma_y, sigma_x = h / 4.0, w / 4.0
    Y, X = np.mgrid[:h, :w]
    centerbias = -((X - cx) ** 2 / (2 * sigma_x**2) + (Y - cy) ** 2 / (2 * sigma_y**2))
    # Normalize to log-density
    from scipy.special import logsumexp as _lse

    centerbias -= _lse(centerbias)
    return centerbias


def _deepgaze_saliency(img_rgb) -> "np.ndarray":
    """Run DeepGaze IIE saliency prediction. Requires torch."""
    np = _import_numpy()

    import torch
    from scipy.ndimage import zoom
    from scipy.special import logsumexp

    model = _get_deepgaze_model()
    device = torch.device("cpu")

    # Prepare input
    h, w = img_rgb.shape[:2]
    img_tensor = (
        torch.from_numpy(img_rgb).permute(2, 0, 1).unsqueeze(0).float().to(device)
    )

    # Gaussian centerbias prior (approximation of MIT1003 centerbias)
    centerbias = _make_centerbias(h, w)
    centerbias_tensor = (
        torch.from_numpy(centerbias).unsqueeze(0).unsqueeze(0).float().to(device)
    )

    with torch.no_grad():
        log_density = model(img_tensor, centerbias_tensor)
        saliency = log_density.squeeze().cpu().numpy()

    # Convert log-density to probability
    saliency = np.exp(saliency - logsumexp(saliency))
    if saliency.shape != (h, w):
        saliency = zoom(saliency, (h / saliency.shape[0], w / saliency.shape[1]))

    return saliency


def _heuristic_saliency(img_bgr) -> "np.ndarray":
    """Simple heuristic saliency based on contrast, color saturation, and edges."""
    np = _import_numpy()
    cv2 = _import_cv2()

    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    h, w = gray.shape

    # 1. Contrast map (local standard deviation)
    blur = cv2.GaussianBlur(gray, (21, 21), 0)
    contrast = np.abs(gray - blur)

    # 2. Color saturation
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    saturation = hsv[:, :, 1].astype(np.float32)

    # 3. Edge map
    edges = cv2.Canny(img_bgr, 50, 150).astype(np.float32)
    edges = cv2.GaussianBlur(edges, (15, 15), 0)

    # 4. Center bias (slight preference for center)
    cy, cx = h / 2, w / 2
    Y, X = np.ogrid[:h, :w]
    center_dist = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
    max_dist = np.sqrt(cx**2 + cy**2)
    center_bias = 1.0 - (center_dist / max_dist) * 0.3

    # Normalize all components to 0-1 before combining
    def _norm(arr):
        mn, mx = arr.min(), arr.max()
        return (arr - mn) / (mx - mn) if mx > mn else np.zeros_like(arr)

    # Combine (all in 0-1 range now)
    saliency = (
        _norm(contrast) * 0.3
        + _norm(saturation) * 0.3
        + _norm(edges) * 0.2
        + center_bias * _norm(gray) * 0.2
    )

    return saliency


# ---------------------------------------------------------------------------
# 2e. ADVANCED VISUAL METRICS (Focus / Clarity / Cognitive Load)
# ---------------------------------------------------------------------------


def _compute_focus_metrics(saliency_norm, regions) -> "FocusMetrics":
    """Compute advanced focus metrics from a normalised saliency map (0-255 uint8).

    Uses entropy, Gini coefficient, and cluster count — all numpy-only.
    """
    from fediaf_verifier.models.artwork_inspection import FocusMetrics

    np = _import_numpy()

    flat = saliency_norm.astype(np.float64).ravel()
    total = flat.sum()

    # --- Entropy on 256-bin histogram (resolution-independent) ---
    hist = np.bincount(saliency_norm.ravel(), minlength=256).astype(np.float64)
    hist = hist[hist > 0]
    hist_prob = hist / hist.sum() if hist.sum() > 0 else hist
    if len(hist_prob) > 0:
        entropy_raw = -float(np.sum(hist_prob * np.log2(hist_prob)))
    else:
        entropy_raw = 0.0

    # Max possible entropy = log2(256) = 8.0 (constant, independent of resolution)
    max_entropy = 8.0
    # Normalise: 0 = all attention in 1 bin (perfect focus), 100 = uniform
    entropy_norm = min(100.0, (entropy_raw / max_entropy) * 100)
    # Invert so high = focused
    entropy_score = 100.0 - entropy_norm

    # --- Gini coefficient ---
    sorted_flat = np.sort(flat)
    n = len(sorted_flat)
    if n > 0 and total > 0:
        index = np.arange(1, n + 1)
        gini = float((2 * np.sum(index * sorted_flat) / (n * total)) - (n + 1) / n)
        gini = max(0.0, min(1.0, gini))
    else:
        gini = 0.0

    # --- Cluster count (from already-detected regions) ---
    cluster_count = len(regions)

    return FocusMetrics(
        entropy=round(entropy_score, 1),
        gini=round(gini, 3),
        cluster_count=cluster_count,
    )


def _compute_composite_focus(metrics: "FocusMetrics") -> float:
    """Compute composite focus score 0-100 from sub-metrics."""
    # Weights: entropy 0.4, gini 0.3, cluster penalty 0.3
    entropy_component = metrics.entropy * 0.4
    gini_component = (metrics.gini * 100) * 0.3

    # Cluster count: 1-2 = excellent, 3-4 = good, 5+ = unfocused
    if metrics.cluster_count <= 2:
        cluster_score = 100.0
    elif metrics.cluster_count <= 4:
        cluster_score = 70.0
    elif metrics.cluster_count <= 6:
        cluster_score = 40.0
    else:
        cluster_score = 15.0
    cluster_component = cluster_score * 0.3

    return min(100.0, max(0.0, entropy_component + gini_component + cluster_component))


def _compute_clarity(img_bgr) -> "ClarityMetrics":
    """Compute visual clarity metrics from a BGR image (OpenCV + numpy only).

    High score = clean, low clutter. Low score = visually chaotic.
    """
    from fediaf_verifier.models.artwork_inspection import ClarityMetrics

    np = _import_numpy()
    cv2 = _import_cv2()

    h, w = img_bgr.shape[:2]
    total_pixels = h * w

    # --- 1. Edge density (Canny) ---
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    edge_density = float(np.count_nonzero(edges)) / total_pixels

    # --- 2. Color complexity (K-means, count clusters with >5% area) ---
    pixels = img_bgr.reshape(-1, 3).astype(np.float32)
    # Subsample for speed (max 50k pixels)
    if len(pixels) > 50000:
        indices = np.random.default_rng(42).choice(len(pixels), 50000, replace=False)
        pixels_sample = pixels[indices]
    else:
        pixels_sample = pixels

    k = min(8, len(pixels_sample))
    if k < 2:
        # Degenerate image — everything is one color
        return ClarityMetrics(
            score=100.0, edge_density=0.0, color_complexity=1,
            whitespace_ratio=1.0, symmetry=1.0,
        )
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 5.0)
    _, labels, _ = cv2.kmeans(pixels_sample, k, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
    label_counts = np.bincount(labels.ravel(), minlength=k)
    # Count clusters that cover >5% of sampled pixels
    threshold = 0.05 * len(pixels_sample)
    color_complexity = int(np.sum(label_counts > threshold))

    # --- 3. Whitespace ratio (low-saturation, high-value pixels) ---
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    s = hsv[:, :, 1].astype(np.float32)
    v = hsv[:, :, 2].astype(np.float32)
    # "Background-like": saturation < 30 and value > 180 (light, desaturated)
    whitespace_mask = (s < 30) & (v > 180)
    whitespace_ratio = float(np.count_nonzero(whitespace_mask)) / total_pixels

    # --- 4. Symmetry (left-right correlation) ---
    if w < 4:
        # Too narrow for meaningful symmetry analysis
        symmetry = 1.0
    else:
        left_half = gray[:, : w // 2]
        right_half = cv2.flip(gray[:, w - w // 2 :], 1)
        # Ensure same shape
        min_w = min(left_half.shape[1], right_half.shape[1])
        left_half = left_half[:, :min_w].astype(np.float64)
        right_half = right_half[:, :min_w].astype(np.float64)
        # Pearson correlation
        left_flat = left_half.ravel()
        right_flat = right_half.ravel()
        left_std = float(np.std(left_flat))
        right_std = float(np.std(right_flat))
        if left_std > 0 and right_std > 0:
            corr = float(np.corrcoef(left_flat, right_flat)[0, 1])
            symmetry = max(0.0, corr)
        else:
            symmetry = 1.0 if left_std == 0 and right_std == 0 else 0.0

    # --- Composite clarity score ---
    # Lower edge_density = cleaner (invert)
    edge_score = max(0.0, 1.0 - edge_density * 10)  # ~0.10 density → 0 score
    # Fewer dominant colors = cleaner
    color_score = max(0.0, min(1.0, 1.0 - (color_complexity - 2) / 6))  # 2 colors → 1.0, 8 → 0.0
    # More whitespace = cleaner
    ws_score = min(1.0, whitespace_ratio * 3)  # 33%+ whitespace → max
    # Higher symmetry = cleaner
    sym_score = symmetry

    composite = (
        edge_score * 0.30
        + color_score * 0.25
        + ws_score * 0.25
        + sym_score * 0.20
    ) * 100

    return ClarityMetrics(
        score=round(min(100.0, max(0.0, composite)), 1),
        edge_density=round(edge_density, 4),
        color_complexity=color_complexity,
        whitespace_ratio=round(whitespace_ratio, 3),
        symmetry=round(symmetry, 3),
    )


def _compute_cognitive_load(img_bgr) -> "CognitiveLoadMetrics":
    """Estimate cognitive load from a BGR image (numpy FFT + OpenCV, no scipy).

    High score = overwhelming, hard to process.
    ease_score = 100 - score (high = easy to process).
    """
    from fediaf_verifier.models.artwork_inspection import CognitiveLoadMetrics

    np = _import_numpy()
    cv2 = _import_cv2()

    h, w = img_bgr.shape[:2]
    total_pixels = h * w
    gray_u8 = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # --- 1. Frequency complexity (high-freq energy ratio via numpy FFT) ---
    # Downsample to max 1024px to bound memory (~16MB vs ~1.5GB at 10kx10k)
    max_fft_dim = 1024
    if max(h, w) > max_fft_dim:
        scale = max_fft_dim / max(h, w)
        fft_gray = cv2.resize(gray_u8, None, fx=scale, fy=scale).astype(np.float64)
    else:
        fft_gray = gray_u8.astype(np.float64)
    fh, fw = fft_gray.shape[:2]

    f_transform = np.fft.fft2(fft_gray)
    f_shift = np.fft.fftshift(f_transform)
    magnitude = np.abs(f_shift)
    total_energy = float(np.sum(magnitude ** 2))

    # Mask out low-frequency center (inner 25% radius)
    cy, cx = fh // 2, fw // 2
    radius = int(min(fh, fw) * 0.25)
    Y, X = np.ogrid[:fh, :fw]
    low_freq_mask = ((X - cx) ** 2 + (Y - cy) ** 2) <= radius ** 2
    high_freq_energy = float(np.sum(magnitude[~low_freq_mask] ** 2))
    freq_complexity = high_freq_energy / total_energy if total_energy > 0 else 0.0

    # --- 2. Element count (contours on binarised image) ---
    _, binary = cv2.threshold(gray_u8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # Filter tiny contours (noise), count only > 0.1% of image area
    min_area = total_pixels * 0.001
    element_count = sum(1 for c in contours if cv2.contourArea(c) > min_area)

    # --- 3. Edge density (reuse Canny) ---
    edges = cv2.Canny(gray_u8, 50, 150)
    edge_density = float(np.count_nonzero(edges)) / total_pixels

    # --- 4. Color diversity (histogram spread in HSV Hue channel) ---
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    hue = hsv[:, :, 0].ravel()  # 0-179 in OpenCV
    sat = hsv[:, :, 1].ravel()
    # Only count pixels with meaningful saturation (>30)
    chromatic_hue = hue[sat > 30]
    if len(chromatic_hue) > 0:
        hist, _ = np.histogram(chromatic_hue, bins=18, range=(0, 180))
        hist_norm = hist / hist.sum()
        # Number of hue bins with >3% of chromatic pixels
        active_bins = int(np.sum(hist_norm > 0.03))
        color_diversity = active_bins / 18.0
    else:
        color_diversity = 0.0

    # --- Composite cognitive load (0 = easy, 100 = overwhelming) ---
    freq_score = min(1.0, freq_complexity * 2)  # typical ~0.3-0.7
    element_score = min(1.0, element_count / 30)  # 30+ elements = max load
    edge_score = min(1.0, edge_density * 10)  # ~0.10 = max
    color_div_score = color_diversity  # already 0-1

    composite = (
        freq_score * 0.30
        + element_score * 0.25
        + edge_score * 0.25
        + color_div_score * 0.20
    ) * 100

    score = round(min(100.0, max(0.0, composite)), 1)

    return CognitiveLoadMetrics(
        score=score,
        ease_score=round(100.0 - score, 1),
        frequency_complexity=round(freq_complexity, 4),
        element_count=element_count,
        color_diversity=round(color_diversity, 3),
        edge_density=round(edge_density, 4),
    )


# ---------------------------------------------------------------------------
# 3. PRINT READINESS
# ---------------------------------------------------------------------------


def analyze_print_readiness(
    img_b64: str,
    media_type: str = "image/png",
    min_dpi: float = 300.0,
) -> "PrintReadinessReport":
    """Analyze whether a file is ready for professional printing.

    Checks: DPI, color space, transparency, bleed marks (PDF), font embedding (PDF).

    Args:
        img_b64: Base64-encoded file (image or PDF page).
        media_type: MIME type of the file.
        min_dpi: Minimum acceptable DPI for print.

    Returns:
        PrintReadinessReport with issues and score.
    """
    from fediaf_verifier.models.artwork_inspection import PrintIssue, PrintReadinessReport

    raw_bytes = base64.b64decode(img_b64)

    issues: list[PrintIssue] = []
    score = 100

    # PDF files cannot be opened by Pillow — render first page via PyMuPDF
    is_pdf = media_type == "application/pdf" or raw_bytes[:5] == b"%PDF-"
    pil_img: Image.Image | None = None

    if is_pdf:
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(stream=raw_bytes, filetype="pdf")
            page = doc[0]
            pix = page.get_pixmap(dpi=150)
            pil_img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            doc.close()
        except ImportError:
            logger.warning("PyMuPDF niedostepny — pomijam renderowanie PDF")
        except Exception as e:
            logger.warning("Blad renderowania PDF: {}", e)
    else:
        try:
            pil_img = Image.open(io.BytesIO(raw_bytes))
        except Exception as e:
            logger.warning("Nie mozna otworzyc obrazu: {}", e)

    if pil_img is None:
        # Cannot analyze — return minimal report
        return PrintReadinessReport(
            file_format="PDF" if is_pdf else "unknown",
            issues=[PrintIssue(
                category="other",
                severity="warning",
                description="Nie udalo sie otworzyc pliku do analizy",
                recommendation="Sprawdz format pliku i zainstaluj PyMuPDF dla PDF",
            )],
            score=50,
        )

    # --- File format ---
    fmt = "PDF" if is_pdf else (pil_img.format or "unknown").upper()

    # --- DPI ---
    dpi_info = pil_img.info.get("dpi", (0, 0))
    dpi = 0.0
    if isinstance(dpi_info, (tuple, list)) and len(dpi_info) >= 2:
        dpi = float(max(dpi_info[0], dpi_info[1]))
    # JFIF density
    if dpi == 0:
        jfif_density = pil_img.info.get("jfif_density", (0, 0))
        if isinstance(jfif_density, (tuple, list)):
            jfif_unit = pil_img.info.get("jfif_unit", 0)
            d = float(max(jfif_density[0], jfif_density[1]))
            if jfif_unit == 1:  # DPI
                dpi = d
            elif jfif_unit == 2:  # dots per cm
                dpi = d * 2.54

    dpi_sufficient = dpi >= min_dpi
    if dpi > 0 and not dpi_sufficient:
        severity = "critical" if dpi < 150 else "warning"
        issues.append(PrintIssue(
            category="resolution",
            severity=severity,
            description=f"Rozdzielczosc {dpi:.0f} DPI jest ponizej wymaganego minimum",
            recommendation=f"Wymagane minimum {min_dpi:.0f} DPI dla druku offsetowego",
            value_found=f"{dpi:.0f} DPI",
            value_expected=f"≥{min_dpi:.0f} DPI",
        ))
        score -= 30 if severity == "critical" else 15
    elif dpi == 0:
        issues.append(PrintIssue(
            category="resolution",
            severity="warning",
            description="Brak informacji o DPI w metadanych pliku",
            recommendation="Sprawdz rozdzielczosc zrodlowa — dla druku wymagane min 300 DPI",
            value_found="brak danych",
            value_expected=f"≥{min_dpi:.0f} DPI",
        ))
        score -= 10

    # --- Color space ---
    color_space = "RGB"
    is_print_ready_cs = False
    pil_mode = pil_img.mode
    if pil_mode == "CMYK":
        color_space = "CMYK"
        is_print_ready_cs = True
    elif pil_mode in ("L", "1"):
        color_space = "Grayscale"
        is_print_ready_cs = True
    elif pil_mode in ("RGB", "RGBA", "P"):
        color_space = "RGB"
        is_print_ready_cs = False
        issues.append(PrintIssue(
            category="color_space",
            severity="warning",
            description="Plik w przestrzeni RGB — druk wymaga CMYK",
            recommendation="Przekonwertuj do CMYK przed drukiem (uwzglednij profile ICC)",
            value_found=color_space,
            value_expected="CMYK",
        ))
        score -= 15

    # --- Transparency ---
    has_transparency = pil_img.mode in ("RGBA", "LA", "PA") or "transparency" in pil_img.info
    if has_transparency:
        issues.append(PrintIssue(
            category="other",
            severity="warning",
            description="Plik zawiera kanal alfa / przezroczystosc",
            recommendation="Splaszcz przezroczystosc na biale tlo przed drukiem",
            value_found="przezroczystosc wykryta",
            value_expected="brak przezroczystosci",
        ))
        score -= 10

    # --- Page size ---
    w_px, h_px = pil_img.size
    page_size_mm: list[float] = []
    if dpi > 0:
        w_mm = w_px / dpi * 25.4
        h_mm = h_px / dpi * 25.4
        page_size_mm = [round(w_mm, 1), round(h_mm, 1)]

    # --- PDF-specific checks ---
    fonts_embedded: bool | None = None
    has_bleed = False
    if is_pdf:
        fonts_embedded, has_bleed, pdf_issues = _analyze_pdf_details(raw_bytes, min_dpi)
        issues.extend(pdf_issues)
        if fonts_embedded is False:
            score -= 20
        if not has_bleed:
            score -= 5

    # Clamp score
    score = max(0, min(100, score))

    # Overall verdict
    has_critical = any(i.severity == "critical" for i in issues)
    print_ready = not has_critical and score >= 70

    return PrintReadinessReport(
        dpi=round(dpi, 1),
        dpi_sufficient=dpi_sufficient,
        color_space=color_space,
        color_space_print_ready=is_print_ready_cs,
        has_transparency=has_transparency,
        has_bleed=has_bleed,
        fonts_embedded=fonts_embedded,
        page_size_mm=page_size_mm,
        file_format=fmt,
        issues=issues,
        print_ready=print_ready,
        score=score,
    )


def _analyze_pdf_details(
    pdf_bytes: bytes,
    min_dpi: float,
) -> tuple[bool | None, bool, list]:
    """Extract PDF-specific print readiness info using PyMuPDF (if available)."""
    from fediaf_verifier.models.artwork_inspection import PrintIssue

    issues: list[PrintIssue] = []
    fonts_embedded: bool | None = None
    has_bleed = False

    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.warning("PyMuPDF niedostepny — pomijam szczegolowa analize PDF")
        return None, False, []

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page = doc[0]

        # Bleed box vs trim box
        bleed_rect = page.bleedbox
        trim_rect = page.trimbox
        media_rect = page.mediabox
        if bleed_rect and trim_rect and bleed_rect != trim_rect:
            has_bleed = True
        elif bleed_rect and media_rect and bleed_rect != media_rect:
            has_bleed = True

        if not has_bleed:
            issues.append(PrintIssue(
                category="bleed",
                severity="info",
                description="Nie wykryto obszaru spadow (bleed) w PDF",
                recommendation="Dodaj min 3mm spadu (bleed) dla bezpiecznego ciecia",
                value_found="brak bleed box",
                value_expected="bleed box > trim box o min 3mm",
            ))

        # Font embedding check
        fonts_on_page = page.get_fonts(full=True)
        all_embedded = True
        for font_info in fonts_on_page:
            # font_info: (xref, ext, type, basefont, name, encoding, ...)
            if len(font_info) > 2:
                font_type = font_info[2]
                # Type3, Type1 without file → not embedded
                if font_type and "Type3" in str(font_type):
                    continue
                # Check if font file is referenced
                xref = font_info[0]
                if xref == 0:
                    all_embedded = False

        fonts_embedded = all_embedded
        if not all_embedded:
            issues.append(PrintIssue(
                category="font",
                severity="critical",
                description="Nie wszystkie fonty sa osadzone w PDF",
                recommendation="Osadz wszystkie fonty (embed fonts) przed eksportem do druku",
                value_found="fonty nieosadzone",
                value_expected="wszystkie fonty osadzone",
            ))

        # Image resolution in PDF
        image_list = page.get_images(full=True)
        for img_info in image_list:
            xref = img_info[0]
            try:
                pix = fitz.Pixmap(doc, xref)
                img_w, img_h = pix.width, pix.height
                # Approximate DPI: image pixels / page inches
                page_w_in = page.rect.width / 72
                page_h_in = page.rect.height / 72
                if page_w_in > 0 and page_h_in > 0:
                    est_dpi_x = img_w / page_w_in
                    est_dpi_y = img_h / page_h_in
                    est_dpi = min(est_dpi_x, est_dpi_y)
                    if est_dpi < min_dpi:
                        issues.append(PrintIssue(
                            category="resolution",
                            severity="warning",
                            description=f"Obraz osadzony w PDF ma ~{est_dpi:.0f} DPI",
                            recommendation=f"Zamien na obraz min {min_dpi:.0f} DPI",
                            value_found=f"~{est_dpi:.0f} DPI",
                            value_expected=f"≥{min_dpi:.0f} DPI",
                        ))
                pix = None  # free
            except Exception:
                pass

        doc.close()
    except Exception as e:
        logger.warning("Blad analizy PDF: {}", e)

    return fonts_embedded, has_bleed, issues


# ---------------------------------------------------------------------------
# 4. COMBINED INSPECTION PIPELINE
# ---------------------------------------------------------------------------


def run_artwork_inspection(
    img_a_b64: str,
    media_type_a: str,
    img_b_b64: str | None = None,
    media_type_b: str | None = None,
    pixel_diff_threshold: int = 30,
    n_colors: int = 6,
    min_dpi: float = 300.0,
    enable_ocr: bool = True,
    enable_saliency: bool = True,
    ocr_languages: list[str] | None = None,
) -> "ArtworkInspectionReport":
    """Run full artwork inspection pipeline (deterministic, no AI).

    Args:
        img_a_b64: Base64-encoded master/reference image.
        media_type_a: MIME type of image A.
        img_b_b64: Optional base64-encoded proof/new version.
        media_type_b: MIME type of image B.
        pixel_diff_threshold: Sensitivity for pixel change detection.
        n_colors: Number of dominant colors to extract.
        min_dpi: Minimum DPI for print readiness.
        enable_ocr: Enable OCR text comparison (requires easyocr).
        enable_saliency: Enable saliency heatmap (requires opencv).
        ocr_languages: Language codes for OCR (default: ['en', 'pl', 'de', 'fr']).

    Returns:
        ArtworkInspectionReport with all sub-reports populated.
    """
    from fediaf_verifier.models.artwork_inspection import ArtworkInspectionReport

    pixel_diff = None
    color_a = None
    color_b = None
    print_a = None
    print_b = None
    ocr_report = None
    icc_a = None
    icc_b = None
    saliency_report = None
    overall_score = 100

    # -- Color analysis (always for image A) --
    try:
        color_a = extract_dominant_colors(img_a_b64, n_colors=n_colors)
        logger.info("Ekstrakcja kolorow A: {} dominujacych", len(color_a.dominant_colors))
    except Exception as e:
        logger.error("Blad ekstrakcji kolorow A: {}", e)

    # -- Print readiness (always for image A) --
    try:
        print_a = analyze_print_readiness(img_a_b64, media_type_a, min_dpi)
        logger.info("Print readiness A: score={}, ready={}", print_a.score, print_a.print_ready)
        overall_score = min(overall_score, print_a.score)
    except Exception as e:
        logger.error("Blad analizy print readiness A: {}", e)

    # -- ICC profile (always for image A) --
    try:
        icc_a = extract_icc_profile(img_a_b64, media_type_a)
        logger.info("ICC A: has_profile={}, space={}", icc_a.has_profile, icc_a.color_space)
    except Exception as e:
        logger.error("Blad ekstrakcji ICC A: {}", e)

    # -- Saliency (single image, always for A if enabled) --
    if enable_saliency and not img_b_b64:
        try:
            saliency_report = compute_saliency(img_a_b64)
            logger.info("Saliency: model={}, regions={}", saliency_report.model_used, len(saliency_report.attention_regions))
        except Exception as e:
            logger.warning("Saliency analysis failed: {}", e)

    # -- If second image provided: pixel diff + OCR + color B + print B + ICC B --
    if img_b_b64:
        try:
            pixel_diff = compute_pixel_diff(
                img_a_b64, img_b_b64, threshold=pixel_diff_threshold
            )
            logger.info(
                "Pixel diff: SSIM={}, changed={}%, verdict={}",
                pixel_diff.ssim_score,
                pixel_diff.changed_pixels_pct,
                pixel_diff.verdict,
            )
            ssim_score_pct = int(pixel_diff.ssim_score * 100)
            overall_score = min(overall_score, ssim_score_pct)
        except Exception as e:
            logger.error("Blad pixel diff: {}", e)

        # -- OCR text comparison --
        if enable_ocr:
            try:
                ocr_report = compare_ocr_texts(
                    img_a_b64, img_b_b64, languages=ocr_languages
                )
                logger.info(
                    "OCR comparison: similarity={}%, changes={}",
                    ocr_report.similarity_pct,
                    ocr_report.total_changes,
                )
                # Factor text similarity into score
                text_score = int(ocr_report.similarity_pct)
                overall_score = min(overall_score, text_score)
            except ImportError:
                logger.info("EasyOCR niedostepny — pomijam porownanie tekstu")
            except Exception as e:
                logger.error("Blad porownania OCR: {}", e)

        try:
            color_b = extract_dominant_colors(img_b_b64, n_colors=n_colors)
            if color_a and color_b:
                compare_colors(color_a, color_b)
                logger.info(
                    "Color comparison: max_dE={}, consistency={}",
                    color_a.max_delta_e,
                    color_a.color_consistency_score,
                )
                overall_score = min(overall_score, int(color_a.color_consistency_score))
        except Exception as e:
            logger.error("Blad porownania kolorow: {}", e)

        try:
            print_b = analyze_print_readiness(
                img_b_b64, media_type_b or media_type_a, min_dpi
            )
        except Exception as e:
            logger.error("Blad analizy print readiness B: {}", e)

        try:
            icc_b = extract_icc_profile(img_b_b64, media_type_b or media_type_a)
        except Exception as e:
            logger.error("Blad ekstrakcji ICC B: {}", e)

    # Verdict
    overall_score = max(0, min(100, overall_score))
    if overall_score >= 85:
        verdict = "pass"
    elif overall_score >= 60:
        verdict = "review"
    else:
        verdict = "fail"

    return ArtworkInspectionReport(
        pixel_diff=pixel_diff,
        color_analysis=color_a,
        color_analysis_b=color_b,
        print_readiness=print_a,
        print_readiness_b=print_b,
        ocr_comparison=ocr_report,
        icc_profile=icc_a,
        icc_profile_b=icc_b,
        saliency=saliency_report,
        overall_score=overall_score,
        overall_verdict=verdict,
    )
