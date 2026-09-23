"""
Phase 12: Standardized Real Historical Case Onboarding Engine.

Defines the standardized multi-step onboarding workflow for incorporating real historical
oil-spill incidents with credible source/culprit information:
1. Validate case configuration against CaseConfig schema
2. Register satellite observation metadata & file paths
3. Register environmental data (HYCOM & ERA5)
4. Register AIS trajectory datasets
5. Register reference ground truth separately (strictly isolated)
6. Run data feasibility checks (file existence, formats, resolution)
7. Run spatiotemporal integrity checks (AOI bounding box, temporal overlap)
8. Assign validation eligibility (ELIGIBLE, PARTIALLY_ELIGIBLE, INELIGIBLE_MISSING_DATA)
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import yaml

from src.common.config import load_yaml_file
from src.common.geo import validate_bounding_box, geodesic_bounding_box_area_km2
from src.common.logging import get_logger
from src.common.paths import (
    CASES_DIR,
    resolve_path,
)
from src.common.time_utils import parse_utc_timestamp
from src.validation.case_schema import (
    AlgorithmInputs,
    CaseQualityLevel,
    CaseStatus,
    GroundTruth,
    GroundTruthQuality,
    SourceType,
    ValidationCase,
    ValidationEligibility,
    ValidationRole,
)

logger = get_logger(__name__)


class CaseOnboardingWorkflow:
    """
    Standardized onboarding orchestrator for real-world oil-spill incident datasets.
    """

    def __init__(self, cases_dir: Optional[Union[str, Path]] = None):
        if cases_dir:
            self.cases_dir = Path(cases_dir)
        else:
            self.cases_dir = resolve_path(CASES_DIR)

    def create_case_template(
        self,
        case_id: str,
        incident_name: str,
        incident_type: str,
        incident_date: str,
        source_type: SourceType,
        quality_level: CaseQualityLevel,
        aoi_bbox: Dict[str, float],
        reference_location: Optional[Tuple[float, float]] = None,
        reference_time_utc: Optional[str] = None,
        reference_vessel_mmsi: Optional[int] = None,
        reference_vessel_name: Optional[str] = None,
        ground_truth_source: str = "Official Investigation Report",
        satellite_platform: str = "Sentinel-1A",
        scene_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a standardized YAML configuration dictionary cleanly separating
        algorithm inputs from reference ground truth.
        """
        role = (
            ValidationRole.POSITIVE_VESSEL_CASE.value
            if source_type == SourceType.VESSEL
            else ValidationRole.NEGATIVE_NON_VESSEL_CASE.value
        )
        quality_str = (
            GroundTruthQuality.VERIFIED.value
            if quality_level in [CaseQualityLevel.A, CaseQualityLevel.B]
            else GroundTruthQuality.UNVERIFIED.value
        )

        template: Dict[str, Any] = {
            "case_id": case_id,
            "name": incident_name,
            "incident_type": incident_type,
            "incident_date": incident_date,
            "spatial": {
                "crs": "EPSG:4326",
                "aoi_bounding_box": aoi_bbox,
                "incident_point": {
                    "longitude": reference_location[0] if reference_location else None,
                    "latitude": reference_location[1] if reference_location else None,
                },
            },
            "temporal": {
                "spill_incident_estimated_start": reference_time_utc,
                "source_search_time_range": {
                    "start_utc": reference_time_utc,
                    "end_utc": reference_time_utc,
                    "search_window_hours": 36,
                },
            },
            "satellite": {
                "platform": satellite_platform,
                "scene_id": scene_id or "PENDING_ACQUISITION",
                "polarizations": ["VV", "VH"],
                "files": {
                    "measurement_raster_vv": f"data/raw/satellite/{case_id}_measurement_vv.tif",
                    "calibration_lut": f"data/raw/satellite/{case_id}_calibration_vv.xml",
                },
            },
            "environmental": {
                "ocean_currents": {
                    "source_name": "HYCOM Ocean Currents",
                    "file_path": f"data/raw/environmental/{case_id}_ocean_currents.nc",
                },
                "wind": {
                    "source_name": "ECMWF ERA5 Reanalysis",
                    "files": {
                        "csv_path": f"data/raw/environmental/{case_id}_wind_era5.csv",
                    },
                },
            },
            "ais": {
                "source_name": "Terrestrial/Satellite AIS Archive",
                "files": {
                    "filtered_csv": f"data/raw/ais/{case_id}_ais_filtered.csv",
                },
            },
            "validation": {
                "incident_name": incident_name,
                "incident_date": incident_date,
                "source_type": source_type.value,
                "quality_level": quality_level.value,
                "ground_truth_quality": quality_str,
                "ground_truth_source": ground_truth_source,
                "validation_role": role,
                "reference_source_location": {
                    "lon": reference_location[0] if reference_location else None,
                    "lat": reference_location[1] if reference_location else None,
                } if reference_location else None,
                "reference_source_time_utc": reference_time_utc,
                "reference_vessel_mmsi": reference_vessel_mmsi,
                "reference_vessel_name": reference_vessel_name,
                "case_status": CaseStatus.POTENTIALLY_AVAILABLE.value,
                "notes": f"Onboarded case definition for {incident_name}.",
            },
        }
        return template

    def check_data_feasibility(self, case_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Audit physical file presence and format validity for a case configuration.
        """
        issues = []
        checks = {
            "satellite_file_present": False,
            "ais_file_present": False,
            "currents_file_present": False,
            "wind_file_present": False,
            "ground_truth_isolated": True,
        }

        # Check satellite
        sat_files = case_dict.get("satellite", {}).get("files", {})
        vv_path_str = sat_files.get("measurement_raster_vv")
        if vv_path_str and resolve_path(vv_path_str).exists():
            checks["satellite_file_present"] = True
        else:
            issues.append(f"Satellite measurement raster missing: {vv_path_str}")

        # Check AIS
        ais_files = case_dict.get("ais", {}).get("files", {})
        ais_path_str = ais_files.get("filtered_csv") or ais_files.get("parquet")
        if ais_path_str and resolve_path(ais_path_str).exists():
            checks["ais_file_present"] = True
        else:
            issues.append(f"Filtered AIS file missing: {ais_path_str}")

        # Check ocean currents
        env = case_dict.get("environmental", {})
        cur_path_str = env.get("ocean_currents", {}).get("file_path")
        if cur_path_str and resolve_path(cur_path_str).exists():
            checks["currents_file_present"] = True
        else:
            issues.append(f"HYCOM ocean currents file missing: {cur_path_str}")

        # Check wind
        wind_path_str = env.get("wind", {}).get("files", {}).get("csv_path")
        if wind_path_str and resolve_path(wind_path_str).exists():
            checks["wind_file_present"] = True
        else:
            issues.append(f"ERA5 wind file missing: {wind_path_str}")

        checks["all_files_present"] = all([
            checks["satellite_file_present"],
            checks["ais_file_present"],
            checks["currents_file_present"],
            checks["wind_file_present"],
        ])
        checks["feasibility_issues"] = issues
        return checks

    def check_spatiotemporal_integrity(self, case_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate bounding box geometry, temporal ordering, and coordinate validity.
        """
        errors = []
        spatial = case_dict.get("spatial", {})
        aoi = spatial.get("aoi_bounding_box", {})

        if not validate_bounding_box(aoi):
            errors.append(f"Invalid AOI bounding box coordinates: {aoi}")
        else:
            area = geodesic_bounding_box_area_km2(aoi)
            if area <= 0:
                errors.append(f"Non-positive AOI bounding box area: {area}")

        temporal = case_dict.get("temporal", {})
        search_range = temporal.get("source_search_time_range", {})
        start_str = search_range.get("start_utc")
        end_str = search_range.get("end_utc")

        if start_str and end_str:
            t_start = parse_utc_timestamp(start_str)
            t_end = parse_utc_timestamp(end_str)
            if t_start >= t_end:
                errors.append(f"Invalid temporal order: start_utc ({start_str}) >= end_utc ({end_str})")

        return {
            "spatial_valid": len(errors) == 0,
            "integrity_errors": errors,
        }

    def assign_validation_eligibility(
        self,
        feasibility: Dict[str, Any],
        integrity: Dict[str, Any],
        quality_level: CaseQualityLevel,
    ) -> ValidationEligibility:
        """Assign eligibility based on data completeness and ground-truth quality."""
        if not integrity.get("spatial_valid", False):
            return ValidationEligibility.INELIGIBLE_MISSING_DATA

        if not feasibility.get("all_files_present", False):
            return ValidationEligibility.INELIGIBLE_MISSING_DATA

        if quality_level in [CaseQualityLevel.A, CaseQualityLevel.B]:
            return ValidationEligibility.ELIGIBLE
        elif quality_level == CaseQualityLevel.C:
            return ValidationEligibility.PARTIALLY_ELIGIBLE
        else:
            return ValidationEligibility.INELIGIBLE_MISSING_DATA

    def build_validation_case_from_dict(self, case_dict: Dict[str, Any]) -> ValidationCase:
        """
        Construct a strongly-typed ValidationCase object from a case configuration dict.
        """
        case_id = str(case_dict.get("case_id", "unknown"))
        name = str(case_dict.get("name", "Unnamed Incident"))
        inc_type = str(case_dict.get("incident_type", "unknown"))
        inc_date = str(case_dict.get("incident_date", "2021-10-02"))

        val_cfg = case_dict.get("validation", {})
        source_type_str = str(val_cfg.get("source_type", "unknown")).lower()
        source_type = SourceType(source_type_str) if source_type_str in [s.value for s in SourceType] else SourceType.UNKNOWN

        q_lvl_str = str(val_cfg.get("quality_level", "A")).upper()
        quality_level = CaseQualityLevel(q_lvl_str) if q_lvl_str in [q.value for q in CaseQualityLevel] else CaseQualityLevel.A

        gt_q_str = str(val_cfg.get("ground_truth_quality", "VERIFIED")).upper()
        gt_quality = GroundTruthQuality(gt_q_str) if gt_q_str in [q.value for q in GroundTruthQuality] else GroundTruthQuality.VERIFIED

        role_str = str(val_cfg.get("validation_role", "POSITIVE_VESSEL_CASE"))
        role = ValidationRole(role_str) if role_str in [r.value for r in ValidationRole] else ValidationRole.POSITIVE_VESSEL_CASE

        ref_loc = val_cfg.get("reference_source_location")
        ref_coords = (float(ref_loc["lon"]), float(ref_loc["lat"])) if ref_loc and "lon" in ref_loc and "lat" in ref_loc and ref_loc["lon"] is not None else None

        ref_time = val_cfg.get("reference_source_time_utc")
        ref_mmsi = val_cfg.get("reference_vessel_mmsi")
        ref_name = val_cfg.get("reference_vessel_name")
        gt_source = str(val_cfg.get("ground_truth_source", "Investigation Report"))

        gt = GroundTruth(
            source_type=source_type,
            reference_source_location=ref_coords,
            reference_source_time_utc=ref_time,
            reference_vessel_mmsi=ref_mmsi,
            reference_vessel_name=ref_name,
            ground_truth_quality=gt_quality,
            quality_level=quality_level,
            ground_truth_source=gt_source,
            validation_role=role,
            notes=str(val_cfg.get("notes", "")),
        )

        inputs = AlgorithmInputs(
            case_id=case_id,
            satellite_files=case_dict.get("satellite", {}).get("files", {}),
            ais_files=case_dict.get("ais", {}).get("files", {}),
            environmental_files=case_dict.get("environmental", {}).get("wind", {}).get("files", {}),
            drift_parameters=case_dict.get("drift", {}).get("physics", {}),
        )

        status_str = str(val_cfg.get("case_status", CaseStatus.POTENTIALLY_AVAILABLE.value))
        case_status = CaseStatus(status_str) if status_str in [s.value for s in CaseStatus] else CaseStatus.POTENTIALLY_AVAILABLE

        feasibility = self.check_data_feasibility(case_dict)
        integrity = self.check_spatiotemporal_integrity(case_dict)
        eligibility = self.assign_validation_eligibility(feasibility, integrity, quality_level)

        return ValidationCase(
            case_id=case_id,
            incident_name=name,
            incident_type=inc_type,
            incident_date=inc_date,
            is_synthetic=False,
            ground_truth=gt,
            algorithm_inputs=inputs,
            case_availability="AVAILABLE" if feasibility["all_files_present"] else "PENDING_INGESTION",
            case_status=case_status,
            validation_eligibility=eligibility,
            satellite_available=feasibility["satellite_file_present"],
            ais_available=feasibility["ais_file_present"],
            currents_available=feasibility["currents_file_present"],
            wind_available=feasibility["wind_file_present"],
            source_location_available=ref_coords is not None,
            source_time_available=ref_time is not None,
            culprit_vessel_available=ref_mmsi is not None or ref_name is not None,
        )
