"""Property-based tests for OpenClaws query processing pipeline.

Feature: openclaws-ai-assistant
Property 7: Prompt construction includes all required components

Validates: Requirements 5.4, 6.1
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from openclaws.models import IndexedArtifact, LegislationSnippet, SearchResult
from openclaws.prompt_builder import PromptBuilder


# =============================================================================
# Strategies for generating test data
# =============================================================================

# Strategy for non-empty user queries (1 to 200 chars for practical test speed)
_user_query = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
    min_size=1,
    max_size=200,
).filter(lambda s: s.strip())

# Strategy for non-empty strings used in artifact fields
_non_empty_text = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P")),
    min_size=1,
    max_size=50,
)

# Strategy for folder paths
_folder_path = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="/._-"),
    min_size=3,
    max_size=100,
).filter(lambda s: s.strip())

# Strategy for generating IndexedArtifact instances
_indexed_artifact = st.builds(
    IndexedArtifact,
    contract_id=_non_empty_text,
    orgao=_non_empty_text,
    unidade_gestora=_non_empty_text,
    contract_number=_non_empty_text,
    supplier_name=_non_empty_text,
    contract_value=_non_empty_text,
    start_date=_non_empty_text,
    end_date=_non_empty_text,
    object_description=_non_empty_text,
    extra_fields=st.dictionaries(
        keys=_non_empty_text,
        values=_non_empty_text,
        min_size=0,
        max_size=3,
    ),
    attachments=st.lists(_non_empty_text, min_size=0, max_size=3),
    scraped_at=_non_empty_text,
    folder_path=_folder_path,
    pdf_texts=st.dictionaries(
        keys=_non_empty_text,
        values=_non_empty_text,
        min_size=0,
        max_size=2,
    ),
)

# Strategy for generating SearchResult instances
_search_result = st.builds(
    SearchResult,
    artifact=_indexed_artifact,
    relevance_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    matched_fields=st.lists(_non_empty_text, min_size=1, max_size=5),
)

# Strategy for generating LegislationSnippet instances
_legislation_snippet = st.builds(
    LegislationSnippet,
    source_url=st.from_regex(r"https://[a-z]+\.[a-z]+\.[a-z]+/[a-z]+", fullmatch=True),
    law_name=_non_empty_text,
    content=_non_empty_text,
)

# Strategy for non-empty lists of search results (1 to 5 for test speed)
_artifact_list = st.lists(_search_result, min_size=1, max_size=5)

# Strategy for non-empty lists of legislation snippets (1 to 3 for test speed)
_legislation_list = st.lists(_legislation_snippet, min_size=1, max_size=3)


# =============================================================================
# Property 7: Prompt construction includes all required components
# =============================================================================


@settings(max_examples=100, deadline=5000)
@given(
    user_query=_user_query,
    artifacts=_artifact_list,
    legislation=_legislation_list,
)
def test_prompt_contains_user_query(
    user_query: str,
    artifacts: list[SearchResult],
    legislation: list[LegislationSnippet],
) -> None:
    """Property 7 (a): The constructed prompt SHALL contain the user query text.

    Feature: openclaws-ai-assistant, Property 7: Prompt construction includes all required components

    **Validates: Requirements 5.4, 6.1**
    """
    builder = PromptBuilder()
    prompt = builder.build_prompt(user_query, artifacts, legislation)

    assert user_query in prompt


@settings(max_examples=100, deadline=5000)
@given(
    user_query=_user_query,
    artifacts=_artifact_list,
    legislation=_legislation_list,
)
def test_prompt_contains_artifact_folder_paths(
    user_query: str,
    artifacts: list[SearchResult],
    legislation: list[LegislationSnippet],
) -> None:
    """Property 7 (b): The constructed prompt SHALL contain data from each
    matched artifact including its folder path.

    Feature: openclaws-ai-assistant, Property 7: Prompt construction includes all required components

    **Validates: Requirements 5.4, 6.1**
    """
    builder = PromptBuilder()
    prompt = builder.build_prompt(user_query, artifacts, legislation)

    for result in artifacts:
        assert result.artifact.folder_path in prompt


@settings(max_examples=100, deadline=5000)
@given(
    user_query=_user_query,
    artifacts=_artifact_list,
    legislation=_legislation_list,
)
def test_prompt_contains_artifact_metadata_fields(
    user_query: str,
    artifacts: list[SearchResult],
    legislation: list[LegislationSnippet],
) -> None:
    """Property 7 (b): The constructed prompt SHALL contain data from each
    matched artifact including its metadata fields.

    Feature: openclaws-ai-assistant, Property 7: Prompt construction includes all required components

    **Validates: Requirements 5.4, 6.1**
    """
    builder = PromptBuilder()
    prompt = builder.build_prompt(user_query, artifacts, legislation)

    for result in artifacts:
        artifact = result.artifact
        assert artifact.contract_id in prompt
        assert artifact.contract_number in prompt
        assert artifact.orgao in prompt
        assert artifact.unidade_gestora in prompt
        assert artifact.supplier_name in prompt
        assert artifact.contract_value in prompt
        assert artifact.start_date in prompt
        assert artifact.end_date in prompt
        assert artifact.object_description in prompt


@settings(max_examples=100, deadline=5000)
@given(
    user_query=_user_query,
    artifacts=_artifact_list,
    legislation=_legislation_list,
)
def test_prompt_contains_legislation_snippets(
    user_query: str,
    artifacts: list[SearchResult],
    legislation: list[LegislationSnippet],
) -> None:
    """Property 7 (c): The constructed prompt SHALL contain at least one
    legislation snippet with citation instructions.

    Feature: openclaws-ai-assistant, Property 7: Prompt construction includes all required components

    **Validates: Requirements 5.4, 6.1**
    """
    builder = PromptBuilder()
    prompt = builder.build_prompt(user_query, artifacts, legislation)

    # Verify at least one legislation snippet content is present
    legislation_found = any(snippet.content in prompt for snippet in legislation)
    assert legislation_found

    # Verify at least one law name is present
    law_name_found = any(snippet.law_name in prompt for snippet in legislation)
    assert law_name_found

    # Verify citation instructions are present in the prompt
    assert "CITATION INSTRUCTIONS" in prompt or "citation" in prompt.lower()


# =============================================================================
# Property 6: Search returns only artifacts containing query terms
# =============================================================================


# Strategy for generating query terms that are simple lowercase words
_query_term = st.text(
    alphabet=st.characters(whitelist_categories=("L",)),
    min_size=2,
    max_size=15,
).map(lambda s: s.lower()).filter(lambda s: len(s.strip()) >= 2)

# Strategy for generating a non-empty query (1 to 3 terms joined by spaces)
_search_query = st.lists(_query_term, min_size=1, max_size=3).map(
    lambda terms: " ".join(terms)
)

# Strategy for generating artifact field values that may or may not contain a term
_field_value = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
    min_size=1,
    max_size=80,
)

# Strategy for generating IndexedArtifact with controlled field values
_artifact_for_search = st.builds(
    IndexedArtifact,
    contract_id=_field_value,
    orgao=_field_value,
    unidade_gestora=_field_value,
    contract_number=_field_value,
    supplier_name=_field_value,
    contract_value=_field_value,
    start_date=_field_value,
    end_date=_field_value,
    object_description=_field_value,
    extra_fields=st.just({}),
    attachments=st.just([]),
    scraped_at=_field_value,
    folder_path=_folder_path,
    pdf_texts=st.dictionaries(
        keys=st.text(
            alphabet=st.characters(whitelist_categories=("L", "N")),
            min_size=1,
            max_size=20,
        ),
        values=_field_value,
        min_size=0,
        max_size=2,
    ),
)


from openclaws.index import ArtifactIndex


@settings(max_examples=100, deadline=10000)
@given(
    query=_search_query,
    artifacts=st.lists(_artifact_for_search, min_size=1, max_size=15),
)
def test_search_results_contain_query_terms(
    query: str,
    artifacts: list[IndexedArtifact],
) -> None:
    """Property 6: Every artifact in search results SHALL contain at least one
    query term in a searchable field (contract_id, contract_number,
    supplier_name, object_description, or extracted PDF text).

    Feature: openclaws-ai-assistant, Property 6: Search returns only artifacts containing query terms

    **Validates: Requirements 5.3**
    """
    # Build the index
    index = ArtifactIndex()
    for artifact in artifacts:
        index.add_artifact(artifact)

    # Perform the search
    results = index.search(query)

    # Extract query terms (same logic as ArtifactIndex.search)
    terms = query.lower().split()

    # Verify every result contains at least one query term in a searchable field
    for result in results:
        artifact = result.artifact

        # Collect all searchable field content (lowercased)
        searchable_content = [
            artifact.contract_id.lower() if artifact.contract_id else "",
            artifact.contract_number.lower() if artifact.contract_number else "",
            artifact.supplier_name.lower() if artifact.supplier_name else "",
            artifact.object_description.lower() if artifact.object_description else "",
        ]

        # Add PDF text content
        for _filename, text in artifact.pdf_texts.items():
            if text:
                searchable_content.append(text.lower())

        # At least one term must appear in at least one searchable field
        term_found = False
        for term in terms:
            for content in searchable_content:
                if term in content:
                    term_found = True
                    break
            if term_found:
                break

        assert term_found, (
            f"Artifact with contract_id='{artifact.contract_id}' was returned "
            f"in search results for query '{query}' but none of the query terms "
            f"{terms} were found in any searchable field."
        )


# =============================================================================
# Property 9: Truncation notice when results exceed limit
# =============================================================================

from unittest.mock import MagicMock

from openclaws.index import ArtifactIndex
from openclaws.query_engine import QueryEngine, _TRUNCATION_NOTICE


def _make_artifact_with_term(term: str, index: int) -> IndexedArtifact:
    """Create an IndexedArtifact that contains the given term in object_description."""
    return IndexedArtifact(
        contract_id=f"contract-{index}",
        orgao=f"orgao-{index}",
        unidade_gestora=f"ug-{index}",
        contract_number=f"CN-{index}",
        supplier_name=f"supplier-{index}",
        contract_value=f"{index * 1000}.00",
        start_date="2024-01-01",
        end_date="2024-12-31",
        object_description=f"This contract is about {term} services number {index}",
        extra_fields={},
        attachments=[],
        scraped_at="2024-06-01T00:00:00Z",
        folder_path=f"/target/org/ug/contract-{index}",
        pdf_texts={},
    )


@settings(max_examples=100, deadline=30000)
@given(
    num_artifacts=st.integers(min_value=21, max_value=40),
    common_term=st.text(
        alphabet=st.characters(whitelist_categories=("Ll",)),
        min_size=4,
        max_size=15,
    ).filter(lambda s: s.strip() and s.isalpha()),
)
def test_truncation_notice_when_results_exceed_limit(
    num_artifacts: int,
    common_term: str,
) -> None:
    """Property 9: For any query that matches more than 20 artifacts in the index,
    the query response SHALL include a notice informing the user that results are
    limited to the first 20 matches and suggesting query refinement.

    Feature: openclaws-ai-assistant, Property 9: Truncation notice when results exceed limit

    **Validates: Requirements 6.6**
    """
    # Build an index with more than 20 artifacts all containing the common term
    artifact_index = ArtifactIndex()
    for i in range(num_artifacts):
        artifact = _make_artifact_with_term(common_term, i)
        artifact_index.add_artifact(artifact)

    # Mock the GraniteClient to return a simple response
    mock_granite = MagicMock()
    from openclaws.models import GenerationResult

    mock_granite.generate.return_value = GenerationResult(
        text=f"Analysis of contracts related to {common_term}.",
        prompt_tokens=100,
        completion_tokens=50,
    )

    # Mock the LegislationCache to return empty list
    mock_legislation = MagicMock()
    mock_legislation.get_relevant_content.return_value = []

    # Use a real PromptBuilder
    prompt_builder = PromptBuilder()

    # Create the QueryEngine with real index and mocked dependencies
    engine = QueryEngine(
        index=artifact_index,
        legislation=mock_legislation,
        granite_client=mock_granite,
        prompt_builder=prompt_builder,
    )

    # Process the query using the common term (should match all artifacts)
    response = engine.process_query(common_term)

    # Verify the truncation notice is present in the answer
    assert "more than 20 contracts" in response.answer, (
        f"Expected truncation notice containing 'more than 20 contracts' "
        f"in response answer when {num_artifacts} artifacts match, "
        f"but got: {response.answer[-200:]}"
    )
    assert "refining your query" in response.answer, (
        f"Expected truncation notice containing 'refining your query' "
        f"in response answer when {num_artifacts} artifacts match, "
        f"but got: {response.answer[-200:]}"
    )

    # Verify the response only references up to 20 contracts
    assert len(response.referenced_contracts) <= 20, (
        f"Expected at most 20 referenced contracts but got "
        f"{len(response.referenced_contracts)}"
    )
