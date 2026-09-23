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
    EventInfo,
    LocationInfo,
    ObservationInfo,
    SarRasterInfo,
    SlickFeatureCollection,
    UncertaintySummary,
    VesselAttributionItem,
    VesselCandidateItem,
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
                    validation_role=val.get("role"),
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
        validation_role=val.get("role"),
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


@app.get("/api/cases/{case_id}/attribution/ranking", response_model=List[VesselAttributionItem])
def get_attribution_ranking(case_id: str):
    """
    Expose existing ranked attribution outputs for candidate vessels.
    Preserves exact backend scores, ranks, and evidence component decompositions.
    Uses validated causal consistency artifacts if present (Phase 13), falling back
    to baseline attribution outputs.
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

                results.append(
                    VesselAttributionItem(
                        mmsi=mmsi_val,
                        vessel_name=vname,
                        vessel_type=str(row.get("vessel_type", "UNKNOWN")),
                        vessel_rank=int(row["vessel_rank"]),
                        best_evidence_score=float(row["best_evidence_score"]),
                        mean_evidence_score=float(row.get("mean_evidence_score", row["best_evidence_score"])),
                        vessel_evidence_state=str(row.get("vessel_evidence_state", "UNKNOWN")),
                        causal_precedence_status=str(ev_detail.get("causal_precedence_status", "UNKNOWN")),
                        best_hypothesis_id=hid,
                        best_associated_slick=row.get("best_associated_slick"),
                        compatible_hypotheses_count=int(row.get("compatible_hypotheses_count", 1)),
                        evidence_components=components,
                        best_hypothesis_explanation=row.get("best_hypothesis_explanation"),
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

            results.append(
                VesselAttributionItem(
                    mmsi=mmsi_val,
                    vessel_name=vname,
                    vessel_type=str(row.get("vessel_type", "UNKNOWN")),
                    vessel_rank=int(row["vessel_rank"]),
                    best_evidence_score=float(row["best_evidence_score"]),
                    mean_evidence_score=float(row.get("mean_evidence_score", row["best_evidence_score"])),
                    vessel_evidence_state=str(row.get("vessel_evidence_state", "UNKNOWN")),
                    causal_precedence_status=str(ev_detail.get("causal_precedence_status", "UNKNOWN")),
                    best_hypothesis_id=hid,
                    best_associated_slick=row.get("best_associated_slick"),
                    compatible_hypotheses_count=int(row.get("compatible_hypotheses_count", 1)),
                    evidence_components=components,
                    best_hypothesis_explanation=row.get("best_hypothesis_explanation"),
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


