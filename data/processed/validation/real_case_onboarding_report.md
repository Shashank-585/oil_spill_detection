# Real Historical Case Expansion and Onboarding Report

## 1. Executive Summary & Scientific Status

> [!IMPORTANT]
> **CURRENT STATUS**: `BLOCKED_PENDING_POSITIVE_REAL_CASE_DATA`
> 
> - **Real Data Availability**: Currently, exactly **ONE** real-world incident (`case_001`, Huntington Beach) is locally provisioned in the repository.
> - **Non-Vessel Negative Role**: `case_001` is a verified underwater pipeline rupture. It functions rigorously as a **negative safety test** (confirming the engine refuses `HIGH_SUPPORT` to innocent vessels), but cannot validate true culprit identification.
> - **Synthetic Segregation**: The 6 synthetic benchmark cases (`SYN_001` through `SYN_006`) verify software components and failure modes, but **must never be counted toward empirical real-world accuracy claims**.
> - **Positive Validation Requirement**: At least one independent, verified vessel-caused historical incident (e.g. `MV Wakashio`) must be onboarded before claiming positive attribution recall.

---

## 2. Standardized Real-Case Onboarding Architecture

Phase 12 establishes a standardized 8-step ingestion workflow that reuses the proven `CaseConfig` architecture from Case 001 without creating duplicate data pipelines:

```
  1. Case YAML Configuration    --> data/cases/<case_id>.yaml (bounding box, dates, files)
  2. Satellite Registration     --> Sentinel-1 C-SAR GRD scene, acquisition time, orbit, LUT
  3. Environmental Registration --> HYCOM 3D ocean currents (NetCDF) + ECMWF ERA5 winds (CSV)
  4. AIS Data Registration      --> Filtered spatiotemporal trajectories (CSV/Parquet)
  5. Ground Truth Registration  --> Isolated block (Source type, Tier A-D quality, culprit MMSI)
  6. Data Feasibility Audit     --> Automated file presence, pixel valid mask, metadata checks
  7. Spatiotemporal Integrity   --> AOI validity, geodesic area, chronological timestamp order
  8. Eligibility Marking        --> Assign ELIGIBLE, PARTIALLY_ELIGIBLE, or INELIGIBLE
```

---

## 3. Ground-Truth Quality Tiers (A–D)

| Tier | Name | Description | Eligible for Primary Attribution? |
| :---: | :--- | :--- | :---: |
| **A** | **Strong Ground Truth** | Official statutory accident investigation report (USCG, NTSB, MAIB, BEA Mer, IMO) with verified culprit vessel identity, exact collision/grounding coordinates, and sub-hour timeline. | **YES** |
| **B** | **Credible Ground Truth** | Strong operational consensus or eyewitness confirmation; minor uncertainty in exact slick release duration or salvage drift trajectory. | **YES** |
| **C** | **Weak / Indirect Ground Truth** | Preliminary news or unverified eyewitness sightings; significant temporal or spatial ambiguity. | **Exploratory Only** |
| **D** | **Unsuitable** | Lacks verified culprit or source location; inland/freshwater settings incompatible with marine radar. | **NO (Excluded)** |

---

## 4. Prioritized Candidate Positive Cases for Ingestion

1. **`case_002_wakashio` (MV Wakashio Grounding, Mauritius, 2020) — Priority 1**:
   - Known culprit bulk carrier WAKASHIO (MMSI 356508000). Official Panama Maritime Authority investigation report.
   - Copernicus Sentinel-1A scene `S1A_IW_GRDH_1SDV_20200806T014312` captures bunker slick spreading into lagoon.
2. **`case_004_os35` (MV OS 35 Collision & Grounding, Gibraltar, 2022) — Priority 2**:
   - Known culprit bulk carrier OS 35 (MMSI 572396000). Official Gibraltar Port Authority investigation.
   - Dense Mediterranean vessel traffic presents the ideal real-world stress test for AIS candidate filtering recall.
3. **`case_003_sanchi` (MV Sanchi Tanker Collision, East China Sea, 2018) — Priority 3**:
   - Known culprit tanker SANCHI (MMSI 477156900). Joint official investigation submitted to IMO.

---

## 5. Non-Calibration & Legal Integrity Declaration

> [!CAUTION]
> **Attribution Evidence Scores are NOT Probabilities**.
> Because the repository currently contains only 1 real incident ($N=1 < 30$), training logistic regression or Platt scaling produces extreme overfitting and false certainty. Attribution scores evaluate physical consistency under the calibrated Lagrangian model and must never be represented in legal or regulatory forums as mathematical probabilities of guilt.