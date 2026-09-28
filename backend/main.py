"""
backend/main.py

SIH26143 — Marine Oil Spill Attribution Decision-Support System
Read-Only FastAPI Data Bridge (Phase 15.2A)

Exposes validated scientific artifacts (SAR metrics, slick geometries,
AIS candidates, attribution rankings, and uncertainty metrics) without
modifying or computing scientific results.
"""

from pathlib import Path
from typing import List, Optional
import json

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from backend.schemas import (
    CaseDetail,
    CaseSummary,
    DatasetsAvailable,
    ErrorResponse,
    EvidenceBreakdown,
    EventInfo,
    LimitingFactor,
    LocationInfo,
    ObservationInfo,
    SarRasterInfo,
    SlickFeatureCollection,
    UncertaintySummary,
    UnderlyingMetrics,
    VesselAttributionItem,
    VesselCandidateItem,
    InvestigationDossier,
    ExecutiveQAItem,
    Section1CaseIdentification,
    Section2ExecutiveSummary,
    Section3SatelliteObservation,
    Section4DetectedSlick,
    Section5EnvironmentalConditions,
    Section6SourceReconstruction,
    Section7AisCoverage,
    Section8CandidateVessels,
    Section9Hypotheses4D,
    Section10CounterfactualSimulation,
    Section11EvidenceRanking,
    Section12CausalConsistency,
    Section13Uncertainty,
    Section14DataLimitations,
    Section15Conclusion,
    Section16Provenance,
)
from src.common.paths import (
    ATTRIBUTION_PROCESSED_DIR,
    CASES_DIR,
    HYPOTHESES_PROCESSED_DIR,
    PROJECT_ROOT,
    SATELLITE_PROCESSED_DIR,
    resolve_path,
)
from src.common.case_loader import load_case_config

app = FastAPI(
    title="SIH26143 Marine Oil Spill Attribution API",
    description="Read-only data bridge delivering verified scientific artifacts to the investigation frontend.",
    version="1.0.0",
)

# CORS: Allow local Vite development servers strictly
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)


def _safe_resolve_case_id(case_id: str) -> Path:
    """
    Validate case_id against path traversal and verify case YAML existence.
    Raises HTTPException 400 or 404 on failure.
    """
    if ".." in case_id or "/" in case_id or "\\" in case_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_CASE_ID", "message": "Path traversal detected in case_id."},
        )
    
    cases_dir = resolve_path(CASES_DIR)
    case_path = cases_dir / f"{case_id}.yaml"
    if not case_path.is_file():
        case_path = cases_dir / f"{case_id}.yml"
        if not case_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "CASE_NOT_FOUND", "message": f"No registered case with id '{case_id}'."},
            )
    return case_path


def _load_case_yaml(case_id: str) -> dict:
    cases_dir = resolve_path(CASES_DIR)
    case_path = cases_dir / f"{case_id}.yaml"
    if not case_path.is_file():
        case_path = cases_dir / f"{case_id}.yml"
    if case_path.is_file():
        try:
            cfg = load_case_config(case_path)
            return cfg.raw_data or {}
        except Exception:
            return {}
    return {}



def _get_dataset_availability(case_id: str) -> DatasetsAvailable:
    """Determine actual physical file existence for all scientific layers of a case."""
    sat_dir = resolve_path(SATELLITE_PROCESSED_DIR)
    hyp_dir = resolve_path(HYPOTHESES_PROCESSED_DIR)
    attr_dir = resolve_path(ATTRIBUTION_PROCESSED_DIR)

    sar_stats_file = sat_dir / f"{case_id}_s1_preprocessing_stats.json"
    slicks_file = sat_dir / f"{case_id}_candidate_slicks.geojson"
    ais_file = hyp_dir / f"{case_id}_source_hypotheses_summary.json"
    
    # Check attribution
    attr_file = attr_dir / f"{case_id}_vessel_summary.json"
    if not attr_file.is_file():
        attr_file = attr_dir / f"{case_id}_causal_vessel_summary.csv"
        
    uncertainty_file = attr_dir / f"{case_id}_uncertainty_summary.json"

    return DatasetsAvailable(
        sar=sar_stats_file.is_file(),
        slicks=slicks_file.is_file(),
        ais=ais_file.is_file(),
        backward_drift=resolve_path(f"data/processed/drift/{case_id}_source_reconstruction_summary.json").is_file(),
        forward_drift=resolve_path(f"data/processed/attribution/{case_id}_forward_simulations_summary.json").is_file(),
        attribution=attr_file.is_file(),
        uncertainty=uncertainty_file.is_file(),
    )


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/api/health")
def get_health():
    """Health check endpoint confirming API status."""
    return {"status": "ok", "service": "SIH26143 Data Bridge", "version": "1.0.0"}


@app.get("/api/cases", response_model=List[CaseSummary])
def list_cases():
    """
    Discover all registered cases dynamically from data/cases/*.yaml.
    Never hardcodes case IDs.
    """
    cases_dir = resolve_path(CASES_DIR)
    if not cases_dir.is_dir():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "CONFIG_ERROR", "message": "Cases directory missing."},
        )

    summaries: List[CaseSummary] = []
    for yaml_path in sorted(cases_dir.glob("*.yaml")) + sorted(cases_dir.glob("*.yml")):
        try:
            cfg = load_case_config(yaml_path)
            raw = cfg.raw_data
            spatial = raw.get("spatial", {})
            temporal = raw.get("temporal", {})
            sat = raw.get("satellite", {})
            val = raw.get("validation", {})

            incident_pt = spatial.get("incident_point", {})
            loc = None
            if "latitude" in incident_pt and "longitude" in incident_pt:
                loc = LocationInfo(
                    latitude=float(incident_pt["latitude"]),
                    longitude=float(incident_pt["longitude"]),
                    description=incident_pt.get("description"),
                )

            avail = _get_dataset_availability(cfg.case_id)

            summaries.append(
                CaseSummary(
                    case_id=cfg.case_id,
                    name=cfg.name,
                    incident_type=cfg.incident_type,
                    location_name=cfg.location_name,
                    location=loc,
                    event_time_utc=temporal.get("spill_incident_estimated_start"),
                    observation_time_utc=sat.get("observation_timestamp_utc"),
                    validation_role=val.get("validation_role") or val.get("role"),
                    ground_truth_quality=val.get("ground_truth_quality"),
                    datasets_available=avail,
                )
            )
        except Exception:
            # Continue on malformed non-essential manifests
            continue

    return summaries


@app.get("/api/cases/{case_id}", response_model=CaseDetail)
def get_case_detail(case_id: str):
    """
    Return comprehensive case metadata including spatial bounds and dataset availability.
    """
    _safe_resolve_case_id(case_id)
    cfg = load_case_config(case_id)
    raw = cfg.raw_data

    spatial = raw.get("spatial", {})
    temporal = raw.get("temporal", {})
    sat = raw.get("satellite", {})
    val = raw.get("validation", {})

    incident_pt = spatial.get("incident_point", {})
    loc = LocationInfo(
        latitude=float(incident_pt.get("latitude", 0.0)),
        longitude=float(incident_pt.get("longitude", 0.0)),
        description=incident_pt.get("description"),
    )

    aoi = spatial.get("aoi_bounding_box", {})
    bounds = None
    if all(k in aoi for k in ["west", "south", "east", "north"]):
        bounds = {
            "west": float(aoi["west"]),
            "south": float(aoi["south"]),
            "east": float(aoi["east"]),
            "north": float(aoi["north"]),
        }

    search_range = temporal.get("source_search_time_range", {})
    event_info = EventInfo(
        incident_type=cfg.incident_type,
        estimated_start_utc=temporal.get("spill_incident_estimated_start"),
        estimated_end_utc=temporal.get("spill_incident_estimated_end"),
        search_start_utc=search_range.get("start_utc"),
        search_end_utc=search_range.get("end_utc"),
    )

    obs_info = ObservationInfo(
        platform=sat.get("platform"),
        instrument=sat.get("instrument"),
        sensor_mode=sat.get("sensor_mode"),
        scene_id=sat.get("scene_id"),
        timestamp_utc=sat.get("observation_timestamp_utc"),
        orbit_direction=sat.get("orbit_direction"),
    )

    return CaseDetail(
        case_id=cfg.case_id,
        name=cfg.name,
        location_name=cfg.location_name,
        location=loc,
        bounding_box=bounds,
        event=event_info,
        observation=obs_info,
        validation_role=val.get("validation_role") or val.get("role"),
        ground_truth_quality=val.get("ground_truth_quality"),
        ground_truth_source=val.get("ground_truth_source"),
        datasets=_get_dataset_availability(cfg.case_id),
    )


@app.get("/api/cases/{case_id}/sar/stats")
def get_sar_stats(case_id: str):
    """
    Expose existing calibrated Sentinel-1 SAR preprocessing statistics.
    """
    _safe_resolve_case_id(case_id)
    stats_path = resolve_path(f"data/processed/satellite/{case_id}_s1_preprocessing_stats.json")
    if not stats_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "DATASET_NOT_AVAILABLE",
                "message": f"SAR preprocessing statistics unavailable for case '{case_id}'.",
            },
        )

    with open(stats_path, "r", encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/cases/{case_id}/slicks")
def get_slicks_geojson(case_id: str):
    """
    Expose verified segmented oil slick geometries as standard GeoJSON.
    """
    _safe_resolve_case_id(case_id)
    geojson_path = resolve_path(f"data/processed/satellite/{case_id}_candidate_slicks.geojson")
    if not geojson_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "DATASET_NOT_AVAILABLE",
                "message": f"Candidate slick GeoJSON unavailable for case '{case_id}'.",
            },
        )

    with open(geojson_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return JSONResponse(content=data)


@app.get("/api/cases/{case_id}/ais/vessels", response_model=List[VesselCandidateItem])
def get_ais_vessels(case_id: str):
    """
    Expose candidate vessels extracted from AIS within the 4D spatiotemporal window.
    """
    _safe_resolve_case_id(case_id)
    summary_path = resolve_path(f"data/processed/hypotheses/{case_id}_source_hypotheses_summary.json")
    if not summary_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "DATASET_NOT_AVAILABLE",
                "message": f"AIS candidate vessel data unavailable for case '{case_id}'.",
            },
        )

    with open(summary_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    case_meta = _load_case_yaml(case_id)
    val_info = case_meta.get("validation", {})
    ref_mmsi = val_info.get("reference_vessel_mmsi")
    ref_name = val_info.get("reference_vessel_name")

    vessels_dict = data.get("hypotheses_per_vessel", {})
    result: List[VesselCandidateItem] = []
    for mmsi_str, vinfo in vessels_dict.items():
        try:
            mmsi = int(mmsi_str)
        except ValueError:
            continue

        raw_name = str(vinfo.get("vessel_name", "UNKNOWN"))
        if (raw_name == "UNKNOWN" or not raw_name) and ref_mmsi and mmsi == ref_mmsi and ref_name:
            vname = str(ref_name)
        else:
            vname = raw_name

        result.append(
            VesselCandidateItem(
                mmsi=mmsi,
                vessel_name=vname,
                hypothesis_count=int(vinfo.get("hypothesis_count", 0)),
                hypothesis_ids=vinfo.get("hypothesis_ids", []),
                min_distance_m=float(vinfo.get("min_distance_m", 0.0)),
                max_distance_m=float(vinfo.get("max_distance_m", 0.0)),
            )
        )

    # Sort deterministically by hypothesis_count desc, then min_distance asc
    result.sort(key=lambda x: (-x.hypothesis_count, x.min_distance_m))
    return result


def _safe_float(val, default=None):
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _build_explainability(ev_detail: dict, row: dict, vessel_rank: int):
    if not ev_detail:
        return None, None, None, None

    centroid_err = _safe_float(ev_detail.get("centroid_error_m"))
    mean_part_dist = _safe_float(ev_detail.get("mean_particle_distance_m"))
    source_dist = _safe_float(ev_detail.get("vessel_source_distance_m"))
    rel_time = ev_detail.get("release_timestamp")
    ais_gap = _safe_float(ev_detail.get("ais_gap_seconds"))
    ais_quality = ev_detail.get("ais_track_quality")
    coverage = _safe_float(ev_detail.get("coverage"))
    iou = _safe_float(ev_detail.get("iou"))

    drift_sc = _safe_float(ev_detail.get("drift_score"), 0.0)
    spatial_sc = _safe_float(ev_detail.get("spatial_score"), 0.0)
    temporal_sc = _safe_float(ev_detail.get("temporal_score"), 0.0)
    source_sc = _safe_float(ev_detail.get("source_score"), 0.0)
    ais_sc = _safe_float(ev_detail.get("ais_quality_score"), 0.0)

    causal_status = str(ev_detail.get("causal_precedence_status", "UNKNOWN"))
    raw_elig = ev_detail.get("causal_eligibility")
    if isinstance(raw_elig, str):
        causal_elig = raw_elig.lower() in ("true", "1", "yes")
    elif isinstance(raw_elig, bool):
        causal_elig = raw_elig
    else:
        causal_elig = None

    raw_conflict = ev_detail.get("has_conflict")
    if isinstance(raw_conflict, str):
        has_conflict = raw_conflict.lower() in ("true", "1", "yes")
    elif isinstance(raw_conflict, bool):
        has_conflict = raw_conflict
    else:
        has_conflict = False

    conflict_desc = ev_detail.get("conflict_description")
    if conflict_desc in ("None", "", None):
        conflict_desc = None

    metrics = UnderlyingMetrics(
        centroid_error_m=centroid_err,
        mean_particle_distance_m=mean_part_dist,
        vessel_source_distance_m=source_dist,
        release_timestamp=rel_time,
        ais_gap_seconds=ais_gap,
        ais_track_quality=ais_quality,
        coverage=coverage,
        iou=iou,
        causal_precedence_status=causal_status,
        causal_eligibility=causal_elig,
        has_conflict=has_conflict,
        conflict_description=conflict_desc,
        source_score=source_sc,
        spatial_score=spatial_sc,
        temporal_score=temporal_sc,
        drift_score=drift_sc,
        ais_quality_score=ais_sc,
    )

    primary_str = ev_detail.get("primary_strength") or row.get("best_hypothesis_strength")
    primary_wk = ev_detail.get("primary_weakness") or row.get("best_hypothesis_weakness")

    # Build Why Ranked Highly
    why_highly = []
    if drift_sc >= 0.70:
        err_str = f"Centroid error: {centroid_err:.1f} m" if centroid_err is not None else f"Drift score: {drift_sc:.2f}"
        why_highly.append(f"Physical drift compatibility: {err_str} (score: {drift_sc:.2f})")
    elif drift_sc >= 0.60:
        why_highly.append(f"Physical drift compatibility: Consistent drift trajectory (score: {drift_sc:.2f})")

    if spatial_sc >= 0.60:
        dist_str = f"Source distance: {source_dist:,.1f} m" if source_dist is not None else f"Spatial score: {spatial_sc:.2f}"
        why_highly.append(f"Spatial compatibility: {dist_str} (score: {spatial_sc:.2f})")

    if temporal_sc >= 0.80:
        time_str = f"Release time: {rel_time}" if rel_time else "Coincides with release window"
        why_highly.append(f"Temporal compatibility: {time_str} (score: {temporal_sc:.2f})")

    if ais_sc >= 0.60:
        qual_str = f"Track quality: {ais_quality}" if ais_quality else "AIS telemetry consistent"
        if ais_gap is not None:
            qual_str += f" ({ais_gap:.0f}s gap)"
        why_highly.append(f"AIS trajectory compatibility: {qual_str} (score: {ais_sc:.2f})")

    if causal_status == "AT_RELEASE" and causal_elig is not False:
        why_highly.append("Causal consistency: Status: AT_RELEASE (eligible)")
    elif causal_status not in ("POST_RELEASE", "UNKNOWN") and causal_elig is not False:
        why_highly.append(f"Causal consistency: Status: {causal_status}")

    if iou and iou >= 0.08:
        why_highly.append(f"Forward simulation compatibility: Slick dispersion matches observed geometry (IoU: {iou:.3f})")

    # Build Why Not Ranked Higher / Limiting factors
    why_not = []
    limiting_factors = []

    # 1. Post-event check
    if causal_status == "POST_RELEASE" or causal_elig is False:
        reason = "Not eligible as a release-source explanation because its relevant AIS presence occurs after the hypothesized release."
        why_not.append(reason)
        limiting_factors.append(LimitingFactor(
            dimension="causal",
            label="Post-Event AIS Presence",
            severity="DISQUALIFYING",
            detail=reason,
            underlying_value=f"Status: {causal_status}, Eligible: {causal_elig}"
        ))

    # 2. Spatial limitation
    if (source_dist and source_dist >= 3000.0) or (spatial_sc < 0.40):
        dist_km = (source_dist / 1000.0) if source_dist else 0.0
        reason = f"Candidate vessel was {dist_km:.1f} km away from hypothesized release position at candidate release time (spatial score: {spatial_sc:.2f})."
        why_not.append(reason)
        limiting_factors.append(LimitingFactor(
            dimension="spatial",
            label="Poor Spatial Match",
            severity="HIGH_LIMITING" if spatial_sc < 0.25 else "MODERATE_LIMITING",
            detail=reason,
            underlying_value=f"{dist_km:.1f} km distance (score: {spatial_sc:.2f})"
        ))

    # 3. Drift limitation
    if (centroid_err and centroid_err >= 100.0) or (drift_sc < 0.60):
        reason = f"Substantial displacement from simulated backward drift trajectory (centroid error: {centroid_err:.1f} m, drift score: {drift_sc:.2f})."
        why_not.append(reason)
        limiting_factors.append(LimitingFactor(
            dimension="drift",
            label="Poor Drift Match",
            severity="HIGH_LIMITING" if drift_sc < 0.50 else "MODERATE_LIMITING",
            detail=reason,
            underlying_value=f"Centroid error: {centroid_err:.1f} m (score: {drift_sc:.2f})"
        ))

    # 4. Temporal limitation
    if temporal_sc < 0.65:
        reason = f"Candidate AIS telemetry deviates from hypothesized release time (temporal score: {temporal_sc:.2f})."
        why_not.append(reason)
        limiting_factors.append(LimitingFactor(
            dimension="temporal",
            label="Poor Temporal Match",
            severity="MODERATE_LIMITING",
            detail=reason,
            underlying_value=f"Temporal score: {temporal_sc:.2f}"
        ))

    # 5. AIS telemetry limitation
    if (ais_gap and ais_gap > 1800.0) or (ais_sc < 0.50):
        reason = f"Insufficient AIS evidence due to sparse telemetry or significant track gap ({ais_gap:.0f}s gap, score: {ais_sc:.2f})."
        why_not.append(reason)
        limiting_factors.append(LimitingFactor(
            dimension="ais",
            label="Insufficient AIS Evidence",
            severity="MODERATE_LIMITING",
            detail=reason,
            underlying_value=f"AIS gap: {ais_gap:.0f} s (score: {ais_sc:.2f})"
        ))

    # 6. Forward simulation limitation
    if (iou is not None and iou < 0.05) and (coverage is not None and coverage < 0.70):
        reason = f"Forward trajectory simulation exhibits low geometric overlap with observed slick (IoU: {iou:.3f}, coverage: {coverage:.2f})."
        why_not.append(reason)
        limiting_factors.append(LimitingFactor(
            dimension="forward_simulation",
            label="Poor Forward Simulation Match",
            severity="MODERATE_LIMITING",
            detail=reason,
            underlying_value=f"IoU: {iou:.3f}, Coverage: {coverage:.2f}"
        ))

    # 7. Discrepancy conflict from artifact
    if has_conflict and conflict_desc:
        limiting_factors.append(LimitingFactor(
            dimension="evidence_conflict",
            label="Dimensional Discrepancy",
            severity="MODERATE_LIMITING",
            detail=conflict_desc,
            underlying_value=conflict_desc
        ))

    breakdown = EvidenceBreakdown(
        why_ranked_highly=why_highly,
        why_not_ranked_higher=why_not,
        limiting_factors=limiting_factors,
    )

    return primary_str, primary_wk, metrics, breakdown


@app.get("/api/cases/{case_id}/attribution/ranking", response_model=List[VesselAttributionItem])
def get_attribution_ranking(case_id: str):
    """
    Expose existing ranked attribution outputs for candidate vessels.
    Preserves exact backend scores, ranks, and evidence component decompositions.
    Uses validated causal consistency artifacts if present (Phase 13), falling back
    to baseline attribution outputs.
    Enriches each candidate with deterministic why / why-not explainability and underlying metrics.
    """
    _safe_resolve_case_id(case_id)
    attr_dir = resolve_path(ATTRIBUTION_PROCESSED_DIR)

    # 1. Evidence map resolution (check causal hypothesis evidence CSV, then hypothesis evidence JSON)
    evidence_map = {}
    causal_hyp_csv = attr_dir / f"{case_id}_causal_hypothesis_evidence.csv"
    hyp_json = attr_dir / f"{case_id}_hypothesis_evidence.json"

    if causal_hyp_csv.is_file():
        import csv
        with open(causal_hyp_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                hid = row.get("hypothesis_id")
                if hid:
                    evidence_map[hid] = row
    elif hyp_json.is_file():
        try:
            with open(hyp_json, "r", encoding="utf-8") as f:
                ev_list = json.load(f)
                for item in ev_list:
                    hid = item.get("hypothesis_id")
                    if hid:
                        evidence_map[hid] = item
        except Exception:
            pass

    case_meta = _load_case_yaml(case_id)
    val_info = case_meta.get("validation", {})
    ref_mmsi = val_info.get("reference_vessel_mmsi")
    ref_name = val_info.get("reference_vessel_name")

    # 2. Check for causal vessel summary CSV first, then vessel summary JSON
    causal_ves_csv = attr_dir / f"{case_id}_causal_vessel_summary.csv"
    ves_json = attr_dir / f"{case_id}_vessel_summary.json"

    if causal_ves_csv.is_file():
        import csv
        results: List[VesselAttributionItem] = []
        with open(causal_ves_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                mmsi_val = int(row["mmsi"])
                hid = row.get("best_hypothesis_id", "")
                ev_detail = evidence_map.get(hid, {})
                v_rank = int(row["vessel_rank"])

                components = None
                if ev_detail:
                    components = {
                        "drift_consistency": float(ev_detail.get("drift_score", 0.0)),
                        "spatial_compatibility": float(ev_detail.get("spatial_score", 0.0)),
                        "source_plausibility": float(ev_detail.get("source_score", 0.0)),
                        "temporal_compatibility": float(ev_detail.get("temporal_score", 0.0)),
                        "ais_track_quality": float(ev_detail.get("ais_quality_score", 0.0)),
                    }

                raw_name = str(row.get("vessel_name", "UNKNOWN"))
                if (raw_name == "UNKNOWN" or not raw_name) and ref_mmsi and mmsi_val == ref_mmsi and ref_name:
                    vname = str(ref_name)
                else:
                    vname = raw_name

                prim_str, prim_wk, und_metrics, ev_breakdown = _build_explainability(ev_detail, row, v_rank)

                results.append(
                    VesselAttributionItem(
                        mmsi=mmsi_val,
                        vessel_name=vname,
                        vessel_type=str(row.get("vessel_type", "UNKNOWN")),
                        vessel_rank=v_rank,
                        best_evidence_score=float(row["best_evidence_score"]),
                        mean_evidence_score=float(row.get("mean_evidence_score", row["best_evidence_score"])),
                        vessel_evidence_state=str(row.get("vessel_evidence_state", "UNKNOWN")),
                        causal_precedence_status=str(ev_detail.get("causal_precedence_status", "UNKNOWN")),
                        best_hypothesis_id=hid,
                        best_associated_slick=row.get("best_associated_slick"),
                        compatible_hypotheses_count=int(row.get("compatible_hypotheses_count", 1)),
                        evidence_components=components,
                        best_hypothesis_explanation=row.get("best_hypothesis_explanation"),
                        primary_strength=prim_str,
                        primary_weakness=prim_wk,
                        underlying_metrics=und_metrics,
                        evidence_breakdown=ev_breakdown,
                    )
                )
        results.sort(key=lambda x: x.vessel_rank)
        return results

    elif ves_json.is_file():
        with open(ves_json, "r", encoding="utf-8") as f:
            raw_list = json.load(f)

        results: List[VesselAttributionItem] = []
        for row in raw_list:
            mmsi_val = int(row["mmsi"])
            hid = row.get("best_hypothesis_id", "")
            ev_detail = evidence_map.get(hid, {})
            v_rank = int(row["vessel_rank"])

            components = None
            if ev_detail:
                components = {
                    "drift_consistency": float(ev_detail.get("drift_score", 0.0)),
                    "spatial_compatibility": float(ev_detail.get("spatial_score", 0.0)),
                    "source_plausibility": float(ev_detail.get("source_score", 0.0)),
                    "temporal_compatibility": float(ev_detail.get("temporal_score", 0.0)),
                    "ais_track_quality": float(ev_detail.get("ais_quality_score", 0.0)),
                }

            raw_name = str(row.get("vessel_name", "UNKNOWN"))
            if (raw_name == "UNKNOWN" or not raw_name) and ref_mmsi and mmsi_val == ref_mmsi and ref_name:
                vname = str(ref_name)
            else:
                vname = raw_name

            prim_str, prim_wk, und_metrics, ev_breakdown = _build_explainability(ev_detail, row, v_rank)

            results.append(
                VesselAttributionItem(
                    mmsi=mmsi_val,
                    vessel_name=vname,
                    vessel_type=str(row.get("vessel_type", "UNKNOWN")),
                    vessel_rank=v_rank,
                    best_evidence_score=float(row["best_evidence_score"]),
                    mean_evidence_score=float(row.get("mean_evidence_score", row["best_evidence_score"])),
                    vessel_evidence_state=str(row.get("vessel_evidence_state", "UNKNOWN")),
                    causal_precedence_status=str(ev_detail.get("causal_precedence_status", "UNKNOWN")),
                    best_hypothesis_id=hid,
                    best_associated_slick=row.get("best_associated_slick"),
                    compatible_hypotheses_count=int(row.get("compatible_hypotheses_count", 1)),
                    evidence_components=components,
                    best_hypothesis_explanation=row.get("best_hypothesis_explanation"),
                    primary_strength=prim_str,
                    primary_weakness=prim_wk,
                    underlying_metrics=und_metrics,
                    evidence_breakdown=ev_breakdown,
                )
            )

        results.sort(key=lambda x: x.vessel_rank)
        return results

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "error": "DATASET_NOT_AVAILABLE",
            "message": f"Attribution ranking data unavailable for case '{case_id}'.",
        },
    )


@app.get("/api/cases/{case_id}/attribution/uncertainty", response_model=UncertaintySummary)
def get_attribution_uncertainty(case_id: str):
    """
    Expose existing Monte Carlo uncertainty analysis summary.
    """
    _safe_resolve_case_id(case_id)
    unc_path = resolve_path(f"data/processed/attribution/{case_id}_uncertainty_summary.json")
    if not unc_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "DATASET_NOT_AVAILABLE",
                "message": f"Uncertainty analysis data unavailable for case '{case_id}'.",
            },
        )

    with open(unc_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return UncertaintySummary(
        case_id=data.get("case_id", case_id),
        timestamp_utc=data.get("timestamp_utc", ""),
        ensemble_size=int(data.get("ensemble_size", 50)),
        random_seed=int(data.get("random_seed", 42)),
        calibration_audit=data.get("calibration_audit", {}),
        rank_stability_top_hypotheses=data.get("rank_stability_top_hypotheses", []),
    )


# ============================================================================
# GEOSPATIAL ENDPOINTS (PHASE 15.2C)
# ============================================================================

_ais_tracks_cache = {}
_drift_cache = {}


@app.get("/api/cases/{case_id}/sar/raster", response_model=SarRasterInfo)
def get_sar_raster_info(case_id: str):
    """
    Expose georeferenced raster metadata for Sentinel-1 SAR imagery.
    Distinguishes the source scientific GeoTIFF from the read-only visualization derivative.
    """
    _safe_resolve_case_id(case_id)
    stats_path = resolve_path(f"data/processed/satellite/{case_id}_s1_preprocessing_stats.json")
    derivative_path = resolve_path(f"data/processed/satellite/{case_id}_s1_visual_derivative.png")

    if not stats_path.is_file() or not derivative_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "DATASET_NOT_AVAILABLE",
                "message": f"SAR raster visualization derivative unavailable for case '{case_id}'.",
            },
        )

    with open(stats_path, "r", encoding="utf-8") as f:
        stats = json.load(f)

    bounds = stats.get("raster_metadata", {}).get("bounds_epsg4326")
    if not bounds:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "DATASET_NOT_AVAILABLE",
                "message": f"Spatial bounds missing for SAR raster in case '{case_id}'.",
            },
        )

    w, s, e, n = bounds["west"], bounds["south"], bounds["east"], bounds["north"]
    # Coordinates order for MapLibre image source: top-left, top-right, bottom-right, bottom-left
    coordinates = [
        [w, n],
        [e, n],
        [e, s],
        [w, s],
    ]

    return SarRasterInfo(
        case_id=case_id,
        source_scientific_raster=f"data/processed/satellite/{case_id}_s1_calibrated.tif",
        visualization_derivative_url=f"/api/cases/{case_id}/sar/visual-derivative.png",
        is_visualization_derivative=True,
        bounds=bounds,
        coordinates=coordinates,
    )


@app.get("/api/cases/{case_id}/sar/visual-derivative.png")
def get_sar_visual_derivative(case_id: str):
    """
    Serve the pre-generated read-only georeferenced visualization derivative PNG for Sentinel-1 SAR.
    """
    _safe_resolve_case_id(case_id)
    derivative_path = resolve_path(f"data/processed/satellite/{case_id}_s1_visual_derivative.png")
    if not derivative_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "DATASET_NOT_AVAILABLE",
                "message": f"SAR visual derivative PNG unavailable for case '{case_id}'.",
            },
        )
    return FileResponse(path=derivative_path, media_type="image/png")


@app.get("/api/cases/{case_id}/hypotheses")
def get_hypotheses_geojson(case_id: str):
    """
    Expose actual 4D source hypotheses as standard GeoJSON Point features.
    """
    _safe_resolve_case_id(case_id)
    hyp_path = resolve_path(f"data/processed/hypotheses/{case_id}_source_hypotheses_4d.geojson")
    if not hyp_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "DATASET_NOT_AVAILABLE",
                "message": f"4D source hypotheses GeoJSON unavailable for case '{case_id}'.",
            },
        )

    with open(hyp_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return JSONResponse(content=data)


@app.get("/api/cases/{case_id}/ais/tracks")
def get_ais_tracks(case_id: str):
    """
    Expose actual candidate vessel AIS trajectories as GeoJSON LineStrings.
    Trajectories correspond to vessels evaluated in the 4D hypothesis space.
    """
    _safe_resolve_case_id(case_id)
    if case_id in _ais_tracks_cache:
        return JSONResponse(content=_ais_tracks_cache[case_id])

    ais_path = resolve_path(f"data/processed/ais/{case_id}_ais_normalized.csv")
    summary_path = resolve_path(f"data/processed/hypotheses/{case_id}_source_hypotheses_summary.json")

    if not ais_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "DATASET_NOT_AVAILABLE",
                "message": f"AIS normalized trajectories unavailable for case '{case_id}'.",
            },
        )

    import pandas as pd
    try:
        df = pd.read_csv(ais_path)

        # Identify candidate MMSIs
        candidate_mmsis = set()
        if summary_path.is_file():
            with open(summary_path, "r", encoding="utf-8") as f:
                s = json.load(f)
            candidate_mmsis = {int(k) for k in s.get("hypotheses_per_vessel", {}).keys() if str(k).isdigit()}

        if not candidate_mmsis:
            cv_path = resolve_path(f"data/processed/ais/{case_id}_candidate_vessels.csv")
            if cv_path.is_file():
                cv_df = pd.read_csv(cv_path)
                candidate_mmsis = set(cv_df["mmsi"].dropna().astype(int).unique())

        if candidate_mmsis:
            cand_df = df[df["mmsi"].isin(candidate_mmsis)]
        else:
            cand_df = df

        time_col = "timestamp_utc" if "timestamp_utc" in cand_df.columns else "timestamp"
        if time_col in cand_df.columns:
            cand_df = cand_df.sort_values(["mmsi", time_col])

        features = []
        for mmsi, grp in cand_df.groupby("mmsi"):
            coords = []
            timestamps = []
            for row in grp.itertuples():
                if pd.notna(row.latitude) and pd.notna(row.longitude):
                    coords.append([float(row.longitude), float(row.latitude)])
                    timestamps.append(str(getattr(row, time_col)))
            if len(coords) >= 2:
                name = (
                    grp["vessel_name"].dropna().iloc[0]
                    if "vessel_name" in grp and not grp["vessel_name"].dropna().empty
                    else "UNKNOWN"
                )
                vtype = (
                    grp["vessel_type"].dropna().iloc[0]
                    if "vessel_type" in grp and not grp["vessel_type"].dropna().empty
                    else "UNKNOWN"
                )
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "LineString", "coordinates": coords},
                    "properties": {
                        "mmsi": int(mmsi),
                        "vessel_name": str(name),
                        "vessel_type": str(vtype),
                        "point_count": len(coords),
                        "start_time": timestamps[0] if timestamps else None,
                        "end_time": timestamps[-1] if timestamps else None,
                        "timestamps": timestamps,
                    },
                })

        fc = {"type": "FeatureCollection", "features": features}
        _ais_tracks_cache[case_id] = fc
        return JSONResponse(content=fc)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "PROCESSING_ERROR", "message": str(e)},
        )


@app.get("/api/cases/{case_id}/drift/trajectories")
def get_drift_trajectories(case_id: str):
    """
    Expose actual backward Lagrangian drift trajectory particles as GeoJSON LineStrings.
    Samples the Monte Carlo drift ensemble to provide representative trajectories.
    """
    _safe_resolve_case_id(case_id)
    if case_id in _drift_cache:
        return JSONResponse(content=_drift_cache[case_id])

    drift_path = resolve_path(f"data/processed/drift/{case_id}_source_trajectories.json")
    if not drift_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "DATASET_NOT_AVAILABLE",
                "message": f"Backward drift trajectories unavailable for case '{case_id}'.",
            },
        )

    try:
        with open(drift_path, "r", encoding="utf-8") as f:
            d = json.load(f)

        features = []
        step = 25  # Sample representative particles from 500-particle ensemble
        for cand_id, particles in d.get("trajectories_by_candidate", {}).items():
            for i in range(0, len(particles), step):
                p = particles[i]
                coords = [[float(pt["lon"]), float(pt["lat"])] for pt in p if "lon" in pt and "lat" in pt]
                timestamps = [pt.get("time") for pt in p if "lon" in pt and "lat" in pt]
                if len(coords) >= 2:
                    features.append({
                        "type": "Feature",
                        "geometry": {"type": "LineString", "coordinates": coords},
                        "properties": {
                            "candidate_slick_id": cand_id,
                            "particle_index": i,
                            "start_time": p[0].get("time"),
                            "end_time": p[-1].get("time"),
                            "timestamps": timestamps,
                        },
                    })

        fc = {"type": "FeatureCollection", "features": features}
        _drift_cache[case_id] = fc
        return JSONResponse(content=fc)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "PROCESSING_ERROR", "message": str(e)},
        )


@app.get("/api/cases/{case_id}/attribution/spill-comparisons")
def get_spill_comparisons(case_id: str, hypothesis_id: Optional[str] = None):
    """
    Expose actual forward simulation comparisons between predicted slicks and observed SAR slicks.
    Returns physical comparison metrics (IoU, centroid error, particle coverage).
    """
    _safe_resolve_case_id(case_id)
    comp_path = resolve_path(f"data/processed/attribution/{case_id}_spill_comparisons.json")
    if not comp_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "DATASET_NOT_AVAILABLE",
                "message": f"Forward simulation spill comparisons unavailable for case '{case_id}'.",
            },
        )

    with open(comp_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if hypothesis_id:
        filtered = [item for item in data if item.get("hypothesis_id") == hypothesis_id]
        return JSONResponse(content=filtered)

    return JSONResponse(content=data)


@app.get("/api/cases/{case_id}/attribution/simulations/{hypothesis_id}")
def get_simulation_detail(case_id: str, hypothesis_id: str):
    """
    Expose forward hydrodynamic simulation particles and sampled trajectory for a hypothesis.
    Used by deck.gl for interactive counterfactual plume and drift visualization.
    """
    _safe_resolve_case_id(case_id)
    if ".." in hypothesis_id or "/" in hypothesis_id or "\\" in hypothesis_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_HYPOTHESIS_ID", "message": "Path traversal detected in hypothesis_id."},
        )
    sim_dir = resolve_path(f"data/processed/attribution/simulations/{hypothesis_id}")

    particles = []
    trajectories = []
    metadata = {}

    if sim_dir.is_dir():
        meta_file = sim_dir / "simulation_metadata.json"
        if meta_file.is_file():
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
            except Exception:
                pass

        particles_file = sim_dir / "final_particles.json"
        if particles_file.is_file():
            try:
                with open(particles_file, "r", encoding="utf-8") as f:
                    raw_particles = json.load(f)
                    # Extract compact [lon, lat] and particle info
                    particles = [
                        {
                            "particle_id": p.get("particle_id", idx),
                            "lat": float(p["lat"]),
                            "lon": float(p["lon"]),
                            "status": p.get("status", "active"),
                        }
                        for idx, p in enumerate(raw_particles)
                        if "lat" in p and "lon" in p
                    ]
            except Exception:
                pass

        traj_file = sim_dir / "trajectory.json"
        if traj_file.is_file():
            try:
                with open(traj_file, "r", encoding="utf-8") as f:
                    raw_trajs = json.load(f)
                    # Subsample representative trajectory tracks (every 25th track)
                    step = 25 if len(raw_trajs) > 25 else 1
                    sampled = []
                    for i in range(0, len(raw_trajs), step):
                        track = raw_trajs[i]
                        coords = [[float(pt["lon"]), float(pt["lat"])] for pt in track if "lon" in pt and "lat" in pt]
                        if coords:
                            sampled.append({
                                "track_index": i,
                                "coordinates": coords,
                            })
                    trajectories = sampled
            except Exception:
                pass

    # If simulation directory didn't exist or lacked metadata, fallback to spill-comparisons
    if not metadata:
        comp_path = resolve_path(f"data/processed/attribution/{case_id}_spill_comparisons.json")
        if comp_path.is_file():
            try:
                with open(comp_path, "r", encoding="utf-8") as f:
                    comps = json.load(f)
                matched = next((c for c in comps if c.get("hypothesis_id") == hypothesis_id), None)
                if matched:
                    metadata = matched
            except Exception:
                pass

    if not metadata and not particles:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "SIMULATION_NOT_FOUND",
                "message": f"Simulation artifacts for hypothesis '{hypothesis_id}' not found.",
            },
        )

    return JSONResponse(content={
        "case_id": case_id,
        "hypothesis_id": hypothesis_id,
        "metadata": metadata,
        "particles": particles,
        "trajectories": trajectories,
    })


# ============================================================================
# PHASE 23: INVESTIGATION DOSSIER & EXPORT ENDPOINTS
# ============================================================================

from backend.dossier_builder import build_investigation_dossier


@app.get("/api/cases/{case_id}/dossier", response_model=InvestigationDossier)
@app.get("/api/cases/{case_id}/report", response_model=InvestigationDossier)
def get_investigation_dossier(case_id: str):
    """
    Generate an investigator-facing 16-section investigation dossier from existing scientific outputs.
    Adheres strictly to decision-support terminology (best-supported hypothesis, investigation evidence,
    data limitation).
    Answers the 7 fundamental investigator questions.
    """
    _safe_resolve_case_id(case_id)
    return build_investigation_dossier(case_id)


# ============================================================================
# PHASE 24: AUTHORITY NOTIFICATION & ALERT WORKFLOW ENDPOINTS
# ============================================================================

from backend.notification_builder import build_authority_notifications
from backend.schemas import AuthorityAlert, NotificationFeedResponse


@app.get("/api/cases/{case_id}/notifications", response_model=NotificationFeedResponse)
def get_case_notifications(case_id: str):
    """
    Deliver structured decision-support notifications and authority dispatch memos
    for an investigation case from existing scientific artifacts.
    """
    _safe_resolve_case_id(case_id)
    return build_authority_notifications(case_id)


@app.get("/api/notifications", response_model=List[AuthorityAlert])
def get_all_notifications():
    """
    Retrieve all authority alerts across all registered cases in chronological order.
    """
    cases_dir = resolve_path(CASES_DIR)
    case_ids = []
    if cases_dir.is_dir():
        for p in sorted(cases_dir.glob("*.yaml")):
            case_ids.append(p.stem)
        for p in sorted(cases_dir.glob("*.yml")):
            if p.stem not in case_ids:
                case_ids.append(p.stem)

    all_alerts: List[AuthorityAlert] = []
    for cid in case_ids:
        try:
            feed = build_authority_notifications(cid)
            all_alerts.extend(feed.alerts)
        except Exception:
            continue

    # Sort descending by timestamp
    all_alerts.sort(key=lambda a: a.timestamp_utc, reverse=True)
    return all_alerts


@app.get("/api/notifications/{alert_id}", response_model=AuthorityAlert)
def get_single_notification(alert_id: str):
    """
    Retrieve a specific authority alert by unique alert identifier.
    """
    all_alerts = get_all_notifications()
    for alert in all_alerts:
        if alert.alert_id == alert_id:
            return alert
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"error": "ALERT_NOT_FOUND", "message": f"Authority alert '{alert_id}' not found."},
    )


# ============================================================================
# PHASE 25: DATA READINESS & PROVENANCE ENDPOINTS
# ============================================================================

from backend.readiness_builder import build_data_readiness_report
from backend.schemas import DataReadinessReport, DatasetProvenanceRecord


@app.get("/api/cases/{case_id}/readiness", response_model=DataReadinessReport)
def get_case_data_readiness(case_id: str):
    """
    Expose data availability, pillar checks, and data limitations for a case.
    Statuses strictly limited to: READY, LIMITED, UNAVAILABLE, NOT REQUIRED.
    """
    _safe_resolve_case_id(case_id)
    return build_data_readiness_report(case_id)


@app.get("/api/cases/{case_id}/provenance", response_model=List[DatasetProvenanceRecord])
def get_case_reproducible_provenance(case_id: str):
    """
    Expose reproducible provenance records (dataset name, source, acquisition time,
    processing version, SHA-256 where available, artifact timestamp).
    """
    _safe_resolve_case_id(case_id)
    report = build_data_readiness_report(case_id)
    return report.provenance_records


# ============================================================================
# Phase 26: Satellite Observation Metadata Upgrade
# ============================================================================

from backend.satellite_builder import build_satellite_observation_package
from backend.schemas import SatelliteObservationPackage


@app.get("/api/cases/{case_id}/satellite/observations", response_model=SatelliteObservationPackage)
def get_case_satellite_observations(case_id: str):
    """
    Expose detailed satellite observation package distinguishing operational Sentinel-1
    SAR (channel actually used by detector) from supporting Sentinel-2 optical imagery,
    along with observation timeline, revisit context, and structured observation records.
    """
    _safe_resolve_case_id(case_id)
    return build_satellite_observation_package(case_id)


# ============================================================================
# Phase 5: Operational SAR Observation Processing Pipeline
# ============================================================================

from pydantic import BaseModel

from backend.sar_pipeline.engine import (
    execute_sar_processing_job,
    get_sar_job,
    get_sar_job_results,
    get_sar_observation_detail,
    get_sar_observations_for_case,
)
from backend.sar_pipeline.schemas import (
    SARJobResult,
    SARObservationRecord,
    SARProcessingJob,
    SARValidationResult,
)
from backend.sar_pipeline.validator import validate_sar_artifact


@app.get("/api/cases/{case_id}/satellite/observations/{observation_id}", response_model=SARObservationRecord)
def get_case_satellite_observation_detail(case_id: str, observation_id: str):
    """
    Retrieve single SAR or optical observation record by ID with validation status.
    """
    _safe_resolve_case_id(case_id)
    obs = get_sar_observation_detail(case_id, observation_id)
    if not obs:
        raise HTTPException(status_code=404, detail=f"Observation '{observation_id}' not found for case '{case_id}'")
    return obs


@app.get("/api/cases/{case_id}/satellite/validation", response_model=SARValidationResult)
def get_case_satellite_validation(case_id: str, observation_id: Optional[str] = None):
    """
    Validate SAR observation raster and metadata across 8 physical/raster checks.
    """
    _safe_resolve_case_id(case_id)
    return validate_sar_artifact(case_id, observation_id)


class SARProcessRequest(BaseModel):
    observation_id: Optional[str] = None
    reprocess: bool = False


@app.post("/api/cases/{case_id}/satellite/process", response_model=SARProcessingJob)
def process_case_satellite_sar(case_id: str, body: Optional[SARProcessRequest] = None):
    """
    Execute or verify SAR observation processing pipeline:
    Input Validation -> Radiometric Calibration -> Speckle Filter -> Dark-Spot Detection -> Vectorization -> Geospatial Overlay.
    """
    _safe_resolve_case_id(case_id)
    obs_id = body.observation_id if body else None
    reprocess = body.reprocess if body else False
    return execute_sar_processing_job(case_id, obs_id, reprocess)


@app.get("/api/satellite/jobs/{job_id}", response_model=SARProcessingJob)
def get_satellite_processing_job(job_id: str):
    """
    Retrieve SAR observation processing job status and progress stages.
    """
    job = get_sar_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"SAR processing job '{job_id}' not found")
    return job


@app.get("/api/satellite/jobs/{job_id}/results", response_model=SARJobResult)
def get_satellite_processing_job_results(job_id: str):
    """
    Retrieve comprehensive SAR observation processing results and 6-stage provenance chain.
    """
    res = get_sar_job_results(job_id)
    if not res:
        raise HTTPException(status_code=404, detail=f"Results for SAR processing job '{job_id}' not found")
    return res





