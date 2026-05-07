# Implementation Plan: OpenClaws AI Assistant

## Overview

Implement the OpenClaws AI Assistant as a containerized Python CLI application that analyzes Brazilian government contract artifacts using IBM Granite LLM. The implementation follows a bottom-up approach: core data models and configuration first, then infrastructure modules (discovery, indexing, PDF extraction), followed by the query pipeline (legislation, prompt builder, Granite client, query engine), CLI interface, health monitoring, and finally Docker containerization.

## Tasks

- [x] 1. Set up project structure and core data models
  - [x] 1.1 Create the `openclaws/` package with `__init__.py` and `__main__.py`
    - Create `openclaws/__init__.py` with package version `1.2.0-SNAPSHOT`
    - Create `openclaws/__main__.py` that invokes `cli.main()`
    - Add `PyPDF2>=3.0.0` to project dependencies in `pyproject.toml`
    - Add `openclaws` to `[tool.setuptools.packages.find]` include list
    - Add `openclaws` CLI entry point in `[project.scripts]`
    - _Requirements: 1.1, 1.6_

  - [x] 1.2 Implement core data models in `openclaws/models.py`
    - Create dataclasses: `IndexedArtifact`, `SearchResult`, `LegislationSnippet`, `GenerationResult`, `QueryResponse`, `FetchReport`
    - Create `HealthStatus` enum with HEALTHY, UNHEALTHY, UNREACHABLE values
    - Ensure all fields match the design document interface definitions
    - _Requirements: 3.2, 5.3, 6.1_

- [x] 2. Implement configuration management
  - [x] 2.1 Implement `openclaws/config.py` with `AgentConfig` and `GraniteConfig`
    - Implement `AgentConfig.from_env()` parsing: target_folder (str, max 4096 chars), granite_endpoint (str, max 2048 chars), health_check_interval (int, 5–300), log_level (DEBUG|INFO|WARN|ERROR)
    - Implement `GraniteConfig.from_env()` parsing: model_name (str, max 256 chars), inference_port (int, 1–65535), max_context_length (int, 512–131072), temperature (float, 0.0–2.0), max_tokens (int, 1–8192), top_p (float, 0.0–1.0)
    - Implement default values: AgentConfig defaults (health_check_interval=30, log_level=INFO, target_folder="./target"); GraniteConfig defaults (inference_port=8080, max_context_length=4096, temperature=0.7, max_tokens=2048, top_p=0.95)
    - Implement validation errors with messages containing variable name, invalid value, and expected format
    - Log active configuration at INFO level on successful startup (excluding sensitive credentials)
    - Exit with non-zero status code on invalid configuration
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7_

  - [x]* 2.2 Write property test for AgentConfig validation (Property 1)
    - **Property 1: Agent configuration validation round-trip**
    - **Validates: Requirements 8.1, 8.5, 7.2**
    - Test file: `tests/property/test_openclaws_config_props.py`
    - Use Hypothesis strategies to generate valid and invalid env var combinations
    - Verify valid values produce correct AgentConfig; invalid values raise validation errors with proper messages

  - [x]* 2.3 Write property test for GraniteConfig validation (Property 2)
    - **Property 2: Granite configuration validation round-trip**
    - **Validates: Requirements 8.2, 8.6, 2.4**
    - Test file: `tests/property/test_openclaws_config_props.py`
    - Use Hypothesis strategies to generate valid and invalid env var combinations
    - Verify valid values produce correct GraniteConfig; invalid values raise validation errors with proper messages

- [x] 3. Implement PDF extraction
  - [x] 3.1 Implement `openclaws/pdf_extractor.py`
    - Create `extract_text(file_path: str, max_size_mb: int = 50) -> str | None` function
    - Use PyPDF2 to extract text from PDF files
    - Skip files exceeding 50 MB with a warning log
    - Return `None` and log warning if PDF cannot be read or contains no extractable text
    - Handle corrupted PDFs gracefully without raising exceptions
    - _Requirements: 3.3, 3.6_

  - [x]* 3.2 Write unit tests for PDF extractor
    - Test file: `tests/unit/test_openclaws_pdf_extractor.py`
    - Test successful text extraction from a valid PDF
    - Test handling of corrupted/unreadable PDFs
    - Test file size limit enforcement (>50 MB skip)
    - Test empty PDF (no extractable text)
    - _Requirements: 3.3, 3.6_

- [x] 4. Implement artifact discovery and indexing
  - [x] 4.1 Implement `openclaws/discovery.py`
    - Create `discover_artifacts(target_folder: str) -> list[IndexedArtifact]` function
    - Recursively scan target folder for directories containing `metadata.json`
    - Parse each `metadata.json` and create `IndexedArtifact` instances
    - Call PDF extractor for each PDF attachment found in artifact folders
    - Log total number of discovered artifacts and processed PDFs on completion
    - Skip artifacts with invalid JSON (log error with file path, continue scan)
    - Exit with non-zero status if target folder does not exist or is not accessible
    - Log warning if target folder contains zero artifacts (continue with empty index)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8_

  - [x]* 4.2 Write property test for artifact discovery (Property 3)
    - **Property 3: Artifact discovery identifies exactly folders containing metadata.json**
    - **Validates: Requirements 3.1**
    - Test file: `tests/property/test_openclaws_discovery_props.py`
    - Use Hypothesis to generate arbitrary directory trees with and without metadata.json
    - Verify discovery returns exactly the set of folders containing metadata.json

  - [x] 4.3 Implement `openclaws/index.py` with `ArtifactIndex` class
    - Implement `add_artifact(artifact: IndexedArtifact) -> None`
    - Implement `search(query: str, max_results: int = 20) -> list[SearchResult]` matching against contract_id, contract_number, supplier_name, object_description, and PDF text
    - Implement `artifact_count() -> int` and `pdf_count() -> int`
    - Search must return at most 20 results regardless of matches
    - Calculate relevance_score based on number of matched fields and term frequency
    - _Requirements: 3.2, 5.3, 6.4_

  - [x]* 4.4 Write property test for metadata indexing (Property 4)
    - **Property 4: Metadata indexing preserves all fields**
    - **Validates: Requirements 3.2**
    - Test file: `tests/property/test_openclaws_index_props.py`
    - Use Hypothesis to generate valid IndexedArtifact instances
    - Verify all fields are preserved after add_artifact and retrieval

  - [x]* 4.5 Write property test for search result cap (Property 8)
    - **Property 8: Search results are capped at 20**
    - **Validates: Requirements 6.4**
    - Test file: `tests/property/test_openclaws_index_props.py`
    - Use Hypothesis to generate indexes with >20 matching artifacts
    - Verify search never returns more than 20 results

- [x] 5. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement legislation knowledge base
  - [x] 6.1 Implement `openclaws/legislation.py` with `LegislationCache` class
    - Implement `__init__(self, cache_dir: str, timeout: int = 30)`
    - Implement `fetch_and_cache(self, urls: list[str]) -> FetchReport` with 30s timeout per URL
    - Implement `get_relevant_content(self, topic: str) -> list[LegislationSnippet]`
    - Store fetched content in file-based cache (survives container restarts)
    - On fetch failure: log warning, use previously cached content if available
    - On first run with unreachable URLs: log error, start with degraded knowledge base
    - Include all 10 legislation URLs from requirements 4.1
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [x]* 6.2 Write unit tests for legislation cache
    - Test file: `tests/unit/test_openclaws_legislation.py`
    - Test successful fetch and cache storage
    - Test cache hit (serve from file cache)
    - Test timeout handling (30s per URL)
    - Test degraded startup (unreachable URLs, no cache)
    - Test partial degradation (some URLs cached, some unreachable)
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 7. Implement Granite client and health monitor
  - [x] 7.1 Implement `openclaws/granite_client.py` with `GraniteClient` class
    - Implement `__init__(self, endpoint_url: str, timeout: int = 60)`
    - Implement `generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 1024, top_p: float = 0.9) -> GenerationResult`
    - Implement `health_check(self, timeout: int = 5) -> HealthStatus`
    - POST to `/v1/completions` for inference
    - GET `/health` for health checks
    - Handle 400 (invalid params/context exceeded), 503 (model loading), timeout, and connection refused errors
    - _Requirements: 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

  - [x] 7.2 Implement `openclaws/health_monitor.py` with `HealthMonitor` class
    - Implement periodic health checking at configurable interval (5–300s, default 30s)
    - Log warning on non-successful health check response or 5s timeout
    - Log error-level message after 3 consecutive health check failures
    - Track consecutive failure count; reset on successful check
    - _Requirements: 7.1, 7.2, 7.3, 7.5_

  - [x]* 7.3 Write property test for health monitor consecutive failures (Property 10)
    - **Property 10: Health monitor detects consecutive failures**
    - **Validates: Requirements 7.5**
    - Test file: `tests/property/test_openclaws_health_props.py`
    - Use Hypothesis to generate sequences of health check results
    - Verify error log triggers if and only if 3+ consecutive failures occur

  - [x]* 7.4 Write unit tests for Granite client
    - Test file: `tests/unit/test_openclaws_granite_client.py`
    - Test successful inference request and response parsing
    - Test 60s timeout handling (inform user, suggest retry)
    - Test 503 response (model loading)
    - Test 400 response (context exceeded, invalid params)
    - Test connection refused handling
    - _Requirements: 2.3, 2.5, 2.6, 2.7_

- [x] 8. Implement query processing pipeline
  - [x] 8.1 Implement `openclaws/prompt_builder.py` with `PromptBuilder` class
    - Implement `build_prompt(self, user_query: str, artifacts: list[SearchResult], legislation: list[LegislationSnippet]) -> str`
    - Include user query text in prompt
    - Include matched artifact data with folder paths and metadata fields
    - Include legislation snippets with citation instructions
    - Instruct LLM to cite contract_id, contract_number, law name, and article numbers
    - Instruct LLM to label claims as "based on available data" or "could not be determined from available artifacts"
    - _Requirements: 5.4, 6.1, 6.2, 6.3, 6.5_

  - [x]* 8.2 Write property test for prompt construction (Property 7)
    - **Property 7: Prompt construction includes all required components**
    - **Validates: Requirements 5.4, 6.1**
    - Test file: `tests/property/test_openclaws_query_props.py`
    - Use Hypothesis to generate queries, artifact lists, and legislation contexts
    - Verify prompt contains user query, artifact data with paths, and legislation snippets

  - [x] 8.3 Implement `openclaws/query_engine.py` with `QueryEngine` class
    - Implement `__init__(self, index, legislation, granite_client, prompt_builder)`
    - Implement `process_query(self, user_query: str) -> QueryResponse`
    - Search index for matching artifacts
    - Get relevant legislation content
    - Build prompt and send to Granite for inference
    - Return QueryResponse with answer, referenced contracts, legislation citations, and confidence labels
    - Handle no-match case: inform user no artifacts found, suggest refining query
    - Handle >20 matches: include truncation notice in response
    - Handle Granite timeout/unavailability: inform user, suggest retry
    - _Requirements: 5.3, 5.4, 5.7, 5.8, 6.4, 6.6_

  - [x]* 8.4 Write property tests for search correctness (Property 6)
    - **Property 6: Search returns only artifacts containing query terms**
    - **Validates: Requirements 5.3**
    - Test file: `tests/property/test_openclaws_query_props.py`
    - Use Hypothesis to generate queries and artifact indexes
    - Verify every result contains at least one query term in a searchable field

  - [x]* 8.5 Write property test for truncation notice (Property 9)
    - **Property 9: Truncation notice when results exceed limit**
    - **Validates: Requirements 6.6**
    - Test file: `tests/property/test_openclaws_query_props.py`
    - Use Hypothesis to generate indexes with >20 matching artifacts
    - Verify query response includes truncation notice

- [x] 9. Implement CLI interface
  - [x] 9.1 Implement `openclaws/cli.py` with main loop and input validation
    - Implement `main()` entry point that orchestrates startup sequence
    - Validate environment configuration (exit non-zero on invalid)
    - Scan target folder and build in-memory index
    - Fetch and cache legislation
    - Perform initial Granite health check
    - Start interactive CLI loop accepting user queries
    - Validate query length (1–2000 chars, reject empty/blank/over-limit with error message)
    - Display progress indicator while Granite processes inference
    - Display Analysis_Response with contract references and legislation citations
    - Handle Granite unreachable after startup: log error, exit within 30s
    - _Requirements: 5.1, 5.2, 5.5, 5.6, 5.7, 1.8_

  - [x]* 9.2 Write property test for query input validation (Property 5)
    - **Property 5: Query input validation accepts valid lengths and rejects invalid**
    - **Validates: Requirements 5.1, 5.2**
    - Test file: `tests/property/test_openclaws_query_props.py`
    - Use Hypothesis to generate strings of various lengths
    - Verify acceptance for stripped length 1–2000, rejection for empty/blank/over-limit

  - [x]* 9.3 Write unit tests for CLI interaction
    - Test file: `tests/unit/test_openclaws_cli.py`
    - Test progress indicator display
    - Test response formatting with contract references
    - Test error message display for invalid queries
    - Test graceful exit on Granite connectivity loss
    - _Requirements: 5.1, 5.2, 5.5, 5.6, 5.7_

- [x] 10. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Implement Docker containerization
  - [x] 11.1 Create `openclaws/Dockerfile`
    - Use Python 3.10+ slim base image
    - Copy openclaws package and install dependencies
    - Set read-only volume mount for target folder at `/app/target`
    - Set writable volume for legislation cache at `/app/legislation_cache`
    - Configure entry point to run `openclaws` CLI
    - Enable stdin/tty for interactive CLI usage
    - _Requirements: 1.1, 1.6_

  - [x] 11.2 Create `docker-compose.yml` with two-container architecture
    - Define `granite` service: IBM Granite LLM image, attached only to `openclaws-internal` network, health check (GET /health, interval 30s, timeout 5s, retries 3, start_period 120s), GPU reservation, environment variables for GraniteConfig
    - Define `openclaws` service: build from `openclaws/Dockerfile`, depends_on granite (condition: service_healthy), attached to both `default` and `openclaws-internal` networks, read-only target volume, writable cache volume, environment variables for AgentConfig, stdin_open and tty enabled
    - Define `openclaws-internal` network with `internal: true` (no external routing)
    - Define `openclaws-cache` named volume
    - Ensure Granite has no route to external hosts
    - Ensure OpenClaws Agent starts only after Granite is healthy
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 7.4_

  - [x] 11.3 Update `.dockerignore` and `.gitignore`
    - Add `openclaws-cache/`, `legislation_cache/` to `.dockerignore`
    - Add `legislation_cache/` to `.gitignore`
    - Ensure `.hypothesis/`, `__pycache__/`, `*.pyc` are in both ignore files
    - _Requirements: N/A (workspace policy)_

  - [x]* 11.4 Write unit tests for Docker Compose configuration validation
    - Test file: `tests/unit/test_openclaws_docker.py`
    - Validate docker-compose.yml structure programmatically (parse YAML, check networks, volumes, depends_on)
    - Verify granite service has no default network attachment
    - Verify openclaws service has both networks
    - Verify internal network has `internal: true`
    - _Requirements: 1.1, 1.2, 1.3, 1.5_

- [x] 12. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [~] 13. Version control and release
  - [x] Ensure all previous tasks are complete and tests pass
  - [-] Remove SNAPSHOT suffix from all version references in the codebase
  - [~] Commit the version bump: "release: 1.2.0 - openclaws-ai-assistant"
  - [~] Merge branch into main/master
  - [~] Apply Git tag: 1.2.0 (without SNAPSHOT)
  - [~] Push branch, merge, and tag to remote

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The implementation language is Python 3.10+ (matching the existing project)
- Hypothesis 6.122.3 is already available in dev dependencies
- PyPDF2 must be added as a new dependency
- All commits follow the pattern: `2026.000003.{task-number}: <short description>`

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2"] },
    { "id": 2, "tasks": ["2.1", "3.1"] },
    { "id": 3, "tasks": ["2.2", "2.3", "3.2", "4.1"] },
    { "id": 4, "tasks": ["4.2", "4.3"] },
    { "id": 5, "tasks": ["4.4", "4.5", "6.1"] },
    { "id": 6, "tasks": ["6.2", "7.1"] },
    { "id": 7, "tasks": ["7.2", "7.3", "7.4"] },
    { "id": 8, "tasks": ["8.1"] },
    { "id": 9, "tasks": ["8.2", "8.3"] },
    { "id": 10, "tasks": ["8.4", "8.5", "9.1"] },
    { "id": 11, "tasks": ["9.2", "9.3"] },
    { "id": 12, "tasks": ["11.1"] },
    { "id": 13, "tasks": ["11.2"] },
    { "id": 14, "tasks": ["11.3", "11.4"] }
  ]
}
```
