"""Property-based tests for attachment filename extraction.

Feature: gov-data-crawler
Property 5: filename is preserved from download URL

Validates: Requirements 3.3
"""

from unittest.mock import MagicMock

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from gov_data_crawler.attachments import AttachmentDownloader
from gov_data_crawler.http_client import HttpClient


# Strategy for generating valid filename characters (no path separators or null bytes)
_FILENAME_CHARS = st.sampled_from(
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789"
    "-_. "
)

# Strategy for generating realistic filenames: name + extension
_FILENAME_STRATEGY = st.builds(
    lambda name, ext: f"{name}.{ext}",
    name=st.text(alphabet=_FILENAME_CHARS, min_size=1, max_size=50).filter(
        lambda s: s.strip() != "" and s.strip(".")  != ""
    ),
    ext=st.sampled_from(["pdf", "docx", "xlsx", "txt", "csv", "zip", "png", "jpg"]),
)

# Strategy for generating URL path prefixes
_PATH_PREFIX_STRATEGY = st.sampled_from([
    "https://example.com/files",
    "https://contratos.comprasnet.gov.br/download",
    "https://portal.gov.br/attachments/docs",
    "https://example.com/a/b/c",
    "https://example.com",
])


def _make_downloader() -> AttachmentDownloader:
    """Create an AttachmentDownloader with a mocked HttpClient."""
    http_client = MagicMock(spec=HttpClient)
    return AttachmentDownloader(http_client=http_client)


@settings(max_examples=100, deadline=1000)
@given(
    prefix=_PATH_PREFIX_STRATEGY,
    filename=_FILENAME_STRATEGY,
)
def test_filename_preserved_from_url_path(prefix: str, filename: str) -> None:
    """Property 5: For any URL containing a path component with a filename,
    the AttachmentDownloader.extract_filename method SHALL return the filename
    portion of the URL path (the last path segment), preserving the original
    name and extension.

    **Validates: Requirements 3.3**
    """
    # Ensure filename is non-empty after stripping
    assume(len(filename.strip()) > 0)

    url = f"{prefix}/{filename}"
    downloader = _make_downloader()

    result = downloader.extract_filename(url, {})

    assert result == filename, (
        f"Expected filename '{filename}' from URL '{url}', got '{result}'"
    )
