"""Query processing pipeline for the OpenClaws AI Assistant.

Orchestrates the full query flow: search the artifact index, retrieve
relevant legislation, build a prompt, send to Granite for inference,
and return a structured QueryResponse.
"""

import logging
import re

from openclaws.granite_client import (
    GraniteClient,
    GraniteConnectionError,
    GraniteContextExceededError,
    GraniteModelLoadingError,
    GraniteTimeoutError,
)
from openclaws.index import ArtifactIndex
from openclaws.legislation import LegislationCache
from openclaws.models import QueryResponse, SearchResult
from openclaws.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)

_MAX_RESULTS = 20

_NO_MATCH_ANSWER = (
    "No matching artifacts were found for your query. "
    "Please try refining your search terms — for example, use a specific "
    "contract number, supplier name, or keywords from the contract description."
)

_TRUNCATION_NOTICE = (
    "\n\nNote: Your query matched more than 20 contracts. "
    "The response covers the first 20 matching contracts. "
    "Consider refining your query to narrow the scope."
)

_GRANITE_UNAVAILABLE_ANSWER = (
    "The inference service is temporarily unavailable. "
    "Please retry your query in a few moments."
)

_GRANITE_CONTEXT_EXCEEDED_ANSWER = (
    "The query and matched data exceed the maximum allowed context size. "
    "Please try a shorter query or refine your search to match fewer contracts."
)


class QueryEngine:
    """Orchestrates the query processing pipeline.

    Coordinates between the artifact index, legislation cache, prompt builder,
    and Granite client to process user queries and produce structured responses.
    """

    def __init__(
        self,
        index: ArtifactIndex,
        legislation: LegislationCache,
        granite_client: GraniteClient,
        prompt_builder: PromptBuilder,
    ) -> None:
        """Initialize the query engine.

        Args:
            index: The in-memory artifact index for searching contracts.
            legislation: The legislation cache for retrieving relevant legal content.
            granite_client: The HTTP client for Granite Service inference.
            prompt_builder: The prompt constructor for assembling LLM prompts.
        """
        self._index = index
        self._legislation = legislation
        self._granite_client = granite_client
        self._prompt_builder = prompt_builder

    def process_query(self, user_query: str) -> QueryResponse:
        """Process a user query through the full pipeline.

        Steps:
        1. Search the artifact index for matching contracts.
        2. Handle no-match case (inform user, suggest refinement).
        3. Retrieve relevant legislation content.
        4. Build prompt with artifacts, legislation, and user query.
        5. Send prompt to Granite for inference.
        6. Parse response and return structured QueryResponse.

        Handles error cases:
        - No matches: returns informative message suggesting query refinement.
        - >20 matches: includes truncation notice in the response.
        - Granite timeout/connection error: returns message suggesting retry.
        - Granite context exceeded: returns message suggesting shorter query.

        Args:
            user_query: The natural language question from the user.

        Returns:
            A QueryResponse with the answer, referenced contracts,
            legislation citations, and confidence labels.
        """
        logger.info("Processing query: %s", user_query[:100])

        # Step 1: Search the artifact index
        # Request max_results + 1 to detect if truncation is needed
        search_results = self._index.search(user_query, max_results=_MAX_RESULTS)
        total_potential = len(search_results)

        # Check if there are more matches than the cap by searching with a higher limit
        extended_results = self._index.search(user_query, max_results=_MAX_RESULTS + 1)
        has_truncation = len(extended_results) > _MAX_RESULTS

        # Step 2: Handle no-match case
        if not search_results:
            logger.info("No artifacts matched query: %s", user_query[:100])
            return QueryResponse(
                answer=_NO_MATCH_ANSWER,
                referenced_contracts=[],
                legislation_citations=[],
                confidence_labels={},
            )

        # Step 3: Retrieve relevant legislation
        legislation_snippets = self._legislation.get_relevant_content(user_query)

        # Step 4: Build prompt
        prompt = self._prompt_builder.build_prompt(
            user_query=user_query,
            artifacts=search_results,
            legislation=legislation_snippets,
        )

        # Step 5: Send to Granite for inference
        try:
            generation_result = self._granite_client.generate(prompt=prompt)
        except (GraniteTimeoutError, GraniteConnectionError, GraniteModelLoadingError) as e:
            logger.error("Granite inference failed: %s", str(e))
            return QueryResponse(
                answer=_GRANITE_UNAVAILABLE_ANSWER,
                referenced_contracts=self._extract_contract_ids(search_results),
                legislation_citations=[],
                confidence_labels={},
            )
        except GraniteContextExceededError as e:
            logger.error("Granite context exceeded: %s", str(e))
            return QueryResponse(
                answer=_GRANITE_CONTEXT_EXCEEDED_ANSWER,
                referenced_contracts=self._extract_contract_ids(search_results),
                legislation_citations=[],
                confidence_labels={},
            )

        # Step 6: Build the response
        answer = generation_result.text

        # Append truncation notice if results were capped
        if has_truncation:
            answer += _TRUNCATION_NOTICE

        referenced_contracts = self._extract_contract_ids(search_results)
        legislation_citations = self._extract_legislation_citations(
            legislation_snippets
        )
        confidence_labels = self._extract_confidence_labels(answer)

        logger.info(
            "Query processed: %d contracts referenced, %d legislation citations",
            len(referenced_contracts),
            len(legislation_citations),
        )

        return QueryResponse(
            answer=answer,
            referenced_contracts=referenced_contracts,
            legislation_citations=legislation_citations,
            confidence_labels=confidence_labels,
        )

    def _extract_contract_ids(self, results: list[SearchResult]) -> list[str]:
        """Extract unique contract IDs from search results.

        Args:
            results: List of search results from the index.

        Returns:
            List of unique contract_id strings.
        """
        seen: set[str] = set()
        contract_ids: list[str] = []
        for result in results:
            cid = result.artifact.contract_id
            if cid not in seen:
                seen.add(cid)
                contract_ids.append(cid)
        return contract_ids

    def _extract_legislation_citations(
        self, snippets: list
    ) -> list[str]:
        """Extract legislation citation strings from snippets.

        Produces a list of law name citations from the legislation snippets
        that were included in the prompt context.

        Args:
            snippets: List of LegislationSnippet instances.

        Returns:
            List of citation strings (law names).
        """
        citations: list[str] = []
        for snippet in snippets:
            if snippet.law_name and snippet.law_name not in citations:
                citations.append(snippet.law_name)
        return citations

    def _extract_confidence_labels(self, answer: str) -> dict[str, str]:
        """Extract confidence labels from the generated answer.

        Looks for claims labeled as "based on available data" or
        "could not be determined from available artifacts" in the answer text.

        Args:
            answer: The generated answer text from Granite.

        Returns:
            Dictionary mapping claim excerpts to their confidence labels.
        """
        labels: dict[str, str] = {}

        # Match patterns where the LLM labels claims
        based_on_data_pattern = re.compile(
            r'["""]?based on available data["""]?', re.IGNORECASE
        )
        undetermined_pattern = re.compile(
            r'["""]?could not be determined from available artifacts["""]?',
            re.IGNORECASE,
        )

        # Split answer into sentences for labeling
        sentences = re.split(r'(?<=[.!?])\s+', answer)

        for sentence in sentences:
            sentence_stripped = sentence.strip()
            if not sentence_stripped:
                continue

            if based_on_data_pattern.search(sentence_stripped):
                labels[sentence_stripped] = "based on data"
            elif undetermined_pattern.search(sentence_stripped):
                labels[sentence_stripped] = "undetermined"

        return labels
