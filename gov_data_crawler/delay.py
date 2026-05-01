"""Configurable random delay mechanism between HTTP requests."""

import logging
import random
import time

logger = logging.getLogger(__name__)


class DelayMechanism:
    """Configurable random delay between requests.

    Generates random delays within configurable min/max bounds to simulate
    human browsing behavior and avoid triggering anti-bot protections.
    """

    def __init__(self, min_seconds: float = 2.0, max_seconds: float = 5.0) -> None:
        """Initialize with min/max delay bounds.

        If min > max, values are swapped and a warning is logged.

        Args:
            min_seconds: Minimum delay in seconds (default: 2.0).
            max_seconds: Maximum delay in seconds (default: 5.0).
        """
        if min_seconds > max_seconds:
            logger.warning(
                "min_seconds (%.2f) is greater than max_seconds (%.2f), swapping values",
                min_seconds,
                max_seconds,
            )
            min_seconds, max_seconds = max_seconds, min_seconds

        self._min_seconds = min_seconds
        self._max_seconds = max_seconds

    def wait(self) -> float:
        """Pause execution for a random duration within bounds.

        Returns:
            The actual delay duration in seconds.
        """
        delay = random.uniform(self._min_seconds, self._max_seconds)
        logger.debug("Waiting %.2f seconds", delay)
        time.sleep(delay)
        return delay

    @property
    def min_seconds(self) -> float:
        """Return the configured minimum delay in seconds."""
        return self._min_seconds

    @property
    def max_seconds(self) -> float:
        """Return the configured maximum delay in seconds."""
        return self._max_seconds
