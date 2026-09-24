# Phase 20 — Counterfactual Simulation Experience

## Overview

Phase 20 transforms existing forward hydrodynamic simulation outputs into a comprehensive, investigator-facing decision support UI. It answers the central forensic counterfactual question:

> **"If this vessel released material at this location and time, would the resulting spill evolve into what the satellite observed?"**

In strict adherence to the project scientific boundaries, no modifications were made to underlying drift equations, forward simulation algorithms, environmental forcing datasets, particle counts, or scoring logic. All numerical metrics are read dynamically from pre-computed backend artifacts and exposed via dedicated API endpoints.

---

## Architecture & Layout

### 1. Primary Geospatial Viewport (Left / Dominant Canvas)
The primary map retains dominance across 60–65% of the viewport width, rendering high-contrast WebGL deck.gl layers:
- **Observed SAR Slick**: Highlighted observation polygon with distinct amber boundary (`#fabe32` / `#d29922`) and 3.5px stroked border.
- **Simulated Particle Footprint**: 500 forward simulated Lagrangian particles rendered as an electric cyan/blue particle plume (`#38bdf8`) with white containment halos.
- **Hypothesis Release Source Point ($T_0$)**: Vibrant orange/coral diamond marker (`#fb923c`) at $(Lat_{release}, Lon_{release})$.
- **Forward Hydrodynamic Drift Trajectory**: Subsampled forward drift tracks connecting the release point to the final observation epoch.
- **Centroid Displacement Vector**: Red/coral offset line (`#f85149`) linking the predicted centroid to the observed slick centroid, visually illustrating the physical displacement.
- **Counterfactual Map Legend**: Dedicated high-contrast legend with a **Focus** button that smoothly frames the map around the observation and simulated plume extent.

### 2. Evidence Panel ("COUNTERFACTUAL TEST", Right Docked Drawer)
Docked on the right side (`width: 530px`) with a dark nautical intelligence aesthetic (`rgba(10, 13, 19, 0.96)`, glassmorphism blur):
- **Investigation Core Question Banner**:
  *"Counterfactual question: If this hypothesis were true, how closely would the simulated spill match the observed satellite slick?"*
- **Candidate Vessel Switcher**: Interactive pills for all evaluated candidate vessels with their MMSIs and best IoU.
- **4D Hypothesis Selector**: Filter by temporal variations for the selected vessel.
- **Release Setup Card**: Release coordinates, release timestamp (UTC), observation timestamp, and simulation duration.
- **Observed vs Predicted Spatial Concordance Matrix (Exact Artifact Metrics)**:
  - **Centroid Error**: Exact displacement in meters (e.g. `19.01 m`).
  - **Mean Particle Distance**: Average particle distance to observed slick (e.g. `38.46 m`).
  - **Median & P90 Particle Distance**: 50th and 90th percentile particle distances (e.g. `18.4 m` / `111.65 m`).
  - **Particle Coverage / Containment**: Ratio of simulated particles contained within observation domain (e.g. `100.0%`).
  - **Spatial Intersection over Union (IoU)**: Exact geometric overlap (e.g. `15.07%` / `0.1507`).
  - **Area Envelopes**: Predicted vs Observed area in $m^2$.
  - **Geometric Offsets**: $\Delta$ Orientation angle and $\Delta$ Aspect Ratio.
- **Deterministic Physical Interpretation**:
  - `HIGH PHYSICAL COMPATIBILITY` (Centroid Error < 30m, Coverage $\ge$ 95%, IoU $\ge$ 10%)
  - `MODERATE PHYSICAL COMPATIBILITY` (Centroid Error < 100m, Coverage $\ge$ 70%)
  - `LOW PHYSICAL COMPATIBILITY` (Divergent dispersion)
  - Explicit scientific notice: *No probabilistic certainty ("98% chance") or legal guilt assertions ("proved responsible", "confirmed culprit") are made. The system evaluates physical concordance under verified hydrodynamic models.*
- **Cross-Candidate Comparison Matrix**: Side-by-side table comparing candidate vessels with instant click-to-test switching.
- **Navigation Controls**:
  - **Return to Rankings →** button to navigate seamlessly back to candidate rankings (`view=candidates`).

---

## Case 003 Golden Ray Benchmark Verification

For **Case 003 Golden Ray** (`case_003_golden_ray`), verified benchmark hypothesis `4DH_0022` yields:
- **Vessel**: `GOLDEN RAY (MMSI 538007762)`
- **Hypothesis**: `4DH_0022`
- **Observed Slick**: `CS_0035`
- **Centroid Displacement Error**: `19.01 m`
- **Mean Particle Error**: `38.46 m`
- **Particle Coverage**: `100.0%`
- **Spatial IoU**: `15.07%` (`0.1507`)
- **P90 Particle Error**: `111.65 m`
- **Deterministic Assessment**: `HIGH PHYSICAL COMPATIBILITY`

All values are read dynamically from `case_003_golden_ray_spill_comparisons.json` and `simulations/4DH_0022/`.

---

## API Endpoints Added

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/cases/{case_id}/attribution/spill-comparisons` | Fetches forward simulation comparisons against observed SAR slicks. |
| `GET` | `/api/cases/{case_id}/attribution/simulations/{hypothesis_id}` | Returns 500 forward simulated particles, sampled trajectory tracks, and metadata for deck.gl rendering. |

---

## Multi-Case Verification

- **Case 003 (Golden Ray)**: Verified Golden Ray demo, 500 simulated particles on map, trajectory, centroid offset line, and seamless candidate switching to competing craft (`KUJAWY`, `RECOVERY`, etc.).
- **Case 001 (Huntington Beach Pipeline)**: Verified counterfactual comparison metrics and candidate switching for maritime traffic (e.g. `ROAM`, `CALYPSO`, `LAST DANCE`).
- **Case 002 (Wakashio Physical Benchmark)**: Verified clean, graceful `COUNTERFACTUAL SIMULATION UNAVAILABLE` banner without runtime errors or broken UI states.

---

## Automated Verification

- **Backend Pytest**: `179 passed, 2 warnings in 22.93s` (`python -m pytest tests/ -q`)
- **Frontend Build**: Clean TypeScript compilation and Vite production build (`npm run build`, 0 errors).
- **Browser Automation**: End-to-end user workflow recorded and verified across all test cases.
