"""Unit tests for the OutputManager component."""

import json
import os

from gov_data_crawler.output import OutputManager


class TestOutputManagerDefaultDirectory:
    """Tests for default base directory behavior."""

    def test_default_base_dir_is_target(self) -> None:
        manager = OutputManager()
        assert manager.base_dir == os.path.abspath("target")

    def test_custom_base_dir(self, tmp_path) -> None:
        custom = str(tmp_path / "custom_output")
        manager = OutputManager(base_dir=custom)
        assert manager.base_dir == os.path.abspath(custom)


class TestOutputManagerPathConstruction:
    """Tests for contract directory path construction."""

    def test_path_follows_hierarchical_pattern(self, tmp_path) -> None:
        manager = OutputManager(base_dir=str(tmp_path))
        result = manager.get_contract_dir("OrgA", "UnitB", "12345")
        expected = os.path.join(str(tmp_path), "OrgA", "UnitB", "12345")
        assert result == expected

    def test_path_sanitizes_orgao(self, tmp_path) -> None:
        manager = OutputManager(base_dir=str(tmp_path))
        result = manager.get_contract_dir("Org<A>", "UnitB", "12345")
        expected = os.path.join(str(tmp_path), "Org_A_", "UnitB", "12345")
        assert result == expected

    def test_path_sanitizes_unidade_gestora(self, tmp_path) -> None:
        manager = OutputManager(base_dir=str(tmp_path))
        result = manager.get_contract_dir("OrgA", "Unit:B|C", "12345")
        expected = os.path.join(str(tmp_path), "OrgA", "Unit_B_C", "12345")
        assert result == expected

    def test_contract_id_not_sanitized(self, tmp_path) -> None:
        manager = OutputManager(base_dir=str(tmp_path))
        result = manager.get_contract_dir("OrgA", "UnitB", "500112")
        assert result.endswith("500112")


class TestOutputManagerDirectoryCreation:
    """Tests for directory creation behavior."""

    def test_creates_directory_on_get_contract_dir(self, tmp_path) -> None:
        manager = OutputManager(base_dir=str(tmp_path))
        result = manager.get_contract_dir("OrgA", "UnitB", "12345")
        assert os.path.isdir(result)

    def test_creates_nested_directories(self, tmp_path) -> None:
        manager = OutputManager(base_dir=str(tmp_path))
        manager.get_contract_dir("OrgA", "UnitB", "12345")
        assert os.path.isdir(os.path.join(str(tmp_path), "OrgA"))
        assert os.path.isdir(os.path.join(str(tmp_path), "OrgA", "UnitB"))
        assert os.path.isdir(os.path.join(str(tmp_path), "OrgA", "UnitB", "12345"))

    def test_does_not_fail_if_directory_already_exists(self, tmp_path) -> None:
        manager = OutputManager(base_dir=str(tmp_path))
        manager.get_contract_dir("OrgA", "UnitB", "12345")
        # Calling again should not raise
        result = manager.get_contract_dir("OrgA", "UnitB", "12345")
        assert os.path.isdir(result)


class TestOutputManagerSanitization:
    """Tests for the sanitize_folder_name static method."""

    def test_replaces_less_than(self) -> None:
        assert OutputManager.sanitize_folder_name("a<b") == "a_b"

    def test_replaces_greater_than(self) -> None:
        assert OutputManager.sanitize_folder_name("a>b") == "a_b"

    def test_replaces_colon(self) -> None:
        assert OutputManager.sanitize_folder_name("a:b") == "a_b"

    def test_replaces_double_quote(self) -> None:
        assert OutputManager.sanitize_folder_name('a"b') == "a_b"

    def test_replaces_forward_slash(self) -> None:
        assert OutputManager.sanitize_folder_name("a/b") == "a_b"

    def test_replaces_backslash(self) -> None:
        assert OutputManager.sanitize_folder_name("a\\b") == "a_b"

    def test_replaces_pipe(self) -> None:
        assert OutputManager.sanitize_folder_name("a|b") == "a_b"

    def test_replaces_question_mark(self) -> None:
        assert OutputManager.sanitize_folder_name("a?b") == "a_b"

    def test_replaces_asterisk(self) -> None:
        assert OutputManager.sanitize_folder_name("a*b") == "a_b"

    def test_no_change_for_valid_name(self) -> None:
        assert OutputManager.sanitize_folder_name("valid_name") == "valid_name"

    def test_multiple_invalid_chars(self) -> None:
        assert OutputManager.sanitize_folder_name("a<b>c:d") == "a_b_c_d"

    def test_empty_string(self) -> None:
        assert OutputManager.sanitize_folder_name("") == ""


class TestOutputManagerProcessedDetection:
    """Tests for contract_already_processed method."""

    def test_returns_false_when_no_metadata(self, tmp_path) -> None:
        manager = OutputManager(base_dir=str(tmp_path))
        assert manager.contract_already_processed("OrgA", "UnitB", "12345") is False

    def test_returns_true_when_metadata_exists(self, tmp_path) -> None:
        manager = OutputManager(base_dir=str(tmp_path))
        contract_dir = manager.get_contract_dir("OrgA", "UnitB", "12345")
        metadata_path = os.path.join(contract_dir, "metadata.json")
        with open(metadata_path, "w") as f:
            json.dump({"contract_id": "12345"}, f)
        assert manager.contract_already_processed("OrgA", "UnitB", "12345") is True

    def test_returns_false_when_directory_exists_but_no_metadata(self, tmp_path) -> None:
        manager = OutputManager(base_dir=str(tmp_path))
        manager.get_contract_dir("OrgA", "UnitB", "12345")
        assert manager.contract_already_processed("OrgA", "UnitB", "12345") is False

    def test_processed_detection_uses_sanitized_names(self, tmp_path) -> None:
        manager = OutputManager(base_dir=str(tmp_path))
        contract_dir = manager.get_contract_dir("Org:A", "Unit|B", "12345")
        metadata_path = os.path.join(contract_dir, "metadata.json")
        with open(metadata_path, "w") as f:
            json.dump({"contract_id": "12345"}, f)
        assert manager.contract_already_processed("Org:A", "Unit|B", "12345") is True
