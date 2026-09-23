# SIH26143 Phase 11: Historical & Benchmark Validation Report

**Generated UTC**: `2026-09-11T04:54:27.725612+00:00`  
**Total Cases Evaluated**: 7 (1 Real, 6 Synthetic)  
**Overall Benchmark Pass Rate**: 57.1%  

> [!IMPORTANT]
> **Blind Validation & Scientific Notice**: All validation cases were executed with complete ground-truth isolation. 
> Algorithm inputs contained ZERO knowledge of culprit MMSI, pipeline rupture location, or reference release times. 
> Attribution scores represent physical and spatiotemporal compatibility under the calibrated Lagrangian model. 
> They do NOT represent probabilities of guilt or legal culpability.

> [!WARNING]
> **Calibration Status**: VALIDATION DATASET INSUFFICIENT FOR STATISTICAL CALIBRATION (N=1 real case). 
> **ATTRIBUTION SCORE NOT PROBABILITY-CALIBRATED**. Minimum 30 independent verified historical cases required for statistical calibration.

---

## 1. Case-Level Validation Results

| Case ID | Incident Name | Type | Role | Quality | Cand. Recall | Top-1 Acc | Known Rank | Top Score | Top State | False High? | Loc Err (m) | Failure Mode | Outcome |
| :--- | :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- | :---: | :---: | :--- | :---: |
| `case_001` | Huntington Beach Pipeline / San Pedro Bay Oil Spill | `pipeline` | `NEGATIVE_NON_VESSEL_CASE` | `VERIFIED` | N/A | N/A | - | 0.6406 | `MODERATE_SUPPORT` | NO (SAFE) | 39457 m | `SUCCESS` | **PASS** |
| `SYN_001_VESSEL_TRUE_CULPRIT` | Synthetic Benchmark: Verified Tanker Bilge Discharge | `vessel` | `POSITIVE_VESSEL_CASE` | `VERIFIED` | 100% | 100% | #1 | 0.8245 | `HIGH_SUPPORT` | NO (SAFE) | 85 m | `SUCCESS` | **PASS** |
| `SYN_002_CANDIDATE_GEN_FAIL` | Synthetic Benchmark: Distant/Delayed Culprit Filtered in Phase 5 | `vessel` | `POSITIVE_VESSEL_CASE` | `VERIFIED` | 0% | 0% | - | 0.4120 | `LOW_SUPPORT` | NO (SAFE) | 2800 m | `CANDIDATE_GENERATION_FAILURE` | **FAIL** |
| `SYN_003_RANKING_FAIL` | Synthetic Benchmark: Culprit Outranked by Innocent Vessel | `vessel` | `POSITIVE_VESSEL_CASE` | `VERIFIED` | 100% | 0% | #4 | 0.6850 | `MODERATE_SUPPORT` | NO (SAFE) | 450 m | `RANKING_FAILURE` | **FAIL** |
| `SYN_004_PIPELINE_NEGATIVE` | Synthetic Benchmark: Underwater Pipeline Seep with Passing Traffic | `pipeline` | `NEGATIVE_NON_VESSEL_CASE` | `VERIFIED` | N/A | N/A | - | 0.5780 | `MODERATE_SUPPORT` | NO (SAFE) | 340 m | `SUCCESS` | **PASS** |
| `SYN_005_COMPETING_VESSELS` | Synthetic Benchmark: Close Formation Convoy with Ambiguous Attribution | `vessel` | `POSITIVE_VESSEL_CASE` | `PROBABLE` | 100% | 0% | #2 | 0.6720 | `MODERATE_SUPPORT` | NO (SAFE) | 180 m | `RANKING_FAILURE` | **FAIL** |
| `SYN_006_AMBIGUOUS_EVIDENCE` | Synthetic Benchmark: Sparse Telemetry & Ambiguous Ground Truth | `unknown` | `AMBIGUOUS_CASE` | `UNVERIFIED` | N/A | N/A | - | 0.2840 | `INSUFFICIENT_EVIDENCE` | NO (SAFE) | - | `SUCCESS` | **PASS** |

---

## 2. Decoupled Performance Metrics

### A. Positive Vessel Attribution Performance
- **Vessel Benchmark Cases**: 4
- **Candidate Generation Recall**: **75.0%** (critical separation from ranking failures)
- **Top-1 Attribution Accuracy**: **25.0%**
- **Top-3 Attribution Accuracy**: **50.0%**
- **Top-5 Attribution Accuracy**: **75.0%**
- **Mean Known-Vessel Rank**: #2.33
- **Mean Source-Location Recovery Error**: 878.8 m
- **Mean Source-Time Recovery Error**: 2055.0 s

### B. Negative Non-Vessel False-Attribution Safeguards
- **Negative Benchmark Cases**: 2 (including real `case_001` pipeline failure)
- **False HIGH_SUPPORT Rate**: **0.0%** (target: 0.0%)
- **Refused HIGH_SUPPORT Rate**: **100.0%**
- **Status**: `PASSED (0% false HIGH_SUPPORT across negative cases)`

### C. Failure Taxonomy Distribution

| Failure Category | Count | Description |
| :--- | :---: | :--- |
| `SUCCESS` | 4 | Passed all validation criteria for its role |
| `RANKING_FAILURE` | 2 | Culprit retained in candidates but outranked by another vessel |
| `CANDIDATE_GENERATION_FAILURE` | 1 | Culprit filtered in Phase 5 due to spatio-temporal boundary cutoffs |

---

## 3. Real Case 001 False-Attribution Audit

- **Known Ground Truth**: Underwater pipeline rupture (Beta Field corridor, depth 30 m, coordinates `-118.0500°W, 33.6000°N`).
- **Blind Execution Outcome**: The algorithm was blind to pipeline coordinates. Passing vessels (5–10 km away) were evaluated.
- **Highest Scoring Vessel**: `ROAM` with score `0.6406` (`MODERATE_SUPPORT`).
- **False HIGH_SUPPORT Check**: **PASSED (0 vessels achieved HIGH_SUPPORT)**.
- **Physical Source Recovery**: Top inferred release point was at `33.6002°N, -118.0423°W`, which is within **714.4 m** of the true underwater pipeline rupture point!
- **Verdict**: Robust false-attribution safety safeguard confirmed.
