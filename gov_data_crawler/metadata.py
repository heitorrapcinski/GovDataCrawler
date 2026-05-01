"""Serializes and writes contract metadata to JSON."""

import json
import os
from dataclasses import asdict

from gov_data_crawler.contract import ContractMetadata


class MetadataWriter:
    """Serializes and writes contract metadata to JSON."""

    def write(self, metadata: ContractMetadata, target_dir: str) -> str:
        """Write contract metadata as JSON to the target directory.

        Uses ``ensure_ascii=False`` to preserve non-ASCII characters
        (e.g., Portuguese accents) and ``indent=2`` for readability.

        Args:
            metadata: The contract metadata to serialize.
            target_dir: Directory to write the ``metadata.json`` file.

        Returns:
            Absolute path to the written file.
        """
        os.makedirs(target_dir, exist_ok=True)
        file_path = os.path.join(target_dir, "metadata.json")

        data = asdict(metadata)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return os.path.abspath(file_path)
