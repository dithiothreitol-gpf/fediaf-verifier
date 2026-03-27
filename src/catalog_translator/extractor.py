"""PDF text extraction via pymupdf."""

from __future__ import annotations

from loguru import logger

from .models.extraction import CatalogExtraction, PageExtraction, TextBlock


def _parse_page_range(page_range: str, total_pages: int) -> list[int]:
    """Parse page range string into list of 0-based page indices.

    Supports: "all", "1-10", "1,3,5", "2-5,8,10-12".
    """
    if page_range.strip().lower() == "all":
        return list(range(total_pages))

    indices: list[int] = []
    for part in page_range.split(","):
        part = part.strip()
        if "-" in part:
            start_s, end_s = part.split("-", 1)
            start = max(int(start_s) - 1, 0)
            end = min(int(end_s), total_pages)
            indices.extend(range(start, end))
        else:
            idx = int(part) - 1
            if 0 <= idx < total_pages:
                indices.append(idx)
    return sorted(set(indices))


def _extract_blocks_from_page(page_dict: dict, page_index: int) -> list[TextBlock]:
    """Extract TextBlock objects from pymupdf page dict output."""
    blocks: list[TextBlock] = []
    block_index = 0

    for block in page_dict.get("blocks", []):
        if block.get("type") != 0:  # 0 = text block
            continue

        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "").strip()
                if not text:
                    continue

                bbox = span.get("bbox", (0, 0, 0, 0))
                font = span.get("font", "")
                size = span.get("size", 0.0)
                flags = span.get("flags", 0)
                is_bold = bool(flags & 2**4)  # bit 4 = bold

                blocks.append(
                    TextBlock(
                        text=text,
                        bbox=tuple(bbox),
                        font_name=font,
                        font_size=round(size, 1),
                        is_bold=is_bold,
                        block_index=block_index,
                    )
                )
                block_index += 1

    return blocks


def _merge_adjacent_blocks(blocks: list[TextBlock], y_threshold: float = 3.0) -> list[TextBlock]:
    """Merge spans that are on the same line (similar Y position) into single blocks."""
    if not blocks:
        return []

    merged: list[TextBlock] = []
    current = blocks[0]

    for blk in blocks[1:]:
        # Same line: similar Y position and same font characteristics
        same_y = abs(blk.bbox[1] - current.bbox[1]) < y_threshold
        same_font = blk.font_name == current.font_name and abs(blk.font_size - current.font_size) < 0.5

        if same_y and same_font:
            # Merge: extend text and bbox
            current = TextBlock(
                text=current.text + " " + blk.text,
                bbox=(
                    min(current.bbox[0], blk.bbox[0]),
                    min(current.bbox[1], blk.bbox[1]),
                    max(current.bbox[2], blk.bbox[2]),
                    max(current.bbox[3], blk.bbox[3]),
                ),
                font_name=current.font_name,
                font_size=current.font_size,
                is_bold=current.is_bold,
                block_index=current.block_index,
            )
        else:
            merged.append(current)
            current = blk

    merged.append(current)
    return merged


def extract_catalog(
    pdf_bytes: bytes,
    page_range: str = "all",
    source_filename: str = "",
) -> CatalogExtraction:
    """Extract text blocks from a PDF catalog.

    Args:
        pdf_bytes: Raw PDF file content.
        page_range: Pages to process ("all", "1-10", "1,3,5").
        source_filename: Original filename for metadata.

    Returns:
        CatalogExtraction with per-page text blocks including font/position info.
    """
    import fitz  # pymupdf

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    total_pages = len(doc)
    indices = _parse_page_range(page_range, total_pages)

    pages: list[PageExtraction] = []

    for idx in indices:
        page = doc[idx]
        page_dict = page.get_text("dict")
        raw_blocks = _extract_blocks_from_page(page_dict, idx)

        # Filter header/footer area (top/bottom 5% of page)
        height = page_dict.get("height", page.rect.height)
        width = page_dict.get("width", page.rect.width)
        margin_top = height * 0.05
        margin_bottom = height * 0.95

        content_blocks = [
            b for b in raw_blocks if margin_top <= b.bbox[1] <= margin_bottom
        ]

        merged = _merge_adjacent_blocks(content_blocks)

        if merged:
            pages.append(
                PageExtraction(
                    page_number=idx + 1,  # 1-based
                    blocks=merged,
                    width=round(width, 1),
                    height=round(height, 1),
                )
            )
            logger.debug("Page {}: {} blocks extracted", idx + 1, len(merged))
        else:
            logger.info("Page {}: no text content, skipping", idx + 1)

    doc.close()

    logger.info(
        "Extraction complete: {} pages with content out of {} total",
        len(pages),
        total_pages,
    )

    return CatalogExtraction(
        pages=pages,
        total_pages=total_pages,
        source_filename=source_filename,
    )
