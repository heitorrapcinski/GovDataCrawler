# Tasks

- [x] 1. Scaffold project structure and configure dependencies
  - [x] 1.1 Create the Python package directory `gov_data_crawler/` with `__init__.py` and `__main__.py`
  - [x] 1.2 Create `pyproject.toml` with project metadata, Python 3.10+ requirement, and pinned dependencies: `requests==2.32.3`, `beautifulsoup4==4.12.3`, `lxml==5.3.1`
  - [x] 1.3 Add dev dependencies: `pytest==8.3.5`, `hypothesis==6.122.3`, `pytest-cov==6.1.1`, `responses==0.25.7`
  - [x] 1.4 Create the test directory structure: `tests/unit/`, `tests/property/`, `tests/integration/` with `__init__.py` files
  - [x] 1.5 Create `.gitignore` with entries for `__pycache__/`, `*.pyc`, `.pytest_cache/`, `htmlcov/`, `*.egg-info/`, `dist/`, `build/`, `target/`, `.env`, `venv/`, `.venv/`
  - [x] 1.6 Create `.dockerignore` with entries for `.git/`, `.kiro/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `htmlcov/`, `target/`, `tests/`, `*.log`, `.env`, `venv/`, `.venv/`
  - [x] 1.7 Verify the project installs and pytest discovers the test directories

- [x] 2. Implement the DelayMechanism component
  - [x] 2.1 Create `gov_data_crawler/delay.py` with the `DelayMechanism` class: configurable min/max seconds, random delay generation via `random.uniform`, auto-swap when min > max with warning log
  - [x] 2.2 Implement default values of 2.0 and 5.0 seconds when no configuration is provided
  - [x] 2.3 Write unit tests in `tests/unit/test_delay_mechanism.py` for defaults, custom values, and min > max swap behavior
  - [x] 2.4 Write property test in `tests/property/test_delay_mechanism_props.py` for Property 6: delay always within bounds after auto-correction
  - [x] 2.5 Run tests and verify all pass

- [x] 3. Implement the OutputManager component
  - [x] 3.1 Create `gov_data_crawler/output.py` with the `OutputManager` class: base directory management, directory creation, contract directory path construction following `{base_dir}/{orgao}/{unidade_gestora}/{contract_id}/` pattern
  - [x] 3.2 Implement `sanitize_folder_name` static method replacing filesystem-invalid characters (`<`, `>`, `:`, `"`, `/`, `\`, `|`, `?`, `*`) with underscores
  - [x] 3.3 Implement `contract_already_processed` method checking for `metadata.json` existence
  - [x] 3.4 Implement default `target` directory name when no custom path is provided
  - [x] 3.5 Write unit tests in `tests/unit/test_output_manager.py` for path construction, directory creation, default directory, and processed detection
  - [x] 3.6 Write property test in `tests/property/test_sanitization_props.py` for Property 7: sanitization removes invalid characters and is idempotent
  - [x] 3.7 Write property test in `tests/property/test_output_structure_props.py` for Property 4: directory structure follows hierarchical pattern
  - [x] 3.8 Run tests and verify all pass

- [x] 4. Implement the MetadataWriter and ContractMetadata data model
  - [x] 4.1 Create `gov_data_crawler/contract.py` with the `ContractMetadata` dataclass, `ProcessingResult` dataclass, `HttpRequestError` exception, and `ParsingError` exception
  - [x] 4.2 Create `gov_data_crawler/metadata.py` with the `MetadataWriter` class: serialize `ContractMetadata` to JSON with `ensure_ascii=False` and `indent=2`, write to `metadata.json` in target directory
  - [x] 4.3 Write unit tests in `tests/unit/test_metadata_writer.py` for JSON serialization and file writing
  - [x] 4.4 Write property test in `tests/property/test_metadata_roundtrip_props.py` for Property 3: serialization round-trip preserves all fields
  - [x] 4.5 Run tests and verify all pass

- [x] 5. Implement the HttpClient component
  - [x] 5.1 Create `gov_data_crawler/http_client.py` with the `HttpClient` class and `HttpResponse` dataclass
  - [x] 5.2 Implement session-based HTTP GET with `requests.Session` and `HTTPAdapter` configured with `urllib3.util.retry.Retry` (max 3 retries, backoff factor 1.0, retry on 500/502/503/504)
  - [x] 5.3 Integrate `DelayMechanism` to apply delay before each request
  - [x] 5.4 Write unit tests in `tests/unit/test_http_client.py` using `responses` library to mock HTTP calls, test retry behavior, 404 handling, and delay integration

- [x] 6. Implement the ListingParser and ListingNavigator components
  - [x] 6.1 Create `gov_data_crawler/listing.py` with the `ListingParser` class: extract contract IDs from listing page HTML using BeautifulSoup, extract next-page URL from pagination links
  - [x] 6.2 Implement `ListingNavigator` class: paginate through all listing pages using HttpClient and ListingParser, collect all contract IDs
  - [x] 6.3 Write unit tests in `tests/unit/test_listing_parser.py` for contract ID extraction, next-page URL extraction, empty page handling, and last page detection
  - [x] 6.4 Write property test in `tests/property/test_listing_parser_props.py` for Property 1: parser extracts all embedded contract IDs
  - [x] 6.5 Write property test in `tests/property/test_url_construction_props.py` for Property 2: contract detail URL is correctly constructed
  - [x] 6.6 Run tests and verify all pass

- [x] 7. Implement the DetailParser component
  - [x] 7.1 Create `gov_data_crawler/detail_parser.py` with the `DetailParser` class: extract all contract fields (orgao, unidade_gestora, contract_number, supplier_name, contract_value, start_date, end_date, object_description, extra_fields) from detail page HTML using BeautifulSoup
  - [x] 7.2 Implement `parse_attachment_urls` method to extract all attachment download URLs from the detail page
  - [x] 7.3 Write unit tests in `tests/unit/test_detail_parser.py` for field extraction, attachment URL extraction, missing fields handling, and ParsingError raising

- [x] 8. Implement the AttachmentDownloader component
  - [x] 8.1 Create `gov_data_crawler/attachments.py` with the `AttachmentDownloader` class: download files via HttpClient, save to target directory, extract filename from URL path or Content-Disposition header
  - [x] 8.2 Implement error handling: log failures with URL and contract ID, continue with remaining attachments
  - [x] 8.3 Write unit tests in `tests/unit/test_attachment_downloader.py` for successful download, filename extraction, download failure handling, and Content-Disposition parsing
  - [x] 8.4 Write property test in `tests/property/test_filename_extraction_props.py` for Property 5: filename is preserved from download URL
  - [x] 8.5 Run tests and verify all pass

- [x] 9. Implement the SummaryReporter component
  - [x] 9.1 Create `gov_data_crawler/summary.py` with the `CrawlSummary` dataclass and `SummaryReporter` class: track successes, failures, skips, and attachment counts, compute duration
  - [x] 9.2 Implement `finalize` method that produces a `CrawlSummary` and logs the summary to the logger
  - [x] 9.3 Write unit tests in `tests/unit/test_summary_reporter.py` for event recording and summary generation
  - [x] 9.4 Write property test in `tests/property/test_summary_reporter_props.py` for Property 8: summary counts are accurate
  - [x] 9.5 Run tests and verify all pass

- [ ] 10. Implement the ResumeDetector component
  - [~] 10.1 Create `gov_data_crawler/resume.py` with the `ResumeDetector` class: scan output directory for existing metadata.json files, return set of already-processed contract IDs
  - [~] 10.2 Implement logging of skipped contract count during resumption
  - [~] 10.3 Write unit tests in `tests/unit/test_resume_detector.py` for detection with existing files, empty directory, and partial processing
  - [~] 10.4 Write property test in `tests/property/test_resume_detector_props.py` for Property 9: correctly identifies processed contracts
  - [~] 10.5 Run tests and verify all pass

- [ ] 11. Implement the StopConditionChecker component
  - [~] 11.1 Create `gov_data_crawler/stop_condition.py` with the `StopConditionChecker` class: configurable `max_time` (float | None) and `max_contracts` (int | None), `start()` to record start time, `should_stop(successful_count)` to evaluate conditions, `triggered_condition` property
  - [~] 11.2 Implement `should_stop` logic: return True if elapsed time >= max_time or successful_count >= max_contracts; return False when limits are None (no limit)
  - [~] 11.3 Implement `triggered_condition` property returning `"max_time"`, `"max_contracts"`, or None
  - [~] 11.4 Write unit tests in `tests/unit/test_stop_condition.py` for individual limits, combined limits, no limits (defaults), and triggered condition reporting
  - [~] 11.5 Write property test in `tests/property/test_stop_condition_props.py` for Property 10: stop condition checker correctly evaluates stopping criteria
  - [~] 11.6 Run tests and verify all pass

- [ ] 12. Implement the ContractProcessor component
  - [~] 12.1 Create `gov_data_crawler/processor.py` with the `ContractProcessor` class: fetch detail page, parse metadata, download attachments, write metadata, return ProcessingResult
  - [~] 12.2 Implement error handling: catch HttpRequestError and ParsingError, log errors, return failure result; handle 404 as skip without retry
  - [~] 12.3 Write unit tests in `tests/unit/test_contract_processor.py` with mocked dependencies for successful processing, detail page failure, 404 handling, and attachment failure

- [ ] 13. Implement the CrawlOrchestrator and CLI entry point
  - [~] 13.1 Create `gov_data_crawler/orchestrator.py` with the `CrawlOrchestrator` class: coordinate listing navigation, resume detection, contract processing, stop condition checking, and summary reporting
  - [~] 13.2 Implement the full crawl lifecycle: collect IDs → filter already-processed → process remaining (checking stop conditions after each contract) → finalize summary with stop reason
  - [~] 13.3 Create `gov_data_crawler/cli.py` with `parse_args` (argparse with --output-dir, --min-delay, --max-delay, --max-time, --max-contracts, --log-level), `setup_logging` (dual console + file handlers), and `main` entry point
  - [~] 13.4 Update `gov_data_crawler/__main__.py` to call `cli.main()`
  - [~] 13.5 Write unit tests in `tests/unit/test_cli.py` for argument parsing with defaults and custom values, including --max-time and --max-contracts flags
  - [~] 13.6 Write integration tests in `tests/integration/test_crawl_orchestrator.py` for full crawl with mocked HTTP responses, including stop condition scenarios
  - [~] 13.7 Write integration tests in `tests/integration/test_pagination_flow.py` for multi-page navigation with mocked HTTP
  - [~] 13.8 Run the full test suite and verify all tests pass

- [ ] 14. Version control and release
  - [~] 14.1 Ensure all previous tasks are complete and tests pass
  - [~] 14.2 Remove SNAPSHOT suffix from all version references in the codebase
  - [~] 14.3 Commit the version bump: "release: 1.0.0 - gov-data-crawler"
  - [~] 14.4 Merge branch into main/master
  - [~] 14.5 Apply Git tag: 1.0.0 (without SNAPSHOT)
  - [~] 14.6 Push branch, merge, and tag to remote
