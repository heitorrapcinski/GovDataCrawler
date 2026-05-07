"""Artifact discovery module for the OpenClaws AI Assistant.

Recursively scans the target folder for contract artifact directories
containing metadata.json files, parses them into IndexedArtifact instances,
and extracts text from PDF attachments.
"""

import json
import logging
import os
import sys

from openclaws.models import IndexedArtifact
from openclaws.pdf_extractor import extract_text

logger = logging.getLogger(__name__)


def discover_artifacts(target_folder: str) -> list[IndexedArtifact]:
    """Discover and index all contract artifacts in the target folder.

    Recursively scans the target folder for directories containing a
    metadata.json file. For each valid artifact, parses the metadata and
    extracts text from any PDF attachments found in the folder.

    Args:
        target_folder: Path to the root target folder to scan.

    Returns:
        A list of IndexedArtifact instances for all successfully parsed
        artifacts.

    Exits:
        Exits with non-zero status if the target folder does not exist
        or is not accessible.
    """
    if not os.path.exists(target_folder):
        logger.error(
            "Target folder does not exist: '%s'", target_folder
        )
        sys.exit(1)

    if not os.path.isdir(target_folder):
        logger.error(
            "Target folder path is not a directory: '%s'", target_folder
        )
        sys.exit(1)

    if not os.access(target_folder, os.R_OK):
        logger.error(
            "Target folder is not accessible: '%s'", target_folder
        )
        sys.exit(1)

    artifacts: list[IndexedArtifact] = []
    total_pdfs_processed = 0

    for dirpath, _dirnames, filenames in os.walk(target_folder):
        if "metadata.json" not in filenames:
            continue

        metadata_path = os.path.join(dirpath, "metadata.json")

        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(
                "Invalid JSON in metadata file '%s': %s",
                metadata_path,
                e,
            )
            continue
        except OSError as e:
            logger.error(
                "Cannot read metadata file '%s': %s",
                metadata_path,
                e,
            )
            continue

        # Extract PDF text for attachments found in the artifact folder
        pdf_texts: dict[str, str] = {}
        attachments = metadata.get("attachments", [])

        for attachment in attachments:
            if not attachment.lower().endswith(".pdf"):
                continue

            pdf_path = os.path.join(dirpath, attachment)
            if not os.path.isfile(pdf_path):
                logger.warning(
                    "PDF attachment not found: '%s'", pdf_path
                )
                continue

            extracted = extract_text(pdf_path)
            if extracted is not None:
                pdf_texts[attachment] = extracted
                total_pdfs_processed += 1

        artifact = IndexedArtifact(
            contract_id=metadata.get("contract_id", ""),
            orgao=metadata.get("orgao", ""),
            unidade_gestora=metadata.get("unidade_gestora", ""),
            contract_number=metadata.get("contract_number", ""),
            supplier_name=metadata.get("supplier_name", ""),
            contract_value=metadata.get("contract_value", ""),
            start_date=metadata.get("start_date", ""),
            end_date=metadata.get("end_date", ""),
            object_description=metadata.get("object_description", ""),
            extra_fields=metadata.get("extra_fields", {}),
            attachments=attachments,
            scraped_at=metadata.get("scraped_at", ""),
            folder_path=dirpath,
            pdf_texts=pdf_texts,
        )
        artifacts.append(artifact)

    if len(artifacts) == 0:
        logger.warning(
            "Target folder contains zero artifacts: '%s'", target_folder
        )

    logger.info(
        "Discovery complete: %d artifacts discovered, %d PDFs processed",
        len(artifacts),
        total_pdfs_processed,
    )

    return artifacts
