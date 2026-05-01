"""Unit tests for the HttpClient component."""

from unittest.mock import MagicMock, patch

import responses

from gov_data_crawler.contract import HttpRequestError
from gov_data_crawler.delay import DelayMechanism
from gov_data_crawler.http_client import HttpClient, HttpResponse


class TestHttpClientGet:
    """Tests for HttpClient.get method."""

    def _make_client(self) -> tuple[HttpClient, MagicMock]:
        """Create an HttpClient with a mocked DelayMechanism."""
        delay = MagicMock(spec=DelayMechanism)
        delay.wait.return_value = 0.0
        client = HttpClient(delay_mechanism=delay, max_retries=3)
        return client, delay

    @responses.activate
    def test_successful_get_returns_http_response(self) -> None:
        """A successful GET returns an HttpResponse with correct fields."""
        responses.add(
            responses.GET,
            "https://example.com/page",
            body="Hello World",
            status=200,
            headers={"X-Custom": "value"},
        )

        client, _ = self._make_client()
        result = client.get("https://example.com/page")

        assert isinstance(result, HttpResponse)
        assert result.status_code == 200
        assert result.text == "Hello World"
        assert result.headers["X-Custom"] == "value"
        assert result.content == b"Hello World"

    @responses.activate
    def test_get_calls_delay_before_request(self) -> None:
        """The delay mechanism is called before each request."""
        responses.add(
            responses.GET,
            "https://example.com/page",
            body="OK",
            status=200,
        )

        client, delay = self._make_client()
        client.get("https://example.com/page")

        delay.wait.assert_called_once()

    @responses.activate
    def test_retry_on_500_status(self) -> None:
        """The client retries on 500 status codes and succeeds on final attempt."""
        # First two calls return 500, third returns 200
        responses.add(responses.GET, "https://example.com/api", status=500)
        responses.add(responses.GET, "https://example.com/api", status=500)
        responses.add(responses.GET, "https://example.com/api", status=500)
        responses.add(
            responses.GET,
            "https://example.com/api",
            body="Success",
            status=200,
        )

        client, _ = self._make_client()
        result = client.get("https://example.com/api", retry=True)

        assert result.status_code == 200
        assert result.text == "Success"
        # Original request + 3 retries = 4 total calls
        assert len(responses.calls) == 4

    @responses.activate
    def test_404_returns_response_without_retry(self) -> None:
        """A 404 response is returned directly without triggering retries."""
        responses.add(
            responses.GET,
            "https://example.com/missing",
            body="Not Found",
            status=404,
        )

        client, _ = self._make_client()
        result = client.get("https://example.com/missing", retry=True)

        assert result.status_code == 404
        assert result.text == "Not Found"
        # Only 1 call — no retries for 404
        assert len(responses.calls) == 1

    @responses.activate
    def test_no_retry_when_retry_false(self) -> None:
        """When retry=False, no retry adapter is mounted and 500 is returned directly."""
        responses.add(
            responses.GET,
            "https://example.com/api",
            body="Server Error",
            status=500,
        )

        client, _ = self._make_client()
        result = client.get("https://example.com/api", retry=False)

        assert result.status_code == 500
        assert result.text == "Server Error"
        assert len(responses.calls) == 1

    @responses.activate
    def test_connection_error_raises_http_request_error(self) -> None:
        """A connection error raises HttpRequestError."""
        responses.add(
            responses.GET,
            "https://example.com/fail",
            body=ConnectionError("Connection refused"),
        )

        client, _ = self._make_client()
        try:
            client.get("https://example.com/fail", retry=False)
            assert False, "Expected HttpRequestError"
        except HttpRequestError as exc:
            assert exc.url == "https://example.com/fail"
            assert exc.status_code is None
            assert "Connection refused" in exc.message

    @responses.activate
    def test_delay_called_even_on_failure(self) -> None:
        """The delay mechanism is called even when the request fails."""
        responses.add(
            responses.GET,
            "https://example.com/fail",
            body=ConnectionError("timeout"),
        )

        client, delay = self._make_client()
        try:
            client.get("https://example.com/fail", retry=False)
        except HttpRequestError:
            pass

        delay.wait.assert_called_once()
