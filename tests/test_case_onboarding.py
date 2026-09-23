"""
Phase 12: Real Historical Case Onboarding and Readiness Tests.

Verifies:
1. Case schema extensions and quality levels (A, B, C, D)
2. Algorithm inputs and ground truth strict separation
3. Case data completeness evaluation across the 4 pillars
4. Positive vessel case eligibility and candidate profile
5. Negative pipeline safety case retention (Case 001)
6. Missing data handling and feasibility auditing
7. Blind pipeline execution interface (runner.run)
8. Post-hoc ground-truth evaluation interface (runner.evaluate)
9. Strict segregation between synthetic benchmarks and real-world incidents
10. Validation readiness logic and acquisition requirement reporting
"""

import json
from pathlib import Path
import pytest
import pandas as pd

from src.common.paths import VALIDATION_PROCESSED_DIR, resolve_path
from src.validation.case_schema import (
    SourceType,
    GroundTruthQuality,
    CaseQualityLevel,
    ValidationEligibility,
    CaseStatus,
    ValidationRole,
    FailureCategory,
    GroundTruth,
    AlgorithmInputs,
    ValidationCase,
    extract_blind_algorithm_inputs,
)
from src.validation.case_completeness import (
    CaseCompletenessEvaluator,
    CaseCompletenessRecord,
)
from src.validation.case_onboarding import CaseOnboardingWorkflow
from src.validation.case_registry import ValidationCaseRegistry
from src.validation.validation_runner import BlindValidationRunner


# ---------------------------------------------------------------------------
# Test 1: Case Schema & Quality Levels
# ---------------------------------------------------------------------------
def test_case_schema_quality_levels():
    """Verify Quality Levels A-D, CaseStatus, and ValidationEligibility enums."""
    assert CaseQualityLevel.A.value == "A"
    assert CaseQualityLevel.B.value == "B"
    assert CaseQualityLevel.C.value == "C"
    assert CaseQualityLevel.D.value == "D"

    assert CaseStatus.VERIFIED_AVAILABLE.value == "VERIFIED_AVAILABLE"
    assert CaseStatus.POTENTIALLY_AVAILABLE.value == "POTENTIALLY_AVAILABLE"
    assert CaseStatus.NOT_VERIFIED.value == "NOT_VERIFIED"

    assert ValidationEligibility.ELIGIBLE.value == "ELIGIBLE"
    assert ValidationEligibility.PARTIALLY_ELIGIBLE.value == "PARTIALLY_ELIGIBLE"
    assert ValidationEligibility.INELIGIBLE_MISSING_DATA.value == "INELIGIBLE_MISSING_DATA"

    # Test auto-alignment in GroundTruth
    gt_a = GroundTruth(source_type=SourceType.VESSEL, ground_truth_quality=GroundTruthQuality.VERIFIED)
    assert gt_a.quality_level == CaseQualityLevel.A

    gt_b = GroundTruth(source_type=SourceType.VESSEL, ground_truth_quality=GroundTruthQuality.PROBABLE)
    assert gt_b.quality_level == CaseQualityLevel.B

    gt_c = GroundTruth(source_type=SourceType.UNKNOWN, ground_truth_quality=GroundTruthQuality.UNVERIFIED)
    assert gt_c.quality_level == CaseQualityLevel.C


# ---------------------------------------------------------------------------
# Test 2: Algorithm Inputs vs Ground Truth Strict Separation
# ---------------------------------------------------------------------------
def test_algorithm_ground_truth_separation():
    """Ensure blind algorithm inputs strictly omit all reference ground-truth data."""
    gt = GroundTruth(
        source_type=SourceType.VESSEL,
        reference_source_location=(57.74, -20.44),
        reference_source_time_utc="2020-08-06T04:00:00Z",
        reference_vessel_mmsi=356508000,
        reference_vessel_name="WAKASHIO",
        ground_truth_quality=GroundTruthQuality.VERIFIED,
        quality_level=CaseQualityLevel.A,
        ground_truth_source="Panama Maritime Authority Investigation",
        validation_role=ValidationRole.POSITIVE_VESSEL_CASE,
    )
    inputs = AlgorithmInputs(
        case_id="case_002_wakashio",
        satellite_files={"sar": "measurement.tif"},
        ais_files={"ais": "traffic.csv"},
    )
    case = ValidationCase(
        case_id="case_002_wakashio",
        incident_name="MV Wakashio Grounding",
        incident_type="bulk_carrier_grounding",
        is_synthetic=False,
        ground_truth=gt,
        algorithm_inputs=inputs,
    )

    blind_inputs = extract_blind_algorithm_inputs(case)
    
    # Assert ground truth fields are completely absent
    assert "reference_vessel_mmsi" not in blind_inputs
    assert "reference_vessel_name" not in blind_inputs
    assert "reference_source_location" not in blind_inputs
    assert "reference_source_time_utc" not in blind_inputs
    assert "ground_truth_source" not in blind_inputs
    assert "ground_truth" not in blind_inputs
    assert "WAKASHIO" not in json.dumps(blind_inputs)
    assert "356508000" not in json.dumps(blind_inputs)


# ---------------------------------------------------------------------------
# Test 3: Case Data Completeness Evaluation
# ---------------------------------------------------------------------------
def test_case_completeness_evaluation(tmp_path):
    """Verify CaseCompletenessEvaluator computes 4-pillar scores and overall score."""
    registry = ValidationCaseRegistry(output_dir=tmp_path)
    evaluator = CaseCompletenessEvaluator(output_dir=tmp_path)

    case_001 = registry.get_case("case_001")
    rec_001 = evaluator.evaluate_case(case_001)

    assert rec_001.case_id == "case_001"
    assert rec_001.quality_level == "A"
    assert rec_001.satellite_pillar_score == 1.0
    assert rec_001.ais_pillar_score == 1.0
    assert rec_001.ground_truth_pillar_score == 1.0
    assert rec_001.overall_completeness_score >= 0.75
    assert rec_001.validation_eligibility == "ELIGIBLE"

    # Test candidate un-ingested case
    case_wakashio = registry.get_case("case_002_wakashio")
    rec_wakashio = evaluator.evaluate_case(case_wakashio)
    assert rec_wakashio.satellite_raster_available is False
    assert rec_wakashio.ais_data_available is False
    assert "Satellite SAR GRD raster" in rec_wakashio.missing_data_summary


# ---------------------------------------------------------------------------
# Test 4: Positive Vessel Case Eligibility
# ---------------------------------------------------------------------------
def test_positive_case_eligibility(tmp_path):
    """Verify candidate positive case requirements and potential availability."""
    registry = ValidationCaseRegistry(output_dir=tmp_path)
    case = registry.get_case("case_002_wakashio")

    assert case.is_synthetic is False
    assert case.ground_truth.source_type == SourceType.VESSEL
    assert case.ground_truth.quality_level == CaseQualityLevel.A
    assert case.ground_truth.reference_vessel_mmsi == 356508000
    assert case.case_status == CaseStatus.POTENTIALLY_AVAILABLE
    # Ineligible until local files are downloaded
    assert case.validation_eligibility == ValidationEligibility.INELIGIBLE_MISSING_DATA


# ---------------------------------------------------------------------------
# Test 5: Negative Case Eligibility
# ---------------------------------------------------------------------------
def test_negative_case_eligibility(tmp_path):
    """Verify Case 001 retention as an eligible negative pipeline safety case."""
    registry = ValidationCaseRegistry(output_dir=tmp_path)
    case_001 = registry.get_case("case_001")

    assert case_001.is_synthetic is False
    assert case_001.ground_truth.source_type == SourceType.PIPELINE
    assert case_001.ground_truth.validation_role == ValidationRole.NEGATIVE_NON_VESSEL_CASE
    assert case_001.case_status == CaseStatus.VERIFIED_AVAILABLE
    assert case_001.validation_eligibility == ValidationEligibility.ELIGIBLE
    assert case_001.culprit_vessel_available is False  # Non-vessel


# ---------------------------------------------------------------------------
# Test 6: Missing Data Handling & Feasibility Checks
# ---------------------------------------------------------------------------
def test_missing_data_handling(tmp_path):
    """Workflow flags missing files and rejects incomplete cases."""
    workflow = CaseOnboardingWorkflow(cases_dir=tmp_path)

    # Empty dictionary representing missing files
    empty_dict = {
        "satellite": {"files": {"measurement_raster_vv": "nonexistent_sat.tif"}},
        "ais": {"files": {"filtered_csv": "nonexistent_ais.csv"}},
        "environmental": {"wind": {"files": {"csv_path": "nonexistent_wind.csv"}}},
    }
    feasibility = workflow.check_data_feasibility(empty_dict)

    assert feasibility["all_files_present"] is False
    assert feasibility["satellite_file_present"] is False
    assert feasibility["ais_file_present"] is False
    assert len(feasibility["feasibility_issues"]) > 0


# ---------------------------------------------------------------------------
# Test 7: Blind Pipeline Run Interface
# ---------------------------------------------------------------------------
def test_blind_pipeline_run_interface(tmp_path):
    """BlindValidationRunner.run() operates without accessing ground truth."""
    runner = BlindValidationRunner(output_dir=tmp_path)
    registry = ValidationCaseRegistry(output_dir=tmp_path)

    case_001 = registry.get_case("case_001")
    prediction = runner.run(case_001.case_id, case=case_001)

    assert prediction["case_id"] == "case_001"
    assert prediction["execution_status"] == "SUCCESS"
    assert "top_vessel_name" in prediction
    assert "top_evidence_score" in prediction
    assert "candidate_mmsis" in prediction
    assert len(prediction["candidate_mmsis"]) > 0
    # Ground truth reference fields must NOT be in prediction
    assert "reference_source_location" not in prediction
    assert "ground_truth_quality" not in prediction


# ---------------------------------------------------------------------------
# Test 8: Post-Hoc Ground-Truth Evaluate Interface
# ---------------------------------------------------------------------------
def test_post_hoc_ground_truth_evaluate_interface(tmp_path):
    """BlindValidationRunner.evaluate() evaluates predictions post-hoc against ground truth."""
    runner = BlindValidationRunner(output_dir=tmp_path)
    registry = ValidationCaseRegistry(output_dir=tmp_path)

    case_001 = registry.get_case("case_001")
    prediction = runner.run(case_001.case_id, case=case_001)
    metrics = runner.evaluate(case_001.case_id, prediction, case=case_001)

    assert metrics.case_id == "case_001"
    assert metrics.passed is True
    assert metrics.failure_category == FailureCategory.SUCCESS
    assert metrics.false_high_support_flag is False
    assert metrics.source_location_error_m is not None


# ---------------------------------------------------------------------------
# Test 9: Synthetic vs Real Case Separation
# ---------------------------------------------------------------------------
def test_synthetic_real_case_separation(tmp_path):
    """Synthetic cases are strictly segregated from real-world metrics."""
    registry = ValidationCaseRegistry(output_dir=tmp_path)
    real_cases = registry.list_cases(exclude_synthetic=True)
    all_cases = registry.list_cases(exclude_synthetic=False)

    for rc in real_cases:
        assert rc.is_synthetic is False

    synthetic_cases = [c for c in all_cases if c.is_synthetic]
    assert len(synthetic_cases) == 6
    for sc in synthetic_cases:
        assert sc.is_synthetic is True
        assert "Synthetic Benchmark" in sc.incident_name


# ---------------------------------------------------------------------------
# Test 10: Validation Readiness Logic
# ---------------------------------------------------------------------------
def test_validation_readiness_logic():
    """Verify validation_readiness.json reports BLOCKED_PENDING_POSITIVE_REAL_CASE_DATA."""
    out_dir = resolve_path(VALIDATION_PROCESSED_DIR)
    readiness_path = out_dir / "validation_readiness.json"
    assert readiness_path.exists(), "validation_readiness.json not found"

    with open(readiness_path, "r", encoding="utf-8") as f:
        readiness = json.load(f)

    assert readiness["status"] == "BLOCKED_PENDING_POSITIVE_REAL_CASE_DATA"
    assert readiness["ready_for_positive_real_case_validation"] is False
    assert readiness["inventory_statistics"]["locally_available_positive_vessel_cases"] == 0
    assert readiness["inventory_statistics"]["locally_available_negative_cases"] == 1
    assert len(readiness["missing_positive_data_requirements"]) >= 2
    assert readiness["guardrails"]["synthetic_mixing_permitted"] is False
    assert readiness["guardrails"]["score_calibration_permitted"] is False
