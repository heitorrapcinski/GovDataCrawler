"""Summary reporter for tracking and reporting crawl execution statistics."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gov_data_crawler.listing import FilterParameters


@dataclass
class CrawlSummary:
    """Execution statistics for a crawl run."""

    total_contracts: int
    successful: int
    failed: int
    skipped: int
    attachments_downloaded: int
    start_time: str
    end_time: str
    duration_seconds: float
    stopped_by: str | None = None  # "max_time", "max_contracts", or None
    filters: dict[str, str] | None = None  # Active filter params, or None


class SummaryReporter:
    """Tracks and reports crawl execution statistics.

    Records successes, failures, and skips during a crawl run, then
    produces a CrawlSummary with computed duration and totals.
    """

    def __init__(self, logger: logging.Logger, filters: FilterParameters | None = None) -> None:
        """Initialize the reporter and record the start time.

        Args:
            logger: Logger instance for summary output.
            filters: Optional filter parameters to include in the summary.
        """
        self._logger = logger
        self._filters = filters
        self._successful = 0
        self._failed = 0
        self._skipped = 0
        self._attachments_downloaded = 0
        self._start_time = datetime.now(timezone.utc)

    def record_success(self, contract_id: str, attachments: int) -> None:
        """Record a successfully processed contract.

        Args:
            contract_id: The contract ID that was processed.
            attachments: Number of attachments downloaded for this contract.
        """
        self._successful += 1
        self._attachments_downloaded += attachments
        self._logger.info(
            "Contract %s processed successfully (%d attachments)",
            contract_id,
            attachments,
        )

    def record_failure(self, contract_id: str, error: str) -> None:
        """Record a failed contract processing attempt.

        Args:
            contract_id: The contract ID that failed.
            error: Description of the error that occurred.
        """
        self._failed += 1
        self._logger.error("Contract %s failed: %s", contract_id, error)

    def record_skip(self, contract_id: str) -> None:
        """Record a skipped contract (already processed).

        Args:
            contract_id: The contract ID that was skipped.
        """
        self._skipped += 1
        self._logger.debug("Contract %s skipped (already processed)", contract_id)

    def finalize(self, stopped_by: str | None = None) -> CrawlSummary:
        """Produce a CrawlSummary and log the results.

        Args:
            stopped_by: The stop condition that ended the crawl, if any.
                One of "max_time", "max_contracts", or None.

        Returns:
            CrawlSummary with all execution statistics.
        """
        end_time = datetime.now(timezone.utc)
        duration = (end_time - self._start_time).total_seconds()

        summary = CrawlSummary(
            total_contracts=self._successful + self._failed + self._skipped,
            successful=self._successful,
            failed=self._failed,
            skipped=self._skipped,
            attachments_downloaded=self._attachments_downloaded,
            start_time=self._start_time.isoformat(),
            end_time=end_time.isoformat(),
            duration_seconds=duration,
            stopped_by=stopped_by,
            filters=self._filters.to_post_params() if self._filters and self._filters.has_filters else None,
        )

        self._logger.info("Crawl summary:")
        self._logger.info("  Total contracts: %d", summary.total_contracts)
        self._logger.info("  Successful: %d", summary.successful)
        self._logger.info("  Failed: %d", summary.failed)
        self._logger.info("  Skipped: %d", summary.skipped)
        self._logger.info(
            "  Attachments downloaded: %d", summary.attachments_downloaded
        )
        self._logger.info("  Duration: %.2f seconds", summary.duration_seconds)
        if summary.stopped_by:
            self._logger.info("  Stopped by: %s", summary.stopped_by)
        if summary.filters:
            self._logger.info("  Filters: %s", summary.filters)

        return summary
