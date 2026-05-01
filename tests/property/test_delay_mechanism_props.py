"""Property-based tests for the DelayMechanism component.

Feature: gov-data-crawler
Property 6: delay always within bounds after auto-correction

Validates: Requirements 4.2, 4.5
"""

from unittest.mock import patch

from hypothesis import given, settings
from hypothesis import strategies as st

from gov_data_crawler.delay import DelayMechanism


@settings(max_examples=100, deadline=1000)
@given(
    min_val=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    max_val=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
)
@patch("gov_data_crawler.delay.time.sleep")
def test_delay_always_within_bounds_after_auto_correction(
    mock_sleep, min_val: float, max_val: float
) -> None:
    """Property 6: For any pair of min and max delay values (including cases
    where min > max, which triggers auto-swap), every delay produced by
    DelayMechanism.wait SHALL be >= min(min_input, max_input) and
    <= max(min_input, max_input).

    **Validates: Requirements 4.2, 4.5**
    """
    expected_lower = min(min_val, max_val)
    expected_upper = max(min_val, max_val)

    mechanism = DelayMechanism(min_seconds=min_val, max_seconds=max_val)

    # Verify the bounds are correctly set after auto-correction
    assert mechanism.min_seconds == expected_lower
    assert mechanism.max_seconds == expected_upper

    # Verify the delay produced is within bounds
    delay = mechanism.wait()
    assert expected_lower <= delay <= expected_upper

    # Verify sleep was called with the delay value
    mock_sleep.assert_called_once_with(delay)
