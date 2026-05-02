# Requirements Document

## Introduction

This feature extends GovDataCrawler with filtering capabilities for the contract listing scrape. Currently, the Crawler collects all contracts from the ComprasNet transparency portal without discrimination. This enhancement adds two optional CLI filters — organ number (número do órgão) and category (categoria) — so that users can restrict the scrape to contracts matching specific government organizations and/or contract categories. Filters are applied at the listing navigation level by including query parameters in the DataTables API requests, reducing both network traffic and processing time.

## Glossary

- **Crawler**: The main GovDataCrawler application responsible for navigating web pages, extracting data, and downloading files from the ComprasNet_Portal
- **ComprasNet_Portal**: The Brazilian government transparency website at `https://contratos.comprasnet.gov.br/transparencia/contratos` that publishes public contract data
- **Organ_Number**: A numeric identifier representing a top-level government organization (Órgão) on the ComprasNet_Portal, used as a query parameter to filter the contract listing
- **Category**: A string identifier representing a contract category (Categoria) on the ComprasNet_Portal, used as a query parameter to filter the contract listing
- **Filter_Parameters**: The set of optional query parameters (Organ_Number and/or Category) that restrict which contracts appear in the listing results
- **ListingNavigator**: The component responsible for paginating through contract listing pages and collecting Contract_ID values via the DataTables server-side API
- **CLI**: The command-line interface module (`gov_data_crawler/cli.py`) that parses user-provided arguments and configures the Crawler
- **DataTables_API**: The server-side search endpoint (`/transparencia/contratos/search`) used by the ComprasNet_Portal to return paginated contract listings as JSON

## Requirements

### Requirement 1: Organ Number CLI Argument

**User Story:** As a data analyst, I want to specify a government organ number when launching the Crawler, so that only contracts belonging to that organization are scraped.

#### Acceptance Criteria

1. THE CLI SHALL accept an optional `--orgao` argument that takes a string value representing the Organ_Number
2. WHEN the user provides the `--orgao` argument, THE CLI SHALL store the value for use by the ListingNavigator
3. WHEN the user does not provide the `--orgao` argument, THE CLI SHALL default the value to None, indicating no organ filter is applied
4. THE CLI SHALL include a help description for the `--orgao` argument that reads: "Filter contracts by government organ number (número do órgão)"

### Requirement 2: Category CLI Argument

**User Story:** As a data analyst, I want to specify a contract category when launching the Crawler, so that only contracts in that category are scraped.

#### Acceptance Criteria

1. THE CLI SHALL accept an optional `--categoria` argument that takes a string value representing the Category
2. WHEN the user provides the `--categoria` argument, THE CLI SHALL store the value for use by the ListingNavigator
3. WHEN the user does not provide the `--categoria` argument, THE CLI SHALL default the value to None, indicating no category filter is applied
4. THE CLI SHALL include a help description for the `--categoria` argument that reads: "Filter contracts by category (categoria)"

### Requirement 3: Filter Application to DataTables API Requests

**User Story:** As a data analyst, I want the filters to be sent as parameters in the listing API requests, so that the ComprasNet_Portal returns only matching contracts.

#### Acceptance Criteria

1. WHEN the user provides an Organ_Number filter, THE ListingNavigator SHALL include the Organ_Number value as a POST parameter in every request to the DataTables_API
2. WHEN the user provides a Category filter, THE ListingNavigator SHALL include the Category value as a POST parameter in every request to the DataTables_API
3. WHEN the user provides both an Organ_Number filter and a Category filter, THE ListingNavigator SHALL include both values as POST parameters in every request to the DataTables_API, applying AND logic so that only contracts matching both criteria are returned
4. WHEN the user provides no filters, THE ListingNavigator SHALL send requests to the DataTables_API without any filter parameters, preserving the current behavior of collecting all contracts

### Requirement 4: Filter Application to HTML Fallback Scraping

**User Story:** As a data analyst, I want the filters to work even when the DataTables API is unavailable, so that the HTML fallback scraping path also respects my filter selections.

#### Acceptance Criteria

1. WHEN the DataTables_API is unavailable and the HTML fallback scraping path is used, THE ListingNavigator SHALL append the Organ_Number and/or Category as query parameters to the listing page URL
2. WHEN no filters are provided and the HTML fallback path is used, THE ListingNavigator SHALL use the original listing page URL without additional query parameters

### Requirement 5: Active Filter Logging

**User Story:** As a data analyst, I want the Crawler to log which filters are active at startup, so that I can confirm the correct filters are being applied before the crawl begins.

#### Acceptance Criteria

1. WHEN the Crawler starts with one or more Filter_Parameters configured, THE Crawler SHALL log each active filter name and its value at INFO level before beginning the listing navigation
2. WHEN the Crawler starts with no Filter_Parameters configured, THE Crawler SHALL log a message at INFO level indicating that no filters are active and all contracts will be collected
3. WHEN the crawl execution summary is produced, THE Crawler SHALL include the active Filter_Parameters in the summary output

### Requirement 6: Filter Parameter Propagation

**User Story:** As a data analyst, I want the filter values to flow from the CLI through to the listing navigator, so that the entire pipeline respects my filter choices.

#### Acceptance Criteria

1. WHEN the CLI parses the `--orgao` and `--categoria` arguments, THE CLI SHALL pass the filter values to the ListingNavigator during component construction
2. THE ListingNavigator SHALL accept optional Organ_Number and Category parameters in its constructor
3. THE ListingNavigator SHALL use the stored filter values consistently across all paginated requests within a single crawl execution