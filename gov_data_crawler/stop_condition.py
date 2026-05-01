"""Stop condition checker for evaluating crawl stopping criteria."""

import logging
import time


class StopConditionChecker:
    """Evaluates crawl stopping criteria during execution.

    Supports optional max_time (elapsed seconds) and max_contracts
    (successful count) limits. When no limits are configured, the
    checker never signals a stop.
    """

    def __init__(
        self,
        max_time: float | None = None,
        max_contracts: int | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialize with optional stopping limits.

        Args:
            max_time: Maximum execution time in seconds, or None for no limit.
            max_contracts: Maximum number of successfully processed contracts,
                or None for no limit.
            logger: Logger instance for stop condition messages.
        """
        self._max_time = max_time
        self._max_contracts = max_contracts
        self._logger = logger or logging.getLogger(__name__)
        self._start_time: float | None = None
        self._triggered_condition: str | None = None

    def start(self) -> None:
        """Record the start time of the crawl. Must be called before should_stop."""
        self._start_time = time.monotonic()
        self._triggered_condition = None
        self._logger.debug("Stop condition checker started")

    def should_stop(self, successful_count: int) -> bool:
        """Check whether any stopping condition has been met.

        Args:
            successful_count: Number of contracts successfully processed so far.

        Returns:
            True if any configured stopping condition is met.
        """
        if self._start_time is None:
            raise RuntimeError("start() must be called before should_stop()")

        # Check max_time condition
        if self._max_time is not None:
            elapsed = time.monotonic() - self._start_time
            if elapsed >= self._max_time:
                self._triggered_condition = "max_time"
                self._logger.info(
                    "Stop condition met: max_time (%.2f >= %.2f seconds)",
                    elapsed,
                    self._max_time,
                )
                return True

        # Check max_contracts condition
        if self._max_contracts is not None:
            if successful_count >= self._max_contracts:
                self._triggered_condition = "max_contracts"
                self._logger.info(
                    "Stop condition met: max_contracts (%d >= %d)",
                    successful_count,
                    self._max_contracts,
                )
                return True

        return False

    @property
    def triggered_condition(self) -> str | None:
        """Return the name of the condition that triggered the stop, or None.

        Returns:
            'max_time', 'max_contracts', or None if no condition was triggered.
        """
        return self._triggered_condition
