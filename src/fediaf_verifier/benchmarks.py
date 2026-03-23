"""Design benchmarks: static baselines + self-learning from analysed labels.

Provides segment-based reference ranges for each design category so that
a label's scores can be compared against "the industry".

Architecture:
  1. STATIC_BENCHMARKS — hand-curated ranges per product segment.
  2. JSON persistence — every design analysis appends scores to a local
     JSON file, building real percentile data over time.
  3. get_benchmarks() — returns BenchmarkComparison list for a given
     segment + category_scores, preferring real data when N >= 20.
"""

from __future__ import annotations

import json
from pathlib import Path

from loguru import logger

from fediaf_verifier.models.design_analysis import BenchmarkComparison, DesignCategoryScore

# ---------------------------------------------------------------------------
# 1. Static baselines (curated from domain knowledge)
# ---------------------------------------------------------------------------
# Each segment maps category_key -> (p25, median, p75).
# Scores 0-100 representing typical pet food label quality in that segment.

SEGMENTS = [
    "premium_dry",
    "economy_dry",
    "premium_wet",
    "economy_wet",
    "treats",
    "supplements",
    "barf_raw",
    "veterinary",
]

CATEGORY_KEYS = [
    "visual_hierarchy",
    "readability",
    "color_usage",
    "layout_composition",
    "regulatory_placement",
    "shelf_impact",
    "imagery",
    "target_audience",
    "sustainability",
    "multilanguage_layout",
]

# fmt: off
_STATIC: dict[str, dict[str, tuple[int, int, int]]] = {
    "premium_dry": {
        "visual_hierarchy":     (60, 74, 88),
        "readability":          (58, 72, 85),
        "color_usage":          (62, 76, 89),
        "layout_composition":   (55, 70, 84),
        "regulatory_placement": (50, 65, 78),
        "shelf_impact":         (58, 73, 87),
        "imagery":              (60, 75, 88),
        "target_audience":      (62, 77, 90),
        "sustainability":       (40, 55, 72),
        "multilanguage_layout": (45, 60, 75),
    },
    "economy_dry": {
        "visual_hierarchy":     (42, 56, 68),
        "readability":          (45, 58, 70),
        "color_usage":          (40, 54, 66),
        "layout_composition":   (38, 52, 65),
        "regulatory_placement": (44, 57, 70),
        "shelf_impact":         (35, 48, 62),
        "imagery":              (35, 50, 64),
        "target_audience":      (38, 52, 66),
        "sustainability":       (25, 38, 52),
        "multilanguage_layout": (40, 54, 68),
    },
    "premium_wet": {
        "visual_hierarchy":     (58, 72, 86),
        "readability":          (55, 70, 83),
        "color_usage":          (60, 75, 88),
        "layout_composition":   (54, 68, 82),
        "regulatory_placement": (48, 62, 76),
        "shelf_impact":         (56, 71, 85),
        "imagery":              (62, 77, 90),
        "target_audience":      (58, 73, 87),
        "sustainability":       (38, 52, 68),
        "multilanguage_layout": (42, 58, 73),
    },
    "economy_wet": {
        "visual_hierarchy":     (38, 52, 65),
        "readability":          (40, 54, 67),
        "color_usage":          (36, 50, 63),
        "layout_composition":   (35, 48, 62),
        "regulatory_placement": (42, 55, 68),
        "shelf_impact":         (32, 45, 58),
        "imagery":              (33, 47, 62),
        "target_audience":      (35, 49, 63),
        "sustainability":       (22, 35, 48),
        "multilanguage_layout": (38, 52, 66),
    },
    "treats": {
        "visual_hierarchy":     (52, 66, 80),
        "readability":          (48, 62, 76),
        "color_usage":          (55, 70, 84),
        "layout_composition":   (46, 60, 74),
        "regulatory_placement": (40, 54, 68),
        "shelf_impact":         (55, 70, 84),
        "imagery":              (56, 72, 86),
        "target_audience":      (52, 67, 82),
        "sustainability":       (30, 44, 58),
        "multilanguage_layout": (36, 50, 65),
    },
    "supplements": {
        "visual_hierarchy":     (50, 64, 78),
        "readability":          (54, 68, 82),
        "color_usage":          (48, 62, 76),
        "layout_composition":   (50, 64, 78),
        "regulatory_placement": (55, 68, 82),
        "shelf_impact":         (40, 54, 68),
        "imagery":              (38, 52, 66),
        "target_audience":      (48, 62, 76),
        "sustainability":       (32, 46, 60),
        "multilanguage_layout": (44, 58, 72),
    },
    "barf_raw": {
        "visual_hierarchy":     (44, 58, 72),
        "readability":          (42, 56, 70),
        "color_usage":          (46, 60, 74),
        "layout_composition":   (40, 54, 68),
        "regulatory_placement": (38, 52, 66),
        "shelf_impact":         (42, 56, 70),
        "imagery":              (48, 62, 76),
        "target_audience":      (50, 64, 78),
        "sustainability":       (35, 50, 65),
        "multilanguage_layout": (34, 48, 62),
    },
    "veterinary": {
        "visual_hierarchy":     (55, 70, 84),
        "readability":          (60, 74, 88),
        "color_usage":          (50, 64, 78),
        "layout_composition":   (54, 68, 82),
        "regulatory_placement": (60, 74, 88),
        "shelf_impact":         (42, 56, 70),
        "imagery":              (40, 55, 70),
        "target_audience":      (55, 70, 84),
        "sustainability":       (30, 44, 58),
        "multilanguage_layout": (48, 62, 76),
    },
}
# fmt: on

# Default segment when none specified
DEFAULT_SEGMENT = "premium_dry"

# Minimum number of stored analyses before we prefer real data over static
MIN_SAMPLES_FOR_REAL = 20

# Where accumulated scores are stored
_STORE_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "benchmark_scores.json"


# ---------------------------------------------------------------------------
# 2. JSON persistence
# ---------------------------------------------------------------------------


def _load_store() -> dict:
    """Load the accumulated scores store (segment -> category -> list[int])."""
    if _STORE_PATH.exists():
        try:
            return json.loads(_STORE_PATH.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("Nie mozna wczytac benchmark store: {}", e)
    return {}


def _save_store(store: dict) -> None:
    """Persist the accumulated scores store."""
    try:
        _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _STORE_PATH.write_text(
            json.dumps(store, ensure_ascii=False, indent=1),
            encoding="utf-8",
        )
    except Exception as e:
        logger.warning("Nie mozna zapisac benchmark store: {}", e)


def record_scores(
    segment: str,
    category_scores: list[DesignCategoryScore],
) -> None:
    """Append a new set of design scores to the persistent store."""
    if segment not in SEGMENTS:
        segment = DEFAULT_SEGMENT

    store = _load_store()
    seg_data = store.setdefault(segment, {})

    for cs in category_scores:
        if cs.category in CATEGORY_KEYS:
            scores_list = seg_data.setdefault(cs.category, [])
            scores_list.append(cs.score)
            # Cap at 500 samples per category to limit file size
            if len(scores_list) > 500:
                seg_data[cs.category] = scores_list[-500:]

    _save_store(store)
    logger.debug("Zapisano benchmark scores dla segmentu '{}'", segment)


# ---------------------------------------------------------------------------
# 3. Benchmark computation
# ---------------------------------------------------------------------------


def _percentile_from_static(score: int, low: int, median: int, high: int) -> int:
    """Estimate percentile from static p25/p50/p75 using linear interpolation."""
    if score <= low:
        # Map 0..low -> 0..25
        return max(0, int(25 * score / low)) if low > 0 else 0
    elif score <= median:
        # Map low..median -> 25..50
        return 25 + int(25 * (score - low) / (median - low)) if median > low else 25
    elif score <= high:
        # Map median..high -> 50..75
        return 50 + int(25 * (score - median) / (high - median)) if high > median else 50
    else:
        # Map high..100 -> 75..100
        return 75 + int(25 * (score - high) / (100 - high)) if high < 100 else 100


def _percentile_from_real(score: int, scores: list[int]) -> int:
    """Compute actual percentile rank from stored scores."""
    below = sum(1 for s in scores if s < score)
    equal = sum(1 for s in scores if s == score)
    return int(100 * (below + 0.5 * equal) / len(scores))


def _verdict(percentile: int) -> str:
    if percentile >= 75:
        return "excellent"
    elif percentile >= 50:
        return "above_average"
    elif percentile >= 25:
        return "average"
    else:
        return "below_average"


def get_benchmarks(
    segment: str,
    category_scores: list[DesignCategoryScore],
) -> list[BenchmarkComparison]:
    """Compare design scores against benchmarks for the given segment.

    Uses real accumulated data if available (N >= 20), otherwise static baselines.
    """
    if segment not in SEGMENTS:
        segment = DEFAULT_SEGMENT

    store = _load_store()
    seg_data = store.get(segment, {})
    static_seg = _STATIC.get(segment, _STATIC[DEFAULT_SEGMENT])

    results: list[BenchmarkComparison] = []

    for cs in category_scores:
        cat = cs.category
        if cat not in CATEGORY_KEYS:
            continue

        real_scores = seg_data.get(cat, [])
        static = static_seg.get(cat, (50, 65, 80))

        if len(real_scores) >= MIN_SAMPLES_FOR_REAL:
            import numpy as np  # core dep, cached by Python after first import

            arr = np.array(real_scores)
            low = int(np.percentile(arr, 25))
            median = int(np.percentile(arr, 50))
            high = int(np.percentile(arr, 75))
            percentile = _percentile_from_real(cs.score, real_scores)
        else:
            low, median, high = static
            percentile = _percentile_from_static(cs.score, low, median, high)

        clamped_pct = min(100, max(0, percentile))
        results.append(BenchmarkComparison(
            category=cat,
            category_name=cs.category_name,
            score=cs.score,
            segment=segment,
            benchmark_low=low,
            benchmark_median=median,
            benchmark_high=high,
            percentile=clamped_pct,
            verdict=_verdict(clamped_pct),
        ))

    return results
