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
    """Extract TextBlock objects from pymupdf page dict output.

    Works at the pymupdf *block* level (≈ paragraph), not at span level.
    All spans within a block are concatenated into a single TextBlock,
    using the dominant (most frequent) font for metadata.
    """
    blocks: list[TextBlock] = []
    block_index = 0

    for block in page_dict.get("blocks", []):
        if block.get("type") != 0:  # 0 = text block
            continue

        # Collect all text and font info from spans in this block
        line_texts: list[str] = []
        span_fonts: list[tuple[str, float, bool, int]] = []  # (font, size, bold, char_count)

        for line in block.get("lines", []):
            span_texts_in_line: list[str] = []
            for span in line.get("spans", []):
                text = span.get("text", "")
                if not text.strip():
                    continue
                span_texts_in_line.append(text.strip())

                font = span.get("font", "")
                size = span.get("size", 0.0)
                flags = span.get("flags", 0)
                is_bold = bool(flags & 2**4)
                span_fonts.append((font, size, is_bold, len(text)))

            if span_texts_in_line:
                line_texts.append(" ".join(span_texts_in_line))

        full_text = " ".join(line_texts).strip()
        if not full_text:
            continue

        # Dominant font = the one covering the most characters
        if span_fonts:
            # Pick font with most characters
            best = max(span_fonts, key=lambda f: f[3])
            font_name = best[0]
            font_size = round(best[1], 1)
            is_bold = best[2]
        else:
            font_name = ""
            font_size = 0.0
            is_bold = False

        bbox = block.get("bbox", (0, 0, 0, 0))

        blocks.append(
            TextBlock(
                text=full_text,
                bbox=tuple(bbox),
                font_name=font_name,
                font_size=font_size,
                is_bold=is_bold,
                block_index=block_index,
            )
        )
        block_index += 1

    return blocks


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

        if content_blocks:
            pages.append(
                PageExtraction(
                    page_number=idx + 1,  # 1-based
                    blocks=content_blocks,
                    width=round(width, 1),
                    height=round(height, 1),
                )
            )
            logger.debug("Page {}: {} blocks extracted", idx + 1, len(content_blocks))
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
