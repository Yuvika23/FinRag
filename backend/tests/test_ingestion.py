"""
FinRAG — Tests for the ingestion pipeline services.
"""

import pytest
from pathlib import Path
from app.services.ingestion.extractor import extract_txt, _clean_text
from app.services.ingestion.chunker import chunk_pages, TextChunk


# ── Text extraction tests ──────────────────────────────────────────────────

class TestTextCleaning:
    def test_removes_control_characters(self):
        dirty = "Hello\x00World\x01\x02Text"
        result = _clean_text(dirty)
        assert "\x00" not in result
        assert "HelloWorldText" in result or "Hello" in result

    def test_preserves_newlines_and_text(self):
        text = "Line 1\nLine 2\nLine 3"
        result = _clean_text(text)
        assert "Line 1" in result
        assert "Line 3" in result

    def test_collapses_excessive_blank_lines(self):
        text = "Para 1\n\n\n\n\nPara 2"
        result = _clean_text(text)
        assert "\n\n\n" not in result

    def test_empty_string(self):
        assert _clean_text("") == ""


class TestTxtExtraction:
    def test_extracts_from_txt_file(self, tmp_path):
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("This is a test document.\nIt has two lines.", encoding="utf-8")

        result = extract_txt(txt_file)

        assert result.total_pages >= 1
        assert result.extracted_pages >= 1
        assert result.file_type == "txt"
        assert any("This is a test document" in p.text for p in result.pages)

    def test_empty_file(self, tmp_path):
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("", encoding="utf-8")

        result = extract_txt(empty_file)

        assert result.total_pages >= 1
        assert result.empty_pages >= 1

    def test_page_numbers_are_positive(self, tmp_path):
        txt_file = tmp_path / "test.txt"
        # Write 200 lines to span multiple virtual pages
        txt_file.write_text("\n".join(f"Line {i}" for i in range(200)), encoding="utf-8")

        result = extract_txt(txt_file)

        for page in result.pages:
            assert page.page_number >= 1

    def test_preserves_text_content(self, tmp_path):
        content = "Revenue: $1,000 million\nNet income: $200 million"
        txt_file = tmp_path / "financial.txt"
        txt_file.write_text(content, encoding="utf-8")

        result = extract_txt(txt_file)
        full_text = " ".join(p.text for p in result.pages)

        assert "Revenue" in full_text
        assert "1,000 million" in full_text


# ── Chunking tests ─────────────────────────────────────────────────────────

class TestChunking:
    def _make_pages(self, texts: list[str]):
        from app.services.ingestion.extractor import ExtractedPage
        return [
            ExtractedPage(
                page_number=i + 1,
                text=text,
                char_count=len(text),
                word_count=len(text.split()),
                is_empty=len(text.strip()) < 10,
                is_image_only=False,
            )
            for i, text in enumerate(texts)
        ]

    def test_produces_chunks(self):
        pages = self._make_pages(["word " * 200])
        chunks = chunk_pages(pages, document_id="doc1", chunk_size=50, chunk_overlap=10)
        assert len(chunks) > 0
        assert all(isinstance(c, TextChunk) for c in chunks)

    def test_chunk_metadata_set(self):
        pages = self._make_pages(["word " * 100])
        chunks = chunk_pages(
            pages,
            document_id="test_doc",
            chunk_size=30,
            chunk_overlap=5,
            company_name="Acme Corp",
            ticker="ACM",
            fiscal_year="FY2024",
        )
        for chunk in chunks:
            assert chunk.document_id == "test_doc"
            assert chunk.company_name == "Acme Corp"
            assert chunk.ticker == "ACM"
            assert chunk.fiscal_year == "FY2024"
            assert chunk.page_number >= 1

    def test_chunk_index_sequential(self):
        pages = self._make_pages(["word " * 300])
        chunks = chunk_pages(pages, document_id="doc2", chunk_size=50, chunk_overlap=10)
        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_empty_pages_skipped(self):
        pages = self._make_pages(["", "   ", "word " * 100])
        chunks = chunk_pages(pages, document_id="doc3", chunk_size=30, chunk_overlap=5)
        # Should still produce chunks from the non-empty page
        assert len(chunks) > 0

    def test_single_page_chunks(self):
        pages = self._make_pages(["Alpha Beta Gamma Delta Epsilon " * 10])
        chunks = chunk_pages(pages, document_id="doc4", chunk_size=5, chunk_overlap=1)
        assert len(chunks) > 1
        # Check overlap — adjacent chunks should share some words
        for i in range(len(chunks) - 1):
            words_a = set(chunks[i].text.split())
            words_b = set(chunks[i + 1].text.split())
            assert len(words_a & words_b) > 0, "No overlap between adjacent chunks"
