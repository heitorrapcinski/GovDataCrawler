"""Listing page parser and navigator for ComprasNet contract listings."""

import logging
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from gov_data_crawler.http_client import HttpClient

BASE_URL = "https://contratos.comprasnet.gov.br"
LISTING_PATH = "/transparencia/contratos"
CONTRACT_DETAIL_URL_TEMPLATE = f"{BASE_URL}{LISTING_PATH}/{{}}"

# Pattern to match contract detail links: /transparencia/contratos/{numeric_id}
CONTRACT_LINK_PATTERN = re.compile(r"^/transparencia/contratos/(\d+)$")


class ListingParser:
    """Extracts contract IDs and pagination links from listing HTML."""

    def parse_contract_ids(self, html: str) -> list[str]:
        """Extract all contract IDs from a listing page.

        Finds all anchor tags whose href matches the contract detail URL
        pattern and extracts the numeric contract ID from each.

        Args:
            html: Raw HTML of a contract listing page.

        Returns:
            List of unique contract ID strings found on the page,
            preserving first-occurrence order.
        """
        soup = BeautifulSoup(html, "lxml")
        seen: set[str] = set()
        contract_ids: list[str] = []

        for link in soup.find_all("a", href=True):
            match = CONTRACT_LINK_PATTERN.match(link["href"])
            if match:
                contract_id = match.group(1)
                if contract_id not in seen:
                    seen.add(contract_id)
                    contract_ids.append(contract_id)

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
            # Ensure the URL is absolute
            return urljoin(BASE_URL, href)

        return None


class ListingNavigator:
    """Navigates all pages of the contract listing."""

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
            parser: Parser for extracting data from listing HTML.
            base_url: The starting URL for the contract listing.
            logger: Logger instance for progress messages.
        """
        self._http_client = http_client
        self._parser = parser
        self._base_url = base_url
        self._logger = logger

    def collect_all_contract_ids(self) -> list[str]:
        """Navigate all listing pages and collect every contract ID.

        Starts from the base URL and follows next-page links until no
        more pages are available.

        Returns:
            Complete list of unique contract IDs across all pages,
            preserving discovery order.
        """
        all_ids: list[str] = []
        seen: set[str] = set()
        current_url: str | None = self._base_url
        page_number = 1

        while current_url is not None:
            self._logger.info("Fetching listing page %d: %s", page_number, current_url)
            response = self._http_client.get(current_url)
            page_ids = self._parser.parse_contract_ids(response.text)

            new_count = 0
            for cid in page_ids:
                if cid not in seen:
                    seen.add(cid)
                    all_ids.append(cid)
                    new_count += 1

            self._logger.info(
                "Page %d: found %d contract IDs (%d new)",
                page_number,
                len(page_ids),
                new_count,
            )

            current_url = self._parser.parse_next_page_url(response.text)
            page_number += 1

        self._logger.info(
            "Listing navigation complete: %d total contract IDs collected",
            len(all_ids),
        )
        return all_ids
