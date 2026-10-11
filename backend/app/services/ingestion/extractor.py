"""
FinRAG — PDF/TXT text extraction using PyMuPDF.
Preserves original page numbers and detects image-only pages.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ExtractedPage:
    page_number: int        # 1-indexed
    text: str
    char_count: int
    word_count: int
    is_empty: bool
    is_image_only: bool
    warnings: list[str] = field(default_factory=list)


@dataclass
class ExtractionResult:
    pages: list[ExtractedPage]
    total_pages: int
    extracted_pages: int
    image_only_pages: int
    empty_pages: int
    warnings: list[str]
    file_type: str  # "pdf" | "txt"


def extract_pdf(file_path: Path) -> ExtractionResult:
    """
    Extract text from a PDF file page by page using PyMuPDF.
    Returns page-level text with original page numbers.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise RuntimeError("PyMuPDF is not installed. Run: pip install pymupdf")

    pages: list[ExtractedPage] = []
    warnings: list[str] = []
    image_only_count = 0
    empty_count = 0

    try:
        doc = fitz.open(str(file_path))
    except Exception as e:
        raise ValueError(f"Failed to open PDF {file_path.name}: {e}") from e

    total_pages = len(doc)

    for page_num in range(total_pages):
        page = doc[page_num]
        page_number = page_num + 1  # Convert to 1-indexed

        # Extract text
        raw_text = page.get_text("text")

        # Check if page has any images
        image_list = page.get_images(full=False)
        has_images = len(image_list) > 0

        # Clean the text
        cleaned_text = _clean_text(raw_text)

        char_count = len(cleaned_text)
        word_count = len(cleaned_text.split()) if cleaned_text else 0

        is_empty = char_count < 10
        is_image_only = is_empty and has_images

        page_warnings = []
        if is_image_only:
            image_only_count += 1
            page_warnings.append(
                f"Page {page_number}: contains images only — OCR may be required for text extraction."
            )
            logger.warning(
                "image_only_page",
                file=file_path.name,
                page=page_number,
            )
        elif is_empty:
            empty_count += 1

        pages.append(
            ExtractedPage(
                page_number=page_number,
                text=cleaned_text,
                char_count=char_count,
                word_count=word_count,
                is_empty=is_empty,
                is_image_only=is_image_only,
                warnings=page_warnings,
            )
        )

    doc.close()

    if image_only_count > 0:
        warnings.append(
            f"{image_only_count} page(s) appear to contain images only and could not be extracted. "
            "Consider using an OCR tool (e.g., Tesseract) for those pages."
        )

    extracted_count = sum(1 for p in pages if not p.is_empty)
    logger.info(
        "pdf_extraction_complete",
        file=file_path.name,
        total_pages=total_pages,
        extracted=extracted_count,
        image_only=image_only_count,
        empty=empty_count,
    )

    return ExtractionResult(
        pages=pages,
        total_pages=total_pages,
        extracted_pages=extracted_count,
        image_only_pages=image_only_count,
        empty_pages=empty_count,
        warnings=warnings,
        file_type="pdf",
    )


def extract_txt(file_path: Path) -> ExtractionResult:
    """
    Extract text from a plain TXT file.
    Treats each 50-line block as a virtual 'page' for consistent chunk metadata.
    """
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        raise ValueError(f"Failed to read TXT file {file_path.name}: {e}") from e

    lines = content.splitlines()
    lines_per_page = 50
    pages: list[ExtractedPage] = []

    if not lines:
        # Empty file
        pages.append(ExtractedPage(
            page_number=1,
            text="",
            char_count=0,
            word_count=0,
            is_empty=True,
            is_image_only=False,
            warnings=["File is empty."],
        ))
    else:
        for i in range(0, max(len(lines), 1), lines_per_page):
            chunk_lines = lines[i : i + lines_per_page]
            text = "\n".join(chunk_lines)
            cleaned = _clean_text(text)
            page_num = (i // lines_per_page) + 1
            pages.append(ExtractedPage(
                page_number=page_num,
                text=cleaned,
                char_count=len(cleaned),
                word_count=len(cleaned.split()),
                is_empty=len(cleaned) < 10,
                is_image_only=False,
            ))

    extracted = sum(1 for p in pages if not p.is_empty)
    return ExtractionResult(
        pages=pages,
        total_pages=len(pages),
        extracted_pages=extracted,
        image_only_pages=0,
        empty_pages=len(pages) - extracted,
        warnings=[],
        file_type="txt",
    )


def extract_document(file_path: Path) -> ExtractionResult:
    """
    Route to the appropriate extractor based on file extension.
    """
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return extract_pdf(file_path)
    elif suffix in (".txt", ".text"):
        return extract_txt(file_path)
    else:
        raise ValueError(f"Unsupported file type: {suffix}. Supported: .pdf, .txt")


def _clean_text(text: str) -> str:
    """Clean extracted text while preserving meaningful structure."""
    if not text:
        return ""

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove null bytes and other control characters except tabs and newlines
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    # Collapse excessive blank lines (more than 2) to 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Remove trailing whitespace on each line
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines)

    return text.strip()
