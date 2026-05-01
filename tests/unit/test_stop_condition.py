"""Unit tests for the StopConditionChecker component."""

import logging
from unittest.mock import patch

import pytest

from gov_data_crawler.stop_condition import StopConditionChecker


class TestStopConditionDefaults:
    """Tests for default configuration (no limits)."""

    def test_no_limits_returns_false(self) -> None:
        checker = StopConditionChecker()
        checker.start()
        assert checker.should_stop(0) is False

    def test_no_limits_returns_false_with_high_count(self) -> None:
        checker = StopConditionChecker()
        checker.start()
        assert checker.should_stop(999999) is False

    def test_no_limits_triggered_condition_is_none(self) -> None:
        checker = StopConditionChecker()
        checker.start()
        checker.should_stop(100)
        assert checker.triggered_condition is None

    def test_triggered_condition_is_none_before_check(self) -> None:
        checker = StopConditionChecker()
        assert checker.triggered_condition is None


class TestStopConditionMaxContracts:
    """Tests for max_contracts limit."""

    def test_below_limit_returns_false(self) -> None:
        checker = StopConditionChecker(max_contracts=10)
        checker.start()
        assert checker.should_stop(5) is False

    def test_at_limit_returns_true(self) -> None:
        checker = StopConditionChecker(max_contracts=10)
        checker.start()
        assert checker.should_stop(10) is True

    def test_above_limit_returns_true(self) -> None:
        checker = StopConditionChecker(max_contracts=10)
        checker.start()
        assert checker.should_stop(15) is True

    def test_triggered_condition_is_max_contracts(self) -> None:
        checker = StopConditionChecker(max_contracts=5)
        checker.start()
        checker.should_stop(5)
        assert checker.triggered_condition == "max_contracts"

    def test_zero_limit_stops_immediately(self) -> None:
        checker = StopConditionChecker(max_contracts=0)
        checker.start()
        assert checker.should_stop(0) is True


class TestStopConditionMaxTime:
    """Tests for max_time limit."""

    @patch("gov_data_crawler.stop_condition.time.monotonic")
    def test_below_time_limit_returns_false(self, mock_monotonic) -> None:
        mock_monotonic.side_effect = [100.0, 105.0]  # start, check
        checker = StopConditionChecker(max_time=30.0)
        checker.start()
        assert checker.should_stop(0) is False

    @patch("gov_data_crawler.stop_condition.time.monotonic")
    def test_at_time_limit_returns_true(self, mock_monotonic) -> None:
        mock_monotonic.side_effect = [100.0, 130.0]  # start, check (elapsed=30)
        checker = StopConditionChecker(max_time=30.0)
        checker.start()
        assert checker.should_stop(0) is True

    @patch("gov_data_crawler.stop_condition.time.monotonic")
    def test_above_time_limit_returns_true(self, mock_monotonic) -> None:
        mock_monotonic.side_effect = [100.0, 200.0]  # start, check (elapsed=100)
        checker = StopConditionChecker(max_time=30.0)
        checker.start()
        assert checker.should_stop(0) is True

    @patch("gov_data_crawler.stop_condition.time.monotonic")
    def test_triggered_condition_is_max_time(self, mock_monotonic) -> None:
        mock_monotonic.side_effect = [0.0, 60.0]
        checker = StopConditionChecker(max_time=30.0)
        checker.start()
        checker.should_stop(0)
        assert checker.triggered_condition == "max_time"


class TestStopConditionCombinedLimits:
    """Tests for combined max_time and max_contracts limits."""

    @patch("gov_data_crawler.stop_condition.time.monotonic")
    def test_time_triggers_first(self, mock_monotonic) -> None:
        mock_monotonic.side_effect = [0.0, 60.0]
        checker = StopConditionChecker(max_time=30.0, max_contracts=100)
        checker.start()
        assert checker.should_stop(5) is True
        assert checker.triggered_condition == "max_time"

    @patch("gov_data_crawler.stop_condition.time.monotonic")
    def test_contracts_triggers_first(self, mock_monotonic) -> None:
        mock_monotonic.side_effect = [0.0, 5.0]
        checker = StopConditionChecker(max_time=300.0, max_contracts=10)
        checker.start()
        assert checker.should_stop(10) is True
        assert checker.triggered_condition == "max_contracts"

    @patch("gov_data_crawler.stop_condition.time.monotonic")
    def test_neither_triggers(self, mock_monotonic) -> None:
        mock_monotonic.side_effect = [0.0, 5.0]
        checker = StopConditionChecker(max_time=300.0, max_contracts=100)
        checker.start()
        assert checker.should_stop(5) is False
        assert checker.triggered_condition is None


class TestStopConditionStartRequired:
    """Tests that start() must be called before should_stop()."""

    def test_should_stop_without_start_raises(self) -> None:
        checker = StopConditionChecker(max_time=30.0)
        with pytest.raises(RuntimeError, match="start\\(\\) must be called"):
            checker.should_stop(0)


class TestStopConditionLogging:
    """Tests for logging behavior."""

    @patch("gov_data_crawler.stop_condition.time.monotonic")
    def test_max_time_logs_info(self, mock_monotonic, caplog) -> None:
        mock_monotonic.side_effect = [0.0, 60.0]
        logger = logging.getLogger("test.stop_condition")
        checker = StopConditionChecker(max_time=30.0, logger=logger)
        with caplog.at_level(logging.INFO, logger="test.stop_condition"):
            checker.start()
            checker.should_stop(0)
        assert "max_time" in caplog.text

    def test_max_contracts_logs_info(self, caplog) -> None:
        logger = logging.getLogger("test.stop_condition")
        checker = StopConditionChecker(max_contracts=5, logger=logger)
        with caplog.at_level(logging.INFO, logger="test.stop_condition"):
            checker.start()
            checker.should_stop(5)
        assert "max_contracts" in caplog.text
