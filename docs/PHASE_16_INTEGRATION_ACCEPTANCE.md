# SIH26143 — Phase 16 Full System Integration & Acceptance Test Report

**Project:** SIH26143 — Marine Oil Spill Attribution Decision-Support System  
**Role:** Senior Integration Engineer & QA Lead  
**Status:** ACCEPTANCE PASSED  
**Date:** September 12, 2026  
**Test Suite:** `pytest` (179/179 passed), `npm run build` (Clean exit code 0)  

---

## 1. Executive Summary & Verification Objective

Phase 16 executes a full end-to-end integration and acceptance test of the SIH26143 Marine Oil Spill Attribution Decision-Support System. The goal was to rigorously prove that:

$$\text{FRONTEND} \longleftrightarrow \text{FASTAPI} \longleftrightarrow \text{EXISTING SCIENTIFIC ARTIFACTS}$$

functions as one unified, resilient, and scientifically honest operational application.

### Absolute Immutable Boundary Compliance
In strict adherence to requirements, the core scientific baseline was frozen:
- **`src/attribution/`**: UNMODIFIED
- **`src/drift/`**: UNMODIFIED
- **`src/detection/`**: UNMODIFIED
- **`src/satellite/`**: UNMODIFIED
- **Zero modification** to scientific formulas, causal logic, drift equations, or threshold weights.
- **Zero case-specific hardcoding** in frontend components.
- **Zero fabrication** of vessel rankings or synthetic scientific layers.

---

## 2. System Integration Matrix

The following matrix records the verified integration status for each registered benchmark case across all system dimensions:

| Dimension | Case 001 (Negative Control) | Case 002 (Wakashio) | Case 003 (Golden Ray) | Verification Method |
| :--- | :--- | :--- | :--- | :--- |
| **API Connectivity** | AVAILABLE | AVAILABLE | AVAILABLE | HTTP 200 via `GET /api/cases/{case_id}` |
| **Map Viewport** | AVAILABLE | AVAILABLE | AVAILABLE | MapLibre dark nautical base + deck.gl |
| **SAR Imagery / Stats** | AVAILABLE | AVAILABLE | AVAILABLE | Sentinel-1 SAR raster info & preprocessed metrics |
| **Slick Geometries** | AVAILABLE | AVAILABLE | AVAILABLE | GeoJSON vector polygons rendered on deck.gl |
| **AIS Vessel Tracks** | AVAILABLE (Sparse) | UNAVAILABLE (Honest Notice) | AVAILABLE (25 vessels) | Dynamic GeoJSON trajectory streaming |
| **Drift Trajectories**| AVAILABLE | AVAILABLE (Ground truth verified) | AVAILABLE (Lagrangian forward & backward) | GeoJSON particles & trajectory paths |
| **Hypotheses** | AVAILABLE (0 generated) | UNAVAILABLE (Honest Notice) | AVAILABLE (102 hypotheses) | 4D spatiotemporal release hypotheses |
| **Candidate Ranking** | AVAILABLE (0 candidates) | UNAVAILABLE (Honest Notice) | AVAILABLE (25 ranked candidates) | Causal consistency composite scoring |
| **Evidence Breakdown**| AVAILABLE (N/A message) | UNAVAILABLE (Honest Notice) | AVAILABLE (5-axis radar & breakdown) | Spatial, temporal, drift, plausibility, AIS |
| **Causal Status** | AVAILABLE (N/A) | UNAVAILABLE (Honest Notice) | AVAILABLE (`AT_RELEASE`, `VALID_PRE_EVENT`) | Counterfactual causal verification engine |
| **Uncertainty Bounds** | AVAILABLE | AVAILABLE (Physical error only) | AVAILABLE (Monte Carlo & weight bounds) | Sensitivity & confidence intervals |
| **Master Timeline** | AVAILABLE (Case range) | AVAILABLE (Case range) | AVAILABLE (Full multi-horizon scrubber) | Synchronized spatiotemporal playback |
| **Inspector Drawer** | AVAILABLE | AVAILABLE | AVAILABLE | Dynamic deep-dive context panel |

*Legend: AVAILABLE (Fully integrated and displaying validated data) | UNAVAILABLE (Honest domain limitation surfaced without synthetic data) | ERROR (0 errors recorded).*

---

## 3. End-to-End Case Verification

### 3.1 Case 001 — Negative Control (Pipeline Origin)
- **Scientific Premise:** Fixed offshore infrastructure / pipeline leak where no vessel is culpable.
- **API Response:** `datasets_available: { sar: true, slicks: true, ais: true, forward_drift: true, attribution: false }`.
- **Integrity Verification:**
  - Case metadata correctly identifies offshore incident in Gulf of Mexico (28.45°N, -89.85°W).
  - SAR metrics and slick geometry CS_0001 correctly load from Sentinel-1 preprocessing artifacts.
  - AIS query reveals 2 transient vessels in spatiotemporal window, but 0 source hypotheses generated matching slick drift history.
  - **Honest Attribution:** Attribution views display an explicit domain notice: *"0 candidate vessels identified. No vessel attribution forced."* The UI refuses to manufacture a false vessel ranking for a pipeline spill.
  - **Zero Leakage:** No stale layers or metadata from Case 003 or Case 002 are present.

### 3.2 Case 002 — Bulk Carrier Wakashio (Physical Validation)
- **Scientific Premise:** Well-documented grounding on Pointe d'Esny reef, Mauritius. Used for hydrodynamic and physical drift model validation.
- **API Response:** `datasets_available: { sar: true, slicks: true, ais: false, forward_drift: true, attribution: false }`.
- **Integrity Verification:**
  - Case metadata correctly displays Mauritius grounding coordinates (-20.44°S, 57.75°E).
  - Sentinel-1 SAR analysis displays verified slick detection and coastal ocean current vector field (HYCOM + ERA5).
  - **Distinction of Capabilities:** When user inspects attribution or candidates, the UI clearly displays:
    $$\text{PHYSICAL VALIDATION AVAILABLE} \quad \text{vs.} \quad \text{AIS ATTRIBUTION DATA UNAVAILABLE}$$
    Surfacing a clear explanation that historical multi-vessel terrestrial/satellite AIS feeds are unavailable for this benchmark segment.
  - The UI does not fabricate a synthetic vessel list or false ranking.

### 3.3 Case 003 — M/V Golden Ray (Blind Attribution Validation)
- **Scientific Premise:** Multi-vessel candidate field (25 vessels, 102 hypotheses) in St. Simons Sound, GA where M/V Golden Ray capsized.
- **API Response:** `datasets_available: { sar: true, slicks: true, ais: true, forward_drift: true, attribution: true }`.
- **Integrity Verification:**
  - **API-Provided Ranking:** The FastAPI bridge reads directly from `case_003_golden_ray_causal_vessel_summary.csv` and `case_003_golden_ray_causal_hypothesis_evidence.csv`.
  - **Rank #1 Verification:** Vessel **MMSI `538007762` (`M/V GOLDEN RAY`)** appears as Rank #1 with composite compatibility score **`0.6891`**.
  - **5-Axis Evidence Breakdown:**
    - Drift Consistency: `0.7463`
    - Spatial Compatibility: `0.7115`
    - Temporal Compatibility: `0.8914`
    - Source Plausibility: `0.4678`
    - AIS Track Quality: `0.6000`
  - **Causal Status:** Verified as `AT_RELEASE` with valid spatiotemporal precedence.
  - **No Hardcoded Values:** The frontend renders this dynamically from the TanStack Query response (`useAttributionRanking("case_003_golden_ray")`).

---

## 4. Data Provenance & Lineage Trace

Every data point rendered on the user interface is traced back to its raw scientific pipeline origin:

```
[UI Component]
      ↓ (TanStack Query hook)
[FastAPI REST Endpoint]
      ↓ (backend/main.py resolver)
[Validated Output Artifact]
      ↓ (src/ scientific pipeline)
[Raw Source Data / Case Definition]
```

### Traceability Audit Table

| UI Field / Visualization | API Endpoint | Source Artifact File | Scientific Generating Module |
| :--- | :--- | :--- | :--- |
| **Case Name & Incident Info** | `GET /api/cases/{case_id}` | `data/cases/{case_id}.yaml` | `src/common/case_loader.py` |
| **Incident Coordinates** | `GET /api/cases/{case_id}` | `data/cases/{case_id}.yaml` | `src/common/case_loader.py` |
| **SAR Backscatter & SNR** | `GET /api/cases/{case_id}/satellite/sar` | `data/processed/satellite/{case_id}_s1_preprocessing_stats.json` | `src/satellite/preprocessor.py` |
| **Candidate Slick Polygons** | `GET /api/cases/{case_id}/satellite/slicks` | `data/processed/satellite/{case_id}_candidate_slicks.geojson` | `src/detection/detector.py` |
| **Candidate Vessel List** | `GET /api/cases/{case_id}/ais/vessels` | `data/processed/hypotheses/{case_id}_source_hypotheses_summary.json` | `src/ais/candidate_generator.py` |
| **Vessel Trajectory Tracks** | `GET /api/cases/{case_id}/ais/tracks` | `data/processed/hypotheses/{case_id}_vessel_tracks.geojson` | `src/ais/track_builder.py` |
| **Drift Trajectories (Forward/Back)** | `GET /api/cases/{case_id}/drift/trajectories` | `data/processed/drift/{case_id}_drift_trajectories.geojson` | `src/drift/integrator.py` |
| **Release Hypotheses** | `GET /api/cases/{case_id}/drift/hypotheses` | `data/processed/hypotheses/{case_id}_source_hypotheses_summary.json` | `src/drift/source_reconstructor.py` |
| **Vessel Attribution Ranking** | `GET /api/cases/{case_id}/attribution/ranking` | `data/processed/attribution/{case_id}_causal_vessel_summary.csv` | `src/attribution/engine.py` |
| **5-Axis Evidence Components** | `GET /api/cases/{case_id}/attribution/ranking` | `data/processed/attribution/{case_id}_causal_hypothesis_evidence.csv` | `src/attribution/causal_consistency.py` |
| **Counterfactual Audit** | `GET /api/cases/{case_id}/attribution/ranking` | `data/processed/attribution/{case_id}_causal_hypothesis_evidence.csv` | `src/attribution/counterfactual.py` |
| **Uncertainty & Sensitivity** | `GET /api/cases/{case_id}/attribution/uncertainty` | `data/processed/attribution/{case_id}_uncertainty_summary.json` | `src/attribution/uncertainty.py` |

---

## 5. Scientific Integrity & Hardcoding Audit

An exhaustive code audit was executed across the `frontend/src/` and `backend/` directories to detect any potential hardcoding of scientific answers or case identities:

| Search Target | Occurrences in Production Code | Classification | Status |
| :--- | :--- | :--- | :--- |
| `case_003` | 0 in active logic | Legitimate unit test fixtures and fallback test file | CLEAN |
| `Golden Ray` | 0 in active UI | YAML case config (`data/cases/`) & unit test assertions | CLEAN |
| `9775816` (IMO) | 0 in active logic | YAML case metadata & unit test fixture | CLEAN |
| `538007762` (MMSI) | 0 in active logic | YAML case metadata & unit test fixture | CLEAN |
| `0.6891` (Score) | 0 in active UI | CSV scientific artifact & pipeline test assertion | CLEAN |
| `VALID_PRE_EVENT` | 0 in active UI logic | Legitimate TypeScript enum definition (`schemas.ts`) | CLEAN |

**Verdict:** Zero hardcoded scientific results exist in the user interface or API bridge. All rankings, scores, and hypothesis identities are computed by the scientific pipeline and delivered dynamically.

---

## 6. Case Switching & State Cleanliness

A stress test of sequential case switching was conducted:
$$\text{Case 001} \longrightarrow \text{Case 002} \longrightarrow \text{Case 003} \longrightarrow \text{Case 001}$$

### Observations
1. **Zustand State Reset:** Upon changing `activeCaseId`, `selectedMmsi`, `selectedHypothesisId`, and `activeSlickId` are immediately cleared.
2. **TanStack Query Cache Segregation:** Query keys are keyed by `['cases', activeCaseId, dataset]`, preventing stale data collision.
3. **Map Re-Centering:** The camera viewport smoothly animates and re-centers to the new case's bounding box and incident coordinates.
4. **deck.gl Layer Flushing:** Old vector layers (tracks, particles, slicks) unmount cleanly without visual artifacts or memory leaks.

---

## 7. Routing & Deep-Linking Verification

Direct URL routing was tested and verified across both modern path routing (`/cases/{case_id}/{view}`) and hash navigation (`#case={case_id}&view={view}`):

| Route Tested | Expected View | Observed Result | Status |
| :--- | :--- | :--- | :--- |
| `/cases/case_003_golden_ray/overview` | Case 003 Map & Inspector | Loaded correctly, viewport centered on St. Simons Sound | PASS |
| `/cases/case_003_golden_ray/attribution` | Case 003 Candidate Ranking Table | Table rendered with 25 candidates, Golden Ray #1 | PASS |
| `/cases/case_003_golden_ray/evidence` | 5-Axis Evidence Modal | Modal displayed radar chart with drift=0.75, spatial=0.71 | PASS |
| `/cases/case_003_golden_ray/uncertainty` | Uncertainty & Sensitivity Panel | Uncertainty bands and Monte Carlo distribution rendered | PASS |
| `/cases/case_003_golden_ray/audit` | Chain-of-Custody Provenance | Cryptographic hash & pipeline run logs displayed | PASS |
| `/cases/case_002_wakashio/overview` | Case 002 Map & Ocean Layers | Mauritius coastline, slick, and current vectors loaded | PASS |
| `/cases/case_001_pipeline/overview` | Case 001 Pipeline Incident | Gulf of Mexico viewport and single slick polygon loaded | PASS |
| `/cases/invalid_case_id/overview` | Error Boundary / 404 View | Clean fallback banner: *"Error Loading Case: Not Found"* | PASS |
| **Page Refresh on Route** | Preserved active case & subview | URL retained, state cleanly re-hydrated from API | PASS |

---

## 8. Failure Mode & Resilience Testing

The system was evaluated against simulated failure modes:
- **API Server Down / Connection Refused:** Frontend displays non-intrusive banner indicating backend connection failure with automatic TanStack Query retry exponential backoff.
- **Invalid Case ID:** FastAPI returns standard `404 Not Found` with structured JSON (`{"error": "CASE_NOT_FOUND", ...}`). The UI traps this error and renders an informative error recovery screen.
- **Unavailable Scientific Layers (Case 002 AIS):** API returns `404 DATASET_NOT_AVAILABLE`. Frontend gracefully intercepts and presents a domain notice explaining the limitation without breaking the map or application flow.
- **Path Traversal Attacks (`/cases/../../etc/passwd`):** FastAPI `_safe_resolve_case_id` traps `..` and returns `400 Bad Request` instantly.

---

## 9. Verification & Build Results

### Automated Backend Tests
```bash
python -m pytest tests/
```
```
============================= test session starts =============================
platform win32 -- Python 3.14.0, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\rkchi\OneDrive\Desktop\Oil_spill
collected 179 items

tests\test_ais_candidate_generation.py ............                      [  6%]
tests\test_api_bridge.py ................                                [ 15%]
tests\test_attribution_engine.py ...............                         [ 24%]
tests\test_case_003_acquisition.py ......                                [ 27%]
tests\test_case_loading.py .                                             [ 27%]
tests\test_case_onboarding.py ..........                                 [ 33%]
tests\test_case_validation.py .                                          [ 34%]
tests\test_causal_consistency.py ..........                              [ 39%]
tests\test_config.py ..                                                  [ 40%]
tests\test_detection.py ........                                         [ 45%]
tests\test_forward_simulation.py ............                            [ 51%]
tests\test_geo.py ......                                                 [ 55%]
tests\test_health_check.py .                                             [ 55%]
tests\test_paths.py ....                                                 [ 58%]
tests\test_sar_preprocessing.py .........                                [ 63%]
tests\test_source_hypothesis_generation.py ............                  [ 69%]
tests\test_source_reconstruction.py .......                              [ 73%]
tests\test_spill_comparison.py ............                              [ 80%]
tests\test_time_utils.py .....                                           [ 83%]
tests\test_uncertainty_analysis.py ...............                       [ 91%]
tests\test_validation_framework.py ...............                       [100%]

====================== 179 passed, 2 warnings in 26.42s =======================
```

### Production Frontend Build
```bash
npm run build
```
```
> frontend@0.0.0 build
> tsc -b && vite build

vite v8.3.0 building client environment for production...
transforming...
✓ 2915 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                                         0.72 kB │ gzip:   0.37 kB
dist/assets/index-BeBZLIN1.css                         86.97 kB │ gzip:  12.16 kB
dist/assets/webgl-D1kLyPkI.js                          18.84 kB │ gzip:   6.61 kB
dist/assets/get-attribute-from-layouts-Dd2gixpo.js     19.20 kB │ gzip:   5.54 kB
dist/assets/array-utils-flat-BL8Cekj1.js               29.53 kB │ gzip:   9.53 kB
dist/assets/expression-CLhvvDPZ.js                     96.58 kB │ gzip:  29.17 kB
dist/assets/index-Mrfwrqfl.js                       2,143.45 kB │ gzip: 588.47 kB

✓ built in 808ms
```

---

## 10. Conclusion & Acceptance Sign-off

The SIH26143 Marine Oil Spill Attribution Decision-Support System has satisfied all Phase 16 Full System Integration and Acceptance criteria:
1. **Front-to-back integration** operates smoothly without mock scientific generators.
2. **Scientific baseline is intact** with 179/179 automated tests passing and zero formula tampering.
3. **Scientific honesty is upheld**: Case 001 refrains from forcing vessel attributions, Case 002 clearly acknowledges AIS data unavailability, and Case 003 demonstrates data-driven causal attribution placing M/V Golden Ray at Rank #1.
4. **State and routing transitions** are robust, resilient, and persistent.

**Phase 16 is hereby certified as COMPLETE and ACCEPTED.**
