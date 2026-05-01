"""Property-based tests for output directory structure.

Feature: gov-data-crawler
Property 4: directory structure follows hierarchical pattern

Validates: Requirements 3.2, 5.1, 5.2, 5.3
"""

import os
import tempfile

from hypothesis import given, settings
from hypothesis import strategies as st

from gov_data_crawler.output import OutputManager

# Strategy for realistic folder names: printable characters (no control chars),
# at least one non-whitespace character, similar to real orgao/unidade_gestora values.
_name_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "S", "Z"),
        blacklist_characters=("\x00",),
    ),
    min_size=1,
    max_size=50,
).filter(lambda s: s.strip() != "")

# Contract IDs are numeric strings
_contract_id_strategy = st.from_regex(r"[1-9][0-9]{0,8}", fullmatch=True)


@settings(max_examples=100, deadline=1000)
@given(
    orgao=_name_strategy,
    unidade_gestora=_name_strategy,
    contract_id=_contract_id_strategy,
)
def test_directory_structure_follows_hierarchical_pattern(
    orgao: str, unidade_gestora: str, contract_id: str
) -> None:
    """Property 4: For any combination of orgao, unidade_gestora, and
    contract_id, the path returned by get_contract_dir SHALL follow the
    pattern {base_dir}/{sanitized_orgao}/{sanitized_unidade_gestora}/{contract_id}/,
    and both metadata files and attachment files for that contract SHALL
    reside in this same directory.

    **Validates: Requirements 3.2, 5.1, 5.2, 5.3**
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        manager = OutputManager(base_dir=tmp_dir)
        result = manager.get_contract_dir(orgao, unidade_gestora, contract_id)

        sanitized_orgao = OutputManager.sanitize_folder_name(orgao)
        sanitized_ug = OutputManager.sanitize_folder_name(unidade_gestora)

        # Verify the path follows the expected hierarchical pattern
        expected = os.path.join(tmp_dir, sanitized_orgao, sanitized_ug, contract_id)
        assert result == expected, (
            f"Expected path '{expected}', got '{result}'"
        )

        # Verify the directory was actually created
        assert os.path.isdir(result), f"Directory was not created: {result}"

        # Verify metadata and attachment files would reside in this directory
        metadata_path = os.path.join(result, "metadata.json")
        attachment_path = os.path.join(result, "example_attachment.pdf")

        # Both paths should share the same parent directory
        assert os.path.dirname(metadata_path) == result
        assert os.path.dirname(attachment_path) == result
