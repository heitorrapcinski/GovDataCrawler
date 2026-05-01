"""Unit tests for the ListingParser and ListingNavigator components."""

import logging
from unittest.mock import MagicMock, call

from gov_data_crawler.http_client import HttpClient, HttpResponse
from gov_data_crawler.listing import ListingNavigator, ListingParser


class TestListingParserContractIds:
    """Tests for ListingParser.parse_contract_ids."""

    def test_extracts_single_contract_id(self) -> None:
        """A page with one contract link yields one contract ID."""
        html = """
        <html><body>
            <a href="/transparencia/contratos/500112">Contract 500112</a>
        </body></html>
        """
        parser = ListingParser()
        ids = parser.parse_contract_ids(html)
        assert ids == ["500112"]

    def test_extracts_multiple_contract_ids(self) -> None:
        """A page with multiple contract links yields all contract IDs."""
        html = """
        <html><body>
            <a href="/transparencia/contratos/500112">Contract 500112</a>
            <a href="/transparencia/contratos/500113">Contract 500113</a>
            <a href="/transparencia/contratos/500114">Contract 500114</a>
        </body></html>
        """
        parser = ListingParser()
        ids = parser.parse_contract_ids(html)
        assert ids == ["500112", "500113", "500114"]

    def test_deduplicates_contract_ids(self) -> None:
        """Duplicate contract links on the same page produce unique IDs."""
        html = """
        <html><body>
            <a href="/transparencia/contratos/500112">Contract 500112</a>
            <a href="/transparencia/contratos/500112">Contract 500112 (duplicate)</a>
            <a href="/transparencia/contratos/500113">Contract 500113</a>
        </body></html>
        """
        parser = ListingParser()
        ids = parser.parse_contract_ids(html)
        assert ids == ["500112", "500113"]

    def test_ignores_non_contract_links(self) -> None:
        """Links that do not match the contract URL pattern are ignored."""
        html = """
        <html><body>
            <a href="/transparencia/contratos/500112">Contract 500112</a>
            <a href="/transparencia/outros/123">Other link</a>
            <a href="/about">About</a>
            <a href="https://external.com">External</a>
        </body></html>
        """
        parser = ListingParser()
        ids = parser.parse_contract_ids(html)
        assert ids == ["500112"]

    def test_ignores_non_numeric_ids(self) -> None:
        """Links with non-numeric IDs in the contract path are ignored."""
        html = """
        <html><body>
            <a href="/transparencia/contratos/abc">Not numeric</a>
            <a href="/transparencia/contratos/500112">Valid</a>
        </body></html>
        """
        parser = ListingParser()
        ids = parser.parse_contract_ids(html)
        assert ids == ["500112"]

    def test_empty_page_returns_empty_list(self) -> None:
        """A page with no contract links returns an empty list."""
        html = """
        <html><body>
            <p>No contracts available.</p>
        </body></html>
        """
        parser = ListingParser()
        ids = parser.parse_contract_ids(html)
        assert ids == []

    def test_page_with_no_links_returns_empty_list(self) -> None:
        """A page with no anchor tags at all returns an empty list."""
        html = "<html><body><p>Empty page</p></body></html>"
        parser = ListingParser()
        ids = parser.parse_contract_ids(html)
        assert ids == []


class TestListingParserNextPageUrl:
    """Tests for ListingParser.parse_next_page_url."""

    def test_extracts_next_page_url(self) -> None:
        """A page with a rel='next' link returns the absolute next page URL."""
        html = """
        <html><body>
            <a rel="next" href="/transparencia/contratos?page=2">Next</a>
        </body></html>
        """
        parser = ListingParser()
        url = parser.parse_next_page_url(html)
        assert url == "https://contratos.comprasnet.gov.br/transparencia/contratos?page=2"

    def test_returns_none_on_last_page(self) -> None:
        """A page without a rel='next' link returns None."""
        html = """
        <html><body>
            <a href="/transparencia/contratos?page=1">Previous</a>
        </body></html>
        """
        parser = ListingParser()
        url = parser.parse_next_page_url(html)
        assert url is None

    def test_returns_none_on_empty_page(self) -> None:
        """An empty page returns None for next page URL."""
        html = "<html><body></body></html>"
        parser = ListingParser()
        url = parser.parse_next_page_url(html)
        assert url is None

    def test_handles_absolute_next_url(self) -> None:
        """An absolute URL in the next link is returned as-is."""
        html = """
        <html><body>
            <a rel="next" href="https://contratos.comprasnet.gov.br/transparencia/contratos?page=3">Next</a>
        </body></html>
        """
        parser = ListingParser()
        url = parser.parse_next_page_url(html)
        assert url == "https://contratos.comprasnet.gov.br/transparencia/contratos?page=3"

    def test_ignores_next_link_without_href(self) -> None:
        """A rel='next' link without an href attribute returns None."""
        html = """
        <html><body>
            <a rel="next">Next</a>
        </body></html>
        """
        parser = ListingParser()
        url = parser.parse_next_page_url(html)
        assert url is None


class TestListingNavigator:
    """Tests for ListingNavigator.collect_all_contract_ids."""

    def _make_response(self, html: str) -> HttpResponse:
        """Create an HttpResponse with the given HTML body."""
        return HttpResponse(
            status_code=200,
            text=html,
            headers={"Content-Type": "text/html"},
            content=html.encode("utf-8"),
        )

    def test_single_page_collects_all_ids(self) -> None:
        """A single-page listing collects all contract IDs."""
        html = """
        <html><body>
            <a href="/transparencia/contratos/100">C100</a>
            <a href="/transparencia/contratos/200">C200</a>
        </body></html>
        """
        http_client = MagicMock(spec=HttpClient)
        http_client.get.return_value = self._make_response(html)

        navigator = ListingNavigator(
            http_client=http_client,
            parser=ListingParser(),
            base_url="https://contratos.comprasnet.gov.br/transparencia/contratos",
            logger=logging.getLogger("test"),
        )

        ids = navigator.collect_all_contract_ids()
        assert ids == ["100", "200"]
        http_client.get.assert_called_once()

    def test_multi_page_collects_all_ids(self) -> None:
        """A multi-page listing navigates all pages and collects all IDs."""
        page1 = """
        <html><body>
            <a href="/transparencia/contratos/100">C100</a>
            <a rel="next" href="/transparencia/contratos?page=2">Next</a>
        </body></html>
        """
        page2 = """
        <html><body>
            <a href="/transparencia/contratos/200">C200</a>
            <a rel="next" href="/transparencia/contratos?page=3">Next</a>
        </body></html>
        """
        page3 = """
        <html><body>
            <a href="/transparencia/contratos/300">C300</a>
        </body></html>
        """
        http_client = MagicMock(spec=HttpClient)
        http_client.get.side_effect = [
            self._make_response(page1),
            self._make_response(page2),
            self._make_response(page3),
        ]

        navigator = ListingNavigator(
            http_client=http_client,
            parser=ListingParser(),
            base_url="https://contratos.comprasnet.gov.br/transparencia/contratos",
            logger=logging.getLogger("test"),
        )

        ids = navigator.collect_all_contract_ids()
        assert ids == ["100", "200", "300"]
        assert http_client.get.call_count == 3

    def test_empty_listing_returns_empty_list(self) -> None:
        """An empty listing page returns an empty list."""
        html = "<html><body><p>No contracts.</p></body></html>"
        http_client = MagicMock(spec=HttpClient)
        http_client.get.return_value = self._make_response(html)

        navigator = ListingNavigator(
            http_client=http_client,
            parser=ListingParser(),
            base_url="https://contratos.comprasnet.gov.br/transparencia/contratos",
            logger=logging.getLogger("test"),
        )

        ids = navigator.collect_all_contract_ids()
        assert ids == []

    def test_deduplicates_across_pages(self) -> None:
        """Contract IDs appearing on multiple pages are deduplicated."""
        page1 = """
        <html><body>
            <a href="/transparencia/contratos/100">C100</a>
            <a rel="next" href="/transparencia/contratos?page=2">Next</a>
        </body></html>
        """
        page2 = """
        <html><body>
            <a href="/transparencia/contratos/100">C100 again</a>
            <a href="/transparencia/contratos/200">C200</a>
        </body></html>
        """
        http_client = MagicMock(spec=HttpClient)
        http_client.get.side_effect = [
            self._make_response(page1),
            self._make_response(page2),
        ]

        navigator = ListingNavigator(
            http_client=http_client,
            parser=ListingParser(),
            base_url="https://contratos.comprasnet.gov.br/transparencia/contratos",
            logger=logging.getLogger("test"),
        )

        ids = navigator.collect_all_contract_ids()
        assert ids == ["100", "200"]
