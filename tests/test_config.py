"""Tests for configuration management and YAML parsing."""
import pytest
from src.common.config import load_default_config, deep_merge_dicts
from src.common.paths import DEFAULT_CONFIG_PATH


def test_load_default_config():
    assert DEFAULT_CONFIG_PATH.exists()
    cfg = load_default_config()
    assert isinstance(cfg, dict)
    assert "project" in cfg
    assert "active_case_id" in cfg
    assert cfg["active_case_id"] == "case_001"
    assert "satellite_processing" in cfg
    assert "lagrangian_drift" in cfg
    assert "ais_candidate_generation" in cfg
    assert "attribution_scoring" in cfg


def test_deep_merge_dicts():
    base = {"a": 1, "b": {"x": 10, "y": 20}}
    override = {"b": {"y": 99, "z": 30}, "c": 3}
    merged = deep_merge_dicts(base, override)
    assert merged["a"] == 1
    assert merged["b"]["x"] == 10
    assert merged["b"]["y"] == 99
    assert merged["b"]["z"] == 30
    assert merged["c"] == 3
