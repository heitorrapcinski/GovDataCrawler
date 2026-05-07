"""Legislation knowledge base fetching and caching module."""

import hashlib
import json
import logging
import os
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from openclaws.models import FetchReport, LegislationSnippet

logger = logging.getLogger(__name__)

# Mapping of URL patterns to human-readable law names
URL_LAW_NAMES: dict[str, str] = {
    "l14133": "Lei 14.133/2021 (Nova Lei de Licitações)",
    "nllc/lista-de-atos-normativos": "Atos Normativos da Lei 14.133/2021",
    "nllc/legislacao-14-133-por-tema": "Legislação 14.133 por Tema",
    "nllc": "Nova Lei de Licitações e Contratos (NLLC)",
    "l13303": "Lei 13.303/2016 (Lei das Estatais)",
    "l8666": "Lei 8.666/1993 (Lei de Licitações)",
    "l10520": "Lei 10.520/2002 (Pregão)",
    "l12462": "Lei 12.462/2011 (RDC)",
    "licitacoes-e-contratos-orientacoes": "TCU - Licitações e Contratos",
    "licitacoes-e-contratacoes": "Portal da Transparência - Licitações",
}

# All 10 legislation URLs from requirements 4.1
LEGISLATION_URLS: list[str] = [
    "https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2021/lei/l14133.htm",
    "https://www.gov.br/compras/pt-br/nllc",
    "https://www.gov.br/compras/pt-br/nllc/lista-de-atos-normativos-e-estagios-de-regulamentacao-da-lei-14133-de-2021.pdf",
    "https://www.gov.br/compras/pt-br/nllc/legislacao-14-133-por-tema",
    "https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2016/lei/l13303.htm",
    "https://www.planalto.gov.br/ccivil_03/leis/l8666cons.htm",
    "https://www.planalto.gov.br/ccivil_03/leis/2002/l10520.htm",
    "https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2011/lei/l12462.htm",
    "https://portal.tcu.gov.br/publicacoes-institucionais/cartilha-manual-ou-tutorial/licitacoes-e-contratos-orientacoes-e-jurisprudencia-do-tcu",
    "https://portaldatransparencia.gov.br/entenda-a-gestao-publica/licitacoes-e-contratacoes",
]


def _url_to_hash(url: str) -> str:
    """Generate a stable hash filename from a URL."""
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def _get_law_name(url: str) -> str:
    """Map a URL to its human-readable law name."""
    for pattern, name in URL_LAW_NAMES.items():
        if pattern in url:
            return name
    return "Legislação Brasileira"


def _extract_text_from_html(html_content: str) -> str:
    """Extract readable text from HTML content."""
    soup = BeautifulSoup(html_content, "lxml")

    # Remove script and style elements
    for element in soup(["script", "style", "nav", "header", "footer"]):
        element.decompose()

    text = soup.get_text(separator="\n", strip=True)

    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text


class LegislationCache:
    """File-based cache for Brazilian procurement legislation content.

    Fetches legislation from predefined URLs and stores the content
    in a file-based cache that survives container restarts.
    """

    def __init__(self, cache_dir: str, timeout: int = 30) -> None:
        """Initialize the legislation cache.

        Args:
            cache_dir: Directory path for storing cached content.
            timeout: Maximum seconds to wait per URL fetch (default 30).
        """
        self._cache_dir = Path(cache_dir)
        self._timeout = timeout
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def fetch_and_cache(self, urls: list[str]) -> FetchReport:
        """Fetch legislation content from URLs and cache locally.

        For each URL:
        - Attempts to fetch fresh content with the configured timeout.
        - On success: stores content in file cache.
        - On failure: falls back to previously cached content if available.
        - On first run with no cache: logs error for unreachable URLs.

        Args:
            urls: List of legislation URLs to fetch.

        Returns:
            FetchReport with successful, failed, and cached URL lists.
        """
        successful_urls: list[str] = []
        failed_urls: list[str] = []
        cached_urls: list[str] = []

        for url in urls:
            url_hash = _url_to_hash(url)
            cache_file = self._cache_dir / f"{url_hash}.json"

            try:
                response = requests.get(url, timeout=self._timeout)
                response.raise_for_status()

                # Determine content type for extraction
                content_type = response.headers.get("Content-Type", "")
                if "pdf" in content_type.lower():
                    # Store raw text indicator for PDFs (cannot extract inline)
                    text_content = f"[PDF document from {url}]"
                else:
                    text_content = _extract_text_from_html(response.text)

                # Store in cache
                cache_data = {
                    "url": url,
                    "law_name": _get_law_name(url),
                    "content": text_content,
                }
                cache_file.write_text(
                    json.dumps(cache_data, ensure_ascii=False), encoding="utf-8"
                )

                successful_urls.append(url)
                logger.info("Fetched and cached legislation: %s", _get_law_name(url))

            except (
                requests.RequestException,
                requests.Timeout,
                OSError,
            ) as e:
                # Fetch failed — try to use cached content
                if cache_file.exists():
                    cached_urls.append(url)
                    logger.warning(
                        "Failed to fetch %s (%s), using cached content",
                        url,
                        str(e),
                    )
                else:
                    failed_urls.append(url)
                    logger.error(
                        "Failed to fetch %s (%s) and no cached content available",
                        url,
                        str(e),
                    )

        # Log summary
        total = len(urls)
        available = len(successful_urls) + len(cached_urls)
        if failed_urls:
            logger.error(
                "Legislation knowledge base degraded: %d/%d URLs unavailable",
                len(failed_urls),
                total,
            )
        else:
            logger.info(
                "Legislation knowledge base ready: %d/%d URLs available "
                "(%d fresh, %d from cache)",
                available,
                total,
                len(successful_urls),
                len(cached_urls),
            )

        return FetchReport(
            successful_urls=successful_urls,
            failed_urls=failed_urls,
            cached_urls=cached_urls,
        )

    def get_relevant_content(self, topic: str) -> list[LegislationSnippet]:
        """Search cached legislation for content relevant to a topic.

        Performs a case-insensitive keyword search across all cached
        legislation content and returns matching snippets.

        Args:
            topic: The topic or query to search for in legislation.

        Returns:
            List of LegislationSnippet with relevant excerpts.
        """
        snippets: list[LegislationSnippet] = []
        topic_lower = topic.lower()

        # Tokenize topic into search terms (words with 3+ chars)
        terms = [
            word
            for word in re.split(r"\W+", topic_lower)
            if len(word) >= 3
        ]

        if not terms:
            return snippets

        # Search all cached files
        for cache_file in self._cache_dir.glob("*.json"):
            try:
                cache_data = json.loads(
                    cache_file.read_text(encoding="utf-8")
                )
            except (json.JSONDecodeError, OSError):
                continue

            content = cache_data.get("content", "")
            content_lower = content.lower()

            # Check if any search term appears in the content
            matching_terms = [t for t in terms if t in content_lower]
            if not matching_terms:
                continue

            # Extract relevant paragraphs containing the terms
            paragraphs = content.split("\n\n")
            relevant_paragraphs: list[str] = []

            for paragraph in paragraphs:
                paragraph_lower = paragraph.lower()
                if any(term in paragraph_lower for term in matching_terms):
                    # Keep paragraph if it has meaningful content
                    stripped = paragraph.strip()
                    if len(stripped) > 20:
                        relevant_paragraphs.append(stripped)

            if relevant_paragraphs:
                # Limit to first 5 relevant paragraphs per source
                snippet_content = "\n\n".join(relevant_paragraphs[:5])
                snippets.append(
                    LegislationSnippet(
                        source_url=cache_data.get("url", ""),
                        law_name=cache_data.get("law_name", ""),
                        content=snippet_content,
                    )
                )

        return snippets
