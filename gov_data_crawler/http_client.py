"""HTTP client with session management, retry logic, and delay between requests."""

import logging
from dataclasses import dataclass

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from gov_data_crawler.contract import HttpRequestError
from gov_data_crawler.delay import DelayMechanism

logger = logging.getLogger(__name__)


@dataclass
class HttpResponse:
    """Simplified HTTP response."""

    status_code: int
    text: str
    headers: dict[str, str]
    content: bytes


class HttpClient:
    """HTTP client with session management, retry, and delay."""

    RETRY_STATUS_CODES = (500, 502, 503, 504)

    def __init__(
        self,
        delay_mechanism: DelayMechanism,
        max_retries: int = 3,
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialize the HTTP client.

        Args:
            delay_mechanism: Delay mechanism to apply before each request.
            max_retries: Maximum number of retries for failed requests.
            logger: Logger instance. Falls back to module logger if None.
        """
        self._delay_mechanism = delay_mechanism
        self._max_retries = max_retries
        self._logger = logger or logging.getLogger(__name__)

    def _create_session(self, retry: bool) -> requests.Session:
        """Create a requests session with optional retry adapter.

        Args:
            retry: Whether to mount the retry adapter on the session.

        Returns:
            Configured requests.Session instance.
        """
        session = requests.Session()

        if retry:
            retry_strategy = Retry(
                total=self._max_retries,
                backoff_factor=1.0,
                status_forcelist=list(self.RETRY_STATUS_CODES),
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            session.mount("http://", adapter)
            session.mount("https://", adapter)

        return session

    def get(self, url: str, retry: bool = True) -> HttpResponse:
        """Send a GET request with delay and optional retry.

        Args:
            url: Target URL.
            retry: Whether to apply retry logic (default True).

        Returns:
            HttpResponse with status_code, text, headers, and content.

        Raises:
            HttpRequestError: After all retries are exhausted or on request failure.
        """
        self._delay_mechanism.wait()
        self._logger.debug("GET %s (retry=%s)", url, retry)

        session = self._create_session(retry=retry)
        try:
            response = session.get(url)
            self._logger.debug(
                "Response from %s: status=%d", url, response.status_code
            )
            return HttpResponse(
                status_code=response.status_code,
                text=response.text,
                headers=dict(response.headers),
                content=response.content,
            )
        except (requests.exceptions.RequestException, ConnectionError) as exc:
            self._logger.error("Request failed for %s: %s", url, exc)
            raise HttpRequestError(
                url=url,
                status_code=None,
                message=str(exc),
            ) from exc
        finally:
            session.close()
