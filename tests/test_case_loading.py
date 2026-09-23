"""Tests for Case loading and validation."""
import pytest
from datetime import timezone
from src.common.case_loader import load_case


def test_load_case_001():
    case = load_case("case_001")
    assert case.case_id == "case_001"
    assert case.crs == "EPSG:4326"
    assert "west" in case.aoi and "north" in case.aoi
    assert case.aoi["west"] == -118.40
    assert case.aoi["north"] == 33.80

    # Strict UTC timestamps
    assert case.satellite_timestamp_utc.tzinfo == timezone.utc
    assert case.search_start_utc.tzinfo == timezone.utc
    assert case.search_end_utc.tzinfo == timezone.utc
    assert case.search_start_utc < case.satellite_timestamp_utc <= case.search_end_utc

    # Area calculation
    assert case.aoi_area_km2 > 0
    assert 1000 < case.aoi_area_km2 < 3000  # Approx 0.55 deg x 0.40 deg ≈ 2,100 km²

    # Verify all referenced local files exist
    errors = case.validate_integrity()
    assert not errors, f"Case 001 integrity validation failed: {errors}"
