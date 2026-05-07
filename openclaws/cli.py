"""Command-line interface for the OpenClaws AI Assistant.

Provides the interactive CLI loop for user queries, orchestrates the
startup sequence (config validation, artifact discovery, legislation
caching, Granite health check), and handles graceful shutdown.
"""

import logging
import sys
import threading
import time

from openclaws.config import load_and_validate_config
from openclaws.discovery import discover_artifacts
from openclaws.granite_client import GraniteClient, GraniteConnectionError
from openclaws.health_monitor import HealthMonitor
from openclaws.index import ArtifactIndex
from openclaws.legislation import LEGISLATION_URLS, LegislationCache
from openclaws.models import HealthStatus, QueryResponse
from openclaws.prompt_builder import PromptBuilder
from openclaws.query_engine import QueryEngine

logger = logging.getLogger(__name__)

_MIN_QUERY_LENGTH = 1
_MAX_QUERY_LENGTH = 2000
_PROMPT_TEXT = "openclaws> "
_UNREACHABLE_EXIT_TIMEOUT = 30
_CONSECUTIVE_FAILURE_THRESHOLD = 3


def validate_query(query: str) -> tuple[bool, str]:
    """Validate a user query for length and content constraints.

    A query is valid if its stripped length is between 1 and 2000
    characters (inclusive). Empty strings, whitespace-only strings,
    and strings exceeding 2000 characters after stripping are rejected.

    Args:
        query: The raw user input string.

    Returns:
        A tuple of (is_valid, error_message). If valid, error_message
        is an empty string. If invalid, error_message describes the issue.
    """
    stripped = query.strip()

    if len(stripped) == 0:
        return False, "Query cannot be empty or blank. Please enter a query between 1 and 2000 characters."

    if len(stripped) > _MAX_QUERY_LENGTH:
        return (
            False,
            f"Query exceeds maximum length of {_MAX_QUERY_LENGTH} characters "
            f"(got {len(stripped)}). Please shorten your query.",
        )

    return True, ""


def _format_response(response: QueryResponse) -> str:
    """Format a QueryResponse for display in the CLI.

    Includes the answer text, referenced contracts, and legislation
    citations in a readable format.

    Args:
        response: The QueryResponse from the query engine.

    Returns:
        A formatted string ready for display.
    """
    lines: list[str] = []

    lines.append("")
    lines.append(response.answer)

    if response.referenced_contracts:
        lines.append("")
        lines.append("Referenced Contracts:")
        for contract_id in response.referenced_contracts:
            lines.append(f"  - {contract_id}")

    if response.legislation_citations:
        lines.append("")
        lines.append("Legislation Citations:")
        for citation in response.legislation_citations:
            lines.append(f"  - {citation}")

    lines.append("")
    return "\n".join(lines)


def _setup_logging(log_level: str) -> None:
    """Configure logging with the specified level.

    Args:
        log_level: One of DEBUG, INFO, WARN, ERROR.
    """
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARN": logging.WARNING,
        "ERROR": logging.ERROR,
    }
    level = level_map.get(log_level, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )


def main() -> None:
    """Main entry point for the OpenClaws AI Assistant.

    Orchestrates the full startup sequence:
    1. Load and validate configuration
    2. Scan target folder and build in-memory index
    3. Fetch and cache legislation
    4. Perform initial Granite health check
    5. Start health monitor
    6. Enter interactive CLI loop

    Exits with non-zero status on configuration errors, missing target
    folder, or Granite unreachable after startup (within 30 seconds).
    """
    # Step 1: Load and validate configuration
    agent_config, granite_config = load_and_validate_config()

    # Set up logging with configured level
    _setup_logging(agent_config.log_level)

    logger.info("OpenClaws AI Assistant starting...")

    # Step 2: Scan target folder and build in-memory index
    artifacts = discover_artifacts(agent_config.target_folder)

    index = ArtifactIndex()
    for artifact in artifacts:
        index.add_artifact(artifact)

    logger.info(
        "Artifact index built: %d artifacts, %d PDFs",
        index.artifact_count(),
        index.pdf_count(),
    )

    # Step 3: Fetch and cache legislation
    legislation_cache = LegislationCache(cache_dir="./legislation_cache")
    fetch_report = legislation_cache.fetch_and_cache(LEGISLATION_URLS)

    total_available = len(fetch_report.successful_urls) + len(fetch_report.cached_urls)
    logger.info(
        "Legislation cache: %d/%d URLs available",
        total_available,
        len(LEGISLATION_URLS),
    )

    # Step 4: Perform initial Granite health check
    granite_client = GraniteClient(
        endpoint_url=agent_config.granite_endpoint,
        timeout=60,
    )

    initial_status = granite_client.health_check(timeout=5)
    if initial_status == HealthStatus.HEALTHY:
        logger.info("Granite Service is healthy and ready")
    else:
        logger.warning(
            "Granite Service initial health check: %s (will continue startup)",
            initial_status.value,
        )

    # Step 5: Start health monitor
    health_monitor = HealthMonitor(
        granite_client=granite_client,
        interval=agent_config.health_check_interval,
    )
    health_monitor.start()

    # Step 6: Build query engine
    prompt_builder = PromptBuilder()
    query_engine = QueryEngine(
        index=index,
        legislation=legislation_cache,
        granite_client=granite_client,
        prompt_builder=prompt_builder,
    )

    logger.info("OpenClaws AI Assistant ready. Type your query or Ctrl+C to exit.")

    # Step 7: Enter interactive CLI loop
    _exit_event = threading.Event()

    try:
        while not _exit_event.is_set():
            # Check if Granite has become unreachable (3 consecutive failures)
            if health_monitor.consecutive_failures >= _CONSECUTIVE_FAILURE_THRESHOLD:
                logger.error(
                    "Granite Service unreachable (%d consecutive failures). "
                    "Shutting down within %d seconds.",
                    health_monitor.consecutive_failures,
                    _UNREACHABLE_EXIT_TIMEOUT,
                )
                health_monitor.stop()
                sys.exit(1)

            try:
                user_input = input(_PROMPT_TEXT)
            except EOFError:
                # End of input stream (e.g., piped input exhausted)
                break

            # Validate query
            is_valid, error_message = validate_query(user_input)
            if not is_valid:
                print(f"Error: {error_message}", file=sys.stderr)
                continue

            # Show progress indicator
            print("Analyzing...", flush=True)

            # Process query
            try:
                response = query_engine.process_query(user_input.strip())
            except GraniteConnectionError:
                logger.error(
                    "Granite Service became unreachable during query processing"
                )
                # Check if we should exit
                if health_monitor.consecutive_failures >= _CONSECUTIVE_FAILURE_THRESHOLD:
                    logger.error(
                        "Granite Service unreachable. Shutting down."
                    )
                    health_monitor.stop()
                    sys.exit(1)
                print(
                    "Error: The inference service is temporarily unavailable. "
                    "Please retry your query.",
                    file=sys.stderr,
                )
                continue

            # Display formatted response
            formatted = _format_response(response)
            print(formatted)

    except KeyboardInterrupt:
        # Graceful exit on Ctrl+C
        print("\nExiting OpenClaws. Goodbye.")
    finally:
        health_monitor.stop()
        logger.info("OpenClaws AI Assistant stopped.")
