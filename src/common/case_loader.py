"""
Case configuration loader and validator for the SIH26143 pipeline.

Loads case definitions (e.g. data/cases/case_001.yaml) and validates:
1. Spatial bounds and coordinate correctness.
2. Temporal coverage and strict UTC timestamps.
3. Path resolution for raw satellite, environmental, and AIS files.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from src.common.paths import resolve_path, get_case_path, PROJECT_ROOT
from src.common.config import load_yaml_file
from src.common.time_utils import parse_utc_timestamp
from src.common.geo import validate_bounding_box, geodesic_bounding_box_area_km2
from src.common.logging import get_logger

logger = get_logger("src.common.case_loader")


class CaseConfig:
    """Wrapper providing structured access to a validated case configuration."""

    def __init__(self, raw_data: Dict[str, Any], source_path: Path):
        self.source_path = source_path
        self.raw_data = raw_data

        self.case_id: str = raw_data.get("case_id", "unknown")
        self.name: str = raw_data.get("name", "")
        self.incident_type: str = raw_data.get("incident_type", "")
        self.location_name: str = raw_data.get("location_name", "")

        # Spatial
        spatial = raw_data.get("spatial", {})
        self.crs: str = spatial.get("crs", "EPSG:4326")
        self.aoi: Dict[str, float] = spatial.get("aoi_bounding_box", {})
        self.incident_point: Dict[str, Any] = spatial.get("incident_point", {})

        # Temporal
        temporal = raw_data.get("temporal", {})
        self.search_start_utc: datetime = parse_utc_timestamp(
            temporal.get("source_search_time_range", {}).get("start_utc")
        )
        self.search_end_utc: datetime = parse_utc_timestamp(
            temporal.get("source_search_time_range", {}).get("end_utc")
        )

        # Satellite
        sat = raw_data.get("satellite", {})
        self.satellite_platform: str = sat.get("platform", "")
        self.satellite_scene_id: str = sat.get("scene_id", "")
        self.satellite_timestamp_utc: datetime = parse_utc_timestamp(
            sat.get("observation_timestamp_utc")
        )
        self.satellite_polarizations: List[str] = sat.get("polarizations", [])
        self.satellite_files: Dict[str, Path] = {
            k: resolve_path(v) for k, v in sat.get("files", {}).items() if not str(v).startswith("http")
        }

        # Environmental
        env = raw_data.get("environmental", {})
        self.ocean_current_file: Optional[Path] = (
            resolve_path(env.get("ocean_currents", {}).get("file_path"))
            if env.get("ocean_currents", {}).get("file_path") else None
        )
        self.wind_files: Dict[str, Path] = {
            k: resolve_path(v) for k, v in env.get("wind", {}).get("files", {}).items()
        }

        # AIS
        ais = raw_data.get("ais", {})
        self.ais_files: Dict[str, Path] = {
            k: resolve_path(v) for k, v in ais.get("files", {}).items()
        }

    def __getitem__(self, key: str) -> Any:
        return self.raw_data[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.raw_data.get(key, default)

    @property
    def aoi_area_km2(self) -> float:
        """Geodesic area of the case AOI in km^2."""
        return geodesic_bounding_box_area_km2(self.aoi)

    def validate_integrity(self) -> List[str]:
        """Validate that all referenced local measurement and input files exist."""
        errors = []
        if not validate_bounding_box(self.aoi):
            errors.append(f"Invalid AOI bounding box coordinates: {self.aoi}")

        # Check satellite measurement file
        vv_raster = self.satellite_files.get("measurement_raster_vv")
        if not vv_raster or not vv_raster.exists():
            errors.append(f"Missing Sentinel-1 VV measurement raster: {vv_raster}")

        # Check ocean currents
        if not self.ocean_current_file or not self.ocean_current_file.exists():
            errors.append(f"Missing ocean currents file: {self.ocean_current_file}")

        # Check wind
        wind_csv = self.wind_files.get("csv_path")
        if not wind_csv or not wind_csv.exists():
            errors.append(f"Missing wind CSV file: {wind_csv}")

        # Check AIS
        ais_csv = self.ais_files.get("filtered_csv")
        if not ais_csv or not ais_csv.exists():
            errors.append(f"Missing filtered AIS CSV file: {ais_csv}")

        return errors


def load_case(case_identifier: Union[str, Path]) -> CaseConfig:
    """
    Load a case by case_id (e.g. 'case_001') or path to YAML file.
    """
    if isinstance(case_identifier, Path) or ("/" in str(case_identifier) or "\\" in str(case_identifier)):
        path = resolve_path(case_identifier)
    else:
        path = get_case_path(str(case_identifier))

    data = load_yaml_file(path)
    case_obj = CaseConfig(data, path)
    logger.info(f"Loaded case '{case_obj.case_id}' from {path}")
    return case_obj


# Canonical alias for convenience
load_case_config = load_case
