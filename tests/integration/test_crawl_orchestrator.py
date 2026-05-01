"""Integration tests for CrawlOrchestrator with mocked HTTP responses."""

import json
import logging
import os

import responses

from gov_data_crawler.attachments import AttachmentDownloader
from gov_data_crawler.delay import DelayMechanism
from gov_data_crawler.detail_parser import DetailParser
from gov_data_crawler.http_client import HttpClient
from gov_data_crawler.listing import ListingNavigator, ListingParser
from gov_data_crawler.metadata import MetadataWriter
from gov_data_crawler.orchestrator import CrawlOrchestrator
from gov_data_crawler.output import OutputManager
from gov_data_crawler.processor import ContractProcessor
from gov_data_crawler.stop_condition import StopConditionChecker
from gov_data_crawler.summary import SummaryReporter

BASE_URL = "https://contratos.comprasnet.gov.br"
LISTING_URL = f"{BASE_URL}/transparencia/contratos"


def _build_listing_html(
    contract_ids: list[str], next_page_url: str | None = None
) -> str:
    """Build a listing page HTML with contract links and optional next page."""
    links = "\n".join(
        f'<a href="/transparencia/contratos/{cid}">Contract {cid}</a>'
        for cid in contract_ids
    )
    next_link = ""
    if next_page_url:
        next_link = f'<a rel="next" href="{next_page_url}">Next</a>'
    return f"<html><body>\n{links}\n{next_link}\n</body></html>"


def _build_detail_html(
    orgao: str,
    unidade_gestora: str,
    contract_number: str = "01/2024",
    supplier: str = "Empresa XYZ Ltda",
    value: str = "R$ 100.000,00",
    start_date: str = "2024-01-01",
    end_date: str = "2024-12-31",
    obj_desc: str = "Servicos gerais",
    attachments: list[tuple[str, str]] | None = None,
) -> str:
    """Build a detail page HTML with field-group divs."""
    fields = {
        "Órgão": orgao,
        "Unidade Gestora": unidade_gestora,
        "Número do Contrato": contract_number,
        "Fornecedor": supplier,
        "Valor do Contrato": value,
        "Data de Início": start_date,
        "Data de Término": end_date,
        "Objeto": obj_desc,
    }
    field_groups = ""
    for label, val in fields.items():
        field_groups += (
            f'<div class="field-group">'
            f'<span class="field-label">{label}:</span>'
            f'<span class="field-value">{val}</span>'
            f"</div>\n"
        )

    attachment_section = ""
    if attachments:
        att_links = "\n".join(
            f'<a href="{href}">{text}</a>' for href, text in attachments
        )
        attachment_section = f'<div class="attachments">\n{att_links}\n</div>'

    return f"<html><body>\n{field_groups}\n{attachment_section}\n</body></html>"


def _create_orchestrator(
    tmp_path,
    max_time: float | None = None,
    max_contracts: int | None = None,
) -> CrawlOrchestrator:
    """Create a fully wired CrawlOrchestrator with zero-delay HTTP client."""
    logger = logging.getLogger("test_orchestrator")
    logger.setLevel(logging.DEBUG)

    output_dir = str(tmp_path / "output")
    delay = DelayMechanism(min_seconds=0.0, max_seconds=0.0)
    http_client = HttpClient(delay_mechanism=delay, logger=logger)
    output_manager = OutputManager(base_dir=output_dir)

    listing_parser = ListingParser()
    listing_navigator = ListingNavigator(
        http_client=http_client,
        parser=listing_parser,
        base_url=LISTING_URL,
        logger=logger,
    )

    detail_parser = DetailParser()
    attachment_downloader = AttachmentDownloader(
        http_client=http_client, logger=logger
    )
    metadata_writer = MetadataWriter()

    contract_processor = ContractProcessor(
        http_client=http_client,
        detail_parser=detail_parser,
        attachment_downloader=attachment_downloader,
        metadata_writer=metadata_writer,
        output_manager=output_manager,
        logger=logger,
    )

    summary_reporter = SummaryReporter(logger=logger)
    stop_checker = StopConditionChecker(
        max_time=max_time,
        max_contracts=max_contracts,
        logger=logger,
    )

    return CrawlOrchestrator(
        listing_navigator=listing_navigator,
        contract_processor=contract_processor,
        summary_reporter=summary_reporter,
        stop_condition_checker=stop_checker,
        output_dir=output_dir,
        logger=logger,
    )


class TestFullCrawlLifecycle:
    """Integration tests for the full crawl lifecycle."""

    @responses.activate
    def test_crawl_single_contract(self, tmp_path):
        """A crawl with one contract produces metadata on disk."""
        # Mock listing page
        responses.add(
            responses.GET,
            LISTING_URL,
            body=_build_listing_html(["100"]),
            status=200,
        )
        # Mock detail page
        responses.add(
            responses.GET,
            f"{LISTING_URL}/100",
            body=_build_detail_html(
                orgao="Ministerio da Defesa",
                unidade_gestora="160089 - Base de Apoio",
            ),
            status=200,
        )

        orchestrator = _create_orchestrator(tmp_path)
        summary = orchestrator.run()

        assert summary.successful == 1
        assert summary.failed == 0
        assert summary.skipped == 0
        assert summary.total_contracts == 1
        assert summary.stopped_by is None

    @responses.activate
    def test_crawl_multiple_contracts(self, tmp_path):
        """A crawl with multiple contracts processes all of them."""
        responses.add(
            responses.GET,
            LISTING_URL,
            body=_build_listing_html(["100", "200", "300"]),
            status=200,
        )
        for cid in ["100", "200", "300"]:
            responses.add(
                responses.GET,
                f"{LISTING_URL}/{cid}",
                body=_build_detail_html(
                    orgao="Ministerio da Defesa",
                    unidade_gestora=f"UG-{cid}",
                ),
                status=200,
            )

        orchestrator = _create_orchestrator(tmp_path)
        summary = orchestrator.run()

        assert summary.successful == 3
        assert summary.failed == 0
        assert summary.total_contracts == 3

    @responses.activate
    def test_crawl_with_detail_failure(self, tmp_path):
        """A contract that returns 404 is recorded as a failure."""
        responses.add(
            responses.GET,
            LISTING_URL,
            body=_build_listing_html(["100", "200"]),
            status=200,
        )
        responses.add(
            responses.GET,
            f"{LISTING_URL}/100",
            body="Not Found",
            status=404,
        )
        responses.add(
            responses.GET,
            f"{LISTING_URL}/200",
            body=_build_detail_html(
                orgao="Ministerio da Defesa",
                unidade_gestora="UG-200",
            ),
            status=200,
        )

        orchestrator = _create_orchestrator(tmp_path)
        summary = orchestrator.run()

        assert summary.successful == 1
        assert summary.failed == 1
        assert summary.total_contracts == 2

    @responses.activate
    def test_crawl_with_attachments(self, tmp_path):
        """Attachments are downloaded and recorded in metadata."""
        responses.add(
            responses.GET,
            LISTING_URL,
            body=_build_listing_html(["100"]),
            status=200,
        )
        responses.add(
            responses.GET,
            f"{LISTING_URL}/100",
            body=_build_detail_html(
                orgao="Ministerio da Defesa",
                unidade_gestora="UG-100",
                attachments=[
                    ("/download/doc1.pdf", "doc1.pdf"),
                    ("/download/doc2.pdf", "doc2.pdf"),
                ],
            ),
            status=200,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}/download/doc1.pdf",
            body=b"PDF content 1",
            status=200,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}/download/doc2.pdf",
            body=b"PDF content 2",
            status=200,
        )

        orchestrator = _create_orchestrator(tmp_path)
        summary = orchestrator.run()

        assert summary.successful == 1
        assert summary.attachments_downloaded == 2

    @responses.activate
    def test_crawl_resumes_skipping_processed(self, tmp_path):
        """Already-processed contracts are skipped on resume."""
        output_dir = str(tmp_path / "output")

        # Pre-create a processed contract on disk
        contract_dir = os.path.join(
            output_dir, "Ministerio_da_Defesa", "UG-100", "100"
        )
        os.makedirs(contract_dir, exist_ok=True)
        metadata = {"contract_id": "100", "orgao": "Ministerio da Defesa"}
        with open(
            os.path.join(contract_dir, "metadata.json"), "w", encoding="utf-8"
        ) as f:
            json.dump(metadata, f)

        # Mock listing with both contracts
        responses.add(
            responses.GET,
            LISTING_URL,
            body=_build_listing_html(["100", "200"]),
            status=200,
        )
        responses.add(
            responses.GET,
            f"{LISTING_URL}/200",
            body=_build_detail_html(
                orgao="Ministerio da Defesa",
                unidade_gestora="UG-200",
            ),
            status=200,
        )

        orchestrator = _create_orchestrator(tmp_path)
        summary = orchestrator.run()

        assert summary.skipped == 1
        assert summary.successful == 1
        assert summary.total_contracts == 2

    @responses.activate
    def test_empty_listing_produces_empty_summary(self, tmp_path):
        """An empty listing page produces a summary with zero counts."""
        responses.add(
            responses.GET,
            LISTING_URL,
            body=_build_listing_html([]),
            status=200,
        )

        orchestrator = _create_orchestrator(tmp_path)
        summary = orchestrator.run()

        assert summary.total_contracts == 0
        assert summary.successful == 0
        assert summary.failed == 0
        assert summary.skipped == 0


class TestStopConditionScenarios:
    """Integration tests for stop condition behavior."""

    @responses.activate
    def test_max_contracts_stops_crawl(self, tmp_path):
        """Crawl stops after reaching max_contracts limit."""
        responses.add(
            responses.GET,
            LISTING_URL,
            body=_build_listing_html(["100", "200", "300"]),
            status=200,
        )
        for cid in ["100", "200", "300"]:
            responses.add(
                responses.GET,
                f"{LISTING_URL}/{cid}",
                body=_build_detail_html(
                    orgao="Ministerio da Defesa",
                    unidade_gestora=f"UG-{cid}",
                ),
                status=200,
            )

        orchestrator = _create_orchestrator(tmp_path, max_contracts=2)
        summary = orchestrator.run()

        assert summary.successful == 2
        assert summary.stopped_by == "max_contracts"

    @responses.activate
    def test_max_time_stops_crawl(self, tmp_path):
        """Crawl stops after exceeding max_time limit."""
        responses.add(
            responses.GET,
            LISTING_URL,
            body=_build_listing_html(["100", "200", "300"]),
            status=200,
        )
        for cid in ["100", "200", "300"]:
            responses.add(
                responses.GET,
                f"{LISTING_URL}/{cid}",
                body=_build_detail_html(
                    orgao="Ministerio da Defesa",
                    unidade_gestora=f"UG-{cid}",
                ),
                status=200,
            )

        # Use a very small max_time so it triggers quickly
        orchestrator = _create_orchestrator(tmp_path, max_time=0.0)
        summary = orchestrator.run()

        # At least one contract should be processed before stop is checked
        assert summary.successful >= 1
        assert summary.stopped_by == "max_time"

    @responses.activate
    def test_no_stop_conditions_processes_all(self, tmp_path):
        """Without stop conditions, all contracts are processed."""
        responses.add(
            responses.GET,
            LISTING_URL,
            body=_build_listing_html(["100", "200"]),
            status=200,
        )
        for cid in ["100", "200"]:
            responses.add(
                responses.GET,
                f"{LISTING_URL}/{cid}",
                body=_build_detail_html(
                    orgao="Ministerio da Defesa",
                    unidade_gestora=f"UG-{cid}",
                ),
                status=200,
            )

        orchestrator = _create_orchestrator(tmp_path)
        summary = orchestrator.run()

        assert summary.successful == 2
        assert summary.stopped_by is None

    @responses.activate
    def test_max_contracts_with_failures(self, tmp_path):
        """max_contracts counts only successful contracts, not failures."""
        responses.add(
            responses.GET,
            LISTING_URL,
            body=_build_listing_html(["100", "200", "300"]),
            status=200,
        )
        # First contract fails (404)
        responses.add(
            responses.GET,
            f"{LISTING_URL}/100",
            body="Not Found",
            status=404,
        )
        # Second and third succeed
        for cid in ["200", "300"]:
            responses.add(
                responses.GET,
                f"{LISTING_URL}/{cid}",
                body=_build_detail_html(
                    orgao="Ministerio da Defesa",
                    unidade_gestora=f"UG-{cid}",
                ),
                status=200,
            )

        orchestrator = _create_orchestrator(tmp_path, max_contracts=2)
        summary = orchestrator.run()

        assert summary.successful == 2
        assert summary.failed == 1
        assert summary.stopped_by == "max_contracts"
