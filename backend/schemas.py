"""
backend/schemas.py

Pydantic models for the SIH26143 Read-Only FastAPI Data Bridge.
Preserves scientific fidelity without lossy transformations.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class LocationInfo(BaseModel):
    latitude: float
    longitude: float
    description: Optional[str] = None


class DatasetsAvailable(BaseModel):
    sar: bool = False
    slicks: bool = False
    ais: bool = False
    backward_drift: bool = False
    forward_drift: bool = False
    attribution: bool = False
    uncertainty: bool = False


class CaseSummary(BaseModel):
    case_id: str
    name: str
    incident_type: Optional[str] = None
    location_name: Optional[str] = None
    location: Optional[LocationInfo] = None
    event_time_utc: Optional[str] = None
    observation_time_utc: Optional[str] = None
    validation_role: Optional[str] = None
    ground_truth_quality: Optional[str] = None
    datasets_available: DatasetsAvailable


class EventInfo(BaseModel):
    incident_type: Optional[str] = None
    estimated_start_utc: Optional[str] = None
    estimated_end_utc: Optional[str] = None
    search_start_utc: Optional[str] = None
    search_end_utc: Optional[str] = None


class ObservationInfo(BaseModel):
    platform: Optional[str] = None
    instrument: Optional[str] = None
    sensor_mode: Optional[str] = None
    scene_id: Optional[str] = None
    timestamp_utc: Optional[str] = None
    orbit_direction: Optional[str] = None


class CaseDetail(BaseModel):
    case_id: str
    name: str
    location_name: Optional[str] = None
    location: Optional[LocationInfo] = None
    bounding_box: Optional[Dict[str, float]] = None
    event: Optional[EventInfo] = None
    observation: Optional[ObservationInfo] = None
    validation_role: Optional[str] = None
    ground_truth_quality: Optional[str] = None
    ground_truth_source: Optional[str] = None
    datasets: DatasetsAvailable


class VesselCandidateItem(BaseModel):
    mmsi: int
    vessel_name: str
    hypothesis_count: int
    hypothesis_ids: List[str] = Field(default_factory=list)
    min_distance_m: float
    max_distance_m: float


class EvidenceComponents(BaseModel):
    drift_consistency: float
    spatial_compatibility: float
    source_plausibility: float
    temporal_compatibility: float
    ais_track_quality: float


class VesselAttributionItem(BaseModel):
    mmsi: int
    vessel_name: str
    vessel_type: str
    vessel_rank: int
    best_evidence_score: float
    mean_evidence_score: float
    vessel_evidence_state: str
    causal_precedence_status: Optional[str] = "UNKNOWN"
    best_hypothesis_id: str
    best_associated_slick: Optional[str] = None
    compatible_hypotheses_count: int = 1
    evidence_components: Optional[Dict[str, float]] = None
    best_hypothesis_explanation: Optional[str] = None


class SlickFeature(BaseModel):
    type: str = "Feature"
    id: Optional[str] = None
    geometry: Dict[str, Any]
    properties: Dict[str, Any]


class SlickFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    metadata: Optional[Dict[str, Any]] = None
    features: List[Dict[str, Any]] = Field(default_factory=list)


class CalibrationAudit(BaseModel):
    is_probability_calibrated: bool
    calibration_status: str
    available_cases_count: Optional[int] = None
    verified_culprit_cases_count: Optional[int] = None
    mandatory_scientific_notice: str


class RankStabilityItem(BaseModel):
    hypothesis_id: Optional[str] = None
    vessel_name: Optional[str] = None
    top_1_frequency: float
    top_3_frequency: float
    mean_rank: float
    std_rank: float
    mean_score: Optional[float] = None
    rank_stability_category: str


class UncertaintySummary(BaseModel):
    case_id: str
    timestamp_utc: str
    ensemble_size: int
    random_seed: int
    calibration_audit: Dict[str, Any]
    rank_stability_top_hypotheses: List[Dict[str, Any]] = Field(default_factory=list)


class SarRasterInfo(BaseModel):
    case_id: str
    source_scientific_raster: str
    visualization_derivative_url: str
    is_visualization_derivative: bool = True
    bounds: Dict[str, float]
    coordinates: List[List[float]]


class ErrorResponse(BaseModel):
    error: str
    message: str

