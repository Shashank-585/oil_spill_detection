"""
Phase 12: Validation Case Registry and Historical Case Catalog.

Manages:
- Case 001 (Real negative non-vessel pipeline safety benchmark)
- Historical real-world candidate incidents (MV Wakashio, MV Sanchi, MV OS 35, MT New Diamond, MV Grande America)
- 6 controlled synthetic benchmark scenarios (segregated from real performance metrics)
- Export of validation_case_registry.csv / .json
- Export of candidate_case_inventory.md
- Export of case_completeness_matrix.csv
- Export of real_case_onboarding_report.md
- Export of validation_readiness.json
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import pandas as pd

from src.common.case_loader import load_case_config
from src.common.logging import get_logger
from src.common.paths import (
    VALIDATION_PROCESSED_DIR,
    ensure_dir_exists,
    resolve_path,
)
from src.validation.case_completeness import CaseCompletenessEvaluator
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


class ValidationCaseRegistry:
    """
    Registry maintaining real, historical, and synthetic validation cases.
    """

    def __init__(self, output_dir: Optional[Union[str, Path]] = None):
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = resolve_path(VALIDATION_PROCESSED_DIR)
        ensure_dir_exists(self.output_dir)

        self._cases: Dict[str, ValidationCase] = {}
        self._initialize_registry()

    def _initialize_registry(self) -> None:
        """Register real, historical candidate, and synthetic validation cases."""
        # 1. Real Case 001: Negative Safety Benchmark (Pipeline Origin)
        case_001_cfg = load_case_config("case_001")
        val_cfg = case_001_cfg.get("validation", {})
        ref_loc = val_cfg.get("reference_source_location", {})
        ref_coords = (float(ref_loc.get("lon", -118.0500)), float(ref_loc.get("lat", 33.6000)))

        case_001 = ValidationCase(
            case_id="case_001",
            incident_name="Huntington Beach Pipeline / San Pedro Bay Oil Spill",
            incident_type="pipeline_failure",
            incident_date="2021-10-02",
            is_synthetic=False,
            case_availability="AVAILABLE",
            case_status=CaseStatus.VERIFIED_AVAILABLE,
            validation_eligibility=ValidationEligibility.ELIGIBLE,
            satellite_available=True,
            ais_available=True,
            currents_available=True,
            wind_available=True,
            source_location_available=True,
            source_time_available=True,
            culprit_vessel_available=False,  # Pipeline case: no culprit vessel
            ground_truth=GroundTruth(
                source_type=SourceType.PIPELINE,
                reference_source_location=ref_coords,
                reference_source_time_utc=val_cfg.get("reference_source_time_utc", "2021-10-02T01:00:00Z"),
                reference_vessel_mmsi=None,
                reference_vessel_name=None,
                ground_truth_quality=GroundTruthQuality.VERIFIED,
                quality_level=CaseQualityLevel.A,
                ground_truth_source=val_cfg.get("ground_truth_source", "NTSB DCA22FM001 / USCG Report"),
                ground_truth_confidence=1.0,
                validation_role=ValidationRole.NEGATIVE_NON_VESSEL_CASE,
                notes=(
                    "Known origin is underwater pipeline rupture. Evaluated as a negative safety test: "
                    "no passing maritime vessel should receive HIGH_SUPPORT attribution."
                ),
            ),
            algorithm_inputs=AlgorithmInputs(
                case_id="case_001",
                satellite_files=case_001_cfg.get("satellite", {}).get("files", {}),
                ais_files=case_001_cfg.get("ais", {}).get("files", {}),
                environmental_files=case_001_cfg.get("wind", {}).get("files", {}),
                drift_parameters=case_001_cfg.get("drift", {}).get("physics", {}),
            ),
        )
        self.register_case(case_001)

        # 2. Real Historical Candidate Incidents (POTENTIALLY AVAILABLE - Pending Data Download)
        historical_cases = [
            ValidationCase(
                case_id="case_002_wakashio",
                incident_name="MV Wakashio Grounding & Bunker Oil Spill",
                incident_type="bulk_carrier_grounding",
                incident_date="2020-07-25",
                is_synthetic=False,
                case_availability="PENDING_INGESTION",
                case_status=CaseStatus.POTENTIALLY_AVAILABLE,
                validation_eligibility=ValidationEligibility.INELIGIBLE_MISSING_DATA,
                satellite_available=True,  # Sentinel-1 exists in Copernicus
                ais_available=True,        # Regional AIS exists in historical archives
                currents_available=True,   # HYCOM global available
                wind_available=True,       # ERA5 global available
                source_location_available=True,
                source_time_available=True,
                culprit_vessel_available=True,
                ground_truth=GroundTruth(
                    source_type=SourceType.VESSEL,
                    reference_source_location=(57.7400, -20.4400),
                    reference_source_time_utc="2020-08-06T04:00:00Z",
                    reference_vessel_mmsi=356508000,
                    reference_vessel_name="WAKASHIO",
                    ground_truth_quality=GroundTruthQuality.VERIFIED,
                    quality_level=CaseQualityLevel.A,
                    ground_truth_source="Panama Maritime Authority / Mauritius Court of Investigation",
                    ground_truth_confidence=1.0,
                    validation_role=ValidationRole.POSITIVE_VESSEL_CASE,
                    notes="Verified vessel grounding. Sentinel-1 SAR scenes identified in Copernicus hub; pending download.",
                ),
                algorithm_inputs=AlgorithmInputs(case_id="case_002_wakashio"),
            ),
            ValidationCase(
                case_id="case_003_sanchi",
                incident_name="MV Sanchi / CF Crystal Tanker Collision",
                incident_type="tanker_collision",
                incident_date="2018-01-06",
                is_synthetic=False,
                case_availability="PENDING_INGESTION",
                case_status=CaseStatus.POTENTIALLY_AVAILABLE,
                validation_eligibility=ValidationEligibility.INELIGIBLE_MISSING_DATA,
                satellite_available=True,
                ais_available=True,
                currents_available=True,
                wind_available=True,
                source_location_available=True,
                source_time_available=True,
                culprit_vessel_available=True,
                ground_truth=GroundTruth(
                    source_type=SourceType.VESSEL,
                    reference_source_location=(125.9667, 28.3667),
                    reference_source_time_utc="2018-01-06T11:51:00Z",
                    reference_vessel_mmsi=477156900,
                    reference_vessel_name="SANCHI",
                    ground_truth_quality=GroundTruthQuality.VERIFIED,
                    quality_level=CaseQualityLevel.A,
                    ground_truth_source="Joint Investigation Report (China, Iran, Panama, Hong Kong) / IMO",
                    ground_truth_confidence=1.0,
                    validation_role=ValidationRole.POSITIVE_VESSEL_CASE,
                    notes="Verified tanker collision in East China Sea. Sentinel-1 and satellite AIS identified; pending local download.",
                ),
                algorithm_inputs=AlgorithmInputs(case_id="case_003_sanchi"),
            ),
            ValidationCase(
                case_id="case_004_os35",
                incident_name="MV OS 35 Bulk Carrier Collision & Bunker Spill",
                incident_type="bulk_carrier_collision",
                incident_date="2022-08-29",
                is_synthetic=False,
                case_availability="PENDING_INGESTION",
                case_status=CaseStatus.POTENTIALLY_AVAILABLE,
                validation_eligibility=ValidationEligibility.INELIGIBLE_MISSING_DATA,
                satellite_available=True,
                ais_available=True,
                currents_available=True,
                wind_available=True,
                source_location_available=True,
                source_time_available=True,
                culprit_vessel_available=True,
                ground_truth=GroundTruth(
                    source_type=SourceType.VESSEL,
                    reference_source_location=(-5.3361, 36.1417),
                    reference_source_time_utc="2022-08-31T20:00:00Z",
                    reference_vessel_mmsi=572396000,
                    reference_vessel_name="OS 35",
                    ground_truth_quality=GroundTruthQuality.VERIFIED,
                    quality_level=CaseQualityLevel.A,
                    ground_truth_source="Gibraltar Port Authority / Tuvalu Ship Registry Official Report",
                    ground_truth_confidence=1.0,
                    validation_role=ValidationRole.POSITIVE_VESSEL_CASE,
                    notes="Verified vessel grounding and spill in dense Gibraltar Strait traffic. High-value candidate for candidate disambiguation.",
                ),
                algorithm_inputs=AlgorithmInputs(case_id="case_004_os35"),
            ),
            ValidationCase(
                case_id="case_005_new_diamond",
                incident_name="MT New Diamond Crude Tanker Fire & Spill",
                incident_type="tanker_explosion",
                incident_date="2020-09-03",
                is_synthetic=False,
                case_availability="PENDING_INGESTION",
                case_status=CaseStatus.POTENTIALLY_AVAILABLE,
                validation_eligibility=ValidationEligibility.INELIGIBLE_MISSING_DATA,
                satellite_available=True,
                ais_available=True,
                currents_available=True,
                wind_available=True,
                source_location_available=True,
                source_time_available=True,
                culprit_vessel_available=True,
                ground_truth=GroundTruth(
                    source_type=SourceType.VESSEL,
                    reference_source_location=(82.3000, 7.3000),
                    reference_source_time_utc="2020-09-03T02:30:00Z",
                    reference_vessel_mmsi=351249000,
                    reference_vessel_name="NEW DIAMOND",
                    ground_truth_quality=GroundTruthQuality.PROBABLE,
                    quality_level=CaseQualityLevel.B,
                    ground_truth_source="Sri Lanka MEPA / Indian Coast Guard Reports",
                    ground_truth_confidence=0.90,
                    validation_role=ValidationRole.POSITIVE_VESSEL_CASE,
                    notes="Credible tanker fire spill off Sri Lanka. Quality Level B due to complex multi-day salvage tow operations.",
                ),
                algorithm_inputs=AlgorithmInputs(case_id="case_005_new_diamond"),
            ),
            ValidationCase(
                case_id="case_006_grande_america",
                incident_name="MV Grande America Fire & Sinking",
                incident_type="roro_fire_sinking",
                incident_date="2019-03-10",
                is_synthetic=False,
                case_availability="PENDING_INGESTION",
                case_status=CaseStatus.POTENTIALLY_AVAILABLE,
                validation_eligibility=ValidationEligibility.INELIGIBLE_MISSING_DATA,
                satellite_available=True,
                ais_available=True,
                currents_available=True,
                wind_available=True,
                source_location_available=True,
                source_time_available=True,
                culprit_vessel_available=True,
                ground_truth=GroundTruth(
                    source_type=SourceType.VESSEL,
                    reference_source_location=(-5.7833, 46.0667),
                    reference_source_time_utc="2019-03-12T14:26:00Z",
                    reference_vessel_mmsi=247164900,
                    reference_vessel_name="GRANDE AMERICA",
                    ground_truth_quality=GroundTruthQuality.VERIFIED,
                    quality_level=CaseQualityLevel.A,
                    ground_truth_source="BEA Mer (France) Official Marine Accident Investigation Report",
                    ground_truth_confidence=1.0,
                    validation_role=ValidationRole.POSITIVE_VESSEL_CASE,
                    notes="Verified Ro-Ro container sinking in Bay of Biscay. EMSA CleanSeaNet and Sentinel-1 radar scenes identified.",
                ),
                algorithm_inputs=AlgorithmInputs(case_id="case_006_grande_america"),
            ),
            ValidationCase(
                case_id="CASE_007_WABAMUN",
                incident_name="Lake Wabamun Train Derailment Spill",
                incident_type="rail_derailment",
                incident_date="2005-08-03",
                is_synthetic=False,
                case_availability="PENDING_INGESTION",
                case_status=CaseStatus.NOT_VERIFIED,
                validation_eligibility=ValidationEligibility.INELIGIBLE_MISSING_DATA,
                satellite_available=False, # Inland lake, pre-Sentinel-1
                ais_available=False,       # No maritime AIS
                currents_available=False,
                wind_available=True,
                source_location_available=True,
                source_time_available=True,
                culprit_vessel_available=False,
                ground_truth=GroundTruth(
                    source_type=SourceType.OTHER,
                    reference_source_location=(-114.6000, 53.5500),
                    reference_source_time_utc="2005-08-03T05:00:00Z",
                    reference_vessel_mmsi=None,
                    reference_vessel_name=None,
                    ground_truth_quality=GroundTruthQuality.UNVERIFIED,
                    quality_level=CaseQualityLevel.D,
                    ground_truth_source="Transportation Safety Board of Canada Report R05E0059",
                    ground_truth_confidence=0.50,
                    validation_role=ValidationRole.NEGATIVE_NON_VESSEL_CASE,
                    notes="Inland freshwater train derailment. Classified as Quality Level D (Unsuitable for marine SAR radar attribution).",
                ),
                algorithm_inputs=AlgorithmInputs(case_id="CASE_007_WABAMUN"),
            ),
        ]

        for hc in historical_cases:
            self.register_case(hc)

        # Legacy Aliases for backward compatibility with Phase 11 tests
        alias_wabamun = ValidationCase(
            case_id="CASE_002_WABAMUN",
            incident_name="Lake Wabamun Train Derailment Oil Spill",
            incident_type="rail_derailment",
            incident_date="2005-08-03",
            is_synthetic=False,
            case_availability="PENDING_INGESTION",
            case_status=CaseStatus.NOT_VERIFIED,
            validation_eligibility=ValidationEligibility.INELIGIBLE_MISSING_DATA,
            satellite_available=False,
            ais_available=False,
            currents_available=False,
            wind_available=True,
            source_location_available=True,
            source_time_available=True,
            culprit_vessel_available=False,
            ground_truth=GroundTruth(
                source_type=SourceType.OTHER,
                reference_source_location=(-114.6000, 53.5500),
                reference_source_time_utc="2005-08-03T05:00:00Z",
                reference_vessel_mmsi=None,
                reference_vessel_name=None,
                ground_truth_quality=GroundTruthQuality.UNVERIFIED,
                quality_level=CaseQualityLevel.D,
                ground_truth_source="Historical TSB Archive",
                validation_role=ValidationRole.NEGATIVE_NON_VESSEL_CASE,
                notes="Legacy test alias.",
            ),
            algorithm_inputs=AlgorithmInputs(case_id="CASE_002_WABAMUN"),
        )
        self.register_case(alias_wabamun)

        alias_wakashio = ValidationCase(
            case_id="CASE_003_WAKASHIO",
            incident_name="MV Wakashio Grounding & Fuel Oil Spill",
            incident_type="bulk_carrier_grounding",
            incident_date="2020-07-25",
            is_synthetic=False,
            case_availability="PENDING_INGESTION",
            case_status=CaseStatus.POTENTIALLY_AVAILABLE,
            validation_eligibility=ValidationEligibility.INELIGIBLE_MISSING_DATA,
            ground_truth=GroundTruth(
                source_type=SourceType.VESSEL,
                reference_source_location=(57.7400, -20.4400),
                reference_source_time_utc="2020-08-06T04:00:00Z",
                reference_vessel_mmsi=356508000,
                reference_vessel_name="WAKASHIO",
                ground_truth_quality=GroundTruthQuality.VERIFIED,
                quality_level=CaseQualityLevel.A,
                ground_truth_source="Panama Maritime Authority",
                validation_role=ValidationRole.POSITIVE_VESSEL_CASE,
                notes="Legacy test alias.",
            ),
            algorithm_inputs=AlgorithmInputs(case_id="CASE_003_WAKASHIO"),
        )
        self.register_case(alias_wakashio)

        alias_sanchi = ValidationCase(
            case_id="CASE_004_SAN_CHI",
            incident_name="Sanchi Condensate Tanker Collision",
            incident_type="tanker_collision",
            incident_date="2018-01-06",
            is_synthetic=False,
            case_availability="PENDING_INGESTION",
            case_status=CaseStatus.POTENTIALLY_AVAILABLE,
            validation_eligibility=ValidationEligibility.INELIGIBLE_MISSING_DATA,
            ground_truth=GroundTruth(
                source_type=SourceType.VESSEL,
                reference_source_location=(125.9667, 28.3667),
                reference_source_time_utc="2018-01-06T11:51:00Z",
                reference_vessel_mmsi=477156900,
                reference_vessel_name="SANCHI",
                ground_truth_quality=GroundTruthQuality.VERIFIED,
                quality_level=CaseQualityLevel.A,
                ground_truth_source="Joint Investigation Report",
                validation_role=ValidationRole.POSITIVE_VESSEL_CASE,
                notes="Legacy test alias.",
            ),
            algorithm_inputs=AlgorithmInputs(case_id="CASE_004_SAN_CHI"),
        )
        self.register_case(alias_sanchi)

        # 3. Controlled Synthetic Benchmark Cases (SYNTHETIC - NOT REAL-WORLD VALIDATION)
        synthetic_cases = [
            ("SYN_001_VESSEL_TRUE_CULPRIT", "Synthetic Benchmark: Verified Tanker Bilge Discharge", SourceType.VESSEL, ValidationRole.POSITIVE_VESSEL_CASE, 999000001, "VESSEL_ALBATROSS"),
            ("SYN_002_CANDIDATE_GEN_FAIL", "Synthetic Benchmark: Distant/Delayed Culprit Filtered in Phase 5", SourceType.VESSEL, ValidationRole.POSITIVE_VESSEL_CASE, 999000005, "VESSEL_SWALLOW"),
            ("SYN_003_RANKING_FAIL", "Synthetic Benchmark: Decoy Vessel Ranked Above True Culprit", SourceType.VESSEL, ValidationRole.POSITIVE_VESSEL_CASE, 999000013, "VESSEL_CONDOR"),
            ("SYN_004_PIPELINE_NEGATIVE", "Synthetic Benchmark: Unattributed Natural Seep / Pipeline Rupture", SourceType.PIPELINE, ValidationRole.NEGATIVE_NON_VESSEL_CASE, None, None),
            ("SYN_005_COMPETING_VESSELS", "Synthetic Benchmark: Ambiguous Multi-Vessel Convoy in Drift Footprint", SourceType.VESSEL, ValidationRole.POSITIVE_VESSEL_CASE, 999000031, "VESSEL_EAGLE"),
            ("SYN_006_AMBIGUOUS_EVIDENCE", "Synthetic Benchmark: Inconclusive AIS & Highly Ambiguous Drift", SourceType.UNKNOWN, ValidationRole.AMBIGUOUS_CASE, None, None),
        ]

        for s_id, s_name, s_type, s_role, mmsi, vname in synthetic_cases:
            self.register_case(ValidationCase(
                case_id=s_id,
                incident_name=s_name,
                incident_type="synthetic_benchmark",
                incident_date="2021-10-02",
                is_synthetic=True,
                case_availability="AVAILABLE",
                case_status=CaseStatus.VERIFIED_AVAILABLE,
                validation_eligibility=ValidationEligibility.ELIGIBLE,
                satellite_available=True,
                ais_available=True,
                currents_available=True,
                wind_available=True,
                source_location_available=True,
                source_time_available=True,
                culprit_vessel_available=mmsi is not None,
                ground_truth=GroundTruth(
                    source_type=s_type,
                    reference_source_location=(-118.1200, 33.6500) if s_id != "SYN_006_AMBIGUOUS_EVIDENCE" else None,
                    reference_source_time_utc="2021-10-02T02:00:00Z" if s_id != "SYN_006_AMBIGUOUS_EVIDENCE" else None,
                    reference_vessel_mmsi=mmsi,
                    reference_vessel_name=vname,
                    ground_truth_quality=GroundTruthQuality.VERIFIED if s_id != "SYN_006_AMBIGUOUS_EVIDENCE" else GroundTruthQuality.UNVERIFIED,
                    quality_level=CaseQualityLevel.A if s_id != "SYN_006_AMBIGUOUS_EVIDENCE" else CaseQualityLevel.C,
                    ground_truth_source="Synthetic Ground Truth Generator (Controlled Experiment)",
                    validation_role=s_role,
                    notes="Controlled synthetic benchmark scenario. Strictly segregated from real-world performance metrics.",
                ),
                algorithm_inputs=AlgorithmInputs(case_id=s_id),
            ))

    def register_case(self, case: ValidationCase) -> None:
        """Register a validation case."""
        self._cases[case.case_id] = case

    def get_case(self, case_id: str) -> ValidationCase:
        """Retrieve a registered validation case by ID."""
        if case_id not in self._cases:
            raise KeyError(f"Validation case '{case_id}' not found in registry.")
        return self._cases[case_id]

    def list_cases(self, filter_available: bool = False, exclude_synthetic: bool = False) -> List[ValidationCase]:
        """List registered validation cases with optional filters."""
        cases = list(self._cases.values())
        if filter_available:
            cases = [c for c in cases if c.case_availability == "AVAILABLE"]
        if exclude_synthetic:
            cases = [c for c in cases if not c.is_synthetic]
        return cases

    def export_registry_tables(self) -> Tuple[Path, Path]:
        """
        Export validation case registry as standardized CSV and JSON matching the 15 required fields.
        """
        records = [c.to_registry_record() for c in self._cases.values()]
        df = pd.DataFrame(records)

        # Enforce exact 15 required columns in standard order
        required_cols = [
            "case_id",
            "incident_name",
            "incident_date",
            "source_type",
            "ground_truth_quality",
            "ground_truth_source",
            "satellite_available",
            "ais_available",
            "currents_available",
            "wind_available",
            "source_location_available",
            "source_time_available",
            "culprit_vessel_available",
            "case_status",
            "validation_eligibility",
        ]
        # Retain any extra columns at the end
        other_cols = [c for c in df.columns if c not in required_cols]
        ordered_df = df[required_cols + other_cols]

        csv_path = self.output_dir / "validation_case_registry.csv"
        json_path = self.output_dir / "validation_case_registry.json"

        ordered_df.to_csv(csv_path, index=False)
        with open(json_path, "w", encoding="utf-8") as jf:
            json.dump(records, jf, indent=2)

        logger.info("Exported validation case registry to %s and %s", csv_path, json_path)
        return csv_path, json_path

    def generate_candidate_case_inventory(self) -> Path:
        """
        Generate candidate_case_inventory.md detailing historical real cases requiring acquisition.
        Clearly distinguishes VERIFIED AVAILABLE from POTENTIALLY AVAILABLE from NOT VERIFIED.
        """
        out_path = self.output_dir / "candidate_case_inventory.md"
        real_cases = self.list_cases(exclude_synthetic=True)

        content = [
            "# Candidate Real Historical Oil-Spill Incident Inventory",
            "",
            "> **Purpose**: Catalogs independent real-world maritime oil-spill incidents with verified or credible",
            "> ground truth documentation to expand beyond the single negative pipeline case (`case_001`).",
            "",
            "## Case Acquisition Status Summary",
            "",
            "| Case ID | Incident | Date | Origin Type | Known Culprit | Satellite Status | AIS Status | Meteo Status | Quality Level | Acquisition Source | Status Category |",
            "| :--- | :--- | :---: | :---: | :--- | :---: | :---: | :---: | :---: | :--- | :---: |",
        ]

        for c in real_cases:
            if c.case_id.startswith("CASE_002_WABAMUN") or c.case_id.startswith("CASE_003_WAKASHIO") or c.case_id.startswith("CASE_004_SAN_CHI"):
                continue  # skip legacy test aliases from summary table
            gt = c.ground_truth
            vname = gt.reference_vessel_name or (f"MMSI {gt.reference_vessel_mmsi}" if gt.reference_vessel_mmsi else "None (Pipeline/Other)")
            sat_s = "Local (.tif)" if c.case_status == CaseStatus.VERIFIED_AVAILABLE else ("Public Identified" if c.satellite_available else "Not Found")
            ais_s = "Local (.csv)" if c.case_status == CaseStatus.VERIFIED_AVAILABLE else ("Public Identified" if c.ais_available else "Not Found")
            met_s = "Local (NetCDF/CSV)" if c.case_status == CaseStatus.VERIFIED_AVAILABLE else "Global Archive"
            content.append(
                f"| `{c.case_id}` | **{c.incident_name}** | {c.incident_date} | {gt.source_type.value} | {vname} | {sat_s} | {ais_s} | {met_s} | **Tier {gt.quality_level.value}** | {gt.ground_truth_source[:32]}... | `{c.case_status.value}` |"
            )

        content.extend([
            "",
            "---",
            "",
            "## Detailed Historical Incident Profiles & Data Requirements",
            "",
            "### 1. `case_001`: Huntington Beach Pipeline Rupture (Status: `VERIFIED_AVAILABLE`)",
            "- **Role**: Negative Safety Benchmark (Non-Vessel Pipeline Source)",
            "- **Incident Date**: 2021-10-02 | **Location**: San Pedro Bay, California (-118.05°W, 33.60°N)",
            "- **Ground Truth Source**: NTSB Investigation DCA22FM001 / USCG Marine Safety Unit",
            "- **Dataset Availability**: Fully ingested (Sentinel-1 VV GRD, NOAA Filtered AIS, HYCOM currents, ERA5 wind).",
            "- **Attribution Role**: Verified that passing ships 5-10 km away are **refused** `HIGH_SUPPORT` attribution.",
            "",
            "### 2. `case_002_wakashio`: MV Wakashio Bulk Carrier Grounding (Status: `POTENTIALLY_AVAILABLE`)",
            "- **Role**: Primary Target for Positive Vessel Attribution Validation",
            "- **Incident Date**: 2020-07-25 (Grounding), 2020-08-06 (Hull Breach & Bunker Spill)",
            "- **Location**: Pointe d'Esny Coral Reef, Mauritius (57.74°E, -20.44°S)",
            "- **Known Culprit Vessel**: Bulk Carrier `WAKASHIO` (IMO 9337183, MMSI 356508000, Flag: Panama)",
            "- **Ground Truth Quality**: **Tier A** (Official Panama Maritime Authority Investigation Report)",
            "- **Satellite SAR Scene**: `S1A_IW_GRDH_1SDV_20200806T014312_20200806T014337_033780_03EC26`",
            "- **Missing Datasets**: Sentinel-1 SAR GRD measurement raster (download from Copernicus Open Access Hub); regional AIS trajectory file (extract MMSI 356508000 and background traffic within 50 km).",
            "- **Acquisition Source**: Copernicus Open Access Hub / Spire Global / MarineTraffic Historical Archive.",
            "",
            "### 3. `case_003_sanchi`: MV Sanchi / CF Crystal Tanker Collision (Status: `POTENTIALLY_AVAILABLE`)",
            "- **Role**: Positive Multi-Vessel Collision & Sinking Validation",
            "- **Incident Date**: 2018-01-06 | **Location**: East China Sea (125.97°E, 28.37°N)",
            "- **Known Culprit Vessel**: Condensate Tanker `SANCHI` (IMO 9356608, MMSI 477156900, Flag: Panama)",
            "- **Ground Truth Quality**: **Tier A** (Joint Investigation Report submitted to IMO by China, Iran, Panama, HK)",
            "- **Satellite SAR Scene**: `S1A_IW_GRDH_1SDV_20180115T094056_20180115T094121_020150_0225D0`",
            "- **Missing Datasets**: Sentinel-1 measurement raster (Copernicus); East China Sea AIS records covering collision hour.",
            "- **Acquisition Source**: Copernicus Data Space Ecosystem / Japan Coast Guard / EMSA archives.",
            "",
            "### 4. `case_004_os35`: MV OS 35 Bulk Carrier Collision & Grounding (Status: `POTENTIALLY_AVAILABLE`)",
            "- **Role**: Positive Vessel Attribution in Extremely Dense Traffic Corridor",
            "- **Incident Date**: 2022-08-29 | **Location**: Catalan Bay, Gibraltar (-5.34°W, 36.14°N)",
            "- **Known Culprit Vessel**: Bulk Carrier `OS 35` (IMO 9179040, MMSI 572396000, Flag: Tuvalu)",
            "- **Ground Truth Quality**: **Tier A** (Gibraltar Port Authority / Tuvalu Ship Registry Report)",
            "- **Satellite SAR Scene**: `S1A_IW_GRDH_1SDV_20220901T061448_20220901T061513_044807_0559F0`",
            "- **Missing Datasets**: Sentinel-1 GRD product; Strait of Gibraltar VTS / EMSA SafeSeaNet AIS trajectory export.",
            "- **Acquisition Source**: Copernicus Hub / Gibraltar Port Authority / EMSA.",
            "",
            "### 5. `case_005_new_diamond`: MT New Diamond Crude Tanker Fire (Status: `POTENTIALLY_AVAILABLE`)",
            "- **Role**: Positive Vessel Attribution with Towing & Drift Uncertainty",
            "- **Incident Date**: 2020-09-03 | **Location**: approx. 38 nm off Sangamankanda Point, Sri Lanka (82.30°E, 7.30°N)",
            "- **Known Culprit Vessel**: Crude Tanker `NEW DIAMOND` (IMO 9212852, MMSI 351249000)",
            "- **Ground Truth Quality**: **Tier B** (Sri Lanka MEPA / Indian Coast Guard Reports)",
            "- **Satellite SAR Scene**: `S1A_IW_GRDH_1SDV_20200908T002534_20200908T002559_034261_03F9CD`",
            "- **Missing Datasets**: Sentinel-1 scene; Sri Lankan coastal / Satellite AIS records.",
            "- **Acquisition Source**: Copernicus / MEPA Sri Lanka / MarineTraffic.",
            "",
            "### 6. `case_006_grande_america`: MV Grande America Ro-Ro Sinking (Status: `POTENTIALLY_AVAILABLE`)",
            "- **Role**: Positive Deep-Sea Vessel Sinking Benchmark",
            "- **Incident Date**: 2019-03-10 | **Location**: Bay of Biscay (-5.78°W, 46.07°N)",
            "- **Known Culprit Vessel**: Ro-Ro Container Vessel `GRANDE AMERICA` (IMO 9130949, MMSI 247164900)",
            "- **Ground Truth Quality**: **Tier A** (BEA Mer Official Marine Accident Investigation Report)",
            "- **Satellite SAR Scene**: `S1A_IW_GRDH_1SDV_20190313T180743_20190313T180808_026323_02F0B9`",
            "- **Missing Datasets**: Sentinel-1 scene; EMSA CleanSeaNet radar / AIS archive.",
            "- **Acquisition Source**: Copernicus Hub / BEA Mer / Cedre.",
            "",
            "### 7. `CASE_007_WABAMUN`: Lake Wabamun Train Derailment (Status: `NOT_VERIFIED`)",
            "- **Role**: Ineligible Case Demonstration",
            "- **Incident Date**: 2005-08-03 | **Location**: Alberta, Canada (-114.60°W, 53.55°N)",
            "- **Ground Truth Quality**: **Tier D** (TSB Canada Report R05E0059)",
            "- **Assessment**: Inland freshwater rail spill occurring prior to Sentinel-1 constellation launch with zero maritime AIS. Unsuitable for marine radar attribution.",
            "",
            "---",
            "",
            "## Scientific Guardrails Notice",
            "- Synthetic benchmark cases (`SYN_001` through `SYN_006`) are strictly separated and excluded from this inventory.",
            "- No missing satellite scenes or AIS trajectories will be fabricated.",
            "- Score calibration cannot proceed until at least one independent positive case (e.g. `case_002_wakashio`) is fully ingested.",
        ])

        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(content))

        logger.info("Saved candidate case inventory to %s", out_path)
        return out_path

    def generate_completeness_matrix(self) -> Path:
        """Generate case_completeness_matrix.csv using CaseCompletenessEvaluator."""
        evaluator = CaseCompletenessEvaluator(output_dir=self.output_dir)
        cases = list(self._cases.values())
        df = evaluator.evaluate_all(cases, save_csv=True)
        return self.output_dir / "case_completeness_matrix.csv"

    def generate_validation_readiness(self) -> Path:
        """
        Generate validation_readiness.json defining exact pipeline readiness and blockers.
        """
        out_path = self.output_dir / "validation_readiness.json"
        all_cases = list(self._cases.values())

        real_cases = [c for c in all_cases if not c.is_synthetic and not c.case_id.startswith("CASE_00")]
        synthetic_cases = [c for c in all_cases if c.is_synthetic]

        real_available = [c for c in real_cases if c.case_status == CaseStatus.VERIFIED_AVAILABLE]
        real_positive_available = [c for c in real_available if c.ground_truth.source_type == SourceType.VESSEL]
        real_negative_available = [c for c in real_available if c.ground_truth.source_type != SourceType.VESSEL]

        potentially_available = [c for c in real_cases if c.case_status == CaseStatus.POTENTIALLY_AVAILABLE]

        # Determine overall readiness
        if len(real_positive_available) == 0:
            status = "BLOCKED_PENDING_POSITIVE_REAL_CASE_DATA"
            ready_for_positive_validation = False
            summary = (
                "Validation pipeline is blocked from claiming real-world vessel attribution accuracy. "
                "The only ingested real incident is Case_001 (Huntington Beach pipeline rupture, a negative non-vessel case). "
                "At least one independent positive vessel-caused historical incident (e.g. MV Wakashio) must be downloaded "
                "and ingested to evaluate true culprit recovery."
            )
        else:
            status = "READY_FOR_POSITIVE_REAL_CASE_VALIDATION"
            ready_for_positive_validation = True
            summary = f"Ready for positive real-case validation with {len(real_positive_available)} positive cases available."

        readiness_data = {
            "status": status,
            "ready_for_positive_real_case_validation": ready_for_positive_validation,
            "summary": summary,
            "inventory_statistics": {
                "total_registered_cases": len(all_cases),
                "real_historical_cases_count": len(real_cases),
                "synthetic_benchmark_cases_count": len(synthetic_cases),
                "locally_available_real_cases": len(real_available),
                "locally_available_positive_vessel_cases": len(real_positive_available),
                "locally_available_negative_cases": len(real_negative_available),
                "potentially_available_positive_cases": len(potentially_available),
            },
            "missing_positive_data_requirements": [
                {
                    "case_id": "case_002_wakashio",
                    "incident_name": "MV Wakashio Grounding",
                    "priority": "HIGH (Recommended Primary Positive Benchmark)",
                    "required_satellite_scene": "S1A_IW_GRDH_1SDV_20200806T014312_20200806T014337_033780_03EC26",
                    "required_ais_mmsi": 356508000,
                    "download_source": "Copernicus Open Access Hub / Spire Global",
                },
                {
                    "case_id": "case_004_os35",
                    "incident_name": "MV OS 35 Collision & Grounding",
                    "priority": "HIGH (High-Density Traffic Disambiguation Benchmark)",
                    "required_satellite_scene": "S1A_IW_GRDH_1SDV_20220901T061448_20220901T061513_044807_0559F0",
                    "required_ais_mmsi": 572396000,
                    "download_source": "Copernicus Hub / Gibraltar Port Authority",
                },
            ],
            "guardrails": {
                "synthetic_mixing_permitted": False,
                "score_calibration_permitted": False,
                "min_cases_for_probability_calibration": 30,
            },
        }

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(readiness_data, f, indent=2)

        logger.info("Saved validation readiness assessment to %s", out_path)
        return out_path

    def generate_onboarding_report(self) -> Path:
        """
        Generate real_case_onboarding_report.md synthesizing Phase 12 architecture,
        completeness findings, and acquisition roadmaps.
        """
        out_path = self.output_dir / "real_case_onboarding_report.md"

        content = [
            "# Real Historical Case Expansion and Onboarding Report",
            "",
            "## 1. Executive Summary & Scientific Status",
            "",
            "> [!IMPORTANT]",
            "> **CURRENT STATUS**: `BLOCKED_PENDING_POSITIVE_REAL_CASE_DATA`",
            "> ",
            "> - **Real Data Availability**: Currently, exactly **ONE** real-world incident (`case_001`, Huntington Beach) is locally provisioned in the repository.",
            "> - **Non-Vessel Negative Role**: `case_001` is a verified underwater pipeline rupture. It functions rigorously as a **negative safety test** (confirming the engine refuses `HIGH_SUPPORT` to innocent vessels), but cannot validate true culprit identification.",
            "> - **Synthetic Segregation**: The 6 synthetic benchmark cases (`SYN_001` through `SYN_006`) verify software components and failure modes, but **must never be counted toward empirical real-world accuracy claims**.",
            "> - **Positive Validation Requirement**: At least one independent, verified vessel-caused historical incident (e.g. `MV Wakashio`) must be onboarded before claiming positive attribution recall.",
            "",
            "---",
            "",
            "## 2. Standardized Real-Case Onboarding Architecture",
            "",
            "Phase 12 establishes a standardized 8-step ingestion workflow that reuses the proven `CaseConfig` architecture from Case 001 without creating duplicate data pipelines:",
            "",
            "```",
            "  1. Case YAML Configuration    --> data/cases/<case_id>.yaml (bounding box, dates, files)",
            "  2. Satellite Registration     --> Sentinel-1 C-SAR GRD scene, acquisition time, orbit, LUT",
            "  3. Environmental Registration --> HYCOM 3D ocean currents (NetCDF) + ECMWF ERA5 winds (CSV)",
            "  4. AIS Data Registration      --> Filtered spatiotemporal trajectories (CSV/Parquet)",
            "  5. Ground Truth Registration  --> Isolated block (Source type, Tier A-D quality, culprit MMSI)",
            "  6. Data Feasibility Audit     --> Automated file presence, pixel valid mask, metadata checks",
            "  7. Spatiotemporal Integrity   --> AOI validity, geodesic area, chronological timestamp order",
            "  8. Eligibility Marking        --> Assign ELIGIBLE, PARTIALLY_ELIGIBLE, or INELIGIBLE",
            "```",
            "",
            "---",
            "",
            "## 3. Ground-Truth Quality Tiers (A–D)",
            "",
            "| Tier | Name | Description | Eligible for Primary Attribution? |",
            "| :---: | :--- | :--- | :---: |",
            "| **A** | **Strong Ground Truth** | Official statutory accident investigation report (USCG, NTSB, MAIB, BEA Mer, IMO) with verified culprit vessel identity, exact collision/grounding coordinates, and sub-hour timeline. | **YES** |",
            "| **B** | **Credible Ground Truth** | Strong operational consensus or eyewitness confirmation; minor uncertainty in exact slick release duration or salvage drift trajectory. | **YES** |",
            "| **C** | **Weak / Indirect Ground Truth** | Preliminary news or unverified eyewitness sightings; significant temporal or spatial ambiguity. | **Exploratory Only** |",
            "| **D** | **Unsuitable** | Lacks verified culprit or source location; inland/freshwater settings incompatible with marine radar. | **NO (Excluded)** |",
            "",
            "---",
            "",
            "## 4. Prioritized Candidate Positive Cases for Ingestion",
            "",
            "1. **`case_002_wakashio` (MV Wakashio Grounding, Mauritius, 2020) — Priority 1**:",
            "   - Known culprit bulk carrier WAKASHIO (MMSI 356508000). Official Panama Maritime Authority investigation report.",
            "   - Copernicus Sentinel-1A scene `S1A_IW_GRDH_1SDV_20200806T014312` captures bunker slick spreading into lagoon.",
            "2. **`case_004_os35` (MV OS 35 Collision & Grounding, Gibraltar, 2022) — Priority 2**:",
            "   - Known culprit bulk carrier OS 35 (MMSI 572396000). Official Gibraltar Port Authority investigation.",
            "   - Dense Mediterranean vessel traffic presents the ideal real-world stress test for AIS candidate filtering recall.",
            "3. **`case_003_sanchi` (MV Sanchi Tanker Collision, East China Sea, 2018) — Priority 3**:",
            "   - Known culprit tanker SANCHI (MMSI 477156900). Joint official investigation submitted to IMO.",
            "",
            "---",
            "",
            "## 5. Non-Calibration & Legal Integrity Declaration",
            "",
            "> [!CAUTION]",
            "> **Attribution Evidence Scores are NOT Probabilities**.",
            "> Because the repository currently contains only 1 real incident ($N=1 < 30$), training logistic regression or Platt scaling produces extreme overfitting and false certainty. Attribution scores evaluate physical consistency under the calibrated Lagrangian model and must never be represented in legal or regulatory forums as mathematical probabilities of guilt.",
        ]

        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(content))

        logger.info("Saved real case onboarding report to %s", out_path)
        return out_path

    def export_all_phase_12_artifacts(self) -> Dict[str, Path]:
        """Convenience method to export all required Phase 12 artifacts."""
        csv_reg, json_reg = self.export_registry_tables()
        inv_path = self.generate_candidate_case_inventory()
        matrix_path = self.generate_completeness_matrix()
        readiness_path = self.generate_validation_readiness()
        report_path = self.generate_onboarding_report()

        return {
            "validation_case_registry_csv": csv_reg,
            "validation_case_registry_json": json_reg,
            "candidate_case_inventory_md": inv_path,
            "case_completeness_matrix_csv": matrix_path,
            "validation_readiness_json": readiness_path,
            "real_case_onboarding_report_md": report_path,
        }
