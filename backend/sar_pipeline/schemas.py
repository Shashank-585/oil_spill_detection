"""
backend/sar_pipeline/schemas.py

Pydantic schemas for the Phase 5 SAR Observation Processing Pipeline.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ValidationCheckItem(BaseModel):
    check_id: str
    name: str
    passed: bool
    status: str  # "PASSED", "FAILED", "WARNING"
    message: str
    details: Optional[str] = None


class SARValidationResult(BaseModel):
    case_id: str
    observation_id: str
    is_valid: bool
    overall_status: str  # "READY_FOR_PROCESSING", "VALIDATION_FAILED"
    checks: List[ValidationCheckItem] = Field(default_factory=list)
    metadata_summary: Dict[str, Any] = Field(default_factory=dict)
    timestamp_utc: str


class SARObservationRecord(BaseModel):
    observation_id: str
    case_id: str
    platform: str
    sensor: str
    acquisition_timestamp_utc: str
    polarization: str
    polarizations_available: List[str] = Field(default_factory=list)
    acquisition_mode: str
    product_type: str
    crs: str
    raster_dimensions: Dict[str, Any]
    spatial_resolution: str
    geographic_bounds: List[float]  # [min_lon, min_lat, max_lon, max_lat]
    source_artifact: str
    processing_status: str  # "RAW", "CALIBRATED_INPUT", "PROCESSED", "READY_FOR_PROCESSING"
    role: str = "Operational detection channel"
    is_operational: bool = True
    validation_status: Optional[str] = None
    calibrated_radiometry_available: bool = False
    speckle_filter_info: Optional[str] = None
    detector_info: Optional[str] = None


class SARJobStage(BaseModel):
    stage_id: str
    name: str
    status: str  # "PENDING", "IN_PROGRESS", "COMPLETE", "SKIPPED_CALIBRATED_INPUT", "FAILED"
    details: str
    duration_ms: Optional[float] = None


class SARProcessingJob(BaseModel):
    job_id: str
    case_id: str
    observation_id: str
    current_stage: str  # "QUEUED", "VALIDATING", "CALIBRATING", "FILTERING", "DETECTING", "VECTORIZING", "COMPLETE", "FAILED"
    start_time_utc: str
    completion_time_utc: Optional[str] = None
    stages: List[SARJobStage] = Field(default_factory=list)
    output_artifacts: Dict[str, str] = Field(default_factory=dict)
    error_message: Optional[str] = None


class ProvenanceStep(BaseModel):
    step_number: int
    stage: str  # "SOURCE", "CALIBRATION", "FILTER", "DETECTION", "VECTORIZATION", "ATTRIBUTION"
    title: str
    method: str
    input_artifact: str
    output_artifact: str
    details: str
    status: str = "VERIFIED"


class SARDetectionSummary(BaseModel):
    total_candidates: int
    accepted_candidates: int
    rejected_candidates: int
    rejection_reasons: Dict[str, int] = Field(default_factory=dict)
    accepted_candidate_ids: List[str] = Field(default_factory=list)
    total_slick_area_ha: Optional[float] = None


class SARJobResult(BaseModel):
    job_id: str
    case_id: str
    observation_id: str
    status: str
    observation: Dict[str, Any]
    detection: SARDetectionSummary
    provenance_chain: List[ProvenanceStep] = Field(default_factory=list)
    output_artifacts: Dict[str, str] = Field(default_factory=dict)
    elapsed_seconds: Optional[float] = None
