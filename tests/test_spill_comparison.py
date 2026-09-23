"""
Tests for Phase 8: Predicted vs Observed Spill Comparison.

Covers:
1. Centroid error calculation (geodesic accuracy).
2. Geodesic particle-to-polygon distance (0 inside, accurate outside).
3. Mean, median, and P90 particle distance ordering and statistics.
4. Coverage calculation across configurable distance thresholds.
5. Spatial overlap / IoU calculation (intersection, union, IoU).
6. Shape metrics extraction (length, width, aspect ratio).
7. Orientation comparison with periodic 180-degree wrapping.
8. Predicted continuous spatial representation generation (buffered disks).
9. Sparse particle distribution handling (graceful fallback, is_sparse flag).
10. Deterministic output reproducibility.
11. Synthetic correct-vs-wrong hypothesis separation.
12. Case 001 comparison output integrity and artifact completeness.
"""

import json
import math
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import Point, Polygon

from src.common.geo import haversine_distance_m
from src.attribution.spill_comparator import (
    SpillComparator,
    angular_difference_deg,
    build_particle_polygon,
    compute_shape_metrics,
    project_geometry_to_metric,
    project_point_to_metric,
)


# ---------------------------------------------------------------------------
# Test 1: Centroid Error Calculation
# ---------------------------------------------------------------------------
def test_centroid_error_calculation():
    """Verify geodesic distance calculation between observed and predicted centroids."""
    obs_lat, obs_lon = 33.41168, -118.37887
    pred_lat, pred_lon = 33.412824, -118.379395

    expected_m = haversine_distance_m(obs_lat, obs_lon, pred_lat, pred_lon)
    assert 130.0 < expected_m < 140.0
    assert pytest.approx(expected_m, abs=0.1) == 136.22


# ---------------------------------------------------------------------------
# Test 2: Geodesic Particle-to-Polygon Distance
# ---------------------------------------------------------------------------
def test_geodesic_particle_distance():
    """Verify that particles inside polygon have 0 distance, outside have Euclidean metric distance."""
    # 200m x 200m square centered at (0, 0) in metric coordinates
    poly_metric = Polygon([(-100, -100), (100, -100), (100, 100), (-100, 100)])

    p_inside = Point(0, 0)
    assert poly_metric.contains(p_inside)
    dist_inside = 0.0 if poly_metric.contains(p_inside) else poly_metric.distance(p_inside)
    assert dist_inside == 0.0

    p_boundary = Point(100, 0)
    dist_boundary = 0.0 if poly_metric.contains(p_boundary) else poly_metric.distance(p_boundary)
    assert dist_boundary == 0.0

    p_outside = Point(250, 0)
    assert not poly_metric.contains(p_outside)
    dist_outside = poly_metric.distance(p_outside)
    assert pytest.approx(dist_outside, abs=1e-3) == 150.0  # 250 - 100 = 150 m


# ---------------------------------------------------------------------------
# Test 3: Mean, Median, and P90 Particle Distance
# ---------------------------------------------------------------------------
def test_mean_median_p90_particle_distance():
    """Verify proper calculation and ordering of distance distribution percentiles."""
    poly_metric = Polygon([(-50, -50), (50, -50), (50, 50), (-50, 50)])

    # 10 particles at known positions outside polygon:
    # 5 particles at x=100 (distance = 50m)
    # 4 particles at x=200 (distance = 150m)
    # 1 particle at x=550 (distance = 500m)
    pts = [Point(100, 0)] * 5 + [Point(200, 0)] * 4 + [Point(550, 0)] * 1
    dists = [poly_metric.distance(p) for p in pts]

    mean_d = float(np.mean(dists))
    median_d = float(np.median(dists))
    p90_d = float(np.percentile(dists, 90))

    assert median_d == 100.0
    assert pytest.approx(mean_d, abs=1e-2) == (5 * 50 + 4 * 150 + 1 * 500) / 10.0  # 135.0 m
    assert p90_d >= median_d
    assert p90_d <= 500.0


# ---------------------------------------------------------------------------
# Test 4: Coverage Calculation
# ---------------------------------------------------------------------------
def test_coverage_calculation():
    """Verify fraction of particles within configurable distance threshold."""
    poly_metric = Polygon([(-50, -50), (50, -50), (50, 50), (-50, 50)])

    # 6 particles within 200m distance, 4 particles at 600m distance
    pts = [Point(150, 0)] * 6 + [Point(650, 0)] * 4  # dists: 100m (6) and 600m (4)
    dists = [poly_metric.distance(p) for p in pts]

    thresh_500m = 500.0
    coverage = sum(1 for d in dists if d <= thresh_500m) / len(dists)
    assert coverage == 0.6  # 6/10 = 60%

    thresh_50m = 50.0
    coverage_strict = sum(1 for d in dists if d <= thresh_50m) / len(dists)
    assert coverage_strict == 0.0


# ---------------------------------------------------------------------------
# Test 5: Spatial Overlap / IoU Calculation
# ---------------------------------------------------------------------------
def test_spatial_overlap_iou():
    """Verify intersection area, union area, and IoU calculation."""
    # Square 1: [0, 100] x [0, 100] -> area 10,000 m2
    s1 = Polygon([(0, 0), (100, 0), (100, 100), (0, 100)])
    # Square 2: [50, 150] x [0, 100] -> area 10,000 m2
    s2 = Polygon([(50, 0), (150, 0), (150, 100), (50, 100)])

    inter = s1.intersection(s2).area  # [50, 100] x [0, 100] = 5,000 m2
    union = s1.union(s2).area         # [0, 150] x [0, 100] = 15,000 m2
    iou = inter / union

    assert pytest.approx(inter, abs=1e-3) == 5000.0
    assert pytest.approx(union, abs=1e-3) == 15000.0
    assert pytest.approx(iou, abs=1e-4) == 1.0 / 3.0

    # Disjoint polygons
    s3 = Polygon([(500, 0), (600, 0), (600, 100), (500, 100)])
    inter_disjoint = s1.intersection(s3).area
    assert inter_disjoint == 0.0


# ---------------------------------------------------------------------------
# Test 6: Shape Metrics Extraction
# ---------------------------------------------------------------------------
def test_shape_metrics():
    """Verify length, width, aspect ratio, and orientation extraction."""
    # East-West elongated rectangle 1000m x 200m
    poly = Polygon([(-500, -100), (500, -100), (500, 100), (-500, 100)])
    shape_dict = compute_shape_metrics(poly)

    assert pytest.approx(shape_dict["length_m"], abs=1.0) == 1000.0
    assert pytest.approx(shape_dict["width_m"], abs=1.0) == 200.0
    assert pytest.approx(shape_dict["aspect_ratio"], abs=0.05) == 5.0
    assert abs(shape_dict["orientation_deg"]) < 2.0  # Horizontal (East-West)


# ---------------------------------------------------------------------------
# Test 7: Orientation Comparison with Periodic 180-Degree Wrapping
# ---------------------------------------------------------------------------
def test_orientation_comparison():
    """Verify angular difference under 180-degree axis symmetry."""
    # Near +/- 90 degrees wrapping
    diff1 = angular_difference_deg(85.0, -85.0)
    assert pytest.approx(diff1, abs=1e-3) == 10.0  # Not 170!

    diff2 = angular_difference_deg(0.0, 90.0)
    assert pytest.approx(diff2, abs=1e-3) == 90.0

    diff3 = angular_difference_deg(30.0, 30.0)
    assert pytest.approx(diff3, abs=1e-3) == 0.0

    diff4 = angular_difference_deg(-45.0, 45.0)
    assert pytest.approx(diff4, abs=1e-3) == 90.0


# ---------------------------------------------------------------------------
# Test 8: Predicted Representation Generation (Buffered Disks)
# ---------------------------------------------------------------------------
def test_predicted_representation_generation():
    """Verify deterministic buffered particle polygon generation."""
    origin_lat, origin_lon = 33.5, -118.2
    particles = [
        {"particle_id": i, "lat": origin_lat + i * 0.0001, "lon": origin_lon, "status": "active"}
        for i in range(20)
    ]

    poly, is_sparse = build_particle_polygon(
        particles=particles,
        origin_lat=origin_lat,
        origin_lon=origin_lon,
        buffer_radius_m=50.0,
    )

    assert not is_sparse
    assert poly.is_valid
    assert not poly.is_empty
    assert poly.area > math.pi * (50.0 ** 2)  # Area larger than single disk


# ---------------------------------------------------------------------------
# Test 9: Sparse Particle Handling
# ---------------------------------------------------------------------------
def test_sparse_particle_handling():
    """Verify that sparse particle distributions are flagged gracefully without crash."""
    origin_lat, origin_lon = 33.5, -118.2
    # Only 3 particles
    particles = [
        {"particle_id": 0, "lat": origin_lat, "lon": origin_lon, "status": "active"},
        {"particle_id": 1, "lat": origin_lat + 0.001, "lon": origin_lon, "status": "active"},
        {"particle_id": 2, "lat": origin_lat, "lon": origin_lon + 0.001, "status": "active"},
    ]

    poly, is_sparse = build_particle_polygon(
        particles=particles,
        origin_lat=origin_lat,
        origin_lon=origin_lon,
        buffer_radius_m=30.0,
    )

    assert is_sparse is True
    assert poly.is_valid
    assert not np.isnan(poly.area)


# ---------------------------------------------------------------------------
# Test 10: Deterministic Output
# ---------------------------------------------------------------------------
def test_deterministic_output():
    """Verify identical comparison results on repeated executions."""
    origin_lat, origin_lon = 33.41168, -118.37887
    hyp_row = {
        "hypothesis_id": "4DH_TEST",
        "candidate_id": "VC_TEST",
        "mmsi": 123456789,
        "vessel_name": "TEST_VESSEL",
        "observed_slick_id": "CS_TEST",
        "release_timestamp": "2021-10-01T23:58:36+00:00",
        "release_lat": 33.414692,
        "release_lon": -118.412924,
        "observation_timestamp": "2021-10-02T01:58:36+00:00",
        "duration_hours": 2.0,
        "particle_count": 100,
        "active_particle_fraction": 1.0,
        "predicted_centroid_lat": origin_lat + 0.0005,
        "predicted_centroid_lon": origin_lon + 0.0005,
    }
    particles = [
        {"particle_id": i, "lat": origin_lat + np.sin(i) * 0.0005, "lon": origin_lon + np.cos(i) * 0.0005, "status": "active"}
        for i in range(100)
    ]
    obs_geom = Polygon([
        (origin_lon - 0.001, origin_lat - 0.001),
        (origin_lon + 0.001, origin_lat - 0.001),
        (origin_lon + 0.001, origin_lat + 0.001),
        (origin_lon - 0.001, origin_lat + 0.001),
    ])
    obs_row = {"centroid_lat": origin_lat, "centroid_lon": origin_lon}

    comp = SpillComparator("case_001")
    res1 = comp.compare_single_hypothesis(hyp_row, particles, obs_geom, obs_row)
    res2 = comp.compare_single_hypothesis(hyp_row, particles, obs_geom, obs_row)

    assert res1 == res2


# ---------------------------------------------------------------------------
# Test 11: Synthetic Correct vs Wrong Hypothesis Separation
# ---------------------------------------------------------------------------
def test_synthetic_correct_vs_wrong_separation():
    """
    Synthetic controlled test:
    - 'Correct' hypothesis cloud overlaps observed slick: low centroid error, low particle distance, high coverage.
    - 'Wrong' hypothesis cloud released 15 km away: high error, high distance, 0 coverage, 0 IoU.
    """
    obs_lat, obs_lon = 33.50, -118.20
    obs_geom = Polygon([
        (obs_lon - 0.002, obs_lat - 0.002),
        (obs_lon + 0.002, obs_lat - 0.002),
        (obs_lon + 0.002, obs_lat + 0.002),
        (obs_lon - 0.002, obs_lat + 0.002),
    ])
    obs_row = {"centroid_lat": obs_lat, "centroid_lon": obs_lon}

    comp = SpillComparator("case_001")

    # 1. Correct hypothesis (centered on slick)
    hyp_correct = {
        "hypothesis_id": "4DH_CORRECT",
        "candidate_id": "VC_001",
        "mmsi": 111111111,
        "vessel_name": "TRUE_SOURCE",
        "observed_slick_id": "CS_SYNTH",
        "release_timestamp": "2021-10-01T23:58:36+00:00",
        "release_lat": 33.50,
        "release_lon": -118.22,
        "observation_timestamp": "2021-10-02T01:58:36+00:00",
        "duration_hours": 2.0,
        "particle_count": 50,
        "active_particle_fraction": 1.0,
        "predicted_centroid_lat": obs_lat + 0.0001,
        "predicted_centroid_lon": obs_lon + 0.0001,
    }
    particles_correct = [
        {"particle_id": i, "lat": obs_lat + np.random.uniform(-0.001, 0.001), "lon": obs_lon + np.random.uniform(-0.001, 0.001), "status": "active"}
        for i in range(50)
    ]
    res_correct = comp.compare_single_hypothesis(hyp_correct, particles_correct, obs_geom, obs_row)

    # 2. Wrong hypothesis (15 km away)
    wrong_lat = obs_lat + 0.135  # ~15 km north
    hyp_wrong = {
        "hypothesis_id": "4DH_WRONG",
        "candidate_id": "VC_002",
        "mmsi": 222222222,
        "vessel_name": "WRONG_VESSEL",
        "observed_slick_id": "CS_SYNTH",
        "release_timestamp": "2021-10-01T23:58:36+00:00",
        "release_lat": wrong_lat,
        "release_lon": obs_lon,
        "observation_timestamp": "2021-10-02T01:58:36+00:00",
        "duration_hours": 2.0,
        "particle_count": 50,
        "active_particle_fraction": 1.0,
        "predicted_centroid_lat": wrong_lat,
        "predicted_centroid_lon": obs_lon,
    }
    particles_wrong = [
        {"particle_id": i, "lat": wrong_lat + np.random.uniform(-0.001, 0.001), "lon": obs_lon + np.random.uniform(-0.001, 0.001), "status": "active"}
        for i in range(50)
    ]
    res_wrong = comp.compare_single_hypothesis(hyp_wrong, particles_wrong, obs_geom, obs_row)

    # Assert clear physical separation
    assert res_correct["centroid_error_m"] < 50.0
    assert res_correct["mean_particle_distance_m"] < 50.0
    assert res_correct["coverage"] == 1.0
    assert res_correct["iou"] > 0.10

    assert res_wrong["centroid_error_m"] > 14000.0  # > 14 km
    assert res_wrong["mean_particle_distance_m"] > 14000.0
    assert res_wrong["coverage"] == 0.0
    assert res_wrong["iou"] == 0.0


# ---------------------------------------------------------------------------
# Test 12: Case 001 Output Integrity
# ---------------------------------------------------------------------------
def test_case_001_comparison_output_integrity():
    """Verify Case 001 comparison artifacts exist, are non-empty, and adhere to schema."""
    csv_path = Path("data/processed/attribution/case_001_spill_comparisons.csv")
    json_path = Path("data/processed/attribution/case_001_spill_comparisons.json")
    summary_path = Path("data/processed/attribution/case_001_spill_comparison_summary.json")
    diag_path = Path("data/processed/attribution/case_001_spill_comparison_diagnostic.png")

    assert csv_path.exists(), "Comparisons CSV missing"
    assert json_path.exists(), "Comparisons JSON missing"
    assert summary_path.exists(), "Comparisons summary JSON missing"
    assert diag_path.exists(), "Diagnostic PNG missing"

    df = pd.read_csv(csv_path)
    assert len(df) == 19
    assert df["hypothesis_id"].nunique() == 19

    expected_cols = [
        "hypothesis_id",
        "candidate_id",
        "mmsi",
        "vessel_name",
        "observed_slick_id",
        "release_timestamp",
        "release_lat",
        "release_lon",
        "observation_timestamp",
        "simulation_duration_hours",
        "particle_count",
        "active_particle_count",
        "active_particle_fraction",
        "simulation_status",
        "predicted_centroid_lat",
        "predicted_centroid_lon",
        "observed_centroid_lat",
        "observed_centroid_lon",
        "centroid_error_m",
        "mean_particle_distance_m",
        "median_particle_distance_m",
        "p90_particle_distance_m",
        "coverage",
        "in_slick_fraction",
        "intersection_area_m2",
        "union_area_m2",
        "iou",
        "predicted_area_m2",
        "observed_area_m2",
        "predicted_length_m",
        "predicted_width_m",
        "predicted_aspect_ratio",
        "predicted_orientation_deg",
        "observed_length_m",
        "observed_width_m",
        "observed_aspect_ratio",
        "observed_orientation_deg",
        "delta_length_m",
        "delta_width_m",
        "delta_aspect_ratio",
        "delta_orientation_deg",
        "is_sparse",
        "norm_centroid_score",
        "norm_particle_score",
        "norm_coverage_score",
        "norm_iou_score",
    ]
    for col in expected_cols:
        assert col in df.columns, f"Missing expected column: {col}"

    with open(summary_path, "r", encoding="utf-8") as f:
        summary_data = json.load(f)
    assert summary_data["case_id"] == "case_001"
    assert summary_data["total_hypotheses_compared"] == 19
    assert "metric_distributions" in summary_data
    assert "rankings_by_metric" in summary_data
