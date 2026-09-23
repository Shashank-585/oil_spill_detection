# Case 002 (MV Wakashio) Data Acquisition & Case Verification Plan

> **Scientific Role**: Primary Target for Real-World Positive Vessel Attribution Validation (Tier A Ground Truth).  
> **Status**: Gated / Pending Data Acquisition.  
> **Rule**: Strict isolation between algorithm inputs and reference ground truth.

---

## 1. Executive Summary & Missing Dataset Audit

| Required Input | Target Local File Path | Present Locally? | Status | Verified vs Cataloged |
| :--- | :--- | :---: | :---: | :---: |
| **Sentinel-1 Scene & Metadata** | `data/raw/satellite/case_002_wakashio_calibration_vv.xml` | **NO** | Missing | Merely Cataloged |
| **SAR Measurement Raster** | `data/raw/satellite/case_002_wakashio_s1_measurement_vv.tif` | **NO** | Missing | Merely Cataloged |
| **Regional AIS Trajectories** | `data/raw/ais/case_002_wakashio_ais_filtered.csv` | **NO** | Missing | Merely Cataloged |
| **HYCOM Surface Ocean Currents** | `data/raw/environmental/case_002_wakashio_ocean_currents.nc` | **NO** | Missing | Merely Cataloged |
| **ERA5 10m Surface Winds** | `data/raw/environmental/case_002_wakashio_wind_era5.csv` | **NO** | Missing | Merely Cataloged |
| **Reference Ground Truth** | `data/cases/case_002_wakashio.yaml` (isolated block) | **YES** | Verified | **Verified & Documented** |

---

## 2. Dataset Specifications & Acquisition Requirements

### 1. Sentinel-1 SAR Scene & Measurement Raster
- **Target Scene ID**: `S1A_IW_GRDH_1SDV_20200806T014312_20200806T014337_033780_03EC26`
- **Platform / Instrument**: Sentinel-1A / C-SAR, Interferometric Wide Swath (IW), Ground Range Detected High Resolution (GRDH)
- **Polarization**: VV (primary detection channel), VH (cross-polarization)
- **Observation Timestamp**: `2020-08-06T01:43:24Z`
- **Spatial Coverage**: AOI Bounding Box `[57.50°E, -20.60°S, 57.90°E, -20.30°S]` (Pointe d'Esny and southeastern coral reef lagoon, Mauritius)
- **CRS Convention**: `EPSG:4326` (WGS 84 geographical coordinates) or original UTM Zone 40S (`EPSG:32740`) with valid affine GeoTransform
- **Required Format**: Cloud-Optimized GeoTIFF (`.tif`), 16-bit unsigned integer Digital Number (DN) or calibrated $\sigma^0$
- **Calibration Lookup Table**: SAFE format `calibration-s1a-iw-grd-vv-*.xml` containing vector grids for radiometric calibration to $\sigma^0$
- **Acquisition Source**: Copernicus Data Space Ecosystem (CDSE) / Microsoft Planetary Computer STAC API (`sentinel-1-grd` collection)
- **Integrity Checks (Post-Download)**:
  - Valid GeoTIFF header with non-empty affine transform and EPSG projection
  - Dimensions $> 2000 \times 2000$ pixels covering the entire AOI
  - Non-zero finite pixel values across the marine lagoon
  - XML calibration lookup table parses correctly with matching line/pixel vectors

### 2. AIS Historical Vessel Trajectory Data
- **Target File**: `data/raw/ais/case_002_wakashio_ais_filtered.csv`
- **Required Format**: CSV with standard tabular schema:
  - `mmsi` (int64)
  - `timestamp` (ISO 8601 UTC string: `YYYY-MM-DDTHH:MM:SSZ`)
  - `lon` / `longitude` (float64, degrees East: 57.2 to 58.2)
  - `lat` / `latitude` (float64, degrees North: -20.8 to -20.0)
  - `sog` (float, knots)
  - `cog` (float, degrees: 0.0–360.0)
  - `vessel_name` (string, optional)
- **Temporal Coverage**: At least 72 to 280 hours preceding observation: from grounding (`2020-07-25T15:25:00Z`) through post-observation (`2020-08-07T00:00:00Z`)
- **Spatial Coverage**: Southeastern Mauritius maritime zone (AOI: `[57.20°E, -20.80°S, 58.20°E, -20.00°S]`)
- **Candidate Vessel Presence**: Must include MV WAKASHIO (`MMSI 356508000`) and all passing commercial traffic within 50 km
- **Acquisition Source**: Spire Global / MarineTraffic Historical Research Archive / Global Fishing Watch (GFW) / Indian Ocean regional VTS
- **Integrity Checks (Post-Download)**:
  - Zero latitude/longitude out-of-bounds records
  - Chronological timestamp monotonicity per MMSI
  - At least 1 candidate vessel matching MMSI 356508000 with known stationary pings on the reef

### 3. HYCOM Surface Ocean Currents
- **Target File**: `data/raw/environmental/case_002_wakashio_ocean_currents.nc`
- **Required Format**: NetCDF-4 (`.nc`)
- **Required Variables**: `water_u` (eastward surface velocity, m/s), `water_v` (northward surface velocity, m/s)
- **Dimensions**: `time`, `lat`, `lon` (and single surface `depth` = 0 m)
- **Temporal Coverage**: `2020-08-04T00:00:00Z` to `2020-08-07T00:00:00Z` (at 3-hourly or hourly intervals)
- **Spatial Coverage**: Grid covering at least `[57.3°E, -20.7°S]` to `[58.1°E, -20.1°S]`
- **CRS Convention**: Regular latitude/longitude grid (`EPSG:4326`)
- **Acquisition Source**: HYCOM GLBy0.04 (Experiment 93.0) or Copernicus Marine Service (CMEMS Global Ocean Physics Analysis `GLOBAL_ANALYSISFORECAST_PHY_001_024`)
- **Integrity Checks (Post-Download)**:
  - NetCDF file opens cleanly with `xarray` / `netCDF4`
  - Current magnitudes strictly within physically realistic bounds ($0.0 \le \sqrt{u^2 + v^2} \le 2.5$ m/s)
  - No NaNs over open water pixels within the drift domain

### 4. ECMWF ERA5 10m Surface Wind
- **Target File**: `data/raw/environmental/case_002_wakashio_wind_era5.csv`
- **Required Format**: CSV with columns `timestamp`, `u10`, `v10` (or `wind_speed`, `wind_direction`)
- **Temporal Coverage**: Hourly resolution from `2020-08-04T00:00:00Z` to `2020-08-07T00:00:00Z`
- **Spatial Coverage**: Spatially averaged over case AOI or spatial grid covering Mauritius lagoon
- **CRS Convention**: `EPSG:4326`
- **Acquisition Source**: ECMWF Climate Data Store (CDS) ERA5 Reanalysis hourly data on single levels
- **Integrity Checks (Post-Download)**:
  - Hourly continuous timestamps without temporal gaps
  - Wind speed magnitudes physically realistic ($0.0 \le U_{10} \le 30.0$ m/s)

### 5. Ground-Truth Information
- **Target Location**: Isolated block in `data/cases/case_002_wakashio.yaml`
- **Current Status**: **VERIFIED & PRESENT LOCALLY**
  - Incident: MV Wakashio Bulk Carrier Grounding & Bunker Oil Spill
  - Date: Grounding `2020-07-25`, major bunker release `2020-08-06`
  - Coordinates: `-20.4400°N, 57.7400°E` (Pointe d'Esny coral reef)
  - Time: `2020-08-06T04:00:00Z`
  - Culprit: Bulk Carrier `WAKASHIO` (IMO 9337183, MMSI `356508000`, Flag: Panama)
  - Quality Level: **Tier A** (Panama Maritime Authority / Mauritius Court of Investigation)
  - Role: `POSITIVE_VESSEL_CASE`
- **Strict Isolation Rule**: The ground-truth block must remain strictly unreferenced by the blind runner (`run(case_id)`).

---

## 3. Case Verification Protocol (To be run post-download)

Once raw files are placed in their respective `data/raw/` directories, the following deterministic verification checks must pass before any algorithmic execution:
1. `test_case_002_config_loading`: Confirms YAML configuration parses into a valid `CaseConfig` without schema errors.
2. `test_case_002_raster_geometry`: Confirms Sentinel-1 raster exists, has CRS EPSG:4326, and covers the bounding box `[57.50, -20.60, 57.90, -20.30]`.
3. `test_case_002_calibration_xml`: Confirms XML calibration LUT exists and contains valid calibration vectors matching the scene.
4. `test_case_002_environmental_continuity`: Confirms HYCOM and ERA5 datasets contain finite values covering the backward drift window.
5. `test_case_002_ais_candidate_presence`: Confirms AIS dataset contains valid MMSI 356508000 pings with coordinate bounds matching the grounding reef.
6. `test_case_002_ground_truth_isolation`: Confirms algorithm inputs extracted via `extract_blind_algorithm_inputs()` contain zero ground-truth keys.
