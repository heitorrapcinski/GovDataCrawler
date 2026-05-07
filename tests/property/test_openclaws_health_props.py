"""Property-based tests for OpenClaws health monitor.

Feature: openclaws-ai-assistant
Property 10: Health monitor detects consecutive failures

Validates: Requirements 7.5
"""

import logging
from unittest.mock import MagicMock, patch

from hypothesis import given, settings
from hypothesis import strategies as st

from openclaws.granite_client import GraniteClient
from openclaws.health_monitor import HealthMonitor
from openclaws.models import HealthStatus


# =============================================================================
# Property 10: Health monitor detects consecutive failures
# =============================================================================

# Strategy: generate sequences of health check results (True = healthy, False = failure)
_health_check_sequence = st.lists(
    st.sampled_from([HealthStatus.HEALTHY, HealthStatus.UNHEALTHY, HealthStatus.UNREACHABLE]),
    min_size=1,
    max_size=50,
)


def _has_3_or_more_consecutive_failures(sequence: list[HealthStatus]) -> bool:
    """Check if a sequence contains 3 or more consecutive failures."""
    consecutive = 0
    for status in sequence:
        if status != HealthStatus.HEALTHY:
            consecutive += 1
            if consecutive >= 3:
                return True
        else:
            consecutive = 0
    return False


def _count_error_log_triggers(sequence: list[HealthStatus]) -> int:
    """Count how many times the error log should be triggered.

    The error log triggers every time consecutive_failures >= 3 after
    an increment (i.e., on the 3rd, 4th, 5th, ... consecutive failure).
    """
    consecutive = 0
    error_count = 0
    for status in sequence:
        if status != HealthStatus.HEALTHY:
            consecutive += 1
            if consecutive >= 3:
                error_count += 1
        else:
            consecutive = 0
    return error_count


@settings(max_examples=100, deadline=2000)
@given(sequence=_health_check_sequence)
def test_health_monitor_logs_error_iff_3_consecutive_failures(
    sequence: list[HealthStatus],
) -> None:
    """Property 10: For any sequence of health check results, the health monitor
    SHALL log an error-level message if and only if the sequence contains 3 or
    more consecutive failures (unhealthy or unreachable). Sequences with fewer
    than 3 consecutive failures SHALL not trigger the error log.

    Feature: openclaws-ai-assistant, Property 10: Health monitor detects consecutive failures

    **Validates: Requirements 7.5**
    """
    # Create a mock GraniteClient that returns statuses from the sequence
    mock_client = MagicMock(spec=GraniteClient)
    status_iter = iter(sequence)
    mock_client.health_check.side_effect = lambda timeout=5: next(status_iter)

    # Create the health monitor with the mock client
    monitor = HealthMonitor(granite_client=mock_client, interval=30)

    # Track error-level log calls
    with patch("openclaws.health_monitor.logger") as mock_logger:
        for _ in sequence:
            monitor.check_once()

        # Determine expected behavior
        expected_has_error = _has_3_or_more_consecutive_failures(sequence)
        expected_error_count = _count_error_log_triggers(sequence)

        # Verify: error log triggered if and only if 3+ consecutive failures
        actual_error_count = mock_logger.error.call_count

        if expected_has_error:
            assert actual_error_count > 0, (
                f"Expected error log for sequence with 3+ consecutive failures, "
                f"but got 0 error calls. Sequence: {[s.value for s in sequence]}"
            )
            assert actual_error_count == expected_error_count, (
                f"Expected {expected_error_count} error log calls, "
                f"got {actual_error_count}. Sequence: {[s.value for s in sequence]}"
            )
        else:
            assert actual_error_count == 0, (
                f"Expected no error log for sequence without 3+ consecutive "
                f"failures, but got {actual_error_count} error calls. "
                f"Sequence: {[s.value for s in sequence]}"
            )


@settings(max_examples=100, deadline=2000)
@given(sequence=_health_check_sequence)
def test_health_monitor_resets_counter_on_success(
    sequence: list[HealthStatus],
) -> None:
    """Property 10 (counter reset): For any sequence of health check results,
    a HEALTHY result SHALL reset the consecutive failure counter to zero,
    ensuring that subsequent failures start counting from zero.

    Feature: openclaws-ai-assistant, Property 10: Health monitor detects consecutive failures

    **Validates: Requirements 7.5**
    """
    # Create a mock GraniteClient that returns statuses from the sequence
    mock_client = MagicMock(spec=GraniteClient)
    status_iter = iter(sequence)
    mock_client.health_check.side_effect = lambda timeout=5: next(status_iter)

    # Create the health monitor with the mock client
    monitor = HealthMonitor(granite_client=mock_client, interval=30)

    # Process the sequence and verify counter behavior
    expected_consecutive = 0
    for status in sequence:
        monitor.check_once()
        if status == HealthStatus.HEALTHY:
            expected_consecutive = 0
        else:
            expected_consecutive += 1

        assert monitor.consecutive_failures == expected_consecutive, (
            f"After processing status={status.value}, expected "
            f"consecutive_failures={expected_consecutive}, "
            f"got {monitor.consecutive_failures}"
        )


@settings(max_examples=100, deadline=2000)
@given(
    prefix_failures=st.integers(min_value=0, max_value=10),
    suffix_failures=st.integers(min_value=0, max_value=10),
)
def test_health_monitor_no_error_below_threshold(
    prefix_failures: int,
    suffix_failures: int,
) -> None:
    """Property 10 (below threshold): For any sequence where no run of
    consecutive failures reaches 3, the health monitor SHALL NOT log any
    error-level message.

    Feature: openclaws-ai-assistant, Property 10: Health monitor detects consecutive failures

    **Validates: Requirements 7.5**
    """
    # Build a sequence that never has 3+ consecutive failures:
    # up to 2 failures, then a success, then up to 2 failures
    capped_prefix = min(prefix_failures, 2)
    capped_suffix = min(suffix_failures, 2)

    sequence: list[HealthStatus] = []
    for _ in range(capped_prefix):
        sequence.append(HealthStatus.UNHEALTHY)
    sequence.append(HealthStatus.HEALTHY)
    for _ in range(capped_suffix):
        sequence.append(HealthStatus.UNREACHABLE)

    # Create a mock GraniteClient
    mock_client = MagicMock(spec=GraniteClient)
    status_iter = iter(sequence)
    mock_client.health_check.side_effect = lambda timeout=5: next(status_iter)

    monitor = HealthMonitor(granite_client=mock_client, interval=30)

    with patch("openclaws.health_monitor.logger") as mock_logger:
        for _ in sequence:
            monitor.check_once()

        # No error should be logged since max consecutive failures is 2
        assert mock_logger.error.call_count == 0, (
            f"Expected no error log for sequence with max 2 consecutive "
            f"failures, but got {mock_logger.error.call_count} error calls. "
            f"Sequence: {[s.value for s in sequence]}"
        )
