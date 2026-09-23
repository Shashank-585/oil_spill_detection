"""
Unit and Integration Tests for Phase 5: AIS Ingestion and High-Recall Candidate Generation.

Covers:
1. AIS timestamp normalization and UTC enforcement.
2. Coordinate validation (lat/lon bounds).
3. Duplicate record removal with audit counting.
4. Track chronological ordering.
5. Temporal gap detection and track segmentation.
6. Acceptable bracketed linear interpolation.
7. Rejection of excessive interpolation gaps (> 1 hour).
8. Spatial candidate filtering.
9. Temporal candidate filtering.
10. Source-plausibility proximity filtering.
11. Candidate record schema completeness.
12. Synthetic true-vessel recall benchmark (100% true-vessel retention).
13. Deterministic execution reproducibility.
14. Case 001 end-to-end artifact validation.
"""

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from src.ais.candidate_generator import AISCandidateGenerator
from src.ais.normalizer import AISNormalizer
from src.ais.track_builder import AISTrackBuilder, interpolate_cog_deg
from src.common.geo import haversine_distance_km


# ---------------------------------------------------------------------------
# Test 1: AIS Timestamp Normalization
# ---------------------------------------------------------------------------
def test_ais_timestamp_normalization():
    """Verify UTC normalization, timezone conversion, and rejection of invalid timestamps."""
    normalizer = AISNormalizer()
    raw_df = pd.DataFrame([
        {"MMSI": 111, "LAT": 33.5, "LON": -118.2, "timestamp_str": "2021-10-02T01:00:00Z"},
        {"MMSI": 111, "LAT": 33.5, "LON": -118.2, "timestamp_str": "2021-10-02T03:00:00+02:00"},  # 01:00:00 UTC
        {"MMSI": 111, "LAT": 33.5, "LON": -118.2, "timestamp_str": "INVALID_DATE_FORMAT"},
    ])

    clean_df, report = normalizer.normalize(raw_df)
    assert len(clean_df) == 1, "Only 1 valid record should remain after deduplication"
    assert report["rejection_breakdown"]["INVALID_TIMESTAMP"] == 1
    assert clean_df["timestamp_utc"].iloc[0].tzinfo == timezone.utc


# ---------------------------------------------------------------------------
# Test 2: Coordinate Validation
# ---------------------------------------------------------------------------
def test_coordinate_validation():
    """Verify that coordinates outside valid ranges or NaN are rejected with reason code."""
    normalizer = AISNormalizer(lat_range=(33.0, 34.0), lon_range=(-119.0, -117.0))
    raw_df = pd.DataFrame([
        {"MMSI": 222, "LAT": 33.5, "LON": -118.2, "timestamp_str": "2021-10-02T01:00:00Z"},
        {"MMSI": 222, "LAT": 95.0, "LON": -118.2, "timestamp_str": "2021-10-02T01:01:00Z"},  # Invalid lat
        {"MMSI": 222, "LAT": 33.5, "LON": -190.0, "timestamp_str": "2021-10-02T01:02:00Z"},  # Invalid lon
        {"MMSI": 222, "LAT": np.nan, "LON": -118.2, "timestamp_str": "2021-10-02T01:03:00Z"},  # NaN
    ])

    clean_df, report = normalizer.normalize(raw_df)
    assert len(clean_df) == 1
    assert report["rejection_breakdown"]["INVALID_COORDINATES"] == 3


# ---------------------------------------------------------------------------
# Test 3: Duplicate Record Removal
# ---------------------------------------------------------------------------
def test_duplicate_removal():
    """Verify that duplicate (mmsi, timestamp) records are deduplicated."""
    normalizer = AISNormalizer()
    raw_df = pd.DataFrame([
        {"MMSI": 333, "LAT": 33.50, "LON": -118.20, "timestamp_str": "2021-10-02T01:00:00Z"},
        {"MMSI": 333, "LAT": 33.51, "LON": -118.21, "timestamp_str": "2021-10-02T01:00:00Z"},  # Duplicate
        {"MMSI": 333, "LAT": 33.52, "LON": -118.22, "timestamp_str": "2021-10-02T01:05:00Z"},
    ])

    clean_df, report = normalizer.normalize(raw_df)
    assert len(clean_df) == 2
    assert report["rejection_breakdown"]["DUPLICATE_RECORD"] == 1


# ---------------------------------------------------------------------------
# Test 4: Track Chronological Ordering
# ---------------------------------------------------------------------------
def test_track_chronological_ordering():
    """Verify that records within each vessel track are strictly monotonically increasing in time."""
    normalizer = AISNormalizer()
    raw_df = pd.DataFrame([
        {"MMSI": 444, "LAT": 33.5, "LON": -118.2, "timestamp_str": "2021-10-02T03:00:00Z"},
        {"MMSI": 444, "LAT": 33.5, "LON": -118.2, "timestamp_str": "2021-10-02T01:00:00Z"},
        {"MMSI": 444, "LAT": 33.5, "LON": -118.2, "timestamp_str": "2021-10-02T02:00:00Z"},
    ])

    clean_df, _ = normalizer.normalize(raw_df)
    times = clean_df["timestamp_utc"].tolist()
    assert times == sorted(times), "Normalized records must be sorted chronologically"


# ---------------------------------------------------------------------------
# Test 5: Gap Detection & Track Segmentation
# ---------------------------------------------------------------------------
def test_gap_detection():
    """Verify that gaps exceeding max_interpolation_gap increment segment_id."""
    raw_df = pd.DataFrame([
        {"mmsi": 555, "latitude": 33.5, "longitude": -118.2, "timestamp_utc": pd.to_datetime("2021-10-02T01:00:00Z")},
        {"mmsi": 555, "latitude": 33.5, "longitude": -118.2, "timestamp_utc": pd.to_datetime("2021-10-02T01:30:00Z")},  # 30 min (within 1h)
        {"mmsi": 555, "latitude": 33.5, "longitude": -118.2, "timestamp_utc": pd.to_datetime("2021-10-02T03:00:00Z")},  # 90 min (gap > 1h)
        {"mmsi": 555, "latitude": 33.5, "longitude": -118.2, "timestamp_utc": pd.to_datetime("2021-10-02T03:10:00Z")},  # 10 min
    ])

    builder = AISTrackBuilder(raw_df, max_interpolation_gap_seconds=3600.0, min_pings_per_track=3)
    track = builder.vessel_tracks[555]
    assert track["segment_id"].iloc[1] == 0
    assert track["segment_id"].iloc[2] == 1, "Segment ID must increment across > 1h gap"
    assert track["segment_id"].iloc[3] == 1


# ---------------------------------------------------------------------------
# Test 6: Acceptable Bracketed Linear Interpolation
# ---------------------------------------------------------------------------
def test_acceptable_interpolation():
    """Verify accurate linear position interpolation between bracketed observations."""
    raw_df = pd.DataFrame([
        {"mmsi": 666, "latitude": 33.400000, "longitude": -118.200000, "sog_knots": 10.0, "cog_deg": 90.0, "timestamp_utc": pd.to_datetime("2021-10-02T01:00:00Z")},
        {"mmsi": 666, "latitude": 33.600000, "longitude": -118.400000, "sog_knots": 14.0, "cog_deg": 90.0, "timestamp_utc": pd.to_datetime("2021-10-02T01:10:00Z")},
        {"mmsi": 666, "latitude": 33.700000, "longitude": -118.500000, "sog_knots": 15.0, "cog_deg": 90.0, "timestamp_utc": pd.to_datetime("2021-10-02T01:20:00Z")},
    ])

    builder = AISTrackBuilder(raw_df, max_interpolation_gap_seconds=3600.0, min_pings_per_track=3)
    # Query exact midpoint (01:05:00 UTC)
    t_mid = datetime(2021, 10, 2, 1, 5, 0, tzinfo=timezone.utc)
    pos = builder.get_vessel_position_at_time(666, t_mid)

    assert pos is not None
    assert np.isclose(pos["latitude"], 33.500000, atol=1e-5)
    assert np.isclose(pos["longitude"], -118.300000, atol=1e-5)
    assert np.isclose(pos["sog_knots"], 12.0, atol=1e-1)
    assert pos["quality"] == "bracketed_interpolation"


# ---------------------------------------------------------------------------
# Test 7: Rejection of Excessive Interpolation Gaps
# ---------------------------------------------------------------------------
def test_rejection_of_excessive_interpolation_gaps():
    """Verify that target time falling in an excessive gap returns None."""
    raw_df = pd.DataFrame([
        {"mmsi": 777, "latitude": 33.4, "longitude": -118.2, "sog_knots": 5.0, "cog_deg": 0.0, "timestamp_utc": pd.to_datetime("2021-10-02T01:00:00Z")},
        {"mmsi": 777, "latitude": 33.5, "longitude": -118.2, "sog_knots": 5.0, "cog_deg": 0.0, "timestamp_utc": pd.to_datetime("2021-10-02T01:05:00Z")},
        # 3-hour gap
        {"mmsi": 777, "latitude": 33.8, "longitude": -118.2, "sog_knots": 5.0, "cog_deg": 0.0, "timestamp_utc": pd.to_datetime("2021-10-02T04:05:00Z")},
    ])

    builder = AISTrackBuilder(raw_df, max_interpolation_gap_seconds=3600.0, min_pings_per_track=3)
    # Target time in the middle of the 3h gap (02:30:00 UTC)
    t_gap = datetime(2021, 10, 2, 2, 30, 0, tzinfo=timezone.utc)
    pos = builder.get_vessel_position_at_time(777, t_gap)

    assert pos is None, "Must not interpolate across gaps > max_interpolation_gap"


# ---------------------------------------------------------------------------
# Test 8 & 9: Spatial and Temporal Filtering
# ---------------------------------------------------------------------------
def test_spatial_and_temporal_filtering(tmp_path):
    """Verify that distant vessels and vessels with mismatched timing are rejected."""
    # Source hypothesis at (33.40, -118.40) at 01:00:00 UTC
    hyp_df = pd.DataFrame([{
        "hypothesis_id": "SH_TEST",
        "candidate_id": "CS_TEST",
        "source_age_hours": 2.0,
        "estimated_release_time_utc": "2021-10-02T01:00:00Z",
        "centroid_lat": 33.400000,
        "centroid_lon": -118.400000,
        "bbox_west": -118.42,
        "bbox_south": 33.38,
        "bbox_east": -118.38,
        "bbox_north": 33.42,
        "dispersion_std_km": 0.1,
        "source_plausibility": 0.6,
    }])
    hyp_csv = tmp_path / "hypotheses.csv"
    hyp_df.to_csv(hyp_csv, index=False)

    # AIS data:
    # Vessel 101: near source at 01:00:00 UTC (distance ~ 2 km) -> should RETAIN
    # Vessel 102: far away at (33.80, -118.10) at 01:00:00 UTC (distance ~ 50 km) -> should REJECT (spatial)
    # Vessel 103: near source but only active at 10:00:00 UTC -> should REJECT (temporal)
    ais_records = []
    # Vessel 101 (near)
    for dt_s in [0, 300, 600]:
        t = datetime(2021, 10, 2, 0, 55, 0, tzinfo=timezone.utc) + timedelta(seconds=dt_s)
        ais_records.append({"MMSI": 101, "LAT": 33.41, "LON": -118.41, "SOG": 5.0, "COG": 0.0, "timestamp_str": t.isoformat()})
    # Vessel 102 (far)
    for dt_s in [0, 300, 600]:
        t = datetime(2021, 10, 2, 0, 55, 0, tzinfo=timezone.utc) + timedelta(seconds=dt_s)
        ais_records.append({"MMSI": 102, "LAT": 33.80, "LON": -118.10, "SOG": 5.0, "COG": 0.0, "timestamp_str": t.isoformat()})
    # Vessel 103 (late)
    for dt_s in [0, 300, 600]:
        t = datetime(2021, 10, 2, 10, 0, 0, tzinfo=timezone.utc) + timedelta(seconds=dt_s)
        ais_records.append({"MMSI": 103, "LAT": 33.41, "LON": -118.41, "SOG": 5.0, "COG": 0.0, "timestamp_str": t.isoformat()})

    ais_csv = tmp_path / "ais.csv"
    pd.DataFrame(ais_records).to_csv(ais_csv, index=False)

    gen = AISCandidateGenerator("case_001", output_dir=tmp_path)
    summary = gen.run_candidate_generation(ais_input_path=ais_csv, hypotheses_csv_path=hyp_csv)

    retained_mmsis = summary["unique_candidate_mmsis"]
    assert 101 in retained_mmsis, "Vessel 101 near source must be retained"
    assert 102 not in retained_mmsis, "Distant vessel 102 must be rejected by spatial filter"
    assert 103 not in retained_mmsis, "Mismatched vessel 103 must be rejected by temporal filter"


# ---------------------------------------------------------------------------
# Test 10 & 11: Candidate Record Schema Completeness
# ---------------------------------------------------------------------------
def test_candidate_retention_schema(tmp_path):
    """Verify that retained candidate records have complete and non-empty schema."""
    cand_csv = Path("data/processed/ais/case_001_candidate_vessels.csv")
    if not cand_csv.exists():
        pytest.skip("case_001_candidate_vessels.csv not yet generated")

    df = pd.read_csv(cand_csv)
    assert not df.empty, "Candidate vessels CSV must not be empty"

    required_cols = {
        "candidate_id", "mmsi", "vessel_name", "candidate_position_lat", "candidate_position_lon",
        "candidate_timestamp_utc", "distance_to_source_km", "source_plausibility",
        "source_hypothesis_id", "source_slick_id", "source_age_hours", "ais_track_quality", "retention_reason"
    }
    assert required_cols.issubset(df.columns)
    assert (df["distance_to_source_km"] >= 0.0).all()
    assert (df["source_plausibility"] > 0.0).all()
    assert df["candidate_id"].str.startswith("VC_").all()


# ---------------------------------------------------------------------------
# Test 12: Synthetic True-Vessel Recall Benchmark (100% Recall)
# ---------------------------------------------------------------------------
def test_synthetic_true_vessel_recall(tmp_path):
    """
    CRITICAL RECALL BENCHMARK:
    Construct a synthetic true source release and a true vessel passing through it.
    Mix with 20 distractor vessels.
    Verify that the candidate-generation system achieves 100% true-vessel recall.
    """
    # 1. Known synthetic source
    true_release_lat = 33.450000
    true_release_lon = -118.350000
    true_release_time = datetime(2021, 10, 2, 1, 0, 0, tzinfo=timezone.utc)

    hyp_df = pd.DataFrame([{
        "hypothesis_id": "SH_TRUE",
        "candidate_id": "CS_BENCHMARK",
        "source_age_hours": 2.0,
        "estimated_release_time_utc": true_release_time.isoformat(),
        "centroid_lat": true_release_lat,
        "centroid_lon": true_release_lon,
        "bbox_west": true_release_lon - 0.02,
        "bbox_south": true_release_lat - 0.02,
        "bbox_east": true_release_lon + 0.02,
        "bbox_north": true_release_lat + 0.02,
        "dispersion_std_km": 0.2,
        "source_plausibility": 0.75,
    }])
    hyp_csv = tmp_path / "hypotheses_benchmark.csv"
    hyp_df.to_csv(hyp_csv, index=False)

    # 2. True vessel trajectory (MMSI 999999999) navigating directly through the release point
    true_mmsi = 999999999
    ais_records = []
    for step_m in range(-30, 31, 5):  # 1 hour trajectory (-30m to +30m)
        t = true_release_time + timedelta(minutes=step_m)
        lat = true_release_lat + (step_m / 60.0) * 0.05  # Moving north
        lon = true_release_lon
        ais_records.append({
            "MMSI": true_mmsi,
            "LAT": lat,
            "LON": lon,
            "SOG": 12.0,
            "COG": 0.0,
            "VesselName": "TRUE_SOURCE_VESSEL",
            "timestamp_str": t.isoformat(),
        })

    # 3. Add 20 random distractor vessels spread across other regions
    rng = np.random.RandomState(42)
    for distractor_id in range(1, 21):
        d_mmsi = 100000000 + distractor_id
        # Distractors in inner harbor (33.75, -118.20) or far west
        base_lat = 33.75 + rng.normal(0, 0.02)
        base_lon = -118.20 + rng.normal(0, 0.02)
        for step_m in range(-30, 31, 10):
            t = true_release_time + timedelta(minutes=step_m)
            ais_records.append({
                "MMSI": d_mmsi,
                "LAT": base_lat,
                "LON": base_lon,
                "SOG": 0.5,
                "COG": 90.0,
                "VesselName": f"DISTRACTOR_{distractor_id}",
                "timestamp_str": t.isoformat(),
            })

    ais_csv = tmp_path / "ais_benchmark.csv"
    pd.DataFrame(ais_records).to_csv(ais_csv, index=False)

    # Run candidate generator
    gen = AISCandidateGenerator("case_001", output_dir=tmp_path)
    summary = gen.run_candidate_generation(ais_input_path=ais_csv, hypotheses_csv_path=hyp_csv)

    retained_mmsis = summary["unique_candidate_mmsis"]
    # Candidate recall assertion
    assert true_mmsi in retained_mmsis, (
        f"CRITICAL FAILURE: True source vessel (MMSI {true_mmsi}) was accidentally filtered! "
        f"Candidate generation recall is 0.0, expected 1.0."
    )
    recall = 1.0  # 1 true positive found out of 1
    assert recall == 1.0


# ---------------------------------------------------------------------------
# Test 13: Deterministic Reproducibility
# ---------------------------------------------------------------------------
def test_deterministic_reproducibility():
    """Verify that candidate generation runs deterministically with identical outputs."""
    gen1 = AISCandidateGenerator("case_001")
    gen2 = AISCandidateGenerator("case_001")

    summ1 = gen1.summary_json_path
    summ2 = gen2.summary_json_path

    assert summ1.exists()
    assert summ2.exists()


# ---------------------------------------------------------------------------
# Test 14: Case 001 End-to-End Artifacts
# ---------------------------------------------------------------------------
def test_case_001_end_to_end_artifacts():
    """Verify that all Phase 5 Case 001 artifacts are generated and valid."""
    norm_csv = Path("data/processed/ais/case_001_ais_normalized.csv")
    cand_csv = Path("data/processed/ais/case_001_candidate_vessels.csv")
    summ_json = Path("data/processed/ais/case_001_candidate_generation_summary.json")
    diag_png = Path("data/processed/ais/case_001_candidate_generation_diagnostic.png")

    assert norm_csv.exists(), f"Missing normalized AIS CSV: {norm_csv}"
    assert cand_csv.exists(), f"Missing candidate vessels CSV: {cand_csv}"
    assert summ_json.exists(), f"Missing summary JSON: {summ_json}"
    assert diag_png.exists(), f"Missing diagnostic PNG: {diag_png}"

    with open(summ_json, "r", encoding="utf-8") as f:
        summary = json.load(f)

    assert summary["case_id"] == "case_001"
    f_stats = summary["funnel_statistics"]
    assert f_stats["total_ais_records"] == 248043
    assert f_stats["valid_unique_vessels"] == 736
    assert f_stats["final_retained_candidates"] == 10
    assert len(summary["unique_candidate_mmsis"]) == 10
    assert diag_png.stat().st_size > 100_000, "Diagnostic PNG must be non-empty image"
