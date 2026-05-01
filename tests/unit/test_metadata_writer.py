"""Unit tests for the MetadataWriter component and ContractMetadata data model."""

import json
import os

from gov_data_crawler.contract import (
    ContractMetadata,
    HttpRequestError,
    ParsingError,
    ProcessingResult,
)
from gov_data_crawler.metadata import MetadataWriter


def _sample_metadata() -> ContractMetadata:
    """Create a sample ContractMetadata for testing."""
    return ContractMetadata(
        contract_id="500112",
        orgao="Ministério da Defesa",
        unidade_gestora="160089 - Base de Apoio Logístico do Exército",
        contract_number="01/2024",
        supplier_name="Empresa XYZ Ltda",
        contract_value="R$ 1.500.000,00",
        start_date="2024-01-15",
        end_date="2025-01-14",
        object_description="Prestação de serviços de manutenção predial",
        extra_fields={"modalidade": "Pregão Eletrônico", "situacao": "Ativo"},
        attachments=["contrato_001_2024.pdf", "termo_aditivo_001.pdf"],
        scraped_at="2026-01-15T10:30:00Z",
    )


class TestContractMetadata:
    """Tests for the ContractMetadata dataclass."""

    def test_all_fields_accessible(self) -> None:
        meta = _sample_metadata()
        assert meta.contract_id == "500112"
        assert meta.orgao == "Ministério da Defesa"
        assert meta.unidade_gestora == "160089 - Base de Apoio Logístico do Exército"
        assert meta.contract_number == "01/2024"
        assert meta.supplier_name == "Empresa XYZ Ltda"
        assert meta.contract_value == "R$ 1.500.000,00"
        assert meta.start_date == "2024-01-15"
        assert meta.end_date == "2025-01-14"
        assert meta.object_description == "Prestação de serviços de manutenção predial"
        assert meta.extra_fields == {"modalidade": "Pregão Eletrônico", "situacao": "Ativo"}
        assert meta.attachments == ["contrato_001_2024.pdf", "termo_aditivo_001.pdf"]
        assert meta.scraped_at == "2026-01-15T10:30:00Z"

    def test_empty_extra_fields_and_attachments(self) -> None:
        meta = ContractMetadata(
            contract_id="1",
            orgao="Org",
            unidade_gestora="UG",
            contract_number="01",
            supplier_name="Supplier",
            contract_value="R$ 0,00",
            start_date="2024-01-01",
            end_date="2024-12-31",
            object_description="Desc",
            extra_fields={},
            attachments=[],
            scraped_at="2026-01-01T00:00:00Z",
        )
        assert meta.extra_fields == {}
        assert meta.attachments == []


class TestProcessingResult:
    """Tests for the ProcessingResult dataclass."""

    def test_success_result(self) -> None:
        result = ProcessingResult(
            contract_id="500112", success=True, attachments_downloaded=3
        )
        assert result.contract_id == "500112"
        assert result.success is True
        assert result.attachments_downloaded == 3
        assert result.error is None

    def test_failure_result(self) -> None:
        result = ProcessingResult(
            contract_id="500112",
            success=False,
            attachments_downloaded=0,
            error="Connection timeout",
        )
        assert result.success is False
        assert result.error == "Connection timeout"


class TestHttpRequestError:
    """Tests for the HttpRequestError exception."""

    def test_attributes(self) -> None:
        err = HttpRequestError(
            url="https://example.com", status_code=503, message="Service unavailable"
        )
        assert err.url == "https://example.com"
        assert err.status_code == 503
        assert err.message == "Service unavailable"

    def test_none_status_code(self) -> None:
        err = HttpRequestError(
            url="https://example.com", status_code=None, message="Connection refused"
        )
        assert err.status_code is None

    def test_str_representation(self) -> None:
        err = HttpRequestError(
            url="https://example.com", status_code=500, message="Internal error"
        )
        assert "https://example.com" in str(err)
        assert "500" in str(err)


class TestParsingError:
    """Tests for the ParsingError exception."""

    def test_attributes(self) -> None:
        err = ParsingError(
            contract_id="500112", field="orgao", message="Field not found"
        )
        assert err.contract_id == "500112"
        assert err.field == "orgao"
        assert err.message == "Field not found"

    def test_str_representation(self) -> None:
        err = ParsingError(
            contract_id="500112", field="supplier_name", message="Empty value"
        )
        assert "500112" in str(err)
        assert "supplier_name" in str(err)


class TestMetadataWriterSerialization:
    """Tests for JSON serialization behavior."""

    def test_writes_valid_json(self, tmp_path) -> None:
        writer = MetadataWriter()
        meta = _sample_metadata()
        file_path = writer.write(meta, str(tmp_path))

        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        assert data["contract_id"] == "500112"
        assert data["orgao"] == "Ministério da Defesa"

    def test_preserves_non_ascii_characters(self, tmp_path) -> None:
        writer = MetadataWriter()
        meta = _sample_metadata()
        file_path = writer.write(meta, str(tmp_path))

        with open(file_path, encoding="utf-8") as f:
            raw = f.read()

        # ensure_ascii=False means accented characters appear directly
        assert "Ministério" in raw
        assert "Logístico" in raw
        assert "Exército" in raw
        assert "Prestação" in raw
        assert "manutenção" in raw

    def test_json_is_indented(self, tmp_path) -> None:
        writer = MetadataWriter()
        meta = _sample_metadata()
        file_path = writer.write(meta, str(tmp_path))

        with open(file_path, encoding="utf-8") as f:
            raw = f.read()

        # indent=2 means lines should start with spaces
        assert '\n  "contract_id"' in raw

    def test_all_fields_present_in_json(self, tmp_path) -> None:
        writer = MetadataWriter()
        meta = _sample_metadata()
        file_path = writer.write(meta, str(tmp_path))

        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        expected_keys = {
            "contract_id",
            "orgao",
            "unidade_gestora",
            "contract_number",
            "supplier_name",
            "contract_value",
            "start_date",
            "end_date",
            "object_description",
            "extra_fields",
            "attachments",
            "scraped_at",
        }
        assert set(data.keys()) == expected_keys

    def test_extra_fields_serialized_as_dict(self, tmp_path) -> None:
        writer = MetadataWriter()
        meta = _sample_metadata()
        file_path = writer.write(meta, str(tmp_path))

        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        assert isinstance(data["extra_fields"], dict)
        assert data["extra_fields"]["modalidade"] == "Pregão Eletrônico"

    def test_attachments_serialized_as_list(self, tmp_path) -> None:
        writer = MetadataWriter()
        meta = _sample_metadata()
        file_path = writer.write(meta, str(tmp_path))

        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        assert isinstance(data["attachments"], list)
        assert len(data["attachments"]) == 2


class TestMetadataWriterFileWriting:
    """Tests for file writing behavior."""

    def test_writes_to_metadata_json(self, tmp_path) -> None:
        writer = MetadataWriter()
        meta = _sample_metadata()
        file_path = writer.write(meta, str(tmp_path))

        assert os.path.basename(file_path) == "metadata.json"
        assert os.path.isfile(file_path)

    def test_returns_absolute_path(self, tmp_path) -> None:
        writer = MetadataWriter()
        meta = _sample_metadata()
        file_path = writer.write(meta, str(tmp_path))

        assert os.path.isabs(file_path)

    def test_creates_target_directory_if_missing(self, tmp_path) -> None:
        writer = MetadataWriter()
        meta = _sample_metadata()
        nested_dir = str(tmp_path / "a" / "b" / "c")
        file_path = writer.write(meta, nested_dir)

        assert os.path.isfile(file_path)

    def test_overwrites_existing_metadata(self, tmp_path) -> None:
        writer = MetadataWriter()
        meta1 = _sample_metadata()
        writer.write(meta1, str(tmp_path))

        meta2 = ContractMetadata(
            contract_id="999",
            orgao="Updated Org",
            unidade_gestora="Updated UG",
            contract_number="99/2024",
            supplier_name="New Supplier",
            contract_value="R$ 0,00",
            start_date="2024-06-01",
            end_date="2025-06-01",
            object_description="Updated description",
            extra_fields={},
            attachments=[],
            scraped_at="2026-06-01T00:00:00Z",
        )
        file_path = writer.write(meta2, str(tmp_path))

        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        assert data["contract_id"] == "999"
        assert data["orgao"] == "Updated Org"
