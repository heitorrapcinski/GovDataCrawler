"""Detail page parser for ComprasNet contract detail pages."""

from datetime import datetime, timezone
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from gov_data_crawler.contract import ContractMetadata, ParsingError

BASE_URL = "https://contratos.comprasnet.gov.br"

# Mapping of Portuguese labels to ContractMetadata field names.
# Each field maps to a list of possible label variations found on the portal.
_FIELD_LABEL_MAP: dict[str, list[str]] = {
    "orgao": ["Órgão", "Orgao"],
    "unidade_gestora": ["Unidade Gestora"],
    "contract_number": [
        "Número do Contrato",
        "Número Contrato",
        "Contrato",
    ],
    "supplier_name": ["Fornecedor", "Razão Social"],
    "contract_value": [
        "Valor do Contrato",
        "Valor Global",
        "Valor",
    ],
    "start_date": [
        "Data de Início",
        "Início",
        "Vigência Início",
        "Vig. Início",
    ],
    "end_date": [
        "Data de Término",
        "Término",
        "Vigência Fim",
        "Vig. Fim",
    ],
    "object_description": ["Objeto", "Objeto do Contrato"],
}

# Fields that must be present; a ParsingError is raised if they are missing.
_REQUIRED_FIELDS = {"orgao", "unidade_gestora"}


def _build_label_to_field_map() -> dict[str, str]:
    """Build a reverse lookup from normalised label text to field name."""
    mapping: dict[str, str] = {}
    for field_name, labels in _FIELD_LABEL_MAP.items():
        for label in labels:
            mapping[label.strip().lower()] = field_name
    return mapping


_LABEL_TO_FIELD: dict[str, str] = _build_label_to_field_map()


class DetailParser:
    """Extracts structured data from a contract detail page."""

    def parse(self, html: str, contract_id: str) -> ContractMetadata:
        """Parse a contract detail page into structured metadata.

        Supports two HTML layouts:

        1. **Legacy layout** — ``<div class="field-group">`` elements
           containing ``<span class="field-label">`` /
           ``<span class="field-value">`` pairs.
        2. **Table layout** (current portal) — ``<table>`` rows where the
           first ``<td>`` holds a ``<strong>`` label and the second ``<td>``
           holds the value.

        Args:
            html: Raw HTML of the contract detail page.
            contract_id: The contract's ID for reference.

        Returns:
            ContractMetadata with all extracted fields.

        Raises:
            ParsingError: If a required field (orgao, unidade_gestora) cannot
                be extracted.
        """
        soup = BeautifulSoup(html, "lxml")

        extracted: dict[str, str] = {}
        extra_fields: dict[str, str] = {}

        # Strategy 1: Legacy field-group layout.
        self._extract_from_field_groups(soup, extracted, extra_fields)

        # Strategy 2: Table-based layout (current portal).
        if not extracted:
            self._extract_from_table_rows(soup, extracted, extra_fields)

        # Validate required fields.
        for field in _REQUIRED_FIELDS:
            if field not in extracted:
                raise ParsingError(
                    contract_id=contract_id,
                    field=field,
                    message=f"Required field '{field}' not found in detail page",
                )

        return ContractMetadata(
            contract_id=contract_id,
            orgao=extracted.get("orgao", ""),
            unidade_gestora=extracted.get("unidade_gestora", ""),
            contract_number=extracted.get("contract_number", ""),
            supplier_name=extracted.get("supplier_name", ""),
            contract_value=extracted.get("contract_value", ""),
            start_date=extracted.get("start_date", ""),
            end_date=extracted.get("end_date", ""),
            object_description=extracted.get("object_description", ""),
            extra_fields=extra_fields,
            attachments=[],
            scraped_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

    # ------------------------------------------------------------------
    # Extraction strategies
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_from_field_groups(
        soup: BeautifulSoup,
        extracted: dict[str, str],
        extra_fields: dict[str, str],
    ) -> None:
        """Extract fields from ``<div class="field-group">`` elements."""
        for group in soup.find_all("div", class_="field-group"):
            label_el = group.find("span", class_="field-label")
            value_el = group.find("span", class_="field-value")

            if label_el is None or value_el is None:
                continue

            raw_label = label_el.get_text(strip=True).rstrip(":")
            value = value_el.get_text(strip=True)
            normalised_label = raw_label.strip().lower()

            field_name = _LABEL_TO_FIELD.get(normalised_label)
            if field_name is not None:
                extracted[field_name] = value
            else:
                extra_fields[raw_label] = value

    @staticmethod
    def _extract_from_table_rows(
        soup: BeautifulSoup,
        extracted: dict[str, str],
        extra_fields: dict[str, str],
    ) -> None:
        """Extract fields from ``<tr>`` rows with ``<strong>`` labels.

        The current ComprasNet portal renders contract details as a table
        where each row has two cells: the first contains a ``<strong>``
        element with the label, and the second contains the value (often
        wrapped in a ``<span>``).
        """
        for row in soup.find_all("tr"):
            cells = row.find_all("td", recursive=False)
            if len(cells) < 2:
                continue

            strong_el = cells[0].find("strong")
            if strong_el is None:
                continue

            raw_label = strong_el.get_text(strip=True).rstrip(":")
            if not raw_label:
                continue

            # Get the value from the second cell.  Prefer the text of a
            # <span> child if present (it often carries a cleaner value
            # via its ``title`` attribute), otherwise use the cell text.
            value_cell = cells[1]
            span_el = value_cell.find("span", recursive=False)
            if span_el is not None:
                # The ``title`` attribute often has the full untruncated
                # value; fall back to the element text.
                value = (
                    span_el.get("title", "").strip()
                    or span_el.get_text(strip=True)
                )
            else:
                value = value_cell.get_text(strip=True)

            # Skip empty values and nested tables (sub-sections like
            # "Histórico", "Empenhos", etc. that contain their own tables).
            if not value or value_cell.find("table"):
                continue

            normalised_label = raw_label.strip().lower()
            field_name = _LABEL_TO_FIELD.get(normalised_label)
            if field_name is not None:
                extracted[field_name] = value
            else:
                extra_fields[raw_label] = value

    # ------------------------------------------------------------------
    # Attachment extraction
    # ------------------------------------------------------------------

    def parse_attachment_urls(self, html: str) -> list[str]:
        """Extract all attachment download URLs from a detail page.

        Looks for anchor tags inside ``<div class="attachments">`` whose
        ``href`` points to a download path, and returns absolute URLs.
        Also checks for file links in the "Arquivos" table section.

        Args:
            html: Raw HTML of the contract detail page.

        Returns:
            List of absolute URLs for downloadable attachments.
        """
        soup = BeautifulSoup(html, "lxml")
        urls: list[str] = []
        seen: set[str] = set()

        # Strategy 1: Legacy attachments div.
        attachments_div = soup.find("div", class_="attachments")
        if attachments_div is not None:
            for link in attachments_div.find_all("a", href=True):
                href = link["href"]
                absolute_url = urljoin(BASE_URL, href)
                if absolute_url not in seen:
                    seen.add(absolute_url)
                    urls.append(absolute_url)

        # Strategy 2: Look for download links anywhere on the page
        # that point to file download paths.
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if "/download" in href or "/arquivo" in href:
                absolute_url = urljoin(BASE_URL, href)
                if absolute_url not in seen:
                    seen.add(absolute_url)
                    urls.append(absolute_url)

        return urls
