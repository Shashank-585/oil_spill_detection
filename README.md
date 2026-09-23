# SIH26143: Maritime Oil Spill Attribution Pipeline

> **“Leveraging satellite imagery to determine oil spills at sea along with AIS data correlations to identify vessel responsible for the spill.”**

---

## 1. Scientific Philosophy & Framing

This system is built as an explainable decision-support platform for maritime environmental investigators.

* **Core Premise**: The system **does NOT claim to prove vessel guilt**. Attribution is formulated as identifying the *"most likely candidate under available physical evidence"* or declaring *"insufficient evidence"*.
* **Hypothesis Formulation**:
  $$H = (\text{vessel}, \text{release\_location}, \text{release\_time})$$
  The objective is finding $H^* = \arg\max P(H \mid \text{satellite, wind, current, AIS})$.
* **Drift Modelling Separation**:
  * **Backward drift** is used strictly for *source reconstruction* (identifying candidate 4D spatio-temporal envelopes).
  * **Forward drift** is used for *counterfactual testing* of individual vessel discharge hypotheses.
  * Backward and forward drift are never treated as independent physical evidence.

---

## 2. Core Architecture & Pipeline

```
Satellite SAR Imagery (Sentinel-1)
  │
  ▼
[Phase 2] SAR Preprocessing & Radiometric Calibration (DN -> σ°)
  │
  ▼
[Phase 3] Oil Spill Segmentation & Geometry Extraction (Polygons, Confidence)
  │
  ├────────────────────────────────────────┐
  ▼                                        ▼
Ocean Currents (HYCOM) + Wind (ERA5)   AIS Ingestion (NOAA / DMA)
  │                                        │
  ▼                                        ▼
[Phase 4] Lagrangian Backward Drift    [Phase 5] High-Recall Candidate Filter
(Source Time × Location Distribution)     (Spatio-temporal Trajectory Gating)
  │                                        │
  └──────────────────┬─────────────────────┘
                     ▼
  [Phase 6] 4D Source Hypotheses H = (vessel, location, time)
                     │
                     ▼
  Forward Counterfactual Lagrangian Simulation
                     │
                     ▼
  Multi-Evidence Scoring & Explainable Ranking
  (Spatial Jaccard, Hausdorff Distance, Speed Anomalies)
                     │
                     ▼
  [Phase 7] Investigator Dashboard & API (React + FastAPI)
  (Ranked Candidates or Explicit "Insufficient Evidence")
```

---

## 3. Current Project Status

* **Current Phase**: **PHASE 1 — PROJECT & DATA INFRASTRUCTURE** (Complete & Verified)
* **Active Case**: `case_001` (Huntington Beach / San Pedro Bay Oil Spill, October 2021)
* **Raw Artifacts Verified**:
  * Sentinel-1A C-SAR GRD VV measurement raster: 4,000 × 5,500 pixels, EPSG:4326 (`data/raw/satellite/case_001_s1_measurement_vv.tif`).
  * HYCOM 3-hourly ocean surface current vectors (`data/raw/environmental/case_001_ocean_currents_hycom.nc`).
  * ECMWF ERA5 hourly 10m wind vector fields (`data/raw/environmental/case_001_wind_era5.csv`).
  * NOAA MarineCadastre filtered AIS trajectories: 248,043 positions, 737 vessels (`data/raw/ais/case_001_ais_filtered.csv`).

---

## 4. Repository Structure

```text
oilspill-attribution/
├── README.md                               # Project documentation & scientific framing
├── requirements.txt                        # Core Python dependencies
├── .env.example                            # Environment credentials template
├── health_check.py                         # Root health-check entrypoint
├── data/
│   ├── raw/
│   │   ├── satellite/                      # Sentinel-1 GeoTIFF, manifest, STAC JSON
│   │   ├── ais/                            # NOAA AIS raw zips and filtered CSVs
│   │   └── environmental/                  # HYCOM NetCDF and ERA5 wind datasets
│   ├── processed/
│   │   ├── satellite/                      # Diagnostic plots, calibrated rasters, masks
│   │   ├── ais/                            # Reconstructed vessel trajectories
│   │   └── environmental/                  # Spatio-temporally interpolated forcings
│   └── cases/
│       └── case_001.yaml                   # Reproducible historical case configuration
├── notebooks/                              # Guided Jupyter exploratory notebooks
│   ├── 01_satellite_exploration.ipynb
│   ├── 02_environment_exploration.ipynb
│   ├── 03_drift_exploration.ipynb
│   └── 04_ais_exploration.ipynb
├── src/                                    # Modular scientific pipeline source code
│   ├── common/                             # Paths, config, geo, time, and logging utilities
│   ├── satellite/                          # SAR ingestion & radiometric calibration
│   ├── detection/                          # Dark patch segmentation & geometry extraction
│   ├── environmental/                      # HYCOM and ERA5 vector field interpolation
│   ├── drift/                              # Lagrangian particle drift engine
│   ├── source/                             # Backward source probability estimation
│   ├── ais/                                # Vessel candidate generation & kinematic filtering
│   ├── attribution/                        # Counterfactual forward simulation & ranking
│   ├── validation/                         # Data feasibility & integrity validators
│   └── health_check.py                     # Infrastructure verification module
├── backend/                                # FastAPI backend API (planned Phase 6)
├── frontend/                               # Interactive React dashboard (planned Phase 7)
├── tests/                                  # Automated pytest unit test suite
└── configs/
    └── default.yaml                        # Central default pipeline configuration
```

---

## 5. How to Run & Verify

### Running Health Check
To verify repository integrity, directory layout, case loading, and data paths:
```powershell
python health_check.py
# or
python -m src.health_check
```

### Running the Case Validation Utility
To run full scientific data feasibility checks on `case_001`:
```powershell
python src/validation/validate_case_data.py
```

### Running Automated Test Suite
```powershell
python -m pytest tests/ -v
```

---

## 6. Geospatial & Temporal Conventions

* **Default Geographic CRS**: `EPSG:4326` (WGS84 2D latitude/longitude in degrees).
* **Metric Calculation Policy**: Metric distances and spatial areas are **never** calculated directly on angular degrees. All metric evaluations use geodesic formulations (Haversine/Vincenty via `src/common/geo.py`) or local projected coordinate systems (UTM).
* **Timestamp Handling**: Internally, **all timestamps must be UTC-aware**. Naive datetimes are strictly disallowed.
