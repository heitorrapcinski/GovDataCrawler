"""Unit tests for the SummaryReporter component."""

import logging
from unittest.mock import patch

from gov_data_crawler.summary import CrawlSummary, SummaryReporter


class TestSummaryReporterRecording:
    """Tests for event recording methods."""

    def _make_reporter(self) -> SummaryReporter:
        return SummaryReporter(logger=logging.getLogger("test"))

    def test_initial_counts_are_zero(self) -> None:
        reporter = self._make_reporter()
        summary = reporter.finalize()
        assert summary.successful == 0
        assert summary.failed == 0
        assert summary.skipped == 0
        assert summary.total_contracts == 0
        assert summary.attachments_downloaded == 0

    def test_record_success_increments_count(self) -> None:
        reporter = self._make_reporter()
        reporter.record_success("C001", attachments=2)
        summary = reporter.finalize()
        assert summary.successful == 1

    def test_record_success_accumulates_attachments(self) -> None:
        reporter = self._make_reporter()
        reporter.record_success("C001", attachments=3)
        reporter.record_success("C002", attachments=5)
        summary = reporter.finalize()
        assert summary.attachments_downloaded == 8

    def test_record_failure_increments_count(self) -> None:
        reporter = self._make_reporter()
        reporter.record_failure("C001", error="timeout")
        summary = reporter.finalize()
        assert summary.failed == 1

    def test_record_skip_increments_count(self) -> None:
        reporter = self._make_reporter()
        reporter.record_skip("C001")
        summary = reporter.finalize()
        assert summary.skipped == 1

    def test_multiple_events_produce_correct_totals(self) -> None:
        reporter = self._make_reporter()
        reporter.record_success("C001", attachments=2)
        reporter.record_success("C002", attachments=1)
        reporter.record_failure("C003", error="404")
        reporter.record_skip("C004")
        reporter.record_skip("C005")
        summary = reporter.finalize()
        assert summary.successful == 2
        assert summary.failed == 1
        assert summary.skipped == 2
        assert summary.total_contracts == 5
        assert summary.attachments_downloaded == 3

    def test_record_success_with_zero_attachments(self) -> None:
        reporter = self._make_reporter()
        reporter.record_success("C001", attachments=0)
        summary = reporter.finalize()
        assert summary.successful == 1
        assert summary.attachments_downloaded == 0


class TestSummaryReporterFinalize:
    """Tests for the finalize method and CrawlSummary generation."""

    def _make_reporter(self) -> SummaryReporter:
        return SummaryReporter(logger=logging.getLogger("test"))

    def test_finalize_returns_crawl_summary(self) -> None:
        reporter = self._make_reporter()
        summary = reporter.finalize()
        assert isinstance(summary, CrawlSummary)

    def test_finalize_includes_start_time_iso_format(self) -> None:
        reporter = self._make_reporter()
        summary = reporter.finalize()
        assert "T" in summary.start_time
        assert "+" in summary.start_time or summary.start_time.endswith("Z") or "+00:00" in summary.start_time

    def test_finalize_includes_end_time_iso_format(self) -> None:
        reporter = self._make_reporter()
        summary = reporter.finalize()
        assert "T" in summary.end_time
        assert "+" in summary.end_time or summary.end_time.endswith("Z") or "+00:00" in summary.end_time

    def test_finalize_computes_non_negative_duration(self) -> None:
        reporter = self._make_reporter()
        summary = reporter.finalize()
        assert summary.duration_seconds >= 0.0

    def test_finalize_stopped_by_default_is_none(self) -> None:
        reporter = self._make_reporter()
        summary = reporter.finalize()
        assert summary.stopped_by is None

    def test_finalize_stopped_by_max_time(self) -> None:
        reporter = self._make_reporter()
        summary = reporter.finalize(stopped_by="max_time")
        assert summary.stopped_by == "max_time"

    def test_finalize_stopped_by_max_contracts(self) -> None:
        reporter = self._make_reporter()
        summary = reporter.finalize(stopped_by="max_contracts")
        assert summary.stopped_by == "max_contracts"

    def test_total_contracts_equals_sum_of_categories(self) -> None:
        reporter = self._make_reporter()
        reporter.record_success("C001", attachments=1)
        reporter.record_failure("C002", error="err")
        reporter.record_skip("C003")
        summary = reporter.finalize()
        assert summary.total_contracts == summary.successful + summary.failed + summary.skipped


class TestSummaryReporterLogging:
    """Tests for logging behavior."""

    def _make_reporter(self) -> SummaryReporter:
        return SummaryReporter(logger=logging.getLogger("test.summary"))

    def test_record_success_logs_info(self, caplog) -> None:
        with caplog.at_level(logging.INFO, logger="test.summary"):
            reporter = self._make_reporter()
            reporter.record_success("C001", attachments=3)
        assert "C001" in caplog.text
        assert "3" in caplog.text

    def test_record_failure_logs_error(self, caplog) -> None:
        with caplog.at_level(logging.ERROR, logger="test.summary"):
            reporter = self._make_reporter()
            reporter.record_failure("C002", error="connection timeout")
        assert "C002" in caplog.text
        assert "connection timeout" in caplog.text

    def test_record_skip_logs_debug(self, caplog) -> None:
        with caplog.at_level(logging.DEBUG, logger="test.summary"):
            reporter = self._make_reporter()
            reporter.record_skip("C003")
        assert "C003" in caplog.text

    def test_finalize_logs_summary(self, caplog) -> None:
        with caplog.at_level(logging.INFO, logger="test.summary"):
            reporter = self._make_reporter()
            reporter.record_success("C001", attachments=2)
            reporter.finalize()
        assert "Crawl summary" in caplog.text
        assert "Total contracts" in caplog.text

    def test_finalize_logs_stopped_by_when_set(self, caplog) -> None:
        with caplog.at_level(logging.INFO, logger="test.summary"):
            reporter = self._make_reporter()
            reporter.finalize(stopped_by="max_time")
        assert "max_time" in caplog.text

    def test_finalize_does_not_log_stopped_by_when_none(self, caplog) -> None:
        with caplog.at_level(logging.INFO, logger="test.summary"):
            reporter = self._make_reporter()
            reporter.finalize()
        assert "Stopped by" not in caplog.text
