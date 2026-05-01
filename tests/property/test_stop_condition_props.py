"""Property-based tests for the StopConditionChecker component.

Feature: gov-data-crawler
Property 10: stop condition checker correctly evaluates stopping criteria

Validates: Requirements 8.1, 8.2, 8.3, 8.6
"""

from unittest.mock import patch

from hypothesis import given, settings
from hypothesis import strategies as st

from gov_data_crawler.stop_condition import StopConditionChecker

# Strategy for optional max_time: None or a positive float
max_time_strategy = st.one_of(st.none(), st.floats(min_value=0.0, max_value=3600.0))

# Strategy for optional max_contracts: None or a non-negative integer
max_contracts_strategy = st.one_of(
    st.none(), st.integers(min_value=0, max_value=10000)
)

# Strategy for elapsed time (simulated via monotonic clock offset)
elapsed_time_strategy = st.floats(min_value=0.0, max_value=7200.0)

# Strategy for successful contract count
successful_count_strategy = st.integers(min_value=0, max_value=20000)


@settings(max_examples=100, deadline=1000)
@given(
    max_time=max_time_strategy,
    max_contracts=max_contracts_strategy,
    elapsed=elapsed_time_strategy,
    successful_count=successful_count_strategy,
)
def test_stop_condition_evaluates_correctly(
    max_time: float | None,
    max_contracts: int | None,
    elapsed: float,
    successful_count: int,
) -> None:
    """Property 10: For any configuration of optional max_time and optional
    max_contracts limits (including None for no limit), and for any state of
    elapsed time and successful contract count, StopConditionChecker.should_stop
    SHALL return True if and only if at least one configured limit has been
    reached or exceeded. When no limits are configured, it SHALL always return
    False.

    **Validates: Requirements 8.1, 8.2, 8.3, 8.6**
    """
    checker = StopConditionChecker(max_time=max_time, max_contracts=max_contracts)

    start_time = 1000.0
    check_time = start_time + elapsed

    with patch("gov_data_crawler.stop_condition.time.monotonic") as mock_monotonic:
        mock_monotonic.side_effect = [start_time, check_time]
        checker.start()
        result = checker.should_stop(successful_count)

    # Compute expected result using the same arithmetic path as the implementation:
    # The implementation computes elapsed as (check_time - start_time), which may
    # differ from the original `elapsed` due to floating-point rounding.
    actual_elapsed = check_time - start_time
    time_exceeded = max_time is not None and actual_elapsed >= max_time
    contracts_exceeded = max_contracts is not None and successful_count >= max_contracts
    expected = time_exceeded or contracts_exceeded

    assert result == expected, (
        f"should_stop returned {result}, expected {expected}. "
        f"max_time={max_time}, max_contracts={max_contracts}, "
        f"elapsed={elapsed}, actual_elapsed={actual_elapsed}, "
        f"successful_count={successful_count}"
    )

    # Verify triggered_condition is consistent
    if result:
        assert checker.triggered_condition is not None
        assert checker.triggered_condition in ("max_time", "max_contracts")
    else:
        assert checker.triggered_condition is None
