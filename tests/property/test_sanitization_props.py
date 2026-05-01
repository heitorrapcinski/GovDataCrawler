"""Property-based tests for folder name sanitization.

Feature: gov-data-crawler
Property 7: sanitization removes invalid characters and is idempotent

Validates: Requirements 5.4
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from gov_data_crawler.output import OutputManager

# Characters that are invalid in Windows, Linux, or macOS file paths
INVALID_CHARS = set('<>:"/\\|?*')


@settings(max_examples=100, deadline=1000)
@given(name=st.text(min_size=0, max_size=200))
def test_sanitization_removes_all_invalid_characters(name: str) -> None:
    """Property 7 (part 1): For any input string, sanitize_folder_name SHALL
    produce a string containing no characters that are invalid in Windows,
    Linux, or macOS file paths.

    **Validates: Requirements 5.4**
    """
    sanitized = OutputManager.sanitize_folder_name(name)
    remaining_invalid = INVALID_CHARS.intersection(set(sanitized))
    assert remaining_invalid == set(), (
        f"Sanitized name '{sanitized}' still contains invalid chars: {remaining_invalid}"
    )


@settings(max_examples=100, deadline=1000)
@given(name=st.text(min_size=0, max_size=200))
def test_sanitization_is_idempotent(name: str) -> None:
    """Property 7 (part 2): Applying sanitization twice SHALL produce the
    same result as applying it once (idempotence).

    **Validates: Requirements 5.4**
    """
    once = OutputManager.sanitize_folder_name(name)
    twice = OutputManager.sanitize_folder_name(once)
    assert once == twice, (
        f"Sanitization is not idempotent: first='{once}', second='{twice}'"
    )
