"""Unit tests for the ResumeDetector component."""

import json
import logging
import os

from gov_data_crawler.output import OutputManager
from gov_data_crawler.resume import ResumeDetector


class TestResumeDetectorWithExistingFiles:
    """Tests for detection when metadata files exist on disk."""

    def test_detects_single_processed_contract(self, tmp_path) -> None:
        manager = OutputManager(base_dir=str(tmp_path))
        logger = logging.getLogger("test.resume")
        detector = ResumeDetector(output_manager=manager, logger=logger)

        # Create a metadata.json for contract "100"
        contract_dir = manager.get_contract_dir("OrgA", "UnitB", "100")
        with open(os.path.join(contract_dir, "metadata.json"), "w") as f:
            json.dump({"contract_id": "100"}, f)

        contract_ids = ["100", "200"]
        metadata = {"100": ("OrgA", "UnitB"), "200": ("OrgA", "UnitB")}

        result = detector.find_processed_ids(contract_ids, metadata)

        assert result == {"100"}

    def test_detects_multiple_processed_contracts(self, tmp_path) -> None:
        manager = OutputManager(base_dir=str(tmp_path))
        logger = logging.getLogger("test.resume")
        detector = ResumeDetector(output_manager=manager, logger=logger)

        # Create metadata.json for contracts "100" and "300"
        for cid in ["100", "300"]:
            contract_dir = manager.get_contract_dir("OrgA", "UnitB", cid)
            with open(os.path.join(contract_dir, "metadata.json"), "w") as f:
                json.dump({"contract_id": cid}, f)

        contract_ids = ["100", "200", "300"]
        metadata = {
            "100": ("OrgA", "UnitB"),
            "200": ("OrgA", "UnitB"),
            "300": ("OrgA", "UnitB"),
        }

        result = detector.find_processed_ids(contract_ids, metadata)

        assert result == {"100", "300"}

    def test_detects_contracts_across_different_orgs(self, tmp_path) -> None:
        manager = OutputManager(base_dir=str(tmp_path))
        logger = logging.getLogger("test.resume")
        detector = ResumeDetector(output_manager=manager, logger=logger)

        # Create metadata for contracts in different organizations
        dir1 = manager.get_contract_dir("OrgA", "Unit1", "100")
        with open(os.path.join(dir1, "metadata.json"), "w") as f:
            json.dump({"contract_id": "100"}, f)

        dir2 = manager.get_contract_dir("OrgB", "Unit2", "200")
        with open(os.path.join(dir2, "metadata.json"), "w") as f:
            json.dump({"contract_id": "200"}, f)

        contract_ids = ["100", "200", "300"]
        metadata = {
            "100": ("OrgA", "Unit1"),
            "200": ("OrgB", "Unit2"),
            "300": ("OrgC", "Unit3"),
        }

        result = detector.find_processed_ids(contract_ids, metadata)

        assert result == {"100", "200"}


class TestResumeDetectorEmptyDirectory:
    """Tests for detection with an empty output directory."""

    def test_returns_empty_set_when_no_files_exist(self, tmp_path) -> None:
        manager = OutputManager(base_dir=str(tmp_path))
        logger = logging.getLogger("test.resume")
        detector = ResumeDetector(output_manager=manager, logger=logger)

        contract_ids = ["100", "200", "300"]
        metadata = {
            "100": ("OrgA", "UnitB"),
            "200": ("OrgA", "UnitB"),
            "300": ("OrgA", "UnitB"),
        }

        result = detector.find_processed_ids(contract_ids, metadata)

        assert result == set()

    def test_returns_empty_set_for_empty_contract_list(self, tmp_path) -> None:
        manager = OutputManager(base_dir=str(tmp_path))
        logger = logging.getLogger("test.resume")
        detector = ResumeDetector(output_manager=manager, logger=logger)

        result = detector.find_processed_ids([], {})

        assert result == set()


class TestResumeDetectorPartialProcessing:
    """Tests for detection with partially processed contracts."""

    def test_directory_exists_but_no_metadata(self, tmp_path) -> None:
        manager = OutputManager(base_dir=str(tmp_path))
        logger = logging.getLogger("test.resume")
        detector = ResumeDetector(output_manager=manager, logger=logger)

        # Create directory but no metadata.json
        manager.get_contract_dir("OrgA", "UnitB", "100")

        contract_ids = ["100"]
        metadata = {"100": ("OrgA", "UnitB")}

        result = detector.find_processed_ids(contract_ids, metadata)

        assert result == set()

    def test_skips_contract_ids_not_in_metadata_map(self, tmp_path) -> None:
        manager = OutputManager(base_dir=str(tmp_path))
        logger = logging.getLogger("test.resume")
        detector = ResumeDetector(output_manager=manager, logger=logger)

        contract_ids = ["100", "200"]
        # Only "100" has metadata mapping
        metadata = {"100": ("OrgA", "UnitB")}

        result = detector.find_processed_ids(contract_ids, metadata)

        assert result == set()

    def test_mixed_processed_and_unprocessed(self, tmp_path) -> None:
        manager = OutputManager(base_dir=str(tmp_path))
        logger = logging.getLogger("test.resume")
        detector = ResumeDetector(output_manager=manager, logger=logger)

        # "100" is fully processed, "200" has dir but no metadata, "300" has nothing
        dir1 = manager.get_contract_dir("OrgA", "UnitB", "100")
        with open(os.path.join(dir1, "metadata.json"), "w") as f:
            json.dump({"contract_id": "100"}, f)

        manager.get_contract_dir("OrgA", "UnitB", "200")

        contract_ids = ["100", "200", "300"]
        metadata = {
            "100": ("OrgA", "UnitB"),
            "200": ("OrgA", "UnitB"),
            "300": ("OrgA", "UnitB"),
        }

        result = detector.find_processed_ids(contract_ids, metadata)

        assert result == {"100"}


class TestResumeDetectorLogging:
    """Tests for logging behavior during resumption."""

    def test_logs_skipped_count_when_contracts_found(
        self, tmp_path, caplog
    ) -> None:
        manager = OutputManager(base_dir=str(tmp_path))
        logger = logging.getLogger("test.resume.log")
        detector = ResumeDetector(output_manager=manager, logger=logger)

        # Create metadata for two contracts
        for cid in ["100", "200"]:
            contract_dir = manager.get_contract_dir("OrgA", "UnitB", cid)
            with open(os.path.join(contract_dir, "metadata.json"), "w") as f:
                json.dump({"contract_id": cid}, f)

        contract_ids = ["100", "200", "300"]
        metadata = {
            "100": ("OrgA", "UnitB"),
            "200": ("OrgA", "UnitB"),
            "300": ("OrgA", "UnitB"),
        }

        with caplog.at_level(logging.INFO, logger="test.resume.log"):
            detector.find_processed_ids(contract_ids, metadata)

        assert "skipping 2 already-processed contract(s)" in caplog.text.lower()

    def test_no_log_when_no_contracts_skipped(self, tmp_path, caplog) -> None:
        manager = OutputManager(base_dir=str(tmp_path))
        logger = logging.getLogger("test.resume.nolog")
        detector = ResumeDetector(output_manager=manager, logger=logger)

        contract_ids = ["100", "200"]
        metadata = {"100": ("OrgA", "UnitB"), "200": ("OrgA", "UnitB")}

        with caplog.at_level(logging.INFO, logger="test.resume.nolog"):
            detector.find_processed_ids(contract_ids, metadata)

        assert "skipping" not in caplog.text.lower()
