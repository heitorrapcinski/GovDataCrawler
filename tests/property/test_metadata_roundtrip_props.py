"""Property-based tests for contract metadata serialization round-trip.

Feature: gov-data-crawler
Property 3: serialization round-trip preserves all fields

Validates: Requirements 2.3
"""

import json
import os
import tempfile

from hypothesis import given, settings
from hypothesis import strategies as st

from gov_data_crawler.contract import ContractMetadata
from gov_data_crawler.metadata import MetadataWriter

# Strategy for non-empty text strings (printable, no null bytes)
_text_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "S", "Z"),
        blacklist_characters=("\x00",),
    ),
    min_size=1,
    max_size=80,
).filter(lambda s: s.strip() != "")

# Strategy for extra_fields: dict of string keys to string values
_extra_fields_strategy = st.dictionaries(
    keys=_text_strategy,
    values=_text_strategy,
    min_size=0,
    max_size=5,
)

# Strategy for attachments: list of filename-like strings
_attachments_strategy = st.lists(
    _text_strategy,
    min_size=0,
    max_size=5,
)

# Strategy for generating arbitrary ContractMetadata instances
_contract_metadata_strategy = st.builds(
    ContractMetadata,
    contract_id=_text_strategy,
    orgao=_text_strategy,
    unidade_gestora=_text_strategy,
    contract_number=_text_strategy,
    supplier_name=_text_strategy,
    contract_value=_text_strategy,
    start_date=_text_strategy,
    end_date=_text_strategy,
    object_description=_text_strategy,
    extra_fields=_extra_fields_strategy,
    attachments=_attachments_strategy,
    scraped_at=_text_strategy,
)


@settings(max_examples=100, deadline=1000)
@given(metadata=_contract_metadata_strategy)
def test_serialization_roundtrip_preserves_all_fields(
    metadata: ContractMetadata,
) -> None:
    """Property 3: For any valid ContractMetadata object, serializing it to
    JSON and then deserializing the JSON back SHALL produce an object equal
    to the original.

    **Validates: Requirements 2.3**
    """
    writer = MetadataWriter()

    with tempfile.TemporaryDirectory() as tmp_dir:
        file_path = writer.write(metadata, tmp_dir)

        # Read back the JSON
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        # Reconstruct the ContractMetadata from the deserialized dict
        restored = ContractMetadata(**data)

        # The restored object must be equal to the original
        assert restored == metadata, (
            f"Round-trip failed.\nOriginal: {metadata}\nRestored: {restored}"
        )
