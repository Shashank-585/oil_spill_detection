# Phase 16 Reconciliation Report: Case 001 Identity & Case 003 Hypothesis Baseline

**Project:** SIH26143 — Marine Oil Spill Attribution Decision-Support System  
**Date:** September 12, 2026  
**Status:** RECONCILED — NO CODE OR ARTIFACT CHANGES

---

## 1. Executive Summary

This reconciliation report formally resolves two documentation discrepancies identified during the Phase 16 review:
1. The real identity and geographic coordinates of **Case 001**.
2. The exact baseline count of hypotheses, simulations, and candidate vessels in **Case 003**.

All determinations below were verified directly from raw and processed artifacts, case YAML definitions, and automated test fixtures. **No code or data artifacts were altered.**

---

## 2. Case 001 Identity Reconciliation

| Attribute | Erroneous Draft Report Text | Actual Repository Artifact ([data/cases/case_001.yaml](file:///c:/Users/rkchi/OneDrive/Desktop/Oil_spill/data/cases/case_001.yaml)) | Verification Status |
| :--- | :--- | :--- | :--- |
| **Case ID** | `case_001` | `case_001` | Confirmed |
| **Case Name** | Gulf of Mexico Pipeline | **Huntington Beach Pipeline / San Pedro Bay Oil Spill** | **Report Erroneous** |
| **Location Name** | Gulf of Mexico | **San Pedro Bay / Huntington Beach, California, USA** | **Report Erroneous** |
| **Incident Point** | `28.45° N, -89.85° W` | **`33.60° N, -118.05° W`** | **Report Erroneous** |
| **AOI Bounding Box**| Not specified | West: `-118.40`, South: `33.40`, East: `-117.85`, North: `33.80` | Confirmed |
| **Incident Type** | Pipeline leak | **Pipeline rupture following suspected vessel anchor drag** | Confirmed |
| **Observation Time**| 2020-04-12 | **2021-10-02T01:58:36Z** (Sentinel-1A IW GRDH) | **Report Erroneous** |

### Findings:
1. **Case Registry Status:** **The case registry was NEVER changed.** `data/cases/case_001.yaml` has always specified the San Pedro Bay / Huntington Beach pipeline incident (33.60° N, -118.05° W), as validated by `tests/test_case_loading.py` and `tests/test_validation_framework.py`.
2. **Report Error:** The Phase 16 Markdown documentation contained an errant copy-paste draft statement referencing "Gulf of Mexico (28.45° N, -89.85° W)". The actual system code and API bridge correctly serve Huntington Beach.

---

## 3. Case 003 Hypothesis Count Reconciliation

### Exact Pipeline Audit Table:

| Pipeline Level / Entity | Exact Count | Backing Artifact Filename |
| :--- | :--- | :--- |
| **Lagrangian Source Hypotheses** | **42** | `data/validation/case_003_golden_ray/CASE_003_BLIND_ATTRIBUTION_REPORT.md` ($6\text{ slicks} \times 7\text{ backtrack release ages} = 42\text{ source points}$) |
| **Unique AIS Corridor Vessels** | **49** | NOAA MarineCadastre Zone 17 AIS filter |
| **Usable Tracks ($\ge 3$ pings)** | **48** | `data/processed/hypotheses/case_003_golden_ray_vessel_tracks.geojson` |
| **Retained Candidate Vessels** | **25** | `data/processed/hypotheses/case_003_golden_ray_source_hypotheses_summary.json` |
| **4D Spatiotemporal Release Hypotheses** | **256** | `data/processed/hypotheses/case_003_golden_ray_source_hypotheses_4d.csv` (`total_hypotheses: 256`) |
| **Counterfactual Forward Simulations** | **256** | `data/processed/attribution/case_003_golden_ray_forward_simulations.csv` (256 completed simulations) |
| **Predicted-vs-Observed Comparisons** | **256** | `data/processed/attribution/case_003_golden_ray_spill_comparisons.csv` (256 comparison records) |
| **Hypothesis Evidence Evaluations** | **256** | `data/processed/attribution/case_003_golden_ray_causal_hypothesis_evidence.csv` (256 evaluated tuples) |
| **Vessel Attribution Summaries** | **25** | `data/processed/attribution/case_003_golden_ray_causal_vessel_summary.csv` (25 unique ranked vessels) |

### API Endpoint Exposure Audit:
- **`GET /api/cases/{case_id}/ais/vessels`**: Exposes **25** candidate vessels.
- **`GET /api/cases/{case_id}/attribution/ranking`**: Exposes **25** ranked candidate vessels (Golden Ray MMSI `538007762` at Rank #1).
- **`GET /api/cases/{case_id}/hypotheses`**: Exposes a GeoJSON FeatureCollection of **512 features**:
  - **256 Points**: `hypothesized_release_location`
  - **256 LineStrings**: `vessel_to_source_vector`
- **`GET /api/cases/{case_id}/attribution/spill-comparisons`**: Exposes **256** comparison rows.

### Reconciliation of 102 vs. 256:
- The actual validated scientific baseline across the entire pipeline is unequivocally **256 vessel/4D hypotheses** across **25 candidate vessels**.
- A repository-wide search confirmed that **102 was an errant draft typographical misstatement in the Phase 16 acceptance report text**. No file, JSON summary, or CSV artifact in the pipeline has 102 hypotheses.
