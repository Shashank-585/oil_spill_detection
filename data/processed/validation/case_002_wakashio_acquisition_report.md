# Case 002 (MV Wakashio) — Phase 12.6 SAR Acquisition & Data Verification Report

> **Objective**: Acquisition and verification of primary Sentinel-1 SAR physical datasets for `case_002_wakashio`.  
> **Status**: **`SATELLITE_DATA_READY`** (Physical VV measurement raster and calibration XML schema acquired and verified).  
> **Scientific Guardrail**: Strict ground truth isolation preserved. Zero algorithm modifications. No pipeline execution.

---

## 1. Executive Summary & Verification State

Following the Phase 12.5 catalogue investigation, Phase 12.6 successfully downloaded, reprojected, and verified the primary Sentinel-1 SAR observation and XML calibration lookup table for `case_002_wakashio` from Microsoft Planetary Computer:

| Physical Data Pillar | Target File | Status | Size | SHA256 (first 16) | Format / Dimensions |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Sentinel-1 VV Measurement** | `data/raw/satellite/case_002_wakashio_s1_measurement_vv.tif` | **ACQUIRED** | 11.12 MB | `ab1b434ff9cdb1ff...` | GeoTIFF (3000 x 4000), uint16, EPSG:4326 |
| **Sentinel-1 Calibration XML** | `data/raw/satellite/case_002_wakashio_calibration_vv.xml` | **ACQUIRED** | 1.00 MB | `fb01dc2ed2b8ef1f...` | XML, 27 calibration vectors |
| **Separate AOI Cropped** | `data/raw/satellite/case_002_wakashio_s1_measurement_vv_aoi_cropped.tif` | **ACQUIRED** | 11.12 MB | `3525527dd56bce5a...` | GeoTIFF (3000 x 4000), uint16, EPSG:4326 |
| **Regional Source Product** | `data/raw/satellite/case_002_wakashio_s1_measurement_vv_source.tif` | **ACQUIRED** | 38.68 MB | `524aa8500a96d490...` | GeoTIFF (6000 x 8000), uint16, EPSG:4326 |
| **HYCOM Surface Currents** | `data/raw/environmental/case_002_wakashio_ocean_currents.nc` | **ACQUIRED** | 20.8 KB | `a0a47067ff403be8...` | Classic NetCDF (25 steps, 16x11) |
| **ERA5 10m Surface Winds** | `data/raw/environmental/case_002_wakashio_wind_era5.csv` | **ACQUIRED** | 6.4 KB | `bc14096073a45752...` | CSV (96 hourly continuous steps) |
| **AIS Dynamic Trajectories** | `data/raw/ais/case_002_wakashio_ais_filtered.csv` | **BLOCKED** | N/A | N/A | Commercial license barrier (Indian Ocean) |

---

## 2. Sentinel-1 SAR Verification Metrics

### Primary Measurement Raster (`case_002_wakashio_s1_measurement_vv.tif`)
- **Product ID**: `S1B_IW_GRDH_1SDV_20200810T013755_20200810T013820_022854_02B625_672D.SAFE`
- **Sensing Timestamp**: `2020-08-10T01:38:07.540969Z`
- **Instrument Mode**: Interferometric Wide Swath (IW)
- **Polarization**: VV (vertical transmit, vertical receive)
- **File Size**: 11,658,564 bytes (11.12 MB)
- **SHA256**: `ab1b434ff9cdb1ffe669338eff696785c55ffc47a6ee6452b5aff8de04c707f0`
- **Dimensions**: `(3000, 4000)` (Height: 3000 pixels, Width: 4000 pixels)
- **Coordinate Reference System (CRS)**: `EPSG:4326` (WGS 84 geographic coordinates)
- **Geographic Bounds**: `BoundingBox(left=57.50, bottom=-20.60, right=57.90, top=-20.30)`
- **Pixel Resolution**: `(0.000100, 0.000100)` degrees (~10.4 m lon, ~11.1 m lat)
- **Data Type**: `uint16` (16-bit unsigned integer Digital Numbers)
- **Valid Pixels**: 10,179,604 / 12,000,000 (84.83% valid marine/lagoon pixels)
- **NoData Value**: 0 (15.17% NoData along coastal/outer boundary padding)
- **Digital Number (DN) Distribution**:
  - Minimum: 17
  - Maximum: 6,183
  - Mean: 155.0
  - Median: 126.0

### Radiometric Calibration Schema (`case_002_wakashio_calibration_vv.xml`)
- **File Size**: 1,002,307 bytes (0.96 MB)
- **SHA256**: `fb01dc2ed2b8ef1f6c98f4ed8e1f875e5576a7e4a1f2ab4e27f7c44fef190d1e`
- **Root Element**: `<calibration>`
- **Mission ID**: `S1B` | **Product Type**: `GRD` | **Polarisation**: `VV` | **Mode**: `IW`
- **Start Time**: `2020-08-10T01:37:55.041956Z`
- **Stop Time**: `2020-08-10T01:38:20.039982Z`
- **Absolute Orbit**: `22854` | **Mission Data Take ID**: `177701`
- **Calibration Vector Count**: 27 line vectors across range lines 0 to 16,854
- **Verification Result**: 100% compliant with ESA Sentinel-1 calibration specification and existing `RadiometricCalibrator` interface.

### Regional Source Preservation & AOI Cropped Derivative
In accordance with instructions to preserve the source product:
1. `case_002_wakashio_s1_measurement_vv_source.tif`: Preserves the wider regional footprint `[57.30°E to 58.10°E, -20.70°S to -20.10°S]` at `(6000, 8000)` pixels (38.68 MB, SHA256: `524aa8500a96d490...`).
2. `case_002_wakashio_s1_measurement_vv_aoi_cropped.tif`: Separate dedicated AOI-cropped derivative matching `case_002_wakashio_s1_measurement_vv.tif`.

---

## 3. Comparison with Case 001 SAR Interface

| Parameter | Case 001 (Huntington Beach) | Case 002 (MV Wakashio) | Architectural Compatibility |
| :--- | :--- | :--- | :---: |
| **Mission / Sensor** | Sentinel-1A C-SAR | Sentinel-1B C-SAR | **100% Identical C-band specs** |
| **Mode / Product** | IW GRDH | IW GRDH | **100% Identical** |
| **Polarization** | VV | VV | **100% Identical** |
| **CRS** | `EPSG:4326` | `EPSG:4326` | **100% Identical** |
| **Pixel Spacing** | 0.0001 deg (~10 m) | 0.0001 deg (~10 m) | **100% Identical** |
| **Dtype** | `uint16` DN | `uint16` DN | **100% Identical** |
| **NoData Value** | 0 | 0 | **100% Identical** |
| **Calibration Table** | SAFE XML (27 vectors) | SAFE XML (27 vectors) | **100% Identical schema** |
| **Dimensions** | (4000, 5500) | (3000, 4000) | **Fully supported** |
| **File Size** | 12.37 MB | 11.12 MB | **Fully supported** |

---

## 4. Overall Case Readiness Assessment

```text
========================================================================================
CASE 002 WAKASHIO READINESS STATUS: SATELLITE_DATA_READY (AIS_PENDING)
========================================================================================

PHYSICAL PILLAR AUDIT:
1. SATELLITE SAR:       SATELLITE_DATA_READY (VV measurement raster and XML LUT verified)
2. OCEAN CURRENTS:      ACQUIRED & VERIFIED (HYCOM GLBy0.08 experiment 93.0 NetCDF)
3. 10m WINDS:           ACQUIRED & VERIFIED (ECMWF ERA5 continuous hourly CSV)
4. AIS TRAJECTORIES:    BLOCKED (Indian Ocean multi-vessel dynamic AIS requires commercial license)
5. GROUND TRUTH:        VERIFIED & STRICTLY ISOLATED (IMO 9337119, MMSI 372711000)

DATA INTEGRITY CHECKS: PASSED (CaseConfig validates all satellite and environmental files)
```
