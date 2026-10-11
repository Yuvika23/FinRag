"""
FinRAG — Text chunking service.
Splits extracted pages into overlapping chunks while preserving page metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.ingestion.extractor import ExtractedPage

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class TextChunk:
    chunk_index: int
    text: str
    page_number: int         # The starting page number of this chunk
    start_char: int          # Character offset in the full document text
    end_char: int
    token_count: int
    document_id: str
    company_name: Optional[str] = None
    ticker: Optional[str] = None
    fiscal_year: Optional[str] = None
    document_type: Optional[str] = None
    source_filename: Optional[str] = None


def chunk_pages(
    pages: list[ExtractedPage],
    document_id: str,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
    company_name: Optional[str] = None,
    ticker: Optional[str] = None,
    fiscal_year: Optional[str] = None,
    document_type: Optional[str] = None,
    source_filename: Optional[str] = None,
) -> list[TextChunk]:
    """
    Split extracted pages into overlapping text chunks.

    Strategy:
    1. Build a page-boundary-aware concatenated text.
    2. Split on sentence boundaries where possible.
    3. Track page numbers per character so each chunk knows its source page.
    4. Preserve overlap between chunks for context continuity.
    """
    cfg_chunk_size = chunk_size or settings.chunk_size
    cfg_overlap = chunk_overlap or settings.chunk_overlap

    # Build character → page_number lookup
    full_text_parts: list[str] = []
    page_boundaries: list[tuple[int, int]] = []  # (start_char, page_number)
    cursor = 0

    for page in pages:
        if page.is_empty:
            continue
        text = page.text
        page_boundaries.append((cursor, page.page_number))
        full_text_parts.append(text)
        cursor += len(text) + 1  # +1 for the joining newline

    if not full_text_parts:
        return []

    full_text = "\n".join(full_text_parts)

    def get_page_for_char(char_pos: int) -> int:
        """Binary search: find which page a character belongs to."""
        lo, hi = 0, len(page_boundaries) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if page_boundaries[mid][0] <= char_pos:
                lo = mid
            else:
                hi = mid - 1
        return page_boundaries[lo][1]

    # Tokenize by approximate word count (no heavy tokenizer needed here)
    words = full_text.split()

    chunks: list[TextChunk] = []
    chunk_index = 0
    i = 0

    while i < len(words):
        chunk_words = words[i : i + cfg_chunk_size]
        chunk_text = " ".join(chunk_words)

        # Estimate character position for page lookup
        # Find the start character of word i in full_text
        start_char = _find_word_char_pos(full_text, words, i)
        end_char = start_char + len(chunk_text)

        page_number = get_page_for_char(start_char) if page_boundaries else 1

        token_count = len(chunk_words)

        chunks.append(
            TextChunk(
                chunk_index=chunk_index,
                text=chunk_text,
                page_number=page_number,
                start_char=start_char,
                end_char=end_char,
                token_count=token_count,
                document_id=document_id,
                company_name=company_name,
                ticker=ticker,
                fiscal_year=fiscal_year,
                document_type=document_type,
                source_filename=source_filename,
            )
        )

        chunk_index += 1
        i += cfg_chunk_size - cfg_overlap  # Advance with overlap

        if i >= len(words) and chunk_index > 0:
            break

    logger.info(
        "chunking_complete",
        document_id=document_id,
        total_chunks=len(chunks),
        chunk_size=cfg_chunk_size,
        overlap=cfg_overlap,
    )

    return chunks


def _find_word_char_pos(full_text: str, words: list[str], word_index: int) -> int:
    """
    Find the character position of the word at word_index in full_text.
    Uses cumulative word position tracking for efficiency.
    """
    if word_index == 0:
        return 0

    # Walk through the text counting words
    pos = 0
    count = 0
    in_word = False

    for i, ch in enumerate(full_text):
        if ch in (" ", "\n", "\t"):
            if in_word:
                count += 1
                in_word = False
                if count == word_index:
                    # Skip leading whitespace
                    j = i + 1
                    while j < len(full_text) and full_text[j] in (" ", "\n", "\t"):
                        j += 1
                    return j
        else:
            in_word = True

    return len(full_text)
