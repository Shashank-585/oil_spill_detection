"""
Centralized project path management.

Ensures no scientific module hard-codes relative or absolute filesystem paths.
Provides resolution relative to the canonical project repository root.
"""

from pathlib import Path
from typing import Union

# Canonical Project Root: directory containing this file is src/common, parent.parent is project root
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent


def get_project_root() -> Path:
    """Return the canonical project root directory."""
    return PROJECT_ROOT

# Core Directories
DATA_DIR: Path = PROJECT_ROOT / "data"
RAW_DATA_DIR: Path = DATA_DIR / "raw"
PROCESSED_DATA_DIR: Path = DATA_DIR / "processed"
CASES_DIR: Path = DATA_DIR / "cases"

# Raw Category Subdirectories
SATELLITE_RAW_DIR: Path = RAW_DATA_DIR / "satellite"
ENVIRONMENTAL_RAW_DIR: Path = RAW_DATA_DIR / "environmental"
AIS_RAW_DIR: Path = RAW_DATA_DIR / "ais"

# Processed Category Subdirectories
SATELLITE_PROCESSED_DIR: Path = PROCESSED_DATA_DIR / "satellite"
ENVIRONMENTAL_PROCESSED_DIR: Path = PROCESSED_DATA_DIR / "environmental"
AIS_PROCESSED_DIR: Path = PROCESSED_DATA_DIR / "ais"
DRIFT_PROCESSED_DIR: Path = PROCESSED_DATA_DIR / "drift"
HYPOTHESES_PROCESSED_DIR: Path = PROCESSED_DATA_DIR / "hypotheses"
ATTRIBUTION_PROCESSED_DIR: Path = PROCESSED_DATA_DIR / "attribution"
VALIDATION_PROCESSED_DIR: Path = PROCESSED_DATA_DIR / "validation"


# Configuration & Aux Directories
CONFIGS_DIR: Path = PROJECT_ROOT / "configs"
NOTEBOOKS_DIR: Path = PROJECT_ROOT / "notebooks"
TESTS_DIR: Path = PROJECT_ROOT / "tests"
DEFAULT_CONFIG_PATH: Path = CONFIGS_DIR / "default.yaml"


def resolve_path(path_str_or_path: Union[str, Path]) -> Path:
    """
    Resolve any given path string to an absolute canonical Path.
    If the path is relative, it is resolved relative to PROJECT_ROOT.
    """
    p = Path(path_str_or_path)
    if p.is_absolute():
        return p.resolve()
    return (PROJECT_ROOT / p).resolve()


def get_case_path(case_id: str) -> Path:
    """Return the absolute path to a case configuration YAML."""
    if not case_id.endswith(".yaml") and not case_id.endswith(".yml"):
        case_id = f"{case_id}.yaml"
    return CASES_DIR / case_id


def ensure_dir_exists(dir_path: Union[str, Path]) -> Path:
    """Ensure a directory exists on disk, creating parents if needed."""
    resolved = resolve_path(dir_path)
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved
