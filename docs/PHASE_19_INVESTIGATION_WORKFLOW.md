# PHASE 19 — INVESTIGATION WORKFLOW V2 REPORT

**Project:** SIH26143 — Marine Oil Spill Attribution Decision-Support System  
**Phase:** Phase 19 — Investigation Workflow V2  
**Date:** 2026-09-23  
**Status:** COMPLETED & VERIFIED (179/179 Pytest Passing, Clean Production Build)

---

## 1. Executive Summary & Objective

Phase 19 upgrades the decision-support system to provide an intuitive, investigator-facing workflow:
$$\text{OBSERVE} \longrightarrow \text{INVESTIGATE} \longrightarrow \text{ATTRIBUTE} \longrightarrow \text{REPORT}$$

The objective was achieved **strictly without modifying any scientific algorithms or formulas**:
- Frozen scientific modules (`src/attribution/`, `src/drift/`, `src/detection/`, `src/satellite/`) remained **100% untouched**.
- Zero modification to attribution weights, causal consistency logic, or calibration datasets.
- The UI exclusively consumes real scientific artifacts and read-only FastAPI data bridge endpoints.

---

## 2. Four-Stage Investigation Workflow Architecture

### Stage 01: OBSERVE
* **Purpose**: Establish what the remote sensing and maritime telemetry observation show.
* **Core Data Presented**:
  - Copernicus Sentinel-1 Synthetic Aperture Radar (SAR) acquisition ($T_{\text{obs}}$).
  - Radiometrically calibrated backscatter intensity ($\sigma^\circ$ linear and dB percentiles: p10, p50, p90).
  - Adaptive CFAR dark-spot segmented slick geometries and polygon areas ($m^2$).
  - Terrestrial and satellite AIS corridor traffic context.
* **Map Configuration**: SAR raster `ON`, Slick polygons `ON`, AIS tracks `ON`, Drift particles `OFF`.

### Stage 02: INVESTIGATE
* **Purpose**: Determine where and when the discharge originated via backward source reconstruction.
* **Core Data Presented**:
  - Runge-Kutta 4th-order Eulerian-Lagrangian backward time integration ($dt < 0$).
  - Hydrodynamic surface current vectors (HYCOM GLBy0.08°).
  - Wind leeway forcing (ECMWF ERA5 10m wind, leeway factor $\alpha = 3.10\%$, deflection $\theta = +15^\circ$).
  - Turbulent Brownian diffusion ($D_h = 1.00\text{ m}^2/\text{s}$).
  - 42 source release horizons ($T-2\text{h}$ to $T-24\text{h}$) with dynamic dispersion radiuses ($\pm 250\text{ m}$ to $\pm 2200\text{ m}$).
* **Map Configuration**: SAR raster `OFF`, Slick polygons `ON`, AIS tracks `OFF`, Backward drift particles `ON`, Candidate markers `ON`.

### Stage 03: ATTRIBUTE
* **Purpose**: Evaluate vessel hypotheses against counterfactual forward simulations under causal physics.
* **Core Data Presented**:
  - Candidate vessels evaluated in the maritime traffic corridor (25 vessels for Case 003).
  - 256 4D release hypotheses ($x, y, z, t$).
  - Counterfactual forward particle dispersion simulations.
  - Multi-criteria composite evidence scoring:
    $$S_{\text{composite}} = w_{\text{spatial}} S_{\text{spatial}} + w_{\text{temporal}} S_{\text{temporal}} + w_{\text{drift}} S_{\text{drift}} + w_{\text{track}} S_{\text{track}}$$
  - 4D Causal Precedence Enforcement: Prunes vessels entering the spill region *after* the slick was formed.
  - Uncertainty Analysis: Bootstrap ensemble perturbation ($N=500$) and rank stability index.
* **Attribution Finding (Case 003)**: **M/V Golden Ray** (MMSI `538007762`) correctly identified as **Rank #1** with score `0.6891` and causal status `AT_RELEASE`.
* **Map Configuration**: SAR raster `OFF`, Slick polygons `ON`, AIS tracks `ON`, Drift particles `ON`, Candidate markers `ON`.

### Stage 04: REPORT
* **Purpose**: Produce a court-admissible, investigator-facing forensic synthesis dossier.
* **Core Data Presented**:
  - Executive Incident Overview: Incident ID, coordinates, datetime datum ($T_0$ vs $T_{\text{obs}}$), validation role.
  - 4-Stage Narrative Synthesis: Direct links and summaries for Observe, Investigate, and Attribute.
  - Complete Candidate Attribution Ranking Table.
  - Cryptographic Data Integrity Ledger: SHA-256 integrity verification across Sentinel-1, NetCDF, and AIS.
  - Regulatory Export Actions: One-click `EXPORT AUDIT JSON` and `EXPORT CSV`.
  - Quick Printing: `PRINT DOSSIER` for paper/PDF distribution.

---

## 3. UI/UX Hardening & Components Modified

1. **`InvestigationStepper.tsx`** ([`frontend/src/components/workflow/InvestigationStepper.tsx`](file:///c:/Users/rkchi/OneDrive/Desktop/Oil_spill/frontend/src/components/workflow/InvestigationStepper.tsx)):
   - Prominently positioned in the top header.
   - Distinct stage buttons with icons, active glowing state, and completed checkmarks.
   - `◀ PREV` and `NEXT ▶` buttons for step-by-step guided demos.
2. **`TopHeader.tsx`** ([`frontend/src/components/layout/TopHeader.tsx`](file:///c:/Users/rkchi/OneDrive/Desktop/Oil_spill/frontend/src/components/layout/TopHeader.tsx)):
   - Integrated stepper seamlessly between the Case Switcher and the Causal Physics Engine toggle.
   - Clean $T_0$ clock datum display.
3. **`NavigationRail.tsx`** ([`frontend/src/components/layout/NavigationRail.tsx`](file:///c:/Users/rkchi/OneDrive/Desktop/Oil_spill/frontend/src/components/layout/NavigationRail.tsx)):
   - Re-categorized navigation items into the 4 workflow categories (`OBSERVE`, `INVESTIGATE`, `ATTRIBUTE`, `REPORT`).
4. **`investigationStore.ts`** ([`frontend/src/store/investigationStore.ts`](file:///c:/Users/rkchi/OneDrive/Desktop/Oil_spill/frontend/src/store/investigationStore.ts)):
   - Added `activeStage: InvestigationStage` state and `setActiveStage` action with layer visibility presets.
   - Bi-directional synchronization between `activeStage` and `activeWorkspace`.
5. **`InvestigationReportView.tsx`** ([`frontend/src/components/report/InvestigationReportView.tsx`](file:///c:/Users/rkchi/OneDrive/Desktop/Oil_spill/frontend/src/components/report/InvestigationReportView.tsx)):
   - Implemented the comprehensive Stage 04 reporting modal with export capabilities.
6. **`App.tsx`** ([`frontend/src/App.tsx`](file:///c:/Users/rkchi/OneDrive/Desktop/Oil_spill/frontend/src/App.tsx)):
   - Full URL synchronization (`/cases/:case_id/:stage_or_view` and `#case=...&view=...`).
   - Active workflow stage badge in the upper right.

---

## 4. Case-Specific Validation Results

| Case ID | Incident Name | Validation Role | Verified Behavior |
| :--- | :--- | :--- | :--- |
| **Case 001** | Huntington Beach Pipeline | Negative-Control Benchmark | Pipeline rupture source correctly preserved; passing vessels exonerated; legal attribution disclaimer visible. |
| **Case 002** | MV Wakashio Grounding | Physical Observation Benchmark | Physical Sentinel-1 SAR observations and drift verified; honest disclosure *"AIS ATTRIBUTION ARCHIVE DATA UNAVAILABLE"* displayed without crashing. |
| **Case 003** | M/V Golden Ray Capsizing | Blind Attribution Ground-Truth | 42 source hypotheses $\to$ 25 vessels $\to$ 256 hypotheses $\to$ 256 forward simulations $\to$ **M/V Golden Ray Rank #1** under causal consistency. |

---

## 5. Verification Evidence

- **Frontend TypeScript & Vite**:
  ```bash
  cd frontend && npm run build
  # Output: tsc -b && vite build -> 0 errors, built in 2.20s
  ```
- **Backend & Scientific Pytest Suite**:
  ```bash
  python -m pytest tests/ -q
  # Output: 179 passed, 2 warnings in 37.44s (100% pass rate)
  ```
- **Browser Automation Test**:
  - Stepper navigation: Verified through all 4 stages.
  - Case switching: Verified across Case 003 $\to$ Case 001 $\to$ Case 002 $\to$ Case 003.
  - Zero console errors, zero WebGL context drops.
  - Live recording captured and saved to artifacts.

---

## 6. Disclosures & Known Limitations

1. **Case 002 AIS Telemetry**: Historical high-resolution AIS receiver coverage was not archived for the Indian Ocean Mauritius coastal segment in 2020. The system surfaces this limitation explicitly in both the AIS view and the Report dossier.
2. **Case 001 Pipeline Root Cause**: Case 001 serves as a negative control for vessel discharge; the system evaluates traffic in the corridor but correctly indicates that oil originated from subsea pipeline infrastructure.
3. **Map Rendering Constraints**: WebGL hardware acceleration in standard web browsers renders up to 500 active Lagrangian drift particle paths simultaneously without degradation.
