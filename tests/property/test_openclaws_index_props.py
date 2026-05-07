"""Property-based tests for OpenClaws artifact index.

Feature: openclaws-ai-assistant
Property 8: Search results are capped at 20

Validates: Requirements 6.4
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from openclaws.index import ArtifactIndex
from openclaws.models import IndexedArtifact


# =============================================================================
# Strategies for generating IndexedArtifact instances
# =============================================================================

# A common search term that will be embedded in all generated artifacts
_COMMON_TERM = "procurement"

# Strategy for generating a number of artifacts (always > 20 to test the cap)
_artifact_count = st.integers(min_value=21, max_value=60)

# Strategy for generating a unique suffix for each artifact
_unique_suffix = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N")),
    min_size=1,
    max_size=10,
)


def _make_artifact(index: int, suffix: str) -> IndexedArtifact:
    """Create an IndexedArtifact that contains the common search term."""
    return IndexedArtifact(
        contract_id=f"contract-{index}-{suffix}",
        orgao=f"orgao-{index}",
        unidade_gestora=f"ug-{index}",
        contract_number=f"CN-{index:06d}",
        supplier_name=f"{_COMMON_TERM} supplier {index} {suffix}",
        contract_value=f"{(index + 1) * 1000:.2f}",
        start_date="2024-01-01",
        end_date="2024-12-31",
        object_description=f"Object for {_COMMON_TERM} contract {index}",
        extra_fields={},
        attachments=[],
        scraped_at="2024-06-01T00:00:00Z",
        folder_path=f"/target/contracts/{index}",
        pdf_texts={},
    )


# =============================================================================
# Property 8: Search results are capped at 20
# =============================================================================


@settings(max_examples=100, deadline=5000)
@given(
    num_artifacts=_artifact_count,
    suffixes=st.lists(
        _unique_suffix, min_size=60, max_size=60
    ),
)
def test_search_results_never_exceed_20(
    num_artifacts: int,
    suffixes: list[str],
) -> None:
    """Property 8: For any artifact index and any query, the search method
    SHALL return at most 20 results regardless of how many artifacts match.

    Feature: openclaws-ai-assistant, Property 8: Search results are capped at 20

    **Validates: Requirements 6.4**
    """
    index = ArtifactIndex()

    # Add more than 20 artifacts that all contain the common search term
    for i in range(num_artifacts):
        artifact = _make_artifact(i, suffixes[i])
        index.add_artifact(artifact)

    # Search for the common term — all artifacts should match
    results = index.search(_COMMON_TERM)

    # The result count must never exceed 20
    assert len(results) <= 20
    # Since we added > 20 matching artifacts, we expect exactly 20
    assert len(results) == 20


@settings(max_examples=100, deadline=5000)
@given(
    num_artifacts=_artifact_count,
    max_results=st.integers(min_value=1, max_value=50),
    suffixes=st.lists(
        _unique_suffix, min_size=60, max_size=60
    ),
)
def test_search_results_respect_custom_max_results(
    num_artifacts: int,
    max_results: int,
    suffixes: list[str],
) -> None:
    """Property 8 (custom cap): For any artifact index and any max_results
    parameter, the search method SHALL return at most max_results results
    regardless of how many artifacts match.

    Feature: openclaws-ai-assistant, Property 8: Search results are capped at 20

    **Validates: Requirements 6.4**
    """
    index = ArtifactIndex()

    # Add more than max_results artifacts that all contain the common term
    for i in range(num_artifacts):
        artifact = _make_artifact(i, suffixes[i])
        index.add_artifact(artifact)

    # Search with a custom max_results parameter
    results = index.search(_COMMON_TERM, max_results=max_results)

    # The result count must never exceed max_results
    assert len(results) <= max_results

    # If we added more artifacts than max_results, we expect exactly max_results
    if num_artifacts > max_results:
        assert len(results) == max_results


@settings(max_examples=100, deadline=5000)
@given(
    num_artifacts=st.integers(min_value=0, max_value=19),
    suffixes=st.lists(
        _unique_suffix, min_size=19, max_size=19
    ),
)
def test_search_returns_all_matches_when_below_cap(
    num_artifacts: int,
    suffixes: list[str],
) -> None:
    """Property 8 (below cap): When fewer than 20 artifacts match, the search
    method SHALL return all matching artifacts without artificial truncation.

    Feature: openclaws-ai-assistant, Property 8: Search results are capped at 20

    **Validates: Requirements 6.4**
    """
    index = ArtifactIndex()

    # Add fewer than 20 artifacts that all contain the common term
    for i in range(num_artifacts):
        artifact = _make_artifact(i, suffixes[i])
        index.add_artifact(artifact)

    # Search for the common term
    results = index.search(_COMMON_TERM)

    # All matching artifacts should be returned (no artificial truncation)
    assert len(results) == num_artifacts
    # And still respects the cap
    assert len(results) <= 20
