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
