"""Property-based tests for the ResumeDetector component.

Feature: gov-data-crawler
Property 9: correctly identifies processed contracts

Validates: Requirements 7.1, 7.2
"""

import json
import logging
import os
import tempfile

from hypothesis import given, settings
from hypothesis import strategies as st

from gov_data_crawler.output import OutputManager
from gov_data_crawler.resume import ResumeDetector

# Strategy for contract IDs: short alphanumeric strings
contract_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N")),
    min_size=1,
    max_size=10,
)

# Strategy for org/unit names: alphanumeric strings with underscores/hyphens/spaces
# that are safe for filesystem use on all platforms (no trailing spaces, no
# whitespace-only names).
safe_name_strategy = st.from_regex(r"[A-Za-z0-9][A-Za-z0-9 _-]{0,14}", fullmatch=True)


@settings(max_examples=100, deadline=1000)
@given(
    contract_ids=st.lists(
        contract_id_strategy, min_size=1, max_size=10, unique=True
    ),
    orgao=safe_name_strategy,
    unidade_gestora=safe_name_strategy,
    processed_flags=st.lists(st.booleans(), min_size=1, max_size=10),
)
def test_resume_detector_identifies_processed_contracts(
    contract_ids: list[str],
    orgao: str,
    unidade_gestora: str,
    processed_flags: list[bool],
) -> None:
    """Property 9: For any set of contract IDs where a subset has
    corresponding metadata.json files on disk,
    ResumeDetector.find_processed_ids SHALL return exactly the subset of
    IDs that have metadata files, with no false positives and no false
    negatives.

    **Validates: Requirements 7.1, 7.2**
    """
    # Align flags to contract_ids length
    flags = processed_flags[: len(contract_ids)]
    while len(flags) < len(contract_ids):
        flags.append(False)

    with tempfile.TemporaryDirectory() as tmp_dir:
        manager = OutputManager(base_dir=tmp_dir)
        logger = logging.getLogger("test.property.resume")
        detector = ResumeDetector(output_manager=manager, logger=logger)

        # Build metadata mapping and create files for "processed" contracts
        contracts_metadata: dict[str, tuple[str, str]] = {}
        expected_processed: set[str] = set()

        for cid, is_processed in zip(contract_ids, flags):
            contracts_metadata[cid] = (orgao, unidade_gestora)

            if is_processed:
                contract_dir = manager.get_contract_dir(
                    orgao, unidade_gestora, cid
                )
                metadata_path = os.path.join(contract_dir, "metadata.json")
                with open(metadata_path, "w") as f:
                    json.dump({"contract_id": cid}, f)
                expected_processed.add(cid)

        result = detector.find_processed_ids(contract_ids, contracts_metadata)

        # Property: no false negatives — every processed ID is detected
        assert expected_processed <= result, (
            f"False negatives: {expected_processed - result}"
        )

        # Property: no false positives — no unprocessed ID is returned
        assert result <= expected_processed, (
            f"False positives: {result - expected_processed}"
        )

        # Combined: exact match
        assert result == expected_processed
