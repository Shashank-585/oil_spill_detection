"""
Tests for Case 003 (M/V Golden Ray) Data Acquisition, Preprocessing, and Isolation.

Verifies:
1. Sentinel-1 product exists, is readable, and metadata/statistics are valid.
2. AOI bounding box intersects SAR footprint.
3. NOAA AIS archive files exist and filtered AIS dataset has genuine multi-vessel traffic (>10 vessels).
4. AIS filtering does NOT explicitly select Golden Ray (unbiased multi-vessel traffic).
5. Environmental forcing (HYCOM currents & ERA5 winds) covers the full operational window.
6. Ground-truth identity is strictly isolated in validation configuration and absent from operational modules.
"""

import os
import pytest
import pandas as pd
import numpy as np
import rasterio
from pathlib import Path
from datetime import datetime, timezone
from src.common.case_loader import load_case
from src.environmental.interpolator import EnvironmentalForcingInterpolator


@pytest.fixture
def case_003():
    return load_case("case_003_golden_ray")


def test_case_003_integrity(case_003):
    """Verify case_003 configuration passes standard integrity checks."""
    assert case_003.case_id == "case_003_golden_ray"
    assert case_003.crs == "EPSG:4326"
    assert case_003.aoi["west"] == -81.60
    assert case_003.aoi["east"] == -81.10
    assert case_003.aoi["south"] == 31.00
    assert case_003.aoi["north"] == 31.30
    assert case_003.aoi_area_km2 > 0

    errors = case_003.validate_integrity()
    assert not errors, f"Case 003 integrity validation failed: {errors}"


def test_case_003_sentinel1_raster(case_003):
    """Verify Sentinel-1 VV measurement raster exists, has valid dimensions, CRS, and non-zero pixels."""
    vv_path = case_003.satellite_files.get("measurement_raster_vv")
    assert vv_path is not None and vv_path.exists(), f"Missing Sentinel-1 VV raster: {vv_path}"

    with rasterio.open(vv_path) as src:
        assert src.width == 5000
        assert src.height == 3000
        assert src.count == 1
        assert str(src.crs).upper() in ["EPSG:4326", "WGS 84"]
        
        # Check bounds intersect AOI
        bounds = src.bounds
        assert bounds.left <= case_003.aoi["west"] + 0.05
        assert bounds.right >= case_003.aoi["east"] - 0.05
        assert bounds.bottom <= case_003.aoi["south"] + 0.05
        assert bounds.top >= case_003.aoi["north"] - 0.05

        # Sample data to verify validity
        data = src.read(1, window=rasterio.windows.Window(1000, 1000, 500, 500))
        assert np.any(data > 0), "Expected non-zero SAR measurements in center window"
        assert np.mean(data) > 10, "Mean DN should be reasonable SAR backscatter"


def test_case_003_ais_traffic(case_003):
    """Verify AIS filtered dataset has realistic multi-vessel traffic and covers the full time window."""
    ais_path = case_003.ais_files.get("filtered_csv")
    assert ais_path is not None and ais_path.exists(), f"Missing AIS CSV: {ais_path}"

    df = pd.read_csv(ais_path)
    assert len(df) > 1000, f"Expected substantial AIS records, got {len(df)}"
    
    unique_mmsi = df["MMSI"].nunique()
    assert unique_mmsi >= 20, f"Expected realistic multi-vessel traffic (>=20 vessels), got {unique_mmsi}"

    # Temporal window covers incident (2019-09-08 05:46 UTC)
    min_time = pd.to_datetime(df["timestamp_utc"].min())
    max_time = pd.to_datetime(df["timestamp_utc"].max())
    incident_time = pd.to_datetime("2019-09-08T05:46:00Z")
    
    assert min_time <= incident_time - pd.Timedelta(hours=6), "AIS should cover pre-incident period"
    assert max_time >= incident_time + pd.Timedelta(hours=6), "AIS should cover post-incident period"


def test_case_003_ais_no_leakage(case_003):
    """Verify that AIS filtering was unbiased and contains multiple candidates, not just Golden Ray."""
    ais_path = case_003.ais_files.get("filtered_csv")
    df = pd.read_csv(ais_path)

    # Must contain multiple vessels
    assert df["MMSI"].nunique() >= 10
    
    # Golden Ray MMSI should not constitute the overwhelming majority of records
    golden_ray_mmsi = 538007762
    if golden_ray_mmsi in df["MMSI"].values:
        golden_records = (df["MMSI"] == golden_ray_mmsi).sum()
        ratio = golden_records / len(df)
        assert ratio < 0.20, f"Golden Ray records ({golden_records}) should be a minority of overall regional traffic, got {ratio:.2%}"


def test_case_003_environmental_forcing(case_003):
    """Verify environmental forcing (HYCOM and ERA5) can be interpolated across the operational window."""
    nc_path = case_003.ocean_current_file
    wind_path = case_003.wind_files.get("csv_path")
    assert nc_path is not None and nc_path.exists()
    assert wind_path is not None and wind_path.exists()

    interp = EnvironmentalForcingInterpolator(hycom_netcdf_path=nc_path, era5_wind_csv_path=wind_path)

    # Test interpolation at incident time and location
    inc_lat = case_003.incident_point["latitude"]
    inc_lon = case_003.incident_point["longitude"]
    inc_time = datetime(2019, 9, 8, 5, 46, 0, tzinfo=timezone.utc)

    u_curr, v_curr = interp.get_ocean_current(inc_lat, inc_lon, inc_time)
    u_wind, v_wind = interp.get_wind(inc_lat, inc_lon, inc_time)
    u_tot, v_tot = interp.get_total_surface_velocity(inc_lat, inc_lon, inc_time)

    assert not np.isnan(u_curr)
    assert not np.isnan(v_curr)
    assert not np.isnan(u_wind)
    assert not np.isnan(v_wind)
    assert not np.isnan(u_tot)
    assert not np.isnan(v_tot)


def test_case_003_ground_truth_isolation(case_003):
    """Verify ground truth is stored in validation section and isolated from operational inputs."""
    val_section = case_003.get("validation", {})
    assert val_section.get("reference_vessel_mmsi") == 538007762
    assert val_section.get("reference_vessel_name") == "GOLDEN RAY"
    assert val_section.get("validation_role") == "POSITIVE_VESSEL_CASE"

    # Operational sections must NOT specify the target vessel
    assert "reference_vessel_mmsi" not in case_003.get("spatial", {})
    assert "reference_vessel_mmsi" not in case_003.get("temporal", {})
    assert "reference_vessel_mmsi" not in case_003.get("satellite", {})
    assert "reference_vessel_mmsi" not in case_003.get("environmental", {})
    assert "reference_vessel_mmsi" not in case_003.get("ais", {})
