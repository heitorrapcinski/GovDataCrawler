"""Contract processor for end-to-end single contract processing."""

import logging

from gov_data_crawler.attachments import AttachmentDownloader
from gov_data_crawler.contract import (
    ContractMetadata,
    HttpRequestError,
    ParsingError,
    ProcessingResult,
)
from gov_data_crawler.detail_parser import DetailParser
from gov_data_crawler.http_client import HttpClient
from gov_data_crawler.listing import CONTRACT_DETAIL_URL_TEMPLATE
from gov_data_crawler.metadata import MetadataWriter
from gov_data_crawler.output import OutputManager


class ContractProcessor:
    """Processes a single contract: fetch, parse, download, save."""

    def __init__(
        self,
        http_client: HttpClient,
        detail_parser: DetailParser,
        attachment_downloader: AttachmentDownloader,
        metadata_writer: MetadataWriter,
        output_manager: OutputManager,
        logger: logging.Logger,
    ) -> None:
        """Initialize the contract processor.

        Args:
            http_client: HTTP client for fetching detail pages.
            detail_parser: Parser for extracting metadata from detail HTML.
            attachment_downloader: Downloader for contract attachments.
            metadata_writer: Writer for serializing metadata to JSON.
            output_manager: Manager for output directory structure.
            logger: Logger instance for progress and error messages.
        """
        self._http_client = http_client
        self._detail_parser = detail_parser
        self._attachment_downloader = attachment_downloader
        self._metadata_writer = metadata_writer
        self._output_manager = output_manager
        self._logger = logger

    def process(self, contract_id: str) -> ProcessingResult:
        """Process a single contract end-to-end.

        Fetches the detail page, parses metadata and attachment URLs,
        downloads attachments, writes metadata to disk, and returns
        a result indicating success or failure.

        Args:
            contract_id: The contract ID to process.

        Returns:
            ProcessingResult indicating success/failure and attachment count.
        """
        url = CONTRACT_DETAIL_URL_TEMPLATE.format(contract_id)

        try:
            response = self._http_client.get(url)
        except HttpRequestError as exc:
            self._logger.error(
                "Failed to fetch detail page for contract %s: %s",
                contract_id,
                exc.message,
            )
            return ProcessingResult(
                contract_id=contract_id,
                success=False,
                attachments_downloaded=0,
                error=f"HTTP error fetching detail page: {exc.message}",
            )

        # Handle 404 as skip without retry
        if response.status_code == 404:
            self._logger.warning(
                "Contract %s not found (404), skipping", contract_id
            )
            return ProcessingResult(
                contract_id=contract_id,
                success=False,
                attachments_downloaded=0,
                error="Contract detail page not found (404)",
            )

        try:
            metadata = self._detail_parser.parse(response.text, contract_id)
        except ParsingError as exc:
            self._logger.error(
                "Failed to parse detail page for contract %s: %s",
                contract_id,
                exc.message,
            )
            return ProcessingResult(
                contract_id=contract_id,
                success=False,
                attachments_downloaded=0,
                error=f"Parsing error: {exc.message}",
            )

        attachment_urls = self._detail_parser.parse_attachment_urls(response.text)

        contract_dir = self._output_manager.get_contract_dir(
            metadata.orgao, metadata.unidade_gestora, contract_id
        )

        # Download attachments
        downloaded_files: list[str] = []
        for attachment_url in attachment_urls:
            file_path = self._attachment_downloader.download(
                attachment_url, contract_dir
            )
            if file_path is not None:
                downloaded_files.append(file_path)

        # Update metadata with downloaded attachment filenames
        metadata.attachments = [
            _extract_basename(path) for path in downloaded_files
        ]

        # Write metadata to disk
        self._metadata_writer.write(metadata, contract_dir)

        self._logger.info(
            "Processed contract %s: %d attachments downloaded, metadata saved to %s",
            contract_id,
            len(downloaded_files),
            contract_dir,
        )

        return ProcessingResult(
            contract_id=contract_id,
            success=True,
            attachments_downloaded=len(downloaded_files),
        )


def _extract_basename(file_path: str) -> str:
    """Extract the filename from a full file path.

    Args:
        file_path: Full path to a file.

    Returns:
        The basename (filename) portion of the path.
    """
    import os

    return os.path.basename(file_path)
