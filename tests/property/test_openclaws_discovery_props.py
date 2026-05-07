"""Property-based tests for OpenClaws artifact discovery.

Feature: openclaws-ai-assistant
Property 3: Artifact discovery identifies exactly folders containing metadata.json

Validates: Requirements 3.1
"""

import json
import os
import tempfile
from unittest.mock import patch

from hypothesis import given, settings
from hypothesis import strategies as st

from openclaws.discovery import discover_artifacts


# =============================================================================
# Property 3: Artifact discovery identifies exactly folders containing metadata.json
# =============================================================================

# Strategy for valid folder names (safe for filesystem)
_safe_folder_name = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N"),
    ),
    min_size=1,
    max_size=12,
).map(lambda s: s[:12])

# Strategy for generating a minimal valid metadata.json content
_valid_metadata = st.fixed_dictionaries(
    {
        "contract_id": st.text(
            alphabet=st.characters(whitelist_categories=("L", "N")),
            min_size=1,
            max_size=20,
        ),
        "orgao": st.text(
            alphabet=st.characters(whitelist_categories=("L", "N")),
            min_size=1,
            max_size=20,
        ),
        "unidade_gestora": st.text(
            alphabet=st.characters(whitelist_categories=("L", "N")),
            min_size=1,
            max_size=20,
        ),
        "contract_number": st.text(
            alphabet=st.characters(whitelist_categories=("L", "N")),
            min_size=1,
            max_size=20,
        ),
        "supplier_name": st.text(
            alphabet=st.characters(whitelist_categories=("L", "N")),
            min_size=1,
            max_size=20,
        ),
        "contract_value": st.text(
            alphabet=st.characters(whitelist_categories=("N",)),
            min_size=1,
            max_size=10,
        ),
        "start_date": st.text(
            alphabet=st.characters(whitelist_categories=("N", "P")),
            min_size=1,
            max_size=10,
        ),
        "end_date": st.text(
            alphabet=st.characters(whitelist_categories=("N", "P")),
            min_size=1,
            max_size=10,
        ),
        "object_description": st.text(
            alphabet=st.characters(whitelist_categories=("L", "N")),
            min_size=1,
            max_size=30,
        ),
        "extra_fields": st.just({}),
        "attachments": st.just([]),
        "scraped_at": st.text(
            alphabet=st.characters(whitelist_categories=("N", "P")),
            min_size=1,
            max_size=20,
        ),
    }
)


# Strategy for a directory tree structure:
# A list of (relative_path_parts, has_metadata) tuples
# Each tuple represents a folder in the tree
@st.composite
def directory_tree(draw: st.DrawFn):
    """Generate a directory tree specification.

    Returns a list of tuples: (list_of_path_parts, has_metadata, metadata_content)
    where has_metadata indicates whether the folder should contain metadata.json.
    """
    # Generate between 1 and 8 folders
    num_folders = draw(st.integers(min_value=1, max_value=8))

    folders = []
    used_paths: set[tuple[str, ...]] = set()

    for _ in range(num_folders):
        # Each folder has 1-3 levels of nesting
        depth = draw(st.integers(min_value=1, max_value=3))
        parts = []
        for _ in range(depth):
            part = draw(_safe_folder_name)
            # Ensure non-empty after stripping
            if not part.strip():
                part = "dir"
            parts.append(part)

        path_key = tuple(parts)
        # Skip duplicates
        if path_key in used_paths:
            continue
        used_paths.add(path_key)

        has_metadata = draw(st.booleans())
        metadata_content = draw(_valid_metadata) if has_metadata else None
        folders.append((parts, has_metadata, metadata_content))

    return folders


@settings(max_examples=100, deadline=5000)
@given(tree=directory_tree())
def test_discovery_returns_exactly_folders_with_metadata_json(
    tree: list[tuple[list[str], bool, dict | None]],
) -> None:
    """Property 3: For any directory tree under the target folder, the discovery
    module SHALL return exactly the set of folders that contain a file named
    `metadata.json`, and no others.

    Feature: openclaws-ai-assistant, Property 3: Artifact discovery identifies exactly folders containing metadata.json

    **Validates: Requirements 3.1**
    """
    with tempfile.TemporaryDirectory() as target_folder:
        expected_folders: set[str] = set()

        for parts, has_metadata, metadata_content in tree:
            folder_path = os.path.join(target_folder, *parts)
            os.makedirs(folder_path, exist_ok=True)

            if has_metadata and metadata_content is not None:
                metadata_path = os.path.join(folder_path, "metadata.json")
                with open(metadata_path, "w", encoding="utf-8") as f:
                    json.dump(metadata_content, f)
                # Use the normalized absolute path for comparison
                expected_folders.add(os.path.normpath(folder_path))

        # Mock pdf extraction to avoid needing real PDFs
        with patch(
            "openclaws.discovery.extract_text", return_value=None
        ):
            artifacts = discover_artifacts(target_folder)

        # Extract the set of folder_paths from the discovered artifacts
        discovered_folders = {
            os.path.normpath(a.folder_path) for a in artifacts
        }

        # The discovered set must match exactly the expected set
        assert discovered_folders == expected_folders, (
            f"Discovery mismatch.\n"
            f"Expected folders with metadata.json: {expected_folders}\n"
            f"Discovered folders: {discovered_folders}\n"
            f"Missing (expected but not found): {expected_folders - discovered_folders}\n"
            f"Extra (found but not expected): {discovered_folders - expected_folders}"
        )
