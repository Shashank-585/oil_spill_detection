# Phase 14: Frontend Reconnaissance & Architectural Blueprint

**Date:** 2026-09-11  
**Project:** SIH26143 — Marine Oil Spill Attribution Decision-Support System  
**Document Status:** Architecture Reconnaissance & Blueprint (Implementation strictly frozen)  
**Deliverable File:** `docs/PHASE_14_FRONTEND_RECONNAISSANCE.md`

---

## 1. Executive Summary & Context

The backend scientific research and algorithmic validation pipeline is frozen with:
- **Case 001:** Validated Real Negative (Pipeline-origin spill; avoids false vessel attribution; top score reduced to 0.5628).
- **Case 002:** Validated Real Positive Physical Pipeline (SAR detection, backward Lagrangian drift, and environmental forcing intact).
- **Case 003:** Validated Real Positive Blind Attribution (M/V Golden Ray correctly ranked #1 with score 0.6891; escort tugs and salvors cleanly separated; 0 hardcoded logic).
- **Quality Assurance:** 163 automated tests passing (0 failures).

Phase 14 transitions the project towards building a professional, high-density, forensic-grade investigative workspace. This document establishes the reconnaissance audit of the current repository, evaluates visual/architectural anti-patterns, maps the backend data contracts, and specifies the complete information architecture and design system for Phase 15+.

---

## 2. Current Frontend Stack & Repository State

### 2.1 Inventory of Existing Frontend Assets
A comprehensive recursive inspection of the repository was conducted:
- `frontend/`: Exists as an empty directory (`c:\Users\rkchi\OneDrive\Desktop\Oil_spill\frontend\`).
- `backend/`: Exists as an empty directory (`c:\Users\rkchi\OneDrive\Desktop\Oil_spill\backend\`).
- Web Assets: Zero `.html`, `.jsx`, `.tsx`, `.vue`, or `.css` files currently exist in the repository.
- Runtime Environment:
  - **Node.js:** `v24.11.1` (installed and active)
  - **npm:** `11.14.1` (installed and active)
  - **Python:** `3.14.0` (with `pytest 9.1.1`, `numpy 2.2.3`, `rasterio 1.4.3`, `shapely 2.0.7`, `scipy 1.15.2`, `matplotlib 3.10.1`, `PyYAML 6.0.2`).

### 2.2 Stack Assessment for the Target System
Given the scientific nature of the platform (satellite rasters, vector geometries, AIS time-series, Lagrangian trajectories, and Monte Carlo ensembles), the frontend architecture must be selected according to strict engineering criteria:

| Component Layer | Selection | Justification |
| :--- | :--- | :--- |
| **Framework** | **React 18 / 19 + Vite 6** | Ultra-fast HMR, lightweight bundle, zero SSR overhead needed for local investigator desktop/electron/web usage. |
| **Language** | **TypeScript 5.x** | Essential for strict typing of multi-evidence hypotheses, GeoJSON features, and AIS trajectory frames. |
| **State Management** | **Zustand + TanStack Query (v5)** | TanStack Query provides cached data fetching for GeoJSON/NetCDF-derived JSON; Zustand handles active case selection, time scrubbing, and map layer toggles without context boilerplate. |
| **Mapping Engine** | **MapLibre GL JS + deck.gl** | GPU-accelerated rendering for 100,000+ AIS vessel pings and 50,000 Lagrangian drift particles. Supports custom raster layers (SAR $\sigma^0$ GeoTIFF / PNG tiles) and vector polygons. |
| **Charting Engine** | **ECharts or Recharts + Lucide Icons** | High-density multi-evidence radar/polar plots, confidence distribution histograms, and interactive time-scrubber timelines. |
| **Styling** | **Vanilla CSS Design Tokens / CSS Modules** | Eliminates bloated generic Tailwind utility classes; enforces strict maritime intelligence dark-mode styling with pixel-perfect control over borders, monospace metrics, and tabular layouts. |
| **Backend Bridge** | **FastAPI (Python 3.14)** | Directly imports existing `src/` modules (`CaseLoader`, `AttributionEngine`, `SourceReconstructor`), serving lightweight REST endpoints and static GeoJSON/PNG assets. |

---

## 3. Current Data Architecture & Backend Contracts

The frontend does not need to compute physics; the scientific pipeline generates structured, deterministic artifacts on disk in `data/processed/`. The frontend will consume these through a clean FastAPI service.

### 3.1 Data Source Matrix

```
┌────────────────────────────────────────────────────────────────────────┐
│                        DATA SOURCE MAPPING                             │
└────────────────────────────────────────────────────────────────────────┘
  Pipeline Domain        Source Artifacts on Disk                     Target REST Endpoint
  ─────────────────      ───────────────────────────────────────      ──────────────────────────────
  Case Manifests         data/cases/*.yaml                            GET /api/cases
                         data/processed/validation/validation_case... GET /api/cases/{id}
  
  SAR Satellite Layer    data/raw/case_XXX/s1_measurement_vv.tif      GET /api/cases/{id}/sar/raster
                         data/processed/satellite/*_mask.tif          GET /api/cases/{id}/sar/mask
                         data/processed/satellite/*_stats.json        GET /api/cases/{id}/sar/stats
  
  Oil Slick Polygons     data/processed/satellite/*_slicks.geojson    GET /api/cases/{id}/slicks
                         data/processed/satellite/*_summary.json
  
  4D Hypotheses          data/processed/hypotheses/*_4d.json          GET /api/cases/{id}/hypotheses
                         data/processed/hypotheses/*_summary.json
  
  AIS Vessel Tracks      data/raw/case_XXX/*_ais_filtered.csv         GET /api/cases/{id}/ais/vessels
                         data/processed/ais/*_trajectories.parquet    GET /api/cases/{id}/ais/tracks/{mmsi}
  
  Lagrangian Drift       data/processed/drift/*_trajectories.json     GET /api/cases/{id}/drift/backward
                         data/processed/attribution/simulations/...   GET /api/cases/{id}/drift/forward/{hyp_id}
  
  Attribution Scores     data/processed/attribution/*_summary.json    GET /api/cases/{id}/attribution/ranking
                         data/processed/attribution/*_evidence.json   GET /api/cases/{id}/attribution/evidence/{mmsi}
  
  Uncertainty Ensemble   data/processed/attribution/*_uncertainty...  GET /api/cases/{id}/attribution/uncertainty
```

---

## 4. Visual & UX Audit: Avoiding the "AI/Hackathon Demo" Trap

Most contemporary AI hackathon dashboards or academic prototypes suffer from recognizable anti-patterns that destroy credibility with operational maritime and coast guard investigators.

### 4.1 Detailed Breakdown of Anti-Patterns to Eliminate

| Dimension | "SIH-Demo / Generic AI" Flaw | Professional Maritime Intelligence Standard |
| :--- | :--- | :--- |
| **Visual Tone** | Neon glowing borders, saturated cyberpunk cyan/purple, animated glassmorphism, heavy drop-shadows. | Deep charcoal matte surfaces (`#0F141C`, `#18202C`), muted slate dividers (`#253346`), zero gratuitous glow. |
| **Typography** | Default sans-serif (`Inter` or `Roboto`) applied uniformly everywhere at identical weights. | Dual-type hierarchy: Crisp geometric grotesque (`Space Grotesk` or `Geist`) for UI labels + tabular monospace (`JetBrains Mono` or `Fira Code`) for coordinates, timestamps, MMSIs, and scores. |
| **Information Density** | Low density, giant padded cards (32px padding), huge round metric numbers without units or context. | High-density, compact investigative view: 8px/12px padding, comprehensive metadata chips, inline coordinate formats (`31°07'44"N 081°24'21"W`). |
| **Spatial Awareness** | Tiny embedded map widget squeezed into a 400px corner card with default OpenStreetMap tiles. | Full-viewport cartographic workspace with collapsible floating analytical drawers. Satellite basemaps (bathymetry/dark nautical) with custom projection controls. |
| **Attribution Framing** | Blatant accusations: "Culprit Identified: 98% Guilt", "Vessel Responsible: 0.98 Confirmed". | Evidentiary framing: "Highest Evidence Concordance Candidate", "Non-Culpable / Inconclusive Under Evidence", explicit uncalibrated compatibility disclaimer. |
| **Time Controls** | Static snapshot views with no temporal awareness or disconnected dropdowns. | 4D Synced Scrubber: Unified timeline scrubber controlling satellite acquisition, vessel positions, particle drift step, and tidal phase. |
| **Empty / Negative States** | Generic "No Data Found" or broken spin-wheel loaders. | Formally classified states: "Non-Attributable / Pipeline Origin", "AIS Archive Surveillance Deficit", "Insufficient Observation Quality". |

---

## 5. Proposed Product Information Architecture

To empower maritime casualty investigators, port state control officers, and environmental scientists, the application is structured into **9 core workspaces**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       PRODUCT WORKSPACE ARCHITECTURE                        │
└─────────────────────────────────────────────────────────────────────────────┘

  [Global Navigation / Top Bar]
  ├── Active Incident Selector: [ Case 003 — M/V Golden Ray Capsizing ▼ ]
  ├── Coordinated Incident Time: [ 2019-09-08 05:46 UTC (t₀) ──●───────── 2019-09-09 23:11 UTC (t_obs) ]
  ├── Causal Consistency Toggle: [ ENABLED (Phase 13 Generic Physics) ]
  └── System Status / Test Coverage: [ 163/163 PASSED | DETERMINISTIC ENGINE ]

  [Main Dual-Pane Layout]
  ┌──────────────────────────────────────────────────────┬────────────────────────────────────┐
  │ WORKSPACE VIEWPORT (Map & Primary Visualizations)     │ FORENSIC INSPECTOR PANEL (Right)   │
  │                                                      │ (Context-Sensitive Tabbed Drawer)  │
  │  Tabs:                                               │                                    │
  │  1. [Overview & Geo-Brief]                           │  Tab A: Hypothesis Breakdown       │
  │  2. [SAR Radiometric Analysis]                       │  Tab B: Multi-Evidence Radar       │
  │  3. [AIS Spatio-Temporal Field]                      │  Tab C: Forward Drift Verification │
  │  4. [Backward Source Reconstruction]                 │  Tab D: Monte Carlo Stability      │
  │  5. [Attribution Matrix & Ranking]                   │  Tab E: Case Audit & Export        │
  │  6. [Uncertainty & Sensitivity]                      │                                    │
  └──────────────────────────────────────────────────────┴────────────────────────────────────┘
```

### 5.1 Screen-by-Screen Functional Specifications

#### 1. Case Selector & Registry Overview
- **Objective:** Incident onboarding, status overview, and comparative triage across registered cases.
- **Key Metrics:** Incident classification (Vessel positive vs. Pipeline negative), Ground-Truth tier (NTSB/USCG Tier A), Data completeness status, Satellite scene ID.

#### 2. Satellite & SAR Analysis Workspace
- **Objective:** Forensic evaluation of the raw radar signal and dark-spot segmentation.
- **Features:** Dual-pane split slider comparing calibrated $\sigma^0$ dB backscatter with candidate slick segmentation masks. Local contrast profiles across slick transects. Lookalike rejection inspector (explaining why 201 false candidates were eliminated).

#### 3. AIS Traffic & Spatio-Temporal Field
- **Objective:** Surveillance audit of all vessels in the Area of Interest (AOI) across the 48-hour search window.
- **Features:** Vessel vector trajectories color-coded by vessel type (Cargo, Tanker, Tug, Special Craft). Interactive time-scrubber displaying kinematic states ($SOG, COG$, draft). Filtering by speed anomaly and navigational status.

#### 4. Backward Source Reconstruction & Particle Drift
- **Objective:** Physical tracing of the oil slick back to its origin envelope.
- **Features:** Interactive backward Lagrangian particle cloud ($N = 2,500$) driven by HYCOM surface currents and ERA5 wind vectors ($c_w = 0.03$). Spatio-temporal source density heatmap ($P_{\text{source}}(x, y, t)$) displaying release window intervals.

#### 5. Attribution Ranking & Causal Consistency Matrix
- **Objective:** Ranked candidate evaluation under multi-evidence scoring.
- **Features:** High-density tabular leaderboard showing Rank, MMSI, Vessel Name, Best Hypothesis ID, Composite Score ($S_{\text{final}}$), and Causal Precedence Tag (`VALID_PRE_EVENT`, `INELIGIBLE_POST_EVENT`). Click-to-inspect opens the forward counterfactual simulation comparison.

#### 6. Evidentiary Breakdown (Radar & Feature Breakdown)
- **Objective:** Transparent explanation of composite score components.
- **Features:** 5-axis polar chart and stacked score waterfall showing:
  1. Drift Consistency ($S_{\text{drift}}$): Centroid distance + Hausdorff + IoU overlap.
  2. Spatial Compatibility ($S_{\text{space}}$): Proximity to backward trajectory cone.
  3. Source Plausibility ($S_{\text{source}}$): Modulated by physical spreading timescale ($t_{\text{min\_spread}}$).
  4. Temporal Compatibility ($S_{\text{time}}$): Alignment with release time window.
  5. AIS Track Quality ($S_{\text{ais}}$): Completeness, ping frequency, and speed anomalies.

#### 7. Monte Carlo Uncertainty & Sensitivity Inspector
- **Objective:** Robustness verification against environmental noise and drift parameter variance.
- **Features:** Box plots of score distributions across $N = 50$ ensemble realizations. Top-1 and Top-3 rank stability frequencies. Calibration notice emphasizing uncalibrated compatibility index status.

#### 8. Investigation Report & Formal Audit Exporter
- **Objective:** Generate reproducible evidence summaries for court/coast guard submission.
- **Features:** One-click generation of court-ready Markdown / PDF audit packages with exact data provenance hashes, model parameters, and satellite scene IDs.

---

## 6. Design System Specification (Maritime Intelligence Theme)

The design system is engineered for maximum legibility in low-light operations centers and high-density technical analysis.

### 6.1 Color Palette Tokens

```css
:root {
  /* Surface & Base Backgrounds */
  --color-bg-base: #0a0d13;            /* Deepest ocean black */
  --color-bg-surface: #111620;         /* Primary container surface */
  --color-bg-surface-raised: #18202d;  /* Card / floating panel surface */
  --color-bg-surface-hover: #1f2a3c;   /* Row / button hover state */
  --color-border-subtle: #243042;      /* Default divider line */
  --color-border-strong: #384961;      /* Active selection border */

  /* Text & Data */
  --color-text-primary: #e6edf3;       /* High-contrast data values */
  --color-text-secondary: #8b9bb4;     /* Field labels, units */
  --color-text-muted: #53647c;         /* Inactive metadata */
  --color-text-monospace: #79c0ff;     /* Coordinates, timestamps */

  /* Maritime Domain Accents */
  --color-accent-blue: #388bfd;        /* Navigation, selection */
  --color-accent-cyan: #39c5cf;        /* Satellite SAR observation */
  --color-accent-amber: #d29922;       /* Moderate support, warning */
  --color-accent-crimson: #f85149;     /* High support, slick boundary */
  --color-accent-emerald: #2ea043;     /* Negative control passed, verified */
  --color-accent-purple: #bc8cff;      /* Lagrangian drift particles */

  /* Causal Consistency Status Tags */
  --tag-pre-event-bg: rgba(46, 160, 67, 0.15);
  --tag-pre-event-text: #3fb950;
  --tag-post-event-bg: rgba(248, 81, 73, 0.15);
  --tag-post-event-text: #f85149;
}
```

### 6.2 Typography & Sizing System

```css
:root {
  --font-sans: 'Geist', 'Space Grotesk', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;

  /* Type Scale */
  --text-2xs: 10px; /* Status pills, metadata tags */
  --text-xs: 11px;  /* Table headers, coordinate labels */
  --text-sm: 13px;  /* Body text, table rows, input fields */
  --text-base: 14px;/* Section headers, metric values */
  --text-lg: 16px;  /* Panel titles */
  --text-xl: 20px;  /* Viewport headers */

  /* Spatial Grid */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 24px;
  --space-6: 32px;

  /* Component Geometry */
  --radius-xs: 2px;
  --radius-sm: 4px;
  --radius-md: 6px;
  --border-width: 1px;
}
```

### 6.3 Monospace Data Display Conventions
- **Geographic Coordinates:** `31°07'44.4"N 081°24'21.6"W` or `+31.1290, -081.4060` (always formatted to 4 decimal places with fixed width).
- **Timestamps:** `2019-09-08 05:46:00 UTC` (never ambiguous local time; ISO-8601 with explicit UTC designation).
- **Scores & Metrics:** `0.6891` (formatted to 4 decimals with inline visual confidence bar).

---

## 7. Recommended Component Hierarchy

```text
src/
├── components/
│   ├── layout/
│   │   ├── TopHeader.tsx              # Incident selector, status badges, global timeline
│   │   ├── NavigationRail.tsx         # Sleek sidebar with route icons (overview, SAR, AIS, attribution)
│   │   └── InspectorDrawer.tsx        # Right-hand collapsible evidentiary deep-dive drawer
│   ├── map/
│   │   ├── GeospatialViewport.tsx     # MapLibre/deck.gl base map container
│   │   ├── SarRasterLayer.tsx         # Georeferenced Sentinel-1 SAR imagery overlay
│   │   ├── SlickPolygonLayer.tsx      # Vectorized segmented oil slick footprints
│   │   ├── DriftParticleLayer.tsx     # Animated backward/forward Lagrangian particle clouds
│   │   ├── AisTrackLayer.tsx          # Interpolated vessel trajectory polylines with directional arrows
│   │   └── MapLayerControls.tsx       # Layer visibility toggles (SAR, Slicks, AIS, Particles)
│   ├── timeline/
│   │   ├── MasterTimelineScrubber.tsx # 4D dual-thumb synchronized time scrubber
│   │   └── EventMarkers.tsx           # Capsizing, observation, and release time flags
│   ├── attribution/
│   │   ├── RankingTable.tsx           # Forensic table of candidate vessels with causal tags
│   │   ├── EvidenceRadarChart.tsx     # 5-axis polar chart of evidence weights
│   │   ├── CounterfactualViewer.tsx   # Predicted vs. observed slick geometry visualizer
│   │   └── CausalTagPill.tsx          # PRE_EVENT vs. POST_EVENT_ONLY status badge
│   ├── uncertainty/
│   │   ├── RankStabilityChart.tsx     # Ensemble rank frequency horizontal bar chart
│   │   └── SensitivityMatrix.tsx      # Current/wind deflection sensitivity indicators
│   └── common/
│       ├── MonospaceCoordinate.tsx    # Standardized geo-coordinate text block
│       ├── StatMetricCard.tsx         # Compact metric chip with delta indicator
│       └── StatusBadge.tsx            # Standardized evidence support badge
```

---

## 8. Migration & Implementation Strategy (Phase 15 Roadmap)

The transition will occur incrementally without touching or risking the frozen 163-test backend:

```
[Phase 15.1: Scaffold Workspace]
  ├── Initialize Vite + React + TypeScript in `frontend/`
  ├── Set up core design tokens in `frontend/src/styles/tokens.css`
  └── Configure MapLibre GL + deck.gl dependencies

[Phase 15.2: Lightweight API Service]
  ├── Implement `backend/main.py` using FastAPI
  ├── Mount read-only endpoints returning existing `data/processed/*.json` and GeoJSONs
  └── Serve calibrated SAR PNG tiles / GeoTIFF over HTTP

[Phase 15.3: Geospatial Map Canvas]
  ├── Render base dark-nautical vector tile canvas
  ├── Implement SAR raster and slick polygon overlays
  └── Wire up deck.gl AIS trajectory and Lagrangian particle rendering

[Phase 15.4: Attribution & Evidence Inspector]
  ├── Build forensic candidate ranking table
  ├── Integrate multi-evidence radar chart and score breakdown
  └── Implement interactive time scrubber controlling particle time-steps

[Phase 15.5: End-to-End Verification]
  ├── Verify Case 001 (Negative test display correctly indicates pipeline origin)
  ├── Verify Case 002 (Physical validation displays with AIS deficit notice)
  └── Verify Case 003 (Golden Ray ranks #1 with causal tags clearly rendered)
```

---

## 9. Immutable Boundaries (What Should NOT Be Changed)

To safeguard scientific validity throughout the frontend implementation, the following architectural invariants are established:
1. **Zero Algorithm Code Modifications:** `src/attribution/`, `src/drift/`, `src/detection/`, and `src/satellite/` remain frozen.
2. **Zero Hardcoded Case Overrides:** The frontend must never contain `if (caseId === "case_003") { highlight("Golden Ray"); }`. All data displayed must be parsed strictly from the backend JSON payloads.
3. **No Culpability Assertions:** The UI must adhere to scientific decision-support language ("Compatible Hypothesis", "Attribution Compatibility Index", "Inconclusive Evidence") and display the mandatory calibration notice.
4. **Data Model Integrity:** The frontend must consume the exact schema output by `AttributionEngine` and `HypothesisGenerator` without reshaping data in a lossy manner.4

---
*Report compiled and verified against project baseline.*
