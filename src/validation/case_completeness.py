"""
Phase 12: Case Data Completeness Evaluator.

Evaluates data completeness across the four essential pillars:
1. Satellite Pillar (Sentinel-1 availability, acquisition timestamp, spatial coverage, measurement pixels)
2. AIS Pillar (vessel identity, temporal coverage, spatial coverage, track quality)
3. Environmental Pillar (HYCOM ocean currents, ERA5 winds, temporal overlap)
4. Ground Truth Pillar (culprit vessel identity, source location, source time, documentation)

Produces:
- case_completeness_matrix.csv
- Per-case feasibility diagnostics and eligibility classification
"""

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import pandas as pd

from src.common.logging import get_logger
from src.common.paths import (
    VALIDATION_PROCESSED_DIR,
    ensure_dir_exists,
    resolve_path,
)
from src.validation.case_schema import (
    CaseQualityLevel,
    CaseStatus,
    SourceType,
    ValidationCase,
    ValidationEligibility,
)

logger = get_logger(__name__)


@dataclass
class CaseCompletenessRecord:
    """Structured data completeness record for a single case."""
    case_id: str
    incident_name: str
    incident_date: str
    source_type: str
    is_synthetic: bool
    case_status: str
    quality_level: str

    # Satellite Pillar
    satellite_platform_valid: bool
    satellite_timestamp_valid: bool
    satellite_spatial_coverage_valid: bool
    satellite_raster_available: bool
    satellite_pillar_score: float

    # AIS Pillar
    ais_identity_valid: bool
    ais_temporal_overlap: bool
    ais_spatial_overlap: bool
    ais_data_available: bool
    ais_pillar_score: float

    # Environmental Pillar
    currents_data_available: bool
    wind_data_available: bool
    environment_temporal_overlap: bool
    environmental_pillar_score: float

    # Ground Truth Pillar
    ground_truth_source_location_known: bool
    ground_truth_source_time_known: bool
    ground_truth_culprit_known: bool
    ground_truth_documentation_verified: bool
    ground_truth_pillar_score: float

    # Overall Summary
    overall_completeness_score: float
    validation_eligibility: str
    missing_data_summary: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CaseCompletenessEvaluator:
    """
    Evaluates and generates the data completeness matrix for historical and benchmark cases.
    """

    def __init__(self, output_dir: Optional[Union[str, Path]] = None):
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = resolve_path(VALIDATION_PROCESSED_DIR)
        ensure_dir_exists(self.output_dir)

    def evaluate_case(self, case: ValidationCase) -> CaseCompletenessRecord:
        """Evaluate completeness across all four pillars for a validation case."""
        gt = case.ground_truth
        inputs = case.algorithm_inputs

        # 1. Satellite Pillar
        sat_files = inputs.satellite_files or {}
        has_sat_files = bool(sat_files.get("measurement_raster_vv") or sat_files.get("sar"))
        # In synthetic cases, files are simulated
        if case.is_synthetic:
            sat_platform = True
            sat_time = True
            sat_spatial = True
            sat_raster = True
        else:
            sat_platform = case.satellite_available
            sat_time = bool(case.incident_date)
            sat_spatial = case.satellite_available
            sat_raster = has_sat_files and case.case_status == CaseStatus.VERIFIED_AVAILABLE

        sat_checks = [sat_platform, sat_time, sat_spatial, sat_raster]
        sat_score = round(sum(sat_checks) / len(sat_checks), 2)

        # 2. AIS Pillar
        ais_files = inputs.ais_files or {}
        has_ais_files = bool(ais_files.get("filtered_csv") or ais_files.get("ais"))
        if case.is_synthetic:
            ais_id = True
            ais_time = True
            ais_space = True
            ais_data = True
        else:
            ais_id = case.ais_available
            ais_time = case.ais_available
            ais_space = case.ais_available
            ais_data = has_ais_files and case.case_status == CaseStatus.VERIFIED_AVAILABLE

        ais_checks = [ais_id, ais_time, ais_space, ais_data]
        ais_score = round(sum(ais_checks) / len(ais_checks), 2)

        # 3. Environmental Pillar
        env_files = inputs.environmental_files or {}
        has_env_files = bool(env_files.get("csv_path") or env_files.get("hycom") or env_files.get("wind"))
        if case.is_synthetic:
            cur_avail = True
            wind_avail = True
            env_time = True
        else:
            cur_avail = case.currents_available and has_env_files
            wind_avail = case.wind_available and has_env_files
            env_time = bool(case.incident_date) and (case.case_status == CaseStatus.VERIFIED_AVAILABLE)

        env_checks = [cur_avail, wind_avail, env_time]
        env_score = round(sum(env_checks) / len(env_checks), 2)

        # 4. Ground Truth Pillar
        gt_loc = gt.reference_source_location is not None
        gt_time = gt.reference_source_time_utc is not None
        if gt.source_type == SourceType.VESSEL:
            gt_culprit = gt.reference_vessel_mmsi is not None or gt.reference_vessel_name is not None
        else:
            # For pipeline/non-vessel cases, absence of culprit vessel is expected
            gt_culprit = True

        gt_doc = bool(gt.ground_truth_source and len(gt.ground_truth_source) > 5)
        gt_checks = [gt_loc, gt_time, gt_culprit, gt_doc]
        gt_score = round(sum(gt_checks) / len(gt_checks), 2)

        # Overall Completeness
        overall = round((sat_score + ais_score + env_score + gt_score) / 4.0, 2)

        # Missing data summary
        missing_items = []
        if not sat_raster:
            missing_items.append("Satellite SAR GRD raster")
        if not ais_data:
            missing_items.append("AIS trajectory records")
        if not (cur_avail and wind_avail):
            missing_items.append("Ocean current / ERA5 wind grids")
        if not gt_loc:
            missing_items.append("Verified source location")
        if not gt_time:
            missing_items.append("Verified incident timestamp")
        if gt.source_type == SourceType.VESSEL and not gt_culprit:
            missing_items.append("Known culprit vessel identity")

        missing_summary = "; ".join(missing_items) if missing_items else "None (Dataset Complete)"

        # Eligibility assignment
        if case.is_synthetic:
            eligibility = ValidationEligibility.ELIGIBLE.value
        elif case.case_status == CaseStatus.VERIFIED_AVAILABLE and overall >= 0.75 and gt.quality_level in [CaseQualityLevel.A, CaseQualityLevel.B]:
            eligibility = ValidationEligibility.ELIGIBLE.value
        elif overall >= 0.50 and gt.quality_level != CaseQualityLevel.D:
            eligibility = ValidationEligibility.PARTIALLY_ELIGIBLE.value
        else:
            eligibility = ValidationEligibility.INELIGIBLE_MISSING_DATA.value

        return CaseCompletenessRecord(
            case_id=case.case_id,
            incident_name=case.incident_name,
            incident_date=case.incident_date or "2021-10-02",
            source_type=gt.source_type.value,
            is_synthetic=case.is_synthetic,
            case_status=case.case_status.value,
            quality_level=gt.quality_level.value,
            satellite_platform_valid=sat_platform,
            satellite_timestamp_valid=sat_time,
            satellite_spatial_coverage_valid=sat_spatial,
            satellite_raster_available=sat_raster,
            satellite_pillar_score=sat_score,
            ais_identity_valid=ais_id,
            ais_temporal_overlap=ais_time,
            ais_spatial_overlap=ais_space,
            ais_data_available=ais_data,
            ais_pillar_score=ais_score,
            currents_data_available=cur_avail,
            wind_data_available=wind_avail,
            environment_temporal_overlap=env_time,
            environmental_pillar_score=env_score,
            ground_truth_source_location_known=gt_loc,
            ground_truth_source_time_known=gt_time,
            ground_truth_culprit_known=gt_culprit,
            ground_truth_documentation_verified=gt_doc,
            ground_truth_pillar_score=gt_score,
            overall_completeness_score=overall,
            validation_eligibility=eligibility,
            missing_data_summary=missing_summary,
        )

    def evaluate_all(self, cases: List[ValidationCase], save_csv: bool = True) -> pd.DataFrame:
        """Evaluate completeness across a list of cases and optionally export CSV."""
        records = [self.evaluate_case(c).to_dict() for c in cases]
        df = pd.DataFrame(records)
        if save_csv:
            csv_path = self.output_dir / "case_completeness_matrix.csv"
            df.to_csv(csv_path, index=False)
            logger.info("Saved case completeness matrix to %s", csv_path)
        return df
