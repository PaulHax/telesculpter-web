"""
Metadata Serializer module for Burn Out application.

This module provides simple functions to serialize metadata to JSON strings
and deserialize from JSON strings using KWIVER's metadata functionality.
"""

from typing import Dict, List, Optional
import tempfile
import os

from kwiver.vital.algo import MetadataMapIO
from kwiver.vital.config import empty_config
from kwiver.vital.types import SimpleMetadataMap
from kwiver.vital import vital_logging

logger = vital_logging.getLogger(__name__)


def serialize(frame_metadata: Dict[int, List]) -> str:
    config = empty_config()
    config["metadata_writer:type"] = "json"

    smm = SimpleMetadataMap(frame_metadata)

    metadata_serializer = MetadataMapIO.set_nested_algo_configuration(
        "metadata_writer", config
    )
    if metadata_serializer is None:
        logger.error("Failed to create metadata serializer")
        raise RuntimeError("Failed to create metadata serializer")

    with tempfile.NamedTemporaryFile(
        mode="w+", suffix=".json", delete=False
    ) as temp_file:
        temp_filename = temp_file.name

    try:
        metadata_serializer.save(temp_filename, smm)
        with open(temp_filename, "r") as f:
            metadata_json = f.read()
    finally:
        if os.path.exists(temp_filename):
            os.unlink(temp_filename)

    return metadata_json


def deserialize(json_str: str) -> Optional[Dict[int, List]]:
    """
    Deserialize metadata from a JSON string.

    Args:
        json_str: JSON string containing serialized metadata.

    Returns:
        Dictionary mapping frame numbers to metadata lists, or None if deserialization failed.
    """
    config = empty_config()
    config["metadata_reader:type"] = "json"

    metadata_deserializer = MetadataMapIO.set_nested_algo_configuration(
        "metadata_reader", config
    )
    if metadata_deserializer is None:
        logger.error("Failed to create metadata deserializer")
        return None

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as temp_file:
        temp_file.write(json_str)
        temp_filename = temp_file.name

    try:
        metadata_map = metadata_deserializer.load(temp_filename)
    finally:
        if os.path.exists(temp_filename):
            os.unlink(temp_filename)

    return metadata_map
