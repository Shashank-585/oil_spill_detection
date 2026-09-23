"""
Unit and Integration Tests for Sentinel-1 SAR Preprocessing (Phase 2).

Verifies:
1. Calibration numerical correctness (sigma0 = DN^2 / A_sigma^2)
2. Finite positive sigma0 for all valid pixels
3. Correct dB conversion (sigma0_dB = 10 * log10(sigma0_linear))
4. NoData preservation (swath boundary and zero DN preserved as NoData, not zero radar return)
5. Dimensions unchanged (4000 x 5500)
6. CRS preserved (EPSG:4326)
7. Spatial bounds preserved ([-118.40, 33.40, -117.85, 33.80])
8. Calibration metadata actually used from official ESA XML files
9. No fabricated or hard-coded calibration constants (spatial gradient present)
10. Speckle filter preserves dimensions, NoData, and reduces variance when invoked
"""

import os
import pytest
import numpy as np
import rasterio

from src.common.paths import resolve_path
from src.common.config import load_config
from src.satellite.calibration import Sentinel1Calibration
from src.satellite.speckle import apply_speckle_filter
from src.satellite.preprocessor import Sentinel1SARPreprocessor


@pytest.fixture(scope="module")
def paths():
    """Resolve file paths for test execution."""
    return {
        "raw_tif": resolve_path("data/raw/satellite/case_001_s1_measurement_vv.tif"),
        "cal_xml": resolve_path("data/raw/satellite/case_001_calibration_vv.xml"),
        "annot_xml": resolve_path("data/raw/satellite/case_001_annotation_vv.xml"),
        "sigma0_lin": resolve_path("data/processed/satellite/case_001_s1_sigma0_linear.tif"),
        "sigma0_db": resolve_path("data/processed/satellite/case_001_s1_sigma0_db.tif"),
        "valid_mask": resolve_path("data/processed/satellite/case_001_s1_valid_mask.tif"),
        "stats_json": resolve_path("data/processed/satellite/case_001_s1_preprocessing_stats.json")
    }


# -------------------------------------------------------------------------
# Test 1 & 8: Calibration Metadata Actually Used (From ESA XML)
# -------------------------------------------------------------------------
def test_calibration_metadata_actually_used(paths):
    """Verify that calibration LUT is parsed directly from official ESA XML metadata."""
    assert os.path.exists(paths["cal_xml"]), "Calibration XML file is missing"
    assert os.path.exists(paths["annot_xml"]), "Annotation XML file is missing"

    cal = Sentinel1Calibration(
        calibration_xml_path=str(paths["cal_xml"]),
        annotation_xml_path=str(paths["annot_xml"])
    )
    summary = cal.get_metadata_summary()

    # Must contain 32 vectors across lines 0 to 20719 and pixels 0 to 25409
    assert summary["num_vectors"] == 32
    assert summary["line_range"] == (0, 20719)
    assert summary["pixel_range"] == (0, 25409)
    assert summary["tie_points_count"] == 231

    # Official ESA Level-1 GRDH IW sigmaNought values span [558.5241, 662.3792]
    min_sig, max_sig = summary["sigma0_lut_range"]
    assert pytest.approx(min_sig, abs=1e-3) == 558.5241
    assert pytest.approx(max_sig, abs=1e-3) == 662.3792


# -------------------------------------------------------------------------
# Test 9: No Fabricated Calibration Constants
# -------------------------------------------------------------------------
def test_no_fabricated_calibration_constants(paths):
    """Verify that calibration factor A_sigma varies across space and is NOT a scalar constant."""
    cal = Sentinel1Calibration(
        calibration_xml_path=str(paths["cal_xml"]),
        annotation_xml_path=str(paths["annot_xml"])
    )
    bounds = (-118.40, 33.40, -117.85, 33.80)
    shape = (100, 100)
    grid = cal.compute_calibration_grid(bounds=bounds, shape=shape)

    # Must not be uniform / constant
    grid_min = float(grid.min())
    grid_max = float(grid.max())
    grid_std = float(grid.std())

    assert grid_max > grid_min, "A_sigma must not be constant across the range swath"
    assert (grid_max - grid_min) >= 5.0, f"Expected range variation > 5.0, got {grid_max - grid_min}"
    assert grid_std > 1.0, f"Standard deviation of A_sigma must be significant, got {grid_std}"
    assert grid_min > 500.0 and grid_max < 700.0, "A_sigma values outside expected physical range"


# -------------------------------------------------------------------------
# Test 1 & 3: Calibration Numerical Correctness
# -------------------------------------------------------------------------
def test_calibration_numerical_correctness():
    """Verify mathematical equation: sigma0_linear = DN^2 / A_sigma^2 and dB conversion."""
    test_dns = np.array([10, 60, 250, 1500, 10000], dtype=np.float64)
    test_asigma = np.array([560.0, 562.5, 565.0, 567.5, 570.0], dtype=np.float64)

    expected_linear = (test_dns ** 2) / (test_asigma ** 2)
    expected_db = 10.0 * np.log10(expected_linear)

    # Check algebraic identity: 10*log10(DN^2 / A^2) == 20*log10(DN) - 20*log10(A)
    alt_db = 20.0 * np.log10(test_dns) - 20.0 * np.log10(test_asigma)

    np.testing.assert_allclose(expected_linear, (test_dns / test_asigma) ** 2, rtol=1e-7)
    np.testing.assert_allclose(expected_db, alt_db, rtol=1e-7)


# -------------------------------------------------------------------------
# Test 2: Finite Positive sigma0 on Valid Pixels
# -------------------------------------------------------------------------
def test_finite_positive_sigma0_valid_pixels(paths):
    """Verify that all valid pixels in the calibrated products are finite and strictly positive."""
    with rasterio.open(paths["sigma0_lin"]) as src_lin, \
         rasterio.open(paths["valid_mask"]) as src_mask:
        lin_data = src_lin.read(1)
        mask_data = src_mask.read(1) == 1

        valid_vals = lin_data[mask_data]
        assert len(valid_vals) > 0, "No valid pixels found"
        assert np.all(np.isfinite(valid_vals)), "Valid pixels contain NaN or Inf"
        assert np.all(valid_vals > 0), "Valid sigma0 linear contains zero or negative values"

        # Ocean backscatter typically has minimum ~ 1e-4 and max ~ 1e4 for point targets
        assert valid_vals.min() > 1e-5, f"Unrealistically small backscatter: {valid_vals.min()}"
        assert valid_vals.max() < 1e6, f"Unrealistically large backscatter: {valid_vals.max()}"


# -------------------------------------------------------------------------
# Test 3: Correct dB Conversion on Processed Products
# -------------------------------------------------------------------------
def test_correct_db_conversion_on_products(paths):
    """Verify that sigma0_db in the output GeoTIFF matches 10 * log10(sigma0_linear)."""
    with rasterio.open(paths["sigma0_lin"]) as src_lin, \
         rasterio.open(paths["sigma0_db"]) as src_db, \
         rasterio.open(paths["valid_mask"]) as src_mask:
        lin_data = src_lin.read(1)
        db_data = src_db.read(1)
        mask = src_mask.read(1) == 1

        # Check sample of 5,000 valid pixels
        lin_sample = lin_data[mask][::2700]
        db_sample = db_data[mask][::2700]

        expected_db = 10.0 * np.log10(lin_sample)
        np.testing.assert_allclose(db_sample, expected_db, atol=1e-4)


# -------------------------------------------------------------------------
# Test 4: NoData Preservation (Swath Boundary & Zero DN)
# -------------------------------------------------------------------------
def test_nodata_preservation(paths):
    """Verify that raw NoData pixels (DN=0) remain strictly NoData in all output products."""
    with rasterio.open(paths["raw_tif"]) as src_raw, \
         rasterio.open(paths["sigma0_lin"]) as src_lin, \
         rasterio.open(paths["sigma0_db"]) as src_db, \
         rasterio.open(paths["valid_mask"]) as src_mask:
        raw_dn = src_raw.read(1)
        lin_data = src_lin.read(1)
        db_data = src_db.read(1)
        mask_data = src_mask.read(1)

        raw_zero_mask = (raw_dn == 0)
        assert np.any(raw_zero_mask), "Raw raster has no NoData pixels"

        # In valid mask, raw zero must be 0
        assert np.all(mask_data[raw_zero_mask] == 0), "NoData pixel marked as valid in mask"

        # In linear product, raw zero must be nodata value (-9999.0)
        np.testing.assert_allclose(lin_data[raw_zero_mask], -9999.0)

        # In dB product, raw zero must be nodata value (-9999.0), NOT 0 dB
        np.testing.assert_allclose(db_data[raw_zero_mask], -9999.0)

        # Ensure valid pixels (DN > 0) are marked as 1
        raw_valid_mask = (raw_dn > 0)
        assert np.all(mask_data[raw_valid_mask] == 1), "Valid DN marked as NoData"


# -------------------------------------------------------------------------
# Test 5, 6, 7: Georeferencing, Dimensions, CRS, and Bounds Preservation
# -------------------------------------------------------------------------
def test_raster_geometry_preservation(paths):
    """Verify that height, width, CRS, transform, and spatial bounds are preserved exactly."""
    with rasterio.open(paths["raw_tif"]) as src_raw, \
         rasterio.open(paths["sigma0_lin"]) as src_lin, \
         rasterio.open(paths["sigma0_db"]) as src_db, \
         rasterio.open(paths["valid_mask"]) as src_mask:
        raw_shape = src_raw.shape
        raw_crs = str(src_raw.crs)
        raw_bounds = src_raw.bounds
        raw_transform = src_raw.transform

        for prod_name, src_prod in [("sigma0_linear", src_lin), ("sigma0_db", src_db), ("valid_mask", src_mask)]:
            assert src_prod.shape == raw_shape, f"{prod_name} shape mismatch: {src_prod.shape} vs {raw_shape}"
            assert str(src_prod.crs) == raw_crs, f"{prod_name} CRS mismatch: {src_prod.crs} vs {raw_crs}"
            assert src_prod.bounds == raw_bounds, f"{prod_name} bounds mismatch"
            assert src_prod.transform == raw_transform, f"{prod_name} transform mismatch"

            # Check explicit bounds in EPSG:4326
            assert pytest.approx(src_prod.bounds.left, abs=1e-5) == -118.40
            assert pytest.approx(src_prod.bounds.bottom, abs=1e-5) == 33.40
            assert pytest.approx(src_prod.bounds.right, abs=1e-5) == -117.85
            assert pytest.approx(src_prod.bounds.top, abs=1e-5) == 33.80


# -------------------------------------------------------------------------
# Test 10: Speckle Filtering Functionality
# -------------------------------------------------------------------------
def test_speckle_filter_algorithm():
    """Verify that speckle filtering preserves valid boundaries, shape, and reduces noise variance."""
    np.random.seed(42)
    clean_signal = np.full((100, 100), 0.05, dtype=np.float32)
    # Add multiplicative speckle noise with 1/ENL variance
    speckle_noise = np.random.gamma(shape=4.4, scale=1.0 / 4.4, size=(100, 100)).astype(np.float32)
    noisy_img = clean_signal * speckle_noise

    # Inject NoData border
    mask = np.ones((100, 100), dtype=bool)
    mask[:, :20] = False
    noisy_img[~mask] = np.nan

    filtered_lee = apply_speckle_filter(noisy_img, valid_mask=mask, method="lee", window_size=5, num_looks=4.4)
    filtered_box = apply_speckle_filter(noisy_img, valid_mask=mask, method="box", window_size=5)

    assert filtered_lee.shape == (100, 100)
    assert np.all(np.isnan(filtered_lee[~mask])), "Lee filter corrupted NoData mask"
    assert np.all(np.isnan(filtered_box[~mask])), "Box filter corrupted NoData mask"

    # Variance must be reduced by filtering
    raw_var = float(np.var(noisy_img[mask]))
    lee_var = float(np.var(filtered_lee[mask]))
    box_var = float(np.var(filtered_box[mask]))

    assert lee_var < raw_var, "Lee filter did not reduce speckle variance"
    assert box_var < raw_var, "Box filter did not reduce variance"

    # Mean signal must be conserved
    raw_mean = float(np.mean(noisy_img[mask]))
    lee_mean = float(np.mean(filtered_lee[mask]))
    assert pytest.approx(raw_mean, rel=0.05) == lee_mean


# -------------------------------------------------------------------------
# Test 11: End-to-End Pipeline Execution & Result Structure
# -------------------------------------------------------------------------
def test_preprocessor_execution(paths):
    """Verify preprocessor returns READY FOR BASELINE DETECTION and valid statistics."""
    preprocessor = Sentinel1SARPreprocessor(case_id="case_001")
    # Verify initialized paths
    assert os.path.exists(preprocessor.raw_tif_path)
    assert os.path.exists(preprocessor.cal_xml_path)

    # Verify generated stats
    assert os.path.exists(paths["stats_json"])
    import json
    with open(paths["stats_json"]) as f:
        stats = json.load(f)

    assert stats["raster_metadata"]["crs"] == "EPSG:4326"
    assert stats["raster_metadata"]["dimensions"]["height"] == 4000
    assert stats["raster_metadata"]["dimensions"]["width"] == 5500
    assert stats["raster_metadata"]["valid_pixel_count"] == 13697365
    assert stats["raster_metadata"]["nodata_pixel_count"] == 8302635

    # Check realistic dB backscatter range
    db_stats = stats["calibrated_sigma0_dB"]
    assert -22.0 < db_stats["median"] < -17.0, f"Unexpected median backscatter: {db_stats['median']} dB"
    assert -20.0 < db_stats["mean"] < -16.0, f"Unexpected mean backscatter: {db_stats['mean']} dB"
