# Case 003: M/V Golden Ray Data Acquisition & Preprocessing Report

**Case Identifier**: `case_003_golden_ray`  
**Incident Name**: M/V Golden Ray Capsizing & Bunker Oil Spill  
**Incident Date/Time**: 2019-09-08 05:46:00 UTC (01:46 EDT)  
**Location**: St. Simons Sound / Brunswick, Georgia, USA (approx. 31.129° N, -81.406° W)  
**Validation Role**: `POSITIVE_VESSEL_CASE` (Real-World Positive Benchmark)  
**Report Date**: September 11, 2026  
**Status**: `ACQUISITION_COMPLETE_AND_VERIFIED` — **READY FOR BLIND ATTRIBUTION**

---

## Executive Summary

Case 003 establishes the first verified **real-world positive vessel attribution benchmark** for the SIH26143 oil-spill attribution system. Unlike Case 001 (Huntington Beach pipeline negative benchmark) and Case 002 (Mauritius, awaiting open commercial multi-vessel AIS), Case 003 has **all four physical evidence pillars completely acquired, validated, and checksum-verified**:
1. **Satellite SAR**: Sentinel-1A IW GRD VV measurement raster (+5.6 hours post-capsizing) and calibration metadata.
2. **AIS Multi-Vessel Traffic**: Official NOAA MarineCadastre historical AIS containing **49 active vessels** and **25,615 records** across the operational AOI and 48-hour temporal window.
3. **Ocean Surface Currents**: High-resolution HYCOM GLBv0.08 / Experiment 93.0 3-hourly surface currents.
4. **Atmospheric Winds**: ECMWF ERA5 hourly 10-meter reanalysis winds.

Strict operational data isolation has been verified: Golden Ray's identity (MMSI 538007762, IMO 9775816, name) exists **only** in the isolated validation section and was **never** used in candidate generation, AIS filtering, or scoring.

---

## A. Sentinel-1 SAR Acquisition & Preprocessing

### 1. Primary Post-Incident Observation
- **Product ID**: `S1A_IW_GRDH_1SDV_20190908T112519_20190908T112544_028929_0347A9`
- **Platform**: Sentinel-1A (C-band SAR)
- **Sensor Mode**: Interferometric Wide Swath (IW)
- **Product Type**: Ground Range Detected High Resolution (GRDH)
- **Polarization**: VV (primary measurement) and VH
- **Orbit Direction**: Descending (Relative Orbit 145)
- **Acquisition Timestamp**:
  - Start: `2019-09-08T11:25:19.387Z`
  - End: `2019-09-08T11:25:44.385Z`
  - Mean Sensing Time: `2019-09-08T11:25:31.797740Z` (~5.65 hours after capsizing)
- **Source**: Copernicus Data Space Ecosystem / Microsoft Planetary Computer STAC
- **Download URL**: `https://sentinel1euwest.blob.core.windows.net/s1-grd/GRD/2019/9/8/IW/DV/S1A_IW_GRDH_1SDV_20190908T112519_20190908T112544_028929_0347A9/measurement/iw-vv.tiff`

### 2. Physical File & Spatial Characteristics
- **Local Measurement Raster**:
  - `data/raw/satellite/case_003_golden_ray_s1_measurement_vv.tif`
  - Mirrored at: `data/raw/case_003_golden_ray/s1_measurement_vv.tif`
  - File Size: `12,466,249 bytes` (~11.89 MB)
  - SHA256: `c6e2237d15763fbef8680e98f7b779848f7139e3bbaeb9dfb3395e63ca047bdb`
- **Local Calibration XML**:
  - `data/raw/satellite/case_003_golden_ray_calibration_vv.xml`
  - Mirrored at: `data/raw/case_003_golden_ray/calibration_vv.xml`
  - File Size: `1,000,741 bytes`
  - SHA256: `07aa474f5195792313b0a66d8b4947fb450f3107322d3202bfd925a330cf0766`
- **Coordinate Reference System (CRS)**: `EPSG:4326` (WGS 84)
- **Raster Dimensions**: `5000` columns × `3000` rows (1 band, uint16)
- **Operational AOI Bounds**:
  - West: `-81.6000°`
  - South: `31.0000°`
  - East: `-81.1000°`
  - North: `31.3000°`
- **Pixel Statistics**:
  - Valid pixels: 79.94% (non-zero; zero indicates off-swath or outer masking)
  - Min valid DN: `1`
  - Max valid DN: `65,535`
  - Mean valid DN: `119.53`
  - NoData value: `0`

### 3. Pre-Incident Baseline Scene Verification
- **Baseline Product ID**: `S1A_IW_GRDH_1SDV_20190907T232121_20190907T232146_028922_034766`
- **Acquisition Timestamp**: `2019-09-07T23:21:33Z` (~6.4 hours prior to capsizing)
- **Status**: Cataloged as baseline reference scene for radar contrast comparisons.

---

## B. NOAA Historical Multi-Vessel AIS Traffic

### 1. Sourcing & Provenance
- **Source**: NOAA MarineCadastre Historical AIS Archive (Office for Coastal Management)
- **Raw Archive Zips Acquired**:
  - `AIS_2019_09_07.zip` (`315,444,844 bytes`, SHA256: `1865dc6c9fe272445858fc945ae94a1073e6a246870fa67f1398bb9ffdc6ca4d`)
  - `AIS_2019_09_08.zip` (`321,030,997 bytes`, SHA256: `bb94e77da4be1b637a28e578c9d084052f7543886b9762aee8dcbfddb663e020`)
  - `AIS_2019_09_09.zip` (`311,879,901 bytes`, SHA256: `6fa769eb070cfdf3dd3cfa88b64e0ee76b92a2cb705fbbd30c5a242c7aa3a6a9`)
- **Total Raw Records Scanned**: `24,000,000+` national AIS pings.

### 2. Operational Filtering & Traffic Statistics
- **Filtered Spatial Envelope**: `[-81.65, 30.95, -81.05, 31.35]` (covering St. Simons Sound, Brunswick port waters, river channels, and open Atlantic approach).
- **Filtered Temporal Window**: `2019-09-07T12:00:00Z` through `2019-09-09T12:00:00Z` (48-hour continuous window).
- **Unbiased Filtering**: No vessel names, MMSIs, IMOs, or vessel types were filtered.
- **Filtered Output File**:
  - `data/raw/ais/case_003_golden_ray_ais_filtered.csv`
  - Mirrored at: `data/raw/case_003_golden_ray/ais_filtered.csv`
  - File Size: `3,384,308 bytes`
  - SHA256: `55e68575bc2e30ea031e1b8f493eb702053eab1a51bc79ee6bc0e1806d5ac723`
- **Total Records Retained**: `25,615`
- **Unique MMSIs (Vessels)**: `49`
- **Unique Vessel Names**: `48`
- **Actual Temporal Coverage**: `2019-09-07T12:00:05Z` to `2019-09-09T12:00:00Z`
- **Actual Spatial Coverage**: LAT `[30.9504, 31.3480]`, LON `[-81.5719, -81.0502]`
- **Records per Vessel Distribution**:
  - Minimum: `2`
  - Median: `323.0`
  - Mean: `522.8`
  - Maximum: `1,904`

### 3. Traffic Proximity to Incident Location (`31.129° N, -81.406° W`)
| Distance Band | Number of Vessels Entering Band | Description / Operational Role |
|:---|:---:|:---|
| **Within 2.0 km** | **15 vessels** | Immediate incident vicinity (channel, pilot boats, assisting tugs, passing coastal traffic) |
| **Within 5.0 km** | **18 vessels** | St. Simons Sound entrance and sound transit corridor |
| **Within 10.0 km** | **38 vessels** | St. Simons Sound, Brunswick Inner Harbor, and outer anchorage |
| **Within 15.0 km** | **39 vessels** | Port approach and adjacent barrier island waters |
| **Within 20.0 km** | **42 vessels** | Regional coastal shipping lanes |
| **Within 30.0 km** | **48 vessels** | Full coastal approach envelope |
| **Within 50.0 km** | **49 vessels** | Total operational AOI vessel count |

### 4. Temporal Traffic Density
- **Active within ±6 hours of capsizing (`2019-09-07 23:46Z` to `2019-09-08 11:46Z`)**: `28 vessels` (`6,754 records`).
- **Active within ±6 hours AND within 10 km**: `23 vessels` (`5,634 records`).
- **Conclusion**: The AOI contains robust, realistic candidate traffic to rigorously challenge the candidate generation, counterfactual drift simulation, and multi-evidence attribution algorithms without synthetic inflation.

---

## C. Ocean Surface Currents (HYCOM)

- **Dataset**: HYCOM Global Ocean Physics Analysis (`GLBv0.08 / expt_93.0`)
- **Provider**: HYCOM Consortium / NOAA / NRL THREDDS Server
- **Access Endpoint**: `https://ncss.hycom.org/thredds/ncss/GLBv0.08/expt_93.0`
- **Local Artifact**:
  - `data/raw/environmental/case_003_golden_ray_ocean_currents.nc`
  - Mirrored at: `data/raw/case_003_golden_ray/ocean_currents.nc`
  - File Size: `13,720 bytes`
  - SHA256: `490e30043aaf3a11e7846619351b61d14ce2b79a8af9086d6dd883466e4f8147`
- **Format**: NetCDF3 (CF-1.0 compliant)
- **Spatial Grid**:
  - Longitude: `[-81.84, -81.04]` (11 grid points, 0.08° resolution)
  - Latitude: `[30.80, 31.52]` (10 grid points, 0.08° resolution)
- **Temporal Grid**:
  - 24 time steps (3-hourly from `2019-09-07T00:00:00Z` to `2019-09-09T21:00:00Z`)
- **Variables & Statistics**:
  - `water_u` (Eastward velocity, m/s): Min = `-0.518 m/s`, Max = `+0.492 m/s`, Mean = `+0.041 m/s`
  - `water_v` (Northward velocity, m/s): Min = `-0.485 m/s`, Max = `+0.621 m/s`, Mean = `+0.118 m/s`
- **Validation**: Verified compatibility with `src.drift.environmental.EnvironmentalForcingInterpolator`.

---

## D. Atmospheric Winds (ECMWF ERA5)

- **Dataset**: ECMWF ERA5 Hourly Reanalysis 10m Winds
- **Provider**: ECMWF / Open-Meteo Historical Archive
- **Local Artifact**:
  - `data/raw/environmental/case_003_golden_ray_wind_era5.csv`
  - Mirrored at: `data/raw/case_003_golden_ray/wind_era5.csv`
  - File Size: `5,083 bytes`
  - SHA256: `899add55223bc5264cd11effbc76785752b2f2a02e9d3ee42c677f1f05f1066e`
- **Temporal Coverage**: 72 continuous hourly records (`2019-09-07T00:00:00Z` to `2019-09-09T23:00:00Z`)
- **Spatial Center**: `31.129° N, -81.406° W`
- **Variables & Statistics**:
  - `wind_speed_10m_mps`: Min = `2.14 m/s` (4.2 kt), Max = `8.72 m/s` (16.9 kt), Mean = `5.38 m/s` (10.5 kt)
  - `wind_u_10m_mps` (`u10`): Min = `-6.85 m/s`, Max = `+4.12 m/s`
  - `wind_v_10m_mps` (`v10`): Min = `-5.91 m/s`, Max = `+6.48 m/s`
  - `wind_direction_10m_deg`: Predominantly NE/ENE transitioning to SE
- **Validation**: Verified with `EnvironmentalForcingInterpolator`.

---

## E. Ground-Truth Registry & Blind Experiment Isolation

### 1. Documented Ground Truth (Validation Only)
- **Vessel**: M/V GOLDEN RAY
- **Vessel Type**: Vehicle Carrier (Ro-Ro)
- **Flag**: Marshall Islands
- **IMO**: `9775816`
- **MMSI**: `538007762`
- **Incident Location**: `31.1290° N, -81.4060° W` (St. Simons Sound channel near Sound Buoy 19)
- **Incident Time**: `2019-09-08T05:46:00Z` (01:46 EDT)
- **Ground Truth Source**: National Transportation Safety Board (NTSB) Marine Accident Report MAR-21/03; USCG Marine Board of Investigation.
- **Ground Truth Quality**: `A (VERIFIED)`
- **Ground Truth Confidence**: `1.0`

### 2. Operational Isolation Verification (No Data Leakage)
A systematic codebase audit was conducted prior to authorizing blind attribution:
1. **Candidate Generation**: `src/ais/candidate_generator.py` does not contain references to Golden Ray, MMSI `538007762`, or IMO `9775816`.
2. **AIS Filtering**: The operational filtering script applied solely spatial and temporal masks. No vessel identifier filtering was performed.
3. **Scoring & Attribution Engine**: `src/attribution/engine.py` and `src/attribution/multi_evidence_scoring.py` operate purely on physical counterfactual match scores, geometric overlap, and temporal proximity. No vessel identity weighting exists.
4. **Configuration**: `data/cases/case_003_golden_ray.yaml` places all ground-truth details strictly within the `validation:` key, which is ignored during operational pipeline execution.

---

## F. Case Readiness Determination

| Evidence Pillar | Required Condition | Status | Assessment |
|:---|:---|:---:|:---|
| **Satellite SAR** | Sentinel-1 VV GRD + Calibration XML acquired | **YES** | PASS (Valid 5000x3000 raster, 79.94% valid pixels) |
| **AIS Traffic** | Multi-vessel historical AIS covering AOI & window | **YES** | PASS (49 vessels, 25,615 records, 23 vessels near event) |
| **Ocean Currents** | HYCOM GLBv0.08 / expt_93.0 3-hourly grid | **YES** | PASS (24 steps, CF-1.0 NetCDF) |
| **Atmospheric Wind**| ERA5 10m hourly winds | **YES** | PASS (72 hourly records) |
| **Case Config** | Valid YAML passing `CaseConfig.validate_integrity()` | **YES** | PASS (0 integrity errors) |
| **Ground Truth** | Documented and isolated from operational code | **YES** | PASS (Strict isolation verified) |

**FINAL VERDICT**:  
**CASE 003 (M/V GOLDEN RAY) IS 100% ACQUIRED, PREPROCESSED, AND OFFICIALLY READY FOR BLIND ATTRIBUTION.**
