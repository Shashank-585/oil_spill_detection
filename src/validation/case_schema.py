"""
Phase 11: Validation Case Schema and Failure Taxonomy.

Defines:
- Standard validation case schema
- Ground-truth isolation mechanisms
- Validation case roles (positive vessel, negative non-vessel, ambiguous)
- Comprehensive failure taxonomy across the 9 pipeline stages
- Structured per-case validation metrics container
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union


class SourceType(str, Enum):
    """Classification of oil spill source mechanism."""
    VESSEL = "vessel"
    PIPELINE = "pipeline"
    NATURAL = "natural"
    UNKNOWN = "unknown"
    OTHER = "other"


class GroundTruthQuality(str, Enum):
    """Reliability level of ground truth incident information."""
    VERIFIED = "VERIFIED"     # Officially investigated (e.g. USCG / NTSB / MAIB findings)
    PROBABLE = "PROBABLE"     # Strong operational consensus or eyewitness confirmation
    UNVERIFIED = "UNVERIFIED" # Preliminary, anecdotal, or ambiguous reports


class CaseQualityLevel(str, Enum):
    """
    Standardized ground truth confidence tier.
    A: Strong ground truth (official accident investigation: USCG, NTSB, MAIB, IMO, BEA Mer with verified culprit, time, and coordinates).
    B: Credible ground truth (strong operational consensus/eyewitness; minor temporal or spatial bounding uncertainty).
    C: Weak/indirect ground truth (preliminary or media reports; exploratory analysis only).
    D: Unsuitable for quantitative attribution validation (missing core culprit or location data; excluded from benchmarks).
    """
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class ValidationEligibility(str, Enum):
    """Eligibility status of a case for quantitative attribution evaluation."""
    ELIGIBLE = "ELIGIBLE"                               # Complete local data + Quality Level A/B
    PARTIALLY_ELIGIBLE = "PARTIALLY_ELIGIBLE"           # Quality C or minor non-critical telemetry gaps
    INELIGIBLE_MISSING_DATA = "INELIGIBLE_MISSING_DATA" # Missing raw satellite, AIS, or environment


class CaseStatus(str, Enum):
    """Availability and acquisition status of an incident."""
    VERIFIED_AVAILABLE = "VERIFIED_AVAILABLE"           # Locally ingested & ready for pipeline
    POTENTIALLY_AVAILABLE = "POTENTIALLY_AVAILABLE"     # Public archives identified, data pending download
    NOT_VERIFIED = "NOT_VERIFIED"                       # Lacks verifiable satellite/AIS record


class ValidationRole(str, Enum):
    """Validation expectation and role of a case."""
    POSITIVE_VESSEL_CASE = "POSITIVE_VESSEL_CASE"         # Known vessel spill: expect culprit in top candidates
    NEGATIVE_NON_VESSEL_CASE = "NEGATIVE_NON_VESSEL_CASE" # Pipeline/natural: expect refusal of vessel HIGH_SUPPORT
    AMBIGUOUS_CASE = "AMBIGUOUS_CASE"                     # Inconclusive ground truth: expect INSUFFICIENT_EVIDENCE


class FailureCategory(str, Enum):
    """Standardized failure taxonomy isolating the exact pipeline failure stage."""
    DETECTION_FAILURE = "DETECTION_FAILURE"                         # Phase 3: slick missed or falsely filtered
    SOURCE_RECONSTRUCTION_FAILURE = "SOURCE_RECONSTRUCTION_FAILURE" # Phase 4: backward Lagrangian drift missed source
    CANDIDATE_GENERATION_FAILURE = "CANDIDATE_GENERATION_FAILURE"   # Phase 5: known vessel filtered before attribution
    HYPOTHESIS_GENERATION_FAILURE = "HYPOTHESIS_GENERATION_FAILURE" # Phase 6: 4D hypothesis space failed to capture release
    FORWARD_SIMULATION_FAILURE = "FORWARD_SIMULATION_FAILURE"       # Phase 7: counterfactual particle model failed
    COMPARISON_FAILURE = "COMPARISON_FAILURE"                       # Phase 8: spill comparison metric distortion
    RANKING_FAILURE = "RANKING_FAILURE"                             # Phase 9: true culprit retained but ranked below competitors
    UNCERTAINTY_FAILURE = "UNCERTAINTY_FAILURE"                     # Phase 10: rank stability or sensitivity breakdown
    INSUFFICIENT_GROUND_TRUTH = "INSUFFICIENT_GROUND_TRUTH"         # Case lacked reliable validation ground truth
    SUCCESS = "SUCCESS"                                             # Case passed all validation criteria


@dataclass
class GroundTruth:
    """
    Reference ground truth data for a historical case.
    CRITICAL: This object is NEVER passed into the attribution pipeline.
    It is used strictly post-hoc for verification and scoring.
    """
    source_type: SourceType
    reference_source_location: Optional[Tuple[float, float]] = None  # (lon, lat)
    reference_source_time_utc: Optional[str] = None
    reference_vessel_mmsi: Optional[int] = None
    reference_vessel_name: Optional[str] = None
    ground_truth_quality: GroundTruthQuality = GroundTruthQuality.VERIFIED
    quality_level: CaseQualityLevel = CaseQualityLevel.A
    ground_truth_source: str = "Unspecified investigation report"
    ground_truth_confidence: float = 1.0
    validation_role: ValidationRole = ValidationRole.POSITIVE_VESSEL_CASE
    notes: str = ""

    def __post_init__(self):
        # Auto-align quality_level if default A was used but ground_truth_quality differs
        if self.ground_truth_quality == GroundTruthQuality.PROBABLE and self.quality_level == CaseQualityLevel.A:
            self.quality_level = CaseQualityLevel.B
        elif self.ground_truth_quality == GroundTruthQuality.UNVERIFIED and self.quality_level == CaseQualityLevel.A:
            self.quality_level = CaseQualityLevel.C


@dataclass
class AlgorithmInputs:
    """
    Pure algorithm input references without any ground truth contamination.
    """
    case_id: str
    satellite_files: Dict[str, Any] = field(default_factory=dict)
    ais_files: Dict[str, Any] = field(default_factory=dict)
    environmental_files: Dict[str, Any] = field(default_factory=dict)
    drift_parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationCase:
    """
    Complete validation case representation cleanly separating inputs from ground truth.
    """
    case_id: str
    incident_name: str
    incident_type: str
    is_synthetic: bool
    ground_truth: GroundTruth
    algorithm_inputs: AlgorithmInputs
    incident_date: Optional[str] = None
    case_availability: str = "AVAILABLE"  # AVAILABLE, PENDING_INGESTION, NOT_AVAILABLE
    case_status: CaseStatus = CaseStatus.VERIFIED_AVAILABLE
    validation_eligibility: ValidationEligibility = ValidationEligibility.ELIGIBLE

    # Data Availability Flags
    satellite_available: bool = True
    ais_available: bool = True
    currents_available: bool = True
    wind_available: bool = True
    source_location_available: bool = True
    source_time_available: bool = True
    culprit_vessel_available: bool = True

    def __post_init__(self):
        # Auto-populate availability flags from ground truth if not explicitly overridden
        if self.ground_truth.reference_source_location is None:
            self.source_location_available = False
        if self.ground_truth.reference_source_time_utc is None:
            self.source_time_available = False
        if self.ground_truth.reference_vessel_mmsi is None and self.ground_truth.source_type == SourceType.VESSEL:
            self.culprit_vessel_available = False

    def extract_blind_algorithm_inputs(self) -> Dict[str, Any]:
        """
        Extract only algorithm inputs, strictly omitting all reference ground-truth data.
        Guarantees zero ground-truth leakage into the attribution pipeline.
        """
        return {
            "case_id": self.case_id,
            "incident_name": self.incident_name,
            "satellite_files": self.algorithm_inputs.satellite_files,
            "ais_files": self.algorithm_inputs.ais_files,
            "environmental_files": self.algorithm_inputs.environmental_files,
            "drift_parameters": self.algorithm_inputs.drift_parameters,
        }

    def to_registry_record(self) -> Dict[str, Any]:
        """Convert to a standardized 15-field registry summary record."""
        return {
            "case_id": self.case_id,
            "incident_name": self.incident_name,
            "incident_date": self.incident_date or "2021-10-02",
            "source_type": self.ground_truth.source_type.value,
            "quality_level": self.ground_truth.quality_level.value,
            "ground_truth_quality": self.ground_truth.ground_truth_quality.value,
            "ground_truth_source": self.ground_truth.ground_truth_source,
            "satellite_available": self.satellite_available,
            "ais_available": self.ais_available,
            "currents_available": self.currents_available,
            "wind_available": self.wind_available,
            "source_location_available": self.source_location_available,
            "source_time_available": self.source_time_available,
            "culprit_vessel_available": self.culprit_vessel_available,
            "case_status": self.case_status.value,
            "validation_eligibility": self.validation_eligibility.value,
            # Contextual attributes preserved
            "validation_role": self.ground_truth.validation_role.value,
            "is_synthetic": self.is_synthetic,
            "case_availability": self.case_availability,
            "reference_vessel_mmsi": self.ground_truth.reference_vessel_mmsi,
            "reference_vessel_name": self.ground_truth.reference_vessel_name,
        }


def extract_blind_algorithm_inputs(case: ValidationCase) -> Dict[str, Any]:
    """Standalone wrapper to extract blind algorithm inputs from a validation case."""
    return case.extract_blind_algorithm_inputs()


@dataclass
class CaseValidationMetrics:
    """
    Structured performance metrics evaluated for a single validation case.
    """
    case_id: str
    incident_name: str
    source_type: str
    validation_role: str
    ground_truth_quality: str
    is_synthetic: bool

    # Candidate Generation Metrics (Phase 5)
    known_vessel_in_ais_raw: bool = False
    candidate_generation_recall: Optional[float] = None  # 1.0 if culprit in candidates, 0.0 if filtered

    # Attribution Ranking Metrics (Phase 9)
    known_vessel_rank: Optional[int] = None
    top_1_accuracy: Optional[float] = None
    top_3_accuracy: Optional[float] = None
    top_5_accuracy: Optional[float] = None
    top_hypothesis_id: Optional[str] = None
    top_vessel_name: Optional[str] = None
    top_evidence_score: float = 0.0
    top_evidence_state: str = "UNKNOWN"

    # Negative Non-Vessel Case Safety Metrics
    false_high_support_flag: bool = False  # True if any vessel received HIGH_SUPPORT on non-vessel case
    false_attribution_flag: bool = False   # True if any vessel was falsely declared responsible
    refused_high_support: bool = True      # True if HIGH_SUPPORT was avoided

    # Physical Source Reconstruction Accuracy (Phase 4 vs Ground Truth)
    source_location_error_m: Optional[float] = None
    source_time_error_seconds: Optional[float] = None
    forward_prediction_error_m: Optional[float] = None

    # Ensemble Rank Stability (Phase 10)
    top_1_ensemble_frequency: Optional[float] = None
    top_3_ensemble_frequency: Optional[float] = None
    mean_rank_ensemble: Optional[float] = None
    std_rank_ensemble: Optional[float] = None

    passed_validation: bool = False
    failure_category: FailureCategory = FailureCategory.SUCCESS
    notes: str = ""

    @property
    def passed(self) -> bool:
        """Alias for passed_validation."""
        return self.passed_validation

    @property
    def known_vessel_in_candidates(self) -> bool:
        """True if the known vessel was captured in Phase 5 candidates."""
        return self.candidate_generation_recall is not None and self.candidate_generation_recall > 0.5

    @property
    def known_vessel_in_top_1(self) -> bool:
        """True if the known vessel ranked #1."""
        return self.top_1_accuracy is not None and self.top_1_accuracy > 0.5

    @property
    def known_vessel_in_top_3(self) -> bool:
        """True if the known vessel ranked within top 3."""
        return self.top_3_accuracy is not None and self.top_3_accuracy > 0.5

    @property
    def top_1_score(self) -> float:
        """Score of the top ranked hypothesis/vessel."""
        return self.top_evidence_score

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res["failure_category"] = self.failure_category.value
        return res
