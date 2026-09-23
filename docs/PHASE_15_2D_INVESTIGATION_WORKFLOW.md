# PHASE 15.2D — SYNCHRONIZED INVESTIGATION WORKFLOW
## SIH26143 Marine Oil Spill Attribution Decision-Support System

**Status:** COMPLETE & VERIFIED  
**Backend Integrity:** FROZEN (179/179 Automated Tests Passing)  
**Frontend Architecture:** MapLibre GL JS + deck.gl + TanStack Query + Zustand  
**Verification Coverage:** TypeScript Strict Build (0 errors) + Full Headless Browser E2E Validation  

---

### 1. Executive Summary

Phase 15.2D completes the continuous forensic investigation workflow for the Marine Oil Spill Attribution Decision-Support System. Prior phases established the read-only FastAPI data bridge (Phase 15.2A), real case metadata routing (Phase 15.2B), and real geospatial layer rendering (Phase 15.2C).

Phase 15.2D establishes full, bidirectional synchronization across the analytical chain:
$$\text{CASE} \longrightarrow \text{MAP} \longrightarrow \text{TIMELINE} \longrightarrow \text{VESSEL} \longrightarrow \text{HYPOTHESIS} \longrightarrow \text{EVIDENCE} \longrightarrow \text{COUNTERFACTUAL} \longrightarrow \text{UNCERTAINTY}$$

All interactions operate strictly upon deterministic backend artifacts without synthetic data fabrication or client-side heuristic alterations.

---

### 2. Core Workflow Architecture & Synchronization

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Active Case Selection                              │
│              [Case 001: Pipeline] [Case 002: Wakashio] [Case 003: Golden Ray] │
└──────────────────────┬──────────────────────────────────────────────────────┘
                       │
       ┌───────────────┴───────────────┐
       ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────────┐
│  Geospatial Viewport    │     │  Master Timeline Scrubber   │
│  - SAR S-1 σ° Raster    │◄───►│  - Event T₀ & Observation   │
│  - Slick Polygons       │     │  - Active Epoch Scrubber    │
│  - AIS Trajectory Lines │     │  - Live Vessel Interpolation│
│  - Live Vessels at T    │     │  - Drift Particles at T     │
│  - Drift Particles at T │     └─────────────────────────────┘
│  - 4D Hypotheses at T   │
└────────────┬────────────┘
             │
             ├──────────────────────────┐
             ▼                          ▼
┌─────────────────────────┐    ┌──────────────────────────────┐
│ Candidate Ranking Table │    │   Evidence / Counterfactual  │
│ - Backend Rank Order    │    │ - Predicted vs Observed Slicks│
│ - MMSI & Vessel Name    │    │ - Forward IoU Progress Bar   │
│ - Compatibility Score   │    │ - Centroid Displacement Error│
│ - Causal Status Tag     │    │ - Particle Coverage Envelope │
└────────────┬────────────┘    └──────────────┬───────────────┘
             │                                │
             └────────────────┬───────────────┘
                              ▼
               ┌──────────────────────────────┐
               │    Inspector Drawer (Right)  │
               │ - Incident Profile           │
               │ - Selected Candidate Stats   │
               │ - 5 Evidence Component Bars  │
               │ - 4D Hypothesis Inspector    │
               │ - Scientific Legal Notice    │
               └──────────────────────────────┘
```

---

### 3. Investigation Components

#### 3.1. Coordinated 4D Investigation Timeline
- **Real Temporal Metadata:** Dynamically bounds the search envelope to the case metadata ($T_0 - 18\text{h}$ to $T_{\text{obs}} + 12\text{h}$).
- **Key Milestones:** Explicit visual pins for Incident Event ($T_0$), Sentinel-1 SAR Acquisition ($T_{\text{obs}}$), and the AIS encounter corridor.
- **Dynamic Scrubbing:** Scrubbing computes live spatiotemporal positions along recorded trajectories:
  - **Live Vessel Locations:** Evaluates `getPointAtTime()` over AIS coordinate-timestamp pairs and renders glowing vessel nodes with selected candidate highlighting.
  - **Live Drift Particles:** Evaluates particle trajectories at time $T$ to display the instantaneous state of the Monte Carlo dispersion field.
  - **Hypothesis Activation:** 4D hypothesis markers visually pulse when the active epoch is proximate ($\le 30\text{ min}$) to the hypothesis release timestamp.
- **Snap Controls:** Quick button snaps the viewport to exact incident event $T_0$.

#### 3.2. Candidate Vessel Attribution Table
- **Preserved Backend Order:** Consumes `GET /api/cases/{case_id}/attribution/ranking` directly without client-side re-sorting.
- **Columns:**
  - `Rank`: Evaluated position under causal consistency rules.
  - `Vessel Name & MMSI`: Unique identifier with monospace formatting.
  - `Type`: Vessel classification.
  - `Best Hypothesis`: Optimal 4D hypothesis link (e.g. `4DH_0001`).
  - `Compatibility`: Physical concordance index $[0.0000 - 1.0000]$.
  - `Causal Status`: Visual status pill (`AT_RELEASE`, `POST_RELEASE_ONLY`, `PRE_RELEASE_ONLY`).
  - `Support State`: Evaluated support category (`HIGH_SUPPORT`, `MODERATE_SUPPORT`, `LOW_SUPPORT`).
- **Interactive Selection:** Clicking any row updates `selectedMmsi` and `selectedHypothesisId`, highlights the vessel track and marker on the map, and routes detailed metrics to the Forensic Inspector.

#### 3.3. Evidence Components Panel
Conforms strictly to scientific evidentiary framing:
- `Drift Consistency`: Physical overlap between backward Lagrangian trajectories and vessel track.
- `Spatial Compatibility`: Euclidean distance between vessel path and reconstructed release points.
- `Source Plausibility`: Hydrodynamic likelihood of slick emergence.
- `Temporal Alignment`: Timing coincidence with known release window.
- `AIS Track Quality`: Completeness and sampling density of vessel telemetry.

> [!IMPORTANT]
> **Scientific Nomenclature Compliance:** Evidentiary indicators use terms such as *Physical Compatibility*, *Evidence Concordance*, and *Support Classification*. Terms like *"culprit"* or *"guilty"* are strictly forbidden across all views.

#### 3.4. 4D Hypothesis Inspector & Forward Simulation
When a hypothesis is selected (via map, candidate table, or inspector reset):
- **Release Origin:** Exact coordinates $(\text{Lat}, \text{Lon})$ and timestamp.
- **Observed Slick Reference:** Linkage to Sentinel-1 candidate slick polygon.
- **Forward Hydrodynamic Metrics:**
  - **Intersection over Union (IoU):** Quantitative contour overlap between forward 500-particle dispersion simulation and observed SAR slick.
  - **Centroid Displacement Error:** Distance in meters between predicted slick center and SAR detection centroid.
  - **Particle Coverage:** Percentage of released particles remaining within surveillance bounds.
  - **Predicted vs. Observed Area:** Quantitative comparison in $\text{m}^2$.

#### 3.5. Counterfactual & Simulation Comparison Viewer
Accessible via the Navigation Rail (`ATTRIBUTE: Evidence Matrix`):
- Displays high-level comparison card for the selected hypothesis.
- Interactive table of top 30 evaluated counterfactual releases.
- Honest handling for Case 002 (Wakashio) displaying physical validation notices without AIS simulations.

#### 3.6. Monte Carlo Uncertainty & Rank Stability
Accessible via the Navigation Rail (`ATTRIBUTE: Uncertainty`):
- **Ensemble Summary:** $N=500$ perturbations with random seed and parameter variances.
- **Calibration Status:** Distinct warning banner noting that compatibility scores reflect physical drift concordance rather than calibrated legal probability.
- **Rank Stability Distribution:** Evaluates Top-1 and Top-3 frequencies, mean rank, and rank standard deviation across perturbations.

---

### 4. Case-Specific Ground-Truth Integrity

| Case | Category | Ground Truth | System Behavior |
| :--- | :--- | :--- | :--- |
| **Case 001** | Pipeline Origin / Negative Control | Clean / Negative | Attribution identifies low compatibility across traffic; pipeline origin verified; zero vessel support. |
| **Case 002** | Physical Grounding Validation | Verified | Displays explicit `AIS ATTRIBUTION: ARCHIVE DATA UNAVAILABLE` domain notices; prohibits synthetic vessel fabrication. |
| **Case 003** | Blind Attribution Benchmark | Verified (Golden Ray) | Evaluates 25 vessels; M/V Golden Ray ranks #1 after causal precedence filtering; full forward IoU and centroid metrics available. |

---

### 5. Verification Results

#### 5.1. Backend Automated Test Suite
```bash
python -m pytest tests/
================= 179 passed, 2 warnings in 73.84s (0:01:13) ==================
```
- 179/179 tests passing (100%).
- Read-only data bridge, candidate generation, attribution ranking, forward simulation comparison, and uncertainty analysis verified.

#### 5.2. Frontend Production Build
```bash
npm run build
✓ 2915 modules transformed.
✓ built in 2.94s
```
- TypeScript compile (`tsc -b`) passed with 0 errors under strict type checking.

#### 5.3. Headless Browser End-to-End Validation
Automated browser subagent verified all user journeys:
1. **Case 003 Initial State:** TopHeader, map, timeline, and inspector loaded with Golden Ray data.
2. **Candidate Table Interaction:** Opened candidate table modal, inspected 25 candidates, selected Candidate #2 (`RECOVERY`), verified Inspector Drawer updated to Candidate #2.
3. **Evidence Modal:** Opened Counterfactual Viewer, verified IoU, centroid error, and area metrics.
4. **Timeline Scrubbing:** Scrubbed timeline slider, confirmed Active Epoch updated, verified `SNAP TO T₀` button.
5. **Case 002 Dataset State:** Switched to Case 002, verified `ARCHIVE DATA UNAVAILABLE` notice in Inspector, Candidate Table, and Evidence modal.
