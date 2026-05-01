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
    """HTTP client with session management, retry, and delay.

    Maintains a persistent :class:`requests.Session` so that cookies
    (e.g. Laravel session cookies required for CSRF validation) are
    preserved across requests.
    """

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
        self._session = self._create_session(retry=True)

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

    def _get_session(self, retry: bool) -> requests.Session:
        """Return the appropriate session based on retry preference.

        When ``retry`` is True the persistent session (with retry adapters)
        is returned.  When False a one-off session without retry adapters is
        created — its cookies are still copied from the persistent session
        so that CSRF / session state is preserved.

        Args:
            retry: Whether retry logic should be active.

        Returns:
            A :class:`requests.Session` instance.
        """
        if retry:
            return self._session

        # Create a temporary session without retry adapters but copy
        # cookies from the persistent session so CSRF tokens work.
        tmp = requests.Session()
        tmp.cookies.update(self._session.cookies)
        return tmp

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

        session = self._get_session(retry)
        try:
            response = session.get(url)
            self._logger.debug(
                "Response from %s: status=%d", url, response.status_code
            )
            # Sync cookies back to the persistent session.
            self._session.cookies.update(session.cookies)
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
            if session is not self._session:
                session.close()

    def post(
        self,
        url: str,
        data: dict | None = None,
        headers: dict[str, str] | None = None,
        retry: bool = True,
    ) -> HttpResponse:
        """Send a POST request with delay and optional retry.

        Args:
            url: Target URL.
            data: Form data to send in the request body.
            headers: Additional headers to include in the request.
            retry: Whether to apply retry logic (default True).

        Returns:
            HttpResponse with status_code, text, headers, and content.

        Raises:
            HttpRequestError: After all retries are exhausted or on request failure.
        """
        self._delay_mechanism.wait()
        self._logger.debug("POST %s (retry=%s)", url, retry)

        session = self._get_session(retry)
        try:
            response = session.post(url, data=data, headers=headers)
            self._logger.debug(
                "Response from %s: status=%d", url, response.status_code
            )
            # Sync cookies back to the persistent session.
            self._session.cookies.update(session.cookies)
            return HttpResponse(
                status_code=response.status_code,
                text=response.text,
                headers=dict(response.headers),
                content=response.content,
            )
        except (requests.exceptions.RequestException, ConnectionError) as exc:
            self._logger.error("POST request failed for %s: %s", url, exc)
            raise HttpRequestError(
                url=url,
                status_code=None,
                message=str(exc),
            ) from exc
        finally:
            if session is not self._session:
                session.close()

    def close(self) -> None:
        """Close the underlying session and release resources."""
        self._session.close()
