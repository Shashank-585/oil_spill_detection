"""
Configuration management system for the SIH26143 pipeline.

Loads, merges, and validates YAML configuration files using typed models.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Union
from src.common.paths import DEFAULT_CONFIG_PATH, resolve_path
from src.common.logging import get_logger

logger = get_logger("src.common.config")


def load_yaml_file(file_path: Union[str, Path]) -> Dict[str, Any]:
    """Load and parse any YAML configuration file."""
    path = resolve_path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Configuration at {path} must parse into a dictionary")
    return data


def deep_merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge two dictionaries without mutating inputs."""
    merged = base.copy()
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = deep_merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_default_config(override_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """
    Load default pipeline configuration from configs/default.yaml,
    optionally merged with an override file.
    """
    config = load_yaml_file(DEFAULT_CONFIG_PATH)
    if override_path:
        override_data = load_yaml_file(override_path)
        config = deep_merge_dicts(config, override_data)
        logger.debug(f"Loaded config with overrides from {override_path}")
    return config


# Canonical alias for convenience
load_config = load_default_config
