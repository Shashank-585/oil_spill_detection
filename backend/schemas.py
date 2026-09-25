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


class UnderlyingMetrics(BaseModel):
    centroid_error_m: Optional[float] = None
    mean_particle_distance_m: Optional[float] = None
    vessel_source_distance_m: Optional[float] = None
    release_timestamp: Optional[str] = None
    ais_gap_seconds: Optional[float] = None
    ais_track_quality: Optional[str] = None
    coverage: Optional[float] = None
    iou: Optional[float] = None
    causal_precedence_status: Optional[str] = None
    causal_eligibility: Optional[bool] = None
    has_conflict: Optional[bool] = None
    conflict_description: Optional[str] = None
    source_score: Optional[float] = None
    spatial_score: Optional[float] = None
    temporal_score: Optional[float] = None
    drift_score: Optional[float] = None
    ais_quality_score: Optional[float] = None


class LimitingFactor(BaseModel):
    dimension: str
    label: str
    severity: str
    detail: str
    underlying_value: Optional[str] = None


class EvidenceBreakdown(BaseModel):
    why_ranked_highly: List[str] = Field(default_factory=list)
    why_not_ranked_higher: List[str] = Field(default_factory=list)
    limiting_factors: List[LimitingFactor] = Field(default_factory=list)


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
    primary_strength: Optional[str] = None
    primary_weakness: Optional[str] = None
    underlying_metrics: Optional[UnderlyingMetrics] = None
    evidence_breakdown: Optional[EvidenceBreakdown] = None


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


# ============================================================================
# PHASE 23: INVESTIGATION DOSSIER & EXPORT MODELS
# ============================================================================

class ExecutiveQAItem(BaseModel):
    question: str
    answer: str
    status: str
    key_metric: Optional[str] = None


class Section1CaseIdentification(BaseModel):
    case_id: str
    name: str
    incident_type: str
    location_name: Optional[str] = None
    origin_coordinates: Optional[Dict[str, float]] = None
    incident_t0_utc: str
    observation_timestamp_utc: str
    validation_role: str
    ground_truth_source: Optional[str] = None
    status_category: str


class Section2ExecutiveSummary(BaseModel):
    core_questions: List[ExecutiveQAItem] = Field(default_factory=list)
    summary_narrative: str


class Section3SatelliteObservation(BaseModel):
    platform: str
    instrument: str
    sensor_mode: str
    scene_id: Optional[str] = None
    timestamp_utc: str
    orbit_direction: Optional[str] = None
    calibrated_file: Optional[str] = None


class Section4DetectedSlick(BaseModel):
    slicks_count: int
    total_area_m2: float
    total_area_hectares: float
    mean_backscatter_sigma0_db: Optional[float] = None
    damping_ratio_db: Optional[float] = None
    segmentation_algorithm: str


class Section5EnvironmentalConditions(BaseModel):
    ocean_currents_source: str
    ocean_currents_file: Optional[str] = None
    wind_source: str
    wind_file: Optional[str] = None
    spatial_coverage: Optional[Dict[str, float]] = None
    temporal_coverage: Optional[Dict[str, Any]] = None


class Section6SourceReconstruction(BaseModel):
    model_name: str
    integration_scheme: str
    leeway_factor: str
    wind_deflection_deg: str
    turbulent_diffusion_dh: str
    release_horizons_hours: List[int] = Field(default_factory=list)
    candidate_slicks_evaluated: int
    total_source_hypotheses: int


class Section7AisCoverage(BaseModel):
    spatial_window: Optional[Dict[str, float]] = None
    temporal_window: Optional[Dict[str, Any]] = None
    archive_available: bool
    total_candidate_mmsis: int
    track_quality_notes: str


class Section8CandidateVessels(BaseModel):
    total_vessels_in_corridor: int
    candidate_vessels_count: int
    filtering_criteria: str
    top_candidates_preview: List[Dict[str, Any]] = Field(default_factory=list)


class Section9Hypotheses4D(BaseModel):
    total_hypotheses_count: int
    dimensions: List[str] = Field(default_factory=lambda: ["Longitude", "Latitude", "Depth", "Release_Time"])
    generation_method: str


class Section10CounterfactualSimulation(BaseModel):
    simulation_engine: str
    particle_count_per_run: int
    total_simulations_run: int
    evaluation_metric: str
    mean_iou: Optional[float] = None
    top_hypothesis_iou: Optional[float] = None


class Section11EvidenceRanking(BaseModel):
    ranking_count: int
    top_vessel_name: Optional[str] = None
    top_vessel_mmsi: Optional[int] = None
    top_vessel_score: Optional[float] = None
    candidates: List[Dict[str, Any]] = Field(default_factory=list)


class Section12CausalConsistency(BaseModel):
    enforced: bool
    causal_status_top_candidate: Optional[str] = None
    disqualified_post_release_count: int = 0
    notes: str


class Section13Uncertainty(BaseModel):
    ensemble_size: int
    random_seed: int
    rank_stability_score: Optional[float] = None
    margin_to_rank_2: Optional[float] = None
    confidence_category: str


class Section14DataLimitations(BaseModel):
    limitations: List[str] = Field(default_factory=list)
    is_negative_control: bool
    ais_archive_missing: bool


class Section15Conclusion(BaseModel):
    best_supported_hypothesis: str
    synthesis_statement: str
    decision_support_role: str


class Section16Provenance(BaseModel):
    sha256_checksum: str
    generated_at_utc: str
    system_version: str
    non_deceptive_statement: str


class InvestigationDossier(BaseModel):
    dossier_version: str = "1.0.0"
    case_id: str
    case_identification: Section1CaseIdentification
    executive_summary: Section2ExecutiveSummary
    satellite_observation: Section3SatelliteObservation
    detected_slick: Section4DetectedSlick
    environmental_conditions: Section5EnvironmentalConditions
    source_reconstruction: Section6SourceReconstruction
    ais_coverage: Section7AisCoverage
    candidate_vessels: Section8CandidateVessels
    hypotheses_4d: Section9Hypotheses4D
    counterfactual_simulation: Section10CounterfactualSimulation
    evidence_ranking: Section11EvidenceRanking
    causal_consistency: Section12CausalConsistency
    uncertainty: Section13Uncertainty
    data_limitations: Section14DataLimitations
    conclusion: Section15Conclusion
    provenance: Section16Provenance


# ==============================================================================
# Phase 24: Authority Notification & Alert Models
# ==============================================================================

class AuthorityAlert(BaseModel):
    alert_id: str
    case_id: str
    alert_type: str  # POTENTIAL_SPILL_DETECTED, INVESTIGATION_READY, STRONGLY_SUPPORTED_HYPOTHESIS, INSUFFICIENT_EVIDENCE, AIS_DATA_UNAVAILABLE, INVESTIGATION_UPDATED
    timestamp_utc: str
    severity: str = "NOTICE"  # INFO, NOTICE, ACTION_REQUIRED (non-prejudicial; avoids unsupported "high risk")
    subject: str
    summary: str
    body_markdown: str
    case_name: str
    observation_time_utc: Optional[str] = None
    satellite_platform: Optional[str] = None
    investigation_status: str
    slick_count: int = 0
    slick_total_area_ha: float = 0.0
    candidate_vessel_count: int = 0
    attribution_status: str  # STRONGLY_SUPPORTED, INSUFFICIENT_EVIDENCE, AIS_UNAVAILABLE, NEGATIVE_CONTROL, PRELIMINARY
    top_supported_hypothesis: Optional[str] = None
    key_limitations: List[str] = Field(default_factory=list)
    dossier_link: str
    recommended_authority_actions: List[str] = Field(default_factory=list)


class NotificationFeedResponse(BaseModel):
    case_id: str
    alerts: List[AuthorityAlert] = Field(default_factory=list)
    total_alerts: int = 0
    latest_attribution_alert: Optional[AuthorityAlert] = None


# ==============================================================================
# Phase 25: Data Readiness & Provenance Models
# ==============================================================================

class ReadinessCheckItem(BaseModel):
    name: str  # Satellite, Environmental, AIS, Temporal overlap, Spatial coverage, Ground truth, Artifact availability
    status: str  # Strictly one of: READY, LIMITED, UNAVAILABLE, NOT REQUIRED
    details: str
    source: Optional[str] = None


class DatasetProvenanceRecord(BaseModel):
    dataset_name: str
    source: str
    acquisition_time: Optional[str] = None
    processing_version: str = "v1.0.0"
    sha256_checksum: Optional[str] = None
    artifact_timestamp: Optional[str] = None
    record_type: str = "reproducible provenance"


class DataReadinessReport(BaseModel):
    case_id: str
    case_name: str
    validation_role: str
    overall_status: str  # READY, LIMITED, UNAVAILABLE, NOT REQUIRED
    checks: List[ReadinessCheckItem] = Field(default_factory=list)
    data_limitations: List[str] = Field(default_factory=list)
    provenance_records: List[DatasetProvenanceRecord] = Field(default_factory=list)
    summary_notes: str


# ==============================================================================
# Phase 26: Satellite Observation Metadata Models
# ==============================================================================

class Sentinel1Metadata(BaseModel):
    platform: str
    sensor: str
    acquisition_time_utc: str
    mode: str
    product_type: str
    polarization_used: str  # e.g., "VV"
    polarization_explanation: str
    polarizations_available: List[str] = Field(default_factory=list)
    orbit_direction: Optional[str] = None
    relative_orbit: Optional[int] = None
    spatial_resolution: Optional[str] = None
    scene_dimensions: Optional[str] = None
    scene_coverage: Optional[str] = None
    processing_status: str  # e.g., "CALIBRATED_AND_DETECTED"
    speckle_filter: Optional[str] = None
    cfar_detector_info: Optional[str] = None


class Sentinel2Metadata(BaseModel):
    available: bool = False
    platform: Optional[str] = None
    sensor: Optional[str] = None
    acquisition_time_utc: Optional[str] = None
    cloud_cover_percentage: Optional[float] = None
    cloud_cover_text: Optional[str] = None
    available_bands: List[str] = Field(default_factory=list)
    product_type: Optional[str] = None
    role: str = "Supporting optical observation"
    pipeline_usage_disclaimer: str = (
        "Supporting optical observation only. Not ingested by the operational SAR dark-spot detection pipeline."
    )
    details: Optional[str] = None


class TimelineObservationEvent(BaseModel):
    event_id: str
    label: str
    event_type: str  # PRE_EVENT, INCIDENT_REFERENCE, OPERATIONAL_SAR, SUPPORTING_OPTICAL, POST_EVENT
    timestamp_utc: str
    platform: Optional[str] = None
    observation_nature: str  # ACTUAL_OBSERVATION, INCIDENT_REFERENCE, REVISIT_OPPORTUNITY
    relative_to_incident_hours: float
    description: str


class ObservationTimeline(BaseModel):
    incident_time_utc: str
    operational_observation_time_utc: str
    events: List[TimelineObservationEvent] = Field(default_factory=list)


class RevisitContext(BaseModel):
    constellation_nominal_repeat_days: int = 12
    constellation_dual_repeat_days: int = 6
    sub_cycle_revisit_opportunity_hours: str
    revisit_distinction_notice: str = (
        "Satellite orbital revisit opportunity refers to geometric satellite track overpass geometry, "
        "whereas actual acquired observation requires active instrument scheduling, payload commanding, "
        "and successful data downlink and processing."
    )
    case_revisit_audit: str


class SatelliteObservationPackage(BaseModel):
    case_id: str
    case_name: str
    sentinel1: Sentinel1Metadata
    sentinel2: Optional[Sentinel2Metadata] = None
    timeline: ObservationTimeline
    revisit_context: RevisitContext



