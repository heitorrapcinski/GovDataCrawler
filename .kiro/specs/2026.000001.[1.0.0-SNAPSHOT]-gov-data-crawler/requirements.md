# Requirements Document

## Introduction

GovDataCrawler is a web scraping tool designed to collect public contract data from the Brazilian government's ComprasNet transparency portal. The tool navigates paginated contract listings, extracts detailed contract information, downloads attached files, and organizes all collected data into a structured folder hierarchy by organization, management unit, and contract. A configurable delay mechanism simulates human browsing behavior to avoid triggering anti-bot protections.

## Glossary

- **Crawler**: The main application responsible for navigating web pages, extracting data, and downloading files from the ComprasNet portal
- **ComprasNet_Portal**: The Brazilian government transparency website at `https://contratos.comprasnet.gov.br/transparencia/contratos` that publishes public contract data
- **Contract_Listing_Page**: A paginated page on the ComprasNet_Portal that displays a list of contracts with summary information
- **Contract_Detail_Page**: A page on the ComprasNet_Portal at `https://contratos.comprasnet.gov.br/transparencia/contratos/{id}` that displays full details for a single contract
- **Contract_ID**: A unique numeric identifier assigned to each contract on the ComprasNet_Portal (e.g., `500112`)
- **Orgao**: The top-level government organization (Órgão) responsible for a contract
- **Unidade_Gestora**: The management unit (Unidade Gestora) within an Orgao that manages a specific contract
- **Attachment**: A file (PDF, document, spreadsheet, or other format) linked to a contract on the Contract_Detail_Page
- **Delay_Mechanism**: A configurable pause between HTTP requests that simulates human browsing behavior to avoid anti-bot detection
- **Output_Directory**: The root folder (default: `target`) where the Crawler stores all scraped data and downloaded files
- **Contract_Metadata**: A JSON file containing all extracted data fields for a single contract
- **PNCP**: Portal Nacional de Contratações Públicas (National Public Procurement Portal)
- **Pagination**: The mechanism used by the ComprasNet_Portal to split contract listings across multiple pages
- **Maximum_Execution_Time**: A user-configurable time limit (in seconds) after which the Crawler stops processing new contracts
- **Maximum_Contract_Count**: A user-configurable limit on the number of contracts to successfully collect before the Crawler stops

## Requirements

### Requirement 1: Contract Listing Navigation

**User Story:** As a data analyst, I want the Crawler to navigate all pages of the contract listing, so that I can collect data from every available contract.

#### Acceptance Criteria

1. WHEN the Crawler is started, THE Crawler SHALL send an HTTP GET request to the Contract_Listing_Page at `https://contratos.comprasnet.gov.br/transparencia/contratos`
2. WHEN a Contract_Listing_Page is loaded, THE Crawler SHALL extract all Contract_ID values present on that page
3. WHEN a Contract_Listing_Page contains a link to a next page, THE Crawler SHALL navigate to the next Contract_Listing_Page after applying the Delay_Mechanism
4. WHEN a Contract_Listing_Page does not contain a link to a next page, THE Crawler SHALL stop pagination and proceed to process the collected Contract_ID values
5. IF the Crawler fails to load a Contract_Listing_Page, THEN THE Crawler SHALL log the error with the page URL and retry the request up to 3 times with exponential backoff

### Requirement 2: Contract Detail Extraction

**User Story:** As a data analyst, I want the Crawler to extract all available data from each contract's detail page, so that I have complete contract information.

#### Acceptance Criteria

1. WHEN a Contract_ID is available for processing, THE Crawler SHALL send an HTTP GET request to the Contract_Detail_Page at `https://contratos.comprasnet.gov.br/transparencia/contratos/{Contract_ID}`
2. WHEN a Contract_Detail_Page is loaded, THE Crawler SHALL extract all visible data fields including but not limited to: Orgao, Unidade_Gestora, contract number, supplier name, contract value, start date, end date, and contract object description
3. WHEN a Contract_Detail_Page is loaded, THE Crawler SHALL store the extracted data as a Contract_Metadata JSON file in the appropriate Output_Directory subfolder
4. IF the Crawler fails to load a Contract_Detail_Page, THEN THE Crawler SHALL log the error with the Contract_ID and continue processing the remaining contracts
5. IF a Contract_Detail_Page returns an HTTP 404 status, THEN THE Crawler SHALL log the missing Contract_ID and skip to the next contract without retrying

### Requirement 3: Attachment Download

**User Story:** As a data analyst, I want the Crawler to download all files attached to each contract, so that I have the complete documentation for every contract.

#### Acceptance Criteria

1. WHEN a Contract_Detail_Page contains one or more Attachment links, THE Crawler SHALL download each Attachment file
2. WHEN an Attachment is downloaded, THE Crawler SHALL save the file in the same Output_Directory subfolder as the corresponding Contract_Metadata file
3. WHEN an Attachment is downloaded, THE Crawler SHALL preserve the original file name from the download link
4. IF an Attachment download fails, THEN THE Crawler SHALL log the error with the Attachment URL and Contract_ID and continue processing the remaining Attachments
5. IF a Contract_Detail_Page contains no Attachment links, THEN THE Crawler SHALL log that no attachments were found for the Contract_ID and proceed to the next contract

### Requirement 4: Delay Mechanism

**User Story:** As a data analyst, I want the Crawler to pause between requests simulating human browsing, so that the tool avoids triggering anti-bot protections on the ComprasNet_Portal.

#### Acceptance Criteria

1. THE Crawler SHALL apply the Delay_Mechanism between every consecutive HTTP request to the ComprasNet_Portal
2. THE Delay_Mechanism SHALL pause execution for a random duration between a configurable minimum and maximum number of seconds
3. THE Delay_Mechanism SHALL use default values of 2 seconds minimum and 5 seconds maximum when no configuration is provided
4. WHEN the user provides custom minimum and maximum delay values, THE Crawler SHALL use the provided values instead of the defaults
5. IF the configured minimum delay value is greater than the maximum delay value, THEN THE Crawler SHALL log a warning and swap the values so that the smaller value becomes the minimum

### Requirement 5: Output Directory Structure

**User Story:** As a data analyst, I want the scraped data organized in a hierarchical folder structure, so that I can easily locate contracts by organization and management unit.

#### Acceptance Criteria

1. THE Crawler SHALL create the Output_Directory structure following the pattern: `{Output_Directory}/{Orgao}/{Unidade_Gestora}/{Contract_ID}/`
2. WHEN a Contract_Metadata file is saved, THE Crawler SHALL place the file inside the folder corresponding to the contract's Orgao, Unidade_Gestora, and Contract_ID
3. WHEN an Attachment is saved, THE Crawler SHALL place the file inside the same folder as the corresponding Contract_Metadata file
4. THE Crawler SHALL sanitize folder names by replacing characters that are invalid in file system paths with underscores
5. IF the Output_Directory does not exist when the Crawler starts, THEN THE Crawler SHALL create the directory and all necessary parent directories
6. THE Crawler SHALL use `target` as the default Output_Directory name when no custom path is provided

### Requirement 6: Execution Logging

**User Story:** As a data analyst, I want the Crawler to log its progress and any errors, so that I can monitor execution and troubleshoot issues.

#### Acceptance Criteria

1. THE Crawler SHALL log the start and end of each execution run with a timestamp
2. WHEN a Contract_Detail_Page is successfully processed, THE Crawler SHALL log the Contract_ID and the output folder path
3. WHEN an error occurs during any operation, THE Crawler SHALL log the error message, the affected resource URL, and a timestamp
4. THE Crawler SHALL write log output to both the console (standard output) and a log file in the Output_Directory
5. WHEN an execution run completes, THE Crawler SHALL log a summary containing the total number of contracts processed, the number of successful extractions, the number of failed extractions, and the total number of Attachments downloaded

### Requirement 7: Execution Resumption

**User Story:** As a data analyst, I want the Crawler to resume from where it stopped if interrupted, so that I do not need to re-scrape contracts that were already collected.

#### Acceptance Criteria

1. WHEN the Crawler starts and the Output_Directory already contains previously scraped data, THE Crawler SHALL detect which Contract_ID values have already been processed
2. WHEN a Contract_ID has already been processed (a Contract_Metadata file exists in the expected folder), THE Crawler SHALL skip that contract and proceed to the next one
3. THE Crawler SHALL log the number of previously processed contracts that were skipped during resumption

### Requirement 8: Crawl Stopping Criteria

**User Story:** As a data analyst, I want to define stopping conditions for the crawl, so that the Crawler does not run indefinitely and I can control resource consumption.

#### Acceptance Criteria

1. WHEN the user provides a maximum execution time, THE Crawler SHALL stop processing new contracts after the specified duration has elapsed
2. WHEN the user provides a maximum number of contracts to collect, THE Crawler SHALL stop processing new contracts after the specified count of successfully processed contracts is reached
3. THE Crawler SHALL use no limit as the default for both maximum execution time and maximum number of contracts when no configuration is provided
4. WHEN a stopping condition is met during execution, THE Crawler SHALL finish processing the current contract before stopping
5. WHEN a stopping condition causes the crawl to end early, THE Crawler SHALL log which stopping condition was triggered and the final execution statistics
6. WHERE both a maximum execution time and a maximum number of contracts are configured, THE Crawler SHALL stop when the first condition is met
