"""Tests for centralized path resolution and directory validation."""
import pytest
from pathlib import Path
from src.common.paths import (
    PROJECT_ROOT,
    DATA_DIR,
    RAW_DATA_DIR,
    PROCESSED_DATA_DIR,
    CASES_DIR,
    CONFIGS_DIR,
    resolve_path,
    get_case_path,
)


def test_project_root_exists():
    assert PROJECT_ROOT.exists()
    assert PROJECT_ROOT.is_dir()
    assert (PROJECT_ROOT / "src").exists()


def test_required_directories_exist():
    required_dirs = [DATA_DIR, RAW_DATA_DIR, PROCESSED_DATA_DIR, CASES_DIR, CONFIGS_DIR]
    for d in required_dirs:
        assert d.exists(), f"Required directory {d} is missing"
        assert d.is_dir()


def test_path_resolution():
    rel = "data/cases/case_001.yaml"
    resolved = resolve_path(rel)
    assert resolved.is_absolute()
    assert resolved == PROJECT_ROOT / "data" / "cases" / "case_001.yaml"
    assert resolved.exists()


def test_get_case_path():
    p1 = get_case_path("case_001")
    p2 = get_case_path("case_001.yaml")
    assert p1 == p2
    assert p1.exists()
