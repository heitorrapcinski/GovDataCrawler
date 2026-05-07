"""HTTP client for the Granite Service inference API."""

import logging

import requests

from openclaws.models import GenerationResult, HealthStatus

logger = logging.getLogger(__name__)


class GraniteConnectionError(Exception):
    """Raised when the Granite Service is unreachable (connection refused)."""


class GraniteTimeoutError(Exception):
    """Raised when the Granite Service does not respond within the timeout."""


class GraniteModelLoadingError(Exception):
    """Raised when the Granite Service is still loading the model (503)."""


class GraniteContextExceededError(Exception):
    """Raised when the prompt exceeds the model context window (400)."""


class GraniteInvalidParamsError(Exception):
    """Raised when request parameters are invalid (400)."""


class GraniteClient:
    """HTTP client for communicating with the Granite Service.

    Handles inference requests (POST /v1/completions) and health checks
    (GET /health) against the Granite Service container.
    """

    def __init__(self, endpoint_url: str, timeout: int = 60) -> None:
        """Initialize the Granite client.

        Args:
            endpoint_url: Base URL of the Granite Service (e.g. http://granite:8080).
            timeout: Maximum seconds to wait for inference responses (default 60).
        """
        self._endpoint_url = endpoint_url.rstrip("/")
        self._timeout = timeout

    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        top_p: float = 0.9,
    ) -> GenerationResult:
        """Send an inference request to the Granite Service.

        Posts to /v1/completions with the given prompt and generation parameters,
        then parses the response into a GenerationResult.

        Args:
            prompt: The text prompt to send for completion.
            temperature: Sampling temperature (0.0–2.0, default 0.7).
            max_tokens: Maximum tokens to generate (default 1024).
            top_p: Nucleus sampling parameter (0.0–1.0, default 0.9).

        Returns:
            GenerationResult with generated text and token usage.

        Raises:
            GraniteContextExceededError: If the prompt exceeds the context window.
            GraniteInvalidParamsError: If a parameter value is invalid.
            GraniteModelLoadingError: If the model is still loading.
            GraniteTimeoutError: If the request exceeds the timeout.
            GraniteConnectionError: If the service is unreachable.
        """
        url = f"{self._endpoint_url}/v1/completions"
        payload = {
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
        }

        try:
            response = requests.post(url, json=payload, timeout=self._timeout)
        except requests.exceptions.ConnectionError as e:
            logger.error("Connection refused to Granite Service at %s", url)
            raise GraniteConnectionError(
                f"Cannot connect to Granite Service at {self._endpoint_url}. "
                "Ensure the service is running and accessible."
            ) from e
        except requests.exceptions.Timeout as e:
            logger.error(
                "Granite Service did not respond within %d seconds", self._timeout
            )
            raise GraniteTimeoutError(
                f"Granite Service did not respond within {self._timeout} seconds. "
                "The inference request timed out. Please retry."
            ) from e

        if response.status_code == 503:
            logger.warning("Granite Service is still loading the model")
            raise GraniteModelLoadingError(
                "Granite Service is unavailable — the model is still loading. "
                "Please retry in a few moments."
            )

        if response.status_code == 400:
            error_body = response.text
            if "context" in error_body.lower() or "token" in error_body.lower():
                logger.error("Prompt exceeds Granite context window")
                raise GraniteContextExceededError(
                    "The prompt exceeds the maximum allowed token count. "
                    "Please shorten your query or reduce the context."
                )
            logger.error("Invalid parameters sent to Granite Service: %s", error_body)
            raise GraniteInvalidParamsError(
                f"Invalid request parameters: {error_body}"
            )

        response.raise_for_status()

        data = response.json()
        usage = data.get("usage", {})

        return GenerationResult(
            text=data["text"],
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
        )

    def health_check(self, timeout: int = 5) -> HealthStatus:
        """Check the health of the Granite Service.

        Sends a GET request to /health and interprets the response.

        Args:
            timeout: Maximum seconds to wait for the health response (default 5).

        Returns:
            HealthStatus.HEALTHY if the service reports healthy status,
            HealthStatus.UNHEALTHY if the service reports unhealthy status,
            HealthStatus.UNREACHABLE if the service cannot be reached or times out.
        """
        url = f"{self._endpoint_url}/health"

        try:
            response = requests.get(url, timeout=timeout)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            logger.warning("Granite Service is unreachable at %s", url)
            return HealthStatus.UNREACHABLE

        if response.status_code != 200:
            logger.warning(
                "Granite health check returned status %d", response.status_code
            )
            return HealthStatus.UNHEALTHY

        try:
            data = response.json()
        except ValueError:
            logger.warning("Granite health check returned invalid JSON")
            return HealthStatus.UNHEALTHY

        status = data.get("status", "")
        if status == "healthy" and data.get("model_loaded", False):
            return HealthStatus.HEALTHY

        logger.warning(
            "Granite Service reports status=%s, model_loaded=%s",
            status,
            data.get("model_loaded"),
        )
        return HealthStatus.UNHEALTHY
