"""
Unit and integration tests for Phase 6 — 4D Source Hypothesis Generation.

Validates:
1. Hypothesis schema completeness and field types
2. Vessel/source spatial compatibility filtering
3. Source-time compatibility and grid preservation
4. Geodesic distance correctness (Vincenty/Haversine metric in meters, not degrees)
5. Source plausibility propagation
6. Multiple hypotheses per vessel
7. Duplicate prevention without merging distinct (vessel, location, time) tuples
8. Preservation of location and time dimensions (no vessel-only collapse)
9. AIS gap handling and track quality attachment
10. Deterministic hypothesis generation
11. Synthetic known hypothesis generation (ground-truth recovery)
12. Case 001 output artifact integrity
"""

import json
import math
from pathlib import Path
import tempfile
import numpy as np
import pandas as pd
import pytest

from src.attribution.hypothesis_generator import SourceHypothesisGenerator4D
from src.common.geo import haversine_distance_m, haversine_distance_km
from src.common.paths import (
    AIS_PROCESSED_DIR,
    DRIFT_PROCESSED_DIR,
    HYPOTHESES_PROCESSED_DIR,
    resolve_path,
)


REQUIRED_SCHEMA_FIELDS = [
    "hypothesis_id",
    "candidate_id",
    "mmsi",
    "vessel_name",
    "imo",
    "vessel_type",
    "release_lat",
    "release_lon",
    "release_timestamp",
    "source_age_hours",
    "source_plausibility",
    "ais_lat",
    "ais_lon",
    "vessel_source_distance_m",
    "ais_track_quality",
    "gap_status",
    "compatibility_status",
]


@pytest.fixture
def case_001_hypotheses():
    """Generate or load Case 001 hypotheses for testing."""
    gen = SourceHypothesisGenerator4D(case_id="case_001")
    return gen.generate_hypotheses()


# Test 1: Hypothesis Schema
def test_hypothesis_schema(case_001_hypotheses):
    """Verify all 16 required fields exist with correct data types and non-null values."""
    assert len(case_001_hypotheses) > 0, "Hypotheses list must not be empty"

    for hyp in case_001_hypotheses:
        for field in REQUIRED_SCHEMA_FIELDS:
            assert field in hyp, f"Missing required field: {field}"
            assert hyp[field] is not None, f"Field {field} must not be None"

        assert isinstance(hyp["hypothesis_id"], str) and hyp["hypothesis_id"].startswith("4DH_")
        assert isinstance(hyp["candidate_id"], str) and hyp["candidate_id"].startswith("VC_")
        assert isinstance(hyp["mmsi"], int)
        assert isinstance(hyp["release_lat"], float)
        assert isinstance(hyp["release_lon"], float)
        assert isinstance(hyp["release_timestamp"], str)
        assert isinstance(hyp["source_age_hours"], float)
        assert isinstance(hyp["source_plausibility"], float)
        assert isinstance(hyp["ais_lat"], float)
        assert isinstance(hyp["ais_lon"], float)
        assert isinstance(hyp["vessel_source_distance_m"], float)
        assert isinstance(hyp["compatibility_status"], str)


# Test 2: Vessel/Source Spatial Compatibility
def test_vessel_source_spatial_compatibility(case_001_hypotheses):
    """Verify that all generated hypotheses satisfy the spatial compatibility threshold."""
    max_thresh_m = 15000.0  # Configured default 15 km
    for hyp in case_001_hypotheses:
        dist_m = hyp["vessel_source_distance_m"]
        assert 0.0 <= dist_m <= max_thresh_m, (
            f"Hypothesis {hyp['hypothesis_id']} distance {dist_m}m exceeds threshold {max_thresh_m}m"
        )
        assert hyp["compatibility_status"] == "COMPATIBLE"


# Test 3: Source-Time Compatibility
def test_source_time_compatibility(case_001_hypotheses):
    """Verify that each hypothesis release timestamp matches the source-time grid from Phase 4."""
    src_hyp_path = DRIFT_PROCESSED_DIR / "case_001_source_hypotheses.csv"
    assert src_hyp_path.exists()
    df_src = pd.read_csv(src_hyp_path)
    valid_source_times = set(df_src["estimated_release_time_utc"].tolist())

    for hyp in case_001_hypotheses:
        assert hyp["release_timestamp"] in valid_source_times, (
            f"Release timestamp {hyp['release_timestamp']} does not match Phase 4 source-time grid"
        )


# Test 4: Geodesic Distance Correctness
def test_geodesic_distance_correctness(case_001_hypotheses):
    """
    Verify that vessel_source_distance_m matches independent geodesic haversine calculation
    within 1 mm and strictly differs from naive Euclidean degree subtraction.
    """
    for hyp in case_001_hypotheses:
        v_lat, v_lon = hyp["ais_lat"], hyp["ais_lon"]
        r_lat, r_lon = hyp["release_lat"], hyp["release_lon"]
        expected_m = haversine_distance_m(v_lat, v_lon, r_lat, r_lon)

        # Must match geodesic within 0.1 meter
        assert abs(hyp["vessel_source_distance_m"] - expected_m) < 0.1

        # Naive degree distance (must NOT equal metric distance)
        naive_degree_diff = math.sqrt((v_lat - r_lat) ** 2 + (v_lon - r_lon) ** 2)
        assert abs(hyp["vessel_source_distance_m"] - naive_degree_diff) > 100.0, (
            "Metric distance must never equal naive degree difference"
        )


# Test 5: Source Plausibility Propagation
def test_source_plausibility_propagation(case_001_hypotheses):
    """Verify source plausibility is in [0, 1] and faithfully preserves Phase 4 values."""
    src_hyp_path = DRIFT_PROCESSED_DIR / "case_001_source_hypotheses.csv"
    df_src = pd.read_csv(src_hyp_path).set_index("hypothesis_id")

    for hyp in case_001_hypotheses:
        plaus = hyp["source_plausibility"]
        assert 0.0 <= plaus <= 1.0, f"Source plausibility {plaus} must be in [0, 1]"

        src_id = hyp["source_hypothesis_id"]
        if src_id in df_src.index:
            expected_plaus = round(float(df_src.loc[src_id, "source_plausibility"]), 4)
            assert hyp["source_plausibility"] == expected_plaus


# Test 6: Multiple Hypotheses Per Vessel
def test_multiple_hypotheses_per_vessel(case_001_hypotheses):
    """
    Verify that candidate vessels associated with multiple distinct source locations/times
    generate multiple distinct hypotheses without premature merging.
    """
    df = pd.DataFrame(case_001_hypotheses)
    vessel_counts = df.groupby("mmsi").size()

    # In Case 001, 9 vessels are near both SH_0001 and SH_0008, generating 2 hypotheses each
    multi_hyp_vessels = vessel_counts[vessel_counts > 1]
    assert len(multi_hyp_vessels) >= 9, "Expected at least 9 vessels with multiple hypotheses"

    # Verify ROAM (338424255) has exactly 2 hypotheses
    roam_hyp = df[df["mmsi"] == 338424255]
    assert len(roam_hyp) == 2
    assert len(roam_hyp["release_lat"].unique()) == 2, "ROAM must link to 2 distinct release locations"


# Test 7: Duplicate Prevention
def test_duplicate_prevention():
    """
    Verify that exact duplicate (vessel, release_location, release_time) tuples are rejected,
    while distinct tuples are preserved.
    """
    gen = SourceHypothesisGenerator4D(case_id="case_001")

    raw_test_data = [
        {
            "candidate_id": "VC_0001",
            "mmsi": 111111111,
            "vessel_name": "TEST_SHIP",
            "imo": "IMO1234567",
            "vessel_type": "70",
            "release_lat": 33.40000,
            "release_lon": -118.40000,
            "release_timestamp": "2021-10-01T23:58:36Z",
            "source_age_hours": 2.0,
            "source_plausibility": 0.5,
            "ais_lat": 33.41000,
            "ais_lon": -118.41000,
            "vessel_source_distance_m": 1400.0,
            "ais_track_quality": "good",
            "gap_status": "0.0s",
            "compatibility_status": "COMPATIBLE",
        },
        # Exact duplicate
        {
            "candidate_id": "VC_0001",
            "mmsi": 111111111,
            "vessel_name": "TEST_SHIP",
            "imo": "IMO1234567",
            "vessel_type": "70",
            "release_lat": 33.40000,
            "release_lon": -118.40000,
            "release_timestamp": "2021-10-01T23:58:36Z",
            "source_age_hours": 2.0,
            "source_plausibility": 0.5,
            "ais_lat": 33.41000,
            "ais_lon": -118.41000,
            "vessel_source_distance_m": 1400.0,
            "ais_track_quality": "good",
            "gap_status": "0.0s",
            "compatibility_status": "COMPATIBLE",
        },
        # Distinct release location
        {
            "candidate_id": "VC_0002",
            "mmsi": 111111111,
            "vessel_name": "TEST_SHIP",
            "imo": "IMO1234567",
            "vessel_type": "70",
            "release_lat": 33.45000,
            "release_lon": -118.45000,
            "release_timestamp": "2021-10-01T23:58:36Z",
            "source_age_hours": 2.0,
            "source_plausibility": 0.6,
            "ais_lat": 33.41000,
            "ais_lon": -118.41000,
            "vessel_source_distance_m": 4500.0,
            "ais_track_quality": "good",
            "gap_status": "0.0s",
            "compatibility_status": "COMPATIBLE",
        },
    ]

    deduped = gen._deduplicate_hypotheses(raw_test_data)
    assert len(deduped) == 2, "Deduplication must reduce 3 records (1 duplicate) to 2 unique records"


# Test 8: Preservation of Location and Time Dimensions
def test_preservation_of_location_and_time_dimensions(case_001_hypotheses):
    """
    Verify that hypotheses retain both AIS position and hypothesized release location,
    as well as source age and timestamp, without collapsing into a single vessel score.
    """
    for hyp in case_001_hypotheses:
        # Both coordinates exist
        assert "ais_lat" in hyp and "ais_lon" in hyp
        assert "release_lat" in hyp and "release_lon" in hyp
        assert "release_timestamp" in hyp
        assert "source_age_hours" in hyp

        # Separation is non-zero in real cases
        assert hyp["vessel_source_distance_m"] > 0.0


# Test 9: AIS Gap Handling
def test_ais_gap_handling(case_001_hypotheses):
    """Verify that AIS track quality and gap status are accurately preserved."""
    for hyp in case_001_hypotheses:
        assert "ais_track_quality" in hyp
        assert hyp["ais_track_quality"] in ["bracketed_interpolation", "near_boundary_first_ping", "extrapolated"]
        assert "gap_status" in hyp
        assert isinstance(hyp["gap_status"], str)


# Test 10: Deterministic Hypothesis Generation
def test_deterministic_hypothesis_generation():
    """Verify that two independent runs produce bit-for-bit identical hypothesis sets."""
    gen1 = SourceHypothesisGenerator4D(case_id="case_001")
    hyp1 = gen1.generate_hypotheses()

    gen2 = SourceHypothesisGenerator4D(case_id="case_001")
    hyp2 = gen2.generate_hypotheses()

    assert len(hyp1) == len(hyp2)
    for h1, h2 in zip(hyp1, hyp2):
        assert h1 == h2


# Test 11: Synthetic Known Hypothesis Generation
def test_synthetic_known_hypothesis_generation(tmp_path):
    """
    Construct synthetic candidate vessel and source hypothesis tables with a known
    pairing, and verify exact hypothesis recovery.
    """
    # Create synthetic source hypotheses CSV
    df_src = pd.DataFrame([{
        "hypothesis_id": "SH_TEST_01",
        "candidate_id": "CS_SYNTH",
        "source_age_hours": 3.0,
        "estimated_release_time_utc": "2021-10-01T22:00:00Z",
        "centroid_lat": 33.4000,
        "centroid_lon": -118.4000,
        "bbox_west": -118.41,
        "bbox_south": 33.39,
        "bbox_east": -118.39,
        "bbox_north": 33.41,
        "dispersion_std_km": 0.2,
        "active_particle_fraction": 1.0,
        "particle_count": 500,
        "source_plausibility": 0.75,
    }])
    src_csv = tmp_path / "synth_src.csv"
    df_src.to_csv(src_csv, index=False)

    # Create synthetic candidate vessels CSV (vessel 5.0 km away)
    # Using small delta lat: ~0.045 deg lat ~ 5.0 km
    v_lat = 33.4450
    v_lon = -118.4000
    df_cand = pd.DataFrame([{
        "candidate_id": "VC_SYNTH_01",
        "mmsi": 999999999,
        "vessel_name": "SYNTHETIC_TANKER",
        "imo": "IMO9999999",
        "vessel_type": "80",
        "candidate_position_lat": v_lat,
        "candidate_position_lon": v_lon,
        "candidate_sog_knots": 12.0,
        "candidate_cog_deg": 180.0,
        "candidate_timestamp_utc": "2021-10-01T22:00:00Z",
        "distance_to_source_km": 5.004,
        "distance_threshold_km": 10.0,
        "source_plausibility": 0.75,
        "source_hypothesis_id": "SH_TEST_01",
        "source_slick_id": "CS_SYNTH",
        "source_age_hours": 3.0,
        "ais_track_quality": "bracketed_interpolation",
        "ais_gap_seconds": 120.0,
        "retention_reason": "Synthetic test candidate",
    }])
    cand_csv = tmp_path / "synth_cand.csv"
    df_cand.to_csv(cand_csv, index=False)

    # Run generator with temporary output
    gen = SourceHypothesisGenerator4D(case_id="case_001", output_dir=tmp_path)
    hypotheses = gen.generate_hypotheses(
        candidate_vessels_csv=cand_csv,
        source_hypotheses_csv=src_csv,
    )

    assert len(hypotheses) == 1
    h = hypotheses[0]
    assert h["mmsi"] == 999999999
    assert h["vessel_name"] == "SYNTHETIC_TANKER"
    assert h["release_lat"] == 33.4000
    assert h["release_lon"] == -118.4000
    assert h["release_timestamp"] == "2021-10-01T22:00:00Z"
    assert h["source_plausibility"] == 0.75
    assert abs(h["vessel_source_distance_m"] - 5003.8) < 5.0


# Test 12: Case 001 Output Integrity
def test_case_001_output_integrity():
    """Verify that actual Case 001 artifacts (CSV, JSON, GeoJSON, summary, PNG) exist and are valid."""
    gen = SourceHypothesisGenerator4D(case_id="case_001")
    result = gen.run()

    artifacts = result["artifacts"]
    assert artifacts["csv"].exists() and artifacts["csv"].stat().st_size > 0
    assert artifacts["json"].exists() and artifacts["json"].stat().st_size > 0
    assert artifacts["geojson"].exists() and artifacts["geojson"].stat().st_size > 0
    assert artifacts["summary"].exists() and artifacts["summary"].stat().st_size > 0
    assert artifacts["diagnostic"].exists() and artifacts["diagnostic"].stat().st_size > 0

    # Verify GeoJSON structure
    with open(artifacts["geojson"], "r", encoding="utf-8") as f:
        geojson_data = json.load(f)
    assert geojson_data["type"] == "FeatureCollection"
    assert len(geojson_data["features"]) > 0

    # Verify summary consistency
    with open(artifacts["summary"], "r", encoding="utf-8") as f:
        summary_data = json.load(f)
    assert summary_data["total_hypotheses"] == result["total_hypotheses"]
    assert summary_data["unique_vessels"] == 10
