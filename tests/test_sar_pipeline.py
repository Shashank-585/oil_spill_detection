"""
tests/test_sar_pipeline.py

Comprehensive tests for Phase 5: SAR Observation Processing Pipeline.
Covers:
1. Input validation & error handling
2. Metadata extraction & observation abstraction
3. Radiometric calibration & speckle noise configuration
4. Dark-spot detection & object filtering results
5. Job lifecycle and progress tracking
6. Observation provenance chain (6 stages)
7. Detector interface & future ML integration stub
8. FastAPI endpoints
"""

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.sar_pipeline.engine import (
    execute_sar_processing_job,
    get_sar_job,
    get_sar_job_results,
    get_sar_observation_detail,
    get_sar_observations_for_case,
)
from backend.sar_pipeline.validator import validate_sar_artifact
from src.detection.interface import (
    DeterministicThresholdDetector,
    MLDetectorInterface,
    get_registered_detector,
)


@pytest.fixture
def client():
    return TestClient(app)


# 1. Validation & Input Abstraction Tests
def test_sar_input_validation_golden_ray():
    """Verify SAR input validation passes on Case 003 Golden Ray with all 8 checks."""
    res = validate_sar_artifact("case_003_golden_ray")
    assert res.is_valid is True
    assert res.overall_status == "READY_FOR_PROCESSING"
    assert len(res.checks) >= 8

    check_ids = [c.check_id for c in res.checks]
    assert "FILE_EXISTS" in check_ids
    assert "RASTER_READABLE" in check_ids
    assert "CRS_VALID" in check_ids
    assert "DIMENSIONS_VALID" in check_ids
    assert "GEOGRAPHIC_EXTENT" in check_ids
    assert "NUMERICAL_PIXEL_VALUES" in check_ids
    assert "OPERATIONAL_POLARIZATION" in check_ids
    assert "ACQUISITION_METADATA" in check_ids

    # Check operational polarization specifically
    pol_check = next(c for c in res.checks if c.check_id == "OPERATIONAL_POLARIZATION")
    assert pol_check.passed is True
    assert "VV" in pol_check.message


def test_sar_input_validation_failure_handling():
    """Verify SAR input validation explicitly catches nonexistent case without crashing."""
    res = validate_sar_artifact("case_nonexistent_999")
    assert res.is_valid is False
    assert res.overall_status == "VALIDATION_FAILED"
    assert len(res.checks) > 0
    assert any(not c.passed for c in res.checks)


def test_sar_observations_discovery():
    """Verify observation abstraction exposes operational Sentinel-1 VV channel."""
    obs_list = get_sar_observations_for_case("case_003_golden_ray")
    assert len(obs_list) >= 1

    s1_obs = obs_list[0]
    assert s1_obs.platform.startswith("Sentinel-1")
    assert s1_obs.polarization == "VV"
    assert s1_obs.is_operational is True
    assert s1_obs.role == "Operational detection channel"
    assert s1_obs.acquisition_mode == "IW"
    assert s1_obs.product_type == "GRDH"
    assert "width" in s1_obs.raster_dimensions
    assert len(s1_obs.geographic_bounds) == 4


def test_supporting_optical_distinction_in_case_002():
    """Verify Sentinel-2 optical observation in Case 002 is marked non-operational."""
    obs_list = get_sar_observations_for_case("case_002_wakashio")
    assert len(obs_list) == 2

    # First is operational SAR
    assert obs_list[0].is_operational is True
    assert obs_list[0].polarization == "VV"

    # Second is supporting optical
    s2_obs = obs_list[1]
    assert s2_obs.is_operational is False
    assert "supporting optical observation" in s2_obs.role.lower()
    assert s2_obs.polarization == "OPTICAL_RGB_NIR"


# 2. Processing Job Lifecycle & Provenance Tests
def test_sar_processing_job_execution():
    """Verify end-to-end job execution runs across all 7 stages and outputs real case data."""
    job = execute_sar_processing_job("case_003_golden_ray")
    assert job.job_id.startswith("job_sar_case_003_golden_ray")
    assert job.current_stage == "COMPLETE"
    assert len(job.stages) == 7

    stage_ids = [s.stage_id for s in job.stages]
    assert "INPUT_VALIDATION" in stage_ids
    assert "RADIOMETRIC_CALIBRATION" in stage_ids
    assert "SPECKLE_FILTER" in stage_ids
    assert "DARK_SPOT_DETECTION" in stage_ids
    assert "OBJECT_FILTERING" in stage_ids
    assert "VECTORIZATION" in stage_ids
    assert "GEOSPATIAL_OVERLAY" in stage_ids

    # Calibration stage must explicitly identify CALIBRATED INPUT
    cal_stage = next(s for s in job.stages if s.stage_id == "RADIOMETRIC_CALIBRATION")
    assert "CALIBRATED INPUT" in cal_stage.details

    # Check output artifacts
    assert "candidate_slicks_geojson" in job.output_artifacts
    assert "calibrated_sigma0_db" in job.output_artifacts


def test_sar_provenance_chain_structure():
    """Verify 6-step provenance chain from Source to Attribution."""
    res = get_sar_job_results(execute_sar_processing_job("case_003_golden_ray").job_id)
    assert res is not None
    assert res.status == "COMPLETE"
    assert len(res.provenance_chain) == 6

    stages = [p.stage for p in res.provenance_chain]
    assert stages == ["SOURCE", "CALIBRATION", "FILTER", "DETECTION", "VECTORIZATION", "ATTRIBUTION"]

    # Golden Ray real scientific detection count check
    assert res.detection.total_candidates == 207
    assert res.detection.accepted_candidates == 6
    assert res.detection.rejected_candidates == 201


# 3. Detector Interface & Future ML Decoupling Tests
def test_detector_interface_deterministic():
    """Verify DeterministicThresholdDetector is operational default."""
    det = get_registered_detector("deterministic")
    assert isinstance(det, DeterministicThresholdDetector)
    info = det.get_detector_info()
    assert info["type"] == "CLASSICAL_DETERMINISTIC"
    assert info["status"] == "OPERATIONAL_DEFAULT"
    assert info["polarization"] == "VV"


def test_detector_interface_ml_stub():
    """Verify MLDetectorInterface is prepared and strictly does not fabricate predictions."""
    ml_det = get_registered_detector("ml")
    assert isinstance(ml_det, MLDetectorInterface)
    info = ml_det.get_detector_info()
    assert info["type"] == "DEEP_LEARNING_FUTURE_EXTENSION"
    assert info["status"] == "INTERFACE_PREPARED_MODEL_UNCONNECTED"

    # Execution must raise NotImplementedError with explanatory scientific message
    with pytest.raises(NotImplementedError) as exc_info:
        ml_det.detect(None, None, None, "", "case_003_golden_ray")
    assert "MLDetectorInterface is a prepared integration point" in str(exc_info.value)


# 4. API Endpoint Integration Tests
def test_api_satellite_observations_extended(client):
    """Verify GET /api/cases/{case_id}/satellite/observations includes observations list."""
    resp = client.get("/api/cases/case_003_golden_ray/satellite/observations")
    assert resp.status_code == 200
    data = resp.json()
    assert "observations" in data
    assert len(data["observations"]) >= 1
    assert data["observations"][0]["polarization"] == "VV"


def test_api_satellite_observation_detail(client):
    """Verify GET /api/cases/{case_id}/satellite/observations/{observation_id}."""
    resp = client.get("/api/cases/case_003_golden_ray/satellite/observations/s1_case_003_golden_ray_vv")
    assert resp.status_code == 200
    data = resp.json()
    assert data["observation_id"] == "s1_case_003_golden_ray_vv"
    assert data["polarization"] == "VV"
    assert data["validation_status"] == "READY_FOR_PROCESSING"


def test_api_satellite_validation_endpoint(client):
    """Verify GET /api/cases/{case_id}/satellite/validation returns structured checks."""
    resp = client.get("/api/cases/case_003_golden_ray/satellite/validation")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_valid"] is True
    assert data["overall_status"] == "READY_FOR_PROCESSING"
    assert len(data["checks"]) >= 8


def test_api_satellite_process_and_job_lifecycle(client):
    """Verify POST /api/cases/{case_id}/satellite/process, GET /api/satellite/jobs/{id}, and GET .../results."""
    post_resp = client.post("/api/cases/case_003_golden_ray/satellite/process", json={"reprocess": False})
    assert post_resp.status_code == 200
    job = post_resp.json()
    assert "job_id" in job
    job_id = job["job_id"]
    assert job["current_stage"] == "COMPLETE"

    # Poll Job
    job_resp = client.get(f"/api/satellite/jobs/{job_id}")
    assert job_resp.status_code == 200
    assert job_resp.json()["job_id"] == job_id

    # Poll Results & Provenance
    res_resp = client.get(f"/api/satellite/jobs/{job_id}/results")
    assert res_resp.status_code == 200
    res_data = res_resp.json()
    assert res_data["status"] == "COMPLETE"
    assert res_data["detection"]["total_candidates"] == 207
    assert len(res_data["provenance_chain"]) == 6
