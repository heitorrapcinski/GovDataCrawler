"""Unit tests for openclaws.cli module.

Tests cover:
- Query input validation (empty, whitespace, valid, over-limit)
- Response formatting with contract references and legislation citations
- Progress indicator display during query processing
- Graceful exit on Granite connectivity loss
"""

from unittest.mock import MagicMock, patch
import sys

import pytest

from openclaws.cli import validate_query, _format_response, main
from openclaws.models import QueryResponse


class TestValidateQuery:
    """Test validate_query for various input conditions."""

    def test_empty_string_rejected(self):
        """Validates: Requirements 5.1, 5.2 — empty input is rejected."""
        is_valid, error_msg = validate_query("")
        assert is_valid is False
        assert "empty" in error_msg.lower() or "blank" in error_msg.lower()

    def test_whitespace_only_rejected(self):
        """Validates: Requirements 5.1, 5.2 — whitespace-only input is rejected."""
        is_valid, error_msg = validate_query("   \t\n  ")
        assert is_valid is False
        assert "empty" in error_msg.lower() or "blank" in error_msg.lower()

    def test_valid_query_accepted(self):
        """Validates: Requirements 5.1 — valid query within length limits is accepted."""
        is_valid, error_msg = validate_query("What contracts were signed in 2024?")
        assert is_valid is True
        assert error_msg == ""

    def test_query_at_max_length_accepted(self):
        """Validates: Requirements 5.1 — query at exactly 2000 chars is accepted."""
        query = "a" * 2000
        is_valid, error_msg = validate_query(query)
        assert is_valid is True
        assert error_msg == ""

    def test_query_over_2000_chars_rejected(self):
        """Validates: Requirements 5.2 — query exceeding 2000 chars is rejected."""
        query = "a" * 2001
        is_valid, error_msg = validate_query(query)
        assert is_valid is False
        assert "2000" in error_msg
        assert "2001" in error_msg

    def test_query_with_leading_trailing_whitespace_stripped(self):
        """Validates: Requirements 5.1 — whitespace is stripped before validation."""
        query = "   valid query   "
        is_valid, error_msg = validate_query(query)
        assert is_valid is True
        assert error_msg == ""

    def test_single_char_query_accepted(self):
        """Validates: Requirements 5.1 — minimum valid query (1 char) is accepted."""
        is_valid, error_msg = validate_query("x")
        assert is_valid is True
        assert error_msg == ""


class TestFormatResponse:
    """Test _format_response for display formatting."""

    def test_response_with_contracts_and_citations(self):
        """Validates: Requirements 5.6 — response displays contracts and citations."""
        response = QueryResponse(
            answer="The contract was signed on 2024-01-15.",
            referenced_contracts=["CT-001", "CT-002"],
            legislation_citations=["Lei 14.133/2021, Art. 75"],
            confidence_labels={"claim1": "based on data"},
        )

        formatted = _format_response(response)

        assert "The contract was signed on 2024-01-15." in formatted
        assert "Referenced Contracts:" in formatted
        assert "CT-001" in formatted
        assert "CT-002" in formatted
        assert "Legislation Citations:" in formatted
        assert "Lei 14.133/2021, Art. 75" in formatted

    def test_response_with_empty_contracts_list(self):
        """Validates: Requirements 5.6 — no contracts section when list is empty."""
        response = QueryResponse(
            answer="No specific contracts found.",
            referenced_contracts=[],
            legislation_citations=[],
            confidence_labels={},
        )

        formatted = _format_response(response)

        assert "No specific contracts found." in formatted
        assert "Referenced Contracts:" not in formatted
        assert "Legislation Citations:" not in formatted

    def test_response_with_only_citations(self):
        """Validates: Requirements 5.6 — citations displayed without contracts."""
        response = QueryResponse(
            answer="Based on legislation analysis.",
            referenced_contracts=[],
            legislation_citations=["Lei 8.666/1993, Art. 23"],
            confidence_labels={},
        )

        formatted = _format_response(response)

        assert "Based on legislation analysis." in formatted
        assert "Referenced Contracts:" not in formatted
        assert "Legislation Citations:" in formatted
        assert "Lei 8.666/1993, Art. 23" in formatted

    def test_response_with_multiple_citations(self):
        """Validates: Requirements 5.6 — multiple citations are listed."""
        response = QueryResponse(
            answer="Analysis complete.",
            referenced_contracts=["CT-100"],
            legislation_citations=[
                "Lei 14.133/2021, Art. 75",
                "Lei 8.666/1993, Art. 23",
                "Decreto 10.024/2019, Art. 5",
            ],
            confidence_labels={},
        )

        formatted = _format_response(response)

        assert "Lei 14.133/2021, Art. 75" in formatted
        assert "Lei 8.666/1993, Art. 23" in formatted
        assert "Decreto 10.024/2019, Art. 5" in formatted


class TestMainProgressIndicator:
    """Test that the CLI displays a progress indicator during query processing."""

    @patch("openclaws.cli.load_and_validate_config")
    @patch("openclaws.cli.discover_artifacts")
    @patch("openclaws.cli.LegislationCache")
    @patch("openclaws.cli.GraniteClient")
    @patch("openclaws.cli.HealthMonitor")
    @patch("openclaws.cli.QueryEngine")
    @patch("builtins.input")
    def test_progress_indicator_displayed(
        self,
        mock_input,
        mock_query_engine_cls,
        mock_health_monitor_cls,
        mock_granite_client_cls,
        mock_legislation_cache_cls,
        mock_discover,
        mock_config,
        capsys,
    ):
        """Validates: Requirements 5.5 — progress indicator shown while processing."""
        # Setup config
        agent_config = MagicMock()
        agent_config.log_level = "INFO"
        agent_config.target_folder = "./target"
        agent_config.granite_endpoint = "http://granite:8080"
        agent_config.health_check_interval = 30
        granite_config = MagicMock()
        mock_config.return_value = (agent_config, granite_config)

        # Setup discovery
        mock_discover.return_value = []

        # Setup legislation cache
        mock_cache = MagicMock()
        mock_cache.fetch_and_cache.return_value = MagicMock(
            successful_urls=[], cached_urls=[], failed_urls=[]
        )
        mock_legislation_cache_cls.return_value = mock_cache

        # Setup granite client
        mock_client = MagicMock()
        from openclaws.models import HealthStatus

        mock_client.health_check.return_value = HealthStatus.HEALTHY
        mock_granite_client_cls.return_value = mock_client

        # Setup health monitor
        mock_monitor = MagicMock()
        mock_monitor.consecutive_failures = 0
        mock_health_monitor_cls.return_value = mock_monitor

        # Setup query engine
        mock_engine = MagicMock()
        mock_engine.process_query.return_value = QueryResponse(
            answer="Test answer",
            referenced_contracts=[],
            legislation_citations=[],
            confidence_labels={},
        )
        mock_query_engine_cls.return_value = mock_engine

        # Simulate user entering a query then EOF to exit
        mock_input.side_effect = ["What is contract CT-001?", EOFError()]

        main()

        captured = capsys.readouterr()
        assert "Analyzing..." in captured.out


class TestMainErrorMessages:
    """Test error message display for invalid queries."""

    @patch("openclaws.cli.load_and_validate_config")
    @patch("openclaws.cli.discover_artifacts")
    @patch("openclaws.cli.LegislationCache")
    @patch("openclaws.cli.GraniteClient")
    @patch("openclaws.cli.HealthMonitor")
    @patch("openclaws.cli.QueryEngine")
    @patch("builtins.input")
    def test_invalid_query_error_displayed(
        self,
        mock_input,
        mock_query_engine_cls,
        mock_health_monitor_cls,
        mock_granite_client_cls,
        mock_legislation_cache_cls,
        mock_discover,
        mock_config,
        capsys,
    ):
        """Validates: Requirements 5.2 — error message shown for invalid queries."""
        # Setup config
        agent_config = MagicMock()
        agent_config.log_level = "INFO"
        agent_config.target_folder = "./target"
        agent_config.granite_endpoint = "http://granite:8080"
        agent_config.health_check_interval = 30
        granite_config = MagicMock()
        mock_config.return_value = (agent_config, granite_config)

        # Setup discovery
        mock_discover.return_value = []

        # Setup legislation cache
        mock_cache = MagicMock()
        mock_cache.fetch_and_cache.return_value = MagicMock(
            successful_urls=[], cached_urls=[], failed_urls=[]
        )
        mock_legislation_cache_cls.return_value = mock_cache

        # Setup granite client
        mock_client = MagicMock()
        from openclaws.models import HealthStatus

        mock_client.health_check.return_value = HealthStatus.HEALTHY
        mock_granite_client_cls.return_value = mock_client

        # Setup health monitor
        mock_monitor = MagicMock()
        mock_monitor.consecutive_failures = 0
        mock_health_monitor_cls.return_value = mock_monitor

        # Setup query engine (should not be called for invalid queries)
        mock_engine = MagicMock()
        mock_query_engine_cls.return_value = mock_engine

        # Simulate user entering empty query then EOF
        mock_input.side_effect = ["", "   ", EOFError()]

        main()

        captured = capsys.readouterr()
        # Error messages go to stderr
        assert "Error:" in captured.err
        # Query engine should not have been called
        mock_engine.process_query.assert_not_called()


class TestMainGraniteConnectivityLoss:
    """Test graceful exit on Granite connectivity loss."""

    @patch("openclaws.cli.load_and_validate_config")
    @patch("openclaws.cli.discover_artifacts")
    @patch("openclaws.cli.LegislationCache")
    @patch("openclaws.cli.GraniteClient")
    @patch("openclaws.cli.HealthMonitor")
    @patch("openclaws.cli.QueryEngine")
    @patch("builtins.input")
    def test_exit_on_consecutive_failures(
        self,
        mock_input,
        mock_query_engine_cls,
        mock_health_monitor_cls,
        mock_granite_client_cls,
        mock_legislation_cache_cls,
        mock_discover,
        mock_config,
    ):
        """Validates: Requirements 5.7 — graceful exit when Granite is unreachable."""
        # Setup config
        agent_config = MagicMock()
        agent_config.log_level = "INFO"
        agent_config.target_folder = "./target"
        agent_config.granite_endpoint = "http://granite:8080"
        agent_config.health_check_interval = 30
        granite_config = MagicMock()
        mock_config.return_value = (agent_config, granite_config)

        # Setup discovery
        mock_discover.return_value = []

        # Setup legislation cache
        mock_cache = MagicMock()
        mock_cache.fetch_and_cache.return_value = MagicMock(
            successful_urls=[], cached_urls=[], failed_urls=[]
        )
        mock_legislation_cache_cls.return_value = mock_cache

        # Setup granite client
        mock_client = MagicMock()
        from openclaws.models import HealthStatus

        mock_client.health_check.return_value = HealthStatus.HEALTHY
        mock_granite_client_cls.return_value = mock_client

        # Setup health monitor with 3 consecutive failures (threshold)
        mock_monitor = MagicMock()
        mock_monitor.consecutive_failures = 3
        mock_health_monitor_cls.return_value = mock_monitor

        # Setup query engine
        mock_engine = MagicMock()
        mock_query_engine_cls.return_value = mock_engine

        # The main loop should detect consecutive_failures >= 3 and exit
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        mock_monitor.stop.assert_called()

    @patch("openclaws.cli.load_and_validate_config")
    @patch("openclaws.cli.discover_artifacts")
    @patch("openclaws.cli.LegislationCache")
    @patch("openclaws.cli.GraniteClient")
    @patch("openclaws.cli.HealthMonitor")
    @patch("openclaws.cli.QueryEngine")
    @patch("builtins.input")
    def test_exit_on_connection_error_during_query(
        self,
        mock_input,
        mock_query_engine_cls,
        mock_health_monitor_cls,
        mock_granite_client_cls,
        mock_legislation_cache_cls,
        mock_discover,
        mock_config,
        capsys,
    ):
        """Validates: Requirements 5.7 — exit when connection lost during query."""
        from openclaws.granite_client import GraniteConnectionError

        # Setup config
        agent_config = MagicMock()
        agent_config.log_level = "INFO"
        agent_config.target_folder = "./target"
        agent_config.granite_endpoint = "http://granite:8080"
        agent_config.health_check_interval = 30
        granite_config = MagicMock()
        mock_config.return_value = (agent_config, granite_config)

        # Setup discovery
        mock_discover.return_value = []

        # Setup legislation cache
        mock_cache = MagicMock()
        mock_cache.fetch_and_cache.return_value = MagicMock(
            successful_urls=[], cached_urls=[], failed_urls=[]
        )
        mock_legislation_cache_cls.return_value = mock_cache

        # Setup granite client
        mock_client = MagicMock()
        from openclaws.models import HealthStatus

        mock_client.health_check.return_value = HealthStatus.HEALTHY
        mock_granite_client_cls.return_value = mock_client

        # Setup health monitor — starts at 0, then goes to 3 after connection error
        mock_monitor = MagicMock()
        # First check: 0 failures (allows entering the loop)
        # After GraniteConnectionError: 3 failures (triggers exit)
        mock_monitor.consecutive_failures = 0

        def update_failures_after_error():
            mock_monitor.consecutive_failures = 3

        mock_health_monitor_cls.return_value = mock_monitor

        # Setup query engine to raise connection error
        mock_engine = MagicMock()
        mock_engine.process_query.side_effect = [GraniteConnectionError("Connection lost")]
        mock_query_engine_cls.return_value = mock_engine

        # Simulate user entering a query
        mock_input.side_effect = ["What is contract CT-001?"]

        # After the GraniteConnectionError, the code checks consecutive_failures
        # We need it to be >= 3 at that point
        def side_effect_process_query(query):
            mock_monitor.consecutive_failures = 3
            raise GraniteConnectionError("Connection lost")

        mock_engine.process_query.side_effect = side_effect_process_query

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        mock_monitor.stop.assert_called()
