"""Core data models for the OpenClaws AI Assistant."""

from dataclasses import dataclass, field
from enum import Enum


@dataclass
class IndexedArtifact:
    """An artifact loaded into the in-memory index."""

    contract_id: str
    orgao: str
    unidade_gestora: str
    contract_number: str
    supplier_name: str
    contract_value: str
    start_date: str
    end_date: str
    object_description: str
    extra_fields: dict[str, str]
    attachments: list[str]
    scraped_at: str
    folder_path: str
    pdf_texts: dict[str, str]  # filename -> extracted text


@dataclass
class SearchResult:
    """A single search match from the artifact index."""

    artifact: IndexedArtifact
    relevance_score: float
    matched_fields: list[str]


@dataclass
class LegislationSnippet:
    """A relevant excerpt from cached legislation."""

    source_url: str
    law_name: str
    content: str


@dataclass
class GenerationResult:
    """Response from the Granite Service."""

    text: str
    prompt_tokens: int
    completion_tokens: int


class HealthStatus(Enum):
    """Health status of the Granite Service."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNREACHABLE = "unreachable"


@dataclass
class QueryResponse:
    """Complete response to a user query."""

    answer: str
    referenced_contracts: list[str]  # contract_ids
    legislation_citations: list[str]
    confidence_labels: dict[str, str]  # claim -> "based on data" | "undetermined"


@dataclass
class FetchReport:
    """Report of legislation fetch operation."""

    successful_urls: list[str]
    failed_urls: list[str]
    cached_urls: list[str]  # served from cache
