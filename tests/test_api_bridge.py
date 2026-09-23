"""
tests/test_api_bridge.py

Automated test suite for Phase 15.2A Read-Only FastAPI Data Bridge.
Verifies all endpoints, dataset availability detection, error codes,
path traversal rejection, and non-lossy scientific artifact delivery.
"""

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_health():
    """Verify health endpoint returns status ok."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "service" in data


def test_case_listing():
    """Verify case listing dynamically retrieves cases from data/cases/."""
    response = client.get("/api/cases")
    assert response.status_code == 200
    cases = response.json()
    assert isinstance(cases, list)
    assert len(cases) >= 3

    case_ids = [c["case_id"] for c in cases]
    assert "case_001" in case_ids
    assert "case_002_wakashio" in case_ids
    assert "case_003_golden_ray" in case_ids

    # Validate structure of a case summary
    for c in cases:
        assert "case_id" in c
        assert "name" in c
        assert "datasets_available" in c
        assert isinstance(c["datasets_available"], dict)
        assert "sar" in c["datasets_available"]
        assert "attribution" in c["datasets_available"]


def test_valid_case_lookup():
    """Verify case detail retrieval for registered cases."""
    # Case 001
    resp1 = client.get("/api/cases/case_001")
    assert resp1.status_code == 200
    c1 = resp1.json()
    assert c1["case_id"] == "case_001"
    assert "Huntington Beach" in c1["name"]
    assert c1["datasets"]["sar"] is True
    assert c1["datasets"]["slicks"] is True
    assert c1["datasets"]["attribution"] is True
    assert c1["location"]["latitude"] is not None
    assert c1["bounding_box"] is not None

    # Case 003
    resp3 = client.get("/api/cases/case_003_golden_ray")
    assert resp3.status_code == 200
    c3 = resp3.json()
    assert c3["case_id"] == "case_003_golden_ray"
    assert "Golden Ray" in c3["name"]
    assert c3["datasets"]["attribution"] is True


def test_invalid_case_lookup():
    """Verify structured 404 for unknown case ID."""
    response = client.get("/api/cases/case_nonexistent_999")
    assert response.status_code == 404
    err = response.json()["detail"]
    assert err["error"] == "CASE_NOT_FOUND"
    assert "case_nonexistent_999" in err["message"]


def test_path_traversal_rejection():
    """Verify path traversal attempts in case_id are rejected."""
    # Using URL-encoded or path segments
    response1 = client.get("/api/cases/..%2F..%2Fetc")
    assert response1.status_code in [400, 404]

    response2 = client.get("/api/cases/..")
    assert response2.status_code in [400, 404]

    response3 = client.get("/api/cases/subdir/case_001")
    assert response3.status_code in [400, 404]

    # Explicit traversal token in case_id
    response4 = client.get("/api/cases/test..traversal")
    assert response4.status_code == 400
    assert response4.json()["detail"]["error"] == "INVALID_CASE_ID"


def test_sar_stats():
    """Verify SAR statistics endpoint returns existing precalculated stats."""
    response = client.get("/api/cases/case_001/sar/stats")
    assert response.status_code == 200
    stats = response.json()
    assert "raster_metadata" in stats or "calibrated_sigma0_db" in stats

    # Case 002 has no preprocessed SAR stats -> structured 404
    resp_missing = client.get("/api/cases/case_002_wakashio/sar/stats")
    assert resp_missing.status_code == 404
    err = resp_missing.json()["detail"]
    assert err["error"] == "DATASET_NOT_AVAILABLE"


def test_slicks_geojson():
    """Verify slick geometry endpoint returns valid GeoJSON FeatureCollection."""
    response = client.get("/api/cases/case_001/slicks")
    assert response.status_code == 200
    geojson = response.json()
    assert geojson["type"] == "FeatureCollection"
    assert "features" in geojson
    assert len(geojson["features"]) > 0
    assert geojson["features"][0]["type"] == "Feature"
    assert "geometry" in geojson["features"][0]
    assert "properties" in geojson["features"][0]

    # Missing slick GeoJSON -> structured 404
    resp_missing = client.get("/api/cases/case_002_wakashio/slicks")
    assert resp_missing.status_code == 404
    assert resp_missing.json()["detail"]["error"] == "DATASET_NOT_AVAILABLE"


def test_ais_vessels():
    """Verify candidate vessels endpoint returns actual candidate list."""
    response = client.get("/api/cases/case_001/ais/vessels")
    assert response.status_code == 200
    vessels = response.json()
    assert isinstance(vessels, list)
    assert len(vessels) > 0
    v0 = vessels[0]
    assert "mmsi" in v0
    assert "vessel_name" in v0
    assert "hypothesis_count" in v0
    assert "min_distance_m" in v0

    # Case 003 Golden Ray vessels
    resp3 = client.get("/api/cases/case_003_golden_ray/ais/vessels")
    assert resp3.status_code == 200
    v3_list = resp3.json()
    assert len(v3_list) > 0
    mmsis = [v["mmsi"] for v in v3_list]
    assert 538007762 in mmsis  # Golden Ray present

    # Missing AIS data -> structured 404
    resp_missing = client.get("/api/cases/case_002_wakashio/ais/vessels")
    assert resp_missing.status_code == 404
    assert resp_missing.json()["detail"]["error"] == "DATASET_NOT_AVAILABLE"


def test_attribution_ranking():
    """Verify ranked attribution results retain backend scores and ordering."""
    # Case 001
    resp1 = client.get("/api/cases/case_001/attribution/ranking")
    assert resp1.status_code == 200
    ranking1 = resp1.json()
    assert isinstance(ranking1, list)
    assert len(ranking1) > 0
    # Confirm rank ordering 1, 2, ...
    assert ranking1[0]["vessel_rank"] == 1
    assert "best_evidence_score" in ranking1[0]
    assert "vessel_evidence_state" in ranking1[0]

    # Case 003 Golden Ray
    resp3 = client.get("/api/cases/case_003_golden_ray/attribution/ranking")
    assert resp3.status_code == 200
    ranking3 = resp3.json()
    assert len(ranking3) > 0
    # Under Phase 13 causal consistency, Golden Ray (MMSI 538007762) is Rank #1
    top_vessel = ranking3[0]
    assert top_vessel["vessel_rank"] == 1
    assert top_vessel["mmsi"] == 538007762
    assert top_vessel["best_evidence_score"] == pytest.approx(0.6891, abs=0.01)
    assert top_vessel["evidence_components"] is not None
    assert "drift_consistency" in top_vessel["evidence_components"]
    assert top_vessel["causal_precedence_status"] == "AT_RELEASE"

    # Missing attribution ranking -> structured 404
    resp_missing = client.get("/api/cases/case_002_wakashio/attribution/ranking")
    assert resp_missing.status_code == 404
    assert resp_missing.json()["detail"]["error"] == "DATASET_NOT_AVAILABLE"


def test_attribution_uncertainty():
    """Verify uncertainty analysis endpoint returns Monte Carlo audit data."""
    response = client.get("/api/cases/case_001/attribution/uncertainty")
    assert response.status_code == 200
    unc = response.json()
    assert unc["case_id"] == "case_001"
    assert "ensemble_size" in unc
    assert "calibration_audit" in unc
    assert unc["calibration_audit"]["is_probability_calibrated"] is False
    assert "mandatory_scientific_notice" in unc["calibration_audit"]

    # Case 003
    resp3 = client.get("/api/cases/case_003_golden_ray/attribution/uncertainty")
    assert resp3.status_code == 200
    unc3 = resp3.json()
    assert unc3["case_id"] == "case_003_golden_ray"
    assert len(unc3["rank_stability_top_hypotheses"]) > 0

    # Missing uncertainty -> structured 404
    resp_missing = client.get("/api/cases/case_002_wakashio/attribution/uncertainty")
    assert resp_missing.status_code == 404
    assert resp_missing.json()["detail"]["error"] == "DATASET_NOT_AVAILABLE"


def test_cors_headers():
    """Verify CORS headers permit local Vite development server origins."""
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "GET",
    }
    response = client.options("/api/cases", headers=headers)
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_sar_raster_and_visual_derivative():
    """Verify SAR raster metadata and visual derivative PNG endpoints."""
    # Case 001
    resp = client.get("/api/cases/case_001/sar/raster")
    assert resp.status_code == 200
    data = resp.json()
    assert data["case_id"] == "case_001"
    assert data["is_visualization_derivative"] is True
    assert "bounds" in data
    assert "coordinates" in data
    assert len(data["coordinates"]) == 4

    resp_img = client.get("/api/cases/case_001/sar/visual-derivative.png")
    assert resp_img.status_code == 200
    assert resp_img.headers["content-type"] == "image/png"
    assert len(resp_img.content) > 100000

    # Case 002 (unavailable)
    resp_missing = client.get("/api/cases/case_002_wakashio/sar/raster")
    assert resp_missing.status_code == 404
    assert resp_missing.json()["detail"]["error"] == "DATASET_NOT_AVAILABLE"


def test_hypotheses_geojson():
    """Verify 4D source hypotheses GeoJSON endpoint."""
    resp = client.get("/api/cases/case_001/hypotheses")
    assert resp.status_code == 200
    geojson = resp.json()
    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) > 0
    f0 = geojson["features"][0]
    assert f0["geometry"]["type"] == "Point"
    assert "hypothesis_id" in f0["properties"]

    # Case 003
    resp3 = client.get("/api/cases/case_003_golden_ray/hypotheses")
    assert resp3.status_code == 200
    assert len(resp3.json()["features"]) > 0

    # Case 002 (unavailable)
    resp_missing = client.get("/api/cases/case_002_wakashio/hypotheses")
    assert resp_missing.status_code == 404
    assert resp_missing.json()["detail"]["error"] == "DATASET_NOT_AVAILABLE"


def test_ais_tracks():
    """Verify candidate vessel AIS trajectory LineStrings endpoint."""
    resp = client.get("/api/cases/case_001/ais/tracks")
    assert resp.status_code == 200
    fc = resp.json()
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) > 0
    f0 = fc["features"][0]
    assert f0["geometry"]["type"] == "LineString"
    assert "mmsi" in f0["properties"]
    assert "vessel_name" in f0["properties"]

    # Case 003
    resp3 = client.get("/api/cases/case_003_golden_ray/ais/tracks")
    assert resp3.status_code == 200
    mmsis = [f["properties"]["mmsi"] for f in resp3.json()["features"]]
    assert 538007762 in mmsis  # Golden Ray present

    # Case 002 (unavailable)
    resp_missing = client.get("/api/cases/case_002_wakashio/ais/tracks")
    assert resp_missing.status_code == 404
    assert resp_missing.json()["detail"]["error"] == "DATASET_NOT_AVAILABLE"


def test_drift_trajectories():
    """Verify backward drift trajectory ensemble LineStrings endpoint."""
    resp = client.get("/api/cases/case_001/drift/trajectories")
    assert resp.status_code == 200
    fc = resp.json()
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) > 0
    f0 = fc["features"][0]
    assert f0["geometry"]["type"] == "LineString"
    assert "candidate_slick_id" in f0["properties"]

    # Case 003
    resp3 = client.get("/api/cases/case_003_golden_ray/drift/trajectories")
    assert resp3.status_code == 200
    assert len(resp3.json()["features"]) > 0

    # Case 002 (unavailable)
    resp_missing = client.get("/api/cases/case_002_wakashio/drift/trajectories")
    assert resp_missing.status_code == 404
    assert resp_missing.json()["detail"]["error"] == "DATASET_NOT_AVAILABLE"


def test_spill_comparisons():
    """Verify forward simulation spill comparisons endpoint."""
    # Case 001
    resp1 = client.get("/api/cases/case_001/attribution/spill-comparisons")
    assert resp1.status_code == 200
    list1 = resp1.json()
    assert isinstance(list1, list)
    assert len(list1) > 0
    assert "hypothesis_id" in list1[0]
    assert "iou" in list1[0]

    # Case 003
    resp3 = client.get("/api/cases/case_003_golden_ray/attribution/spill-comparisons")
    assert resp3.status_code == 200
    list3 = resp3.json()
    assert len(list3) > 0

    # Filter by hypothesis_id
    hid = list3[0]["hypothesis_id"]
    resp_filt = client.get(f"/api/cases/case_003_golden_ray/attribution/spill-comparisons?hypothesis_id={hid}")
    assert resp_filt.status_code == 200
    assert len(resp_filt.json()) >= 1
    assert resp_filt.json()[0]["hypothesis_id"] == hid

    # Case 002 (unavailable)
    resp_missing = client.get("/api/cases/case_002_wakashio/attribution/spill-comparisons")
    assert resp_missing.status_code == 404
    assert resp_missing.json()["detail"]["error"] == "DATASET_NOT_AVAILABLE"


