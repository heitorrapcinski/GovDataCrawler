"""Prompt construction for the Granite LLM inference requests."""

import logging

from openclaws.models import LegislationSnippet, SearchResult

logger = logging.getLogger(__name__)

_SYSTEM_CONTEXT = (
    "You are an AI assistant specialized in analyzing Brazilian government contracts "
    "and public procurement data. You have access to contract artifacts collected from "
    "contratos.comprasnet.gov.br and relevant Brazilian procurement legislation. "
    "Your role is to provide accurate, well-cited answers grounded in the available data."
)

_CITATION_INSTRUCTIONS = (
    "CITATION INSTRUCTIONS:\n"
    "- When referencing a contract, always cite the contract_id and contract_number.\n"
    "- When referencing legislation, always cite the law name and specific article numbers.\n"
    "- Label each factual claim as either:\n"
    '  * "based on available data" — when the claim is directly supported by the '
    "artifact data or legislation provided above.\n"
    '  * "could not be determined from available artifacts" — when the information '
    "is not present in the provided data and cannot be confirmed.\n"
    "- Do not fabricate information. If the data is insufficient, state so explicitly."
)


class PromptBuilder:
    """Constructs LLM prompts from artifacts, legislation, and user queries.

    Assembles a structured prompt that includes system context, matched artifact
    data with folder paths and metadata, legislation snippets with citation
    instructions, and the user query.
    """

    def build_prompt(
        self,
        user_query: str,
        artifacts: list[SearchResult],
        legislation: list[LegislationSnippet],
    ) -> str:
        """Build a complete prompt for the Granite LLM.

        Constructs a prompt structured as:
        1. System context (AI assistant role for Brazilian government contracts)
        2. Artifact data section with folder paths and metadata fields
        3. Legislation section with snippets and citation instructions
        4. Citation instructions (contract_id, contract_number, law name, articles)
        5. User query

        Args:
            user_query: The natural language question from the user.
            artifacts: List of search results with matched artifacts and metadata.
            legislation: List of legislation snippets relevant to the query topic.

        Returns:
            A formatted prompt string ready to send to the Granite Service.
        """
        sections: list[str] = []

        # 1. System context
        sections.append(f"SYSTEM:\n{_SYSTEM_CONTEXT}")

        # 2. Artifact data section
        sections.append(self._build_artifacts_section(artifacts))

        # 3. Legislation section
        sections.append(self._build_legislation_section(legislation))

        # 4. Citation instructions
        sections.append(_CITATION_INSTRUCTIONS)

        # 5. User query
        sections.append(f"USER QUERY:\n{user_query}")

        prompt = "\n\n".join(sections)
        logger.debug(
            "Built prompt with %d artifacts and %d legislation snippets (%d chars)",
            len(artifacts),
            len(legislation),
            len(prompt),
        )
        return prompt

    def _build_artifacts_section(self, artifacts: list[SearchResult]) -> str:
        """Build the artifact data section of the prompt.

        Each artifact includes its folder path, metadata fields, matched fields,
        and relevance score for context.

        Args:
            artifacts: List of search results to include in the prompt.

        Returns:
            Formatted artifact data section string.
        """
        if not artifacts:
            return "CONTRACT ARTIFACTS:\nNo matching artifacts found."

        lines: list[str] = ["CONTRACT ARTIFACTS:"]

        for i, result in enumerate(artifacts, start=1):
            artifact = result.artifact
            lines.append(f"\n--- Artifact {i} (relevance: {result.relevance_score:.2f}, matched fields: {', '.join(result.matched_fields)}) ---")
            lines.append(f"Folder Path: {artifact.folder_path}")
            lines.append(f"Contract ID: {artifact.contract_id}")
            lines.append(f"Contract Number: {artifact.contract_number}")
            lines.append(f"Orgao: {artifact.orgao}")
            lines.append(f"Unidade Gestora: {artifact.unidade_gestora}")
            lines.append(f"Supplier: {artifact.supplier_name}")
            lines.append(f"Contract Value: {artifact.contract_value}")
            lines.append(f"Start Date: {artifact.start_date}")
            lines.append(f"End Date: {artifact.end_date}")
            lines.append(f"Object Description: {artifact.object_description}")

            if artifact.extra_fields:
                extra = "; ".join(
                    f"{k}: {v}" for k, v in artifact.extra_fields.items()
                )
                lines.append(f"Extra Fields: {extra}")

            if artifact.attachments:
                lines.append(f"Attachments: {', '.join(artifact.attachments)}")

            lines.append(f"Scraped At: {artifact.scraped_at}")

            if artifact.pdf_texts:
                lines.append("Extracted PDF Content:")
                for filename, text in artifact.pdf_texts.items():
                    # Truncate long PDF texts to keep prompt manageable
                    truncated = text[:2000] if len(text) > 2000 else text
                    suffix = " [truncated]" if len(text) > 2000 else ""
                    lines.append(f"  [{filename}]: {truncated}{suffix}")

        return "\n".join(lines)

    def _build_legislation_section(
        self, legislation: list[LegislationSnippet]
    ) -> str:
        """Build the legislation context section of the prompt.

        Each snippet includes the law name, source URL, and content excerpt.

        Args:
            legislation: List of legislation snippets to include.

        Returns:
            Formatted legislation section string.
        """
        if not legislation:
            return (
                "LEGISLATION CONTEXT:\n"
                "No relevant legislation snippets available for this query."
            )

        lines: list[str] = [
            "LEGISLATION CONTEXT:",
            "The following legislation excerpts are relevant to the query. "
            "Cite the law name and article numbers when referencing this content.",
        ]

        for i, snippet in enumerate(legislation, start=1):
            lines.append(f"\n--- Legislation {i} ---")
            lines.append(f"Law: {snippet.law_name}")
            lines.append(f"Source: {snippet.source_url}")
            lines.append(f"Content:\n{snippet.content}")

        return "\n".join(lines)
