"""PDF text extraction for OpenClaws AI Assistant."""

import logging
import os

from PyPDF2 import PdfReader
from PyPDF2.errors import PdfReadError

logger = logging.getLogger(__name__)


def extract_text(file_path: str, max_size_mb: int = 50) -> str | None:
    """Extract text content from a PDF file.

    Args:
        file_path: Path to the PDF file.
        max_size_mb: Maximum file size in megabytes. Files exceeding this
            limit are skipped with a warning log.

    Returns:
        Extracted text content as a string, or None if the file cannot be
        read, exceeds the size limit, or contains no extractable text.
    """
    try:
        file_size_bytes = os.path.getsize(file_path)
    except OSError as e:
        logger.warning("Cannot access PDF file '%s': %s", file_path, e)
        return None

    max_size_bytes = max_size_mb * 1024 * 1024
    if file_size_bytes > max_size_bytes:
        logger.warning(
            "Skipping PDF '%s': file size %.2f MB exceeds limit of %d MB",
            file_path,
            file_size_bytes / (1024 * 1024),
            max_size_mb,
        )
        return None

    try:
        reader = PdfReader(file_path)
        text_parts: list[str] = []

        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

        if not text_parts:
            logger.warning(
                "PDF '%s' contains no extractable text", file_path
            )
            return None

        return "\n".join(text_parts)

    except PdfReadError as e:
        logger.warning("Cannot read PDF '%s': %s", file_path, e)
        return None
    except Exception as e:
        logger.warning(
            "Unexpected error extracting text from PDF '%s': %s", file_path, e
        )
        return None
