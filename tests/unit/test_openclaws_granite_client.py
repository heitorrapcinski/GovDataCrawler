"""Unit tests for openclaws.granite_client module."""

import responses
import pytest

from openclaws.granite_client import (
    GraniteClient,
    GraniteConnectionError,
    GraniteContextExceededError,
    GraniteInvalidParamsError,
    GraniteModelLoadingError,
    GraniteTimeoutError,
)
from openclaws.models import GenerationResult, HealthStatus


ENDPOINT_URL = "http://granite:8080"


class TestGraniteClientInit:
    """Test GraniteClient initialization."""

    def test_default_timeout(self):
        client = GraniteClient(ENDPOINT_URL)
        assert client._timeout == 60

    def test_custom_timeout(self):
        client = GraniteClient(ENDPOINT_URL, timeout=120)
        assert client._timeout == 120

    def test_strips_trailing_slash(self):
        client = GraniteClient("http://granite:8080/")
        assert client._endpoint_url == "http://granite:8080"


class TestGraniteClientGenerate:
    """Test successful inference request and response parsing."""

    @responses.activate
    def test_successful_generation(self):
        """Validates: Requirements 2.3"""
        responses.add(
            responses.POST,
            f"{ENDPOINT_URL}/v1/completions",
            json={
                "text": "The contract was signed on 2024-01-15.",
                "usage": {
                    "prompt_tokens": 150,
                    "completion_tokens": 42,
                },
            },
            status=200,
        )

        client = GraniteClient(ENDPOINT_URL)
        result = client.generate("Summarize contract 12345")

        assert isinstance(result, GenerationResult)
        assert result.text == "The contract was signed on 2024-01-15."
        assert result.prompt_tokens == 150
        assert result.completion_tokens == 42

    @responses.activate
    def test_successful_generation_with_custom_params(self):
        """Validates: Requirements 2.3"""
        responses.add(
            responses.POST,
            f"{ENDPOINT_URL}/v1/completions",
            json={
                "text": "Response text",
                "usage": {"prompt_tokens": 100, "completion_tokens": 20},
            },
            status=200,
        )

        client = GraniteClient(ENDPOINT_URL)
        result = client.generate(
            "Test prompt",
            temperature=0.5,
            max_tokens=512,
            top_p=0.8,
        )

        assert result.text == "Response text"
        # Verify the request payload was sent correctly
        request_body = responses.calls[0].request.body
        import json

        payload = json.loads(request_body)
        assert payload["prompt"] == "Test prompt"
        assert payload["temperature"] == 0.5
        assert payload["max_tokens"] == 512
        assert payload["top_p"] == 0.8

    @responses.activate
    def test_successful_generation_missing_usage(self):
        """Validates: Requirements 2.3 — handles missing usage gracefully."""
        responses.add(
            responses.POST,
            f"{ENDPOINT_URL}/v1/completions",
            json={"text": "Generated text"},
            status=200,
        )

        client = GraniteClient(ENDPOINT_URL)
        result = client.generate("Test prompt")

        assert result.text == "Generated text"
        assert result.prompt_tokens == 0
        assert result.completion_tokens == 0


class TestGraniteClientTimeout:
    """Test 60s timeout handling (inform user, suggest retry)."""

    @responses.activate
    def test_timeout_raises_granite_timeout_error(self):
        """Validates: Requirements 2.5 — timeout informs user and suggests retry."""
        import requests as req_lib

        responses.add(
            responses.POST,
            f"{ENDPOINT_URL}/v1/completions",
            body=req_lib.exceptions.Timeout("Connection timed out"),
        )

        client = GraniteClient(ENDPOINT_URL, timeout=60)

        with pytest.raises(GraniteTimeoutError) as exc_info:
            client.generate("Test prompt")

        error_msg = str(exc_info.value)
        assert "60 seconds" in error_msg
        assert "retry" in error_msg.lower()

    @responses.activate
    def test_timeout_with_custom_timeout_value(self):
        """Validates: Requirements 2.5 — timeout message reflects configured timeout."""
        import requests as req_lib

        responses.add(
            responses.POST,
            f"{ENDPOINT_URL}/v1/completions",
            body=req_lib.exceptions.Timeout("Connection timed out"),
        )

        client = GraniteClient(ENDPOINT_URL, timeout=30)

        with pytest.raises(GraniteTimeoutError) as exc_info:
            client.generate("Test prompt")

        assert "30 seconds" in str(exc_info.value)


class TestGraniteClientModelLoading:
    """Test 503 response (model loading)."""

    @responses.activate
    def test_503_raises_model_loading_error(self):
        """Validates: Requirements 2.7 — model still loading returns appropriate error."""
        responses.add(
            responses.POST,
            f"{ENDPOINT_URL}/v1/completions",
            json={"error": "Model is loading"},
            status=503,
        )

        client = GraniteClient(ENDPOINT_URL)

        with pytest.raises(GraniteModelLoadingError) as exc_info:
            client.generate("Test prompt")

        error_msg = str(exc_info.value)
        assert "loading" in error_msg.lower()
        assert "retry" in error_msg.lower()


class TestGraniteClientBadRequest:
    """Test 400 response (context exceeded, invalid params)."""

    @responses.activate
    def test_400_context_exceeded(self):
        """Validates: Requirements 2.5 — context window exceeded."""
        responses.add(
            responses.POST,
            f"{ENDPOINT_URL}/v1/completions",
            body="Input exceeds maximum context token limit",
            status=400,
        )

        client = GraniteClient(ENDPOINT_URL)

        with pytest.raises(GraniteContextExceededError) as exc_info:
            client.generate("A very long prompt " * 10000)

        error_msg = str(exc_info.value)
        assert "token" in error_msg.lower() or "shorten" in error_msg.lower()

    @responses.activate
    def test_400_token_keyword_triggers_context_error(self):
        """Validates: Requirements 2.5 — error body with 'token' triggers context error."""
        responses.add(
            responses.POST,
            f"{ENDPOINT_URL}/v1/completions",
            body="Maximum token count exceeded for this model",
            status=400,
        )

        client = GraniteClient(ENDPOINT_URL)

        with pytest.raises(GraniteContextExceededError):
            client.generate("Test prompt")

    @responses.activate
    def test_400_invalid_params(self):
        """Validates: Requirements 2.6 — invalid parameter returns appropriate error."""
        responses.add(
            responses.POST,
            f"{ENDPOINT_URL}/v1/completions",
            body="Invalid value for temperature: must be between 0.0 and 2.0",
            status=400,
        )

        client = GraniteClient(ENDPOINT_URL)

        with pytest.raises(GraniteInvalidParamsError) as exc_info:
            client.generate("Test prompt", temperature=5.0)

        error_msg = str(exc_info.value)
        assert "Invalid" in error_msg or "invalid" in error_msg


class TestGraniteClientConnectionRefused:
    """Test connection refused handling."""

    @responses.activate
    def test_connection_refused_raises_connection_error(self):
        """Validates: Requirements 2.5 — connection refused informs user."""
        import requests as req_lib

        responses.add(
            responses.POST,
            f"{ENDPOINT_URL}/v1/completions",
            body=req_lib.exceptions.ConnectionError("Connection refused"),
        )

        client = GraniteClient(ENDPOINT_URL)

        with pytest.raises(GraniteConnectionError) as exc_info:
            client.generate("Test prompt")

        error_msg = str(exc_info.value)
        assert "connect" in error_msg.lower() or "Connect" in error_msg
        assert ENDPOINT_URL in error_msg


class TestGraniteClientHealthCheck:
    """Test health_check method."""

    @responses.activate
    def test_healthy_response(self):
        responses.add(
            responses.GET,
            f"{ENDPOINT_URL}/health",
            json={"status": "healthy", "model_loaded": True},
            status=200,
        )

        client = GraniteClient(ENDPOINT_URL)
        result = client.health_check()

        assert result == HealthStatus.HEALTHY

    @responses.activate
    def test_unhealthy_status(self):
        responses.add(
            responses.GET,
            f"{ENDPOINT_URL}/health",
            json={"status": "unhealthy", "model_loaded": False},
            status=200,
        )

        client = GraniteClient(ENDPOINT_URL)
        result = client.health_check()

        assert result == HealthStatus.UNHEALTHY

    @responses.activate
    def test_model_not_loaded(self):
        responses.add(
            responses.GET,
            f"{ENDPOINT_URL}/health",
            json={"status": "healthy", "model_loaded": False},
            status=200,
        )

        client = GraniteClient(ENDPOINT_URL)
        result = client.health_check()

        assert result == HealthStatus.UNHEALTHY

    @responses.activate
    def test_non_200_status_code(self):
        responses.add(
            responses.GET,
            f"{ENDPOINT_URL}/health",
            status=500,
        )

        client = GraniteClient(ENDPOINT_URL)
        result = client.health_check()

        assert result == HealthStatus.UNHEALTHY

    @responses.activate
    def test_connection_error_returns_unreachable(self):
        import requests as req_lib

        responses.add(
            responses.GET,
            f"{ENDPOINT_URL}/health",
            body=req_lib.exceptions.ConnectionError("Connection refused"),
        )

        client = GraniteClient(ENDPOINT_URL)
        result = client.health_check()

        assert result == HealthStatus.UNREACHABLE

    @responses.activate
    def test_timeout_returns_unreachable(self):
        import requests as req_lib

        responses.add(
            responses.GET,
            f"{ENDPOINT_URL}/health",
            body=req_lib.exceptions.Timeout("Timed out"),
        )

        client = GraniteClient(ENDPOINT_URL)
        result = client.health_check()

        assert result == HealthStatus.UNREACHABLE

    @responses.activate
    def test_invalid_json_returns_unhealthy(self):
        responses.add(
            responses.GET,
            f"{ENDPOINT_URL}/health",
            body="not json",
            status=200,
            content_type="text/plain",
        )

        client = GraniteClient(ENDPOINT_URL)
        result = client.health_check()

        assert result == HealthStatus.UNHEALTHY
