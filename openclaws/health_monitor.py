"""Periodic health monitoring for the Granite Service."""

import logging
import threading

from openclaws.granite_client import GraniteClient
from openclaws.models import HealthStatus

logger = logging.getLogger(__name__)


class HealthMonitor:
    """Monitors the Granite Service health at a configurable interval.

    Periodically calls the Granite health check endpoint and tracks
    consecutive failures. Logs a warning on each unhealthy/unreachable
    response, and logs an error after 3 consecutive failures.
    """

    def __init__(self, granite_client: GraniteClient, interval: int = 30) -> None:
        """Initialize the health monitor.

        Args:
            granite_client: The GraniteClient instance used for health checks.
            interval: Seconds between health checks (5–300, default 30).

        Raises:
            ValueError: If interval is outside the valid range (5–300).
        """
        if not (5 <= interval <= 300):
            raise ValueError(
                f"Health check interval must be between 5 and 300 seconds, "
                f"got {interval}"
            )

        self._granite_client = granite_client
        self._interval = interval
        self._consecutive_failures = 0
        self._running = False
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()

    @property
    def consecutive_failures(self) -> int:
        """Return the current consecutive failure count."""
        with self._lock:
            return self._consecutive_failures

    def check_once(self) -> HealthStatus:
        """Perform a single health check against the Granite Service.

        Calls granite_client.health_check(timeout=5) and updates the
        consecutive failure counter accordingly.

        Returns:
            The HealthStatus result from the health check.
        """
        status = self._granite_client.health_check(timeout=5)

        with self._lock:
            if status == HealthStatus.HEALTHY:
                self._consecutive_failures = 0
            else:
                self._consecutive_failures += 1
                logger.warning(
                    "Granite Service health check failed: status=%s "
                    "(consecutive failures: %d)",
                    status.value,
                    self._consecutive_failures,
                )
                if self._consecutive_failures >= 3:
                    logger.error(
                        "Granite Service is degraded: %d consecutive health "
                        "check failures detected",
                        self._consecutive_failures,
                    )

        return status

    def start(self) -> None:
        """Start periodic health checking in a background thread.

        The first check runs after one interval period. Subsequent checks
        continue at the configured interval until stop() is called.
        """
        self._running = True
        self._schedule_next()

    def stop(self) -> None:
        """Stop periodic health checking.

        Cancels any pending timer. Safe to call multiple times.
        """
        self._running = False
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def _schedule_next(self) -> None:
        """Schedule the next health check after the configured interval."""
        if not self._running:
            return
        self._timer = threading.Timer(self._interval, self._run_check)
        self._timer.daemon = True
        self._timer.start()

    def _run_check(self) -> None:
        """Execute a health check and schedule the next one."""
        if not self._running:
            return
        self.check_once()
        self._schedule_next()
