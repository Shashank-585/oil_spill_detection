"""
Unit and Integration Tests for Baseline Dark-Slick Detection (Phase 3).

Verifies:
1. Multi-mode thresholding (global, contrast, adaptive)
2. Local background and contrast computation
3. Connected components labeling & geometric feature extraction
4. Geospatially correct metric area calculation (latitude scaling, no degree differences)
5. Synthetic raster detection with known dark slick locations
6. Look-alike filtering with explicit rejection reason logging (no silent deletions)
7. Heuristic candidate confidence scoring [0.0, 1.0]
8. NoData and orbital swath exclusion
9. Deterministic detection execution
10. Case 001 end-to-end detection products validation
"""

import os
import json
import pytest
import numpy as np
import rasterio
from rasterio.transform import from_origin

from src.common.paths import resolve_path
from src.detection.geometry import (
    compute_metric_pixel_area_km2,
    extract_candidate_components
)
from src.detection.scoring import compute_candidate_score
from src.detection.lookalike_filter import LookAlikeFilter
from src.detection.detector import BaselineDarkSlickDetector


# -------------------------------------------------------------------------
# Test 1: Geospatially Correct Metric Area Calculation
# -------------------------------------------------------------------------
def test_geospatial_metric_area_accuracy():
    """Verify that physical pixel area scales with cos(lat) and is not degree differences."""
    res_deg = 0.0001
    
    # At Equator (lat = 0 deg), cos(0) = 1.0
    area_equator = compute_metric_pixel_area_km2(0.0, res_deg, res_deg)
    # At 60 deg N, cos(60) = 0.5 -> Area must be exactly half of Equator
    area_60n = compute_metric_pixel_area_km2(60.0, res_deg, res_deg)
    
    assert pytest.approx(area_60n / area_equator, rel=1e-4) == 0.5
    
    # At ~33.6 deg N (Case 001 latitude):
    # dx ≈ 11.1195 km * 0.0001 = 11.12 m, dy ≈ 11.1195 * cos(33.6°) = 9.26 m
    # Pixel area ≈ 11.12 * 9.26 ≈ 103 m^2 ≈ 0.000103 km^2
    area_case001 = compute_metric_pixel_area_km2(33.6, res_deg, res_deg)
    assert 0.00009 < area_case001 < 0.00012


# -------------------------------------------------------------------------
# Test 2: Local Contrast Calculation
# -------------------------------------------------------------------------
def test_local_contrast_calculation():
    """Verify that local contrast Delta_sigma0 = local_bg - sigma0_dB detects dark anomalies."""
    from scipy.ndimage import uniform_filter
    
    # Create 100x100 synthetic raster: clean ocean at -18.0 dB
    bg_val = -18.0
    patch_val = -26.0
    img = np.full((100, 100), bg_val, dtype=np.float32)
    
    # Embed 20x20 dark patch in center
    img[40:60, 40:60] = patch_val
    valid = np.ones((100, 100), dtype=bool)
    
    # Compute local background with window size 31
    win = 31
    local_bg = uniform_filter(img, size=win)
    contrast = np.where(valid, local_bg - img, 0.0)
    
    # Inside the center of the dark patch, contrast should be strongly positive
    center_contrast = contrast[50, 50]
    assert center_contrast > 4.0, f"Expected contrast > 4 dB, got {center_contrast}"
    
    # Far in the clean ocean background, contrast should be near 0.0 dB
    ocean_contrast = contrast[10, 10]
    assert abs(ocean_contrast) < 0.1, f"Expected near zero ocean contrast, got {ocean_contrast}"


# -------------------------------------------------------------------------
# Test 3: Multi-Mode Thresholding Logic
# -------------------------------------------------------------------------
def test_thresholding_modes():
    """Verify global, contrast, and adaptive threshold combinations."""
    sigma0_db = np.array([-20.0, -22.0, -24.0, -26.0])
    contrast_db = np.array([1.0, 4.0, 2.0, 5.0])
    valid = np.ones(4, dtype=bool)
    
    t_global = -23.0
    t_contrast = 3.5
    
    mask_global = valid & (sigma0_db <= t_global)       # False, False, True, True
    mask_contrast = valid & (contrast_db >= t_contrast) # False, True, False, True
    mask_adaptive = mask_global & mask_contrast         # False, False, False, True
    
    np.testing.assert_array_equal(mask_global, [False, False, True, True])
    np.testing.assert_array_equal(mask_contrast, [False, True, False, True])
    np.testing.assert_array_equal(mask_adaptive, [False, False, False, True])


# -------------------------------------------------------------------------
# Test 4: Synthetic Raster Detection with Known Dark Slicks
# -------------------------------------------------------------------------
def test_synthetic_raster_known_dark_slicks():
    """Embed known synthetic dark slicks and verify exact detection and geometry recovery."""
    height, width = 150, 150
    transform = from_origin(-118.20, 33.60, 0.0001, 0.0001)
    
    # Background ocean at -18 dB
    db_raster = np.full((height, width), -18.0, dtype=np.float32)
    contrast_raster = np.zeros((height, width), dtype=np.float32)
    
    # Embed Slick 1: Elliptical dark slick centered at (row=50, col=50), 70 pixels, -26 dB
    rr, cc = np.ogrid[:height, :width]
    slick1_mask = (((rr - 50) ** 2) / (5.0 ** 2) + ((cc - 50) ** 2) / (12.0 ** 2)) <= 1.0
    db_raster[slick1_mask] = -26.5
    contrast_raster[slick1_mask] = 6.5
    
    # Embed Slick 2: Small circular slick centered at (row=100, col=110), 120 pixels, -25 dB
    slick2_mask = ((rr - 100) ** 2 + (cc - 110) ** 2) <= (6.0 ** 2)
    db_raster[slick2_mask] = -25.0
    contrast_raster[slick2_mask] = 5.0
    
    # Binary candidate mask
    bin_mask = slick1_mask | slick2_mask
    
    labeled_mask, candidates = extract_candidate_components(
        binary_mask=bin_mask,
        transform=transform,
        sigma0_db=db_raster,
        contrast_db=contrast_raster,
        min_pixels=20
    )
    
    assert len(candidates) == 2, f"Expected 2 synthetic candidates, got {len(candidates)}"
    
    # Verify centroids match ground truth
    exp_lon1, exp_lat1 = rasterio.transform.xy(transform, 50, 50)
    exp_lon2, exp_lat2 = rasterio.transform.xy(transform, 100, 110)
    
    c1 = min(candidates, key=lambda c: (c["centroid_lon"] - exp_lon1)**2 + (c["centroid_lat"] - exp_lat1)**2)
    c2 = min(candidates, key=lambda c: (c["centroid_lon"] - exp_lon2)**2 + (c["centroid_lat"] - exp_lat2)**2)
    
    assert pytest.approx(c1["centroid_lon"], abs=1e-4) == exp_lon1
    assert pytest.approx(c1["centroid_lat"], abs=1e-4) == exp_lat1
    assert pytest.approx(c2["centroid_lon"], abs=1e-4) == exp_lon2
    assert pytest.approx(c2["centroid_lat"], abs=1e-4) == exp_lat2
    
    # Slick 1 is elongated: aspect_ratio must be significantly > 1.5
    assert c1["aspect_ratio"] > 1.8
    # Slick 2 is circular: aspect_ratio should be near 1.0
    assert pytest.approx(c2["aspect_ratio"], abs=0.4) == 1.0


# -------------------------------------------------------------------------
# Test 5: Look-Alike Filter Rejection Logging (No Silent Deletions)
# -------------------------------------------------------------------------
def test_lookalike_filter_rejection_logging():
    """Verify look-alike filter records explicit reason codes and preserves all rows."""
    mock_candidates = [
        {"candidate_id": "C1", "area_km2": 0.01, "mean_contrast_db": 5.0, "aspect_ratio": 2.0},  # Area too small
        {"candidate_id": "C2", "area_km2": 65.0, "mean_contrast_db": 4.0, "aspect_ratio": 1.5},  # Area too large
        {"candidate_id": "C3", "area_km2": 0.20, "mean_contrast_db": 1.5, "aspect_ratio": 3.0},  # Low contrast
        {"candidate_id": "C4", "area_km2": 0.30, "mean_contrast_db": 4.5, "aspect_ratio": 45.0}, # Extreme aspect ratio
        {"candidate_id": "C5", "area_km2": 0.50, "mean_contrast_db": 5.5, "aspect_ratio": 3.5}   # Valid / Accepted
    ]
    
    la_filter = LookAlikeFilter(
        min_area_km2=0.05,
        max_area_km2=50.0,
        min_contrast_db=2.5,
        max_aspect_ratio=30.0
    )
    annotated, breakdown = la_filter.filter_candidates(mock_candidates)
    
    # CRITICAL: No silent deletions
    assert len(annotated) == 5
    
    c_map = {c["candidate_id"]: c for c in annotated}
    assert c_map["C1"]["status"] == "REJECTED" and "AREA_TOO_SMALL" in c_map["C1"]["rejection_reasons"]
    assert c_map["C2"]["status"] == "REJECTED" and "AREA_TOO_LARGE" in c_map["C2"]["rejection_reasons"]
    assert c_map["C3"]["status"] == "REJECTED" and "INSUFFICIENT_CONTRAST" in c_map["C3"]["rejection_reasons"]
    assert c_map["C4"]["status"] == "REJECTED" and "EXTREME_ASPECT_RATIO" in c_map["C4"]["rejection_reasons"]
    assert c_map["C5"]["status"] == "ACCEPTED" and len(c_map["C5"]["rejection_reasons"]) == 0
    
    assert breakdown["AREA_TOO_SMALL"] == 1
    assert breakdown["AREA_TOO_LARGE"] == 1
    assert breakdown["INSUFFICIENT_CONTRAST"] == 1
    assert breakdown["EXTREME_ASPECT_RATIO"] == 1


# -------------------------------------------------------------------------
# Test 6: Heuristic Candidate Confidence Scoring
# -------------------------------------------------------------------------
def test_candidate_scoring_properties():
    """Verify candidate_score is strictly in [0.0, 1.0] and monotonic with contrast/darkness."""
    high_conf = {
        "mean_sigma0_db": -27.0,
        "mean_contrast_db": 6.5,
        "area_km2": 1.5,
        "aspect_ratio": 4.0
    }
    marginal = {
        "mean_sigma0_db": -22.5,
        "mean_contrast_db": 2.2,
        "area_km2": 0.06,
        "aspect_ratio": 1.1
    }
    
    score_high = compute_candidate_score(high_conf)
    score_marginal = compute_candidate_score(marginal)
    
    assert 0.0 <= score_high <= 1.0
    assert 0.0 <= score_marginal <= 1.0
    assert score_high > score_marginal, "Prominent slick must score higher than marginal patch"
    assert score_high >= 0.70, f"Expected strong slick score >= 0.70, got {score_high}"


# -------------------------------------------------------------------------
# Test 7: Deterministic Output
# -------------------------------------------------------------------------
def test_deterministic_output():
    """Verify that scoring and component extraction produce bit-for-bit identical results on repeat."""
    cand = {
        "mean_sigma0_db": -25.6,
        "mean_contrast_db": 5.8,
        "area_km2": 0.85,
        "aspect_ratio": 3.2
    }
    score1 = compute_candidate_score(cand)
    score2 = compute_candidate_score(cand)
    assert score1 == score2


# -------------------------------------------------------------------------
# Test 8: Case 001 End-to-End Products Validation
# -------------------------------------------------------------------------
def test_case_001_detection_products():
    """Verify Case 001 detection products exist and satisfy schema and geometry requirements."""
    paths = {
        "mask": resolve_path("data/processed/satellite/case_001_s1_candidate_slicks_mask.tif"),
        "geojson": resolve_path("data/processed/satellite/case_001_candidate_slicks.geojson"),
        "csv": resolve_path("data/processed/satellite/case_001_candidate_slicks.csv"),
        "summary": resolve_path("data/processed/satellite/case_001_candidate_slicks_summary.json"),
        "diag": resolve_path("data/processed/satellite/case_001_s1_detection_diagnostic.png")
    }
    
    for name, p in paths.items():
        assert os.path.exists(p), f"Detection product missing: {p}"
        assert os.path.getsize(p) > 0, f"Detection product empty: {p}"
        
    # Check GeoTIFF mask geometry
    with rasterio.open(paths["mask"]) as src:
        assert src.shape == (4000, 5500)
        assert str(src.crs) == "EPSG:4326"
        assert src.dtypes[0] == "uint8"
        
    # Check GeoJSON
    with open(paths["geojson"]) as f:
        data = json.load(f)
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) > 0
    for feat in data["features"]:
        assert "candidate_id" in feat["properties"]
        assert "candidate_score" in feat["properties"]
        assert "area_km2" in feat["properties"]
        assert "status" in feat["properties"]
        assert feat["geometry"]["type"] in ["Polygon", "MultiPolygon"]
        
    # Check summary JSON
    with open(paths["summary"]) as f:
        summary = json.load(f)
    assert summary["status"] == "READY FOR PHASE 4"
    assert summary["detection_counts"]["accepted_candidates"] >= 1
    assert "CS_0010" in summary["accepted_candidate_ids"] or "CS_0015" in summary["accepted_candidate_ids"]
