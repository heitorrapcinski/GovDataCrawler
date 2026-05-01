"""Integration tests for multi-page navigation with mocked HTTP."""

import logging

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


def _build_detail_html(orgao: str, unidade_gestora: str) -> str:
    """Build a minimal detail page HTML."""
    fields = {
        "Órgão": orgao,
        "Unidade Gestora": unidade_gestora,
        "Número do Contrato": "01/2024",
        "Fornecedor": "Empresa XYZ Ltda",
        "Valor do Contrato": "R$ 100.000,00",
        "Data de Início": "2024-01-01",
        "Data de Término": "2024-12-31",
        "Objeto": "Servicos gerais",
    }
    field_groups = ""
    for label, val in fields.items():
        field_groups += (
            f'<div class="field-group">'
            f'<span class="field-label">{label}:</span>'
            f'<span class="field-value">{val}</span>'
            f"</div>\n"
        )
    return f"<html><body>\n{field_groups}\n</body></html>"


def _create_orchestrator(tmp_path) -> CrawlOrchestrator:
    """Create a fully wired CrawlOrchestrator with zero-delay HTTP client."""
    logger = logging.getLogger("test_pagination")
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
    stop_checker = StopConditionChecker(logger=logger)

    return CrawlOrchestrator(
        listing_navigator=listing_navigator,
        contract_processor=contract_processor,
        summary_reporter=summary_reporter,
        stop_condition_checker=stop_checker,
        output_dir=output_dir,
        logger=logger,
    )


class TestMultiPageNavigation:
    """Integration tests for multi-page listing navigation."""

    @responses.activate
    def test_two_page_crawl(self, tmp_path):
        """Contracts from two listing pages are all processed."""
        # Page 1 with next link
        responses.add(
            responses.GET,
            LISTING_URL,
            body=_build_listing_html(
                ["100", "200"],
                next_page_url="/transparencia/contratos?page=2",
            ),
            status=200,
        )
        # Page 2 (last page)
        responses.add(
            responses.GET,
            f"{LISTING_URL}?page=2",
            body=_build_listing_html(["300", "400"]),
            status=200,
        )
        # Detail pages for all contracts
        for cid in ["100", "200", "300", "400"]:
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

        assert summary.successful == 4
        assert summary.total_contracts == 4

    @responses.activate
    def test_three_page_crawl(self, tmp_path):
        """Contracts from three listing pages are all processed."""
        # Page 1
        responses.add(
            responses.GET,
            LISTING_URL,
            body=_build_listing_html(
                ["100"],
                next_page_url="/transparencia/contratos?page=2",
            ),
            status=200,
        )
        # Page 2
        responses.add(
            responses.GET,
            f"{LISTING_URL}?page=2",
            body=_build_listing_html(
                ["200"],
                next_page_url="/transparencia/contratos?page=3",
            ),
            status=200,
        )
        # Page 3 (last)
        responses.add(
            responses.GET,
            f"{LISTING_URL}?page=3",
            body=_build_listing_html(["300"]),
            status=200,
        )
        # Detail pages
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
        assert summary.total_contracts == 3

    @responses.activate
    def test_duplicate_ids_across_pages_are_deduplicated(self, tmp_path):
        """Duplicate contract IDs across pages are processed only once."""
        # Page 1 has contract 100
        responses.add(
            responses.GET,
            LISTING_URL,
            body=_build_listing_html(
                ["100"],
                next_page_url="/transparencia/contratos?page=2",
            ),
            status=200,
        )
        # Page 2 also has contract 100 plus 200
        responses.add(
            responses.GET,
            f"{LISTING_URL}?page=2",
            body=_build_listing_html(["100", "200"]),
            status=200,
        )
        # Detail pages
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

        # Contract 100 should only be processed once
        assert summary.successful == 2
        assert summary.total_contracts == 2

    @responses.activate
    def test_single_page_no_pagination(self, tmp_path):
        """A single listing page with no next link processes all contracts."""
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
        assert summary.total_contracts == 2

    @responses.activate
    def test_mixed_success_and_failure_across_pages(self, tmp_path):
        """Failures on one page do not prevent processing contracts from other pages."""
        # Page 1
        responses.add(
            responses.GET,
            LISTING_URL,
            body=_build_listing_html(
                ["100"],
                next_page_url="/transparencia/contratos?page=2",
            ),
            status=200,
        )
        # Page 2
        responses.add(
            responses.GET,
            f"{LISTING_URL}?page=2",
            body=_build_listing_html(["200"]),
            status=200,
        )
        # Contract 100 fails
        responses.add(
            responses.GET,
            f"{LISTING_URL}/100",
            body="Not Found",
            status=404,
        )
        # Contract 200 succeeds
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
