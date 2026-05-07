"""Unit tests for openclaws.query_engine module."""

from unittest.mock import MagicMock, patch

import pytest

from openclaws.granite_client import (
    GraniteClient,
    GraniteConnectionError,
    GraniteContextExceededError,
    GraniteModelLoadingError,
    GraniteTimeoutError,
)
from openclaws.index import ArtifactIndex
from openclaws.legislation import LegislationCache
from openclaws.models import (
    GenerationResult,
    IndexedArtifact,
    LegislationSnippet,
    QueryResponse,
    SearchResult,
)
from openclaws.prompt_builder import PromptBuilder
from openclaws.query_engine import QueryEngine


def _make_artifact(contract_id: str = "CT-001", **kwargs) -> IndexedArtifact:
    """Create a test artifact with sensible defaults."""
    defaults = {
        "contract_id": contract_id,
        "orgao": "Orgao Test",
        "unidade_gestora": "UG-001",
        "contract_number": "2024/001",
        "supplier_name": "Supplier ABC",
        "contract_value": "R$ 100.000,00",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "object_description": "Servicos de TI",
        "extra_fields": {},
        "attachments": [],
        "scraped_at": "2024-06-01T10:00:00",
        "folder_path": "/target/contratos/orgao/ug/CT-001",
        "pdf_texts": {},
    }
    defaults.update(kwargs)
    return IndexedArtifact(**defaults)


def _make_search_result(
    contract_id: str = "CT-001", score: float = 1.0
) -> SearchResult:
    """Create a test search result."""
    return SearchResult(
        artifact=_make_artifact(contract_id=contract_id),
        relevance_score=score,
        matched_fields=["contract_id"],
    )


def _make_query_engine(
    index=None, legislation=None, granite_client=None, prompt_builder=None
):
    """Create a QueryEngine with mock dependencies."""
    if index is None:
        index = MagicMock(spec=ArtifactIndex)
        index.search.return_value = []
    if legislation is None:
        legislation = MagicMock(spec=LegislationCache)
        legislation.get_relevant_content.return_value = []
    if granite_client is None:
        granite_client = MagicMock(spec=GraniteClient)
        granite_client.generate.return_value = GenerationResult(
            text="Test answer", prompt_tokens=100, completion_tokens=50
        )
    if prompt_builder is None:
        prompt_builder = MagicMock(spec=PromptBuilder)
        prompt_builder.build_prompt.return_value = "test prompt"

    return QueryEngine(index, legislation, granite_client, prompt_builder)


class TestQueryEngineInit:
    """Test QueryEngine initialization."""

    def test_stores_dependencies(self):
        index = MagicMock(spec=ArtifactIndex)
        legislation = MagicMock(spec=LegislationCache)
        granite_client = MagicMock(spec=GraniteClient)
        prompt_builder = MagicMock(spec=PromptBuilder)

        engine = QueryEngine(index, legislation, granite_client, prompt_builder)

        assert engine._index is index
        assert engine._legislation is legislation
        assert engine._granite_client is granite_client
        assert engine._prompt_builder is prompt_builder


class TestQueryEngineNoMatch:
    """Test no-match case: inform user no artifacts found, suggest refining query."""

    def test_no_match_returns_informative_message(self):
        """Validates: Requirements 5.8"""
        index = MagicMock(spec=ArtifactIndex)
        index.search.return_value = []

        engine = _make_query_engine(index=index)
        response = engine.process_query("nonexistent contract xyz")

        assert isinstance(response, QueryResponse)
        assert "no matching artifacts" in response.answer.lower()
        assert "refin" in response.answer.lower()
        assert response.referenced_contracts == []
        assert response.legislation_citations == []

    def test_no_match_does_not_call_granite(self):
        """Validates: Requirements 5.8 — no inference call when no matches."""
        index = MagicMock(spec=ArtifactIndex)
        index.search.return_value = []
        granite_client = MagicMock(spec=GraniteClient)

        engine = _make_query_engine(index=index, granite_client=granite_client)
        engine.process_query("nonexistent query")

        granite_client.generate.assert_not_called()


class TestQueryEngineSuccessfulQuery:
    """Test successful query processing pipeline."""

    def test_returns_query_response_with_answer(self):
        """Validates: Requirements 5.3, 5.4"""
        results = [_make_search_result("CT-001"), _make_search_result("CT-002")]
        index = MagicMock(spec=ArtifactIndex)
        index.search.return_value = results

        legislation = MagicMock(spec=LegislationCache)
        legislation.get_relevant_content.return_value = [
            LegislationSnippet(
                source_url="http://example.com/lei",
                law_name="Lei 14.133/2021",
                content="Art. 1 - content",
            )
        ]

        granite_client = MagicMock(spec=GraniteClient)
        granite_client.generate.return_value = GenerationResult(
            text="The contracts show...", prompt_tokens=200, completion_tokens=80
        )

        prompt_builder = MagicMock(spec=PromptBuilder)
        prompt_builder.build_prompt.return_value = "assembled prompt"

        engine = QueryEngine(index, legislation, granite_client, prompt_builder)
        response = engine.process_query("servicos de TI")

        assert isinstance(response, QueryResponse)
        assert response.answer == "The contracts show..."
        assert "CT-001" in response.referenced_contracts
        assert "CT-002" in response.referenced_contracts
        assert "Lei 14.133/2021" in response.legislation_citations

    def test_calls_prompt_builder_with_correct_args(self):
        """Validates: Requirements 5.4"""
        results = [_make_search_result("CT-001")]
        index = MagicMock(spec=ArtifactIndex)
        index.search.return_value = results

        snippets = [
            LegislationSnippet(
                source_url="http://example.com",
                law_name="Lei 8.666/1993",
                content="Content",
            )
        ]
        legislation = MagicMock(spec=LegislationCache)
        legislation.get_relevant_content.return_value = snippets

        prompt_builder = MagicMock(spec=PromptBuilder)
        prompt_builder.build_prompt.return_value = "prompt"

        granite_client = MagicMock(spec=GraniteClient)
        granite_client.generate.return_value = GenerationResult(
            text="Answer", prompt_tokens=100, completion_tokens=50
        )

        engine = QueryEngine(index, legislation, granite_client, prompt_builder)
        engine.process_query("test query")

        prompt_builder.build_prompt.assert_called_once_with(
            user_query="test query",
            artifacts=results,
            legislation=snippets,
        )


class TestQueryEngineTruncation:
    """Test >20 matches: include truncation notice in response."""

    def test_truncation_notice_when_more_than_20_matches(self):
        """Validates: Requirements 6.6"""
        # First call returns 20 results (capped), second call returns 21 (detecting overflow)
        results_20 = [_make_search_result(f"CT-{i:03d}") for i in range(20)]
        results_21 = [_make_search_result(f"CT-{i:03d}") for i in range(21)]

        index = MagicMock(spec=ArtifactIndex)
        index.search.side_effect = [results_20, results_21]

        granite_client = MagicMock(spec=GraniteClient)
        granite_client.generate.return_value = GenerationResult(
            text="Analysis of contracts.", prompt_tokens=500, completion_tokens=100
        )

        engine = _make_query_engine(index=index, granite_client=granite_client)
        response = engine.process_query("servicos")

        assert "more than 20 contracts" in response.answer
        assert "refining your query" in response.answer

    def test_no_truncation_notice_when_20_or_fewer(self):
        """Validates: Requirements 6.4"""
        results = [_make_search_result(f"CT-{i:03d}") for i in range(15)]

        index = MagicMock(spec=ArtifactIndex)
        # Both calls return 15 results (no overflow)
        index.search.side_effect = [results, results]

        granite_client = MagicMock(spec=GraniteClient)
        granite_client.generate.return_value = GenerationResult(
            text="Analysis result.", prompt_tokens=300, completion_tokens=60
        )

        engine = _make_query_engine(index=index, granite_client=granite_client)
        response = engine.process_query("servicos")

        assert "more than 20" not in response.answer


class TestQueryEngineGraniteErrors:
    """Test Granite timeout/unavailability: inform user, suggest retry."""

    def test_timeout_returns_unavailable_message(self):
        """Validates: Requirements 5.7"""
        results = [_make_search_result("CT-001")]
        index = MagicMock(spec=ArtifactIndex)
        index.search.return_value = results

        granite_client = MagicMock(spec=GraniteClient)
        granite_client.generate.side_effect = GraniteTimeoutError(
            "Timed out after 60s"
        )

        engine = _make_query_engine(index=index, granite_client=granite_client)
        response = engine.process_query("test query")

        assert "temporarily unavailable" in response.answer.lower()
        assert "retry" in response.answer.lower()
        assert "CT-001" in response.referenced_contracts

    def test_connection_error_returns_unavailable_message(self):
        """Validates: Requirements 5.7"""
        results = [_make_search_result("CT-001")]
        index = MagicMock(spec=ArtifactIndex)
        index.search.return_value = results

        granite_client = MagicMock(spec=GraniteClient)
        granite_client.generate.side_effect = GraniteConnectionError(
            "Connection refused"
        )

        engine = _make_query_engine(index=index, granite_client=granite_client)
        response = engine.process_query("test query")

        assert "temporarily unavailable" in response.answer.lower()
        assert "retry" in response.answer.lower()

    def test_model_loading_returns_unavailable_message(self):
        """Validates: Requirements 5.7"""
        results = [_make_search_result("CT-001")]
        index = MagicMock(spec=ArtifactIndex)
        index.search.return_value = results

        granite_client = MagicMock(spec=GraniteClient)
        granite_client.generate.side_effect = GraniteModelLoadingError(
            "Model still loading"
        )

        engine = _make_query_engine(index=index, granite_client=granite_client)
        response = engine.process_query("test query")

        assert "temporarily unavailable" in response.answer.lower()

    def test_context_exceeded_returns_specific_message(self):
        """Validates: Requirements 5.7"""
        results = [_make_search_result("CT-001")]
        index = MagicMock(spec=ArtifactIndex)
        index.search.return_value = results

        granite_client = MagicMock(spec=GraniteClient)
        granite_client.generate.side_effect = GraniteContextExceededError(
            "Context exceeded"
        )

        engine = _make_query_engine(index=index, granite_client=granite_client)
        response = engine.process_query("test query")

        assert "context" in response.answer.lower() or "exceed" in response.answer.lower()
        assert "shorter" in response.answer.lower() or "refine" in response.answer.lower()


class TestQueryEngineConfidenceLabels:
    """Test confidence label extraction from generated answers."""

    def test_extracts_based_on_data_label(self):
        results = [_make_search_result("CT-001")]
        index = MagicMock(spec=ArtifactIndex)
        index.search.return_value = results

        granite_client = MagicMock(spec=GraniteClient)
        granite_client.generate.return_value = GenerationResult(
            text='The contract value is R$ 100.000 "based on available data". '
            "Other details could not be determined.",
            prompt_tokens=200,
            completion_tokens=80,
        )

        engine = _make_query_engine(index=index, granite_client=granite_client)
        response = engine.process_query("contract value")

        # Should have at least one confidence label
        assert any("based on data" in v for v in response.confidence_labels.values())

    def test_extracts_undetermined_label(self):
        results = [_make_search_result("CT-001")]
        index = MagicMock(spec=ArtifactIndex)
        index.search.return_value = results

        granite_client = MagicMock(spec=GraniteClient)
        granite_client.generate.return_value = GenerationResult(
            text='The payment schedule "could not be determined from available artifacts".',
            prompt_tokens=200,
            completion_tokens=80,
        )

        engine = _make_query_engine(index=index, granite_client=granite_client)
        response = engine.process_query("payment schedule")

        assert any("undetermined" in v for v in response.confidence_labels.values())


class TestQueryEngineLegislationCitations:
    """Test legislation citation extraction."""

    def test_unique_citations_from_multiple_snippets(self):
        results = [_make_search_result("CT-001")]
        index = MagicMock(spec=ArtifactIndex)
        index.search.return_value = results

        legislation = MagicMock(spec=LegislationCache)
        legislation.get_relevant_content.return_value = [
            LegislationSnippet(
                source_url="http://example.com/1",
                law_name="Lei 14.133/2021",
                content="Content 1",
            ),
            LegislationSnippet(
                source_url="http://example.com/2",
                law_name="Lei 8.666/1993",
                content="Content 2",
            ),
            LegislationSnippet(
                source_url="http://example.com/3",
                law_name="Lei 14.133/2021",  # duplicate
                content="Content 3",
            ),
        ]

        granite_client = MagicMock(spec=GraniteClient)
        granite_client.generate.return_value = GenerationResult(
            text="Answer", prompt_tokens=100, completion_tokens=50
        )

        engine = QueryEngine(index, legislation, granite_client, MagicMock(spec=PromptBuilder))
        response = engine.process_query("licitacao")

        # Should deduplicate
        assert response.legislation_citations == [
            "Lei 14.133/2021",
            "Lei 8.666/1993",
        ]
