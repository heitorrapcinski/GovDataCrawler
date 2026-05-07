"""Unit tests for openclaws.legislation module."""

import json

import pytest
import responses
from responses import matchers

from openclaws.legislation import LEGISLATION_URLS, LegislationCache


@pytest.fixture
def cache(tmp_path):
    """Create a LegislationCache instance with a temporary cache directory."""
    return LegislationCache(cache_dir=str(tmp_path), timeout=30)


@pytest.fixture
def sample_html():
    """Return sample HTML content for mocking HTTP responses."""
    return """
    <html>
    <head><title>Lei 14.133/2021</title></head>
    <body>
        <p>Art. 1º Esta Lei estabelece normas gerais de licitação e contratação.</p>
        <p>Art. 2º Esta Lei aplica-se a todos os entes da Federação.</p>
    </body>
    </html>
    """


class TestLegislationUrls:
    """Test that LEGISLATION_URLS contains exactly 10 URLs."""

    def test_contains_exactly_10_urls(self):
        assert len(LEGISLATION_URLS) == 10

    def test_all_entries_are_strings(self):
        for url in LEGISLATION_URLS:
            assert isinstance(url, str)

    def test_all_entries_are_valid_urls(self):
        for url in LEGISLATION_URLS:
            assert url.startswith("https://")


class TestFetchAndCacheSuccess:
    """Test successful fetch and cache storage."""

    @responses.activate
    def test_fetches_and_caches_single_url(self, cache, tmp_path, sample_html):
        url = "https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2021/lei/l14133.htm"
        responses.add(responses.GET, url, body=sample_html, status=200)

        report = cache.fetch_and_cache([url])

        assert url in report.successful_urls
        assert report.failed_urls == []
        assert report.cached_urls == []

    @responses.activate
    def test_stores_content_in_file_cache(self, cache, tmp_path, sample_html):
        url = "https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2021/lei/l14133.htm"
        responses.add(responses.GET, url, body=sample_html, status=200)

        cache.fetch_and_cache([url])

        # Verify cache file was created
        cache_files = list(tmp_path.glob("*.json"))
        assert len(cache_files) == 1

        # Verify cache file content
        cache_data = json.loads(cache_files[0].read_text(encoding="utf-8"))
        assert cache_data["url"] == url
        assert "law_name" in cache_data
        assert "content" in cache_data
        assert "licitação" in cache_data["content"] or "normas" in cache_data["content"]

    @responses.activate
    def test_fetches_multiple_urls(self, cache, sample_html):
        urls = [
            "https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2021/lei/l14133.htm",
            "https://www.planalto.gov.br/ccivil_03/leis/l8666cons.htm",
        ]
        for url in urls:
            responses.add(responses.GET, url, body=sample_html, status=200)

        report = cache.fetch_and_cache(urls)

        assert len(report.successful_urls) == 2
        assert report.failed_urls == []
        assert report.cached_urls == []

    @responses.activate
    def test_handles_pdf_content_type(self, cache, tmp_path):
        url = "https://www.gov.br/compras/pt-br/nllc/lista-de-atos-normativos-e-estagios-de-regulamentacao-da-lei-14133-de-2021.pdf"
        responses.add(
            responses.GET,
            url,
            body=b"%PDF-1.4 fake pdf content",
            status=200,
            content_type="application/pdf",
        )

        report = cache.fetch_and_cache([url])

        assert url in report.successful_urls
        cache_files = list(tmp_path.glob("*.json"))
        assert len(cache_files) == 1
        cache_data = json.loads(cache_files[0].read_text(encoding="utf-8"))
        assert "[PDF document from" in cache_data["content"]


class TestCacheHit:
    """Test cache hit (serve from file cache when fetch fails)."""

    @responses.activate
    def test_serves_from_cache_on_fetch_failure(self, cache, tmp_path, sample_html):
        url = "https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2021/lei/l14133.htm"

        # First fetch succeeds and populates cache
        responses.add(responses.GET, url, body=sample_html, status=200)
        cache.fetch_and_cache([url])

        # Second fetch fails — should use cached content
        responses.replace(responses.GET, url, body=ConnectionError("Network error"))

        report = cache.fetch_and_cache([url])

        assert url in report.cached_urls
        assert report.successful_urls == []
        assert report.failed_urls == []

    @responses.activate
    def test_serves_from_cache_on_http_error(self, cache, tmp_path, sample_html):
        url = "https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2021/lei/l14133.htm"

        # First fetch succeeds
        responses.add(responses.GET, url, body=sample_html, status=200)
        cache.fetch_and_cache([url])

        # Second fetch returns 500 — should use cached content
        responses.replace(responses.GET, url, body="Server Error", status=500)

        report = cache.fetch_and_cache([url])

        assert url in report.cached_urls
        assert report.successful_urls == []
        assert report.failed_urls == []

    @responses.activate
    def test_cache_file_survives_between_instances(self, tmp_path, sample_html):
        url = "https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2021/lei/l14133.htm"

        # First instance fetches and caches
        cache1 = LegislationCache(cache_dir=str(tmp_path), timeout=30)
        responses.add(responses.GET, url, body=sample_html, status=200)
        cache1.fetch_and_cache([url])

        # Second instance with fetch failure — should use file cache
        cache2 = LegislationCache(cache_dir=str(tmp_path), timeout=30)
        responses.replace(responses.GET, url, body=ConnectionError("Unreachable"))

        report = cache2.fetch_and_cache([url])

        assert url in report.cached_urls
        assert report.failed_urls == []


class TestTimeoutHandling:
    """Test timeout handling (30s per URL)."""

    @responses.activate
    def test_timeout_with_no_cache_reports_failure(self, cache):
        url = "https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2021/lei/l14133.htm"
        responses.add(
            responses.GET,
            url,
            body=ConnectionError("Connection timed out"),
        )

        report = cache.fetch_and_cache([url])

        assert url in report.failed_urls
        assert report.successful_urls == []
        assert report.cached_urls == []

    def test_timeout_parameter_is_configurable(self, tmp_path):
        cache = LegislationCache(cache_dir=str(tmp_path), timeout=5)
        assert cache._timeout == 5

    def test_default_timeout_is_30_seconds(self, tmp_path):
        cache = LegislationCache(cache_dir=str(tmp_path))
        assert cache._timeout == 30


class TestDegradedStartup:
    """Test degraded startup (unreachable URLs, no cache)."""

    @responses.activate
    def test_all_urls_unreachable_no_cache(self, cache):
        urls = [
            "https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2021/lei/l14133.htm",
            "https://www.planalto.gov.br/ccivil_03/leis/l8666cons.htm",
        ]
        for url in urls:
            responses.add(responses.GET, url, body=ConnectionError("Unreachable"))

        report = cache.fetch_and_cache(urls)

        assert report.successful_urls == []
        assert report.cached_urls == []
        assert len(report.failed_urls) == 2
        assert set(report.failed_urls) == set(urls)

    @responses.activate
    def test_degraded_startup_does_not_raise(self, cache):
        """System should start even if all legislation URLs are unreachable."""
        urls = LEGISLATION_URLS[:3]
        for url in urls:
            responses.add(responses.GET, url, body=ConnectionError("Unreachable"))

        # Should not raise — degraded startup is allowed
        report = cache.fetch_and_cache(urls)
        assert len(report.failed_urls) == 3


class TestPartialDegradation:
    """Test partial degradation (some URLs cached, some unreachable)."""

    @responses.activate
    def test_mix_of_success_and_failure(self, cache, sample_html):
        url_ok = "https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2021/lei/l14133.htm"
        url_fail = "https://www.planalto.gov.br/ccivil_03/leis/l8666cons.htm"

        responses.add(responses.GET, url_ok, body=sample_html, status=200)
        responses.add(responses.GET, url_fail, body=ConnectionError("Unreachable"))

        report = cache.fetch_and_cache([url_ok, url_fail])

        assert url_ok in report.successful_urls
        assert url_fail in report.failed_urls
        assert report.cached_urls == []

    @responses.activate
    def test_mix_of_fresh_cached_and_failed(self, cache, tmp_path, sample_html):
        url_fresh = "https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2021/lei/l14133.htm"
        url_cached = "https://www.planalto.gov.br/ccivil_03/leis/l8666cons.htm"
        url_fail = "https://www.planalto.gov.br/ccivil_03/leis/2002/l10520.htm"

        # Pre-populate cache for url_cached
        responses.add(responses.GET, url_cached, body=sample_html, status=200)
        cache.fetch_and_cache([url_cached])

        # Now simulate: url_fresh succeeds, url_cached fails (use cache), url_fail fails (no cache)
        responses.reset()
        responses.add(responses.GET, url_fresh, body=sample_html, status=200)
        responses.add(responses.GET, url_cached, body=ConnectionError("Unreachable"))
        responses.add(responses.GET, url_fail, body=ConnectionError("Unreachable"))

        report = cache.fetch_and_cache([url_fresh, url_cached, url_fail])

        assert url_fresh in report.successful_urls
        assert url_cached in report.cached_urls
        assert url_fail in report.failed_urls

    @responses.activate
    def test_report_totals_are_consistent(self, cache, sample_html):
        urls = [
            "https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2021/lei/l14133.htm",
            "https://www.planalto.gov.br/ccivil_03/leis/l8666cons.htm",
            "https://www.planalto.gov.br/ccivil_03/leis/2002/l10520.htm",
        ]
        responses.add(responses.GET, urls[0], body=sample_html, status=200)
        responses.add(responses.GET, urls[1], body=sample_html, status=200)
        responses.add(responses.GET, urls[2], body=ConnectionError("Unreachable"))

        report = cache.fetch_and_cache(urls)

        total = len(report.successful_urls) + len(report.failed_urls) + len(report.cached_urls)
        assert total == len(urls)
