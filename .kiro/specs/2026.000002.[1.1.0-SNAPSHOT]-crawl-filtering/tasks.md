# Implementation Plan: Crawl Filtering

## Overview

This plan implements optional filtering capabilities for the contract listing scrape. Two new CLI arguments (`--orgao` and `--categoria`) allow users to restrict the crawl to contracts matching specific government organizations and/or contract categories. Filters are applied at the listing navigation level by including them as POST parameters in DataTables API requests or as query parameters in HTML fallback URLs.

The implementation follows an incremental approach: first the data model, then CLI integration, then listing navigator changes, then summary reporting, and finally wiring and integration testing. Each task builds on the previous one.

## Tasks

- [x] 1. Create branch and bump version to 1.1.0-SNAPSHOT
  - Create and checkout branch `feature-2026.000002` from current HEAD
  - Update `version` in `pyproject.toml` from `1.0.0` to `1.1.0-SNAPSHOT`
  - Commit: `chore: bump version to 1.1.0-SNAPSHOT`
  - _Requirements: N/A (version control workflow)_

- [ ] 2. Implement FilterParameters dataclass
  - [x] 2.1 Add FilterParameters frozen dataclass to `gov_data_crawler/listing.py`
    - Define `orgao: str | None = None` and `categoria: str | None = None` fields
    - Implement `has_filters` property returning `True` if at least one field is not None
    - Implement `to_post_params()` returning a dict with only non-None filter entries
    - Implement `to_query_params()` returning the same dict as `to_post_params()`
    - Add the `FilterParameters` import to the module's public API
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 4.1, 4.2, 6.1_

  - [ ]* 2.2 Write property test for FilterParameters serialization
    - **Property 2: FilterParameters serialization includes exactly the non-None filters**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 4.1, 4.2**
    - Create `tests/property/test_filter_params_props.py`
    - Use Hypothesis to generate arbitrary optional string values for orgao and categoria
    - Assert `to_post_params()` contains exactly the non-None entries
    - Assert `to_query_params()` returns the same result as `to_post_params()`
    - Assert empty dict when both values are None

  - [ ]* 2.3 Write property test for FilterParameters has_filters consistency
    - **Property 3: FilterParameters has_filters is consistent with field presence**
    - **Validates: Requirements 3.4, 4.2, 5.1, 5.2**
    - Add to `tests/property/test_filter_params_props.py`
    - Use Hypothesis to generate arbitrary optional string values
    - Assert `has_filters` returns `True` iff at least one of orgao or categoria is not None

  - [ ]* 2.4 Write unit tests for FilterParameters
    - Create `tests/unit/test_filter_params.py`
    - Test construction with no arguments, one argument, both arguments
    - Test immutability (frozen dataclass)
    - Test `to_post_params()` and `to_query_params()` with specific examples
    - Test `has_filters` with edge cases
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 3. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 4. Add CLI filter arguments and logging
  - [x] 4.1 Extend `parse_args` in `gov_data_crawler/cli.py` with `--orgao` and `--categoria`
    - Add `--orgao` argument: `type=str`, `default=None`, help text: "Filter contracts by government organ number (número do órgão)"
    - Add `--categoria` argument: `type=str`, `default=None`, help text: "Filter contracts by category (categoria)"
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4_

  - [x] 4.2 Add filter logging to `main()` in `gov_data_crawler/cli.py`
    - Import `FilterParameters` from `gov_data_crawler.listing`
    - Construct `FilterParameters` from `args.orgao` and `args.categoria`
    - Log each active filter name and value at INFO level when filters are present
    - Log "No filters active — all contracts will be collected" when no filters are set
    - _Requirements: 5.1, 5.2_

  - [ ]* 4.3 Write property test for CLI argument round-trip
    - **Property 1: CLI argument round-trip preserves filter values**
    - **Validates: Requirements 1.1, 1.2, 1.3, 2.1, 2.2, 2.3**
    - Create `tests/property/test_cli_filter_args_props.py`
    - Use Hypothesis to generate arbitrary optional string values for orgao and categoria
    - Build argv list with `--orgao` and/or `--categoria` as appropriate
    - Assert `parse_args(argv).orgao` and `parse_args(argv).categoria` match the generated values
    - Assert omitted arguments default to None

  - [ ]* 4.4 Write unit tests for CLI filter arguments
    - Extend `tests/unit/test_cli.py` with tests for `--orgao` and `--categoria`
    - Test parsing with both arguments provided
    - Test parsing with only `--orgao` provided
    - Test parsing with only `--categoria` provided
    - Test parsing with neither argument (defaults to None)
    - Test help text content for both arguments
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4_

- [x] 5. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Integrate filters into ListingNavigator
  - [x] 6.1 Modify `ListingNavigator.__init__` to accept optional `FilterParameters`
    - Add `filters: FilterParameters | None = None` parameter to constructor
    - Store as `self._filters = filters or FilterParameters()`
    - _Requirements: 6.2_

  - [x] 6.2 Modify `_collect_via_datatables_api` to merge filter params into POST data
    - After constructing the base `post_data` dict, call `post_data.update(self._filters.to_post_params())`
    - This ensures filter key-value pairs are included in every paginated POST request
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [x] 6.3 Modify `_collect_via_html_scraping` to append filter params as query parameters
    - When filters are active, append filter params as URL query parameters to the listing page URL
    - Use `self._filters.to_query_params()` to get the filter dict
    - Apply to both the initial page fetch (re-fetch if filters are active) and subsequent page URLs
    - _Requirements: 4.1, 4.2_

  - [x] 6.4 Update `main()` in `cli.py` to pass `FilterParameters` to `ListingNavigator`
    - Pass the constructed `FilterParameters` instance as the `filters` keyword argument to `ListingNavigator`
    - _Requirements: 6.1, 6.3_

  - [ ]* 6.5 Write unit tests for ListingNavigator filter propagation
    - Extend `tests/unit/` or create `tests/unit/test_listing_navigator.py`
    - Test that `_collect_via_datatables_api` includes filter params in POST data (mocked HTTP)
    - Test that `_collect_via_html_scraping` appends filter params as query parameters (mocked HTTP)
    - Test that no filter params are sent when FilterParameters has no filters
    - Test that both filters are sent when both are provided (AND logic)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 4.1, 4.2_

- [x] 7. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 8. Extend SummaryReporter with filter information
  - [x] 8.1 Add `filters` field to `CrawlSummary` dataclass in `gov_data_crawler/summary.py`
    - Add `filters: dict[str, str] | None = None` field to `CrawlSummary`
    - _Requirements: 5.3_

  - [x] 8.2 Modify `SummaryReporter` to accept and report filters
    - Add `filters: FilterParameters | None = None` parameter to `SummaryReporter.__init__`
    - Store as `self._filters = filters`
    - In `finalize()`, populate `CrawlSummary.filters` with `self._filters.to_post_params()` when filters are active, or `None` when no filters are active
    - Log active filters in the summary output
    - Import `FilterParameters` from `gov_data_crawler.listing`
    - _Requirements: 5.3_

  - [x] 8.3 Update `main()` in `cli.py` to pass `FilterParameters` to `SummaryReporter`
    - Pass the constructed `FilterParameters` instance as the `filters` keyword argument to `SummaryReporter`
    - _Requirements: 5.3_

  - [ ]* 8.4 Write property test for CrawlSummary filter inclusion
    - **Property 4: CrawlSummary includes active filters**
    - **Validates: Requirements 5.3**
    - Create `tests/property/test_summary_filters_props.py`
    - Use Hypothesis to generate arbitrary optional filter values
    - Construct `SummaryReporter` with those filters and call `finalize()`
    - Assert `CrawlSummary.filters` equals `FilterParameters.to_post_params()` when filters are active
    - Assert `CrawlSummary.filters` is `None` when no filters are active

  - [ ]* 8.5 Write unit tests for SummaryReporter filter reporting
    - Extend `tests/unit/test_summary_reporter.py`
    - Test summary includes filter dict when filters are active
    - Test summary has `filters=None` when no filters are provided
    - Test filter information appears in log output
    - _Requirements: 5.3_

- [x] 9. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 10. Integration test for end-to-end filter propagation
  - [ ]* 10.1 Write integration test for filter flow from CLI to API requests
    - Create `tests/integration/test_filter_propagation.py`
    - Test that filters provided via CLI arguments flow through to ListingNavigator POST data
    - Test that filters flow through to HTML fallback query parameters
    - Test that SummaryReporter receives and reports the correct filters
    - Test the no-filter case preserves v1.0.0 behavior
    - Use mocked HTTP to verify actual request parameters
    - _Requirements: 1.1, 2.1, 3.1, 3.2, 3.3, 3.4, 4.1, 4.2, 5.1, 5.2, 5.3, 6.1, 6.2, 6.3_

- [x] 11. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 12. Version control and release
  - [x] 12.1 Ensure all previous tasks are complete and tests pass
  - [x] 12.2 Remove SNAPSHOT suffix from all version references in the codebase
  - [x] 12.3 Commit the version bump: "release: 1.1.0 - crawl-filtering"
  - [x] 12.4 Merge branch into main/master
  - [x] 12.5 Apply Git tag: 1.1.0 (without SNAPSHOT)
  - [x] 12.6 Push branch, merge, and tag to remote

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- Commit format per task: `2026.000002.{task-number}: <description>`
- Branch name: `feature-2026.000002`
