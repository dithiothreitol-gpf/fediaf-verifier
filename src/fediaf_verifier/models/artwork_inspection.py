"""Artwork inspection models: pixel diff, color analysis, print readiness."""

from __future__ import annotations

from pydantic import Field

from .base import NullSafeBase


# ---------------------------------------------------------------------------
# Pixel-level diff
# ---------------------------------------------------------------------------


class PixelDiffRegion(NullSafeBase):
    """A region on the label where pixel differences were detected."""

    x: int = Field(default=0, description="Top-left X (px)")
    y: int = Field(default=0, description="Top-left Y (px)")
    w: int = Field(default=0, description="Width (px)")
    h: int = Field(default=0, description="Height (px)")
    change_pct: float = Field(
        default=0.0,
        description="Percentage of changed pixels within this region",
    )
    description: str = Field(default="", description="AI-generated description of what changed")


class PixelDiffReport(NullSafeBase):
    """Deterministic pixel-level comparison of two label images."""

    ssim_score: float = Field(
        default=0.0,
        description="Structural Similarity Index (0.0–1.0, 1.0 = identical)",
    )
    changed_pixels_pct: float = Field(
        default=0.0,
        description="Overall percentage of pixels that differ (0.0–100.0)",
    )
    total_pixels: int = Field(default=0, description="Total pixel count in comparison area")
    changed_pixels: int = Field(default=0, description="Number of changed pixels")
    diff_regions: list[PixelDiffRegion] = Field(
        default_factory=list,
        description="Detected change regions (bounding boxes)",
    )
    diff_image_b64: str = Field(
        default="",
        description="Base64-encoded diff overlay image (PNG)",
    )
    threshold_used: int = Field(
        default=30,
        description="Pixel intensity threshold used for change detection (0–255)",
    )
    verdict: str = Field(
        default="identical",
        description="'identical', 'minor_changes', 'significant_changes', 'major_changes'",
    )


# ---------------------------------------------------------------------------
# Color analysis
# ---------------------------------------------------------------------------


class DominantColor(NullSafeBase):
    """A dominant color extracted from the label."""

    hex: str = Field(default="#000000", description="Hex color code")
    r: int = Field(default=0, description="Red channel 0–255")
    g: int = Field(default=0, description="Green channel 0–255")
    b: int = Field(default=0, description="Blue channel 0–255")
    percentage: float = Field(
        default=0.0,
        description="Percentage of label area covered by this color cluster",
    )
    name: str = Field(default="", description="Approximate color name")


class ColorComparison(NullSafeBase):
    """Delta E comparison between two corresponding colors."""

    color_a_hex: str = Field(default="#000000", description="Color from image A")
    color_b_hex: str = Field(default="#000000", description="Color from image B")
    delta_e: float = Field(
        default=0.0,
        description="CIE2000 Delta E (0 = identical, <1 imperceptible, 1–2 close, >5 noticeable)",
    )
    verdict: str = Field(
        default="match",
        description="'match' (<2), 'close' (2–5), 'mismatch' (>5)",
    )


class ColorAnalysisReport(NullSafeBase):
    """Color palette extraction and optional cross-version comparison."""

    dominant_colors: list[DominantColor] = Field(
        default_factory=list,
        description="Top dominant colors (sorted by area %)",
    )
    color_space_detected: str = Field(
        default="RGB",
        description="Detected color space: 'RGB', 'CMYK', 'LAB', 'unknown'",
    )
    is_cmyk: bool = Field(
        default=False,
        description="True if source file uses CMYK color space",
    )
    # Cross-version comparison (populated only when two images are provided)
    comparisons: list[ColorComparison] = Field(
        default_factory=list,
        description="Delta E comparisons between two versions (empty if single image)",
    )
    max_delta_e: float = Field(
        default=0.0,
        description="Maximum Delta E found across all comparisons",
    )
    color_consistency_score: float = Field(
        default=100.0,
        description="0–100 score: 100 = perfect color match between versions",
    )


# ---------------------------------------------------------------------------
# Print readiness
# ---------------------------------------------------------------------------


class PrintIssue(NullSafeBase):
    """A specific print-readiness problem found."""

    category: str = Field(
        default="",
        description="'resolution', 'color_space', 'bleed', 'font', 'overprint', 'other'",
    )
    severity: str = Field(
        default="warning",
        description="'critical', 'warning', 'info'",
    )
    description: str = ""
    recommendation: str = ""
    value_found: str = Field(default="", description="What was detected (e.g. '150 DPI')")
    value_expected: str = Field(default="", description="What is required (e.g. '≥300 DPI')")


class PrintReadinessReport(NullSafeBase):
    """Analysis of whether the file is ready for professional printing."""

    dpi: float = Field(default=0.0, description="Effective DPI/PPI of the image")
    dpi_sufficient: bool = Field(default=False, description="True if DPI ≥ 300")
    color_space: str = Field(
        default="unknown",
        description="'CMYK', 'RGB', 'Grayscale', 'LAB', 'unknown'",
    )
    color_space_print_ready: bool = Field(
        default=False,
        description="True if CMYK or Grayscale",
    )
    has_transparency: bool = Field(
        default=False,
        description="True if alpha channel or transparency detected",
    )
    has_bleed: bool = Field(
        default=False,
        description="True if bleed marks or extra bleed area detected (PDF only)",
    )
    fonts_embedded: bool | None = Field(
        default=None,
        description="True if all fonts are embedded (PDF only, None for images)",
    )
    page_size_mm: list[float] = Field(
        default_factory=list,
        description="[width_mm, height_mm] of the document",
    )
    file_format: str = Field(default="", description="'PDF', 'PNG', 'JPG', 'TIFF', etc.")
    issues: list[PrintIssue] = Field(default_factory=list)
    print_ready: bool = Field(
        default=False,
        description="Overall verdict: True if no critical issues",
    )
    score: int = Field(default=0, description="Print readiness score 0–100")


# ---------------------------------------------------------------------------
# OCR text comparison
# ---------------------------------------------------------------------------


class OCRTextBlock(NullSafeBase):
    """A block of text extracted via OCR with position info."""

    text: str = ""
    confidence: float = Field(default=0.0, description="OCR confidence 0.0–1.0")
    bbox: list[int] = Field(
        default_factory=list, description="Bounding box [x1, y1, x2, y2] in pixels"
    )


class TextDiffChange(NullSafeBase):
    """A single text difference between two label versions."""

    change_type: str = Field(
        default="modified", description="'added', 'removed', 'modified'"
    )
    old_text: str = ""
    new_text: str = ""
    line_number: int = Field(default=0, description="Approximate line in text output")
    severity: str = Field(
        default="info",
        description="'critical' (regulatory text changed), 'warning', 'info'",
    )


class OCRComparisonReport(NullSafeBase):
    """OCR-based text comparison between two label versions."""

    text_a: str = Field(default="", description="Full extracted text from image A")
    text_b: str = Field(default="", description="Full extracted text from image B")
    blocks_a: list[OCRTextBlock] = Field(default_factory=list)
    blocks_b: list[OCRTextBlock] = Field(default_factory=list)
    changes: list[TextDiffChange] = Field(default_factory=list)
    similarity_pct: float = Field(
        default=100.0, description="Text similarity percentage (0–100)"
    )
    total_changes: int = Field(default=0, description="Number of text differences found")
    avg_confidence_a: float = Field(default=0.0, description="Mean OCR confidence for image A")
    avg_confidence_b: float = Field(default=0.0, description="Mean OCR confidence for image B")


# ---------------------------------------------------------------------------
# ICC color profile
# ---------------------------------------------------------------------------


class ICCProfileInfo(NullSafeBase):
    """ICC color profile information extracted from a file."""

    has_profile: bool = Field(default=False, description="Whether an ICC profile was found")
    profile_name: str = Field(default="", description="ICC profile description/name")
    color_space: str = Field(default="", description="Profile color space: 'CMYK', 'RGB', etc.")
    rendering_intent: str = Field(
        default="",
        description="'perceptual', 'relative_colorimetric', 'saturation', 'absolute_colorimetric'",
    )
    pcs: str = Field(default="", description="Profile Connection Space: 'XYZ' or 'Lab'")
    version: str = Field(default="", description="ICC profile version")
    issues: list[str] = Field(
        default_factory=list, description="Problems found with the ICC profile"
    )


# ---------------------------------------------------------------------------
# Saliency / visual attention
# ---------------------------------------------------------------------------


class AttentionRegion(NullSafeBase):
    """A region of predicted visual attention."""

    rank: int = Field(default=0, description="Attention rank (1 = most attention)")
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0
    attention_pct: float = Field(
        default=0.0, description="Percentage of total attention in this region"
    )
    description: str = Field(default="", description="AI description of what's in this region")


class FocusMetrics(NullSafeBase):
    """Detailed focus score breakdown."""

    entropy: float = Field(
        default=0.0,
        description="Saliency map entropy (lower = more focused). Normalised to 0–100.",
    )
    gini: float = Field(
        default=0.0,
        description="Gini coefficient of attention distribution (0–1, higher = more concentrated)",
    )
    cluster_count: int = Field(
        default=0,
        description="Number of distinct attention clusters (fewer = more focused)",
    )


class ClarityMetrics(NullSafeBase):
    """Visual clarity / clutter analysis (heuristic, 0–100 where 100 = very clear)."""

    score: float = Field(default=0.0, description="Composite clarity score 0–100")
    edge_density: float = Field(
        default=0.0, description="Edge pixel ratio 0–1 (lower = cleaner)"
    )
    color_complexity: int = Field(
        default=0, description="Number of dominant color clusters (>5% area each)"
    )
    whitespace_ratio: float = Field(
        default=0.0, description="Fraction of low-saturation / background pixels 0–1"
    )
    symmetry: float = Field(
        default=0.0, description="Left-right correlation 0–1 (higher = more symmetric)"
    )


class CognitiveLoadMetrics(NullSafeBase):
    """Cognitive load estimate (heuristic, 0–100 where 0 = easy, 100 = overwhelming)."""

    score: float = Field(default=0.0, description="Composite cognitive load 0–100")
    ease_score: float = Field(
        default=0.0,
        description="Inverted: 0–100 where 100 = very easy to process",
    )
    frequency_complexity: float = Field(
        default=0.0,
        description="High-frequency energy ratio 0–1 (complex textures/detail)",
    )
    element_count: int = Field(
        default=0, description="Estimated number of distinct visual elements"
    )
    color_diversity: float = Field(
        default=0.0, description="Normalised color histogram spread 0–1"
    )
    edge_density: float = Field(
        default=0.0, description="Edge pixel ratio 0–1 (shared with clarity)"
    )


class SaliencyReport(NullSafeBase):
    """Visual attention / saliency analysis report."""

    heatmap_b64: str = Field(
        default="", description="Base64-encoded heatmap overlay image (PNG)"
    )
    attention_regions: list[AttentionRegion] = Field(
        default_factory=list,
        description="Top attention regions sorted by predicted attention",
    )
    focus_score: float = Field(
        default=0.0,
        description="0–100: how focused attention is (high = few dominant areas)",
    )
    focus_metrics: FocusMetrics | None = Field(
        default=None, description="Detailed focus score breakdown"
    )
    clarity: ClarityMetrics | None = Field(
        default=None, description="Visual clarity / clutter analysis"
    )
    cognitive_load: CognitiveLoadMetrics | None = Field(
        default=None, description="Cognitive load estimate"
    )
    brand_attention_pct: float = Field(
        default=0.0,
        description="Estimated % of attention on brand/logo area",
    )
    regulatory_attention_pct: float = Field(
        default=0.0,
        description="Estimated % of attention on regulatory text area",
    )
    model_used: str = Field(default="", description="Which saliency model was used")


class SaliencyResult(NullSafeBase):
    """Pipeline result for saliency analysis."""

    performed: bool = False
    report: SaliencyReport | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Combined artwork inspection result
# ---------------------------------------------------------------------------


class ArtworkInspectionReport(NullSafeBase):
    """Combined artwork QA report: pixel diff + color + print + OCR + ICC + saliency."""

    # Sub-reports (each may be None if that analysis was not requested)
    pixel_diff: PixelDiffReport | None = None
    color_analysis: ColorAnalysisReport | None = None
    color_analysis_b: ColorAnalysisReport | None = None  # second image (if provided)
    print_readiness: PrintReadinessReport | None = None
    print_readiness_b: PrintReadinessReport | None = None  # second image (if provided)
    ocr_comparison: OCRComparisonReport | None = None
    icc_profile: ICCProfileInfo | None = None
    icc_profile_b: ICCProfileInfo | None = None  # second image (if provided)
    saliency: SaliencyReport | None = None

    # AI interpretation (optional — Claude summarises the deterministic findings)
    ai_summary: str = Field(
        default="",
        description="AI-generated summary of all findings in Polish",
    )
    ai_recommendations: list[str] = Field(
        default_factory=list,
        description="AI-generated actionable recommendations",
    )

    # Overall
    overall_score: int = Field(default=0, description="Combined QA score 0–100")
    overall_verdict: str = Field(
        default="",
        description="'pass', 'review', 'fail'",
    )


class ArtworkInspectionResult(NullSafeBase):
    """Pipeline result wrapping ArtworkInspectionReport + error handling."""

    performed: bool = False
    report: ArtworkInspectionReport | None = None
    error: str | None = None
