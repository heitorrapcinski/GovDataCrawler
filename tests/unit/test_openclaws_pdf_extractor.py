"""Unit tests for openclaws.pdf_extractor module."""

import os
import tempfile

import pytest
from PyPDF2 import PdfWriter

from openclaws.pdf_extractor import extract_text


@pytest.fixture
def valid_pdf(tmp_path):
    """Create a valid PDF with extractable text."""
    pdf_path = tmp_path / "valid.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    # Add text via annotation-free approach: create a page with content
    from PyPDF2.generic import (
        ArrayObject,
        DecodedStreamObject,
        DictionaryObject,
        NameObject,
        NumberObject,
    )

    page = writer.pages[0]
    # Build a simple content stream that writes text
    content = b"BT /F1 12 Tf 100 700 Td (Hello World from PDF) Tj ET"
    stream = DecodedStreamObject()
    stream.set_data(content)

    # Add a font resource to the page
    font_dict = DictionaryObject()
    font_dict.update(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    resources = DictionaryObject()
    font_resources = DictionaryObject()
    font_resources[NameObject("/F1")] = font_dict
    resources[NameObject("/Font")] = font_resources
    page[NameObject("/Resources")] = resources
    page[NameObject("/Contents")] = stream

    with open(pdf_path, "wb") as f:
        writer.write(f)

    return str(pdf_path)


@pytest.fixture
def empty_pdf(tmp_path):
    """Create a valid PDF with no extractable text (blank pages only)."""
    pdf_path = tmp_path / "empty.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    with open(pdf_path, "wb") as f:
        writer.write(f)
    return str(pdf_path)


@pytest.fixture
def corrupted_pdf(tmp_path):
    """Create a corrupted file that is not a valid PDF."""
    pdf_path = tmp_path / "corrupted.pdf"
    pdf_path.write_bytes(b"\x00\x01\x02\x03\x04random garbage data not a pdf")
    return str(pdf_path)


class TestExtractTextSuccess:
    """Test successful text extraction from a valid PDF."""

    def test_extracts_text_from_valid_pdf(self, valid_pdf):
        result = extract_text(valid_pdf)
        assert result is not None
        assert "Hello World from PDF" in result

    def test_returns_string_type(self, valid_pdf):
        result = extract_text(valid_pdf)
        assert isinstance(result, str)


class TestExtractTextCorruptedPdf:
    """Test handling of corrupted/unreadable PDFs."""

    def test_returns_none_for_corrupted_pdf(self, corrupted_pdf):
        result = extract_text(corrupted_pdf)
        assert result is None

    def test_does_not_raise_for_corrupted_pdf(self, corrupted_pdf):
        # Should handle gracefully without raising exceptions
        extract_text(corrupted_pdf)

    def test_returns_none_for_nonexistent_file(self):
        result = extract_text("/nonexistent/path/to/file.pdf")
        assert result is None


class TestExtractTextSizeLimit:
    """Test file size limit enforcement (>50 MB skip)."""

    def test_returns_none_when_file_exceeds_default_limit(self, valid_pdf):
        """Mock file size to exceed 50 MB limit."""
        from unittest.mock import patch

        # 51 MB in bytes
        large_size = 51 * 1024 * 1024
        with patch("openclaws.pdf_extractor.os.path.getsize", return_value=large_size):
            result = extract_text(valid_pdf)
        assert result is None

    def test_returns_none_when_file_exceeds_custom_limit(self, valid_pdf):
        """Test with a custom max_size_mb parameter."""
        from unittest.mock import patch

        # 11 MB in bytes, with limit set to 10 MB
        size = 11 * 1024 * 1024
        with patch("openclaws.pdf_extractor.os.path.getsize", return_value=size):
            result = extract_text(valid_pdf, max_size_mb=10)
        assert result is None

    def test_processes_file_at_exact_limit(self, valid_pdf):
        """File exactly at the limit should be processed (not skipped)."""
        from unittest.mock import patch

        # Exactly 50 MB
        exact_size = 50 * 1024 * 1024
        with patch("openclaws.pdf_extractor.os.path.getsize", return_value=exact_size):
            result = extract_text(valid_pdf)
        # Should attempt extraction (not skip)
        assert result is not None


class TestExtractTextEmptyPdf:
    """Test empty PDF (no extractable text)."""

    def test_returns_none_for_empty_pdf(self, empty_pdf):
        result = extract_text(empty_pdf)
        assert result is None
