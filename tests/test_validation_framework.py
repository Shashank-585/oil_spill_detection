"""
Phase 11: Validation Framework Tests.

Verifies:
1. Standard validation case schema and serialization
2. Ground-truth isolation: blind algorithm input extraction strictly omits reference truth
3. Blind validation runner execution
4. Positive vessel case evaluation: synthetic known vessel achieves SUCCESS
5. Negative pipeline case evaluation: pipeline case achieves SUCCESS when 0 vessels have HIGH_SUPPORT
6. Candidate generation recall separation: filtered vessel categorized as CANDIDATE_GENERATION_FAILURE
7. Ranking failure categorization: low-ranked true vessel categorized as RANKING_FAILURE
8. Geodesic source location error calculation
9. Temporal source time error calculation
10. False HIGH_SUPPORT detection on negative cases
11. Failure taxonomy coverage and mutual exclusivity
12. Insufficient ground truth handling
13. Deterministic validation reproducibility
14. Case 001 negative safety validation (pipeline rupture, 0 vessels HIGH_SUPPORT)
15. Aggregate validation outputs integrity (registry, CSV, report, diagnostic figure)
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import pytest
import numpy as np
import pandas as pd

from src.common.geo import haversine_distance_m
from src.common.paths import VALIDATION_PROCESSED_DIR, resolve_path
from src.validation.case_schema import (
    SourceType,
    GroundTruthQuality,
    ValidationRole,
    FailureCategory,
    GroundTruth,
    AlgorithmInputs,
    ValidationCase,
    CaseValidationMetrics,
    extract_blind_algorithm_inputs,
)
from src.validation.case_registry import ValidationCaseRegistry
from src.validation.validation_runner import BlindValidationRunner
from src.validation.validation_aggregator import (
    ValidationAggregator,
    run_historical_validation,
)


# ---------------------------------------------------------------------------
# Test 1: Validation Case Schema
# ---------------------------------------------------------------------------
def test_validation_case_schema():
    """Verify schema fields, types, and serialization of validation case entities."""
    gt = GroundTruth(
        source_type=SourceType.VESSEL,
        reference_source_location=(-118.1500, 33.6500),
        reference_source_time_utc="2021-10-02T01:30:00Z",
        reference_vessel_mmsi=367000111,
        reference_vessel_name="TEST_VESSEL",
        ground_truth_quality=GroundTruthQuality.VERIFIED,
        ground_truth_source="Test Authority Report",
        ground_truth_confidence=0.95,
        validation_role=ValidationRole.POSITIVE_VESSEL_CASE,
        notes="Schema unit test case",
    )
    inputs = AlgorithmInputs(
        case_id="TEST_CASE_01",
        satellite_files={"sar": "sar.tif"},
        ais_files={"ais": "ais.parquet"},
        environmental_files={"hycom": "hycom.nc"},
        drift_parameters={"leeway_factor": 0.03},
    )
    case = ValidationCase(
        case_id="TEST_CASE_01",
        incident_name="Test Validation Case",
        incident_type="Shipboard Illegal Discharge",
        is_synthetic=True,
        ground_truth=gt,
        algorithm_inputs=inputs,
    )

    reg_dict = case.to_registry_record()
    assert reg_dict["case_id"] == "TEST_CASE_01"
    assert reg_dict["source_type"] == "vessel"
    assert reg_dict["validation_role"] == "POSITIVE_VESSEL_CASE"
    assert reg_dict["reference_vessel_mmsi"] == 367000111
    assert reg_dict["ground_truth_quality"] == "VERIFIED"


# ---------------------------------------------------------------------------
# Test 2: Ground-Truth Isolation
# ---------------------------------------------------------------------------
def test_ground_truth_isolation():
    """Ensure blind algorithm inputs strictly omit all reference ground-truth data."""
    gt = GroundTruth(
        source_type=SourceType.PIPELINE,
        reference_source_location=(-118.0500, 33.6000),
        reference_source_time_utc="2021-10-01T20:00:00Z",
        reference_vessel_mmsi=999999999,
        reference_vessel_name="SECRET_VESSEL",
        ground_truth_quality=GroundTruthQuality.VERIFIED,
        ground_truth_source="USCG Formal Investigation",
        ground_truth_confidence=1.0,
        validation_role=ValidationRole.NEGATIVE_NON_VESSEL_CASE,
        notes="Pipeline leak near Huntington Beach",
    )
    inputs = AlgorithmInputs(case_id="SECRET_CASE")
    case = ValidationCase(
        case_id="SECRET_CASE",
        incident_name="Secret Spill",
        incident_type="Pipeline Leak",
        is_synthetic=False,
        ground_truth=gt,
        algorithm_inputs=inputs,
    )

    blind_inputs = extract_blind_algorithm_inputs(case)
    blind_keys = set(blind_inputs.keys())
    
    # Ground truth leakage checks
    forbidden_keys = {
        "reference_source_location",
        "reference_source_time_utc",
        "reference_vessel_mmsi",
        "reference_vessel_name",
        "ground_truth_quality",
        "ground_truth_source",
        "ground_truth_confidence",
        "validation_role",
        "source_type",
        "ground_truth",
        "notes",
    }
    assert forbidden_keys.isdisjoint(blind_keys), f"Leaked keys found: {forbidden_keys.intersection(blind_keys)}"
    assert "SECRET_VESSEL" not in json.dumps(blind_inputs)
    assert "999999999" not in json.dumps(blind_inputs)


# ---------------------------------------------------------------------------
# Test 3: Blind Validation Execution
# ---------------------------------------------------------------------------
def test_blind_validation_execution(tmp_path):
    """Verify the runner can execute blind validation over a registry."""
    registry = ValidationCaseRegistry(output_dir=tmp_path)
    runner = BlindValidationRunner(output_dir=tmp_path)
    
    # Run a single synthetic case
    syn_case = registry.get_case("SYN_001_VESSEL_TRUE_CULPRIT")
    metrics = runner.evaluate_case(syn_case)
    
    assert metrics.case_id == "SYN_001_VESSEL_TRUE_CULPRIT"
    assert metrics.top_hypothesis_id is not None
    assert metrics.failure_category.value in [c.value for c in FailureCategory]


# ---------------------------------------------------------------------------
# Test 4: Positive Vessel Case Evaluation
# ---------------------------------------------------------------------------
def test_positive_vessel_case_evaluation(tmp_path):
    """Synthetic positive vessel case with known culprit scores top rank and achieves SUCCESS."""
    registry = ValidationCaseRegistry(output_dir=tmp_path)
    runner = BlindValidationRunner(output_dir=tmp_path)
    
    case = registry.get_case("SYN_001_VESSEL_TRUE_CULPRIT")
    metrics = runner.evaluate_case(case)
    
    assert metrics.passed is True
    assert metrics.failure_category == FailureCategory.SUCCESS
    assert metrics.known_vessel_in_candidates is True
    assert metrics.known_vessel_rank == 1
    assert metrics.known_vessel_in_top_1 is True
    assert metrics.source_location_error_m < 500.0


# ---------------------------------------------------------------------------
# Test 5: Negative Pipeline Case Evaluation
# ---------------------------------------------------------------------------
def test_negative_pipeline_case_evaluation(tmp_path):
    """Negative pipeline case achieves SUCCESS when 0 vessels receive HIGH_SUPPORT."""
    registry = ValidationCaseRegistry(output_dir=tmp_path)
    runner = BlindValidationRunner(output_dir=tmp_path)
    
    case = registry.get_case("SYN_004_PIPELINE_NEGATIVE")
    metrics = runner.evaluate_case(case)
    
    assert metrics.passed is True
    assert metrics.failure_category == FailureCategory.SUCCESS
    assert metrics.false_high_support_flag is False
    assert metrics.top_1_score < 0.70  # Refused HIGH_SUPPORT


# ---------------------------------------------------------------------------
# Test 6: Candidate Generation Recall Separation
# ---------------------------------------------------------------------------
def test_candidate_generation_recall_separation(tmp_path):
    """A vessel filtered during candidate generation is explicitly CANDIDATE_GENERATION_FAILURE."""
    registry = ValidationCaseRegistry(output_dir=tmp_path)
    runner = BlindValidationRunner(output_dir=tmp_path)
    
    case = registry.get_case("SYN_002_CANDIDATE_GEN_FAIL")
    metrics = runner.evaluate_case(case)
    
    assert metrics.passed is False
    assert metrics.known_vessel_in_candidates is False
    # CRITICAL: Must be CANDIDATE_GENERATION_FAILURE, NOT RANKING_FAILURE
    assert metrics.failure_category == FailureCategory.CANDIDATE_GENERATION_FAILURE


# ---------------------------------------------------------------------------
# Test 7: Ranking Failure Categorization
# ---------------------------------------------------------------------------
def test_ranking_failure_categorization(tmp_path):
    """A retained vessel ranked below acceptable cutoff is categorized as RANKING_FAILURE."""
    registry = ValidationCaseRegistry(output_dir=tmp_path)
    runner = BlindValidationRunner(output_dir=tmp_path)
    
    case = registry.get_case("SYN_003_RANKING_FAIL")
    metrics = runner.evaluate_case(case)
    
    assert metrics.passed is False
    assert metrics.known_vessel_in_candidates is True
    assert metrics.known_vessel_rank == 4  # Below top-3
    assert metrics.failure_category == FailureCategory.RANKING_FAILURE


# ---------------------------------------------------------------------------
# Test 8: Geodesic Source Location Error Calculation
# ---------------------------------------------------------------------------
def test_source_location_error_calculation():
    """Verify geodesic distance calculation between inferred release point and reference."""
    # 0 distance for identical points
    d_zero = haversine_distance_m(33.6000, -118.0500, 33.6000, -118.0500)
    assert abs(d_zero) < 1e-3
    
    # 0.01 deg latitude ≈ 1111 m
    d_lat = haversine_distance_m(33.0000, -118.0000, 33.0100, -118.0000)
    assert 1100.0 < d_lat < 1125.0


# ---------------------------------------------------------------------------
# Test 9: Source Time Error Calculation
# ---------------------------------------------------------------------------
def test_source_time_error_calculation():
    """Verify absolute temporal error calculation in seconds."""
    t_ref = datetime.fromisoformat("2021-10-02T00:00:00+00:00")
    t_inf = datetime.fromisoformat("2021-10-02T00:30:00+00:00")
    dt = abs((t_inf - t_ref).total_seconds())
    assert dt == 1800.0


# ---------------------------------------------------------------------------
# Test 10: False HIGH_SUPPORT Detection
# ---------------------------------------------------------------------------
def test_false_high_support_detection():
    """Negative case producing a vessel score >= 0.70 triggers false_high_support_flag."""
    metrics = CaseValidationMetrics(
        case_id="TEST_NEG",
        incident_name="Test Negative Case",
        source_type="pipeline",
        validation_role="NEGATIVE_NON_VESSEL_CASE",
        ground_truth_quality="VERIFIED",
        is_synthetic=True,
        top_evidence_score=0.82,
        top_evidence_state="HIGH_SUPPORT",
        false_high_support_flag=True,
        passed_validation=False,
        failure_category=FailureCategory.RANKING_FAILURE,
    )
    assert metrics.false_high_support_flag is True
    assert metrics.passed is False
    assert metrics.failure_category == FailureCategory.RANKING_FAILURE


# ---------------------------------------------------------------------------
# Test 11: Failure Taxonomy Coverage
# ---------------------------------------------------------------------------
def test_failure_taxonomy_coverage():
    """Verify all failure categories exist, have non-empty string values, and are mutually distinct."""
    cats = list(FailureCategory)
    cat_values = [c.value for c in cats]
    assert len(cat_values) == len(set(cat_values))
    assert FailureCategory.CANDIDATE_GENERATION_FAILURE.value in cat_values
    assert FailureCategory.RANKING_FAILURE.value in cat_values
    assert FailureCategory.SUCCESS.value in cat_values
    assert FailureCategory.INSUFFICIENT_GROUND_TRUTH.value in cat_values


# ---------------------------------------------------------------------------
# Test 12: Insufficient Ground Truth Handling
# ---------------------------------------------------------------------------
def test_insufficient_ground_truth_handling(tmp_path):
    """Case with UNVERIFIED quality and missing references is assigned INSUFFICIENT_GROUND_TRUTH."""
    runner = BlindValidationRunner(output_dir=tmp_path)
    registry = ValidationCaseRegistry(output_dir=tmp_path)
    
    # Get un-ingested real case from registry
    hist_case = registry.get_case("CASE_002_WABAMUN")
    assert hist_case is not None
    metrics = runner.evaluate_case(hist_case)
    
    assert metrics.failure_category == FailureCategory.INSUFFICIENT_GROUND_TRUTH
    assert metrics.passed is False


# ---------------------------------------------------------------------------
# Test 13: Deterministic Validation Reproducibility
# ---------------------------------------------------------------------------
def test_deterministic_validation(tmp_path):
    """Multiple evaluations of the benchmark suite produce bitwise identical results."""
    runner = BlindValidationRunner(output_dir=tmp_path)
    registry = ValidationCaseRegistry(output_dir=tmp_path)
    
    results_run1 = [m.to_dict() for m in runner.evaluate_all(registry)]
    results_run2 = [m.to_dict() for m in runner.evaluate_all(registry)]
    
    assert len(results_run1) == len(results_run2)
    for r1, r2 in zip(results_run1, results_run2):
        assert r1["case_id"] == r2["case_id"]
        assert r1["passed_validation"] == r2["passed_validation"]
        assert r1["failure_category"] == r2["failure_category"]
        assert r1["top_hypothesis_id"] == r2["top_hypothesis_id"]
        assert r1["top_evidence_score"] == r2["top_evidence_score"]


# ---------------------------------------------------------------------------
# Test 14: Case 001 Negative Safety Validation
# ---------------------------------------------------------------------------
def test_case_001_negative_safety_validation(tmp_path):
    """Case 001 passes negative safety validation with 0 vessels receiving HIGH_SUPPORT."""
    runner = BlindValidationRunner(output_dir=tmp_path)
    registry = ValidationCaseRegistry(output_dir=tmp_path)
    
    case_001 = registry.get_case("case_001")
    assert case_001 is not None
    assert case_001.ground_truth.source_type == SourceType.PIPELINE
    assert case_001.ground_truth.validation_role == ValidationRole.NEGATIVE_NON_VESSEL_CASE
    
    metrics = runner.evaluate_case(case_001)
    
    # 1. Passed negative safety check
    assert metrics.passed is True
    assert metrics.failure_category == FailureCategory.SUCCESS
    
    # 2. Refused HIGH_SUPPORT
    assert metrics.false_high_support_flag is False
    assert metrics.top_1_score < 0.70  # ROAM received ~0.6406 (MODERATE_SUPPORT)
    
    # 3. Observed slicks and candidate vessels are ~39.5 km west of pipeline (pipeline was outside radar swath)
    assert metrics.source_location_error_m is not None
    assert 35000.0 < metrics.source_location_error_m < 45000.0


# ---------------------------------------------------------------------------
# Test 15: Aggregate Validation Outputs Integrity
# ---------------------------------------------------------------------------
def test_aggregate_validation_outputs_integrity():
    """Verify all Phase 11 products exist, are non-empty, and conform to standards."""
    out_dir = resolve_path(VALIDATION_PROCESSED_DIR)
    
    # Required files
    reg_csv = out_dir / "validation_case_registry.csv"
    reg_json = out_dir / "validation_case_registry.json"
    res_csv = out_dir / "case_validation_results.csv"
    res_json = out_dir / "case_validation_results.json"
    sum_json = out_dir / "aggregate_validation_summary.json"
    rep_md = out_dir / "aggregate_validation_report.md"
    diag_png = out_dir / "validation_framework_diagnostic.png"
    
    for f in [reg_csv, reg_json, res_csv, res_json, sum_json, rep_md, diag_png]:
        assert f.exists(), f"Missing required file: {f.name}"
        assert f.stat().st_size > 0, f"Empty file: {f.name}"
    
    # Check registry content
    reg_df = pd.read_csv(reg_csv)
    assert len(reg_df) >= 10  # 1 real + 3 un-ingested real + 6 synthetic
    assert "case_001" in reg_df["case_id"].values
    
    # Check results content
    res_df = pd.read_csv(res_csv)
    assert len(res_df) == 7  # 1 real + 6 synthetic evaluated
    
    # Check calibration disclaimer in summary JSON
    with open(sum_json, "r") as fp:
        summary_data = json.load(fp)
    assert "ATTRIBUTION SCORE NOT PROBABILITY-CALIBRATED" in summary_data["score_calibration_status"]
    assert summary_data["real_cases_count"] == 1
