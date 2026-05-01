"""Unit tests for the DetailParser component."""

import pytest

from gov_data_crawler.contract import ContractMetadata, ParsingError
from gov_data_crawler.detail_parser import DetailParser


def _build_detail_html(
    fields: dict[str, str] | None = None,
    attachments: list[tuple[str, str]] | None = None,
    *,
    include_detail_section: bool = True,
    include_attachments_section: bool = True,
) -> str:
    """Build a minimal ComprasNet-style detail page HTML.

    Args:
        fields: Mapping of label text to value text for field-group divs.
        attachments: List of (href, text) tuples for attachment links.
        include_detail_section: Whether to wrap fields in a detail-section div.
        include_attachments_section: Whether to include the attachments div.

    Returns:
        HTML string.
    """
    field_groups = ""
    if fields:
        for label, value in fields.items():
            field_groups += (
                f'<div class="field-group">'
                f'<span class="field-label">{label}:</span>'
                f'<span class="field-value">{value}</span>'
                f"</div>\n"
            )

    detail_section = ""
    if include_detail_section and field_groups:
        detail_section = f'<div class="detail-section">\n{field_groups}</div>'

    attachment_section = ""
    if include_attachments_section and attachments:
        links = "\n".join(
            f'<a href="{href}">{text}</a>' for href, text in attachments
        )
        attachment_section = f'<div class="attachments">\n{links}\n</div>'

    return f"<html><body>\n{detail_section}\n{attachment_section}\n</body></html>"


# ---------------------------------------------------------------------------
# Minimal required fields for a valid detail page
# ---------------------------------------------------------------------------
_REQUIRED_FIELDS = {
    "Órgão": "Ministério da Defesa",
    "Unidade Gestora": "160089 - Base de Apoio Logístico do Exército",
}

_ALL_FIELDS = {
    **_REQUIRED_FIELDS,
    "Número do Contrato": "01/2024",
    "Fornecedor": "Empresa XYZ Ltda",
    "Valor do Contrato": "R$ 1.500.000,00",
    "Data de Início": "2024-01-15",
    "Data de Término": "2025-01-14",
    "Objeto": "Prestação de serviços de manutenção predial",
}


class TestDetailParserFieldExtraction:
    """Tests for DetailParser.parse field extraction."""

    def test_extracts_all_standard_fields(self) -> None:
        """All standard fields are correctly mapped to ContractMetadata."""
        html = _build_detail_html(fields=_ALL_FIELDS)
        parser = DetailParser()
        result = parser.parse(html, "500112")

        assert result.contract_id == "500112"
        assert result.orgao == "Ministério da Defesa"
        assert result.unidade_gestora == "160089 - Base de Apoio Logístico do Exército"
        assert result.contract_number == "01/2024"
        assert result.supplier_name == "Empresa XYZ Ltda"
        assert result.contract_value == "R$ 1.500.000,00"
        assert result.start_date == "2024-01-15"
        assert result.end_date == "2025-01-14"
        assert result.object_description == "Prestação de serviços de manutenção predial"

    def test_extracts_with_alternative_labels(self) -> None:
        """Alternative Portuguese labels are correctly mapped."""
        fields = {
            "Orgao": "Ministério da Educação",
            "Unidade Gestora": "150001 - Secretaria Executiva",
            "Contrato": "02/2024",
            "Razão Social": "Empresa ABC Ltda",
            "Valor": "R$ 500.000,00",
            "Início": "2024-03-01",
            "Término": "2025-02-28",
            "Objeto do Contrato": "Fornecimento de material de escritório",
        }
        html = _build_detail_html(fields=fields)
        parser = DetailParser()
        result = parser.parse(html, "600200")

        assert result.orgao == "Ministério da Educação"
        assert result.unidade_gestora == "150001 - Secretaria Executiva"
        assert result.contract_number == "02/2024"
        assert result.supplier_name == "Empresa ABC Ltda"
        assert result.contract_value == "R$ 500.000,00"
        assert result.start_date == "2024-03-01"
        assert result.end_date == "2025-02-28"
        assert result.object_description == "Fornecimento de material de escritório"

    def test_extracts_with_vigencia_labels(self) -> None:
        """Vigência-style date labels are correctly mapped."""
        fields = {
            **_REQUIRED_FIELDS,
            "Vigência Início": "2024-06-01",
            "Vigência Fim": "2025-05-31",
        }
        html = _build_detail_html(fields=fields)
        parser = DetailParser()
        result = parser.parse(html, "700300")

        assert result.start_date == "2024-06-01"
        assert result.end_date == "2025-05-31"

    def test_extra_fields_captured(self) -> None:
        """Unrecognised labels are stored in extra_fields."""
        fields = {
            **_REQUIRED_FIELDS,
            "Modalidade": "Pregão Eletrônico",
            "Situação": "Ativo",
        }
        html = _build_detail_html(fields=fields)
        parser = DetailParser()
        result = parser.parse(html, "800400")

        assert result.extra_fields == {
            "Modalidade": "Pregão Eletrônico",
            "Situação": "Ativo",
        }

    def test_scraped_at_is_utc_iso_format(self) -> None:
        """The scraped_at field is a UTC ISO-format timestamp."""
        html = _build_detail_html(fields=_REQUIRED_FIELDS)
        parser = DetailParser()
        result = parser.parse(html, "900500")

        # Should end with Z and be parseable
        assert result.scraped_at.endswith("Z")
        assert "T" in result.scraped_at

    def test_attachments_list_initially_empty(self) -> None:
        """The attachments list is empty after parse (populated separately)."""
        html = _build_detail_html(fields=_REQUIRED_FIELDS)
        parser = DetailParser()
        result = parser.parse(html, "100600")

        assert result.attachments == []


class TestDetailParserMissingFields:
    """Tests for handling missing fields."""

    def test_optional_fields_default_to_empty_string(self) -> None:
        """Missing optional fields default to empty strings."""
        html = _build_detail_html(fields=_REQUIRED_FIELDS)
        parser = DetailParser()
        result = parser.parse(html, "200700")

        assert result.contract_number == ""
        assert result.supplier_name == ""
        assert result.contract_value == ""
        assert result.start_date == ""
        assert result.end_date == ""
        assert result.object_description == ""

    def test_missing_orgao_raises_parsing_error(self) -> None:
        """Missing orgao field raises ParsingError."""
        fields = {"Unidade Gestora": "160089 - Base de Apoio"}
        html = _build_detail_html(fields=fields)
        parser = DetailParser()

        with pytest.raises(ParsingError) as exc_info:
            parser.parse(html, "300800")

        assert exc_info.value.contract_id == "300800"
        assert exc_info.value.field == "orgao"

    def test_missing_unidade_gestora_raises_parsing_error(self) -> None:
        """Missing unidade_gestora field raises ParsingError."""
        fields = {"Órgão": "Ministério da Defesa"}
        html = _build_detail_html(fields=fields)
        parser = DetailParser()

        with pytest.raises(ParsingError) as exc_info:
            parser.parse(html, "400900")

        assert exc_info.value.contract_id == "400900"
        assert exc_info.value.field == "unidade_gestora"

    def test_empty_html_raises_parsing_error(self) -> None:
        """An empty HTML page raises ParsingError for required fields."""
        html = "<html><body></body></html>"
        parser = DetailParser()

        with pytest.raises(ParsingError):
            parser.parse(html, "500100")

    def test_no_field_groups_raises_parsing_error(self) -> None:
        """A page with no field-group divs raises ParsingError."""
        html = "<html><body><div class='detail-section'><p>No data</p></div></body></html>"
        parser = DetailParser()

        with pytest.raises(ParsingError):
            parser.parse(html, "600200")


class TestDetailParserAttachmentUrls:
    """Tests for DetailParser.parse_attachment_urls."""

    def test_extracts_attachment_urls(self) -> None:
        """Attachment links are extracted as absolute URLs."""
        html = _build_detail_html(
            fields=_REQUIRED_FIELDS,
            attachments=[
                ("/download/contrato_001_2024.pdf", "contrato_001_2024.pdf"),
                ("/download/termo_aditivo_001.pdf", "termo_aditivo_001.pdf"),
            ],
        )
        parser = DetailParser()
        urls = parser.parse_attachment_urls(html)

        assert urls == [
            "https://contratos.comprasnet.gov.br/download/contrato_001_2024.pdf",
            "https://contratos.comprasnet.gov.br/download/termo_aditivo_001.pdf",
        ]

    def test_handles_absolute_attachment_urls(self) -> None:
        """Absolute attachment URLs are preserved."""
        html = _build_detail_html(
            fields=_REQUIRED_FIELDS,
            attachments=[
                (
                    "https://contratos.comprasnet.gov.br/download/doc.pdf",
                    "doc.pdf",
                ),
            ],
        )
        parser = DetailParser()
        urls = parser.parse_attachment_urls(html)

        assert urls == [
            "https://contratos.comprasnet.gov.br/download/doc.pdf",
        ]

    def test_no_attachments_section_returns_empty(self) -> None:
        """A page without an attachments div returns an empty list."""
        html = _build_detail_html(
            fields=_REQUIRED_FIELDS,
            include_attachments_section=False,
        )
        parser = DetailParser()
        urls = parser.parse_attachment_urls(html)

        assert urls == []

    def test_empty_attachments_section_returns_empty(self) -> None:
        """An attachments div with no links returns an empty list."""
        html = (
            '<html><body>'
            '<div class="attachments"><p>No files available</p></div>'
            '</body></html>'
        )
        parser = DetailParser()
        urls = parser.parse_attachment_urls(html)

        assert urls == []

    def test_multiple_attachments_extracted_in_order(self) -> None:
        """Multiple attachment links are returned in document order."""
        html = _build_detail_html(
            fields=_REQUIRED_FIELDS,
            attachments=[
                ("/download/a.pdf", "a.pdf"),
                ("/download/b.pdf", "b.pdf"),
                ("/download/c.pdf", "c.pdf"),
            ],
        )
        parser = DetailParser()
        urls = parser.parse_attachment_urls(html)

        assert len(urls) == 3
        assert urls[0].endswith("/a.pdf")
        assert urls[1].endswith("/b.pdf")
        assert urls[2].endswith("/c.pdf")
