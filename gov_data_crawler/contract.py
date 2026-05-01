"""Data models and exceptions for contract processing."""

from dataclasses import dataclass, field


@dataclass
class ContractMetadata:
    """Structured representation of a contract's extracted data."""

    contract_id: str
    orgao: str
    unidade_gestora: str
    contract_number: str
    supplier_name: str
    contract_value: str
    start_date: str
    end_date: str
    object_description: str
    extra_fields: dict[str, str]
    attachments: list[str]
    scraped_at: str


@dataclass
class ProcessingResult:
    """Result of processing a single contract."""

    contract_id: str
    success: bool
    attachments_downloaded: int
    error: str | None = None


class HttpRequestError(Exception):
    """Raised when an HTTP request fails after all retries."""

    def __init__(self, url: str, status_code: int | None, message: str) -> None:
        self.url = url
        self.status_code = status_code
        self.message = message
        super().__init__(f"HTTP error for {url} (status={status_code}): {message}")


class ParsingError(Exception):
    """Raised when HTML parsing fails to extract required fields."""

    def __init__(self, contract_id: str, field: str, message: str) -> None:
        self.contract_id = contract_id
        self.field = field
        self.message = message
        super().__init__(
            f"Parsing error for contract {contract_id}, field '{field}': {message}"
        )
