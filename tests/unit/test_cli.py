"""Unit tests for CLI argument parsing and logging setup."""

import logging
import os

import pytest

from gov_data_crawler.cli import parse_args, setup_logging


class TestParseArgs:
    """Tests for parse_args function."""

    def test_defaults(self):
        """All defaults are applied when no arguments are provided."""
        args = parse_args([])
        assert args.output_dir == "target"
        assert args.min_delay == 2.0
        assert args.max_delay == 5.0
        assert args.max_time is None
        assert args.max_contracts is None
        assert args.log_level == "INFO"

    def test_custom_output_dir(self):
        """Custom output directory is parsed correctly."""
        args = parse_args(["--output-dir", "/tmp/crawl_output"])
        assert args.output_dir == "/tmp/crawl_output"

    def test_custom_delays(self):
        """Custom min and max delay values are parsed correctly."""
        args = parse_args(["--min-delay", "1.0", "--max-delay", "3.0"])
        assert args.min_delay == 1.0
        assert args.max_delay == 3.0

    def test_max_time_flag(self):
        """Max time flag is parsed as a float."""
        args = parse_args(["--max-time", "3600"])
        assert args.max_time == 3600.0

    def test_max_contracts_flag(self):
        """Max contracts flag is parsed as an integer."""
        args = parse_args(["--max-contracts", "50"])
        assert args.max_contracts == 50

    def test_log_level_debug(self):
        """Log level DEBUG is accepted."""
        args = parse_args(["--log-level", "DEBUG"])
        assert args.log_level == "DEBUG"

    def test_log_level_warning(self):
        """Log level WARNING is accepted."""
        args = parse_args(["--log-level", "WARNING"])
        assert args.log_level == "WARNING"

    def test_log_level_error(self):
        """Log level ERROR is accepted."""
        args = parse_args(["--log-level", "ERROR"])
        assert args.log_level == "ERROR"

    def test_invalid_log_level_rejected(self):
        """Invalid log level causes SystemExit."""
        with pytest.raises(SystemExit):
            parse_args(["--log-level", "TRACE"])

    def test_all_custom_values(self):
        """All arguments can be set together."""
        args = parse_args([
            "--output-dir", "output",
            "--min-delay", "0.5",
            "--max-delay", "1.5",
            "--max-time", "600",
            "--max-contracts", "10",
            "--log-level", "DEBUG",
        ])
        assert args.output_dir == "output"
        assert args.min_delay == 0.5
        assert args.max_delay == 1.5
        assert args.max_time == 600.0
        assert args.max_contracts == 10
        assert args.log_level == "DEBUG"

    def test_max_time_none_by_default(self):
        """Max time defaults to None (no limit)."""
        args = parse_args([])
        assert args.max_time is None

    def test_max_contracts_none_by_default(self):
        """Max contracts defaults to None (no limit)."""
        args = parse_args([])
        assert args.max_contracts is None


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_creates_output_directory(self, tmp_path):
        """Output directory is created if it does not exist."""
        log_dir = str(tmp_path / "logs")
        assert not os.path.exists(log_dir)

        logger = setup_logging(log_dir, "INFO")

        assert os.path.isdir(log_dir)
        # Clean up handlers
        logger.handlers.clear()

    def test_creates_log_file(self, tmp_path):
        """A crawl.log file is created in the output directory."""
        log_dir = str(tmp_path / "logs")
        logger = setup_logging(log_dir, "INFO")

        # Write a message to flush to file
        logger.info("test message")

        log_file = os.path.join(log_dir, "crawl.log")
        assert os.path.isfile(log_file)
        # Clean up handlers
        logger.handlers.clear()

    def test_dual_handlers(self, tmp_path):
        """Logger has both console and file handlers."""
        log_dir = str(tmp_path / "logs")
        logger = setup_logging(log_dir, "INFO")

        handler_types = {type(h) for h in logger.handlers}
        assert logging.StreamHandler in handler_types
        assert logging.FileHandler in handler_types
        # Clean up handlers
        logger.handlers.clear()

    def test_log_level_applied(self, tmp_path):
        """Logger level matches the requested level."""
        log_dir = str(tmp_path / "logs")
        logger = setup_logging(log_dir, "DEBUG")

        assert logger.level == logging.DEBUG
        # Clean up handlers
        logger.handlers.clear()

    def test_returns_named_logger(self, tmp_path):
        """Logger is named 'gov_data_crawler'."""
        log_dir = str(tmp_path / "logs")
        logger = setup_logging(log_dir, "INFO")

        assert logger.name == "gov_data_crawler"
        # Clean up handlers
        logger.handlers.clear()
