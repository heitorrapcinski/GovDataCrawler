"""Attachment downloader for contract files."""

import logging
import os
import re
from urllib.parse import unquote, urlparse

from gov_data_crawler.contract import HttpRequestError
from gov_data_crawler.http_client import HttpClient

logger = logging.getLogger(__name__)

FALLBACK_FILENAME = "attachment"


class AttachmentDownloader:
    """Downloads and saves contract attachment files."""

    def __init__(
        self,
        http_client: HttpClient,
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialize the attachment downloader.

        Args:
            http_client: HTTP client for fetching files.
            logger: Logger instance. Falls back to module logger if None.
        """
        self._http_client = http_client
        self._logger = logger or logging.getLogger(__name__)

    def download(self, url: str, target_dir: str) -> str | None:
        """Download a single attachment to the target directory.

        Args:
            url: Absolute URL of the attachment.
            target_dir: Directory to save the file in.

        Returns:
            The saved file path, or None if download failed.
        """
        try:
            os.makedirs(target_dir, exist_ok=True)
            response = self._http_client.get(url)
            filename = self.extract_filename(url, response.headers)
            file_path = os.path.join(target_dir, filename)

            with open(file_path, "wb") as f:
                f.write(response.content)

            self._logger.info("Downloaded attachment: %s -> %s", url, file_path)
            return file_path
        except HttpRequestError as exc:
            self._logger.error(
                "Failed to download attachment from %s: %s", url, exc.message
            )
            return None
        except Exception as exc:
            self._logger.error(
                "Unexpected error downloading attachment from %s: %s", url, exc
            )
            return None

    def extract_filename(self, url: str, response_headers: dict) -> str:
        """Determine the filename for a downloaded attachment.

        Prefers Content-Disposition header (filename* over filename),
        falls back to URL path.

        Args:
            url: The attachment URL.
            response_headers: HTTP response headers.

        Returns:
            Filename string.
        """
        # Try Content-Disposition header first
        content_disposition = response_headers.get(
            "Content-Disposition"
        ) or response_headers.get("content-disposition")

        if content_disposition:
            # Try RFC 5987 filename* first
            filename_star = self._parse_filename_star(content_disposition)
            if filename_star:
                return filename_star

            # Try plain filename parameter
            filename = self._parse_filename(content_disposition)
            if filename:
                return filename

        # Fall back to URL path
        return self._filename_from_url(url)

    def _parse_filename_star(self, content_disposition: str) -> str | None:
        """Extract filename from RFC 5987 filename* parameter.

        Args:
            content_disposition: Content-Disposition header value.

        Returns:
            Decoded filename or None if not found.
        """
        match = re.search(
            r"filename\*\s*=\s*([^']*)'([^']*)'(.+?)(?:;|$)",
            content_disposition,
            re.IGNORECASE,
        )
        if match:
            # encoding = match.group(1)  # e.g., UTF-8
            # language = match.group(2)  # e.g., pt-BR
            encoded_filename = match.group(3).strip()
            return unquote(encoded_filename)
        return None

    def _parse_filename(self, content_disposition: str) -> str | None:
        """Extract filename from plain filename parameter.

        Args:
            content_disposition: Content-Disposition header value.

        Returns:
            Filename or None if not found.
        """
        match = re.search(
            r'filename\s*=\s*"?([^";]+)"?',
            content_disposition,
            re.IGNORECASE,
        )
        if match:
            return match.group(1).strip()
        return None

    def _filename_from_url(self, url: str) -> str:
        """Extract filename from the last segment of the URL path.

        Args:
            url: The attachment URL.

        Returns:
            Filename from URL path, or fallback name if none found.
        """
        parsed = urlparse(url)
        path = unquote(parsed.path)
        # Get the last non-empty segment
        segments = [s for s in path.split("/") if s]
        if segments:
            return segments[-1]
        return FALLBACK_FILENAME
