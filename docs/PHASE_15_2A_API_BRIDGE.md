# Phase 15.2A — Read-Only FastAPI Data Bridge Specification & Verification

**Project:** SIH26143 — Marine Oil Spill Attribution Decision-Support System  
**Phase:** 15.2A (Read-Only FastAPI Data Bridge)  
**Status:** Complete & Verified  
**Baseline Test Count:** 174/174 tests passing (163 scientific tests + 11 API bridge tests)  

---

## 1. Executive Summary

Phase 15.2A establishes a high-performance, strictly **read-only** FastAPI bridge that exposes verified scientific artifacts (SAR preprocessed metrics, segmented slick geometries, candidate AIS vessels, causal attribution rankings, and Monte Carlo uncertainty analyses) to the frontend client.

In accordance with strict system rules:
- **Zero Scientific Modifications:** The scientific core in `src/` is frozen and completely untouched.
- **No Scientific Recomputation:** All endpoints import or stream existing artifacts from `data/cases/` and `data/processed/`.
- **Dynamic Case Discovery:** Case catalogs are derived dynamically from `data/cases/*.yaml` without hardcoding.
- **Path Traversal Security:** Inputs are strictly sanitized to prevent directory traversal outside case manifests.
- **Restricted CORS:** Local Vite development server origins (`http://localhost:5173`, `http://127.0.0.1:5173`, `http://localhost:4173`, `http://127.0.0.1:4173`) are explicitly permitted.
- **Structured Error Reporting:** The API provides unambiguous distinctions between nonexistent cases (`CASE_NOT_FOUND`), missing datasets (`DATASET_NOT_AVAILABLE`), and invalid parameters (`INVALID_CASE_ID`).

---

## 2. API Architecture & Source Artifact Mapping

The API layer is encapsulated in `backend/`:
- `backend/main.py`: FastAPI application, endpoint routers, path security, and artifact serialization.
- `backend/schemas.py`: Pydantic data models preserving exact backend fields without lossy conversion.

### Endpoint Catalog & Source Artifacts

| HTTP Method | Endpoint Path | Source Artifact | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/health` | Memory / Runtime | Service liveness and version check. |
| `GET` | `/api/cases` | `data/cases/*.yaml` + filesystem checks | Dynamically discovers all registered cases and calculates boolean dataset availability for every scientific layer. |
| `GET` | `/api/cases/{case_id}` | `data/cases/{case_id}.yaml` | Detailed case metadata, spatial bounds (EPSG:4326), temporal windows, observation metadata, and dataset availability. |
| `GET` | `/api/cases/{case_id}/sar/stats` | `data/processed/satellite/{case_id}_s1_preprocessing_stats.json` | Calibrated Sentinel-1 SAR radiometry, dimension parameters, and valid pixel counts. |
| `GET` | `/api/cases/{case_id}/slicks` | `data/processed/satellite/{case_id}_candidate_slicks.geojson` | Verified candidate slick geometries as a standard GeoJSON `FeatureCollection`. |
| `GET` | `/api/cases/{case_id}/ais/vessels` | `data/processed/hypotheses/{case_id}_source_hypotheses_summary.json` | Candidate vessels discovered within the 4D spatiotemporal drift cone, hypothesis counts, and geodesic distance ranges. |
| `GET` | `/api/cases/{case_id}/attribution/ranking` | `data/processed/attribution/{case_id}_causal_vessel_summary.csv` or `{case_id}_vessel_summary.json` + `_causal_hypothesis_evidence.csv` / `_hypothesis_evidence.json` | Exact attribution ranking order, compatibility scores, support classification, causal precedence status, and 5-axis evidence components. |
| `GET` | `/api/cases/{case_id}/attribution/uncertainty` | `data/processed/attribution/{case_id}_uncertainty_summary.json` | Monte Carlo ensemble parameters, score distributions, rank stability statistics, and uncalibrated probability guardrail notice. |

---

## 3. Data Schemas & Payload Examples

### 3.1 Case Summary (`GET /api/cases`)
```json
[
  {
    "case_id": "case_001",
    "name": "Huntington Beach Pipeline / San Pedro Bay Oil Spill",
    "incident_type": "PIPELINE_OR_PLATFORM_STRUCTURAL_FAILURE",
    "location_name": "San Pedro Bay, offshore Huntington Beach, California, USA",
    "location": {
      "latitude": 33.565,
      "longitude": -118.095,
      "description": "Reported pipeline breach location (Beta field pipeline)"
    },
    "event_time_utc": "2021-10-01T21:00:00Z",
    "observation_time_utc": "2021-10-02T13:50:00Z",
    "validation_role": "negative_control",
    "ground_truth_quality": "HIGH_CONFIDENCE",
    "datasets_available": {
      "sar": true,
      "slicks": true,
      "ais": true,
      "backward_drift": true,
      "forward_drift": true,
      "attribution": true,
      "uncertainty": true
    }
  }
]
```

### 3.2 Case Detail (`GET /api/cases/{case_id}`)
```json
{
  "case_id": "case_003_golden_ray",
  "name": "M/V Golden Ray Capsizing & Oil Spill (2019)",
  "location_name": "St. Simons Sound, Brunswick, Georgia, USA",
  "location": {
    "latitude": 31.1275,
    "longitude": -81.4031,
    "description": "Capsizing location in St. Simons Sound navigation channel"
  },
  "bounding_box": {
    "west": -81.55,
    "south": 30.98,
    "east": -81.3,
    "north": 31.25
  },
  "event": {
    "incident_type": "VESSEL_CAPSIZING_AND_DISCHARGE",
    "estimated_start_utc": "2019-09-08T05:46:00Z",
    "estimated_end_utc": "2019-09-08T06:15:00Z",
    "search_start_utc": "2019-09-07T12:00:00Z",
    "search_end_utc": "2019-09-08T11:25:31Z"
  },
  "observation": {
    "platform": "Sentinel-1A",
    "instrument": "C-SAR",
    "sensor_mode": "IW",
    "scene_id": "S1A_IW_GRDH_1SDV_20190908T112519_20190908T112544_028929_0347A9",
    "timestamp_utc": "2019-09-08T11:25:31.797740Z",
    "orbit_direction": "DESCENDING"
  },
  "validation_role": "blind_attribution_benchmark",
  "ground_truth_quality": "HIGH_CONFIDENCE",
  "ground_truth_source": "NTSB Marine Accident Report MAR-21-01 & USCG Investigation",
  "datasets": {
    "sar": false,
    "slicks": false,
    "ais": true,
    "backward_drift": false,
    "forward_drift": true,
    "attribution": true,
    "uncertainty": true
  }
}
```

### 3.3 Attribution Ranking (`GET /api/cases/{case_id}/attribution/ranking`)
Preserves the exact backend ranking order, causal precedence status, and 5-axis evidence components:
```json
[
  {
    "mmsi": 538007762,
    "vessel_name": "UNKNOWN",
    "vessel_type": "UNKNOWN",
    "vessel_rank": 1,
    "best_evidence_score": 0.6891,
    "mean_evidence_score": 0.5852,
    "vessel_evidence_state": "MODERATE_SUPPORT",
    "causal_precedence_status": "AT_RELEASE",
    "best_hypothesis_id": "4DH_0065",
    "best_associated_slick": "CS_0035",
    "compatible_hypotheses_count": 14,
    "evidence_components": {
      "drift_consistency": 0.7463,
      "spatial_compatibility": 0.7115,
      "source_plausibility": 0.4678,
      "temporal_compatibility": 0.8914,
      "ais_track_quality": 0.6
    },
    "best_hypothesis_explanation": "UNKNOWN: Physical drift is moderate (0.75), spatial compatibility is moderate (0.71), source plausibility is weak (0.47), temporal alignment is strong (0.89), and AIS track quality is moderate (0.60)."
  },
  {
    "mmsi": 338102861,
    "vessel_name": "RECOVERY",
    "vessel_type": "90.0",
    "vessel_rank": 2,
    "best_evidence_score": 0.6695,
    "mean_evidence_score": 0.5783,
    "vessel_evidence_state": "MODERATE_SUPPORT",
    "causal_precedence_status": "AT_RELEASE",
    "best_hypothesis_id": "4DH_0025",
    "best_associated_slick": "CS_0035",
    "compatible_hypotheses_count": 8,
    "evidence_components": {
      "drift_consistency": 0.7619,
      "spatial_compatibility": 0.5854,
      "source_plausibility": 0.4967,
      "temporal_compatibility": 0.9018,
      "ais_track_quality": 0.6
    },
    "best_hypothesis_explanation": "RECOVERY: Physical drift is strong (0.76), spatial compatibility is moderate (0.59), source plausibility is weak (0.50), temporal alignment is strong (0.90), and AIS track quality is moderate (0.60)."
  }
]
```

### 3.4 Monte Carlo Uncertainty Analysis (`GET /api/cases/{case_id}/attribution/uncertainty`)
```json
{
  "case_id": "case_001",
  "timestamp_utc": "2026-09-11T04:36:03.187313+00:00",
  "ensemble_size": 50,
  "random_seed": 42,
  "calibration_audit": {
    "is_probability_calibrated": false,
    "calibration_status": "NOT_CALIBRATED_ORDINAL_SCORING_ONLY",
    "available_cases_count": 1,
    "verified_culprit_cases_count": 0,
    "mandatory_scientific_notice": "Attribution scores and stability percentages represent ordinal rankings, not calibrated posterior probabilities. Do not interpret as % probability of guilt."
  },
  "rank_stability_top_hypotheses": [
    {
      "hypothesis_id": "4DH_0006",
      "vessel_name": "PACIFIC TITAN",
      "top_1_frequency": 0.38,
      "top_3_frequency": 0.84,
      "mean_rank": 2.12,
      "std_rank": 1.18,
      "mean_score": 0.5218,
      "rank_stability_category": "MODERATE_STABILITY"
    }
  ]
}
```

---

## 4. Error Handling Matrix

All error responses return structured, machine-readable JSON payloads:

```json
{
  "detail": {
    "error": "ERROR_CODE",
    "message": "Descriptive human-readable explanation."
  }
}
```

| HTTP Status | Error Code | Trigger Condition |
| :--- | :--- | :--- |
| `400 Bad Request` | `INVALID_CASE_ID` | Path traversal detected (e.g., `..`, `/`, `\`). |
| `404 Not Found` | `CASE_NOT_FOUND` | No matching case YAML configuration exists in `data/cases/`. |
| `404 Not Found` | `DATASET_NOT_AVAILABLE` | The case exists, but the requested scientific artifact (e.g. SAR raster stats, slick GeoJSON, or AIS attribution) has not been computed or is unavailable. |

For example, querying `GET /api/cases/case_002_wakashio/slicks` yields:
```json
{
  "detail": {
    "error": "DATASET_NOT_AVAILABLE",
    "message": "Candidate slick GeoJSON unavailable for case 'case_002_wakashio'."
  }
}
```

---

## 5. Security & Path Traversal Prevention

The API strictly prohibits arbitrary filesystem access:
```python
def _safe_resolve_case_id(case_id: str) -> Path:
    if ".." in case_id or "/" in case_id or "\\" in case_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_CASE_ID", "message": "Path traversal detected in case_id."},
        )
    ...
```
Endpoints only resolve files from predefined, project-rooted directories (`data/cases/`, `data/processed/satellite/`, `data/processed/hypotheses/`, and `data/processed/attribution/`).

---

## 6. How to Run the API Bridge

### Starting the Server Locally
To start the read-only FastAPI server on the standard backend port:
```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
Interactive OpenAPI documentation is automatically available at:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

### Executing Automated Tests
Run the comprehensive test suite verifying the API bridge alongside all frozen scientific modules:
```bash
python -m pytest tests/ -v
```
To run only the API bridge tests:
```bash
python -m pytest tests/test_api_bridge.py -v
```

---

## 7. Confirmation of Scientific Immutability

The following core scientific modules were verified to have **ZERO changes** during Phase 15.2A:
- `src/attribution/` (`attribution_engine.py`, `hypothesis_generator.py`, `uncertainty_analyzer.py`, `forward_simulator.py`, etc.)
- `src/drift/` (`lagrangian_tracker.py`, `environmental_interpolator.py`, `source_reconstruction.py`, etc.)
- `src/detection/` (`sar_processor.py`, `slick_detector.py`, etc.)
- `src/satellite/` (`sentinel1_calibration.py`, `metadata_parser.py`, etc.)
- `src/ais/` (`candidate_generator.py`, `ais_loader.py`, etc.)

All 163 original baseline scientific tests continue to pass with 100% fidelity.
