"""In-memory artifact index for the OpenClaws AI Assistant.

Provides text-based search across contract artifacts, matching query terms
against contract metadata fields and extracted PDF text content.
"""

import logging

from openclaws.models import IndexedArtifact, SearchResult

logger = logging.getLogger(__name__)


class ArtifactIndex:
    """In-memory index for searching contract artifacts.

    Stores IndexedArtifact instances and supports text-based search
    across contract_id, contract_number, supplier_name,
    object_description, and extracted PDF text.
    """

    def __init__(self) -> None:
        """Initialize an empty artifact index."""
        self._artifacts: list[IndexedArtifact] = []

    def add_artifact(self, artifact: IndexedArtifact) -> None:
        """Add an artifact to the index.

        Args:
            artifact: The IndexedArtifact instance to add.
        """
        self._artifacts.append(artifact)

    def search(self, query: str, max_results: int = 20) -> list[SearchResult]:
        """Search the index for artifacts matching the query terms.

        Splits the query into individual terms (words) and matches them
        against searchable fields: contract_id, contract_number,
        supplier_name, object_description, and PDF text content.

        Relevance score is calculated based on the number of matched
        fields and term frequency across those fields.

        Args:
            query: The search query string.
            max_results: Maximum number of results to return (default 20).

        Returns:
            A list of SearchResult instances sorted by relevance_score
            descending, capped at max_results.
        """
        if not query or not query.strip():
            return []

        terms = query.lower().split()
        if not terms:
            return []

        results: list[SearchResult] = []

        for artifact in self._artifacts:
            matched_fields: list[str] = []
            total_score = 0.0

            # Check each searchable field
            score, matched = self._score_field(
                artifact.contract_id, terms, "contract_id"
            )
            if matched:
                matched_fields.append("contract_id")
                total_score += score

            score, matched = self._score_field(
                artifact.contract_number, terms, "contract_number"
            )
            if matched:
                matched_fields.append("contract_number")
                total_score += score

            score, matched = self._score_field(
                artifact.supplier_name, terms, "supplier_name"
            )
            if matched:
                matched_fields.append("supplier_name")
                total_score += score

            score, matched = self._score_field(
                artifact.object_description, terms, "object_description"
            )
            if matched:
                matched_fields.append("object_description")
                total_score += score

            # Check PDF texts
            pdf_score, pdf_matched = self._score_pdf_texts(
                artifact.pdf_texts, terms
            )
            if pdf_matched:
                matched_fields.append("pdf_text")
                total_score += pdf_score

            if matched_fields:
                # Boost score by number of matched fields
                relevance_score = total_score * len(matched_fields)
                results.append(
                    SearchResult(
                        artifact=artifact,
                        relevance_score=relevance_score,
                        matched_fields=matched_fields,
                    )
                )

        # Sort by relevance score descending
        results.sort(key=lambda r: r.relevance_score, reverse=True)

        # Cap at max_results
        return results[:max_results]

    def artifact_count(self) -> int:
        """Return the total number of artifacts in the index.

        Returns:
            The count of indexed artifacts.
        """
        return len(self._artifacts)

    def pdf_count(self) -> int:
        """Return the total number of PDFs across all indexed artifacts.

        Returns:
            The total count of PDF texts stored across all artifacts.
        """
        return sum(len(a.pdf_texts) for a in self._artifacts)

    def _score_field(
        self, field_value: str, terms: list[str], field_name: str
    ) -> tuple[float, bool]:
        """Calculate the relevance score for a single text field.

        Counts how many query terms appear in the field and their
        frequency to produce a score.

        Args:
            field_value: The text content of the field.
            terms: The list of lowercase query terms.
            field_name: The name of the field (for logging).

        Returns:
            A tuple of (score, matched) where score is the relevance
            contribution and matched indicates if any term was found.
        """
        if not field_value:
            return 0.0, False

        field_lower = field_value.lower()
        score = 0.0
        matched = False

        for term in terms:
            count = field_lower.count(term)
            if count > 0:
                matched = True
                # Score: 1 point per term match + 0.5 for each additional occurrence
                score += 1.0 + (count - 1) * 0.5

        return score, matched

    def _score_pdf_texts(
        self, pdf_texts: dict[str, str], terms: list[str]
    ) -> tuple[float, bool]:
        """Calculate the relevance score across all PDF texts for an artifact.

        Aggregates term frequency across all PDF documents attached to
        the artifact.

        Args:
            pdf_texts: Dictionary mapping filename to extracted text.
            terms: The list of lowercase query terms.

        Returns:
            A tuple of (score, matched) where score is the relevance
            contribution and matched indicates if any term was found.
        """
        if not pdf_texts:
            return 0.0, False

        total_score = 0.0
        matched = False

        for _filename, text in pdf_texts.items():
            if not text:
                continue
            text_lower = text.lower()
            for term in terms:
                count = text_lower.count(term)
                if count > 0:
                    matched = True
                    # Score: 1 point per term match + 0.5 for each additional occurrence
                    total_score += 1.0 + (count - 1) * 0.5

        return total_score, matched
