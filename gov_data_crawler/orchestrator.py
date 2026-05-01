"""Crawl orchestrator coordinating the full crawl lifecycle."""

import json
import logging
import os
from datetime import datetime, timezone

from gov_data_crawler.listing import ListingNavigator
from gov_data_crawler.processor import ContractProcessor
from gov_data_crawler.stop_condition import StopConditionChecker
from gov_data_crawler.summary import CrawlSummary, SummaryReporter


class CrawlOrchestrator:
    """Coordinates the full crawl lifecycle.

    Manages the sequence: collect contract IDs from listing pages,
    filter out already-processed contracts, process remaining contracts
    (checking stop conditions after each), and produce a final summary.
    """

    def __init__(
        self,
        listing_navigator: ListingNavigator,
        contract_processor: ContractProcessor,
        summary_reporter: SummaryReporter,
        stop_condition_checker: StopConditionChecker,
        output_dir: str,
        logger: logging.Logger,
    ) -> None:
        """Initialize the orchestrator with all required components.

        Args:
            listing_navigator: Navigates listing pages and collects contract IDs.
            contract_processor: Processes individual contracts end-to-end.
            summary_reporter: Tracks and reports execution statistics.
            stop_condition_checker: Evaluates stopping criteria during the crawl.
            output_dir: Base output directory for scanning processed contracts.
            logger: Logger instance for orchestration messages.
        """
        self._listing_navigator = listing_navigator
        self._contract_processor = contract_processor
        self._summary_reporter = summary_reporter
        self._stop_condition_checker = stop_condition_checker
        self._output_dir = output_dir
        self._logger = logger

    def run(self) -> CrawlSummary:
        """Execute the full crawl: list -> filter -> process -> summarize.

        The processing loop checks stop conditions after each successfully
        processed contract. When a stop condition is met, the current
        contract is finished before the crawl ends.

        Returns:
            CrawlSummary with execution statistics.
        """
        # Start the stop condition checker
        self._stop_condition_checker.start()

        start_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self._logger.info("Crawl started at %s", start_timestamp)

        # Step 1: Collect contract IDs from listing pages.
        # Pass max_contracts so the navigator can stop early instead of
        # paginating through hundreds of thousands of records.
        max_contracts = self._stop_condition_checker.max_contracts
        self._logger.info("Collecting contract IDs from listing pages...")
        contract_ids = self._listing_navigator.collect_all_contract_ids(
            max_ids=max_contracts,
        )
        self._logger.info("Collected %d contract IDs", len(contract_ids))

        # Step 2: Scan output directory for already-processed contracts
        processed_ids = self._scan_processed_ids()
        if processed_ids:
            self._logger.info(
                "Resumption: found %d already-processed contract(s), skipping them",
                len(processed_ids),
            )

        # Step 3: Process each contract
        successful_count = 0
        stop_reason: str | None = None

        for contract_id in contract_ids:
            # Skip already-processed contracts
            if contract_id in processed_ids:
                self._summary_reporter.record_skip(contract_id)
                continue

            # Process the contract
            result = self._contract_processor.process(contract_id)

            if result.success:
                self._summary_reporter.record_success(
                    contract_id, result.attachments_downloaded
                )
                successful_count += 1

                # Check stop conditions after each successful contract
                if self._stop_condition_checker.should_stop(successful_count):
                    stop_reason = self._stop_condition_checker.triggered_condition
                    self._logger.info(
                        "Stop condition triggered: %s", stop_reason
                    )
                    break
            else:
                self._summary_reporter.record_failure(
                    contract_id, result.error or "Unknown error"
                )

        # Step 4: Finalize summary
        summary = self._summary_reporter.finalize(stopped_by=stop_reason)

        end_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self._logger.info("Crawl ended at %s", end_timestamp)

        return summary

    def _scan_processed_ids(self) -> set[str]:
        """Scan the output directory for already-processed contract IDs.

        Recursively searches for metadata.json files and extracts the
        contract_id field from each one.

        Returns:
            Set of contract IDs that have already been processed.
        """
        processed: set[str] = set()

        if not os.path.isdir(self._output_dir):
            return processed

        for root, _dirs, files in os.walk(self._output_dir):
            if "metadata.json" in files:
                metadata_path = os.path.join(root, "metadata.json")
                try:
                    with open(metadata_path, encoding="utf-8") as f:
                        data = json.load(f)
                    contract_id = data.get("contract_id")
                    if contract_id:
                        processed.add(str(contract_id))
                except (json.JSONDecodeError, OSError) as exc:
                    self._logger.warning(
                        "Failed to read metadata from %s: %s",
                        metadata_path,
                        exc,
                    )

        return processed
