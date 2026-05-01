"""Command-line interface for GovDataCrawler."""

import argparse
import logging
import os
import sys

from gov_data_crawler.attachments import AttachmentDownloader
from gov_data_crawler.delay import DelayMechanism
from gov_data_crawler.detail_parser import DetailParser
from gov_data_crawler.http_client import HttpClient
from gov_data_crawler.listing import BASE_URL, LISTING_PATH, ListingNavigator, ListingParser
from gov_data_crawler.metadata import MetadataWriter
from gov_data_crawler.orchestrator import CrawlOrchestrator
from gov_data_crawler.output import OutputManager
from gov_data_crawler.processor import ContractProcessor
from gov_data_crawler.stop_condition import StopConditionChecker
from gov_data_crawler.summary import SummaryReporter


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Parsed namespace with: output_dir, min_delay, max_delay,
        max_time, max_contracts, log_level.
    """
    parser = argparse.ArgumentParser(
        prog="gov-data-crawler",
        description="Scrape public contract data from the Brazilian government's ComprasNet portal.",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="target",
        help="Root directory for all output (default: target)",
    )
    parser.add_argument(
        "--min-delay",
        type=float,
        default=2.0,
        help="Minimum delay between requests in seconds (default: 2.0)",
    )
    parser.add_argument(
        "--max-delay",
        type=float,
        default=5.0,
        help="Maximum delay between requests in seconds (default: 5.0)",
    )
    parser.add_argument(
        "--max-time",
        type=float,
        default=None,
        help="Maximum execution time in seconds (default: no limit)",
    )
    parser.add_argument(
        "--max-contracts",
        type=int,
        default=None,
        help="Maximum number of contracts to process (default: no limit)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )

    return parser.parse_args(argv)


def setup_logging(output_dir: str, log_level: str) -> logging.Logger:
    """Configure dual logging to console and file.

    Creates the output directory if it does not exist, then sets up
    a FileHandler for ``crawl.log`` in that directory plus a
    StreamHandler for console output.

    Args:
        output_dir: Directory for the log file.
        log_level: Logging level string (DEBUG, INFO, WARNING, ERROR).

    Returns:
        Configured root logger.
    """
    os.makedirs(output_dir, exist_ok=True)

    logger = logging.getLogger("gov_data_crawler")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Clear any existing handlers to avoid duplicates
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler
    log_file = os.path.join(output_dir, "crawl.log")
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def main(argv: list[str] | None = None) -> None:
    """Application entry point.

    Parses arguments, sets up logging, creates all components
    (including StopConditionChecker from --max-time and --max-contracts),
    and runs the CrawlOrchestrator.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).
    """
    args = parse_args(argv)
    logger = setup_logging(args.output_dir, args.log_level)

    logger.info("GovDataCrawler starting with configuration:")
    logger.info("  Output directory: %s", args.output_dir)
    logger.info("  Delay: %.1f - %.1f seconds", args.min_delay, args.max_delay)
    logger.info("  Max time: %s", args.max_time or "no limit")
    logger.info("  Max contracts: %s", args.max_contracts or "no limit")
    logger.info("  Log level: %s", args.log_level)

    # Create all components
    delay_mechanism = DelayMechanism(
        min_seconds=args.min_delay,
        max_seconds=args.max_delay,
    )
    http_client = HttpClient(delay_mechanism=delay_mechanism, logger=logger)
    output_manager = OutputManager(base_dir=args.output_dir)

    listing_parser = ListingParser()
    listing_navigator = ListingNavigator(
        http_client=http_client,
        parser=listing_parser,
        base_url=f"{BASE_URL}{LISTING_PATH}",
        logger=logger,
    )

    detail_parser = DetailParser()
    attachment_downloader = AttachmentDownloader(
        http_client=http_client, logger=logger
    )
    metadata_writer = MetadataWriter()

    contract_processor = ContractProcessor(
        http_client=http_client,
        detail_parser=detail_parser,
        attachment_downloader=attachment_downloader,
        metadata_writer=metadata_writer,
        output_manager=output_manager,
        logger=logger,
    )

    summary_reporter = SummaryReporter(logger=logger)

    stop_condition_checker = StopConditionChecker(
        max_time=args.max_time,
        max_contracts=args.max_contracts,
        logger=logger,
    )

    orchestrator = CrawlOrchestrator(
        listing_navigator=listing_navigator,
        contract_processor=contract_processor,
        summary_reporter=summary_reporter,
        stop_condition_checker=stop_condition_checker,
        output_dir=args.output_dir,
        logger=logger,
    )

    orchestrator.run()
