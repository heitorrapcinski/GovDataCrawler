"""Unit tests for the DelayMechanism component."""

import logging
from unittest.mock import patch

from gov_data_crawler.delay import DelayMechanism


class TestDelayMechanismDefaults:
    """Tests for default configuration values."""

    def test_default_min_seconds(self) -> None:
        delay = DelayMechanism()
        assert delay.min_seconds == 2.0

    def test_default_max_seconds(self) -> None:
        delay = DelayMechanism()
        assert delay.max_seconds == 5.0


class TestDelayMechanismCustomValues:
    """Tests for custom configuration values."""

    def test_custom_min_and_max(self) -> None:
        delay = DelayMechanism(min_seconds=1.0, max_seconds=3.0)
        assert delay.min_seconds == 1.0
        assert delay.max_seconds == 3.0

    def test_equal_min_and_max(self) -> None:
        delay = DelayMechanism(min_seconds=4.0, max_seconds=4.0)
        assert delay.min_seconds == 4.0
        assert delay.max_seconds == 4.0

    @patch("gov_data_crawler.delay.time.sleep")
    def test_wait_returns_value_within_bounds(self, mock_sleep) -> None:
        delay = DelayMechanism(min_seconds=1.0, max_seconds=3.0)
        result = delay.wait()
        assert 1.0 <= result <= 3.0
        mock_sleep.assert_called_once()

    @patch("gov_data_crawler.delay.time.sleep")
    def test_wait_calls_sleep_with_delay_value(self, mock_sleep) -> None:
        delay = DelayMechanism(min_seconds=1.0, max_seconds=3.0)
        result = delay.wait()
        mock_sleep.assert_called_once_with(result)

    @patch("gov_data_crawler.delay.time.sleep")
    def test_equal_bounds_produces_exact_value(self, mock_sleep) -> None:
        delay = DelayMechanism(min_seconds=2.5, max_seconds=2.5)
        result = delay.wait()
        assert result == 2.5


class TestDelayMechanismSwapBehavior:
    """Tests for min > max auto-swap behavior."""

    def test_swap_when_min_greater_than_max(self) -> None:
        delay = DelayMechanism(min_seconds=5.0, max_seconds=2.0)
        assert delay.min_seconds == 2.0
        assert delay.max_seconds == 5.0

    def test_swap_logs_warning(self, caplog) -> None:
        with caplog.at_level(logging.WARNING, logger="gov_data_crawler.delay"):
            DelayMechanism(min_seconds=10.0, max_seconds=1.0)
        assert "swapping values" in caplog.text.lower()

    def test_no_warning_when_min_less_than_max(self, caplog) -> None:
        with caplog.at_level(logging.WARNING, logger="gov_data_crawler.delay"):
            DelayMechanism(min_seconds=1.0, max_seconds=5.0)
        assert "swapping" not in caplog.text.lower()

    @patch("gov_data_crawler.delay.time.sleep")
    def test_wait_within_bounds_after_swap(self, mock_sleep) -> None:
        delay = DelayMechanism(min_seconds=8.0, max_seconds=3.0)
        result = delay.wait()
        assert 3.0 <= result <= 8.0
