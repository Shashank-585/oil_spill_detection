# Phase 23 — Investigation Dossier & Export

## 1. Executive Summary & Objective

Phase 23 delivers a **one-click, investigator-facing Investigation Dossier and Multi-Format Export** capability for the SIH26143 Maritime Oil Spill Attribution Decision-Support System.

### Core Principles
- **Strictly Non-Modifying ("Immutable Science")**: Leverages existing, verified scientific pipeline outputs (SAR detections, backward drift distributions, candidate associations, counterfactual simulations, and uncertainty analyses) without modifying or recomputing underlying science.
- **Forensic Decision Support Framing**: Strictly adheres to neutral, objective forensic language:
  - Uses: `"best-supported hypothesis"`, `"investigation evidence"`, `"data limitation"`.
  - Avoids: `"culprit"`, `"guilty"`, `"legal proof"`, `"chain of custody for court"`.
- **Complete Investigative Coverage**: Directly answers the seven fundamental questions required by maritime environmental investigators and coast guards:
  1. *What happened?*
  2. *Where could it have originated?*
  3. *When could it have originated?*
  4. *Which vessels are compatible?*
  5. *Why?*
  6. *How certain is the result?*
  7. *What data is missing?*

---

## 2. 16-Section Standard Dossier Architecture

The dossier integrates sixteen standardized, forensic-grade sections:

```
┌────────────────────────────────────────────────────────────────────────┐
│               PHASE 23 INVESTIGATION DOSSIER STRUCTURE                 │
├────────────────────────────────┬───────────────────────────────────────┤
│ 1. Case Identification         │ Metadata, AOI bounds, incident T₀     │
│ 2. Executive Summary           │ 7 Core Investigative Q&A Matrix       │
│ 3. Satellite Observation       │ Sentinel-1 SAR acquisition parameters │
│ 4. Detected Slick              │ CFAR dark patch geometries & area (ha)│
│ 5. Environmental Conditions    │ HYCOM currents & ERA5 wind fields     │
│ 6. Source Reconstruction       │ Backward Lagrangian RK4 drift plume   │
│ 7. AIS Coverage                │ Transponder reception & temporal span │
│ 8. Candidate Vessels           │ Spatiotemporal corridor intersections │
│ 9. 4D Hypotheses               │ Combinatorial release hypotheses      │
│ 10. Counterfactual Simulation  │ Forward hydrodynamic dispersion runs  │
│ 11. Evidence Ranking           │ Multi-metric composite score rankings │
│ 12. Causal Consistency         │ Temporal precedence & response filter │
│ 13. Uncertainty Analysis       │ 50-run Monte Carlo rank stability     │
│ 14. Data Limitations           │ Forensic boundaries & missing data    │
│ 15. Conclusion                 │ Best-supported hypothesis synthesis   │
│ 16. Provenance & Integrity     │ SHA-256 integrity hash & audit trail  │
└────────────────────────────────┴───────────────────────────────────────┘
```

---

## 3. Case-by-Case Content & Physical Validation

### Case 001: Huntington Beach / San Pedro Bay (October 2021)
- **Role**: **Negative Safety Benchmark (Non-Vessel Origin)**.
- **Physical Reality**: Underwater pipeline rupture (*Pipeline 001* / Beta offshore platform).
- **Attribution Behavior**:
  - 10 passing commercial transit vessels evaluated in the shipping channel.
  - **No forced vessel attribution**: All candidate vessels are identified as background commercial traffic.
  - Causal consistency and counterfactual modeling verify that passing vessels had no causal connection with the slick.
  - Conclusion explicitly states: `"Negative Control: Underwater Pipeline Failure (Non-Vessel Origin)"`.

### Case 002: MV Wakashio (Mauritius, July–August 2020)
- **Role**: **Physical Validation Benchmark**.
- **Physical Reality**: Bulk carrier grounded on Point d'Esny reef; fuel tanks breached post-grounding.
- **Attribution Behavior**:
  - Satellite SAR slick detection and hydrodynamic dispersion models are physically verified.
  - Dynamic multi-vessel regional AIS archives are commercially paywalled / unavailable for open attribution.
  - Section 7 and Section 14 explicitly state: `"AIS archive missing: multi-vessel regional AIS archives not acquired; candidate ranking suppressed to prevent fabricated vessel attributions"`.

### Case 003: M/V Golden Ray (St. Simons Sound, September 2019)
- **Role**: **Blind Attribution Validated Benchmark**.
- **Physical Reality**: Vehicle carrier capsized in St. Simons Sound upon outbound transit from the Port of Brunswick.
- **Exact Numerical Alignment with Pipeline Artifacts**:
  - **Source Hypotheses Evaluated**: `42` (6 slick candidates $\times$ 7 backward drift temporal horizons).
  - **Candidate Vessels in AOI**: `25` vessels identified within the spatiotemporal search window.
  - **4D Vessel/Release Hypotheses**: `256` spatiotemporal pairings.
  - **Counterfactual Simulations**: `256` forward Lagrangian hydrodynamic simulations (500 particles per run).
  - **Spill Comparisons**: `256` multi-metric comparisons (IoU, Hausdorff, Chamfer, Centroid).
  - **Vessel Rankings Evaluated**: `25` unique vessels ranked.
  - **Attribution Outcome**: **`GOLDEN RAY (MMSI 538007762)` achieves Rank #1** (composite evidence score: `0.6891`).
  - **Causal Consistency**: Verified **`AT_RELEASE`**. Escort tugs (*Dorothy Moran*, *Ann Moran*) and pilot vessels are classified as **`DISQUALIFIED_POST_EVENT`** emergency responders because their proximity occurred strictly post-capsizing.
  - **Uncertainty Analysis**: **`100% Rank Stability`** across 50 Monte Carlo metocean ensemble perturbations, with a margin of `+0.284` over Rank #2.

---

## 4. Multi-Format Export Infrastructure

### 1. Clean Print & PDF Export
- Implemented in `frontend/src/components/report/InvestigationReportView.tsx`.
- Built-in `@media print` CSS rules automatically optimize the layout for letter/A4 paper:
  - Suppresses interactive navigation headers, close buttons, and timeline scrubbers.
  - Forces crisp black-and-white background contrast with page-break protection on cards (`page-break-inside: avoid`).
  - Formats tables, metrics, and forensic QA items for document printing or "Save to PDF" via browser print dialog.

### 2. Full 16-Section JSON Export
- Accessible via the **EXPORT JSON** action button in the investigator report view.
- Downloads `marine_spill_investigation_dossier_<case_id>_<timestamp>.json`, preserving all nested numerical metrics, timestamps, coordinate bounds, and SHA-256 provenance hashes.

### 3. Candidate Evidence CSV Export
- Accessible via the **EXPORT CSV** action button in the investigator report view.
- Downloads `marine_spill_candidate_evidence_<case_id>_<timestamp>.csv` containing tabular candidate vessel rankings, MMSIs, vessel types, evidence scores, and evidence states.

### 4. REST API Endpoints
- `GET /api/cases/{case_id}/dossier` — Returns the complete Pydantic-validated `InvestigationDossier` object.
- `GET /api/cases/{case_id}/report` — Alias endpoint for integration compatibility.

---

## 5. Verification & Acceptance Testing

1. **Backend & Test Suite Integrity**:
   - Automated pytest suite executed across all 22 test files:
     ```powershell
     python -m pytest tests/ -v
     # 181 passed in 66.91s
     ```
   - API data bridge verification:
     ```powershell
     python -m pytest tests/test_api_bridge.py -v
     # 18 passed in 4.32s
     ```
2. **Frontend Build Verification**:
   - TypeScript compilation and Vite production bundling verified:
     ```powershell
     cd frontend
     npm run build
     # tsc -b && vite build
     # Built in 5.91s, 0 errors.
     ```
3. **Infrastructure Health Check**:
   - Executed root verification script:
     ```powershell
     python health_check.py
     # HEALTH CHECK STATUS: PASSED - ALL INFRASTRUCTURE & PRODUCTS OK
     ```
