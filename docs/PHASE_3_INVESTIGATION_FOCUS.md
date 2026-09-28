# PHASE 3 — INVESTIGATION FOCUS & VISUAL HIERARCHY

## 1. Executive Summary

Phase 3 refined the Phase 2 maritime intelligence workstation interface of the SIH26143 oil-spill investigation prototype.

**Core Objective Achieved**: The investigation story is now immediately understandable within 5–10 seconds. The visual hierarchy clearly answers:
1. **What happened?** (Incident origin & estimated $T_0$)
2. **What was observed?** (Sentinel-1 SAR scene capture, segmented slick polygons & total area)
3. **Where could the source have been?** (Calibrated Lagrangian backward drift reconstruction corridor)
4. **Which vessel is currently most compatible?** (Prominent Best-Supported Hypothesis card with rank, compatibility score, and candidate count)
5. **Why?** (Clean, structured evidence checklist covering drift, spatial, temporal, and causal metrics)
6. **What remains uncertain?** (Monte Carlo ensemble stability & sensitivity analysis)

**Scientific Integrity**: All underlying scientific algorithms, attribution rankings, counterfactual simulations, metocean forcing datasets, and API contracts remain strictly frozen and unmodified.

---

## 2. Key UI/UX Enhancements

### 2.1 Map Visual Noise Reduction & "Focus Selected" Mode
- **Problem**: The raw hypothesis dataset contained numerous vector connection lines (`vessel_to_source_vector`), creating a dense "spider web" that obscured the map.
- **Solution**:
  - Implemented `focusSelectedHypothesis` (enabled by default).
  - Selected Candidate Trajectory: High-contrast vibrant cyan line (`[56, 189, 248, 255]`, 2.5px) connecting directly to the hypothesized release origin.
  - Subordinate Hypotheses: Rendered with low opacity (`[100, 116, 139, 20]`, 0.8px), eliminating visual clutter while preserving interactive selectability.
  - Map Segmented Control: Added an ergonomic, non-intrusive toggle at top-left:
    `[FOCUS SELECTED | SHOW ALL HYPOTHESES]`.
  - Selecting another candidate in the bottom drawer or table immediately updates the focus styling.

### 2.2 Investigation Conclusion / Summary Card
- **Location**: Top of the investigation drawer, receiving primary visual emphasis.
- **Dynamic Data Presentation**:
  - **Case 003 (Golden Ray)**:
    - Headline: `BEST-SUPPORTED HYPOTHESIS`
    - Vessel Name: `GOLDEN RAY` (`#1 of 25 candidates`)
    - Classification: `MODERATE SUPPORT` (Compatibility Score: `0.6891`)
    - Qualifier: *"Highest-ranked hypothesis under the available evidence."*
  - **Case 001 (Huntington Beach Negative Control)**:
    - Headline: `NEGATIVE-CONTROL BASELINE`
    - Notice: `No Vessel Attribution Supported`
    - Qualifier: *"Passing traffic evaluated (10 vessels); no hypothesis exceeds support threshold. Origin consistent with pipeline infrastructure."*
  - **Case 002 (Wakashio Data Limitation)**:
    - Headline: `DATA LIMITATION`
    - Notice: `Historical AIS Archive Limitation`
    - Qualifier: *"Physical validation case benchmark without commercial AIS telemetry. Vessel attribution cannot be evaluated."*
- **Terminological Restraint**: Strictly avoided legal culpability claims (no terms like "culprit", "guilty", or "court proof").

### 2.3 Terminology & Restructured Inspector Hierarchy
- **Header Terminology**: Renamed `FORENSIC INSPECTOR` $\rightarrow$ `INVESTIGATION INSPECTOR` to accurately reflect decision-support evidence rather than courtroom determination.
- **Progressive Disclosure Accordion**:
  - **A. Investigation Summary**: Always visible at top.
  - **B. Observation Evidence** *(Expanded by default)*: Incident name, estimated $T_0$, Sentinel-1 platform, capture time, segmented slick count, and surface area in hectares.
  - **C. Source Reconstruction** *(Collapsed by default)*: Drift model, HYCOM current source, ERA5 wind source, evaluated slicks.
  - **D. AIS Candidates** *(Expanded by default)*: Candidate count, candidate identity, compatibility score, comparison action, and the structured "Why This Hypothesis?" checklist.
  - **E. 4D Hypothesis & Simulation** *(Collapsed by default)*: Selected hypothesis ID, forward simulation IoU overlap, centroid error, and particle coverage.
  - **F. Uncertainty & Sensitivity** *(Collapsed by default)*: Monte Carlo ensemble iterations (100 runs), Rank #1 stability percentage, and metocean perturbation notice.
  - **G. Data Readiness & Provenance** *(Collapsed by default)*: Pillar readiness status, SHA-256 artifact checksum, and reproducible provenance statement.

### 2.4 Structured "Why This Hypothesis?" Checklist
- Converted dense text into a clean visual checklist with title case and indented metrics:
  - `✓ Drift compatibility` — Centroid error: `100.86 m`
  - `✓ Spatial compatibility` — Source distance: `1.99 km`
  - `✓ Temporal compatibility` — Release time: `Sun, 08 Sep 2019 07:25:31 UTC`
  - `✓ Causal consistency` — `AT_RELEASE · Eligible`
- Added progressive disclosure: `▼ More evidence dimensions` button expands secondary metrics (Source plausibility score: `0.47`, AIS track quality: `bracketed_interpolation (69s gap)`, Particle mean offset: `98.9 m`, Primary Strength: `Temporal Compatibility (strong, 0.89)`).

### 2.5 Contextual Map Legend
- **Default View**: Clean, compact palette displaying the 5 essential layers:
  - `● Incident (T₀)`
  - `● Detected slick`
  - `━ Selected vessel`
  - `━ Selected drift`
  - `● Source hypothesis`
- **Secondary Layers**: Expandable on demand via `+ Secondary layers` (Other vessels, Lagrangian particles, Forward simulation plume, Centroid offset error).

### 2.6 Domain Tooltips
- Enhanced glossary with concise tooltips for:
  - `SAR`, `AIS`, `4D hypothesis`, `IoU`, `Causal consistency`, `Uncertainty`, `T₀`, and `Tobs`.

---

## 3. Preserved Functionality

All previous workstation shell capabilities remain intact:
- Top navigation with incident dropdown, rapid jury demo buttons, and 4-stage workflow stepper (`01 OBSERVE → 02 INVESTIGATE → 03 ATTRIBUTE → 04 REPORT`).
- Master 4D scrubber timeline with embedded replay controls, step buttons, snap-to-$T_0$, snap-to-$T_{\text{obs}}$, and speed multipliers.
- Candidate ranking bottom sheet drawer with responsive height.
- Candidate comparison modal and side-by-side metric inspection.
- Georeferenced SAR $\sigma^0$ raster visualization derivative toggle.

---

## 4. Verification & Validation Battery

### 4.1 Automated Test Suite
- **Backend Test Suite**:
  ```bash
  python -m pytest tests/
  ```
  **Result**: `199 passed, 2 warnings in 43.41s` (100% pass rate).
- **Frontend Production Build**:
  ```bash
  npm run build
  ```
  **Result**: Built in `1.49s` with `0 TypeScript or bundling errors`.

### 4.2 Interactive Browser Validation
- **Case 003 (Golden Ray)**: Verified Focus Selected mode removes spider-web noise, top summary displays M/V Golden Ray `#1 of 25` Moderate Support, Why This Hypothesis checklist expands cleanly, and contextual legend toggles secondary layers.
- **Case 001 (Huntington Beach)**: Verified negative control summary displays "No Vessel Attribution Supported" and explains that no vessel exceeds threshold under pipeline baseline.
- **Case 002 (Wakashio)**: Verified data limitation summary displays "Historical AIS Archive Limitation" and clarifies missing telemetry.
- **Screen Recording**: `phase3_investigation_focus_verification_1790348306649.webp`.
- **UI Capture**: `golden_ray_ui_1790348681072.png`.

---

## 5. Conclusion

Phase 3 successfully delivered investigation focus, visual hierarchy, and instant cognitive clarity for the SIH26143 decision-support system without modifying any scientific algorithms or data contracts.
