"""Unit tests for the ContractProcessor component."""

import logging
from unittest.mock import MagicMock

from gov_data_crawler.attachments import AttachmentDownloader
from gov_data_crawler.contract import (
    ContractMetadata,
    HttpRequestError,
    ParsingError,
    ProcessingResult,
)
from gov_data_crawler.detail_parser import DetailParser
from gov_data_crawler.http_client import HttpClient, HttpResponse
from gov_data_crawler.metadata import MetadataWriter
from gov_data_crawler.output import OutputManager
from gov_data_crawler.processor import ContractProcessor


def _make_processor() -> tuple[
    ContractProcessor,
    MagicMock,
    MagicMock,
    MagicMock,
    MagicMock,
    MagicMock,
]:
    """Create a ContractProcessor with all dependencies mocked.

    Returns:
        Tuple of (processor, http_client, detail_parser,
        attachment_downloader, metadata_writer, output_manager).
    """
    http_client = MagicMock(spec=HttpClient)
    detail_parser = MagicMock(spec=DetailParser)
    attachment_downloader = MagicMock(spec=AttachmentDownloader)
    metadata_writer = MagicMock(spec=MetadataWriter)
    output_manager = MagicMock(spec=OutputManager)
    logger = logging.getLogger("test_contract_processor")

    processor = ContractProcessor(
        http_client=http_client,
        detail_parser=detail_parser,
        attachment_downloader=attachment_downloader,
        metadata_writer=metadata_writer,
        output_manager=output_manager,
        logger=logger,
    )

    return (
        processor,
        http_client,
        detail_parser,
        attachment_downloader,
        metadata_writer,
        output_manager,
    )


def _make_metadata(contract_id: str = "500112") -> ContractMetadata:
    """Create a sample ContractMetadata for testing."""
    return ContractMetadata(
        contract_id=contract_id,
        orgao="Ministério da Defesa",
        unidade_gestora="160089 - Base de Apoio Logístico",
        contract_number="01/2024",
        supplier_name="Empresa XYZ Ltda",
        contract_value="R$ 1.500.000,00",
        start_date="2024-01-15",
        end_date="2025-01-14",
        object_description="Prestação de serviços",
        extra_fields={},
        attachments=[],
        scraped_at="2026-01-15T10:30:00Z",
    )


class TestContractProcessorSuccess:
    """Tests for successful contract processing."""

    def test_successful_processing_with_attachments(self) -> None:
        """A contract with attachments is fully processed and returns success."""
        (
            processor,
            http_client,
            detail_parser,
            attachment_downloader,
            metadata_writer,
            output_manager,
        ) = _make_processor()

        html = "<html>detail page</html>"
        http_client.get.return_value = HttpResponse(
            status_code=200, text=html, headers={}, content=b""
        )

        metadata = _make_metadata("500112")
        detail_parser.parse.return_value = metadata
        detail_parser.parse_attachment_urls.return_value = [
            "https://example.com/files/contrato.pdf",
            "https://example.com/files/aditivo.pdf",
        ]

        output_manager.get_contract_dir.return_value = "/output/org/ug/500112"

        attachment_downloader.download.side_effect = [
            "/output/org/ug/500112/contrato.pdf",
            "/output/org/ug/500112/aditivo.pdf",
        ]

        metadata_writer.write.return_value = "/output/org/ug/500112/metadata.json"

        result = processor.process("500112")

        assert result.success is True
        assert result.contract_id == "500112"
        assert result.attachments_downloaded == 2
        assert result.error is None

        # Verify the correct URL was fetched
        http_client.get.assert_called_once()
        call_url = http_client.get.call_args[0][0]
        assert "500112" in call_url

        # Verify metadata was parsed
        detail_parser.parse.assert_called_once_with(html, "500112")
        detail_parser.parse_attachment_urls.assert_called_once_with(html)

        # Verify output directory was requested
        output_manager.get_contract_dir.assert_called_once_with(
            metadata.orgao, metadata.unidade_gestora, "500112"
        )

        # Verify attachments were downloaded
        assert attachment_downloader.download.call_count == 2

        # Verify metadata was written with attachment filenames
        metadata_writer.write.assert_called_once()
        written_metadata = metadata_writer.write.call_args[0][0]
        assert written_metadata.attachments == ["contrato.pdf", "aditivo.pdf"]

    def test_successful_processing_without_attachments(self) -> None:
        """A contract with no attachments is processed successfully."""
        (
            processor,
            http_client,
            detail_parser,
            attachment_downloader,
            metadata_writer,
            output_manager,
        ) = _make_processor()

        http_client.get.return_value = HttpResponse(
            status_code=200, text="<html></html>", headers={}, content=b""
        )

        metadata = _make_metadata("500113")
        detail_parser.parse.return_value = metadata
        detail_parser.parse_attachment_urls.return_value = []

        output_manager.get_contract_dir.return_value = "/output/org/ug/500113"
        metadata_writer.write.return_value = "/output/org/ug/500113/metadata.json"

        result = processor.process("500113")

        assert result.success is True
        assert result.contract_id == "500113"
        assert result.attachments_downloaded == 0
        assert result.error is None

        attachment_downloader.download.assert_not_called()
        metadata_writer.write.assert_called_once()


class TestContractProcessorHttpErrors:
    """Tests for HTTP error handling during contract processing."""

    def test_http_request_error_returns_failure(self) -> None:
        """When HttpRequestError is raised, process returns a failure result."""
        (
            processor,
            http_client,
            detail_parser,
            attachment_downloader,
            metadata_writer,
            output_manager,
        ) = _make_processor()

        http_client.get.side_effect = HttpRequestError(
            url="https://example.com/contratos/500112",
            status_code=500,
            message="Server error",
        )

        result = processor.process("500112")

        assert result.success is False
        assert result.contract_id == "500112"
        assert result.attachments_downloaded == 0
        assert result.error is not None
        assert "Server error" in result.error

        # No further processing should occur
        detail_parser.parse.assert_not_called()
        attachment_downloader.download.assert_not_called()
        metadata_writer.write.assert_not_called()

    def test_404_response_returns_failure_without_retry(self) -> None:
        """A 404 response returns a failure result and skips the contract."""
        (
            processor,
            http_client,
            detail_parser,
            attachment_downloader,
            metadata_writer,
            output_manager,
        ) = _make_processor()

        http_client.get.return_value = HttpResponse(
            status_code=404, text="Not Found", headers={}, content=b""
        )

        result = processor.process("999999")

        assert result.success is False
        assert result.contract_id == "999999"
        assert result.attachments_downloaded == 0
        assert result.error is not None
        assert "404" in result.error

        # No parsing or downloading should occur
        detail_parser.parse.assert_not_called()
        attachment_downloader.download.assert_not_called()
        metadata_writer.write.assert_not_called()


class TestContractProcessorParsingErrors:
    """Tests for parsing error handling during contract processing."""

    def test_parsing_error_returns_failure(self) -> None:
        """When ParsingError is raised, process returns a failure result."""
        (
            processor,
            http_client,
            detail_parser,
            attachment_downloader,
            metadata_writer,
            output_manager,
        ) = _make_processor()

        http_client.get.return_value = HttpResponse(
            status_code=200, text="<html>bad page</html>", headers={}, content=b""
        )

        detail_parser.parse.side_effect = ParsingError(
            contract_id="500112",
            field="orgao",
            message="Required field 'orgao' not found in detail page",
        )

        result = processor.process("500112")

        assert result.success is False
        assert result.contract_id == "500112"
        assert result.attachments_downloaded == 0
        assert result.error is not None
        assert "orgao" in result.error

        # No attachment downloading or metadata writing should occur
        attachment_downloader.download.assert_not_called()
        metadata_writer.write.assert_not_called()


class TestContractProcessorAttachmentFailures:
    """Tests for attachment download failure handling."""

    def test_partial_attachment_failure_still_succeeds(self) -> None:
        """When some attachments fail to download, processing still succeeds
        with the successfully downloaded attachments."""
        (
            processor,
            http_client,
            detail_parser,
            attachment_downloader,
            metadata_writer,
            output_manager,
        ) = _make_processor()

        http_client.get.return_value = HttpResponse(
            status_code=200, text="<html></html>", headers={}, content=b""
        )

        metadata = _make_metadata("500112")
        detail_parser.parse.return_value = metadata
        detail_parser.parse_attachment_urls.return_value = [
            "https://example.com/files/contrato.pdf",
            "https://example.com/files/aditivo.pdf",
            "https://example.com/files/termo.pdf",
        ]

        output_manager.get_contract_dir.return_value = "/output/org/ug/500112"

        # First succeeds, second fails, third succeeds
        attachment_downloader.download.side_effect = [
            "/output/org/ug/500112/contrato.pdf",
            None,  # Failed download
            "/output/org/ug/500112/termo.pdf",
        ]

        metadata_writer.write.return_value = "/output/org/ug/500112/metadata.json"

        result = processor.process("500112")

        assert result.success is True
        assert result.contract_id == "500112"
        assert result.attachments_downloaded == 2
        assert result.error is None

        # All three downloads were attempted
        assert attachment_downloader.download.call_count == 3

        # Metadata should only contain the successfully downloaded files
        written_metadata = metadata_writer.write.call_args[0][0]
        assert written_metadata.attachments == ["contrato.pdf", "termo.pdf"]

    def test_all_attachments_fail_still_succeeds(self) -> None:
        """When all attachments fail to download, processing still succeeds
        with zero attachments."""
        (
            processor,
            http_client,
            detail_parser,
            attachment_downloader,
            metadata_writer,
            output_manager,
        ) = _make_processor()

        http_client.get.return_value = HttpResponse(
            status_code=200, text="<html></html>", headers={}, content=b""
        )

        metadata = _make_metadata("500112")
        detail_parser.parse.return_value = metadata
        detail_parser.parse_attachment_urls.return_value = [
            "https://example.com/files/contrato.pdf",
        ]

        output_manager.get_contract_dir.return_value = "/output/org/ug/500112"
        attachment_downloader.download.return_value = None

        metadata_writer.write.return_value = "/output/org/ug/500112/metadata.json"

        result = processor.process("500112")

        assert result.success is True
        assert result.contract_id == "500112"
        assert result.attachments_downloaded == 0

        # Metadata should have empty attachments list
        written_metadata = metadata_writer.write.call_args[0][0]
        assert written_metadata.attachments == []
