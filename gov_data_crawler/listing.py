"""Listing page parser and navigator for ComprasNet contract listings."""

import json
import logging
import re
from dataclasses import dataclass
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from gov_data_crawler.http_client import HttpClient

BASE_URL = "https://contratos.comprasnet.gov.br"
LISTING_PATH = "/transparencia/contratos"
SEARCH_PATH = f"{LISTING_PATH}/search"
CONTRACT_DETAIL_URL_TEMPLATE = f"{BASE_URL}{LISTING_PATH}/{{}}"

# Pattern to match contract detail links: /transparencia/contratos/{numeric_id}
# Works for both relative and absolute URLs.
CONTRACT_LINK_PATTERN = re.compile(
    r"(?:https?://[^/]+)?/transparencia/contratos/(\d+)"
)

# Default page size for DataTables server-side requests.
DEFAULT_PAGE_SIZE = 25


@dataclass(frozen=True)
class FilterParameters:
    """Immutable container for optional listing filters.

    Attributes:
        orgao: Government organ number to filter by, or None.
        categoria: Contract category to filter by, or None.
    """

    orgao: str | None = None
    categoria: str | None = None

    @property
    def has_filters(self) -> bool:
        """Return True if at least one filter is set."""
        return self.orgao is not None or self.categoria is not None

    def to_post_params(self) -> dict[str, str]:
        """Convert active filters to a dict suitable for POST data.

        Returns:
            Dict with only the non-None filter values.
        """
        params: dict[str, str] = {}
        if self.orgao is not None:
            params["orgao"] = self.orgao
        if self.categoria is not None:
            params["categoria"] = self.categoria
        return params

    def to_query_params(self) -> dict[str, str]:
        """Convert active filters to a dict suitable for URL query parameters.

        Returns:
            Dict with only the non-None filter values.
        """
        return self.to_post_params()


class ListingParser:
    """Extracts contract IDs from listing HTML or DataTables JSON responses."""

    def parse_contract_ids(self, html: str) -> list[str]:
        """Extract all contract IDs from HTML content.

        Finds all anchor tags whose href matches the contract detail URL
        pattern and extracts the numeric contract ID from each.  This works
        for both full listing pages and HTML fragments returned inside
        DataTables JSON responses.

        Args:
            html: Raw HTML (full page or fragment) containing contract links.

        Returns:
            List of unique contract ID strings found, preserving
            first-occurrence order.
        """
        soup = BeautifulSoup(html, "lxml")
        seen: set[str] = set()
        contract_ids: list[str] = []

        for link in soup.find_all("a", href=True):
            match = CONTRACT_LINK_PATTERN.search(link["href"])
            if match:
                contract_id = match.group(1)
                if contract_id not in seen:
                    seen.add(contract_id)
                    contract_ids.append(contract_id)

        return contract_ids

    def parse_contract_ids_from_json(self, json_data: dict) -> list[str]:
        """Extract contract IDs from a DataTables server-side JSON response.

        The ComprasNet portal uses jQuery DataTables with server-side
        processing.  Each row in ``json_data["data"]`` is a list of HTML
        fragments.  The last column typically contains an anchor tag
        pointing to the contract detail page.

        Args:
            json_data: Parsed JSON dict from the DataTables ``/search``
                endpoint.

        Returns:
            List of unique contract ID strings found in the response,
            preserving first-occurrence order.
        """
        rows = json_data.get("data", [])
        seen: set[str] = set()
        contract_ids: list[str] = []

        for row in rows:
            # Scan all columns in the row for contract detail links.
            # The link is usually in the last column (actions), but we
            # check every column for robustness.
            for cell in row:
                if not isinstance(cell, str):
                    continue
                match = CONTRACT_LINK_PATTERN.search(cell)
                if match:
                    contract_id = match.group(1)
                    if contract_id not in seen:
                        seen.add(contract_id)
                        contract_ids.append(contract_id)
                    # One ID per row is enough; move to the next row.
                    break

        return contract_ids

    def parse_next_page_url(self, html: str) -> str | None:
        """Extract the URL of the next listing page, if any.

        Looks for an anchor tag with rel="next" attribute, which is the
        standard pagination pattern used by the ComprasNet portal.

        Args:
            html: Raw HTML of a contract listing page.

        Returns:
            Absolute URL of the next page, or None if this is the last page.
        """
        soup = BeautifulSoup(html, "lxml")
        next_link = soup.find("a", rel="next")

        if next_link and next_link.get("href"):
            href = next_link["href"]
            return urljoin(BASE_URL, href)

        return None

    @staticmethod
    def extract_csrf_token(html: str) -> str | None:
        """Extract the CSRF token from a page's meta tag.

        The ComprasNet portal embeds a CSRF token in a
        ``<meta name="csrf-token" content="...">`` tag that must be
        included in POST requests.

        Args:
            html: Raw HTML of any page on the portal.

        Returns:
            The CSRF token string, or None if not found.
        """
        match = re.search(
            r'<meta\s+name="csrf-token"\s+content="([^"]+)"', html
        )
        return match.group(1) if match else None


class ListingNavigator:
    """Navigates all pages of the contract listing via the DataTables API."""

    def __init__(
        self,
        http_client: HttpClient,
        parser: ListingParser,
        base_url: str,
        logger: logging.Logger,
    ) -> None:
        """Initialize the listing navigator.

        Args:
            http_client: HTTP client for fetching pages.
            parser: Parser for extracting data from listing HTML / JSON.
            base_url: The starting URL for the contract listing.
            logger: Logger instance for progress messages.
        """
        self._http_client = http_client
        self._parser = parser
        self._base_url = base_url
        self._logger = logger

    def collect_all_contract_ids(self, max_ids: int | None = None) -> list[str]:
        """Collect contract IDs using the DataTables server-side API.

        1. Fetches the listing page via GET to obtain the CSRF token.
        2. POSTs to the ``/search`` endpoint with DataTables pagination
           parameters, iterating through pages until all IDs are collected
           or ``max_ids`` is reached.

        If the CSRF token cannot be obtained (e.g. the page structure
        changed), falls back to the legacy HTML-scraping approach.

        Args:
            max_ids: Optional upper limit on the number of IDs to collect.
                When set, pagination stops as soon as this many unique IDs
                have been gathered.  Useful to avoid fetching hundreds of
                thousands of IDs when only a small batch is needed.

        Returns:
            Complete list of unique contract IDs, preserving discovery order.
        """
        # Step 1: GET the listing page to obtain the CSRF token.
        self._logger.info("Fetching listing page to obtain CSRF token: %s", self._base_url)
        initial_response = self._http_client.get(self._base_url)
        csrf_token = self._parser.extract_csrf_token(initial_response.text)

        if csrf_token is None:
            self._logger.warning(
                "CSRF token not found; falling back to HTML scraping"
            )
            return self._collect_via_html_scraping(initial_response.text, max_ids)

        self._logger.debug("CSRF token obtained successfully")

        # Step 2: Use the DataTables server-side API to paginate.
        return self._collect_via_datatables_api(csrf_token, max_ids)

    def _collect_via_datatables_api(
        self, csrf_token: str, max_ids: int | None = None
    ) -> list[str]:
        """Paginate through the DataTables ``/search`` endpoint.

        Args:
            csrf_token: CSRF token extracted from the initial page load.
            max_ids: Optional cap on the number of IDs to collect.

        Returns:
            List of unique contract IDs across all pages.
        """
        search_url = f"{BASE_URL}{SEARCH_PATH}"
        all_ids: list[str] = []
        seen: set[str] = set()
        draw = 1
        start = 0
        page_size = DEFAULT_PAGE_SIZE

        headers = {
            "X-CSRF-TOKEN": csrf_token,
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json",
        }

        while True:
            page_number = (start // page_size) + 1
            self._logger.info(
                "Fetching listing page %d via API (start=%d, length=%d)",
                page_number,
                start,
                page_size,
            )

            post_data = {
                "draw": str(draw),
                "start": str(start),
                "length": str(page_size),
            }

            response = self._http_client.post(
                search_url, data=post_data, headers=headers
            )

            try:
                json_data = json.loads(response.text)
            except json.JSONDecodeError:
                self._logger.error(
                    "Failed to parse JSON from search API (status=%d); "
                    "stopping pagination",
                    response.status_code,
                )
                break

            page_ids = self._parser.parse_contract_ids_from_json(json_data)

            new_count = 0
            for cid in page_ids:
                if cid not in seen:
                    seen.add(cid)
                    all_ids.append(cid)
                    new_count += 1

            records_filtered = json_data.get("recordsFiltered", 0)

            self._logger.info(
                "Page %d: found %d contract IDs (%d new) — %d / %d total",
                page_number,
                len(page_ids),
                new_count,
                len(all_ids),
                records_filtered,
            )

            # Stop if we received fewer rows than requested (last page)
            # or if we have collected all filtered records.
            if len(page_ids) == 0 or start + page_size >= records_filtered:
                break

            # Stop if we have collected enough IDs.
            if max_ids is not None and len(all_ids) >= max_ids:
                self._logger.info(
                    "Reached max_ids limit (%d); stopping collection", max_ids
                )
                break

            start += page_size
            draw += 1

        self._logger.info(
            "Listing navigation complete: %d total contract IDs collected",
            len(all_ids),
        )
        return all_ids

    def _collect_via_html_scraping(
        self, initial_html: str, max_ids: int | None = None
    ) -> list[str]:
        """Legacy fallback: scrape contract IDs from rendered HTML pages.

        Used when the CSRF token cannot be obtained and the DataTables
        API is unavailable.

        Args:
            initial_html: HTML of the first listing page (already fetched).
            max_ids: Optional cap on the number of IDs to collect.

        Returns:
            List of unique contract IDs across all pages.
        """
        all_ids: list[str] = []
        seen: set[str] = set()
        page_number = 1

        # Process the already-fetched first page.
        page_ids = self._parser.parse_contract_ids(initial_html)
        for cid in page_ids:
            if cid not in seen:
                seen.add(cid)
                all_ids.append(cid)

        self._logger.info(
            "Page %d (HTML fallback): found %d contract IDs (%d new)",
            page_number,
            len(page_ids),
            len(all_ids),
        )

        current_url = self._parser.parse_next_page_url(initial_html)

        if max_ids is not None and len(all_ids) >= max_ids:
            self._logger.info(
                "Listing navigation complete: %d total contract IDs collected",
                len(all_ids),
            )
            return all_ids

        page_number += 1

        while current_url is not None:
            self._logger.info(
                "Fetching listing page %d: %s", page_number, current_url
            )
            response = self._http_client.get(current_url)
            page_ids = self._parser.parse_contract_ids(response.text)

            new_count = 0
            for cid in page_ids:
                if cid not in seen:
                    seen.add(cid)
                    all_ids.append(cid)
                    new_count += 1

            self._logger.info(
                "Page %d (HTML fallback): found %d contract IDs (%d new)",
                page_number,
                len(page_ids),
                new_count,
            )

            if max_ids is not None and len(all_ids) >= max_ids:
                break

            current_url = self._parser.parse_next_page_url(response.text)
            page_number += 1

        self._logger.info(
            "Listing navigation complete: %d total contract IDs collected",
            len(all_ids),
        )
        return all_ids
