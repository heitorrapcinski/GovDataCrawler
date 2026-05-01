"""Property-based tests for the SummaryReporter component.

Feature: gov-data-crawler
Property 8: summary counts are accurate

Validates: Requirements 6.5
"""

import logging

from hypothesis import given, settings
from hypothesis import strategies as st

from gov_data_crawler.summary import SummaryReporter

# Strategy for a single event: (type, contract_id, attachments_or_error)
# type: 0 = success, 1 = failure, 2 = skip
event_strategy = st.tuples(
    st.integers(min_value=0, max_value=2),
    st.text(
        alphabet=st.characters(whitelist_categories=("L", "N")),
        min_size=1,
        max_size=20,
    ),
    st.integers(min_value=0, max_value=1000),
)


@settings(max_examples=100, deadline=1000)
@given(events=st.lists(event_strategy, min_size=0, max_size=50))
def test_summary_counts_are_accurate(
    events: list[tuple[int, str, int]],
) -> None:
    """Property 8: For any sequence of record_success, record_failure, and
    record_skip calls with arbitrary contract IDs and attachment counts, the
    CrawlSummary returned by finalize SHALL have
    successful + failed + skipped == total_contracts and
    attachments_downloaded SHALL equal the sum of all attachment counts from
    success records.

    **Validates: Requirements 6.5**
    """
    logger = logging.getLogger("test.property.summary")
    reporter = SummaryReporter(logger=logger)

    expected_successful = 0
    expected_failed = 0
    expected_skipped = 0
    expected_attachments = 0

    for event_type, contract_id, attachment_count in events:
        if event_type == 0:
            reporter.record_success(contract_id, attachments=attachment_count)
            expected_successful += 1
            expected_attachments += attachment_count
        elif event_type == 1:
            reporter.record_failure(contract_id, error="test error")
            expected_failed += 1
        else:
            reporter.record_skip(contract_id)
            expected_skipped += 1

    summary = reporter.finalize()

    # Property: successful + failed + skipped == total_contracts
    assert summary.successful + summary.failed + summary.skipped == summary.total_contracts

    # Property: individual counts match expected values
    assert summary.successful == expected_successful
    assert summary.failed == expected_failed
    assert summary.skipped == expected_skipped

    # Property: attachments_downloaded equals sum of attachment counts from successes
    assert summary.attachments_downloaded == expected_attachments
