"""
tests/test_satellite_observation.py

Tests for Phase 26: Satellite Observation Metadata Upgrade.
Verifies:
1. Operational Sentinel-1 metadata (channel actually used by detector is strictly VV).
2. Supporting Sentinel-2 optical metadata (only present for Case 002 Wakashio, never fake).
3. Observation timeline with pre-event, incident reference, and post-event milestones.
4. Revisit context distinguishing geometric pass opportunity from actual acquired product.
5. FastAPI endpoint GET /api/cases/{case_id}/satellite/observations.
"""

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.satellite_builder import build_satellite_observation_package


@pytest.fixture
def client():
    return TestClient(app)


def test_sentinel1_metadata_and_detector_channel():
    """Verify Sentinel-1 metadata accurately exposes the VV operational channel used by the detector."""
    pkg = build_satellite_observation_package("case_001")
    s1 = pkg.sentinel1

    assert s1.platform.startswith("Sentinel-1")
    assert "C-SAR" in s1.sensor
    assert s1.mode.startswith("IW")
    assert s1.product_type.startswith("GRDH")
    assert s1.polarization_used == "VV"
    assert "detector" in s1.polarization_explanation.lower()
    assert "Bragg" in s1.polarization_explanation or "contrast" in s1.polarization_explanation
    assert "VV" in s1.polarizations_available
    assert s1.processing_status in ["CALIBRATED_AND_DETECTED", "CALIBRATED_BENCHMARK"]
    assert s1.speckle_filter is not None
    assert "CFAR" in s1.cfar_detector_info


def test_sentinel2_presence_in_wakashio_case():
    """Verify Case 002 Wakashio includes verified supporting Sentinel-2 optical observation with non-operational disclaimer."""
    pkg = build_satellite_observation_package("case_002_wakashio")
    s2 = pkg.sentinel2

    assert s2 is not None
    assert s2.available is True
    assert s2.platform == "Sentinel-2B"
    assert "MSI" in s2.sensor
    assert s2.acquisition_time_utc.startswith("2020-08-06")
    assert s2.role == "Supporting optical observation"
    assert "not ingested by the operational" in s2.pipeline_usage_disclaimer.lower()
    assert s2.cloud_cover_percentage is not None
    assert len(s2.available_bands) >= 3


def test_sentinel2_absence_in_cases_without_optical():
    """Verify Case 001 and Case 003 do not fake Sentinel-2 processing or claim optical attribution."""
    for case_id in ["case_001", "case_003_golden_ray"]:
        pkg = build_satellite_observation_package(case_id)
        s2 = pkg.sentinel2

        assert s2 is not None
        assert s2.available is False
        assert "not ingested" in s2.pipeline_usage_disclaimer.lower() or "no supporting" in s2.pipeline_usage_disclaimer.lower()
        # Verify no fake claim that S2 contributed to detection or attribution
        assert "exclusively" in s2.pipeline_usage_disclaimer.lower() or "not active" in s2.pipeline_usage_disclaimer.lower()


def test_observation_timeline_structure():
    """Verify timeline contains pre-event, incident reference, and operational SAR events in chronological order."""
    pkg = build_satellite_observation_package("case_002_wakashio")
    timeline = pkg.timeline

    assert timeline.incident_time_utc is not None
    assert timeline.operational_observation_time_utc is not None
    assert len(timeline.events) >= 3

    event_types = [e.event_type for e in timeline.events]
    assert "PRE_EVENT" in event_types
    assert "INCIDENT_REFERENCE" in event_types
    assert "OPERATIONAL_SAR" in event_types
    assert "SUPPORTING_OPTICAL" in event_types

    # Chronological sort check
    hours = [e.relative_to_incident_hours for e in timeline.events]
    assert hours == sorted(hours)

    # Reference time has 0.0 relative hours
    t0_evt = next(e for e in timeline.events if e.event_type == "INCIDENT_REFERENCE")
    assert t0_evt.relative_to_incident_hours == 0.0


def test_revisit_context_distinction():
    """Verify revisit context clearly distinguishes orbital opportunity from actual acquired product."""
    pkg = build_satellite_observation_package("case_001")
    revisit = pkg.revisit_context

    assert revisit.constellation_nominal_repeat_days == 12
    assert "orbital revisit opportunity" in revisit.revisit_distinction_notice.lower()
    assert "actual acquired" in revisit.revisit_distinction_notice.lower()


def test_api_satellite_observations_endpoint(client):
    """Verify GET /api/cases/{case_id}/satellite/observations delivers full package."""
    resp = client.get("/api/cases/case_001/satellite/observations")
    assert resp.status_code == 200
    data = resp.json()

    assert data["case_id"] == "case_001"
    assert data["sentinel1"]["polarization_used"] == "VV"
    assert "timeline" in data
    assert "revisit_context" in data

    # Test Case 002
    resp2 = client.get("/api/cases/case_002_wakashio/satellite/observations")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["sentinel2"]["available"] is True
    assert data2["sentinel2"]["platform"] == "Sentinel-2B"
