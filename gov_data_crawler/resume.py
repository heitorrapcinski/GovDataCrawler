"""Detects previously processed contracts for crawl resumption."""

import logging

from gov_data_crawler.output import OutputManager


class ResumeDetector:
    """Detects previously processed contracts for resumption.

    Scans the output directory for existing ``metadata.json`` files to
    determine which contracts have already been processed, allowing the
    crawler to skip them on subsequent runs.
    """

    def __init__(self, output_manager: OutputManager, logger: logging.Logger) -> None:
        """Initialize with an OutputManager and logger.

        Args:
            output_manager: Manages the output directory structure.
            logger: Logger instance for resumption messages.
        """
        self._output_manager = output_manager
        self._logger = logger

    def find_processed_ids(
        self,
        contract_ids: list[str],
        contracts_metadata: dict[str, tuple[str, str]],
    ) -> set[str]:
        """Identify which contract IDs have already been processed.

        Checks each contract ID against the output directory to see if a
        ``metadata.json`` file already exists for it.

        Args:
            contract_ids: Full list of contract IDs to check.
            contracts_metadata: Mapping of contract_id to
                ``(orgao, unidade_gestora)`` for path resolution.

        Returns:
            Set of contract IDs that already have metadata files.
        """
        processed: set[str] = set()

        for contract_id in contract_ids:
            if contract_id not in contracts_metadata:
                continue

            orgao, unidade_gestora = contracts_metadata[contract_id]

            if self._output_manager.contract_already_processed(
                orgao, unidade_gestora, contract_id
            ):
                processed.add(contract_id)

        if processed:
            self._logger.info(
                "Resumption: skipping %d already-processed contract(s)",
                len(processed),
            )

        return processed
