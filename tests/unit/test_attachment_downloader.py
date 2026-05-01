"""Unit tests for the AttachmentDownloader component."""

import os
from unittest.mock import MagicMock

from gov_data_crawler.attachments import AttachmentDownloader, FALLBACK_FILENAME
from gov_data_crawler.contract import HttpRequestError
from gov_data_crawler.http_client import HttpClient, HttpResponse


class TestAttachmentDownloaderDownload:
    """Tests for AttachmentDownloader.download method."""

    def _make_downloader(self) -> tuple[AttachmentDownloader, MagicMock]:
        """Create an AttachmentDownloader with a mocked HttpClient."""
        http_client = MagicMock(spec=HttpClient)
        downloader = AttachmentDownloader(http_client=http_client)
        return downloader, http_client

    def test_successful_download_saves_file(self, tmp_path: object) -> None:
        """A successful download writes content to disk and returns the file path."""
        target_dir = str(tmp_path)
        downloader, http_client = self._make_downloader()
        http_client.get.return_value = HttpResponse(
            status_code=200,
            text="",
            headers={},
            content=b"PDF file content here",
        )

        result = downloader.download(
            "https://example.com/files/contrato_001.pdf", target_dir
        )

        assert result is not None
        assert result == os.path.join(target_dir, "contrato_001.pdf")
        assert os.path.exists(result)
        with open(result, "rb") as f:
            assert f.read() == b"PDF file content here"

    def test_download_creates_target_directory(self, tmp_path: object) -> None:
        """The download method creates the target directory if it does not exist."""
        target_dir = os.path.join(str(tmp_path), "nested", "dir")
        downloader, http_client = self._make_downloader()
        http_client.get.return_value = HttpResponse(
            status_code=200,
            text="",
            headers={},
            content=b"data",
        )

        result = downloader.download(
            "https://example.com/files/doc.pdf", target_dir
        )

        assert result is not None
        assert os.path.isdir(target_dir)

    def test_download_failure_returns_none(self, tmp_path: object) -> None:
        """When HttpRequestError is raised, download returns None."""
        target_dir = str(tmp_path)
        downloader, http_client = self._make_downloader()
        http_client.get.side_effect = HttpRequestError(
            url="https://example.com/files/doc.pdf",
            status_code=500,
            message="Server error",
        )

        result = downloader.download(
            "https://example.com/files/doc.pdf", target_dir
        )

        assert result is None

    def test_unexpected_error_returns_none(self, tmp_path: object) -> None:
        """When an unexpected exception is raised, download returns None."""
        target_dir = str(tmp_path)
        downloader, http_client = self._make_downloader()
        http_client.get.side_effect = RuntimeError("Unexpected failure")

        result = downloader.download(
            "https://example.com/files/doc.pdf", target_dir
        )

        assert result is None

    def test_download_uses_content_disposition_filename(
        self, tmp_path: object
    ) -> None:
        """When Content-Disposition header has a filename, it is used."""
        target_dir = str(tmp_path)
        downloader, http_client = self._make_downloader()
        http_client.get.return_value = HttpResponse(
            status_code=200,
            text="",
            headers={
                "Content-Disposition": 'attachment; filename="relatorio_final.pdf"'
            },
            content=b"report data",
        )

        result = downloader.download(
            "https://example.com/download?id=123", target_dir
        )

        assert result is not None
        assert os.path.basename(result) == "relatorio_final.pdf"


class TestExtractFilename:
    """Tests for AttachmentDownloader.extract_filename method."""

    def _make_downloader(self) -> AttachmentDownloader:
        """Create an AttachmentDownloader with a mocked HttpClient."""
        http_client = MagicMock(spec=HttpClient)
        return AttachmentDownloader(http_client=http_client)

    def test_filename_from_url_path(self) -> None:
        """Extracts filename from the last segment of the URL path."""
        downloader = self._make_downloader()
        result = downloader.extract_filename(
            "https://example.com/files/contrato_001.pdf", {}
        )
        assert result == "contrato_001.pdf"

    def test_filename_from_url_with_nested_path(self) -> None:
        """Extracts filename from a deeply nested URL path."""
        downloader = self._make_downloader()
        result = downloader.extract_filename(
            "https://example.com/a/b/c/documento.docx", {}
        )
        assert result == "documento.docx"

    def test_filename_from_content_disposition_plain(self) -> None:
        """Prefers Content-Disposition filename over URL path."""
        downloader = self._make_downloader()
        result = downloader.extract_filename(
            "https://example.com/download?id=123",
            {"Content-Disposition": 'attachment; filename="relatorio.pdf"'},
        )
        assert result == "relatorio.pdf"

    def test_filename_from_content_disposition_without_quotes(self) -> None:
        """Handles Content-Disposition filename without quotes."""
        downloader = self._make_downloader()
        result = downloader.extract_filename(
            "https://example.com/download?id=123",
            {"Content-Disposition": "attachment; filename=relatorio.pdf"},
        )
        assert result == "relatorio.pdf"

    def test_filename_star_preferred_over_plain_filename(self) -> None:
        """RFC 5987 filename* is preferred over plain filename."""
        downloader = self._make_downloader()
        result = downloader.extract_filename(
            "https://example.com/download",
            {
                "Content-Disposition": (
                    "attachment; filename=\"fallback.pdf\"; "
                    "filename*=UTF-8''relat%C3%B3rio_final.pdf"
                )
            },
        )
        assert result == "relatório_final.pdf"

    def test_filename_star_with_encoding(self) -> None:
        """filename* with percent-encoded characters is decoded correctly."""
        downloader = self._make_downloader()
        result = downloader.extract_filename(
            "https://example.com/download",
            {
                "Content-Disposition": (
                    "attachment; filename*=UTF-8''contrato%20especial.pdf"
                )
            },
        )
        assert result == "contrato especial.pdf"

    def test_fallback_when_no_filename_available(self) -> None:
        """Returns fallback filename when URL has no path and no Content-Disposition."""
        downloader = self._make_downloader()
        result = downloader.extract_filename("https://example.com/", {})
        assert result == FALLBACK_FILENAME

    def test_url_encoded_filename_is_decoded(self) -> None:
        """Percent-encoded characters in URL path are decoded."""
        downloader = self._make_downloader()
        result = downloader.extract_filename(
            "https://example.com/files/relat%C3%B3rio.pdf", {}
        )
        assert result == "relatório.pdf"

    def test_content_disposition_case_insensitive_header(self) -> None:
        """Content-Disposition header lookup is case-insensitive."""
        downloader = self._make_downloader()
        result = downloader.extract_filename(
            "https://example.com/download",
            {"content-disposition": 'attachment; filename="report.pdf"'},
        )
        assert result == "report.pdf"
