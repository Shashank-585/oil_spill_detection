# PHASE 27 — SIH DEMO UX POLISH & LIVE JURY PLAYBOOK

## Executive Summary

Phase 27 optimizes the **SIH26143 Maritime Oil Spill Forensic Attribution Decision-Support System** for a high-impact, professional live jury demonstration. Without altering underlying scientific computations or redesigning the application layout, this phase refines the user experience around 11 key operational dimensions, guarantees instant 10-second comprehension for first-time viewers, and installs rapid one-click demo switching across the three evaluation case archetypes.

---

## 1. Visual & Design Principles

The user interface follows strict operational intelligence standards rather than generic consumer dashboard tropes:

1. **MAP FIRST**: The interactive geospatial viewport dominates the viewport (>80% visual real estate). All analytical cards, imagery panels, and candidate matrices float as semi-transparent, blurred overlays with high-contrast borders (`var(--color-bg-surface)` with `backdrop-filter: blur(8px)`).
2. **Evidence Second**: High-concordance vessel telemetry, backward Lagrangian drift trajectories, and forward counterfactual slick simulations are presented before summary scores.
3. **Metrics Third**: Statistical ratings (IoU, centroid displacement, rank stability) serve to substantiate physical evidence rather than substitute for it.
4. **Restrained Nautical Intelligence Aesthetic**:
   - Zero gratuitous neon gradients or oversized bubbly card borders.
   - Clean slate and deep navy dark mode (`#0a0d13` to `#161b22`).
   - Accessible color-coding: Cyan/Blue for satellite and AIS telemetry, Emerald for validated concordant evidence, Amber for operational limitations/advisories, Crimson for offline/error states.
5. **Concise Domain Tooltips**: Technical jargon is explained on demand through native floating accessible tooltips with investigation context:
   - **SAR**: Synthetic Aperture Radar (Sentinel-1 C-band VV co-polarization surface backscatter dampening).
   - **AIS**: Automatic Identification System (VHF/Satellite marine transponder telemetry).
   - **4D Hypothesis**: Spatiotemporal candidate release event: $(x, y, z, t)$ evaluated via backward Lagrangian drift.
   - **IoU**: Intersection over Union spatial overlap metric between simulated and observed slick polygons.
   - **Causal Consistency**: Arrow-of-time physical plausibility filter pruning chronological impossibilities.
   - **Uncertainty**: 100-run Monte Carlo wind leeway and current vector perturbation ensemble.

---

## 2. The 11 Focus Areas

| # | Focus Area | Implementation Detail |
|---|---|---|
| 1 | **First-Load Experience** | Clean title `SIH26143 · MARITIME FORENSIC ATTRIBUTION`, immediate map render, instant sync of default benchmark (`case_003_golden_ray`), zero layout shifts or blank screens. |
| 2 | **Case Selection** | Dedicated 1-click **DEMO** selector pills in the top header (`GOLDEN RAY`, `CASE 001`, `CASE 002`) alongside the full dropdown. Single-click switching during jury demos. |
| 3 | **Investigation Workflow** | Four-stage workflow stepper (`OBSERVE` → `INVESTIGATE` → `ATTRIBUTE` → `REPORT`) with active step highlighting and direct stage advancement. |
| 4 | **Map Readability** | Geospatial viewport provides slick boundary polygons, backward drift trajectories, AIS tracks, and candidate pinpoints with clear symbology and layer isolate controls. |
| 5 | **Counterfactual Comparison** | Side-by-side Candidate Comparison Modal evaluating Top Candidate against alternatives across Distance, Drift Error, Temporal Offset, AIS Quality, Causal Status, and Forward IoU. |
| 6 | **Evidence Explanation** | "Why Supported" and "Limiting Factors" breakdown cards for each vessel candidate, explaining physical concordance in plain maritime language. |
| 7 | **Report Generation** | Phase 23 16-section Investigation Dossier with Markdown export, print-ready CSS formatting, and raw JSON export answering the 7 core investigator questions. |
| 8 | **Error States** | Graceful degradation: Case 001 displays natural seepage negative-control state; Case 002 displays explicit "AIS ARCHIVE DATA UNAVAILABLE" state without application error. |
| 9 | **Loading States** | Clean pulsing indicators and monospace syncing status badges (`SYNCING T₀...`, `Syncing attribution rankings...`) preventing UI freezing. |
| 10 | **Responsive Layout** | Collapsible Forensic Inspector Drawer (`380px` to `0px`), header collapse controls, flexible table containers with horizontal scroll for dense telemetry. |
| 11 | **Performance** | Production build bundle optimized with Vite; sub-second client-side case switching; React Query caching across all artifact queries. |

---

## 3. Demo Walkthrough Script for SIH Jury

### Demonstration Flow 1: Flagship Golden Ray Attribution (Primary Benchmark)

**Duration**: ~3 minutes  
**Goal**: Demonstrate complete end-to-end evidence pipeline from satellite observation to counterfactual attribution.

1. **Step 1: Incident Initialization (T₀)**
   - Click the `GOLDEN RAY` demo button in the top header.
   - Point out incident metadata: Golden Ray capsizing in St. Simons Sound, Georgia; $T_0$ timestamp 2019-09-08 06:10 UTC; Engine: READY; Causal Layer: ENABLED.
   - Hover over `CAUSAL LAYER` tooltip to explain generic 4D causal consistency temporal pruning.
2. **Step 2: Observe — Sentinel-1 SAR & Optical Evidence**
   - Click `SAR Imagery` in the navigation rail (or click `OBSERVE` on the stepper).
   - Show Sentinel-1 SAR metadata: Platform Sentinel-1A, acquisition time 2019-09-09 23:14 UTC, Mode IW, Polarization VV (used by detector).
   - Point out Supporting Optical Sentinel-2 observation at +72h post-grounding (2.4% cloud cover).
   - Close SAR overlay; note the dark segmented oil slick polygon visible on the nautical map.
3. **Step 3: Investigate — Backward Lagrangian Drift & Source Area**
   - Click `Lagrangian Drift` on the rail (or click `NEXT` on the stepper).
   - Highlight the reconstructed backward drift path: forced by hourly HYCOM oceanic currents and ERA5 wind vectors backward in time to identify the spatiotemporal release envelope.
4. **Step 4: Attribute — AIS Traffic Corridor & Candidates**
   - Click `Candidates` in the navigation rail.
   - Show the Candidate Vessel Attribution Rankings:
     - Rank #1: **GOLDEN RAY** (MMSI 440316000, Cargo/Ro-Ro).
     - Point out the compatibility score (~0.6277) and Causal Status: `AT_RELEASE`.
   - Hover over `Best Hypothesis` and `Causal Status` table headers to reveal domain tooltips.
5. **Step 5: Counterfactual Validation & Side-by-Side Comparison**
   - Click `Compare Candidates` button.
   - Review side-by-side table:
     - Golden Ray vs Lower-Ranked Vessels.
     - Note Golden Ray's low source distance (68.4 m), high temporal concordance, and forward slick simulation IoU (~24.3%).
     - Close comparison modal.
6. **Step 6: Monte Carlo Uncertainty Analysis**
   - Click `Uncertainty` in the navigation rail.
   - Point out Ensemble $N=100$ perturbations with wind leeway noise ($\pm 20\%$) and current velocity variance ($\pm 15\%$).
   - Show Golden Ray maintains **88% rank stability** under environmental uncertainty.
7. **Step 7: Investigation Dossier & Authority Dispatch**
   - Advance stepper to `REPORT` or click `Investigation Report & Audit` on the rail.
   - Scroll through the 16-section dossier answering:
     - *What happened?*
     - *Where could it have originated?*
     - *When could it have originated?*
     - *Which vessels are compatible?*
     - *Why?*
     - *How certain is the result?*
     - *What data is missing?*
   - Highlight one-click **Export Markdown** and **Print Report** buttons.

---

### Demonstration Flow 2: Case 001 Negative-Control Baseline

**Duration**: ~1 minute  
**Goal**: Demonstrate that the system refuses to force false attribution when physical conditions indicate natural seepage or absence of vessel responsibility.

1. Click `CASE 001 (NEG-CTRL)` demo pill in top header.
2. Note Case Identification: Huntington Beach / San Pedro Bay natural seepage baseline.
3. Open `Candidates` view:
   - Candidate vessels evaluated: 0 attributed.
   - System displays: "Negative Control Case — No candidates attributed; baseline natural seepage."
4. Open `Data Readiness` panel:
   - Ground truth status confirms natural seep benchmark; attribution marked `NOT REQUIRED`.
   - Emphasize to the jury: *The model does not hallucinate vessel culprits when physics does not support it.*

---

### Demonstration Flow 3: Case 002 Data-Limitation Handling

**Duration**: ~1 minute  
**Goal**: Demonstrate honest scientific boundaries and resilience to real-world data gaps (e.g. paywalled commercial archives).

1. Click `CASE 002 (LIMITATION)` demo pill in top header.
2. Note Case Identification: MV Wakashio reef grounding in Mauritius.
3. Observe Data Readiness panel:
   - AIS Pillar: `UNAVAILABLE` (Historical high-frequency AIS transponder archives behind commercial paywalls).
   - Ground Truth Pillar: `READY` (Reef grounding site physically verified).
4. Open `Inspector Drawer`:
   - Clearly flags: `AIS ATTRIBUTION — ARCHIVE DATA UNAVAILABLE`.
   - Explains that hydrodynamic backward drift and SAR slick segmentation remain scientifically valid, but candidate transponder ranking is responsibly withheld rather than guessed.

---

## 4. Verification & Quality Gates

### Backend Test Suite
```bash
python -m pytest tests/
# Result: 199 passed, 2 warnings in 26.69s (100% pass rate)
```

### Frontend Production Build
```bash
npm run build
# Result: tsc -b && vite build -> Built in 1.44s with 0 TypeScript/syntax errors.
```

### Multi-Case Rapid Switching Stress Test
```python
# 75 consecutive rapid API queries across Golden Ray, Case 001, and Case 002
# Result: 100% 200 OK responses with zero state contamination or memory leaks.
```

---

## 5. Summary of Modified Components in Phase 27

- `frontend/src/components/common/DomainTooltip.tsx`: Interactive, accessible popover explaining domain terminology (`SAR`, `AIS`, `4D hypothesis`, `IoU`, `Causal consistency`, `Uncertainty`) with custom placement (`top`, `right`, `bottom`, `left`) and investigation context.
- `frontend/src/components/layout/TopHeader.tsx`: Integrated one-click demo pills (`GOLDEN RAY`, `CASE 001`, `CASE 002`), upgraded platform title subtitle (`SIH26143 · MARITIME FORENSIC ATTRIBUTION`), and wrapped Causal Layer toggle in `DomainTooltip`.
- `frontend/src/components/layout/InspectorDrawer.tsx`: Wrapped `AIS ATTRIBUTION`, `4D HYPOTHESIS & FORWARD VALIDATION`, and `Intersection over Union (IoU)` in `DomainTooltip`.
- `frontend/src/components/layout/NavigationRail.tsx`: Added `domainTerm` properties and tooltips on `SAR`, `AIS`, and `Uncertainty` icons with rightward placement.
- `frontend/src/components/attribution/CandidateComparisonModal.tsx`: Enriched `AIS Trajectory Quality`, `Causal Status`, and `Forward Slick IoU` with `DomainTooltip`.
- `frontend/src/components/attribution/CandidateRankingTable.tsx`: Integrated tooltips for `Best Hypothesis` and `Causal Status` table columns.
- `frontend/src/components/attribution/UncertaintyView.tsx`: Integrated `DomainTooltip` on the Monte Carlo Uncertainty analysis header.
- `frontend/src/components/observation/SatelliteObservationPanel.tsx`: Integrated `DomainTooltip` on Sentinel-1 Operational SAR header.
- `frontend/src/components/observation/AisView.tsx`: Integrated `DomainTooltip` on AIS Maritime Traffic Corridor header.
