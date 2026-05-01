"""Manages the output directory structure for scraped contract data."""

import os
import re


# Characters invalid in Windows, Linux, or macOS file paths
_INVALID_CHARS_PATTERN = re.compile(r'[<>:"/\\|?*]')


class OutputManager:
    """Manages the output directory structure.

    Organizes scraped data into a hierarchical folder structure:
    ``{base_dir}/{orgao}/{unidade_gestora}/{contract_id}/``

    Folder names are sanitized to replace filesystem-invalid characters
    with underscores.
    """

    def __init__(self, base_dir: str = "target") -> None:
        """Initialize with a base output directory.

        Args:
            base_dir: Root directory for all output (default: ``target``).
        """
        self._base_dir = os.path.abspath(base_dir)

    @property
    def base_dir(self) -> str:
        """Return the absolute path of the base output directory."""
        return self._base_dir

    def get_contract_dir(
        self, orgao: str, unidade_gestora: str, contract_id: str
    ) -> str:
        """Build and create the directory path for a contract.

        The path follows the pattern:
        ``{base_dir}/{sanitized_orgao}/{sanitized_unidade_gestora}/{contract_id}/``

        Args:
            orgao: Organization name (will be sanitized).
            unidade_gestora: Management unit name (will be sanitized).
            contract_id: Contract ID.

        Returns:
            Absolute path to the contract's output directory.
        """
        sanitized_orgao = self.sanitize_folder_name(orgao)
        sanitized_ug = self.sanitize_folder_name(unidade_gestora)

        contract_dir = os.path.join(
            self._base_dir, sanitized_orgao, sanitized_ug, contract_id
        )
        os.makedirs(contract_dir, exist_ok=True)
        return contract_dir

    @staticmethod
    def sanitize_folder_name(name: str) -> str:
        """Replace filesystem-invalid characters with underscores.

        Characters replaced: ``<``, ``>``, ``:``, ``"``, ``/``, ``\\``,
        ``|``, ``?``, ``*``.  Trailing spaces and periods are also
        stripped because Windows silently removes them from directory
        names, which can cause path mismatches.

        Args:
            name: Raw folder name.

        Returns:
            Sanitized folder name safe for all major filesystems.
        """
        sanitized = _INVALID_CHARS_PATTERN.sub("_", name)
        # Windows silently strips trailing spaces and periods from
        # directory names, so we strip them explicitly for consistency.
        return sanitized.rstrip(". ")

    def contract_already_processed(
        self, orgao: str, unidade_gestora: str, contract_id: str
    ) -> bool:
        """Check if a contract metadata file already exists.

        A contract is considered processed when a ``metadata.json`` file
        exists in its expected output directory.

        Args:
            orgao: Organization name.
            unidade_gestora: Management unit name.
            contract_id: Contract ID.

        Returns:
            True if ``metadata.json`` exists in the expected directory.
        """
        sanitized_orgao = self.sanitize_folder_name(orgao)
        sanitized_ug = self.sanitize_folder_name(unidade_gestora)

        metadata_path = os.path.join(
            self._base_dir,
            sanitized_orgao,
            sanitized_ug,
            contract_id,
            "metadata.json",
        )
        return os.path.isfile(metadata_path)
