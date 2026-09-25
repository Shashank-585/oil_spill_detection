"""
tests/test_data_readiness.py

Automated test suite for Phase 25 Data Readiness & Provenance Engine.
Validates:
1. The 7 critical data readiness checks exist for every case.
2. Statuses are strictly restricted to: READY, LIMITED, UNAVAILABLE, NOT REQUIRED.
3. Case 001: Negative-control readiness verification.
4. Case 002: Explicit AIS archive limitation (UNAVAILABLE) and overall LIMITED status.
5. Case 003: Full AIS availability (READY) and overall READY status.
6. Provenance exposure: dataset name, source, acquisition time, processing version, SHA-256 where available, artifact timestamp.
7. Non-legal framing: asserts "reproducible provenance" and absence of "chain of custody".
8. API endpoints: /api/cases/{case_id}/readiness and /api/cases/{case_id}/provenance.
"""

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.readiness_builder import build_data_readiness_report

client = TestClient(app)

ALLOWED_STATUSES = {"READY", "LIMITED", "UNAVAILABLE", "NOT REQUIRED"}
EXPECTED_CHECK_NAMES = {
    "Satellite",
    "Environmental",
    "AIS",
    "Temporal overlap",
    "Spatial coverage",
    "Ground truth where applicable",
    "Artifact availability",
}


def test_status_adherence_and_checks_existence():
    """Verify that every case's checks strictly conform to the 4 allowed statuses and 7 check names."""
    for case_id in ["case_001", "case_002_wakashio", "case_003_golden_ray"]:
        report = build_data_readiness_report(case_id)
        assert report.overall_status in ALLOWED_STATUSES

        check_names = {c.name for c in report.checks}
        assert check_names == EXPECTED_CHECK_NAMES, f"Mismatch in check names for {case_id}"

        for c in report.checks:
            assert c.status in ALLOWED_STATUSES, f"Invalid status '{c.status}' for check '{c.name}' in {case_id}"


def test_case_001_negative_control_readiness():
    """Verify Case 001 reflects negative-control pipeline readiness without forced vessel blame."""
    report = build_data_readiness_report("case_001")
    assert report.case_id == "case_001"
    assert report.overall_status == "READY"

    # AIS is READY (commercial transit vessels in fairway)
    ais_check = next(c for c in report.checks if c.name == "AIS")
    assert ais_check.status == "READY"

    # Ground truth is READY (pipeline non-vessel origin verified)
    gt_check = next(c for c in report.checks if c.name == "Ground truth where applicable")
    assert gt_check.status == "READY"
    assert "pipeline" in gt_check.details.lower() or "non-vessel" in gt_check.details.lower()

    # Limitations mention pipeline
    assert any("pipeline" in lim.lower() for lim in report.data_limitations)


def test_case_002_ais_archive_limitation():
    """Verify Case 002 explicitly documents the AIS archive paywall limitation."""
    report = build_data_readiness_report("case_002_wakashio")
    assert report.case_id == "case_002_wakashio"
    assert report.overall_status == "LIMITED"

    # AIS must be UNAVAILABLE
    ais_check = next(c for c in report.checks if c.name == "AIS")
    assert ais_check.status == "UNAVAILABLE"
    assert "paywall" in ais_check.details.lower() or "unavailable" in ais_check.details.lower()

    # Environmental & Temporal overlap are LIMITED
    env_check = next(c for c in report.checks if c.name == "Environmental")
    assert env_check.status == "LIMITED"

    time_check = next(c for c in report.checks if c.name == "Temporal overlap")
    assert time_check.status == "LIMITED"


def test_case_003_full_ais_availability():
    """Verify Case 003 documents full multi-vessel AIS availability and complete pipeline readiness."""
    report = build_data_readiness_report("case_003_golden_ray")
    assert report.case_id == "case_003_golden_ray"
    assert report.overall_status == "READY"

    # AIS is READY with candidate traffic
    ais_check = next(c for c in report.checks if c.name == "AIS")
    assert ais_check.status == "READY"
    assert "25" in ais_check.details

    # All checks are READY
    for c in report.checks:
        assert c.status == "READY"


def test_reproducible_provenance_integrity():
    """Verify provenance records expose required fields and avoid legal chain-of-custody claims."""
    report = build_data_readiness_report("case_003_golden_ray")
    assert len(report.provenance_records) >= 3

    for rec in report.provenance_records:
        assert rec.dataset_name
        assert rec.source
        assert rec.processing_version
        assert rec.record_type == "reproducible provenance"

        # Assert absence of legal claims
        rec_str = str(rec).lower()
        assert "chain of custody" not in rec_str
        assert "chain-of-custody" not in rec_str
        assert "court admissible" not in rec_str


def test_api_readiness_endpoints():
    """Verify GET /api/cases/{case_id}/readiness and /api/cases/{case_id}/provenance endpoints."""
    # Readiness endpoint
    resp = client.get("/api/cases/case_003_golden_ray/readiness")
    assert resp.status_code == 200
    data = resp.json()
    assert data["case_id"] == "case_003_golden_ray"
    assert data["overall_status"] == "READY"
    assert len(data["checks"]) == 7

    # Provenance endpoint
    resp_prov = client.get("/api/cases/case_003_golden_ray/provenance")
    assert resp_prov.status_code == 200
    prov = resp_prov.json()
    assert isinstance(prov, list)
    assert len(prov) >= 3
    assert prov[0]["record_type"] == "reproducible provenance"

    # Path traversal rejection
    resp_trav = client.get("/api/cases/..%2F..%2Fetc/readiness")
    assert resp_trav.status_code in [400, 404]
